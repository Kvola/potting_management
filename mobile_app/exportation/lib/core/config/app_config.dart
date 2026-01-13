/// Configuration globale de l'application ICP Exportation
class AppConfig {
  AppConfig._();

  // Informations de l'application
  static const String appName = 'ICP Exportation';
  static const String appVersion = '1.0.0';
  static const String apiVersion = '1.0.0';

  // ============================================================
  // URL de base de l'API - MODIFIEZ CETTE VALEUR SELON VOTRE ENVIRONNEMENT
  // ============================================================
  // Production:
  // static const String baseUrl = 'https://odoo.icp.ci';
  
  // Développement local (IP de votre serveur Odoo):
  // static const String baseUrl = 'http://192.168.1.100:8069';
  
  // Localhost (pour tests avec Odoo local):
  static const String baseUrl = 'http://localhost:8069';
  // ============================================================

  // ============================================================
  // NOM DE LA BASE DE DONNÉES ODOO
  // ============================================================
  static const String database = 'icp_dev_db';
  // ============================================================

  // Endpoints API
  static const String apiPrefix = '/api/v1/potting';
  
  // Authentification
  static const String loginEndpoint = '$apiPrefix/auth/login';
  static const String logoutEndpoint = '$apiPrefix/auth/logout';
  
  // Dashboard
  static const String dashboardEndpoint = '$apiPrefix/dashboard';
  static const String transitOrdersEndpoint = '$apiPrefix/dashboard/transit-orders';
  static const String customerOrdersEndpoint = '$apiPrefix/dashboard/orders';
  
  // Rapports
  static const String reportSummaryEndpoint = '$apiPrefix/reports/summary';
  static const String dailyReportEndpoint = '$apiPrefix/reports/daily';
  
  // Détails OT
  static const String transitOrderDetailEndpoint = '$apiPrefix/transit-orders';
  
  // Santé
  static const String healthEndpoint = '$apiPrefix/health';

  // Configuration du cache
  static const Duration cacheValidityDuration = Duration(hours: 1);
  static const Duration tokenRefreshThreshold = Duration(days: 1);
  
  // Pagination
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  // Timeouts
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 60);

  // Refresh intervals
  static const Duration dashboardRefreshInterval = Duration(minutes: 5);
  static const Duration ordersRefreshInterval = Duration(minutes: 10);
}

/// Types de produits cacao
enum ProductType {
  cocoaMass('cocoa_mass', 'Masse de cacao'),
  cocoaButter('cocoa_butter', 'Beurre de cacao'),
  cocoaCake('cocoa_cake', 'Tourteau de cacao'),
  cocoaPowder('cocoa_powder', 'Poudre de cacao');

  final String value;
  final String label;
  const ProductType(this.value, this.label);

  static ProductType? fromValue(String? value) {
    if (value == null) return null;
    return ProductType.values.firstWhere(
      (e) => e.value == value,
      orElse: () => ProductType.cocoaMass,
    );
  }
}

/// États des ordres de transit
enum TransitOrderState {
  draft('draft', 'Brouillon'),
  lotsGenerated('lots_generated', 'Lots générés'),
  inProgress('in_progress', 'En cours'),
  readyValidation('ready_validation', 'Prêt validation'),
  done('done', 'Validé'),
  cancelled('cancelled', 'Annulé');

  final String value;
  final String label;
  const TransitOrderState(this.value, this.label);

  static TransitOrderState? fromValue(String? value) {
    if (value == null) return null;
    return TransitOrderState.values.firstWhere(
      (e) => e.value == value,
      orElse: () => TransitOrderState.draft,
    );
  }
}

/// États de livraison
enum DeliveryStatus {
  notDelivered('not_delivered', 'Non livré'),
  partial('partial', 'Partiel'),
  fullyDelivered('fully_delivered', 'Livré');

  final String value;
  final String label;
  const DeliveryStatus(this.value, this.label);

  static DeliveryStatus? fromValue(String? value) {
    if (value == null) return null;
    return DeliveryStatus.values.firstWhere(
      (e) => e.value == value,
      orElse: () => DeliveryStatus.notDelivered,
    );
  }
}
