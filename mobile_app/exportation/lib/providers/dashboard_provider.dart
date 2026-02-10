import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/models.dart';
import '../data/services/services.dart';

/// État du dashboard
class DashboardState {
  final bool isLoading;
  final bool isRefreshing;
  final DashboardModel? dashboard;
  final String? errorMessage;
  final DateTime? lastUpdate;

  const DashboardState({
    this.isLoading = false,
    this.isRefreshing = false,
    this.dashboard,
    this.errorMessage,
    this.lastUpdate,
  });

  DashboardState copyWith({
    bool? isLoading,
    bool? isRefreshing,
    DashboardModel? dashboard,
    String? errorMessage,
    DateTime? lastUpdate,
  }) {
    return DashboardState(
      isLoading: isLoading ?? this.isLoading,
      isRefreshing: isRefreshing ?? this.isRefreshing,
      dashboard: dashboard ?? this.dashboard,
      errorMessage: errorMessage,
      lastUpdate: lastUpdate ?? this.lastUpdate,
    );
  }

  bool get hasData => dashboard != null;
  bool get hasError => errorMessage != null;
}

/// Notifier pour le dashboard
class DashboardNotifier extends StateNotifier<DashboardState> {
  final ApiService _apiService;

  DashboardNotifier(this._apiService) : super(const DashboardState());

  /// Charger le dashboard
  Future<void> loadDashboard({
    String? dateFrom,
    String? dateTo,
    bool forceRefresh = false,
  }) async {
    if (state.isLoading) return;

    state = state.copyWith(
      isLoading: !state.hasData,
      isRefreshing: state.hasData,
      errorMessage: null,
    );

    try {
      final dashboard = await _apiService.getDashboard(
        dateFrom: dateFrom,
        dateTo: dateTo,
        forceRefresh: forceRefresh,
      );

      state = DashboardState(
        dashboard: dashboard,
        lastUpdate: DateTime.now(),
      );
    } on ApiException catch (e) {
      state = state.copyWith(
        isLoading: false,
        isRefreshing: false,
        errorMessage: e.message,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        isRefreshing: false,
        errorMessage: 'Erreur lors du chargement',
      );
    }
  }

  /// Rafraîchir le dashboard
  Future<void> refresh() async {
    await loadDashboard(forceRefresh: true);
  }

  /// Effacer l'erreur
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }
}

/// Provider pour le dashboard
final dashboardProvider = StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
  return DashboardNotifier(ApiService());
});

/// Provider pour le résumé du dashboard
final dashboardSummaryProvider = Provider<DashboardSummary?>((ref) {
  return ref.watch(dashboardProvider).dashboard?.summary;
});

/// Provider pour les stats par état
final transitOrdersByStateProvider = Provider<TransitOrdersByState?>((ref) {
  return ref.watch(dashboardProvider).dashboard?.transitOrdersByState;
});

/// Provider pour les stats de livraison
final deliveryStatusProvider = Provider<DeliveryStatusStats?>((ref) {
  return ref.watch(dashboardProvider).dashboard?.deliveryStatus;
});

/// Provider pour les top clients
final topCustomersProvider = Provider<List<TopCustomer>>((ref) {
  return ref.watch(dashboardProvider).dashboard?.topCustomers ?? [];
});

// ==================== OTS NON VENDUS ====================

/// État des OTs non vendus
class UnsoldTransitOrdersState {
  final bool isLoading;
  final bool isRefreshing;
  final UnsoldTransitOrdersResponse? data;
  final String? errorMessage;
  final DateTime? lastUpdate;

  const UnsoldTransitOrdersState({
    this.isLoading = false,
    this.isRefreshing = false,
    this.data,
    this.errorMessage,
    this.lastUpdate,
  });

  UnsoldTransitOrdersState copyWith({
    bool? isLoading,
    bool? isRefreshing,
    UnsoldTransitOrdersResponse? data,
    String? errorMessage,
    DateTime? lastUpdate,
  }) {
    return UnsoldTransitOrdersState(
      isLoading: isLoading ?? this.isLoading,
      isRefreshing: isRefreshing ?? this.isRefreshing,
      data: data ?? this.data,
      errorMessage: errorMessage,
      lastUpdate: lastUpdate ?? this.lastUpdate,
    );
  }

  bool get hasData => data != null;
  bool get hasError => errorMessage != null;
}

/// Notifier pour les OTs non vendus
class UnsoldTransitOrdersNotifier extends StateNotifier<UnsoldTransitOrdersState> {
  final ApiService _apiService;

  UnsoldTransitOrdersNotifier(this._apiService) : super(const UnsoldTransitOrdersState());

  /// Charger les OTs non vendus
  Future<void> loadUnsoldTransitOrders({
    String? productType,
    int? customerId,
    int limit = 50,
    bool forceRefresh = false,
  }) async {
    if (state.isLoading) return;

    state = state.copyWith(
      isLoading: !state.hasData,
      isRefreshing: state.hasData,
      errorMessage: null,
    );

    try {
      final data = await _apiService.getUnsoldTransitOrders(
        productType: productType,
        customerId: customerId,
        limit: limit,
        forceRefresh: forceRefresh,
      );

      state = UnsoldTransitOrdersState(
        data: data,
        lastUpdate: DateTime.now(),
      );
    } on ApiException catch (e) {
      state = state.copyWith(
        isLoading: false,
        isRefreshing: false,
        errorMessage: e.message,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        isRefreshing: false,
        errorMessage: 'Erreur lors du chargement des OTs non vendus',
      );
    }
  }

  /// Rafraîchir les OTs non vendus
  Future<void> refresh() async {
    await loadUnsoldTransitOrders(forceRefresh: true);
  }

  /// Effacer l'erreur
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }
}

/// Provider pour les OTs non vendus
final unsoldTransitOrdersProvider = StateNotifierProvider<UnsoldTransitOrdersNotifier, UnsoldTransitOrdersState>((ref) {
  return UnsoldTransitOrdersNotifier(ApiService());
});

/// Provider pour le résumé des OTs non vendus
final unsoldTransitOrdersSummaryProvider = Provider<UnsoldSummary?>((ref) {
  return ref.watch(unsoldTransitOrdersProvider).data?.summary;
});

/// Provider pour la liste des OTs non vendus
final unsoldTransitOrdersListProvider = Provider<List<UnsoldTransitOrder>>((ref) {
  return ref.watch(unsoldTransitOrdersProvider).data?.transitOrders ?? [];
});
