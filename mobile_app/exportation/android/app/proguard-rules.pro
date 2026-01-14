# ICP Export ProGuard Rules
# Règles pour garder les classes Flutter
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# Règles pour garder les classes Kotlin
-keep class kotlin.** { *; }
-keep class kotlinx.** { *; }

# Règles pour Gson (si utilisé)
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.** { *; }

# Règles pour les modèles de données
-keep class ci.icp.export.** { *; }

# Règles pour Hive
-keep class * extends com.google.protobuf.GeneratedMessageLite { *; }

# Éviter les warnings
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**
