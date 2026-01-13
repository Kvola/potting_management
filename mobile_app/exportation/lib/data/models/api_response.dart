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
      message: error.message,
      statusCode: statusCode,
    );
  }

  factory ApiException.networkError([String? message]) {
    return ApiException(
      code: 'NETWORK_ERROR',
      message: message ?? 'Erreur de connexion réseau',
    );
  }

  factory ApiException.timeout() {
    return ApiException(
      code: 'TIMEOUT',
      message: 'La requête a expiré, veuillez réessayer',
    );
  }

  factory ApiException.serverError([String? message]) {
    return ApiException(
      code: 'SRV_001',
      message: message ?? 'Erreur serveur, veuillez réessayer',
      statusCode: 500,
    );
  }

  factory ApiException.unauthorized() {
    return ApiException(
      code: 'AUTH_001',
      message: 'Session expirée, veuillez vous reconnecter',
      statusCode: 401,
    );
  }

  bool get isAuthError => code.startsWith('AUTH_');
  bool get isNetworkError => code == 'NETWORK_ERROR';
  bool get isTimeout => code == 'TIMEOUT';

  @override
  String toString() => message;
}
