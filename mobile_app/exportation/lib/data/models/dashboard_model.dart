import 'package:equatable/equatable.dart';
import 'package:hive/hive.dart';

/// Modèle de tableau de bord
@HiveType(typeId: 3)
class DashboardModel extends Equatable {
  @HiveField(0)
  final DashboardSummary summary;

  @HiveField(1)
  final TransitOrdersByState transitOrdersByState;

  @HiveField(2)
  final DeliveryStatusStats deliveryStatus;

  @HiveField(3)
  final Map<String, ProductTypeStats> byProductType;

  @HiveField(4)
  final List<TopCustomer> topCustomers;

  @HiveField(5)
  final String? dateFrom;

  @HiveField(6)
  final String? dateTo;

  @HiveField(7)
  final DateTime generatedAt;

  const DashboardModel({
    required this.summary,
    required this.transitOrdersByState,
    required this.deliveryStatus,
    required this.byProductType,
    required this.topCustomers,
    this.dateFrom,
    this.dateTo,
    required this.generatedAt,
  });

  factory DashboardModel.fromJson(Map<String, dynamic> json, Map<String, dynamic>? meta) {
    final data = json;
    
    // Parse product type stats
    final productTypeStats = <String, ProductTypeStats>{};
    final byProductType = data['by_product_type'] as Map<String, dynamic>? ?? {};
    byProductType.forEach((key, value) {
      productTypeStats[key] = ProductTypeStats.fromJson(value as Map<String, dynamic>);
    });

    return DashboardModel(
      summary: DashboardSummary.fromJson(data['summary'] as Map<String, dynamic>),
      transitOrdersByState: TransitOrdersByState.fromJson(
        data['transit_orders_by_state'] as Map<String, dynamic>,
      ),
      deliveryStatus: DeliveryStatusStats.fromJson(
        data['delivery_status'] as Map<String, dynamic>,
      ),
      byProductType: productTypeStats,
      topCustomers: (data['top_customers'] as List?)
              ?.map((e) => TopCustomer.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      dateFrom: meta?['date_from'] as String?,
      dateTo: meta?['date_to'] as String?,
      generatedAt: meta?['generated_at'] != null
          ? DateTime.tryParse(meta!['generated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'summary': summary.toJson(),
      'transit_orders_by_state': transitOrdersByState.toJson(),
      'delivery_status': deliveryStatus.toJson(),
      'by_product_type':
          byProductType.map((key, value) => MapEntry(key, value.toJson())),
      'top_customers': topCustomers.map((e) => e.toJson()).toList(),
      'date_from': dateFrom,
      'date_to': dateTo,
      'generated_at': generatedAt.toIso8601String(),
    };
  }

  @override
  List<Object?> get props => [summary, transitOrdersByState, deliveryStatus, generatedAt];
}

/// Résumé du tableau de bord
@HiveType(typeId: 4)
class DashboardSummary extends Equatable {
  @HiveField(0)
  final int totalTransitOrders;

  @HiveField(1)
  final int totalCustomerOrders;

  @HiveField(2)
  final double totalTonnage;

  @HiveField(3)
  final double totalTonnageKg;

  @HiveField(4)
  final double currentTonnage;

  @HiveField(5)
  final double currentTonnageKg;

  @HiveField(6)
  final double averageProgress;

  const DashboardSummary({
    required this.totalTransitOrders,
    required this.totalCustomerOrders,
    required this.totalTonnage,
    required this.totalTonnageKg,
    required this.currentTonnage,
    required this.currentTonnageKg,
    required this.averageProgress,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      totalTransitOrders: json['total_transit_orders'] as int? ?? 0,
      totalCustomerOrders: json['total_customer_orders'] as int? ?? 0,
      totalTonnage: (json['total_tonnage'] as num?)?.toDouble() ?? 0.0,
      totalTonnageKg: (json['total_tonnage_kg'] as num?)?.toDouble() ?? 0.0,
      currentTonnage: (json['current_tonnage'] as num?)?.toDouble() ?? 0.0,
      currentTonnageKg: (json['current_tonnage_kg'] as num?)?.toDouble() ?? 0.0,
      averageProgress: (json['average_progress'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_transit_orders': totalTransitOrders,
      'total_customer_orders': totalCustomerOrders,
      'total_tonnage': totalTonnage,
      'total_tonnage_kg': totalTonnageKg,
      'current_tonnage': currentTonnage,
      'current_tonnage_kg': currentTonnageKg,
      'average_progress': averageProgress,
    };
  }

  @override
  List<Object?> get props => [
        totalTransitOrders,
        totalCustomerOrders,
        totalTonnage,
        currentTonnage,
        averageProgress,
      ];
}

/// Statistiques OT par état
@HiveType(typeId: 5)
class TransitOrdersByState extends Equatable {
  @HiveField(0)
  final int done;

  @HiveField(1)
  final int inProgress;

  @HiveField(2)
  final int readyValidation;

  const TransitOrdersByState({
    required this.done,
    required this.inProgress,
    required this.readyValidation,
  });

  factory TransitOrdersByState.fromJson(Map<String, dynamic> json) {
    return TransitOrdersByState(
      done: json['done'] as int? ?? 0,
      inProgress: json['in_progress'] as int? ?? 0,
      readyValidation: json['ready_validation'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'done': done,
      'in_progress': inProgress,
      'ready_validation': readyValidation,
    };
  }

  int get total => done + inProgress + readyValidation;

  @override
  List<Object?> get props => [done, inProgress, readyValidation];
}

/// Statistiques de livraison
@HiveType(typeId: 6)
class DeliveryStatusStats extends Equatable {
  @HiveField(0)
  final int fullyDelivered;

  @HiveField(1)
  final int partial;

  @HiveField(2)
  final int notDelivered;

  const DeliveryStatusStats({
    required this.fullyDelivered,
    required this.partial,
    required this.notDelivered,
  });

  factory DeliveryStatusStats.fromJson(Map<String, dynamic> json) {
    return DeliveryStatusStats(
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

/// Statistiques par type de produit
@HiveType(typeId: 7)
class ProductTypeStats extends Equatable {
  @HiveField(0)
  final int count;

  @HiveField(1)
  final double tonnage;

  @HiveField(2)
  final double currentTonnage;

  @HiveField(3)
  final double avgProgress;

  const ProductTypeStats({
    required this.count,
    required this.tonnage,
    required this.currentTonnage,
    required this.avgProgress,
  });

  factory ProductTypeStats.fromJson(Map<String, dynamic> json) {
    return ProductTypeStats(
      count: json['count'] as int? ?? 0,
      tonnage: (json['tonnage'] as num?)?.toDouble() ?? 0.0,
      currentTonnage: (json['current_tonnage'] as num?)?.toDouble() ?? 0.0,
      avgProgress: (json['avg_progress'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'count': count,
      'tonnage': tonnage,
      'current_tonnage': currentTonnage,
      'avg_progress': avgProgress,
    };
  }

  @override
  List<Object?> get props => [count, tonnage, currentTonnage, avgProgress];
}

/// Top client
@HiveType(typeId: 8)
class TopCustomer extends Equatable {
  @HiveField(0)
  final String name;

  @HiveField(1)
  final int count;

  @HiveField(2)
  final double tonnage;

  const TopCustomer({
    required this.name,
    required this.count,
    required this.tonnage,
  });

  factory TopCustomer.fromJson(Map<String, dynamic> json) {
    return TopCustomer(
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

  @override
  List<Object?> get props => [name, count, tonnage];
}
