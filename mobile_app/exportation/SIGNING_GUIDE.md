# Guide de signature de l'APK ICP Export

## 1. Installation de Java (si nécessaire)

### macOS
```bash
brew install openjdk@17
# ou télécharger depuis https://adoptium.net/
```

### Windows
Télécharger depuis https://adoptium.net/ et installer

## 2. Génération du Keystore

Une fois Java installé, exécutez cette commande :

```bash
cd android/keystore

keytool -genkey -v \
  -keystore icp-export-release.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias icp-export \
  -storepass 'IcpExport2024!' \
  -keypass 'IcpExport2024!' \
  -dname "CN=ICP Export, OU=IT, O=ICP Cote d Ivoire, L=Abidjan, ST=Abidjan, C=CI"
```

## 3. Informations du Keystore

- **Fichier**: `android/keystore/icp-export-release.jks`
- **Alias**: `icp-export`
- **Mot de passe store**: `IcpExport2024!`
- **Mot de passe clé**: `IcpExport2024!`
- **Validité**: 10000 jours (~27 ans)

## 4. Génération de l'APK

### APK Debug (pour tests)
```bash
flutter build apk --debug
```

### APK Release signé
```bash
flutter build apk --release
```

### App Bundle (pour Google Play)
```bash
flutter build appbundle --release
```

## 5. Localisation des fichiers générés

- APK Debug: `build/app/outputs/flutter-apk/app-debug.apk`
- APK Release: `build/app/outputs/flutter-apk/app-release.apk`
- App Bundle: `build/app/outputs/bundle/release/app-release.aab`

## 6. Configuration des environnements

Modifier `lib/core/config/app_config.dart` :

```dart
// Pour la préproduction (actuel)
static const AppEnvironment currentEnvironment = AppEnvironment.preproduction;

// Pour la production
static const AppEnvironment currentEnvironment = AppEnvironment.production;

// Pour le développement
static const AppEnvironment currentEnvironment = AppEnvironment.development;
```

## 7. Environnements disponibles

| Environnement | IP | Base de données |
|--------------|-----|-----------------|
| Développement | 192.168.5.159 | icp_dev_db |
| Préproduction | 192.168.5.85 | icp_test_db |
| Production | 192.168.5.86 | icp_db |

## ⚠️ IMPORTANT

- **Conservez le keystore** dans un endroit sûr
- Ne committez **JAMAIS** le keystore dans Git
- Les mots de passe peuvent être changés via des variables d'environnement :
  - `KEYSTORE_PASSWORD`
  - `KEY_PASSWORD`
