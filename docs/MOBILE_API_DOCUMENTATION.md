# API REST Mobile - Potting Management (PDG)

## Vue d'ensemble

Cette API REST permet au PDG d'ICP de consulter le tableau de bord des activités d'exportation de cacao et de télécharger les rapports quotidiens depuis une application mobile Flutter.

**Base URL**: `https://votre-domaine.com`  
**Version API**: 1.0.0  
**Format**: JSON  
**Authentification**: Bearer Token

---

## Authentification

### POST `/api/v1/potting/auth/login`

Authentifie l'utilisateur et retourne un token JWT.

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "login": "pdg@icp.ci",
  "password": "votre_mot_de_passe"
}
```

**Réponse succès (200):**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "Bearer",
    "expires_at": "2026-01-20T10:30:00",
    "user": {
      "id": 2,
      "name": "PDG ICP",
      "email": "pdg@icp.ci",
      "roles": ["manager", "export_agent"],
      "company": "ICP Côte d'Ivoire"
    }
  }
}
```

**Réponse erreur (401):**
```json
{
  "success": false,
  "error": {
    "code": "AUTH_005",
    "message": "Identifiants incorrects"
  }
}
```

### POST `/api/v1/potting/auth/logout`

Invalide le token courant.

**Headers:**
```
Authorization: Bearer <token>
```

**Réponse:**
```json
{
  "success": true,
  "message": "Déconnexion réussie"
}
```

---

## Tableau de Bord

### GET `/api/v1/potting/dashboard`

Retourne les statistiques globales des activités d'exportation.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Paramètre | Type | Description | Exemple |
|-----------|------|-------------|---------|
| date_from | string | Date début (YYYY-MM-DD) | 2026-01-01 |
| date_to | string | Date fin (YYYY-MM-DD) | 2026-01-13 |

**Réponse succès (200):**
```json
{
  "success": true,
  "api_version": "1.0.0",
  "timestamp": "2026-01-13T10:30:00",
  "data": {
    "summary": {
      "total_transit_orders": 45,
      "total_customer_orders": 12,
      "total_tonnage": 1250.5,
      "total_tonnage_kg": 1250500,
      "current_tonnage": 980.3,
      "current_tonnage_kg": 980300,
      "average_progress": 78.4
    },
    "transit_orders_by_state": {
      "done": 20,
      "in_progress": 15,
      "ready_validation": 10
    },
    "delivery_status": {
      "fully_delivered": 18,
      "partial": 12,
      "not_delivered": 15
    },
    "by_product_type": {
      "cocoa_mass": {
        "count": 15,
        "tonnage": 450.0,
        "current_tonnage": 380.0,
        "avg_progress": 84.4
      },
      "cocoa_butter": {
        "count": 12,
        "tonnage": 380.0,
        "current_tonnage": 320.0,
        "avg_progress": 84.2
      }
    },
    "top_customers": [
      {"name": "Cargill", "count": 10, "tonnage": 350.0},
      {"name": "Barry Callebaut", "count": 8, "tonnage": 280.0}
    ]
  },
  "meta": {
    "date_from": "2026-01-01",
    "date_to": "2026-01-13",
    "generated_at": "2026-01-13T10:30:00"
  }
}
```

### GET `/api/v1/potting/dashboard/transit-orders`

Liste paginée des ordres de transit.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| date_from | string | Date début | - |
| date_to | string | Date fin | - |
| state | string | Filtrer par état | - |
| product_type | string | Type de produit | - |
| customer_id | int | ID client | - |
| page | int | Numéro de page | 1 |
| limit | int | Éléments par page (max 100) | 20 |
| include_details | string | Inclure détails ("0" ou "1") | 0 |

**États possibles (`state`):**
- `draft` - Brouillon
- `lots_generated` - Lots générés
- `in_progress` - En cours
- `ready_validation` - Prêt pour validation
- `done` - Validé
- `cancelled` - Annulé

**Types de produit (`product_type`):**
- `cocoa_mass` - Masse de cacao
- `cocoa_butter` - Beurre de cacao
- `cocoa_cake` - Cake (Tourteau) de cacao
- `cocoa_powder` - Poudre de cacao

**Réponse succès (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 123,
        "name": "OT10532/2526-01",
        "reference": "OT10532",
        "customer": "Cargill",
        "consignee": "Cargill Rotterdam",
        "product_type": "cocoa_mass",
        "product_type_label": "Masse de cacao",
        "tonnage": 25.0,
        "tonnage_kg": 25000,
        "current_tonnage": 22.5,
        "current_tonnage_kg": 22500,
        "progress_percentage": 90.0,
        "state": "in_progress",
        "state_label": "En cours",
        "delivery_status": "partial",
        "date_created": "2026-01-05"
      }
    ]
  },
  "meta": {
    "total": 45,
    "page": 1,
    "limit": 20,
    "pages": 3
  }
}
```

### GET `/api/v1/potting/dashboard/orders`

Liste paginée des commandes clients (contrats).

Mêmes paramètres que `/dashboard/transit-orders`.

---

## Rapports

### GET `/api/v1/potting/reports/summary`

Résumé du rapport quotidien en JSON.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| date | string | Date du rapport | Aujourd'hui |
| date_from | string | Date début OT | 30 jours avant |
| date_to | string | Date fin OT | Aujourd'hui |
| exclude_fully_delivered | string | Exclure livrés ("0" ou "1") | 1 |

**Réponse succès (200):**
```json
{
  "success": true,
  "data": {
    "report_date": "2026-01-13",
    "generated_at": "2026-01-13T10:30:00",
    "ot_count": 35,
    "ot_range": {"from": 10500, "to": 10535},
    "tonnage": {
      "total_kg": 875000,
      "current_kg": 720000,
      "total_formatted": "875 000 Kg",
      "current_formatted": "720 000 Kg"
    },
    "average_progress": 82.3,
    "by_production_state": {
      "in_tc": 15,
      "production_100": 8,
      "in_production": 12
    },
    "by_delivery_status": {
      "fully_delivered": 10,
      "partial": 15,
      "not_delivered": 10
    },
    "by_customer": [
      {"name": "Cargill / Cargill Rotterdam", "count": 8, "tonnage": 200000},
      {"name": "Barry Callebaut", "count": 6, "tonnage": 175000}
    ]
  }
}
```

### GET `/api/v1/potting/reports/daily`

Télécharge le rapport quotidien au format PDF.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| date | string | Date du rapport | Aujourd'hui |
| date_from | string | Date début OT | 30 jours avant |
| date_to | string | Date fin OT | Aujourd'hui |
| exclude_fully_delivered | string | Exclure livrés | 1 |

**Réponse succès (200):**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="OT_Daily_Report_2026-01-13.pdf"`

**Réponse erreur (404):**
```json
{
  "success": false,
  "error": {
    "code": "BUS_002",
    "message": "Aucun OT trouvé pour les critères spécifiés"
  }
}
```

---

## Détails d'un Ordre de Transit

### GET `/api/v1/potting/transit-orders/{id}`

Retourne les détails complets d'un OT incluant ses lots.

**Headers:**
```
Authorization: Bearer <token>
```

**Réponse succès (200):**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "name": "OT10532/2526-01",
    "reference": "OT10532",
    "customer": "Cargill",
    "consignee": "Cargill Rotterdam",
    "product_type": "cocoa_mass",
    "product_type_label": "Masse de cacao",
    "tonnage": 25.0,
    "tonnage_kg": 25000,
    "current_tonnage": 22.5,
    "progress_percentage": 90.0,
    "state": "in_progress",
    "state_label": "En cours",
    "formule_reference": "FO1-2526-0123",
    "lot_count": 5,
    "delivered_tonnage": 10.0,
    "remaining_to_deliver_tonnage": 15.0,
    "lots": [
      {
        "id": 456,
        "name": "T10532-01RA",
        "product_type": "cocoa_mass",
        "target_tonnage": 5.0,
        "current_tonnage": 4.8,
        "fill_percentage": 96.0,
        "state": "ready",
        "state_label": "Prêt pour empotage",
        "container": "MSKU1234567"
      }
    ]
  }
}
```

---

## Vérification de Santé

### GET `/api/v1/potting/health`

Endpoint public pour vérifier que l'API est opérationnelle.

**Réponse (200):**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "api_version": "1.0.0",
    "module": "potting_management",
    "timestamp": "2026-01-13T10:30:00"
  }
}
```

---

## Codes d'Erreur

### Authentification (AUTH_xxx)
| Code | Message |
|------|---------|
| AUTH_001 | Token d'authentification manquant |
| AUTH_002 | Token invalide ou expiré |
| AUTH_003 | Token expiré, veuillez vous reconnecter |
| AUTH_005 | Mot de passe incorrect |
| AUTH_007 | Droits insuffisants pour cette opération |
| AUTH_010 | Trop de tentatives, veuillez réessayer plus tard |

### Validation (VAL_xxx)
| Code | Message |
|------|---------|
| VAL_001 | Champ requis manquant |
| VAL_004 | Format de date invalide |
| VAL_005 | Plage de dates invalide |

### Ressources (RES_xxx)
| Code | Message |
|------|---------|
| RES_001 | Ressource non trouvée |
| RES_002 | Accès non autorisé à cette ressource |

### Business (BUS_xxx)
| Code | Message |
|------|---------|
| BUS_001 | Échec de génération du rapport |
| BUS_002 | Aucun ordre de transit disponible |

### Serveur (SRV_xxx)
| Code | Message |
|------|---------|
| SRV_001 | Erreur technique, veuillez réessayer |

---

## Exemple Flutter

```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

class PottingApiService {
  static const String baseUrl = 'https://votre-domaine.com';
  String? _token;

  // Authentification
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/potting/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'login': email, 'password': password}),
    );

    final data = jsonDecode(response.body);
    if (data['success'] == true) {
      _token = data['data']['token'];
    }
    return data;
  }

  // Tableau de bord
  Future<Map<String, dynamic>> getDashboard({
    String? dateFrom,
    String? dateTo,
  }) async {
    final params = <String, String>{};
    if (dateFrom != null) params['date_from'] = dateFrom;
    if (dateTo != null) params['date_to'] = dateTo;

    final uri = Uri.parse('$baseUrl/api/v1/potting/dashboard')
        .replace(queryParameters: params);

    final response = await http.get(uri, headers: _authHeaders);
    return jsonDecode(response.body);
  }

  // Liste des OT
  Future<Map<String, dynamic>> getTransitOrders({
    int page = 1,
    int limit = 20,
    String? state,
    String? productType,
  }) async {
    final params = <String, String>{
      'page': page.toString(),
      'limit': limit.toString(),
    };
    if (state != null) params['state'] = state;
    if (productType != null) params['product_type'] = productType;

    final uri = Uri.parse('$baseUrl/api/v1/potting/dashboard/transit-orders')
        .replace(queryParameters: params);

    final response = await http.get(uri, headers: _authHeaders);
    return jsonDecode(response.body);
  }

  // Résumé du rapport
  Future<Map<String, dynamic>> getReportSummary({String? date}) async {
    final params = <String, String>{};
    if (date != null) params['date'] = date;

    final uri = Uri.parse('$baseUrl/api/v1/potting/reports/summary')
        .replace(queryParameters: params);

    final response = await http.get(uri, headers: _authHeaders);
    return jsonDecode(response.body);
  }

  // Télécharger le rapport PDF
  Future<File?> downloadDailyReport({String? date}) async {
    final params = <String, String>{};
    if (date != null) params['date'] = date;

    final uri = Uri.parse('$baseUrl/api/v1/potting/reports/daily')
        .replace(queryParameters: params);

    final response = await http.get(uri, headers: _authHeaders);

    if (response.statusCode == 200) {
      final directory = await getApplicationDocumentsDirectory();
      final filename = 'OT_Daily_Report_${date ?? DateTime.now().toString().split(' ')[0]}.pdf';
      final file = File('${directory.path}/$filename');
      await file.writeAsBytes(response.bodyBytes);
      return file;
    }
    return null;
  }

  Map<String, String> get _authHeaders => {
    'Authorization': 'Bearer $_token',
    'Content-Type': 'application/json',
  };
}
```

---

## Rate Limiting

- **Authentification**: 5 requêtes / 5 minutes par IP
- **Dashboard & Listes**: 60 requêtes / minute
- **Téléchargement PDF**: 10 requêtes / minute

En cas de dépassement, vous recevrez une erreur `429 Too Many Requests` avec le code `AUTH_010`.

---

## Notes de Sécurité

1. **Tokens**: Les tokens expirent après 7 jours. Le token en clair n'est jamais stocké côté serveur (seul le hash SHA-256 est conservé).

2. **HTTPS**: Toujours utiliser HTTPS en production.

3. **Droits d'accès**: L'utilisateur doit avoir au minimum le groupe `group_potting_user` pour accéder à l'API.

4. **CORS**: L'API accepte les requêtes cross-origin (`cors='*'`). Configurez cela de manière plus restrictive en production.
