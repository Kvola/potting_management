import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:percent_indicator/circular_percent_indicator.dart';

import '../../core/theme/app_colors.dart';
import '../../data/models/models.dart';
import '../../providers/providers.dart';
import '../../widgets/widgets.dart';

/// Écran de détail d'un ordre de transit
class TransitOrderDetailScreen extends ConsumerStatefulWidget {
  final int orderId;

  const TransitOrderDetailScreen({
    super.key,
    required this.orderId,
  });

  @override
  ConsumerState<TransitOrderDetailScreen> createState() =>
      _TransitOrderDetailScreenState();
}

class _TransitOrderDetailScreenState
    extends ConsumerState<TransitOrderDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(transitOrderDetailProvider.notifier).loadOrder(widget.orderId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(transitOrderDetailProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(state.order?.name ?? 'Détail OT'),
      ),
      body: _buildBody(state),
    );
  }

  Widget _buildBody(TransitOrderDetailState state) {
    if (state.isLoading) {
      return const Center(child: LoadingIndicator());
    }

    if (state.hasError) {
      return ErrorView(
        message: state.errorMessage!,
        onRetry: () =>
            ref.read(transitOrderDetailProvider.notifier).loadOrder(widget.orderId),
      );
    }

    final order = state.order;
    if (order == null) {
      return const EmptyView(
        icon: Icons.local_shipping_outlined,
        title: 'OT non trouvé',
        message: 'Cet ordre de transit n\'existe pas.',
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // En-tête avec progression
          _buildHeader(order),
          const SizedBox(height: 24),

          // Informations principales
          _buildMainInfo(order),
          const SizedBox(height: 24),

          // Tonnages
          _buildTonnageInfo(order),
          const SizedBox(height: 24),

          // Statut de livraison
          _buildDeliveryStatus(order),

          // Lots
          if (order.lots != null && order.lots!.isNotEmpty) ...[
            const SizedBox(height: 24),
            _buildLots(order.lots!),
          ],

          // Notes
          if (order.note != null && order.note!.isNotEmpty) ...[
            const SizedBox(height: 24),
            _buildNotes(order.note!),
          ],
        ],
      ),
    );
  }

  Widget _buildHeader(TransitOrderModel order) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            CircularPercentIndicator(
              radius: 50,
              lineWidth: 8,
              percent: (order.progressPercentage / 100).clamp(0.0, 1.0),
              center: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '${order.progressPercentage.toStringAsFixed(0)}%',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: _getProgressColor(order.progressPercentage),
                        ),
                  ),
                ],
              ),
              progressColor: _getProgressColor(order.progressPercentage),
              backgroundColor: AppColors.border,
              circularStrokeCap: CircularStrokeCap.round,
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    order.name,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: _getStateColor(order.state).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      order.stateLabel,
                      style: TextStyle(
                        color: _getStateColor(order.state),
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    order.productTypeLabel,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMainInfo(TransitOrderModel order) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Informations',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            _buildInfoRow(Icons.business_rounded, 'Client', order.customer),
            if (order.consignee.isNotEmpty)
              _buildInfoRow(Icons.person_rounded, 'Destinataire', order.consignee),
            if (order.formuleReference != null)
              _buildInfoRow(Icons.receipt_rounded, 'Formule', order.formuleReference!),
            if (order.dateCreated != null)
              _buildInfoRow(
                Icons.calendar_today_rounded,
                'Créé le',
                _formatDate(order.dateCreated!),
              ),
            if (order.dateValidated != null)
              _buildInfoRow(
                Icons.check_circle_rounded,
                'Validé le',
                _formatDate(order.dateValidated!),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppColors.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                Text(
                  value,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTonnageInfo(TransitOrderModel order) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Tonnages',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildTonnageCard(
                    'Objectif',
                    order.tonnageKg,
                    AppColors.primary,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildTonnageCard(
                    'Actuel',
                    order.currentTonnageKg,
                    AppColors.success,
                  ),
                ),
              ],
            ),
            if (order.deliveredTonnage != null) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _buildTonnageCard(
                      'Livré',
                      order.deliveredTonnage! * 1000,
                      AppColors.info,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildTonnageCard(
                      'Restant',
                      (order.remainingToDeliverTonnage ?? 0) * 1000,
                      AppColors.warning,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTonnageCard(String label, double kg, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            _formatTonnage(kg),
            style: TextStyle(
              color: color,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDeliveryStatus(TransitOrderModel order) {
    final status = order.deliveryStatus;
    final color = status == 'fully_delivered'
        ? AppColors.deliveryFull
        : status == 'partial'
            ? AppColors.deliveryPartial
            : AppColors.deliveryNone;
    final label = status == 'fully_delivered'
        ? 'Entièrement livré'
        : status == 'partial'
            ? 'Partiellement livré'
            : 'Non livré';
    final icon = status == 'fully_delivered'
        ? Icons.check_circle_rounded
        : status == 'partial'
            ? Icons.timelapse_rounded
            : Icons.pending_rounded;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: color, size: 28),
            ),
            const SizedBox(width: 16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Statut de livraison',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                Text(
                  label,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: color,
                      ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLots(List<LotModel> lots) {
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
                  'Lots (${lots.length})',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                Icon(
                  Icons.inventory_2_rounded,
                  color: AppColors.primary,
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...lots.map((lot) => _buildLotItem(lot)),
          ],
        ),
      ),
    );
  }

  Widget _buildLotItem(LotModel lot) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                lot.name,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: _getLotStateColor(lot.state).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  lot.stateLabel,
                  style: TextStyle(
                    fontSize: 10,
                    color: _getLotStateColor(lot.state),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Remplissage',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 4),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: (lot.fillPercentage / 100).clamp(0.0, 1.0),
                        minHeight: 6,
                        backgroundColor: AppColors.border,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          _getProgressColor(lot.fillPercentage),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Text(
                '${lot.fillPercentage.toStringAsFixed(0)}%',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: _getProgressColor(lot.fillPercentage),
                ),
              ),
            ],
          ),
          if (lot.container != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.view_in_ar_rounded, size: 14, color: AppColors.textSecondary),
                const SizedBox(width: 4),
                Text(
                  lot.container!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildNotes(String note) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.notes_rounded, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(
                  'Notes',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(note),
          ],
        ),
      ),
    );
  }

  Color _getProgressColor(double progress) {
    if (progress >= 80) return AppColors.success;
    if (progress >= 50) return AppColors.warning;
    return AppColors.error;
  }

  Color _getStateColor(String state) {
    switch (state) {
      case 'done':
        return AppColors.stateDone;
      case 'in_progress':
      case 'lots_generated':
        return AppColors.stateInProgress;
      case 'ready_validation':
        return AppColors.stateReady;
      case 'cancelled':
        return AppColors.stateCancelled;
      default:
        return AppColors.stateDraft;
    }
  }

  Color _getLotStateColor(String state) {
    switch (state) {
      case 'ready':
        return AppColors.success;
      case 'in_progress':
        return AppColors.stateInProgress;
      case 'done':
        return AppColors.stateDone;
      default:
        return AppColors.stateDraft;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}/${date.year}';
  }

  String _formatTonnage(double kg) {
    if (kg >= 1000) {
      return '${(kg / 1000).toStringAsFixed(2)} T';
    }
    return '${kg.toStringAsFixed(0)} Kg';
  }
}
