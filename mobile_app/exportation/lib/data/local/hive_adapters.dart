import 'package:hive_flutter/hive_flutter.dart';

import '../models/models.dart';

/// Enregistrement des adapters Hive pour le stockage local
class HiveAdapters {
  HiveAdapters._();

  static void registerAdapters() {
    // User
    if (!Hive.isAdapterRegistered(0)) {
      Hive.registerAdapter(UserModelAdapter());
    }

    // Transit Order
    if (!Hive.isAdapterRegistered(1)) {
      Hive.registerAdapter(TransitOrderModelAdapter());
    }

    // Lot
    if (!Hive.isAdapterRegistered(2)) {
      Hive.registerAdapter(LotModelAdapter());
    }

    // Dashboard
    if (!Hive.isAdapterRegistered(3)) {
      Hive.registerAdapter(DashboardModelAdapter());
    }

    if (!Hive.isAdapterRegistered(4)) {
      Hive.registerAdapter(DashboardSummaryAdapter());
    }

    if (!Hive.isAdapterRegistered(5)) {
      Hive.registerAdapter(TransitOrdersByStateAdapter());
    }

    if (!Hive.isAdapterRegistered(6)) {
      Hive.registerAdapter(DeliveryStatusStatsAdapter());
    }

    if (!Hive.isAdapterRegistered(7)) {
      Hive.registerAdapter(ProductTypeStatsAdapter());
    }

    if (!Hive.isAdapterRegistered(8)) {
      Hive.registerAdapter(TopCustomerAdapter());
    }

    // Report
    if (!Hive.isAdapterRegistered(9)) {
      Hive.registerAdapter(ReportSummaryModelAdapter());
    }

    if (!Hive.isAdapterRegistered(10)) {
      Hive.registerAdapter(OTRangeAdapter());
    }

    if (!Hive.isAdapterRegistered(11)) {
      Hive.registerAdapter(TonnageStatsAdapter());
    }

    if (!Hive.isAdapterRegistered(12)) {
      Hive.registerAdapter(ProductionStateStatsAdapter());
    }

    if (!Hive.isAdapterRegistered(13)) {
      Hive.registerAdapter(ReportDeliveryStatsAdapter());
    }

    if (!Hive.isAdapterRegistered(14)) {
      Hive.registerAdapter(CustomerStatsAdapter());
    }
  }
}

// ==================== ADAPTERS MANUELS ====================
// Ces adapters sont créés manuellement pour éviter les problèmes de génération

class UserModelAdapter extends TypeAdapter<UserModel> {
  @override
  final int typeId = 0;

  @override
  UserModel read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return UserModel(
      id: fields[0] as int,
      name: fields[1] as String,
      email: fields[2] as String,
      roles: (fields[3] as List).cast<String>(),
      company: fields[4] as String,
    );
  }

  @override
  void write(BinaryWriter writer, UserModel obj) {
    writer
      ..writeByte(5)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.email)
      ..writeByte(3)
      ..write(obj.roles)
      ..writeByte(4)
      ..write(obj.company);
  }
}

class TransitOrderModelAdapter extends TypeAdapter<TransitOrderModel> {
  @override
  final int typeId = 1;

  @override
  TransitOrderModel read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return TransitOrderModel(
      id: fields[0] as int,
      name: fields[1] as String,
      reference: fields[2] as String,
      customer: fields[3] as String,
      consignee: fields[4] as String,
      productType: fields[5] as String,
      productTypeLabel: fields[6] as String,
      tonnage: fields[7] as double,
      tonnageKg: fields[8] as double,
      currentTonnage: fields[9] as double,
      currentTonnageKg: fields[10] as double,
      progressPercentage: fields[11] as double,
      state: fields[12] as String,
      stateLabel: fields[13] as String,
      deliveryStatus: fields[14] as String,
      dateCreated: fields[15] as DateTime?,
      formuleReference: fields[16] as String?,
      lotCount: fields[17] as int?,
      containerCount: fields[18] as int?,
      deliveredTonnage: fields[19] as double?,
      remainingToDeliverTonnage: fields[20] as double?,
      dateValidated: fields[21] as DateTime?,
      note: fields[22] as String?,
      lots: (fields[23] as List?)?.cast<LotModel>(),
    );
  }

  @override
  void write(BinaryWriter writer, TransitOrderModel obj) {
    writer
      ..writeByte(24)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.reference)
      ..writeByte(3)
      ..write(obj.customer)
      ..writeByte(4)
      ..write(obj.consignee)
      ..writeByte(5)
      ..write(obj.productType)
      ..writeByte(6)
      ..write(obj.productTypeLabel)
      ..writeByte(7)
      ..write(obj.tonnage)
      ..writeByte(8)
      ..write(obj.tonnageKg)
      ..writeByte(9)
      ..write(obj.currentTonnage)
      ..writeByte(10)
      ..write(obj.currentTonnageKg)
      ..writeByte(11)
      ..write(obj.progressPercentage)
      ..writeByte(12)
      ..write(obj.state)
      ..writeByte(13)
      ..write(obj.stateLabel)
      ..writeByte(14)
      ..write(obj.deliveryStatus)
      ..writeByte(15)
      ..write(obj.dateCreated)
      ..writeByte(16)
      ..write(obj.formuleReference)
      ..writeByte(17)
      ..write(obj.lotCount)
      ..writeByte(18)
      ..write(obj.containerCount)
      ..writeByte(19)
      ..write(obj.deliveredTonnage)
      ..writeByte(20)
      ..write(obj.remainingToDeliverTonnage)
      ..writeByte(21)
      ..write(obj.dateValidated)
      ..writeByte(22)
      ..write(obj.note)
      ..writeByte(23)
      ..write(obj.lots);
  }
}

class LotModelAdapter extends TypeAdapter<LotModel> {
  @override
  final int typeId = 2;

  @override
  LotModel read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return LotModel(
      id: fields[0] as int,
      name: fields[1] as String,
      productType: fields[2] as String,
      targetTonnage: fields[3] as double,
      currentTonnage: fields[4] as double,
      fillPercentage: fields[5] as double,
      state: fields[6] as String,
      stateLabel: fields[7] as String,
      container: fields[8] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, LotModel obj) {
    writer
      ..writeByte(9)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.name)
      ..writeByte(2)
      ..write(obj.productType)
      ..writeByte(3)
      ..write(obj.targetTonnage)
      ..writeByte(4)
      ..write(obj.currentTonnage)
      ..writeByte(5)
      ..write(obj.fillPercentage)
      ..writeByte(6)
      ..write(obj.state)
      ..writeByte(7)
      ..write(obj.stateLabel)
      ..writeByte(8)
      ..write(obj.container);
  }
}

class DashboardModelAdapter extends TypeAdapter<DashboardModel> {
  @override
  final int typeId = 3;

  @override
  DashboardModel read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return DashboardModel(
      summary: fields[0] as DashboardSummary,
      transitOrdersByState: fields[1] as TransitOrdersByState,
      deliveryStatus: fields[2] as DeliveryStatusStats,
      byProductType: (fields[3] as Map).cast<String, ProductTypeStats>(),
      topCustomers: (fields[4] as List).cast<TopCustomer>(),
      dateFrom: fields[5] as String?,
      dateTo: fields[6] as String?,
      generatedAt: fields[7] as DateTime,
    );
  }

  @override
  void write(BinaryWriter writer, DashboardModel obj) {
    writer
      ..writeByte(8)
      ..writeByte(0)
      ..write(obj.summary)
      ..writeByte(1)
      ..write(obj.transitOrdersByState)
      ..writeByte(2)
      ..write(obj.deliveryStatus)
      ..writeByte(3)
      ..write(obj.byProductType)
      ..writeByte(4)
      ..write(obj.topCustomers)
      ..writeByte(5)
      ..write(obj.dateFrom)
      ..writeByte(6)
      ..write(obj.dateTo)
      ..writeByte(7)
      ..write(obj.generatedAt);
  }
}

class DashboardSummaryAdapter extends TypeAdapter<DashboardSummary> {
  @override
  final int typeId = 4;

  @override
  DashboardSummary read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return DashboardSummary(
      totalTransitOrders: fields[0] as int,
      totalCustomerOrders: fields[1] as int,
      totalTonnage: fields[2] as double,
      totalTonnageKg: fields[3] as double,
      currentTonnage: fields[4] as double,
      currentTonnageKg: fields[5] as double,
      averageProgress: fields[6] as double,
    );
  }

  @override
  void write(BinaryWriter writer, DashboardSummary obj) {
    writer
      ..writeByte(7)
      ..writeByte(0)
      ..write(obj.totalTransitOrders)
      ..writeByte(1)
      ..write(obj.totalCustomerOrders)
      ..writeByte(2)
      ..write(obj.totalTonnage)
      ..writeByte(3)
      ..write(obj.totalTonnageKg)
      ..writeByte(4)
      ..write(obj.currentTonnage)
      ..writeByte(5)
      ..write(obj.currentTonnageKg)
      ..writeByte(6)
      ..write(obj.averageProgress);
  }
}

class TransitOrdersByStateAdapter extends TypeAdapter<TransitOrdersByState> {
  @override
  final int typeId = 5;

  @override
  TransitOrdersByState read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return TransitOrdersByState(
      done: fields[0] as int,
      inProgress: fields[1] as int,
      readyValidation: fields[2] as int,
    );
  }

  @override
  void write(BinaryWriter writer, TransitOrdersByState obj) {
    writer
      ..writeByte(3)
      ..writeByte(0)
      ..write(obj.done)
      ..writeByte(1)
      ..write(obj.inProgress)
      ..writeByte(2)
      ..write(obj.readyValidation);
  }
}

class DeliveryStatusStatsAdapter extends TypeAdapter<DeliveryStatusStats> {
  @override
  final int typeId = 6;

  @override
  DeliveryStatusStats read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return DeliveryStatusStats(
      fullyDelivered: fields[0] as int,
      partial: fields[1] as int,
      notDelivered: fields[2] as int,
    );
  }

  @override
  void write(BinaryWriter writer, DeliveryStatusStats obj) {
    writer
      ..writeByte(3)
      ..writeByte(0)
      ..write(obj.fullyDelivered)
      ..writeByte(1)
      ..write(obj.partial)
      ..writeByte(2)
      ..write(obj.notDelivered);
  }
}

class ProductTypeStatsAdapter extends TypeAdapter<ProductTypeStats> {
  @override
  final int typeId = 7;

  @override
  ProductTypeStats read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return ProductTypeStats(
      count: fields[0] as int,
      tonnage: fields[1] as double,
      currentTonnage: fields[2] as double,
      avgProgress: fields[3] as double,
    );
  }

  @override
  void write(BinaryWriter writer, ProductTypeStats obj) {
    writer
      ..writeByte(4)
      ..writeByte(0)
      ..write(obj.count)
      ..writeByte(1)
      ..write(obj.tonnage)
      ..writeByte(2)
      ..write(obj.currentTonnage)
      ..writeByte(3)
      ..write(obj.avgProgress);
  }
}

class TopCustomerAdapter extends TypeAdapter<TopCustomer> {
  @override
  final int typeId = 8;

  @override
  TopCustomer read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return TopCustomer(
      name: fields[0] as String,
      count: fields[1] as int,
      tonnage: fields[2] as double,
    );
  }

  @override
  void write(BinaryWriter writer, TopCustomer obj) {
    writer
      ..writeByte(3)
      ..writeByte(0)
      ..write(obj.name)
      ..writeByte(1)
      ..write(obj.count)
      ..writeByte(2)
      ..write(obj.tonnage);
  }
}

class ReportSummaryModelAdapter extends TypeAdapter<ReportSummaryModel> {
  @override
  final int typeId = 9;

  @override
  ReportSummaryModel read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return ReportSummaryModel(
      reportDate: fields[0] as DateTime,
      generatedAt: fields[1] as DateTime,
      otCount: fields[2] as int,
      otRange: fields[3] as OTRange?,
      tonnage: fields[4] as TonnageStats,
      averageProgress: fields[5] as double,
      byProductionState: fields[6] as ProductionStateStats,
      byDeliveryStatus: fields[7] as ReportDeliveryStats,
      byCustomer: (fields[8] as List).cast<CustomerStats>(),
    );
  }

  @override
  void write(BinaryWriter writer, ReportSummaryModel obj) {
    writer
      ..writeByte(9)
      ..writeByte(0)
      ..write(obj.reportDate)
      ..writeByte(1)
      ..write(obj.generatedAt)
      ..writeByte(2)
      ..write(obj.otCount)
      ..writeByte(3)
      ..write(obj.otRange)
      ..writeByte(4)
      ..write(obj.tonnage)
      ..writeByte(5)
      ..write(obj.averageProgress)
      ..writeByte(6)
      ..write(obj.byProductionState)
      ..writeByte(7)
      ..write(obj.byDeliveryStatus)
      ..writeByte(8)
      ..write(obj.byCustomer);
  }
}

class OTRangeAdapter extends TypeAdapter<OTRange> {
  @override
  final int typeId = 10;

  @override
  OTRange read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return OTRange(
      from: fields[0] as int,
      to: fields[1] as int,
    );
  }

  @override
  void write(BinaryWriter writer, OTRange obj) {
    writer
      ..writeByte(2)
      ..writeByte(0)
      ..write(obj.from)
      ..writeByte(1)
      ..write(obj.to);
  }
}

class TonnageStatsAdapter extends TypeAdapter<TonnageStats> {
  @override
  final int typeId = 11;

  @override
  TonnageStats read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return TonnageStats(
      totalKg: fields[0] as double,
      currentKg: fields[1] as double,
      totalFormatted: fields[2] as String,
      currentFormatted: fields[3] as String,
    );
  }

  @override
  void write(BinaryWriter writer, TonnageStats obj) {
    writer
      ..writeByte(4)
      ..writeByte(0)
      ..write(obj.totalKg)
      ..writeByte(1)
      ..write(obj.currentKg)
      ..writeByte(2)
      ..write(obj.totalFormatted)
      ..writeByte(3)
      ..write(obj.currentFormatted);
  }
}

class ProductionStateStatsAdapter extends TypeAdapter<ProductionStateStats> {
  @override
  final int typeId = 12;

  @override
  ProductionStateStats read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return ProductionStateStats(
      inTc: fields[0] as int,
      production100: fields[1] as int,
      inProduction: fields[2] as int,
    );
  }

  @override
  void write(BinaryWriter writer, ProductionStateStats obj) {
    writer
      ..writeByte(3)
      ..writeByte(0)
      ..write(obj.inTc)
      ..writeByte(1)
      ..write(obj.production100)
      ..writeByte(2)
      ..write(obj.inProduction);
  }
}

class ReportDeliveryStatsAdapter extends TypeAdapter<ReportDeliveryStats> {
  @override
  final int typeId = 13;

  @override
  ReportDeliveryStats read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return ReportDeliveryStats(
      fullyDelivered: fields[0] as int,
      partial: fields[1] as int,
      notDelivered: fields[2] as int,
    );
  }

  @override
  void write(BinaryWriter writer, ReportDeliveryStats obj) {
    writer
      ..writeByte(3)
      ..writeByte(0)
      ..write(obj.fullyDelivered)
      ..writeByte(1)
      ..write(obj.partial)
      ..writeByte(2)
      ..write(obj.notDelivered);
  }
}

class CustomerStatsAdapter extends TypeAdapter<CustomerStats> {
  @override
  final int typeId = 14;

  @override
  CustomerStats read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return CustomerStats(
      name: fields[0] as String,
      count: fields[1] as int,
      tonnage: fields[2] as double,
    );
  }

  @override
  void write(BinaryWriter writer, CustomerStats obj) {
    writer
      ..writeByte(3)
      ..writeByte(0)
      ..write(obj.name)
      ..writeByte(1)
      ..write(obj.count)
      ..writeByte(2)
      ..write(obj.tonnage);
  }
}
