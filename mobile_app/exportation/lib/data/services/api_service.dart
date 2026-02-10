import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/config/app_config.dart';
import '../models/models.dart';
import '../local/cache_manager.dart';
import 'http_service.dart';

/// Service API pour le tableau de bord et les rapports
class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final HttpService _httpService = HttpService();
  final CacheManager _cacheManager = CacheManager();
  final Logger _logger = Logger();

  // ==================== DASHBOARD ====================

  /// Récupérer les statistiques du tableau de bord
  Future<DashboardModel> getDashboard({
    String? dateFrom,
    String? dateTo,
    bool forceRefresh = false,
  }) async {
    final cacheKey = 'dashboard_${dateFrom ?? 'all'}_${dateTo ?? 'all'}';

    // Vérifier le cache si pas de refresh forcé
    if (!forceRefresh) {
      final cached = await _cacheManager.getDashboard(cacheKey);
      if (cached != null) {
        return cached;
      }
    }

    try {
      final queryParams = <String, dynamic>{};
      if (dateFrom != null) queryParams['date_from'] = dateFrom;
      if (dateTo != null) queryParams['date_to'] = dateTo;

      final response = await _httpService.get(
        AppConfig.dashboardEndpoint,
        queryParameters: queryParams,
      );

      final data = _parseResponse(response.data);
      
      if (data['success'] != true) {
        throw _handleApiError(data);
      }

      final dashboard = DashboardModel.fromJson(
        data['data'] as Map<String, dynamic>,
        data['meta'] as Map<String, dynamic>?,
      );

      // Mettre en cache
      await _cacheManager.saveDashboard(cacheKey, dashboard);

      return dashboard;
    } catch (e) {
      _logger.e('Erreur getDashboard: $e');
      
      // En cas d'erreur réseau, retourner le cache
      final cached = await _cacheManager.getDashboard(cacheKey);
      if (cached != null) {
        return cached;
      }
      
      if (e is ApiException) rethrow;
      throw ApiException.serverError(e.toString());
    }
  }

  // ==================== TRANSIT ORDERS ====================

  /// Récupérer la liste des ordres de transit
  Future<PaginatedResponse<TransitOrderModel>> getTransitOrders({
    int page = 1,
    int limit = 20,
    String? dateFrom,
    String? dateTo,
    String? state,
    String? productType,
    int? customerId,
    bool includeDetails = false,
    bool forceRefresh = false,
  }) async {
    final cacheKey = 'transit_orders_${page}_${limit}_${state ?? 'all'}_${productType ?? 'all'}';

    // Vérifier le cache si pas de refresh forcé
    if (!forceRefresh) {
      final cached = await _cacheManager.getTransitOrders(cacheKey);
      if (cached != null) {
        return cached;
      }
    }

    try {
      final queryParams = <String, dynamic>{
        'page': page.toString(),
        'limit': limit.toString(),
        'include_details': includeDetails ? '1' : '0',
      };
      
      if (dateFrom != null) queryParams['date_from'] = dateFrom;
      if (dateTo != null) queryParams['date_to'] = dateTo;
      if (state != null) queryParams['state'] = state;
      if (productType != null) queryParams['product_type'] = productType;
      if (customerId != null) queryParams['customer_id'] = customerId.toString();

      final response = await _httpService.get(
        AppConfig.transitOrdersEndpoint,
        queryParameters: queryParams,
      );

      final data = _parseResponse(response.data);
      
      if (data['success'] != true) {
        throw _handleApiError(data);
      }

      final paginatedResponse = PaginatedResponse.fromJson(
        data,
        TransitOrderModel.fromJson,
      );

      // Mettre en cache
      await _cacheManager.saveTransitOrders(cacheKey, paginatedResponse);

      return paginatedResponse;
    } catch (e) {
      _logger.e('Erreur getTransitOrders: $e');
      
      // En cas d'erreur réseau, retourner le cache
      final cached = await _cacheManager.getTransitOrders(cacheKey);
      if (cached != null) {
        return cached;
      }
      
      if (e is ApiException) rethrow;
      throw ApiException.serverError(e.toString());
    }
  }

  /// Récupérer les détails d'un ordre de transit
  Future<TransitOrderModel> getTransitOrderDetail(int id) async {
    final cacheKey = 'transit_order_$id';

    try {
      final response = await _httpService.get(
        '${AppConfig.transitOrderDetailEndpoint}/$id',
      );

      final data = _parseResponse(response.data);
      
      if (data['success'] != true) {
        throw _handleApiError(data);
      }

      final order = TransitOrderModel.fromJson(data['data'] as Map<String, dynamic>);

      // Mettre en cache
      await _cacheManager.saveTransitOrderDetail(cacheKey, order);

      return order;
    } catch (e) {
      _logger.e('Erreur getTransitOrderDetail: $e');
      
      // En cas d'erreur réseau, retourner le cache
      final cached = await _cacheManager.getTransitOrderDetail(cacheKey);
      if (cached != null) {
        return cached;
      }
      
      if (e is ApiException) rethrow;
      throw ApiException.serverError(e.toString());
    }
  }

  /// Récupérer les OTs non vendus avec leurs lots (Vue PDG)
  Future<UnsoldTransitOrdersResponse> getUnsoldTransitOrders({
    String? productType,
    int? customerId,
    int limit = 50,
    bool forceRefresh = false,
  }) async {
    final cacheKey = 'unsold_transit_orders_${productType ?? 'all'}_${customerId ?? 'all'}';

    // Vérifier le cache si pas de refresh forcé
    if (!forceRefresh) {
      final cached = await _cacheManager.get<Map<String, dynamic>>(cacheKey);
      if (cached != null) {
        try {
          return UnsoldTransitOrdersResponse.fromJson(cached, null);
        } catch (_) {
          // Cache invalide, ignorer
        }
      }
    }

    try {
      final queryParams = <String, dynamic>{
        'limit': limit.toString(),
      };
      
      if (productType != null) queryParams['product_type'] = productType;
      if (customerId != null) queryParams['customer_id'] = customerId.toString();

      final response = await _httpService.get(
        AppConfig.unsoldTransitOrdersEndpoint,
        queryParameters: queryParams,
      );

      final data = _parseResponse(response.data);
      
      if (data['success'] != true) {
        throw _handleApiError(data);
      }

      final result = UnsoldTransitOrdersResponse.fromJson(
        data['data'] as Map<String, dynamic>,
        data['meta'] as Map<String, dynamic>?,
      );

      // Mettre en cache
      await _cacheManager.set(cacheKey, result.toJson());

      return result;
    } catch (e) {
      _logger.e('Erreur getUnsoldTransitOrders: $e');
      
      if (e is ApiException) rethrow;
      throw ApiException.serverError(e.toString());
    }
  }

  // ==================== RAPPORTS ====================

  /// Récupérer le résumé du rapport
  Future<ReportSummaryModel> getReportSummary({
    String? date,
    String? dateFrom,
    String? dateTo,
    bool excludeFullyDelivered = true,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'exclude_fully_delivered': excludeFullyDelivered ? '1' : '0',
      };
      
      if (date != null) queryParams['date'] = date;
      if (dateFrom != null) queryParams['date_from'] = dateFrom;
      if (dateTo != null) queryParams['date_to'] = dateTo;

      final response = await _httpService.get(
        AppConfig.reportSummaryEndpoint,
        queryParameters: queryParams,
      );

      final data = _parseResponse(response.data);
      
      if (data['success'] != true) {
        throw _handleApiError(data);
      }

      return ReportSummaryModel.fromJson(data['data'] as Map<String, dynamic>);
    } catch (e) {
      _logger.e('Erreur getReportSummary: $e');
      if (e is ApiException) rethrow;
      throw ApiException.serverError(e.toString());
    }
  }

  /// Télécharger le rapport quotidien en PDF
  Future<File> downloadDailyReport({
    String? date,
    String? dateFrom,
    String? dateTo,
    bool excludeFullyDelivered = true,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'exclude_fully_delivered': excludeFullyDelivered ? '1' : '0',
      };
      
      if (date != null) queryParams['date'] = date;
      if (dateFrom != null) queryParams['date_from'] = dateFrom;
      if (dateTo != null) queryParams['date_to'] = dateTo;

      final bytes = await _httpService.downloadFile(
        AppConfig.dailyReportEndpoint,
        queryParameters: queryParams,
      );

      if (bytes.isEmpty) {
        throw ApiException(
          code: 'BUS_001',
          message: 'Erreur lors de la génération du rapport',
        );
      }

      // Sauvegarder le fichier (non supporté sur web)
      if (kIsWeb) {
        throw ApiException(
          code: 'PLATFORM_001',
          message: 'Le téléchargement de PDF n\'est pas supporté sur le web.\nUtilisez l\'application mobile.',
        );
      }

      try {
        final directory = await getApplicationDocumentsDirectory();
        final reportDate = date ?? DateTime.now().toIso8601String().split('T')[0];
        final filename = 'OT_Daily_Report_$reportDate.pdf';
        final file = File('${directory.path}/$filename');
        
        await file.writeAsBytes(bytes);
        
        return file;
      } catch (e) {
        _logger.e('Erreur sauvegarde fichier: $e');
        throw ApiException(
          code: 'FILE_001',
          message: 'Impossible de sauvegarder le fichier.\nVérifiez les permissions de l\'application.',
        );
      }
    } on ApiException {
      rethrow;
    } catch (e) {
      _logger.e('Erreur downloadDailyReport: $e');
      // Gérer spécifiquement l'erreur 404
      final errorStr = e.toString();
      if (errorStr.contains('404')) {
        throw ApiException(
          code: 'BUS_002',
          message: 'Aucun ordre de transit disponible pour générer le rapport',
        );
      }
      throw ApiException.serverError('Impossible de télécharger le rapport');
    }
  }

  // ==================== HEALTH CHECK ====================

  /// Vérifier la santé de l'API
  Future<bool> checkHealth() async {
    try {
      final response = await _httpService.get(AppConfig.healthEndpoint);
      final data = _parseResponse(response.data);
      return data['success'] == true && data['data']?['status'] == 'healthy';
    } catch (e) {
      _logger.e('Erreur checkHealth: $e');
      return false;
    }
  }

  // ==================== UTILITAIRES ====================

  /// Parser la réponse (gérer différents formats dont JSON-RPC)
  Map<String, dynamic> _parseResponse(dynamic data) {
    Map<String, dynamic> result;
    
    if (data is String) {
      result = jsonDecode(data) as Map<String, dynamic>;
    } else if (data is Map<String, dynamic>) {
      result = data;
    } else {
      throw ApiException.serverError('Format de réponse invalide');
    }
    
    // Si c'est une réponse JSON-RPC, extraire le résultat
    if (result.containsKey('jsonrpc') && result.containsKey('result')) {
      return result['result'] as Map<String, dynamic>;
    }
    
    return result;
  }

  /// Gérer les erreurs API
  ApiException _handleApiError(Map<String, dynamic> data) {
    final error = data['error'] as Map<String, dynamic>?;
    if (error != null) {
      return ApiException(
        code: error['code'] as String? ?? 'UNKNOWN',
        message: error['message'] as String? ?? 'Une erreur est survenue',
      );
    }
    return ApiException.serverError();
  }
}
