import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/services/services.dart';

/// État de connectivité
class ConnectivityState {
  final bool isConnected;
  final bool isChecking;
  final DateTime? lastCheck;

  const ConnectivityState({
    this.isConnected = true,
    this.isChecking = false,
    this.lastCheck,
  });

  ConnectivityState copyWith({
    bool? isConnected,
    bool? isChecking,
    DateTime? lastCheck,
  }) {
    return ConnectivityState(
      isConnected: isConnected ?? this.isConnected,
      isChecking: isChecking ?? this.isChecking,
      lastCheck: lastCheck ?? this.lastCheck,
    );
  }

  bool get isOffline => !isConnected;
}

/// Notifier pour la connectivité
class ConnectivityNotifier extends StateNotifier<ConnectivityState> {
  final ConnectivityService _connectivityService;
  StreamSubscription<bool>? _subscription;

  ConnectivityNotifier(this._connectivityService) : super(const ConnectivityState()) {
    _init();
  }

  Future<void> _init() async {
    await _connectivityService.init();
    
    // État initial
    state = ConnectivityState(
      isConnected: _connectivityService.isConnected,
      lastCheck: DateTime.now(),
    );

    // Écouter les changements
    _subscription = _connectivityService.connectionStatusStream.listen((isConnected) {
      state = state.copyWith(
        isConnected: isConnected,
        lastCheck: DateTime.now(),
      );
    });
  }

  /// Vérifier la connexion manuellement
  Future<void> checkConnection() async {
    state = state.copyWith(isChecking: true);
    
    final isConnected = await _connectivityService.checkConnection();
    
    state = state.copyWith(
      isConnected: isConnected,
      isChecking: false,
      lastCheck: DateTime.now(),
    );
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _connectivityService.dispose();
    super.dispose();
  }
}

/// Provider pour la connectivité
final connectivityProvider = StateNotifierProvider<ConnectivityNotifier, ConnectivityState>((ref) {
  return ConnectivityNotifier(ConnectivityService());
});

/// Provider pour savoir si l'appareil est connecté
final isConnectedProvider = Provider<bool>((ref) {
  return ref.watch(connectivityProvider).isConnected;
});

/// Provider pour savoir si l'appareil est hors ligne
final isOfflineProvider = Provider<bool>((ref) {
  return ref.watch(connectivityProvider).isOffline;
});
