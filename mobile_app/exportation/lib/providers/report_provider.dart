import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/models.dart';
import '../data/services/services.dart';

/// État du rapport
class ReportState {
  final bool isLoading;
  final bool isDownloading;
  final ReportSummaryModel? summary;
  final File? downloadedFile;
  final String? errorMessage;
  final double downloadProgress;

  const ReportState({
    this.isLoading = false,
    this.isDownloading = false,
    this.summary,
    this.downloadedFile,
    this.errorMessage,
    this.downloadProgress = 0,
  });

  ReportState copyWith({
    bool? isLoading,
    bool? isDownloading,
    ReportSummaryModel? summary,
    File? downloadedFile,
    String? errorMessage,
    double? downloadProgress,
  }) {
    return ReportState(
      isLoading: isLoading ?? this.isLoading,
      isDownloading: isDownloading ?? this.isDownloading,
      summary: summary ?? this.summary,
      downloadedFile: downloadedFile,
      errorMessage: errorMessage,
      downloadProgress: downloadProgress ?? this.downloadProgress,
    );
  }

  bool get hasSummary => summary != null;
  bool get hasDownloadedFile => downloadedFile != null;
  bool get hasError => errorMessage != null;
}

/// Notifier pour les rapports
class ReportNotifier extends StateNotifier<ReportState> {
  final ApiService _apiService;

  ReportNotifier(this._apiService) : super(const ReportState());

  /// Charger le résumé du rapport
  Future<void> loadSummary({
    String? date,
    String? dateFrom,
    String? dateTo,
    bool excludeFullyDelivered = true,
  }) async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final summary = await _apiService.getReportSummary(
        date: date,
        dateFrom: dateFrom,
        dateTo: dateTo,
        excludeFullyDelivered: excludeFullyDelivered,
      );

      state = ReportState(summary: summary);
    } on ApiException catch (e) {
      state = ReportState(errorMessage: e.message);
    } catch (e) {
      state = const ReportState(errorMessage: 'Erreur lors du chargement');
    }
  }

  /// Télécharger le rapport PDF
  Future<File?> downloadReport({
    String? date,
    String? dateFrom,
    String? dateTo,
    bool excludeFullyDelivered = true,
  }) async {
    state = state.copyWith(
      isDownloading: true,
      downloadProgress: 0,
      errorMessage: null,
      downloadedFile: null,
    );

    try {
      final file = await _apiService.downloadDailyReport(
        date: date,
        dateFrom: dateFrom,
        dateTo: dateTo,
        excludeFullyDelivered: excludeFullyDelivered,
      );

      state = state.copyWith(
        isDownloading: false,
        downloadedFile: file,
        downloadProgress: 1,
      );

      return file;
    } on ApiException catch (e) {
      state = state.copyWith(
        isDownloading: false,
        errorMessage: e.message,
      );
      return null;
    } catch (e) {
      state = state.copyWith(
        isDownloading: false,
        errorMessage: 'Erreur lors du téléchargement',
      );
      return null;
    }
  }

  /// Effacer le fichier téléchargé
  void clearDownloadedFile() {
    state = state.copyWith(downloadedFile: null);
  }

  /// Effacer l'erreur
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }
}

/// Provider pour les rapports
final reportProvider = StateNotifierProvider<ReportNotifier, ReportState>((ref) {
  return ReportNotifier(ApiService());
});

/// Provider pour le résumé du rapport
final reportSummaryProvider = Provider<ReportSummaryModel?>((ref) {
  return ref.watch(reportProvider).summary;
});

/// Provider pour l'état de téléchargement
final isDownloadingReportProvider = Provider<bool>((ref) {
  return ref.watch(reportProvider).isDownloading;
});
