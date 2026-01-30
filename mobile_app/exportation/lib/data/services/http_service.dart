import 'dart:convert';
import 'dart:io';
import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

import '../../core/config/app_config.dart';
import '../models/api_response.dart';

/// Service HTTP de base utilisant Dio avec gestion robuste des erreurs
/// 
/// Fonctionnalités:
/// - Retry automatique avec backoff exponentiel
/// - Timeout configurable
/// - Logging détaillé en mode debug
/// - Gestion des erreurs réseau
/// - Support JSON-RPC pour Odoo
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
  
  /// Nombre max de tentatives pour les requêtes
  static const int _maxRetries = 3;
  
  /// Délai initial entre les tentatives (en ms)
  static const int _initialRetryDelay = 1000;

  /// Initialiser le service HTTP
  void init() {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.baseUrl,
        connectTimeout: AppConfig.connectionTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        sendTimeout: const Duration(seconds: 30),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Odoo-Database': AppConfig.database,
        },
        validateStatus: (status) => status != null && status < 500,
      ),
    );

    // Intercepteur pour les logs et l'authentification
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          // Ajouter le token si disponible
          if (_authToken != null) {
            options.headers['Authorization'] = 'Bearer $_authToken';
          }
          
          // Ajouter un ID de corrélation pour le tracing
          options.headers['X-Request-ID'] = _generateRequestId();
          
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
          _logger.e('❌ ${error.type}: ${error.message}');
          return handler.next(error);
        },
      ),
    );
  }
  
  /// Générer un ID de requête unique pour le tracing
  String _generateRequestId() {
    return DateTime.now().millisecondsSinceEpoch.toString() + 
           (DateTime.now().microsecond % 1000).toString().padLeft(3, '0');
  }

  /// Définir le token d'authentification
  void setAuthToken(String? token) {
    _authToken = token;
    if (kDebugMode && token != null) {
      _logger.i('🔐 Token défini');
    }
  }

  /// Supprimer le token d'authentification
  void clearAuthToken() {
    _authToken = null;
    if (kDebugMode) {
      _logger.i('🔓 Token supprimé');
    }
  }

  /// Vérifier si un token est défini
  bool get hasAuthToken => _authToken != null;

  /// GET request avec retry automatique
  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool enableRetry = true,
  }) async {
    return _executeWithRetry(
      () => _dio.get(
        path,
        queryParameters: queryParameters,
        options: options,
      ),
      enableRetry: enableRetry,
    );
  }

  /// POST request (JSON) avec retry automatique
  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    bool useJsonRpc = false,
    bool enableRetry = true,
  }) async {
    return _executeWithRetry(
      () async {
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
          _logger.d('📤 Envoi: ${jsonData.toString().substring(0, jsonData.toString().length > 200 ? 200 : jsonData.toString().length)}...');
        }
        
        return _dio.post(
          path,
          data: jsonData,
          queryParameters: queryParameters,
          options: options ?? Options(
            headers: {'Content-Type': 'application/json'},
          ),
        );
      },
      enableRetry: enableRetry,
    );
  }

  /// POST request spécial pour Odoo (type='json')
  Future<Response> postJsonRpc(
    String path, {
    required Map<String, dynamic> params,
    bool enableRetry = true,
  }) async {
    return _executeWithRetry(
      () => _dio.post(
        path,
        data: jsonEncode(params),
        options: Options(
          headers: {
            'Content-Type': 'application/json',
          },
        ),
      ),
      enableRetry: enableRetry,
    );
  }

  /// Télécharger un fichier (PDF) avec retry
  Future<List<int>> downloadFile(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _executeWithRetry(
      () => _dio.get<List<int>>(
        path,
        queryParameters: queryParameters,
        options: Options(
          responseType: ResponseType.bytes,
          headers: {
            'Accept': 'application/pdf',
          },
        ),
      ),
      enableRetry: true,
    );
    return response.data ?? [];
  }
  
  /// Exécuter une requête avec retry et backoff exponentiel
  Future<Response<T>> _executeWithRetry<T>(
    Future<Response<T>> Function() request, {
    bool enableRetry = true,
  }) async {
    int attempts = 0;
    
    while (true) {
      try {
        return await request();
      } on DioException catch (e) {
        attempts++;
        
        // Vérifier si on doit réessayer
        final shouldRetry = enableRetry &&
            attempts < _maxRetries &&
            _isRetryableError(e);
        
        if (!shouldRetry) {
          throw _handleDioError(e);
        }
        
        // Calculer le délai avec backoff exponentiel
        final delay = _initialRetryDelay * (1 << (attempts - 1));
        
        if (kDebugMode) {
          _logger.w('🔄 Tentative $attempts/$_maxRetries échouée, retry dans ${delay}ms');
        }
        
        await Future.delayed(Duration(milliseconds: delay));
      }
    }
  }
  
  /// Vérifie si une erreur est retryable
  bool _isRetryableError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.connectionError:
        return true;
      case DioExceptionType.badResponse:
        // Retry sur 5xx mais pas sur 4xx
        final statusCode = error.response?.statusCode ?? 0;
        return statusCode >= 500 && statusCode < 600;
      default:
        return false;
    }
  }

  /// Gérer les erreurs Dio de manière robuste
  ApiException _handleDioError(DioException error) {
    // Logger l'erreur pour le debugging
    if (kDebugMode) {
      _logger.e('DioError: ${error.type} - ${error.message}');
      if (error.response?.data != null) {
        _logger.e('Response: ${error.response?.data}');
      }
    }
    
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
        
        if (statusCode == 403) {
          return ApiException(
            code: 'FORBIDDEN',
            message: 'Accès non autorisé à cette ressource.',
          );
        }
        
        if (statusCode == 404) {
          return ApiException(
            code: 'NOT_FOUND',
            message: 'La ressource demandée n\'existe pas.',
          );
        }
        
        if (statusCode == 429) {
          return ApiException(
            code: 'RATE_LIMITED',
            message: 'Trop de requêtes. Veuillez patienter quelques instants.',
          );
        }

        // Essayer d'extraire le message d'erreur de l'API
        if (data is Map<String, dynamic>) {
          if (data['error'] != null) {
            final apiError = ApiError.fromJson(data['error'] as Map<String, dynamic>);
            return ApiException.fromApiError(apiError, statusCode: statusCode);
          }
          if (data['success'] == false && data['error'] != null) {
            final apiError = ApiError.fromJson(data['error'] as Map<String, dynamic>);
            return ApiException.fromApiError(apiError, statusCode: statusCode);
          }
          if (data['message'] != null) {
            return ApiException(
              code: data['code'] as String? ?? 'SERVER_ERROR',
              message: data['message'] as String,
            );
          }
        }

        return ApiException.serverError(
          statusCode != null && statusCode >= 500
              ? 'Erreur serveur. Nos équipes ont été notifiées.'
              : 'Une erreur inattendue est survenue.',
        );

      case DioExceptionType.cancel:
        return ApiException(
          code: 'CANCELLED',
          message: 'Requête annulée',
        );

      case DioExceptionType.badCertificate:
        return ApiException(
          code: 'CERT_ERROR',
          message: 'Erreur de certificat SSL. Contactez le support.',
        );

      default:
        if (error.error is SocketException) {
          return ApiException.networkError();
        }
        return ApiException.serverError(
          error.message ?? 'Une erreur inattendue est survenue.',
        );
    }
  }
}
