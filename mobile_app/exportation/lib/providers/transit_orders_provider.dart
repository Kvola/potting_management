import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/models.dart';
import '../data/services/services.dart';

/// Provider pour ApiService
final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

/// Paramètres de filtre pour les ordres de transit
class TransitOrderFilter {
  final String? state;
  final String? productType;
  final String? dateFrom;
  final String? dateTo;
  final int? customerId;

  const TransitOrderFilter({
    this.state,
    this.productType,
    this.dateFrom,
    this.dateTo,
    this.customerId,
  });

  TransitOrderFilter copyWith({
    String? state,
    String? productType,
    String? dateFrom,
    String? dateTo,
    int? customerId,
  }) {
    return TransitOrderFilter(
      state: state ?? this.state,
      productType: productType ?? this.productType,
      dateFrom: dateFrom ?? this.dateFrom,
      dateTo: dateTo ?? this.dateTo,
      customerId: customerId ?? this.customerId,
    );
  }

  bool get hasFilters =>
      state != null ||
      productType != null ||
      dateFrom != null ||
      dateTo != null ||
      customerId != null;

  TransitOrderFilter clear() => const TransitOrderFilter();
}

/// État des ordres de transit
class TransitOrdersState {
  final bool isLoading;
  final bool isLoadingMore;
  final bool isRefreshing;
  final List<TransitOrderModel> orders;
  final int total;
  final int currentPage;
  final int totalPages;
  final TransitOrderFilter filter;
  final String? errorMessage;

  const TransitOrdersState({
    this.isLoading = false,
    this.isLoadingMore = false,
    this.isRefreshing = false,
    this.orders = const [],
    this.total = 0,
    this.currentPage = 1,
    this.totalPages = 1,
    this.filter = const TransitOrderFilter(),
    this.errorMessage,
  });

  TransitOrdersState copyWith({
    bool? isLoading,
    bool? isLoadingMore,
    bool? isRefreshing,
    List<TransitOrderModel>? orders,
    int? total,
    int? currentPage,
    int? totalPages,
    TransitOrderFilter? filter,
    String? errorMessage,
  }) {
    return TransitOrdersState(
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      isRefreshing: isRefreshing ?? this.isRefreshing,
      orders: orders ?? this.orders,
      total: total ?? this.total,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      filter: filter ?? this.filter,
      errorMessage: errorMessage,
    );
  }

  bool get hasData => orders.isNotEmpty;
  bool get hasMore => currentPage < totalPages;
  bool get hasError => errorMessage != null;
}

/// Notifier pour les ordres de transit
class TransitOrdersNotifier extends StateNotifier<TransitOrdersState> {
  final ApiService _apiService;

  TransitOrdersNotifier(this._apiService) : super(const TransitOrdersState());

  /// Charger les ordres de transit
  Future<void> loadOrders({bool forceRefresh = false}) async {
    if (state.isLoading) return;

    state = state.copyWith(
      isLoading: !state.hasData,
      isRefreshing: state.hasData,
      errorMessage: null,
    );

    try {
      final response = await _apiService.getTransitOrders(
        page: 1,
        state: state.filter.state,
        productType: state.filter.productType,
        dateFrom: state.filter.dateFrom,
        dateTo: state.filter.dateTo,
        customerId: state.filter.customerId,
        forceRefresh: forceRefresh,
      );

      state = TransitOrdersState(
        orders: response.items,
        total: response.total,
        currentPage: response.page,
        totalPages: response.pages,
        filter: state.filter,
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

  /// Charger plus d'ordres (pagination)
  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;

    state = state.copyWith(isLoadingMore: true);

    try {
      final response = await _apiService.getTransitOrders(
        page: state.currentPage + 1,
        state: state.filter.state,
        productType: state.filter.productType,
        dateFrom: state.filter.dateFrom,
        dateTo: state.filter.dateTo,
        customerId: state.filter.customerId,
      );

      state = state.copyWith(
        isLoadingMore: false,
        orders: [...state.orders, ...response.items],
        currentPage: response.page,
        totalPages: response.pages,
      );
    } catch (e) {
      state = state.copyWith(isLoadingMore: false);
    }
  }

  /// Appliquer un filtre
  Future<void> applyFilter(TransitOrderFilter filter) async {
    state = state.copyWith(filter: filter);
    await loadOrders(forceRefresh: true);
  }

  /// Filtrer par état
  Future<void> filterByState(String? filterState) async {
    await applyFilter(state.filter.copyWith(state: filterState));
  }

  /// Filtrer par type de produit
  Future<void> filterByProductType(String? productType) async {
    await applyFilter(state.filter.copyWith(productType: productType));
  }

  /// Effacer les filtres
  Future<void> clearFilters() async {
    await applyFilter(const TransitOrderFilter());
  }

  /// Rafraîchir
  Future<void> refresh() async {
    await loadOrders(forceRefresh: true);
  }
}

/// Provider pour les ordres de transit
final transitOrdersProvider =
    StateNotifierProvider<TransitOrdersNotifier, TransitOrdersState>((ref) {
  return TransitOrdersNotifier(ApiService());
});

/// État du détail d'un ordre de transit
class TransitOrderDetailState {
  final bool isLoading;
  final TransitOrderModel? order;
  final String? errorMessage;

  const TransitOrderDetailState({
    this.isLoading = false,
    this.order,
    this.errorMessage,
  });

  TransitOrderDetailState copyWith({
    bool? isLoading,
    TransitOrderModel? order,
    String? errorMessage,
  }) {
    return TransitOrderDetailState(
      isLoading: isLoading ?? this.isLoading,
      order: order ?? this.order,
      errorMessage: errorMessage,
    );
  }

  bool get hasData => order != null;
  bool get hasError => errorMessage != null;
}

/// Notifier pour le détail d'un ordre de transit
class TransitOrderDetailNotifier extends StateNotifier<TransitOrderDetailState> {
  final ApiService _apiService;

  TransitOrderDetailNotifier(this._apiService) : super(const TransitOrderDetailState());

  /// Charger les détails d'un ordre
  Future<void> loadOrder(int id) async {
    state = const TransitOrderDetailState(isLoading: true);

    try {
      final order = await _apiService.getTransitOrderDetail(id);
      state = TransitOrderDetailState(order: order);
    } on ApiException catch (e) {
      state = TransitOrderDetailState(errorMessage: e.message);
    } catch (e) {
      state = const TransitOrderDetailState(errorMessage: 'Erreur lors du chargement');
    }
  }

  /// Effacer
  void clear() {
    state = const TransitOrderDetailState();
  }
}

/// Provider pour le détail d'un ordre de transit
final transitOrderDetailProvider =
    StateNotifierProvider<TransitOrderDetailNotifier, TransitOrderDetailState>((ref) {
  return TransitOrderDetailNotifier(ApiService());
});
