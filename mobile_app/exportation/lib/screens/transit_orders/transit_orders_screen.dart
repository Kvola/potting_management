import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../data/models/models.dart';
import '../../providers/providers.dart';
import '../../widgets/widgets.dart';
import 'transit_order_detail_screen.dart';

/// Écran de liste des ordres de transit
class TransitOrdersScreen extends ConsumerStatefulWidget {
  const TransitOrdersScreen({super.key});

  @override
  ConsumerState<TransitOrdersScreen> createState() => _TransitOrdersScreenState();
}

class _TransitOrdersScreenState extends ConsumerState<TransitOrdersScreen> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(transitOrdersProvider.notifier).loadOrders();
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(transitOrdersProvider.notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(transitOrdersProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Ordres de Transit'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list_rounded),
            onPressed: () => _showFilterSheet(context),
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => ref.read(transitOrdersProvider.notifier).refresh(),
          ),
        ],
      ),
      body: Column(
        children: [
          // Barre de filtre active
          if (state.filter.hasFilters) _buildActiveFilters(state.filter),

          // Liste
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => ref.read(transitOrdersProvider.notifier).refresh(),
              child: _buildBody(state),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActiveFilters(TransitOrderFilter filter) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: AppColors.primaryLight.withOpacity(0.1),
      child: Row(
        children: [
          const Icon(Icons.filter_alt, size: 16, color: AppColors.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _getFilterText(filter),
              style: const TextStyle(fontSize: 12),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          TextButton(
            onPressed: () => ref.read(transitOrdersProvider.notifier).clearFilters(),
            child: const Text('Effacer'),
          ),
        ],
      ),
    );
  }

  String _getFilterText(TransitOrderFilter filter) {
    final parts = <String>[];
    if (filter.state != null) parts.add('État: ${filter.state}');
    if (filter.productType != null) parts.add('Produit: ${filter.productType}');
    return parts.join(' • ');
  }

  Widget _buildBody(TransitOrdersState state) {
    if (state.isLoading && !state.hasData) {
      return const Center(child: LoadingIndicator());
    }

    if (state.hasError && !state.hasData) {
      return ErrorView(
        message: state.errorMessage!,
        onRetry: () => ref.read(transitOrdersProvider.notifier).loadOrders(),
      );
    }

    if (state.orders.isEmpty) {
      return const EmptyView(
        icon: Icons.local_shipping_outlined,
        title: 'Aucun ordre de transit',
        message: 'Aucun ordre de transit ne correspond aux critères.',
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16),
      itemCount: state.orders.length + (state.isLoadingMore ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == state.orders.length) {
          return const Padding(
            padding: EdgeInsets.all(16),
            child: Center(child: CircularProgressIndicator()),
          );
        }

        final order = state.orders[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: TransitOrderCard(
            order: order,
            onTap: () => _openDetail(order),
          ),
        );
      },
    );
  }

  void _openDetail(TransitOrderModel order) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => TransitOrderDetailScreen(orderId: order.id),
      ),
    );
  }

  void _showFilterSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => const _FilterBottomSheet(),
    );
  }
}

class _FilterBottomSheet extends ConsumerStatefulWidget {
  const _FilterBottomSheet();

  @override
  ConsumerState<_FilterBottomSheet> createState() => _FilterBottomSheetState();
}

class _FilterBottomSheetState extends ConsumerState<_FilterBottomSheet> {
  String? _selectedState;
  String? _selectedProductType;

  final _states = [
    {'value': null, 'label': 'Tous les états'},
    {'value': 'draft', 'label': 'Brouillon'},
    {'value': 'in_progress', 'label': 'En cours'},
    {'value': 'lots_generated', 'label': 'Lots générés'},
    {'value': 'ready_validation', 'label': 'Prêt validation'},
    {'value': 'done', 'label': 'Validé'},
  ];

  final _productTypes = [
    {'value': null, 'label': 'Tous les produits'},
    {'value': 'cocoa_mass', 'label': 'Masse de cacao'},
    {'value': 'cocoa_butter', 'label': 'Beurre de cacao'},
    {'value': 'cocoa_cake', 'label': 'Tourteau de cacao'},
    {'value': 'cocoa_powder', 'label': 'Poudre de cacao'},
  ];

  @override
  void initState() {
    super.initState();
    final filter = ref.read(transitOrdersProvider).filter;
    _selectedState = filter.state;
    _selectedProductType = filter.productType;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Filtrer les OT',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Filtre par état
          Text(
            'État',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _states.map((state) {
              final isSelected = _selectedState == state['value'];
              return FilterChip(
                label: Text(state['label'] as String),
                selected: isSelected,
                onSelected: (_) {
                  setState(() {
                    _selectedState = state['value'] as String?;
                  });
                },
                selectedColor: AppColors.primaryLight.withOpacity(0.3),
                checkmarkColor: AppColors.primary,
              );
            }).toList(),
          ),

          const SizedBox(height: 24),

          // Filtre par type de produit
          Text(
            'Type de produit',
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _productTypes.map((type) {
              final isSelected = _selectedProductType == type['value'];
              return FilterChip(
                label: Text(type['label'] as String),
                selected: isSelected,
                onSelected: (_) {
                  setState(() {
                    _selectedProductType = type['value'] as String?;
                  });
                },
                selectedColor: AppColors.primaryLight.withOpacity(0.3),
                checkmarkColor: AppColors.primary,
              );
            }).toList(),
          ),

          const SizedBox(height: 32),

          // Boutons
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    ref.read(transitOrdersProvider.notifier).clearFilters();
                    Navigator.pop(context);
                  },
                  child: const Text('Réinitialiser'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton(
                  onPressed: () {
                    ref.read(transitOrdersProvider.notifier).applyFilter(
                          TransitOrderFilter(
                            state: _selectedState,
                            productType: _selectedProductType,
                          ),
                        );
                    Navigator.pop(context);
                  },
                  child: const Text('Appliquer'),
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
