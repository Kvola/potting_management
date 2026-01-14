import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'core/config/app_config.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'data/local/hive_adapters.dart';
import 'data/local/cache_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Configuration de l'orientation
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Configuration de la barre de statut
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
    ),
  );

  // Initialisation des locales pour les dates
  await initializeDateFormatting('fr_FR', null);

  // Initialisation de Hive pour le stockage local
  await Hive.initFlutter();
  
  // Enregistrement des adapters Hive
  HiveAdapters.registerAdapters();
  
  // Initialisation du cache
  await CacheManager.init();

  // Log de l'environnement actuel (seulement en debug)
  if (AppConfig.isDebugMode) {
    debugPrint('═══════════════════════════════════════════════');
    debugPrint('🚀 ${AppConfig.appName} v${AppConfig.appVersion}');
    debugPrint('📍 Environnement: ${AppConfig.environment.displayName}');
    debugPrint('🌐 Serveur: ${AppConfig.baseUrl}');
    debugPrint('💾 Base de données: ${AppConfig.database}');
    debugPrint('═══════════════════════════════════════════════');
  }

  runApp(
    const ProviderScope(
      child: ICPExportApp(),
    ),
  );
}

class ICPExportApp extends ConsumerWidget {
  const ICPExportApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: AppConfig.appName,
      debugShowCheckedModeBanner: AppConfig.showDebugBanner,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.light,
      routerConfig: router,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('fr', 'FR'),
        Locale('en', 'US'),
      ],
      locale: const Locale('fr', 'FR'),
      builder: (context, child) {
        // Désactiver le scaling du texte pour une UI cohérente
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.noScaling,
          ),
          child: Banner(
            message: AppConfig.isDevelopment 
                ? 'DEV' 
                : AppConfig.isPreproduction 
                    ? 'TEST' 
                    : '',
            location: BannerLocation.topEnd,
            color: AppConfig.isDevelopment 
                ? Colors.red 
                : Colors.orange,
            textStyle: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 10,
            ),
            child: !AppConfig.isProduction && !AppConfig.showDebugBanner
                ? child!
                : child!,
          ),
        );
      },
    );
  }
}
