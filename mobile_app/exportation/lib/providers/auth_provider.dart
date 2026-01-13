import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/models.dart';
import '../data/services/services.dart';

/// État d'authentification
enum AuthStatus {
  initial,
  loading,
  authenticated,
  unauthenticated,
  error,
}

/// État de l'authentification
class AuthState {
  final AuthStatus status;
  final UserModel? user;
  final String? errorMessage;
  final bool isLoading;

  const AuthState({
    this.status = AuthStatus.initial,
    this.user,
    this.errorMessage,
    this.isLoading = false,
  });

  AuthState copyWith({
    AuthStatus? status,
    UserModel? user,
    String? errorMessage,
    bool? isLoading,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      errorMessage: errorMessage ?? this.errorMessage,
      isLoading: isLoading ?? this.isLoading,
    );
  }

  bool get isAuthenticated => status == AuthStatus.authenticated;
  bool get isUnauthenticated => status == AuthStatus.unauthenticated;
}

/// Provider pour l'état d'authentification
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;
  final HttpService _httpService;

  AuthNotifier(this._authService, this._httpService) : super(const AuthState()) {
    _init();
  }

  /// Initialiser l'authentification
  Future<void> _init() async {
    state = state.copyWith(status: AuthStatus.loading, isLoading: true);
    
    _httpService.init();
    final isAuthenticated = await _authService.init();
    
    if (isAuthenticated) {
      state = AuthState(
        status: AuthStatus.authenticated,
        user: _authService.currentUser,
        isLoading: false,
      );
    } else {
      state = const AuthState(
        status: AuthStatus.unauthenticated,
        isLoading: false,
      );
    }
  }

  /// Connexion
  Future<bool> login(String email, String password) async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final authResponse = await _authService.login(email, password);
      
      state = AuthState(
        status: AuthStatus.authenticated,
        user: authResponse.user,
        isLoading: false,
      );
      
      return true;
    } on ApiException catch (e) {
      state = AuthState(
        status: AuthStatus.error,
        errorMessage: e.message,
        isLoading: false,
      );
      return false;
    } catch (e) {
      state = AuthState(
        status: AuthStatus.error,
        errorMessage: 'Une erreur est survenue',
        isLoading: false,
      );
      return false;
    }
  }

  /// Déconnexion
  Future<void> logout() async {
    state = state.copyWith(isLoading: true);
    
    await _authService.logout();
    
    state = const AuthState(
      status: AuthStatus.unauthenticated,
      isLoading: false,
    );
  }

  /// Effacer l'erreur
  void clearError() {
    state = state.copyWith(errorMessage: null, status: AuthStatus.unauthenticated);
  }
}

/// Provider principal d'authentification
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(AuthService(), HttpService());
});

/// Provider pour vérifier si l'utilisateur est connecté
final isAuthenticatedProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).isAuthenticated;
});

/// Provider pour l'utilisateur courant
final currentUserProvider = Provider<UserModel?>((ref) {
  return ref.watch(authProvider).user;
});
