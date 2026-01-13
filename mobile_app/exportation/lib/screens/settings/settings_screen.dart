import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../data/local/cache_manager.dart';
import '../../providers/providers.dart';

/// Écran des paramètres
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final isConnected = ref.watch(isConnectedProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Paramètres'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Profil utilisateur
          _buildUserCard(context, user),
          const SizedBox(height: 24),

          // Statut de connexion
          _buildConnectionStatus(context, isConnected),
          const SizedBox(height: 24),

          // Actions
          _buildSettingsSection(
            context,
            'Actions',
            [
              _buildSettingsTile(
                icon: Icons.refresh_rounded,
                title: 'Rafraîchir les données',
                subtitle: 'Recharger toutes les données',
                onTap: () => _refreshAllData(context, ref),
              ),
              _buildSettingsTile(
                icon: Icons.delete_outline_rounded,
                title: 'Vider le cache',
                subtitle: 'Supprimer les données locales',
                onTap: () => _clearCache(context),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // À propos
          _buildSettingsSection(
            context,
            'À propos',
            [
              _buildSettingsTile(
                icon: Icons.info_outline_rounded,
                title: 'Version',
                subtitle: '1.0.0',
              ),
              _buildSettingsTile(
                icon: Icons.business_rounded,
                title: 'ICP Côte d\'Ivoire',
                subtitle: 'Gestion des exportations',
              ),
            ],
          ),
          const SizedBox(height: 32),

          // Bouton de déconnexion
          _buildLogoutButton(context, ref),
        ],
      ),
    );
  }

  Widget _buildUserCard(BuildContext context, user) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            CircleAvatar(
              radius: 35,
              backgroundColor: AppColors.primary,
              child: Text(
                user?.initials ?? 'U',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    user?.name ?? 'Utilisateur',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    user?.email ?? '',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    children: (user?.roles ?? []).map<Widget>((role) {
                      return Chip(
                        label: Text(
                          _getRoleLabel(role),
                          style: const TextStyle(fontSize: 10),
                        ),
                        padding: EdgeInsets.zero,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        backgroundColor: AppColors.primaryLight.withOpacity(0.2),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConnectionStatus(BuildContext context, bool isConnected) {
    return Card(
      color: isConnected ? AppColors.successLight : AppColors.warningLight,
      child: ListTile(
        leading: Icon(
          isConnected ? Icons.wifi_rounded : Icons.wifi_off_rounded,
          color: isConnected ? AppColors.success : AppColors.warning,
        ),
        title: Text(
          isConnected ? 'Connecté' : 'Hors ligne',
          style: TextStyle(
            color: isConnected ? AppColors.success : AppColors.warning,
            fontWeight: FontWeight.w600,
          ),
        ),
        subtitle: Text(
          isConnected
              ? 'Les données sont synchronisées'
              : 'Les données affichées proviennent du cache',
          style: TextStyle(
            color: isConnected
                ? AppColors.success.withOpacity(0.8)
                : AppColors.warning.withOpacity(0.8),
            fontSize: 12,
          ),
        ),
      ),
    );
  }

  Widget _buildSettingsSection(
    BuildContext context,
    String title,
    List<Widget> children,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
          ),
        ),
        Card(
          child: Column(
            children: children,
          ),
        ),
      ],
    );
  }

  Widget _buildSettingsTile({
    required IconData icon,
    required String title,
    required String subtitle,
    VoidCallback? onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary),
      title: Text(title),
      subtitle: Text(
        subtitle,
        style: const TextStyle(fontSize: 12),
      ),
      trailing: onTap != null ? const Icon(Icons.chevron_right_rounded) : null,
      onTap: onTap,
    );
  }

  Widget _buildLogoutButton(BuildContext context, WidgetRef ref) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () => _showLogoutDialog(context, ref),
        icon: const Icon(Icons.logout_rounded, color: AppColors.error),
        label: const Text(
          'Se déconnecter',
          style: TextStyle(color: AppColors.error),
        ),
        style: OutlinedButton.styleFrom(
          side: const BorderSide(color: AppColors.error),
          padding: const EdgeInsets.symmetric(vertical: 16),
        ),
      ),
    );
  }

  String _getRoleLabel(String role) {
    switch (role) {
      case 'manager':
        return 'Manager';
      case 'export_agent':
        return 'Agent Export';
      case 'commercial':
        return 'Commercial';
      case 'shipping':
        return 'Expédition';
      default:
        return role;
    }
  }

  void _refreshAllData(BuildContext context, WidgetRef ref) {
    ref.read(dashboardProvider.notifier).refresh();
    ref.read(transitOrdersProvider.notifier).refresh();

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Données actualisées'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  Future<void> _clearCache(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Vider le cache'),
        content: const Text(
          'Cette action supprimera toutes les données locales. '
          'Les données seront rechargées depuis le serveur.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text(
              'Vider',
              style: TextStyle(color: AppColors.error),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      await CacheManager().clearAll();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Cache vidé'),
          backgroundColor: AppColors.success,
        ),
      );
    }
  }

  void _showLogoutDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Déconnexion'),
        content: const Text('Voulez-vous vraiment vous déconnecter ?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ref.read(authProvider.notifier).logout();
            },
            child: const Text(
              'Déconnexion',
              style: TextStyle(color: AppColors.error),
            ),
          ),
        ],
      ),
    );
  }
}
