# ICP Export

Application mobile Flutter pour le suivi des activités d'exportation de cacao d'ICP (Industries de Cacao et de Chocolat de Côte d'Ivoire).

## 🔧 Configuration des Environnements

| Environnement | IP | Base de données | Port |
|--------------|-----|-----------------|------|
| Développement | 192.168.5.159 | icp_dev_db | 8069 |
| **Préproduction** | **192.168.5.85** | **icp_test_db** | **8069** |
| Production | 192.168.5.86 | icp_db | 8069 |

> ⚠️ **Actuellement configuré pour : Préproduction**

### Changer d'environnement

Modifier le fichier `lib/core/config/app_config.dart` (ligne ~40) :

```dart
static const AppEnvironment currentEnvironment = AppEnvironment.preproduction;
// Options : development, preproduction, production
```

## 📱 Fonctionnalités

- **Tableau de bord** : Vue d'ensemble des activités d'exportation
  - Statistiques des ordres de transit
  - Graphiques de progression
  - Répartition par état et type de produit
  - Top clients

- **Ordres de Transit** : Liste et détails des OT
  - Filtrage par état et type de produit
  - Pagination infinie
  - Détails complets avec lots

- **Rapports** : Rapport quotidien du PDG
  - Résumé des tonnages
  - Statistiques de livraison
  - Téléchargement PDF
  - Partage

- **Mode Offline** : Fonctionne sans connexion
  - Cache local avec Hive
  - Synchronisation automatique
  - Bannière de statut

## 🛠 Technologies

- **Flutter** 3.2.0+
- **Riverpod** : Gestion d'état réactive
- **Dio** : Client HTTP avec intercepteurs
- **Hive** : Stockage local NoSQL
- **GoRouter** : Navigation déclarative
- **FL Chart** : Visualisations

## 📦 Installation

### Prérequis

- Flutter SDK >=3.2.0
- Dart SDK >=3.2.0
- Android Studio / Xcode

### Setup

```bash
# Cloner le projet
cd mobile_app/exportation

# Installer les dépendances
flutter pub get

# Télécharger les fonts Poppins
# Placer dans assets/fonts/

# Lancer l'app
flutter run
```

### Configuration API

Modifier `lib/core/config/app_config.dart` :

```dart
static const String baseUrl = 'https://your-odoo-server.com';
```

## 📁 Structure du projet

```
lib/
├── core/
│   ├── config/          # Configuration app
│   ├── theme/           # Thème et couleurs
│   └── router/          # Navigation GoRouter
├── data/
│   ├── models/          # Modèles de données
│   ├── services/        # Services API
│   └── local/           # Stockage Hive
├── providers/           # Providers Riverpod
├── screens/             # Écrans de l'app
│   ├── auth/
│   ├── dashboard/
│   ├── transit_orders/
│   ├── reports/
│   └── settings/
└── widgets/             # Widgets réutilisables
```

## 🔐 Authentification

L'app utilise l'authentification Bearer Token :

1. Login avec identifiants Odoo
2. Token stocké sécurisé (FlutterSecureStorage)
3. Refresh automatique
4. Expiration : 7 jours

## 📊 API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/mobile/auth/login` | POST | Authentification |
| `/api/mobile/auth/logout` | POST | Déconnexion |
| `/api/mobile/dashboard` | GET | Tableau de bord |
| `/api/mobile/transit-orders` | GET | Liste OT |
| `/api/mobile/orders/{id}` | GET | Détail OT |
| `/api/mobile/reports/summary` | GET | Résumé rapport |
| `/api/mobile/reports/daily` | GET | PDF quotidien |

## 🎨 Thème

Couleurs principales :
- **Primary** : #4E342E (Brun chocolat)
- **Success** : #2E7D32 (Vert)
- **Warning** : #F57C00 (Orange)
- **Error** : #D32F2F (Rouge)

## 📱 Screenshots

| Dashboard | Ordres de Transit | Rapports |
|-----------|-------------------|----------|
| ![Dashboard](screenshots/dashboard.png) | ![OT](screenshots/transit_orders.png) | ![Reports](screenshots/reports.png) |

## 🔧 Build

### Android

```bash
flutter build apk --release
# ou
flutter build appbundle --release
```

### iOS

```bash
flutter build ios --release
```

## 📝 Licence

© 2024 ICP - Industrial Cocoa Processing. Tous droits réservés.
