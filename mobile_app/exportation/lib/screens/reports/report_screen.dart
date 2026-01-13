import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:open_file/open_file.dart';
import 'package:share_plus/share_plus.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_colors.dart';
import '../../data/models/models.dart';
import '../../providers/providers.dart';
import '../../widgets/widgets.dart';

/// Écran des rapports
class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key});

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  DateTime _selectedDate = DateTime.now();
  bool _excludeFullyDelivered = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadSummary();
    });
  }

  void _loadSummary() {
    final dateStr = DateFormat('yyyy-MM-dd').format(_selectedDate);
    ref.read(reportProvider.notifier).loadSummary(
          date: dateStr,
          excludeFullyDelivered: _excludeFullyDelivered,
        );
  }

  @override
  Widget build(BuildContext context) {
    final reportState = ref.watch(reportProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Rapport Quotidien'),
        actions: [
          IconButton(
            icon: const Icon(Icons.calendar_today_rounded),
            onPressed: () => _selectDate(context),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _loadSummary(),
        child: _buildBody(context, reportState),
      ),
      floatingActionButton: reportState.hasSummary
          ? FloatingActionButton.extended(
              onPressed: reportState.isDownloading ? null : _downloadReport,
              backgroundColor: AppColors.primary,
              icon: reportState.isDownloading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.download_rounded),
              label: Text(
                reportState.isDownloading ? 'Téléchargement...' : 'Télécharger PDF',
              ),
            )
          : null,
    );
  }

  Widget _buildBody(BuildContext context, ReportState state) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Sélection de date
        _buildDateSelector(),
        const SizedBox(height: 16),

        // Options
        _buildOptions(),
        const SizedBox(height: 24),

        // Contenu du rapport
        if (state.isLoading && !state.hasSummary)
          const Center(child: LoadingIndicator())
        else if (state.hasError && !state.hasSummary)
          ErrorView(
            message: state.errorMessage!,
            onRetry: _loadSummary,
          )
        else if (state.summary != null)
          _buildReportContent(context, state.summary!)
        else
          const EmptyView(
            icon: Icons.description_outlined,
            title: 'Aucun rapport',
            message: 'Sélectionnez une date pour voir le rapport.',
          ),

        // Fichier téléchargé
        if (state.hasDownloadedFile) ...[
          const SizedBox(height: 24),
          _buildDownloadedFile(state.downloadedFile!),
        ],
      ],
    );
  }

  Widget _buildDateSelector() {
    return Card(
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.calendar_month_rounded, color: AppColors.primary),
        ),
        title: const Text('Date du rapport'),
        subtitle: Text(
          DateFormat('EEEE d MMMM yyyy', 'fr_FR').format(_selectedDate),
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        trailing: const Icon(Icons.chevron_right_rounded),
        onTap: () => _selectDate(context),
      ),
    );
  }

  Widget _buildOptions() {
    return Card(
      child: SwitchListTile(
        title: const Text('Exclure les OT livrés'),
        subtitle: const Text('Masquer les OT entièrement livrés'),
        value: _excludeFullyDelivered,
        onChanged: (value) {
          setState(() {
            _excludeFullyDelivered = value;
          });
          _loadSummary();
        },
        activeColor: AppColors.primary,
      ),
    );
  }

  Widget _buildReportContent(BuildContext context, ReportSummaryModel summary) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // En-tête
        _buildReportHeader(summary),
        const SizedBox(height: 16),

        // Statistiques OT
        _buildOTStats(summary),
        const SizedBox(height: 16),

        // Tonnages
        _buildTonnageStats(summary),
        const SizedBox(height: 16),

        // État de production
        _buildProductionStats(summary),
        const SizedBox(height: 16),

        // Livraison
        _buildDeliveryStats(summary),
        const SizedBox(height: 16),

        // Par client
        if (summary.byCustomer.isNotEmpty) _buildCustomerStats(summary),
      ],
    );
  }

  Widget _buildReportHeader(ReportSummaryModel summary) {
    return Card(
      color: AppColors.primary,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.description_rounded, color: Colors.white),
                const SizedBox(width: 12),
                Text(
                  'Rapport du ${DateFormat('dd/MM/yyyy').format(summary.reportDate)}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                _buildHeaderStat('OT', '${summary.otCount}'),
                const SizedBox(width: 24),
                if (summary.otRange != null)
                  _buildHeaderStat('Plage', summary.otRange!.formatted),
                const SizedBox(width: 24),
                _buildHeaderStat('Progression', '${summary.averageProgress.toStringAsFixed(1)}%'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeaderStat(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: 12,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildOTStats(ReportSummaryModel summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Ordres de Transit',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    'Total OT',
                    '${summary.otCount}',
                    Icons.local_shipping_rounded,
                    AppColors.primary,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    'Progression',
                    '${summary.averageProgress.toStringAsFixed(1)}%',
                    Icons.trending_up_rounded,
                    _getProgressColor(summary.averageProgress),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTonnageStats(ReportSummaryModel summary) {
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
                  child: _buildStatItem(
                    'Total',
                    summary.tonnage.totalFormatted,
                    Icons.scale_rounded,
                    AppColors.primary,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    'Actuel',
                    summary.tonnage.currentFormatted,
                    Icons.check_circle_rounded,
                    AppColors.success,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: summary.tonnage.progressPercentage / 100,
                minHeight: 10,
                backgroundColor: AppColors.border,
                valueColor: AlwaysStoppedAnimation<Color>(
                  _getProgressColor(summary.tonnage.progressPercentage),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProductionStats(ReportSummaryModel summary) {
    final production = summary.byProductionState;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'État de Production',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildMiniStat('En TC', production.inTc, AppColors.stateDone),
                ),
                Expanded(
                  child: _buildMiniStat('100%', production.production100, AppColors.success),
                ),
                Expanded(
                  child: _buildMiniStat('En prod', production.inProduction, AppColors.stateInProgress),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeliveryStats(ReportSummaryModel summary) {
    final delivery = summary.byDeliveryStatus;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Livraison',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildMiniStat('Livrés', delivery.fullyDelivered, AppColors.deliveryFull),
                ),
                Expanded(
                  child: _buildMiniStat('Partiels', delivery.partial, AppColors.deliveryPartial),
                ),
                Expanded(
                  child: _buildMiniStat('Non livrés', delivery.notDelivered, AppColors.deliveryNone),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCustomerStats(ReportSummaryModel summary) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Par Client',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 16),
            ...summary.byCustomer.map((customer) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: Text(
                          customer.name,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          '${customer.count} OT',
                          textAlign: TextAlign.center,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          customer.tonnageFormatted,
                          textAlign: TextAlign.right,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 12,
            ),
          ),
          Text(
            value,
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

  Widget _buildMiniStat(String label, int value, Color color) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        children: [
          Text(
            '$value',
            style: TextStyle(
              color: color,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDownloadedFile(File file) {
    final fileName = file.path.split('/').last;

    return Card(
      color: AppColors.successLight,
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.success.withOpacity(0.2),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(Icons.picture_as_pdf_rounded, color: AppColors.success),
        ),
        title: const Text('Rapport téléchargé'),
        subtitle: Text(fileName),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.open_in_new_rounded),
              color: AppColors.success,
              onPressed: () => _openFile(file),
            ),
            IconButton(
              icon: const Icon(Icons.share_rounded),
              color: AppColors.success,
              onPressed: () => _shareFile(file),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _selectDate(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
      locale: const Locale('fr', 'FR'),
    );

    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
      });
      _loadSummary();
    }
  }

  Future<void> _downloadReport() async {
    final dateStr = DateFormat('yyyy-MM-dd').format(_selectedDate);
    final file = await ref.read(reportProvider.notifier).downloadReport(
          date: dateStr,
          excludeFullyDelivered: _excludeFullyDelivered,
        );

    if (file != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Rapport téléchargé avec succès'),
          backgroundColor: AppColors.success,
          action: SnackBarAction(
            label: 'Ouvrir',
            textColor: Colors.white,
            onPressed: () => _openFile(file),
          ),
        ),
      );
    }
  }

  void _openFile(File file) {
    OpenFile.open(file.path);
  }

  void _shareFile(File file) {
    Share.shareXFiles(
      [XFile(file.path)],
      text: 'Rapport quotidien ICP Exportation',
    );
  }

  Color _getProgressColor(double progress) {
    if (progress >= 80) return AppColors.success;
    if (progress >= 50) return AppColors.warning;
    return AppColors.error;
  }
}
