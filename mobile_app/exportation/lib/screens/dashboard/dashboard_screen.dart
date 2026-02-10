import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';

import '../../core/theme/app_colors.dart';
import '../../data/models/models.dart';
import '../../providers/providers.dart';
import '../../widgets/widgets.dart';

/// Écran du tableau de bord
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    // Charger les OTs non vendus au démarrage
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(unsoldTransitOrdersProvider.notifier).loadUnsoldTransitOrders();
    });
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final unsoldState = ref.watch(unsoldTransitOrdersProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tableau de bord'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () {
              ref.read(dashboardProvider.notifier).refresh();
              ref.read(unsoldTransitOrdersProvider.notifier).refresh();
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await Future.wait([
            ref.read(dashboardProvider.notifier).refresh(),
            ref.read(unsoldTransitOrdersProvider.notifier).refresh(),
          ]);
        },
        child: _buildBody(context, dashboardState, unsoldState),
      ),
    );
  }

  Widget _buildBody(BuildContext context, DashboardState state, UnsoldTransitOrdersState unsoldState) {
    if (state.isLoading && !state.hasData) {
      return const Center(child: LoadingIndicator());
    }

    if (state.hasError && !state.hasData) {
      return ErrorView(
        message: state.errorMessage!,
        onRetry: () => ref.read(dashboardProvider.notifier).loadDashboard(),
      );
    }

    final dashboard = state.dashboard;
    if (dashboard == null) {
      return const EmptyView(
        icon: Icons.dashboard_outlined,
        title: 'Aucune donnée',
        message: 'Les données du tableau de bord ne sont pas disponibles.',
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // En-tête de bienvenue
        _buildWelcomeHeader(context, ref),
        const SizedBox(height: 24),

        // Cartes de statistiques principales
        _buildMainStats(context, dashboard.summary),
        const SizedBox(height: 24),

        // Progression moyenne
        _buildProgressCard(context, dashboard.summary),
        const SizedBox(height: 24),

        // États des OT
        _buildStatesPieChart(context, dashboard.transitOrdersByState),
        const SizedBox(height: 24),

        // Statut de livraison
        _buildDeliveryStatusChart(context, dashboard.deliveryStatus),
        const SizedBox(height: 24),

        // Par type de produit
        if (dashboard.byProductType.isNotEmpty) ...[
          _buildProductTypeStats(context, dashboard.byProductType),
          const SizedBox(height: 24),
        ],

        // Top clients
        if (dashboard.topCustomers.isNotEmpty) ...[
          _buildTopCustomers(context, dashboard.topCustomers),
          const SizedBox(height: 24),
        ],

        // OTs Non Vendus (Vue PDG)
        _buildUnsoldTransitOrders(context, unsoldState),
        const SizedBox(height: 24),

        // Dernière mise à jour
        if (state.lastUpdate != null)
          _buildLastUpdate(context, state.lastUpdate!),
      ],
    );
  }

  Widget _buildWelcomeHeader(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final now = DateTime.now();
    final greeting = now.hour < 12
        ? 'Bonjour'
        : now.hour < 18
            ? 'Bon après-midi'
            : 'Bonsoir';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '$greeting,',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: AppColors.textSecondary,
              ),
        ),
        Text(
          user?.name ?? 'PDG',
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
      ],
    );
  }

  Widget _buildMainStats(BuildContext context, DashboardSummary summary) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: StatCard(
                title: 'Ordres de Transit',
                value: '${summary.totalTransitOrders}',
                icon: Icons.local_shipping_rounded,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: StatCard(
                title: 'Commandes',
                value: '${summary.totalCustomerOrders}',
                icon: Icons.shopping_bag_rounded,
                color: AppColors.secondary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: StatCard(
                title: 'Tonnage Total',
                value: _formatTonnage(summary.totalTonnageKg),
                subtitle: '${summary.totalTonnage.toStringAsFixed(1)} T',
                icon: Icons.scale_rounded,
                color: AppColors.chartMass,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: StatCard(
                title: 'Tonnage Actuel',
                value: _formatTonnage(summary.currentTonnageKg),
                subtitle: '${summary.currentTonnage.toStringAsFixed(1)} T',
                icon: Icons.trending_up_rounded,
                color: AppColors.success,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildProgressCard(BuildContext context, DashboardSummary summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Progression Moyenne',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: _getProgressColor(summary.averageProgress).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${summary.averageProgress.toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: _getProgressColor(summary.averageProgress),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: summary.averageProgress / 100,
                minHeight: 12,
                backgroundColor: AppColors.border,
                valueColor: AlwaysStoppedAnimation<Color>(
                  _getProgressColor(summary.averageProgress),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatesPieChart(BuildContext context, TransitOrdersByState states) {
    final total = states.total;
    if (total == 0) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'États des Ordres de Transit',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              height: 200,
              child: Row(
                children: [
                  Expanded(
                    child: PieChart(
                      PieChartData(
                        sections: [
                          PieChartSectionData(
                            value: states.done.toDouble(),
                            title: '${states.done}',
                            color: AppColors.stateDone,
                            radius: 60,
                            titleStyle: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          PieChartSectionData(
                            value: states.inProgress.toDouble(),
                            title: '${states.inProgress}',
                            color: AppColors.stateInProgress,
                            radius: 60,
                            titleStyle: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          PieChartSectionData(
                            value: states.readyValidation.toDouble(),
                            title: '${states.readyValidation}',
                            color: AppColors.stateReady,
                            radius: 60,
                            titleStyle: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                        centerSpaceRadius: 40,
                        sectionsSpace: 2,
                      ),
                    ),
                  ),
                  const SizedBox(width: 20),
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildLegendItem('Validés', states.done, AppColors.stateDone),
                      const SizedBox(height: 8),
                      _buildLegendItem('En cours', states.inProgress, AppColors.stateInProgress),
                      const SizedBox(height: 8),
                      _buildLegendItem('Prêts', states.readyValidation, AppColors.stateReady),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeliveryStatusChart(BuildContext context, DeliveryStatusStats delivery) {
    final total = delivery.total;
    if (total == 0) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Statut de Livraison',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 20),
            _buildDeliveryBar(context, 'Livrés', delivery.fullyDelivered, total, AppColors.deliveryFull),
            const SizedBox(height: 12),
            _buildDeliveryBar(context, 'Partiels', delivery.partial, total, AppColors.deliveryPartial),
            const SizedBox(height: 12),
            _buildDeliveryBar(context, 'Non livrés', delivery.notDelivered, total, AppColors.deliveryNone),
          ],
        ),
      ),
    );
  }

  Widget _buildDeliveryBar(BuildContext context, String label, int value, int total, Color color) {
    final percentage = total > 0 ? (value / total) * 100 : 0.0;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
            Text(
              '$value (${percentage.toStringAsFixed(0)}%)',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: percentage / 100,
            minHeight: 8,
            backgroundColor: color.withOpacity(0.2),
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
      ],
    );
  }

  Widget _buildProductTypeStats(BuildContext context, Map<String, ProductTypeStats> stats) {
    final labels = {
      'cocoa_mass': 'Masse',
      'cocoa_butter': 'Beurre',
      'cocoa_cake': 'Tourteau',
      'cocoa_powder': 'Poudre',
    };

    final colors = {
      'cocoa_mass': AppColors.chartMass,
      'cocoa_butter': AppColors.chartButter,
      'cocoa_cake': AppColors.chartCake,
      'cocoa_powder': AppColors.chartPowder,
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Par Type de Produit',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            ...stats.entries.map((entry) {
              final label = labels[entry.key] ?? entry.key;
              final color = colors[entry.key] ?? AppColors.primary;
              final stat = entry.value;

              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(
                        color: color,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 2,
                      child: Text(label),
                    ),
                    Expanded(
                      child: Text(
                        '${stat.count} OT',
                        style: const TextStyle(fontWeight: FontWeight.w500),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        '${stat.tonnage.toStringAsFixed(1)} T',
                        style: const TextStyle(fontWeight: FontWeight.w500),
                        textAlign: TextAlign.right,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildTopCustomers(BuildContext context, List<TopCustomer> customers) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Top Clients',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const Icon(Icons.people_rounded, color: AppColors.primary),
              ],
            ),
            const SizedBox(height: 16),
            ...customers.asMap().entries.map((entry) {
              final index = entry.key;
              final customer = entry.value;
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: index == 0
                            ? AppColors.secondary
                            : index == 1
                                ? AppColors.primaryLight
                                : AppColors.border,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Center(
                        child: Text(
                          '${index + 1}',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: index < 2 ? Colors.white : AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        customer.name,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Text(
                      '${customer.tonnage.toStringAsFixed(1)} T',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildUnsoldTransitOrders(BuildContext context, UnsoldTransitOrdersState state) {
    if (state.isLoading && !state.hasData) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              Text(
                'OTs Non Vendus',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 16),
              const CircularProgressIndicator(),
            ],
          ),
        ),
      );
    }

    final data = state.data;
    if (data == null || data.transitOrders.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'OTs Non Vendus',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                  const Icon(Icons.inventory_2_outlined, color: AppColors.success),
                ],
              ),
              const SizedBox(height: 16),
              const Center(
                child: Text(
                  'Tous les OTs ont été vendus',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final summary = data.summary;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // En-tête avec résumé
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'OTs Non Vendus',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.warning.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${summary.totalCount} OT${summary.totalCount > 1 ? 's' : ''}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: AppColors.warning,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            
            // Résumé tonnage
            Row(
              children: [
                const Icon(Icons.scale_rounded, size: 16, color: AppColors.textSecondary),
                const SizedBox(width: 6),
                Text(
                  '${summary.currentTonnage.toStringAsFixed(1)} / ${summary.totalTonnage.toStringAsFixed(1)} T',
                  style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                ),
                const Spacer(),
                if (summary.totalValue > 0) ...[
                  const Icon(Icons.euro_rounded, size: 16, color: AppColors.textSecondary),
                  const SizedBox(width: 4),
                  Text(
                    _formatCurrency(summary.totalValue),
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                ],
              ],
            ),
            
            const SizedBox(height: 16),
            const Divider(height: 1),
            const SizedBox(height: 12),
            
            // Liste des OTs avec leurs lots
            ...data.transitOrders.take(5).map((ot) => _buildUnsoldOTItem(context, ot)),
            
            // Voir plus si plus de 5
            if (data.transitOrders.length > 5) ...[
              const SizedBox(height: 8),
              Center(
                child: Text(
                  '+ ${data.transitOrders.length - 5} autres OTs',
                  style: const TextStyle(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildUnsoldOTItem(BuildContext context, UnsoldTransitOrder ot) {
    Color stateColor;
    switch (ot.state) {
      case 'ready_validation':
        stateColor = AppColors.success;
        break;
      case 'in_progress':
        stateColor = AppColors.primary;
        break;
      case 'lots_generated':
        stateColor = AppColors.secondary;
        break;
      default:
        stateColor = AppColors.textSecondary;
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Ligne principale OT
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: stateColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  ot.stateLabel,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    color: stateColor,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  ot.name,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${ot.progressPercentage.toStringAsFixed(0)}%',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: _getProgressColor(ot.progressPercentage),
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          
          // Info client et tonnage
          Row(
            children: [
              const Icon(Icons.business_rounded, size: 14, color: AppColors.textHint),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  ot.customer,
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${ot.currentTonnage.toStringAsFixed(1)} / ${ot.tonnage.toStringAsFixed(1)} T',
                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
            ],
          ),
          
          // Barre de progression
          const SizedBox(height: 6),
          LinearProgressIndicator(
            value: ot.progressPercentage / 100,
            backgroundColor: AppColors.border,
            valueColor: AlwaysStoppedAnimation(_getProgressColor(ot.progressPercentage)),
          ),
          
          // Lots (s'il y en a)
          if (ot.lots.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: ot.lots.take(4).map((lot) => _buildLotChip(lot)).toList(),
            ),
            if (ot.lots.length > 4)
              Padding(
                padding: const EdgeInsets.only(left: 4, top: 4),
                child: Text(
                  '+${ot.lots.length - 4} lots',
                  style: const TextStyle(fontSize: 11, color: AppColors.textHint),
                ),
              ),
          ],
          
          const SizedBox(height: 8),
          const Divider(height: 1),
        ],
      ),
    );
  }

  Widget _buildLotChip(UnsoldLot lot) {
    final color = lot.isFull ? AppColors.success : AppColors.textSecondary;
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            lot.isFull ? Icons.check_circle : Icons.pending,
            size: 12,
            color: color,
          ),
          const SizedBox(width: 4),
          Text(
            lot.name,
            style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500),
          ),
          const SizedBox(width: 4),
          Text(
            '${lot.progress.toStringAsFixed(0)}%',
            style: TextStyle(fontSize: 10, color: color),
          ),
        ],
      ),
    );
  }

  String _formatCurrency(double amount) {
    if (amount >= 1000000) {
      return '${(amount / 1000000).toStringAsFixed(1)}M';
    }
    if (amount >= 1000) {
      return '${(amount / 1000).toStringAsFixed(0)}K';
    }
    return amount.toStringAsFixed(0);
  }

  Widget _buildLastUpdate(BuildContext context, DateTime lastUpdate) {
    return Center(
      child: Text(
        'Dernière mise à jour: ${_formatDateTime(lastUpdate)}',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: AppColors.textHint,
            ),
      ),
    );
  }

  Widget _buildLegendItem(String label, int value, Color color) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 8),
        Text('$label ($value)'),
      ],
    );
  }

  Color _getProgressColor(double progress) {
    if (progress >= 80) return AppColors.success;
    if (progress >= 50) return AppColors.warning;
    return AppColors.error;
  }

  String _formatTonnage(double kg) {
    if (kg >= 1000000) {
      return '${(kg / 1000000).toStringAsFixed(1)}M Kg';
    }
    if (kg >= 1000) {
      return '${(kg / 1000).toStringAsFixed(0)}K Kg';
    }
    return '${kg.toStringAsFixed(0)} Kg';
  }

  String _formatDateTime(DateTime dt) {
    return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
