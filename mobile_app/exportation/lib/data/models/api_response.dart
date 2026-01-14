/// Modèle générique de réponse API
class ApiResponse<T> {
  final bool success;
  final T? data;
  final ApiError? error;
  final String? apiVersion;
  final String? timestamp;
  final Map<String, dynamic>? meta;

  ApiResponse({
    required this.success,
    this.data,
    this.error,
    this.apiVersion,
    this.timestamp,
    this.meta,
  });

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>)? fromJsonT,
  ) {
    return ApiResponse(
      success: json['success'] as bool? ?? false,
      data: json['data'] != null && fromJsonT != null
          ? fromJsonT(json['data'] as Map<String, dynamic>)
          : null,
      error: json['error'] != null
          ? ApiError.fromJson(json['error'] as Map<String, dynamic>)
          : null,
      apiVersion: json['api_version'] as String?,
      timestamp: json['timestamp'] as String?,
      meta: json['meta'] as Map<String, dynamic>?,
    );
  }

  bool get isSuccess => success && error == null;
  bool get isError => !success || error != null;
}

/// Modèle de réponse avec liste paginée
class PaginatedResponse<T> {
  final List<T> items;
  final int total;
  final int page;
  final int limit;
  final int pages;

  PaginatedResponse({
    required this.items,
    required this.total,
    required this.page,
    required this.limit,
    required this.pages,
  });

  factory PaginatedResponse.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) fromJsonT,
  ) {
    final data = json['data'] as Map<String, dynamic>? ?? {};
    final meta = json['meta'] as Map<String, dynamic>? ?? {};
    
    return PaginatedResponse(
      items: (data['items'] as List?)
              ?.map((e) => fromJsonT(e as Map<String, dynamic>))
              .toList() ??
          [],
      total: meta['total'] as int? ?? 0,
      page: meta['page'] as int? ?? 1,
      limit: meta['limit'] as int? ?? 20,
      pages: meta['pages'] as int? ?? 1,
    );
  }

  bool get hasMore => page < pages;
  bool get isEmpty => items.isEmpty;
  bool get isNotEmpty => items.isNotEmpty;
}

/// Modèle d'erreur API
class ApiError {
  final String code;
  final String message;

  ApiError({
    required this.code,
    required this.message,
  });

  factory ApiError.fromJson(Map<String, dynamic> json) {
    return ApiError(
      code: json['code'] as String? ?? 'UNKNOWN',
      message: json['message'] as String? ?? 'Une erreur est survenue',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'code': code,
      'message': message,
    };
  }

  /// Vérifier si l'erreur est liée à l'authentification
  bool get isAuthError => code.startsWith('AUTH_');

  /// Vérifier si l'erreur est liée à la validation
  bool get isValidationError => code.startsWith('VAL_');

  /// Vérifier si le token est expiré
  bool get isTokenExpired => code == 'AUTH_002' || code == 'AUTH_003';

  /// Vérifier si c'est une erreur de limite de requêtes
  bool get isRateLimitError => code == 'AUTH_010';

  @override
  String toString() => '[$code] $message';
}

/// Exception personnalisée pour les erreurs API
class ApiException implements Exception {
  final String code;
  final String message;
  final int? statusCode;
  final dynamic originalError;

  ApiException({
    required this.code,
    required this.message,
    this.statusCode,
    this.originalError,
  });

  factory ApiException.fromApiError(ApiError error, {int? statusCode}) {
    return ApiException(
      code: error.code,
      message: _getLocalizedMessage(error.code, error.message),
      statusCode: statusCode,
    );
  }

  factory ApiException.networkError([String? message]) {
    return ApiException(
      code: 'NETWORK_ERROR',
      message: message ?? 'Impossible de se connecter au serveur.\nVérifiez votre connexion internet.',
    );
  }

  factory ApiException.timeout() {
    return ApiException(
      code: 'TIMEOUT',
      message: 'Le serveur met trop de temps à répondre.\nVeuillez réessayer.',
    );
  }

  factory ApiException.serverError([String? message]) {
    return ApiException(
      code: 'SRV_001',
      message: message ?? 'Le serveur a rencontré une erreur.\nVeuillez réessayer plus tard.',
      statusCode: 500,
    );
  }

  factory ApiException.unauthorized() {
    return ApiException(
      code: 'AUTH_001',
      message: 'Votre session a expiré.\nVeuillez vous reconnecter.',
      statusCode: 401,
    );
  }

  factory ApiException.noInternet() {
    return ApiException(
      code: 'NO_INTERNET',
      message: 'Aucune connexion internet détectée.\nVérifiez votre connexion et réessayez.',
    );
  }

  factory ApiException.maintenance() {
    return ApiException(
      code: 'MAINTENANCE',
      message: 'Le serveur est en maintenance.\nVeuillez réessayer dans quelques minutes.',
      statusCode: 503,
    );
  }

  /// Obtenir un message localisé pour les codes d'erreur courants
  static String _getLocalizedMessage(String code, String defaultMessage) {
    switch (code) {
      case 'AUTH_001':
        return 'Identifiants invalides.\nVérifiez votre email et mot de passe.';
      case 'AUTH_002':
        return 'Votre session a expiré.\nVeuillez vous reconnecter.';
      case 'AUTH_003':
        return 'Token invalide ou expiré.\nVeuillez vous reconnecter.';
      case 'AUTH_004':
        return 'Accès non autorisé.\nVous n\'avez pas les permissions nécessaires.';
      case 'AUTH_010':
        return 'Trop de tentatives.\nVeuillez patienter quelques minutes.';
      case 'VAL_001':
        return 'Données invalides.\nVeuillez vérifier les informations saisies.';
      case 'SRV_001':
        return 'Erreur serveur.\nVeuillez réessayer plus tard.';
      case 'DB_001':
        return 'Base de données non disponible.\nVeuillez contacter le support.';
      default:
        return defaultMessage;
    }
  }

  bool get isAuthError => code.startsWith('AUTH_');
  bool get isNetworkError => code == 'NETWORK_ERROR' || code == 'NO_INTERNET';
  bool get isTimeout => code == 'TIMEOUT';
  bool get isMaintenance => code == 'MAINTENANCE';
  bool get isRateLimited => code == 'AUTH_010';

  /// Obtenir une action suggérée basée sur le type d'erreur
  String get suggestedAction {
    if (isAuthError) return 'Se reconnecter';
    if (isNetworkError) return 'Vérifier la connexion';
    if (isTimeout) return 'Réessayer';
    if (isMaintenance) return 'Patienter';
    return 'Réessayer';
  }

  @override
  String toString() => message;
}
