import 'package:equatable/equatable.dart';
import 'package:hive/hive.dart';

/// Modèle de résumé du rapport
@HiveType(typeId: 9)
class ReportSummaryModel extends Equatable {
  @HiveField(0)
  final DateTime reportDate;

  @HiveField(1)
  final DateTime generatedAt;

  @HiveField(2)
  final int otCount;

  @HiveField(3)
  final OTRange? otRange;

  @HiveField(4)
  final TonnageStats tonnage;

  @HiveField(5)
  final double averageProgress;

  @HiveField(6)
  final ProductionStateStats byProductionState;

  @HiveField(7)
  final ReportDeliveryStats byDeliveryStatus;

  @HiveField(8)
  final List<CustomerStats> byCustomer;

  const ReportSummaryModel({
    required this.reportDate,
    required this.generatedAt,
    required this.otCount,
    this.otRange,
    required this.tonnage,
    required this.averageProgress,
    required this.byProductionState,
    required this.byDeliveryStatus,
    required this.byCustomer,
  });

  factory ReportSummaryModel.fromJson(Map<String, dynamic> json) {
    // Parser les dates de manière robuste
    DateTime parseDate(dynamic value, DateTime fallback) {
      if (value == null) return fallback;
      if (value is String && value.isNotEmpty) {
        return DateTime.tryParse(value) ?? fallback;
      }
      return fallback;
    }
    
    final now = DateTime.now();
    
    return ReportSummaryModel(
      reportDate: parseDate(json['report_date'], now),
      generatedAt: parseDate(json['generated_at'], now),
      otCount: json['ot_count'] as int? ?? 0,
      otRange: json['ot_range'] != null && (json['ot_range'] as Map).isNotEmpty
          ? OTRange.fromJson(json['ot_range'] as Map<String, dynamic>)
          : null,
      tonnage: json['tonnage'] != null 
          ? TonnageStats.fromJson(json['tonnage'] as Map<String, dynamic>)
          : const TonnageStats(totalKg: 0, currentKg: 0, totalFormatted: '0 Kg', currentFormatted: '0 Kg'),
      averageProgress: (json['average_progress'] as num?)?.toDouble() ?? 0.0,
      byProductionState: json['by_production_state'] != null
          ? ProductionStateStats.fromJson(json['by_production_state'] as Map<String, dynamic>)
          : const ProductionStateStats(inTc: 0, production100: 0, inProduction: 0),
      byDeliveryStatus: json['by_delivery_status'] != null
          ? ReportDeliveryStats.fromJson(json['by_delivery_status'] as Map<String, dynamic>)
          : const ReportDeliveryStats(fullyDelivered: 0, partial: 0, notDelivered: 0),
      byCustomer: (json['by_customer'] as List?)
              ?.map((e) => CustomerStats.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'report_date': reportDate.toIso8601String(),
      'generated_at': generatedAt.toIso8601String(),
      'ot_count': otCount,
      'ot_range': otRange?.toJson(),
      'tonnage': tonnage.toJson(),
      'average_progress': averageProgress,
      'by_production_state': byProductionState.toJson(),
      'by_delivery_status': byDeliveryStatus.toJson(),
      'by_customer': byCustomer.map((e) => e.toJson()).toList(),
    };
  }

  @override
  List<Object?> get props => [reportDate, otCount, averageProgress];
}

/// Plage de numéros OT
@HiveType(typeId: 10)
class OTRange extends Equatable {
  @HiveField(0)
  final int from;

  @HiveField(1)
  final int to;

  const OTRange({required this.from, required this.to});

  factory OTRange.fromJson(Map<String, dynamic> json) {
    return OTRange(
      from: json['from'] as int? ?? 0,
      to: json['to'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {'from': from, 'to': to};

  String get formatted => 'OT$from - OT$to';

  @override
  List<Object?> get props => [from, to];
}

/// Statistiques de tonnage
@HiveType(typeId: 11)
class TonnageStats extends Equatable {
  @HiveField(0)
  final double totalKg;

  @HiveField(1)
  final double currentKg;

  @HiveField(2)
  final String totalFormatted;

  @HiveField(3)
  final String currentFormatted;

  const TonnageStats({
    required this.totalKg,
    required this.currentKg,
    required this.totalFormatted,
    required this.currentFormatted,
  });

  factory TonnageStats.fromJson(Map<String, dynamic> json) {
    return TonnageStats(
      totalKg: (json['total_kg'] as num?)?.toDouble() ?? 0.0,
      currentKg: (json['current_kg'] as num?)?.toDouble() ?? 0.0,
      totalFormatted: json['total_formatted'] as String? ?? '0 Kg',
      currentFormatted: json['current_formatted'] as String? ?? '0 Kg',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_kg': totalKg,
      'current_kg': currentKg,
      'total_formatted': totalFormatted,
      'current_formatted': currentFormatted,
    };
  }

  double get progressPercentage => totalKg > 0 ? (currentKg / totalKg) * 100 : 0;

  @override
  List<Object?> get props => [totalKg, currentKg];
}

/// Statistiques par état de production
@HiveType(typeId: 12)
class ProductionStateStats extends Equatable {
  @HiveField(0)
  final int inTc;

  @HiveField(1)
  final int production100;

  @HiveField(2)
  final int inProduction;

  const ProductionStateStats({
    required this.inTc,
    required this.production100,
    required this.inProduction,
  });

  factory ProductionStateStats.fromJson(Map<String, dynamic> json) {
    return ProductionStateStats(
      inTc: json['in_tc'] as int? ?? 0,
      production100: json['production_100'] as int? ?? 0,
      inProduction: json['in_production'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'in_tc': inTc,
      'production_100': production100,
      'in_production': inProduction,
    };
  }

  int get total => inTc + production100 + inProduction;

  @override
  List<Object?> get props => [inTc, production100, inProduction];
}

/// Statistiques de livraison pour le rapport
@HiveType(typeId: 13)
class ReportDeliveryStats extends Equatable {
  @HiveField(0)
  final int fullyDelivered;

  @HiveField(1)
  final int partial;

  @HiveField(2)
  final int notDelivered;

  const ReportDeliveryStats({
    required this.fullyDelivered,
    required this.partial,
    required this.notDelivered,
  });

  factory ReportDeliveryStats.fromJson(Map<String, dynamic> json) {
    return ReportDeliveryStats(
      fullyDelivered: json['fully_delivered'] as int? ?? 0,
      partial: json['partial'] as int? ?? 0,
      notDelivered: json['not_delivered'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'fully_delivered': fullyDelivered,
      'partial': partial,
      'not_delivered': notDelivered,
    };
  }

  int get total => fullyDelivered + partial + notDelivered;

  @override
  List<Object?> get props => [fullyDelivered, partial, notDelivered];
}

/// Statistiques par client
@HiveType(typeId: 14)
class CustomerStats extends Equatable {
  @HiveField(0)
  final String name;

  @HiveField(1)
  final int count;

  @HiveField(2)
  final double tonnage;

  const CustomerStats({
    required this.name,
    required this.count,
    required this.tonnage,
  });

  factory CustomerStats.fromJson(Map<String, dynamic> json) {
    return CustomerStats(
      name: json['name'] as String? ?? '',
      count: json['count'] as int? ?? 0,
      tonnage: (json['tonnage'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'count': count,
      'tonnage': tonnage,
    };
  }

  String get tonnageFormatted {
    if (tonnage >= 1000) {
      return '${(tonnage / 1000).toStringAsFixed(1)} T';
    }
    return '${tonnage.toStringAsFixed(0)} Kg';
  }

  @override
  List<Object?> get props => [name, count, tonnage];
}
