import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

import '../../core/config/app_config.dart';
import '../models/api_response.dart';

/// Service HTTP de base utilisant Dio
class HttpService {
  static final HttpService _instance = HttpService._internal();
  factory HttpService() => _instance;
  HttpService._internal();

  late Dio _dio;
  final Logger _logger = Logger(
    printer: PrettyPrinter(
      methodCount: 0,
      printTime: true,
    ),
  );

  String? _authToken;

  /// Initialiser le service HTTP
  void init() {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.baseUrl,
        connectTimeout: AppConfig.connectionTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Odoo-Database': AppConfig.database,
        },
      ),
    );

    // Intercepteur pour les logs
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (_authToken != null) {
            options.headers['Authorization'] = 'Bearer $_authToken';
          }
          if (kDebugMode) {
            _logger.d('➡️ ${options.method} ${options.path}');
          }
          return handler.next(options);
        },
        onResponse: (response, handler) {
          if (kDebugMode) {
            _logger.d('✅ ${response.statusCode} ${response.requestOptions.path}');
          }
          return handler.next(response);
        },
        onError: (error, handler) {
          _logger.e('❌ ${error.message}');
          return handler.next(error);
        },
      ),
    );
  }

  /// Définir le token d'authentification
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Supprimer le token d'authentification
  void clearAuthToken() {
    _authToken = null;
  }

  /// Vérifier si un token est défini
  bool get hasAuthToken => _authToken != null;

  /// GET request
  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.get(
        path,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// POST request (JSON)
  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool useJsonRpc = false,
  }) async {
    try {
      dynamic jsonData;
      
      if (useJsonRpc && data is Map) {
        // Format JSON-RPC pour Odoo type='json'
        jsonData = jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'params': data,
          'id': null,
        });
      } else {
        jsonData = data is Map || data is List ? jsonEncode(data) : data;
      }
      
      if (kDebugMode) {
        _logger.d('📤 Envoi: $jsonData');
      }
      return await _dio.post(
        path,
        data: jsonData,
        queryParameters: queryParameters,
        options: options ?? Options(
          headers: {'Content-Type': 'application/json'},
        ),
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// POST request spécial pour Odoo (type='json')
  Future<Response> postJsonRpc(
    String path, {
    required Map<String, dynamic> params,
  }) async {
    try {
      // Odoo JSON-RPC attend les paramètres dans 'params'
      return await _dio.post(
        path,
        data: jsonEncode(params),
        options: Options(
          headers: {
            'Content-Type': 'application/json',
          },
        ),
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Télécharger un fichier (PDF)
  Future<List<int>> downloadFile(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.get<List<int>>(
        path,
        queryParameters: queryParameters,
        options: Options(
          responseType: ResponseType.bytes,
          headers: {
            'Accept': 'application/pdf',
          },
        ),
      );
      return response.data ?? [];
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Gérer les erreurs Dio
  ApiException _handleDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException.timeout();

      case DioExceptionType.connectionError:
        return ApiException.networkError();

      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        final data = error.response?.data;

        if (statusCode == 401) {
          return ApiException.unauthorized();
        }

        if (data is Map<String, dynamic>) {
          if (data['error'] != null) {
            final apiError = ApiError.fromJson(data['error'] as Map<String, dynamic>);
            return ApiException.fromApiError(apiError, statusCode: statusCode);
          }
          if (data['success'] == false && data['error'] != null) {
            final apiError = ApiError.fromJson(data['error'] as Map<String, dynamic>);
            return ApiException.fromApiError(apiError, statusCode: statusCode);
          }
        }

        return ApiException.serverError();

      case DioExceptionType.cancel:
        return ApiException(
          code: 'CANCELLED',
          message: 'Requête annulée',
        );

      default:
        if (error.error is SocketException) {
          return ApiException.networkError();
        }
        return ApiException.serverError(error.message);
    }
  }
}
