import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';

/// Service de connectivité pour gérer le mode offline/online
class ConnectivityService {
  static final ConnectivityService _instance = ConnectivityService._internal();
  factory ConnectivityService() => _instance;
  ConnectivityService._internal();

  final Connectivity _connectivity = Connectivity();
  final Logger _logger = Logger();

  final StreamController<bool> _connectionStatusController =
      StreamController<bool>.broadcast();

  Stream<bool> get connectionStatusStream => _connectionStatusController.stream;

  bool _isConnected = true;
  bool get isConnected => _isConnected;
  bool get isOffline => !_isConnected;

  StreamSubscription<ConnectivityResult>? _connectivitySubscription;

  /// Initialiser le service de connectivité
  Future<void> init() async {
    // Vérifier l'état initial
    await checkConnection();

    // Écouter les changements de connectivité
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen(
      (ConnectivityResult result) async {
        final wasConnected = _isConnected;
        _isConnected = _hasActiveConnection(result);
        
        if (wasConnected != _isConnected) {
          _connectionStatusController.add(_isConnected);
          
          if (kDebugMode) {
            _logger.i(
              _isConnected ? '🌐 Connexion rétablie' : '📴 Mode hors ligne',
            );
          }
        }
      },
    );
  }

  /// Vérifier la connexion actuelle
  Future<bool> checkConnection() async {
    try {
      final ConnectivityResult result = await _connectivity.checkConnectivity();
      _isConnected = _hasActiveConnection(result);
      _connectionStatusController.add(_isConnected);
      return _isConnected;
    } catch (e) {
      _logger.e('Erreur lors de la vérification de la connexion: $e');
      return false;
    }
  }

  /// Vérifier si une connexion active existe
  bool _hasActiveConnection(ConnectivityResult result) {
    return result == ConnectivityResult.mobile ||
        result == ConnectivityResult.wifi ||
        result == ConnectivityResult.ethernet;
  }

  /// Libérer les ressources
  void dispose() {
    _connectivitySubscription?.cancel();
    _connectionStatusController.close();
  }
}
