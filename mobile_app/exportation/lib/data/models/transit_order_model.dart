import 'package:equatable/equatable.dart';
import 'package:hive/hive.dart';

/// Modèle d'ordre de transit
@HiveType(typeId: 1)
class TransitOrderModel extends Equatable {
  @HiveField(0)
  final int id;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final String reference;

  @HiveField(3)
  final String customer;

  @HiveField(4)
  final String consignee;

  @HiveField(5)
  final String productType;

  @HiveField(6)
  final String productTypeLabel;

  @HiveField(7)
  final double tonnage;

  @HiveField(8)
  final double tonnageKg;

  @HiveField(9)
  final double currentTonnage;

  @HiveField(10)
  final double currentTonnageKg;

  @HiveField(11)
  final double progressPercentage;

  @HiveField(12)
  final String state;

  @HiveField(13)
  final String stateLabel;

  @HiveField(14)
  final String deliveryStatus;

  @HiveField(15)
  final DateTime? dateCreated;

  // Champs détaillés (optionnels)
  @HiveField(16)
  final String? formuleReference;

  @HiveField(17)
  final int? lotCount;

  @HiveField(18)
  final int? containerCount;

  @HiveField(19)
  final double? deliveredTonnage;

  @HiveField(20)
  final double? remainingToDeliverTonnage;

  @HiveField(21)
  final DateTime? dateValidated;

  @HiveField(22)
  final String? note;

  @HiveField(23)
  final List<LotModel>? lots;

  const TransitOrderModel({
    required this.id,
    required this.name,
    required this.reference,
    required this.customer,
    required this.consignee,
    required this.productType,
    required this.productTypeLabel,
    required this.tonnage,
    required this.tonnageKg,
    required this.currentTonnage,
    required this.currentTonnageKg,
    required this.progressPercentage,
    required this.state,
    required this.stateLabel,
    required this.deliveryStatus,
    this.dateCreated,
    this.formuleReference,
    this.lotCount,
    this.containerCount,
    this.deliveredTonnage,
    this.remainingToDeliverTonnage,
    this.dateValidated,
    this.note,
    this.lots,
  });

  factory TransitOrderModel.fromJson(Map<String, dynamic> json) {
    return TransitOrderModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      reference: json['reference'] as String? ?? '',
      customer: json['customer'] as String? ?? '',
      consignee: json['consignee'] as String? ?? '',
      productType: json['product_type'] as String? ?? '',
      productTypeLabel: json['product_type_label'] as String? ?? '',
      tonnage: (json['tonnage'] as num?)?.toDouble() ?? 0.0,
      tonnageKg: (json['tonnage_kg'] as num?)?.toDouble() ?? 0.0,
      currentTonnage: (json['current_tonnage'] as num?)?.toDouble() ?? 0.0,
      currentTonnageKg: (json['current_tonnage_kg'] as num?)?.toDouble() ?? 0.0,
      progressPercentage: (json['progress_percentage'] as num?)?.toDouble() ?? 0.0,
      state: json['state'] as String? ?? 'draft',
      stateLabel: json['state_label'] as String? ?? '',
      deliveryStatus: json['delivery_status'] as String? ?? 'not_delivered',
      dateCreated: json['date_created'] != null
          ? DateTime.tryParse(json['date_created'] as String)
          : null,
      formuleReference: json['formule_reference'] as String?,
      lotCount: json['lot_count'] as int?,
      containerCount: json['container_count'] as int?,
      deliveredTonnage: (json['delivered_tonnage'] as num?)?.toDouble(),
      remainingToDeliverTonnage:
          (json['remaining_to_deliver_tonnage'] as num?)?.toDouble(),
      dateValidated: json['date_validated'] != null
          ? DateTime.tryParse(json['date_validated'] as String)
          : null,
      note: json['note'] as String?,
      lots: (json['lots'] as List?)
          ?.map((e) => LotModel.fromJson(e as Map<String, dynamic>))
          .toList(),
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
      'tonnage_kg': tonnageKg,
      'current_tonnage': currentTonnage,
      'current_tonnage_kg': currentTonnageKg,
      'progress_percentage': progressPercentage,
      'state': state,
      'state_label': stateLabel,
      'delivery_status': deliveryStatus,
      'date_created': dateCreated?.toIso8601String(),
      'formule_reference': formuleReference,
      'lot_count': lotCount,
      'container_count': containerCount,
      'delivered_tonnage': deliveredTonnage,
      'remaining_to_deliver_tonnage': remainingToDeliverTonnage,
      'date_validated': dateValidated?.toIso8601String(),
      'note': note,
      'lots': lots?.map((e) => e.toJson()).toList(),
    };
  }

  bool get isCompleted => progressPercentage >= 100;
  bool get isDone => state == 'done';
  bool get isInProgress => state == 'in_progress';
  bool get isFullyDelivered => deliveryStatus == 'fully_delivered';
  bool get isPartiallyDelivered => deliveryStatus == 'partial';

  @override
  List<Object?> get props => [id, name, state, progressPercentage];
}

/// Modèle de lot
@HiveType(typeId: 2)
class LotModel extends Equatable {
  @HiveField(0)
  final int id;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final String productType;

  @HiveField(3)
  final double targetTonnage;

  @HiveField(4)
  final double currentTonnage;

  @HiveField(5)
  final double fillPercentage;

  @HiveField(6)
  final String state;

  @HiveField(7)
  final String stateLabel;

  @HiveField(8)
  final String? container;

  const LotModel({
    required this.id,
    required this.name,
    required this.productType,
    required this.targetTonnage,
    required this.currentTonnage,
    required this.fillPercentage,
    required this.state,
    required this.stateLabel,
    this.container,
  });

  factory LotModel.fromJson(Map<String, dynamic> json) {
    return LotModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      productType: json['product_type'] as String? ?? '',
      targetTonnage: (json['target_tonnage'] as num?)?.toDouble() ?? 0.0,
      currentTonnage: (json['current_tonnage'] as num?)?.toDouble() ?? 0.0,
      fillPercentage: (json['fill_percentage'] as num?)?.toDouble() ?? 0.0,
      state: json['state'] as String? ?? '',
      stateLabel: json['state_label'] as String? ?? '',
      container: json['container'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'product_type': productType,
      'target_tonnage': targetTonnage,
      'current_tonnage': currentTonnage,
      'fill_percentage': fillPercentage,
      'state': state,
      'state_label': stateLabel,
      'container': container,
    };
  }

  bool get isFull => fillPercentage >= 100;

  @override
  List<Object?> get props => [id, name, state, fillPercentage];
}
