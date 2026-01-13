import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logger/logger.dart';

import '../../core/config/app_config.dart';
import '../models/models.dart';
import 'http_service.dart';

/// Service d'authentification
class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  final HttpService _httpService = HttpService();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final Logger _logger = Logger();

  static const String _tokenKey = 'auth_token';
  static const String _tokenExpiryKey = 'auth_token_expiry';
  static const String _userKey = 'auth_user';

  UserModel? _currentUser;
  String? _authToken;
  DateTime? _tokenExpiry;

  /// Utilisateur courant
  UserModel? get currentUser => _currentUser;

  /// Token d'authentification
  String? get authToken => _authToken;

  /// Vérifier si l'utilisateur est connecté
  bool get isAuthenticated => _authToken != null && !isTokenExpired;

  /// Vérifier si le token est expiré
  bool get isTokenExpired {
    if (_tokenExpiry == null) return true;
    return DateTime.now().isAfter(_tokenExpiry!);
  }

  /// Vérifier si le token expire bientôt (dans 1 jour)
  bool get tokenExpiresSoon {
    if (_tokenExpiry == null) return true;
    final threshold = _tokenExpiry!.subtract(AppConfig.tokenRefreshThreshold);
    return DateTime.now().isAfter(threshold);
  }

  /// Initialiser le service et restaurer la session
  Future<bool> init() async {
    try {
      _authToken = await _secureStorage.read(key: _tokenKey);
      final expiryStr = await _secureStorage.read(key: _tokenExpiryKey);
      final userJson = await _secureStorage.read(key: _userKey);

      if (_authToken != null && expiryStr != null) {
        _tokenExpiry = DateTime.tryParse(expiryStr);
        
        if (userJson != null) {
          final userData = jsonDecode(userJson) as Map<String, dynamic>;
          _currentUser = UserModel.fromJson(userData);
        }

        if (!isTokenExpired) {
          _httpService.setAuthToken(_authToken);
          return true;
        } else {
          // Token expiré, nettoyer
          await logout();
        }
      }
      return false;
    } catch (e) {
      _logger.e('Erreur lors de l\'initialisation de AuthService: $e');
      return false;
    }
  }

  /// Connexion
  Future<AuthResponse> login(String email, String password) async {
    try {
      final response = await _httpService.post(
        AppConfig.loginEndpoint,
        data: {
          'db': AppConfig.database,
          'login': email,
          'password': password,
        },
        useJsonRpc: true,  // Utiliser le format JSON-RPC pour Odoo
      );

      final data = response.data;
      _logger.d('Réponse login brute: $data');
      
      Map<String, dynamic> result;

      // Gérer les différents formats de réponse
      if (data is String) {
        result = jsonDecode(data) as Map<String, dynamic>;
      } else if (data is Map<String, dynamic>) {
        // Si la réponse contient 'result', c'est du JSON-RPC Odoo
        if (data.containsKey('result')) {
          result = data['result'] as Map<String, dynamic>;
        } else {
          result = data;
        }
      } else {
        throw ApiException.serverError('Format de réponse invalide: ${data.runtimeType}');
      }
      
      _logger.d('Résultat parsé: $result');

      if (result['success'] != true) {
        final error = result['error'] as Map<String, dynamic>?;
        throw ApiException(
          code: error?['code'] as String? ?? 'AUTH_005',
          message: error?['message'] as String? ?? 'Identifiants incorrects',
        );
      }

      final authData = result['data'] as Map<String, dynamic>;
      final authResponse = AuthResponse.fromJson(authData);

      // Sauvegarder les données d'authentification
      await _saveAuthData(authResponse);

      return authResponse;
    } catch (e) {
      _logger.e('Erreur de connexion: $e');
      if (e is ApiException) rethrow;
      throw ApiException.serverError(e.toString());
    }
  }

  /// Déconnexion
  Future<void> logout() async {
    try {
      if (_authToken != null) {
        // Appeler l'API de déconnexion
        try {
          await _httpService.postJsonRpc(
            AppConfig.logoutEndpoint,
            params: {},
          );
        } catch (e) {
          // Ignorer les erreurs de déconnexion API
          _logger.w('Erreur lors de la déconnexion API: $e');
        }
      }
    } finally {
      // Nettoyer les données locales dans tous les cas
      await _clearAuthData();
    }
  }

  /// Sauvegarder les données d'authentification
  Future<void> _saveAuthData(AuthResponse authResponse) async {
    _authToken = authResponse.token;
    _tokenExpiry = authResponse.expiresAt;
    _currentUser = authResponse.user;

    _httpService.setAuthToken(_authToken);

    await _secureStorage.write(key: _tokenKey, value: _authToken);
    await _secureStorage.write(
      key: _tokenExpiryKey,
      value: _tokenExpiry?.toIso8601String(),
    );
    await _secureStorage.write(
      key: _userKey,
      value: jsonEncode(_currentUser?.toJson()),
    );
  }

  /// Nettoyer les données d'authentification
  Future<void> _clearAuthData() async {
    _authToken = null;
    _tokenExpiry = null;
    _currentUser = null;

    _httpService.clearAuthToken();

    await _secureStorage.delete(key: _tokenKey);
    await _secureStorage.delete(key: _tokenExpiryKey);
    await _secureStorage.delete(key: _userKey);
  }
}
