import 'package:equatable/equatable.dart';
import 'package:hive/hive.dart';

/// Modèle utilisateur (PDG)
@HiveType(typeId: 0)
class UserModel extends Equatable {
  @HiveField(0)
  final int id;

  @HiveField(1)
  final String name;

  @HiveField(2)
  final String email;

  @HiveField(3)
  final List<String> roles;

  @HiveField(4)
  final String company;

  const UserModel({
    required this.id,
    required this.name,
    required this.email,
    required this.roles,
    required this.company,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      email: json['email'] as String? ?? '',
      roles: List<String>.from(json['roles'] as List? ?? []),
      company: json['company'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'roles': roles,
      'company': company,
    };
  }

  bool get isManager => roles.contains('manager');
  bool get isExportAgent => roles.contains('export_agent');
  bool get isCommercial => roles.contains('commercial');

  String get initials {
    final parts = name.split(' ');
    if (parts.length >= 2) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return name.isNotEmpty ? name[0].toUpperCase() : 'U';
  }

  @override
  List<Object?> get props => [id, name, email, roles, company];
}

/// Modèle de réponse d'authentification
class AuthResponse {
  final String token;
  final String tokenType;
  final DateTime expiresAt;
  final UserModel user;

  AuthResponse({
    required this.token,
    required this.tokenType,
    required this.expiresAt,
    required this.user,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      token: json['token'] as String,
      tokenType: json['token_type'] as String? ?? 'Bearer',
      expiresAt: DateTime.parse(json['expires_at'] as String),
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
    );
  }

  bool get isExpired => DateTime.now().isAfter(expiresAt);
  
  bool get willExpireSoon {
    final threshold = expiresAt.subtract(const Duration(days: 1));
    return DateTime.now().isAfter(threshold);
  }
}
