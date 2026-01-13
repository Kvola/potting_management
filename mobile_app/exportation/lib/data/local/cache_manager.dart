import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';
import 'package:logger/logger.dart';

import '../../core/config/app_config.dart';
import '../models/models.dart';

/// Gestionnaire de cache local avec Hive
class CacheManager {
  static final CacheManager _instance = CacheManager._internal();
  factory CacheManager() => _instance;
  CacheManager._internal();

  final Logger _logger = Logger();

  static const String _dashboardBoxName = 'dashboard_cache';
  static const String _transitOrdersBoxName = 'transit_orders_cache';
  static const String _transitOrderDetailsBoxName = 'transit_order_details_cache';
  static const String _cacheMetaBoxName = 'cache_meta';

  late Box<String> _dashboardBox;
  late Box<String> _transitOrdersBox;
  late Box<String> _transitOrderDetailsBox;
  late Box<String> _cacheMetaBox;

  bool _isInitialized = false;

  /// Initialiser le gestionnaire de cache
  static Future<void> init() async {
    await CacheManager()._initialize();
  }

  Future<void> _initialize() async {
    if (_isInitialized) return;

    try {
      _dashboardBox = await Hive.openBox<String>(_dashboardBoxName);
      _transitOrdersBox = await Hive.openBox<String>(_transitOrdersBoxName);
      _transitOrderDetailsBox = await Hive.openBox<String>(_transitOrderDetailsBoxName);
      _cacheMetaBox = await Hive.openBox<String>(_cacheMetaBoxName);

      _isInitialized = true;
      _logger.i('CacheManager initialisé');
    } catch (e) {
      _logger.e('Erreur lors de l\'initialisation du cache: $e');
    }
  }

  /// Vérifier si le cache est valide
  bool _isCacheValid(String key) {
    final metaKey = '${key}_timestamp';
    final timestamp = _cacheMetaBox.get(metaKey);
    
    if (timestamp == null) return false;
    
    final cachedAt = DateTime.tryParse(timestamp);
    if (cachedAt == null) return false;
    
    final now = DateTime.now();
    return now.difference(cachedAt) < AppConfig.cacheValidityDuration;
  }

  /// Mettre à jour le timestamp du cache
  void _updateCacheTimestamp(String key) {
    final metaKey = '${key}_timestamp';
    _cacheMetaBox.put(metaKey, DateTime.now().toIso8601String());
  }

  // ==================== DASHBOARD ====================

  /// Sauvegarder le dashboard en cache
  Future<void> saveDashboard(String key, DashboardModel dashboard) async {
    try {
      await _dashboardBox.put(key, jsonEncode(dashboard.toJson()));
      _updateCacheTimestamp(key);
    } catch (e) {
      _logger.e('Erreur lors de la sauvegarde du dashboard: $e');
    }
  }

  /// Récupérer le dashboard depuis le cache
  Future<DashboardModel?> getDashboard(String key) async {
    try {
      if (!_isCacheValid(key)) return null;

      final json = _dashboardBox.get(key);
      if (json == null) return null;

      final data = jsonDecode(json) as Map<String, dynamic>;
      return DashboardModel.fromJson(data, null);
    } catch (e) {
      _logger.e('Erreur lors de la lecture du dashboard: $e');
      return null;
    }
  }

  // ==================== TRANSIT ORDERS ====================

  /// Sauvegarder les ordres de transit en cache
  Future<void> saveTransitOrders(
    String key,
    PaginatedResponse<TransitOrderModel> response,
  ) async {
    try {
      final data = {
        'items': response.items.map((e) => e.toJson()).toList(),
        'meta': {
          'total': response.total,
          'page': response.page,
          'limit': response.limit,
          'pages': response.pages,
        },
      };
      await _transitOrdersBox.put(key, jsonEncode(data));
      _updateCacheTimestamp(key);
    } catch (e) {
      _logger.e('Erreur lors de la sauvegarde des OT: $e');
    }
  }

  /// Récupérer les ordres de transit depuis le cache
  Future<PaginatedResponse<TransitOrderModel>?> getTransitOrders(String key) async {
    try {
      if (!_isCacheValid(key)) return null;

      final json = _transitOrdersBox.get(key);
      if (json == null) return null;

      final data = jsonDecode(json) as Map<String, dynamic>;
      final items = (data['items'] as List)
          .map((e) => TransitOrderModel.fromJson(e as Map<String, dynamic>))
          .toList();
      final meta = data['meta'] as Map<String, dynamic>;

      return PaginatedResponse<TransitOrderModel>(
        items: items,
        total: meta['total'] as int,
        page: meta['page'] as int,
        limit: meta['limit'] as int,
        pages: meta['pages'] as int,
      );
    } catch (e) {
      _logger.e('Erreur lors de la lecture des OT: $e');
      return null;
    }
  }

  // ==================== TRANSIT ORDER DETAILS ====================

  /// Sauvegarder les détails d'un OT en cache
  Future<void> saveTransitOrderDetail(String key, TransitOrderModel order) async {
    try {
      await _transitOrderDetailsBox.put(key, jsonEncode(order.toJson()));
      _updateCacheTimestamp(key);
    } catch (e) {
      _logger.e('Erreur lors de la sauvegarde des détails OT: $e');
    }
  }

  /// Récupérer les détails d'un OT depuis le cache
  Future<TransitOrderModel?> getTransitOrderDetail(String key) async {
    try {
      if (!_isCacheValid(key)) return null;

      final json = _transitOrderDetailsBox.get(key);
      if (json == null) return null;

      final data = jsonDecode(json) as Map<String, dynamic>;
      return TransitOrderModel.fromJson(data);
    } catch (e) {
      _logger.e('Erreur lors de la lecture des détails OT: $e');
      return null;
    }
  }

  // ==================== GESTION DU CACHE ====================

  /// Vider tout le cache
  Future<void> clearAll() async {
    await _dashboardBox.clear();
    await _transitOrdersBox.clear();
    await _transitOrderDetailsBox.clear();
    await _cacheMetaBox.clear();
    _logger.i('Cache vidé');
  }

  /// Vider le cache du dashboard
  Future<void> clearDashboard() async {
    await _dashboardBox.clear();
    _logger.i('Cache dashboard vidé');
  }

  /// Vider le cache des ordres de transit
  Future<void> clearTransitOrders() async {
    await _transitOrdersBox.clear();
    await _transitOrderDetailsBox.clear();
    _logger.i('Cache OT vidé');
  }

  /// Obtenir la taille du cache
  Future<Map<String, int>> getCacheSize() async {
    return {
      'dashboard': _dashboardBox.length,
      'transit_orders': _transitOrdersBox.length,
      'transit_order_details': _transitOrderDetailsBox.length,
    };
  }

  /// Obtenir la dernière mise à jour du cache
  DateTime? getLastUpdate(String key) {
    final metaKey = '${key}_timestamp';
    final timestamp = _cacheMetaBox.get(metaKey);
    if (timestamp == null) return null;
    return DateTime.tryParse(timestamp);
  }
}
