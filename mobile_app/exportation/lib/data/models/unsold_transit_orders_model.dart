import 'package:equatable/equatable.dart';
import 'transit_order_model.dart';

/// Modèle de réponse pour les OTs non vendus
class UnsoldTransitOrdersResponse extends Equatable {
  final UnsoldSummary summary;
  final List<UnsoldTransitOrder> transitOrders;
  final DateTime generatedAt;

  const UnsoldTransitOrdersResponse({
    required this.summary,
    required this.transitOrders,
    required this.generatedAt,
  });

  factory UnsoldTransitOrdersResponse.fromJson(Map<String, dynamic> json, Map<String, dynamic>? meta) {
    final data = json;
    
    return UnsoldTransitOrdersResponse(
      summary: UnsoldSummary.fromJson(data['summary'] as Map<String, dynamic>),
      transitOrders: (data['transit_orders'] as List?)
              ?.map((e) => UnsoldTransitOrder.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      generatedAt: meta?['generated_at'] != null
          ? DateTime.tryParse(meta!['generated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'summary': summary.toJson(),
      'transit_orders': transitOrders.map((e) => e.toJson()).toList(),
      'generated_at': generatedAt.toIso8601String(),
    };
  }

  @override
  List<Object?> get props => [summary, transitOrders, generatedAt];
}

/// Résumé des OTs non vendus
class UnsoldSummary extends Equatable {
  final int totalCount;
  final double totalTonnage;
  final double currentTonnage;
  final double totalValue;
  final Map<String, StateStats> byState;

  const UnsoldSummary({
    required this.totalCount,
    required this.totalTonnage,
    required this.currentTonnage,
    required this.totalValue,
    required this.byState,
  });

  factory UnsoldSummary.fromJson(Map<String, dynamic> json) {
    final byStateJson = json['by_state'] as Map<String, dynamic>? ?? {};
    final byState = <String, StateStats>{};
    byStateJson.forEach((key, value) {
      byState[key] = StateStats.fromJson(value as Map<String, dynamic>);
    });

    return UnsoldSummary(
      totalCount: json['total_count'] as int? ?? 0,
      totalTonnage: (json['total_tonnage'] as num?)?.toDouble() ?? 0.0,
      currentTonnage: (json['current_tonnage'] as num?)?.toDouble() ?? 0.0,
      totalValue: (json['total_value'] as num?)?.toDouble() ?? 0.0,
      byState: byState,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_count': totalCount,
      'total_tonnage': totalTonnage,
      'current_tonnage': currentTonnage,
      'total_value': totalValue,
      'by_state': byState.map((key, value) => MapEntry(key, value.toJson())),
    };
  }

  @override
  List<Object?> get props => [totalCount, totalTonnage, currentTonnage, totalValue];
}

/// Statistiques par état
class StateStats extends Equatable {
  final int count;
  final double tonnage;

  const StateStats({
    required this.count,
    required this.tonnage,
  });

  factory StateStats.fromJson(Map<String, dynamic> json) {
    return StateStats(
      count: json['count'] as int? ?? 0,
      tonnage: (json['tonnage'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'count': count,
      'tonnage': tonnage,
    };
  }

  @override
  List<Object?> get props => [count, tonnage];
}

/// OT non vendu avec ses lots
class UnsoldTransitOrder extends Equatable {
  final int id;
  final String name;
  final String reference;
  final String customer;
  final String consignee;
  final String productType;
  final String productTypeLabel;
  final double tonnage;
  final double currentTonnage;
  final double progressPercentage;
  final String state;
  final String stateLabel;
  final double unitPrice;
  final String currency;
  final double totalAmount;
  final bool taxesPaid;
  final String? formuleState;
  final DateTime? dateCreated;
  final int lotCount;
  final int deliveryNoteCount;
  final List<UnsoldLot> lots;

  const UnsoldTransitOrder({
    required this.id,
    required this.name,
    required this.reference,
    required this.customer,
    required this.consignee,
    required this.productType,
    required this.productTypeLabel,
    required this.tonnage,
    required this.currentTonnage,
    required this.progressPercentage,
    required this.state,
    required this.stateLabel,
    required this.unitPrice,
    required this.currency,
    required this.totalAmount,
    required this.taxesPaid,
    this.formuleState,
    this.dateCreated,
    required this.lotCount,
    required this.deliveryNoteCount,
    required this.lots,
  });

  factory UnsoldTransitOrder.fromJson(Map<String, dynamic> json) {
    return UnsoldTransitOrder(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      reference: json['reference'] as String? ?? '',
      customer: json['customer'] as String? ?? '',
      consignee: json['consignee'] as String? ?? '',
      productType: json['product_type'] as String? ?? '',
      productTypeLabel: json['product_type_label'] as String? ?? '',
      tonnage: (json['tonnage'] as num?)?.toDouble() ?? 0.0,
      currentTonnage: (json['current_tonnage'] as num?)?.toDouble() ?? 0.0,
      progressPercentage: (json['progress_percentage'] as num?)?.toDouble() ?? 0.0,
      state: json['state'] as String? ?? 'draft',
      stateLabel: json['state_label'] as String? ?? '',
      unitPrice: (json['unit_price'] as num?)?.toDouble() ?? 0.0,
      currency: json['currency'] as String? ?? 'EUR',
      totalAmount: (json['total_amount'] as num?)?.toDouble() ?? 0.0,
      taxesPaid: json['taxes_paid'] as bool? ?? false,
      formuleState: json['formule_state'] as String?,
      dateCreated: json['date_created'] != null
          ? DateTime.tryParse(json['date_created'] as String)
          : null,
      lotCount: json['lot_count'] as int? ?? 0,
      deliveryNoteCount: json['delivery_note_count'] as int? ?? 0,
      lots: (json['lots'] as List?)
              ?.map((e) => UnsoldLot.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'reference': reference,
      'customer': customer,
      'consignee': consignee,
      'product_type': productType,
      'product_type_label': productTypeLabel,
      'tonnage': tonnage,
      'current_tonnage': currentTonnage,
      'progress_percentage': progressPercentage,
      'state': state,
      'state_label': stateLabel,
      'unit_price': unitPrice,
      'currency': currency,
      'total_amount': totalAmount,
      'taxes_paid': taxesPaid,
      'formule_state': formuleState,
      'date_created': dateCreated?.toIso8601String(),
      'lot_count': lotCount,
      'delivery_note_count': deliveryNoteCount,
      'lots': lots.map((e) => e.toJson()).toList(),
    };
  }

  /// Retourne le pourcentage de lots complétés
  double get lotsProgress {
    if (lots.isEmpty || lotCount == 0) return 0;
    final completedLots = lots.where((l) => l.progress >= 100).length;
    return (completedLots / lotCount) * 100;
  }

  /// Vérifie si l'OT est prêt à être validé
  bool get isReadyForValidation => state == 'ready_validation';

  /// Vérifie si tous les lots sont complets
  bool get allLotsComplete => lots.isNotEmpty && lots.every((l) => l.progress >= 100);

  @override
  List<Object?> get props => [id, name, state, progressPercentage];
}

/// Lot d'un OT non vendu
class UnsoldLot extends Equatable {
  final int id;
  final String name;
  final double targetTonnage;
  final double currentTonnage;
  final double progress;
  final String state;
  final String stateLabel;
  final String containerNumber;

  const UnsoldLot({
    required this.id,
    required this.name,
    required this.targetTonnage,
    required this.currentTonnage,
    required this.progress,
    required this.state,
    required this.stateLabel,
    required this.containerNumber,
  });

  factory UnsoldLot.fromJson(Map<String, dynamic> json) {
    return UnsoldLot(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      targetTonnage: (json['target_tonnage'] as num?)?.toDouble() ?? 0.0,
      currentTonnage: (json['current_tonnage'] as num?)?.toDouble() ?? 0.0,
      progress: (json['progress'] as num?)?.toDouble() ?? 0.0,
      state: json['state'] as String? ?? '',
      stateLabel: json['state_label'] as String? ?? '',
      containerNumber: json['container_number'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'target_tonnage': targetTonnage,
      'current_tonnage': currentTonnage,
      'progress': progress,
      'state': state,
      'state_label': stateLabel,
      'container_number': containerNumber,
    };
  }

  bool get isFull => progress >= 100;

  @override
  List<Object?> get props => [id, name, state, progress];
}
