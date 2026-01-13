import 'package:flutter/material.dart';

/// Palette de couleurs ICP Exportation
class AppColors {
  AppColors._();

  // Couleurs principales ICP (Cacao/Chocolat)
  static const Color primary = Color(0xFF5D4037);        // Marron chocolat
  static const Color primaryLight = Color(0xFF8B6B61);   // Marron clair
  static const Color primaryDark = Color(0xFF321911);    // Marron foncé
  
  static const Color secondary = Color(0xFFD4A574);      // Caramel/Or
  static const Color secondaryLight = Color(0xFFE8C9A3);
  static const Color secondaryDark = Color(0xFFB8895A);
  
  // Couleurs accent
  static const Color accent = Color(0xFFFF9800);         // Orange
  static const Color accentLight = Color(0xFFFFB74D);
  
  // Couleurs de fond
  static const Color background = Color(0xFFF5F5F5);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color inputBackground = Color(0xFFF8F8F8);
  static const Color chipBackground = Color(0xFFEEEEEE);
  
  // Couleurs de fond sombres
  static const Color backgroundDark = Color(0xFF121212);
  static const Color surfaceDark = Color(0xFF1E1E1E);
  
  // Texte
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF757575);
  static const Color textHint = Color(0xFF9E9E9E);
  static const Color textPrimaryDark = Color(0xFFE0E0E0);
  
  // Bordures et dividers
  static const Color border = Color(0xFFE0E0E0);
  static const Color divider = Color(0xFFEEEEEE);
  static const Color shadow = Color(0x1A000000);
  
  // États
  static const Color success = Color(0xFF4CAF50);
  static const Color successLight = Color(0xFFE8F5E9);
  static const Color warning = Color(0xFFFFC107);
  static const Color warningLight = Color(0xFFFFF8E1);
  static const Color error = Color(0xFFE53935);
  static const Color errorLight = Color(0xFFFFEBEE);
  static const Color info = Color(0xFF2196F3);
  static const Color infoLight = Color(0xFFE3F2FD);
  
  // Couleurs pour les graphiques
  static const Color chartMass = Color(0xFF5D4037);      // Masse
  static const Color chartButter = Color(0xFFD4A574);    // Beurre
  static const Color chartCake = Color(0xFF8D6E63);      // Tourteau
  static const Color chartPowder = Color(0xFFBCAAA4);    // Poudre
  
  // Couleurs d'état OT
  static const Color stateDraft = Color(0xFF9E9E9E);
  static const Color stateInProgress = Color(0xFF2196F3);
  static const Color stateReady = Color(0xFFFF9800);
  static const Color stateDone = Color(0xFF4CAF50);
  static const Color stateCancelled = Color(0xFFE53935);
  
  // Couleurs de livraison
  static const Color deliveryFull = Color(0xFF4CAF50);
  static const Color deliveryPartial = Color(0xFFFF9800);
  static const Color deliveryNone = Color(0xFFE53935);
  
  // Gradients
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, primaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
  
  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0xFF5D4037), Color(0xFF8B6B61)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
  
  static const LinearGradient accentGradient = LinearGradient(
    colors: [secondary, secondaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
