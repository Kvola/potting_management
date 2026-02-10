# 🔄 WORKFLOW DU MODULE POTTING MANAGEMENT
## Guide des Acteurs et Processus d'Exportation

> **Version** : 2.0  
> **Date** : Février 2026  
> **Module** : Potting Management - ICP (Ivory Cocoa Products)

---

## 📑 TABLE DES MATIÈRES

1. [Vue d'ensemble du Workflow](#1-vue-densemble-du-workflow)
2. [Les Acteurs du Système](#2-les-acteurs-du-système)
3. [Workflow Détaillé Étape par Étape](#3-workflow-détaillé-étape-par-étape)
4. [Flux de Paiements](#4-flux-de-paiements)
5. [Gestion des Transitaires](#5-gestion-des-transitaires)
6. [Diagramme de Flux Complet](#6-diagramme-de-flux-complet)
7. [Cas d'Usage Pratiques](#7-cas-dusage-pratiques)

---

## 1. VUE D'ENSEMBLE DU WORKFLOW

### 🎯 Objectif

Le module **Potting Management** gère le cycle complet d'exportation de produits semi-finis du cacao :
- **Masse de cacao** (cocoa_mass)
- **Beurre de cacao** (cocoa_butter)
- **Tourteau/Cake de cacao** (cocoa_cake)
- **Poudre de cacao** (cocoa_powder)

### 📊 Schéma Global du Processus

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1 : AUTORISATIONS                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐            │
│   │ CAMPAGNE    │───────►│     CV      │───────►│  FORMULE    │            │
│   │ Café-Cacao  │        │ Confirmation│        │    (FO)     │            │
│   │ [Manager]   │        │  de Vente   │        │ [Gest. FO]  │            │
│   └─────────────┘        │ [Agent CCC] │        └──────┬──────┘            │
│                          └─────────────┘               │                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 2 : COMMERCE                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐        ┌─────────────┐                                   │
│   │  CONTRAT    │───────►│    OT       │◄──── Liaison FORMULE              │
│   │   Client    │        │ Ordre de    │                                   │
│   │ [Commercial]│        │  Transit    │                                   │
│   └─────────────┘        │[Gest. OT]   │                                   │
│                          └──────┬──────┘                                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 3 : PAIEMENTS                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────┐        ┌─────────────────────┐                   │
│   │ PAIEMENT PRODUCTEURS│        │   DUS (sur OT)      │                   │
│   │      (100%)         │───────►│   (après vente)     │                   │
│   │   [Comptable]       │        │    [Comptable]      │                   │
│   └─────────────────────┘        └─────────────────────┘                   │
│              │                              │                               │
│              ▼                              ▼                               │
│     ┌────────────────┐            ┌────────────────┐                       │
│     │ Formule: Payée│            │ OT: DUS payé   │                       │
│     │                │            │                │                       │
│     └────────────────┘            └────────────────┘                       │
└────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 4 : LOGISTIQUE                                 │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────────┐ │
│   │   LOTS      │───►│ CONTENEURS  │───►│     BL      │───►│  FACTURE   │ │
│   │ [Shipping]  │    │ [Shipping]  │    │ [Shipping]  │    │[Comptable] │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └────────────┘ │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. LES ACTEURS DU SYSTÈME

### 👥 Liste des Profils Utilisateurs

| # | Profil | Code Groupe | Responsabilités |
|---|--------|-------------|-----------------|
| 1 | **Manager** | `group_potting_manager` | Supervision globale, configuration, accès complet |
| 2 | **Commercial** | `group_potting_commercial` | Création et gestion des contrats clients |
| 3 | **Agent CCC** | `group_potting_agent_ccc` | Création des Confirmations de Vente (CV) |
| 4 | **Gestionnaire OT** | `group_potting_ot_manager` | Création des Ordres de Transit |
| 5 | **Gestionnaire Formules** | `group_potting_formule_manager` | Création des Formules (FO) |
| 6 | **Comptable** | `group_potting_accountant` | Paiements taxes, DUS, transitaires |
| 7 | **Shipping** | `group_potting_shipping` | Lots, conteneurs, BL, transitaires |
| 8 | **Agent Exportation** | `group_potting_ceo_agent` | Validation OT, suivi production |

### 📋 Matrice des Responsabilités (RACI)

| Tâche | Manager | Commercial | Agent CCC | Gest. OT | Gest. FO | Comptable | Shipping | Agent Exp. |
|-------|---------|------------|-----------|----------|----------|-----------|----------|------------|
| Créer Campagne | **R** | I | I | I | I | I | I | I |
| Créer CV | A | - | **R** | I | I | - | I | I |
| Créer Contrat | A | **R** | I | I | - | - | I | - |
| Créer Formule | A | - | C | I | **R** | I | - | I |
| Créer OT | A | C | - | **R** | C | - | I | I |
| Lier OT ↔ Formule | A | - | - | **R** | C | - | - | - |
| Paiement Producteurs | A | - | - | - | C | **R** | - | - |
| Générer Lots | A | - | - | - | - | - | **R** | C |
| Empotage Lots | A | - | - | - | - | - | C | **R** |
| Créer BL | A | - | - | - | - | - | **R** | C |
| Créer Facture | A | - | - | - | - | **R** | C | - |
| Paiement DUS (OT) | A | - | - | - | - | **R** | C | - |
| Paiement Transitaire | A | - | - | - | - | **R** | C | - |
| Validation OT | **R** | - | - | - | - | - | - | **R** |

> **Légende** : R = Responsable, A = Approbateur, C = Consulté, I = Informé

---

## 3. WORKFLOW DÉTAILLÉ ÉTAPE PAR ÉTAPE

### 📌 ÉTAPE 1 : Création de la Campagne Café-Cacao

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 👔 Manager |
| **Menu** | `Potting > Configuration > Campagnes` |
| **Fréquence** | 1 fois par an |

**Actions :**
1. Créer une nouvelle campagne (ex: "2025-2026")
2. Définir les dates de début et fin
3. Activer la campagne

**Données requises :**
- Nom de la campagne
- Date de début (ex: 01/10/2025)
- Date de fin (ex: 30/09/2026)

---

### 📌 ÉTAPE 2 : Création de la Confirmation de Vente (CV)

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 🏛️ Agent CCC |
| **Menu** | `Potting > Références CCC > Confirmations de Vente` |
| **Prérequis** | Campagne active |

**Actions :**
1. Créer une nouvelle CV
2. Saisir la référence CCC officielle
3. Définir le tonnage autorisé
4. Définir le prix au tonnage
5. Sélectionner le type de produit
6. **Activer** la CV

**Données requises :**
- Référence CCC (ex: "CV-327-21553")
- Campagne
- Tonnage autorisé (T)
- Prix au tonnage (FCFA/T)
- Type de produit
- Période de validité

**États de la CV :**
```
[Brouillon] ──► [Active] ──► [Consommée]
                   │
                   └──► [Annulée]
```

---

### 📌 ÉTAPE 3 : Création du Contrat Client

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 💼 Commercial |
| **Menu** | `Potting > Contrats Clients` |
| **Prérequis** | CV active |

**Actions :**
1. Créer un nouveau contrat
2. Sélectionner le client (acheteur)
3. Lier à une CV active
4. Définir le tonnage du contrat (≤ tonnage CV)
5. Définir le prix de vente
6. **Confirmer** le contrat

**Données requises :**
- Client (partenaire)
- CV de référence
- Tonnage du contrat
- Prix unitaire (FCFA/T)
- Type de produit
- Taux de droits d'export (%)

---

### 📌 ÉTAPE 4 : Création de la Formule (FO)

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 📊 Gestionnaire Formules |
| **Menu** | `Potting > Références CCC > Formules` |
| **Prérequis** | CV active |

**Actions :**
1. Créer une nouvelle Formule
2. Lier à la CV concernée
3. Saisir la référence FO1 du CCC
4. Définir le tonnage de la formule
5. Saisir le prix au kg/tonne
6. Ajouter les lignes de taxes/redevances
7. **Valider** la formule

**Données requises :**
- Référence CCC complète
- Numéro FO1 (ex: "22-3276")
- Date FO1
- CV associée
- Tonnage (T)
- Prix au kg et/ou au tonnage
- Transitaire
- Destination

**Taxes à configurer :**
| Code | Libellé | Type |
|------|---------|------|
| CCC | Redevance CCC | FCFA/kg |
| FIMR | Fonds Investissement Rural | FCFA/kg |
| SACHERIE | Redevance sacherie | FCFA/kg |
| DIUS | Droit Indicatif Usine | % |

**États de la Formule :**
```
[Brouillon] ──► [Validée] ──► [Payée]
                   │
                   └──► [Annulée]
```

---

### 📌 ÉTAPE 5 : Création de l'Ordre de Transit (OT)

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 📦 Gestionnaire OT |
| **Menu** | `Potting > Ordres de Transit` |
| **Prérequis** | Contrat confirmé + Formule validée |

**Actions :**
1. Créer un nouvel OT (depuis le contrat ou directement)
2. Lier au contrat client
3. **Lier à une Formule validée** (obligatoire)
4. Définir le tonnage
5. Sélectionner le type de produit
6. Définir le destinataire (consignee)
7. Sélectionner la campagne

**Données requises :**
- Formule (FO) - **OBLIGATOIRE**
- Contrat client (optionnel si multi-contrats)
- Tonnage (T)
- Type de produit
- Destinataire
- Campagne
- Navire
- Port de déchargement (POD)
- Numéro de booking

**États de l'OT :**
```
[Brouillon] ──► [Formule liée] ──► [Taxes payées] ──► [Lots générés]
                                                            │
                                                            ▼
[Terminé] ◄── [DUS payé] ◄── [Vendu] ◄── [Prêt validation] ◄── [En cours]
    │
    └──► [Annulé]
```

---

### 📌 ÉTAPE 6 : Paiement aux Producteurs (100%)

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 💰 Comptable |
| **Menu** | `Potting > Formules > [Formule] > Enregistrer le paiement` |
| **Prérequis** | Formule validée |

**Actions :**
1. Ouvrir la Formule concernée
2. Cliquer sur "💳 Enregistrer le paiement"
3. Créer la demande de paiement (via wizard)
4. Préparer le(s) chèque(s) pour les producteurs
5. Valider le paiement

**Impact automatique :**
- ✅ La Formule passe en état "Payée"
- ✅ Un message est posté dans le chatter

**Montants concernés :**
- Paiement producteurs = Montant net (100%)

> **Note** : Le DUS (Droit Unique de Sortie) est géré séparément sur l'OT après la vente.

---

### 📌 ÉTAPE 7 : Génération des Lots

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 🚢 Shipping |
| **Menu** | `Potting > Ordres de Transit > [OT] > Générer les lots` |
| **Prérequis** | OT en état "Brouillon" |

**Actions :**
1. Ouvrir l'OT
2. Cliquer sur "Générer les lots"
3. Confirmer le tonnage maximum par lot (selon type produit)
4. Les lots sont créés automatiquement

**Règles de génération :**
| Type produit | Tonnage max/lot | Conditionnement |
|--------------|-----------------|-----------------|
| Masse cacao | 25 T | Cartons 25 kg |
| Beurre cacao | 25 T | Cartons 25 kg |
| Cake cacao | 25 T | Big bags 1 T |
| Poudre cacao | 25 T | Sacs 25 kg |

**États des lots :**
```
[Brouillon] ──► [En production] ──► [Prêt] ──► [Empoté]
```

---

### 📌 ÉTAPE 8 : Empotage des Lots

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 🏭 Agent Exportation |
| **Menu** | `Potting > Lots` |
| **Prérequis** | Lots générés |

**Actions :**
1. Ouvrir un lot
2. Affecter un conteneur
3. Saisir les lignes de production (tonnage réel)
4. Marquer le lot comme "Empoté"

**Suivi :**
- Tonnage cible vs tonnage actuel
- Pourcentage de remplissage
- Date d'empotage

---

### 📌 ÉTAPE 9 : Marquer l'OT comme Vendu

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 👔 Manager / Agent Exportation |
| **Menu** | `Potting > Ordres de Transit > [OT] > Marquer vendu` |
| **Prérequis** | Formule payée |

**Actions :**
1. Vérifier que la Formule est en état "Payée"
2. Cliquer sur "Marquer vendu"
3. La date de vente est enregistrée

**Vérifications automatiques :**
- ✅ Paiement producteurs effectué
- ✅ OT prêt pour le paiement DUS

---

### 📌 ÉTAPE 10 : Paiement DUS (sur l'OT)

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 💰 Comptable |
| **Menu** | `Potting > Ordres de Transit > [OT] > Payer DUS` |
| **Prérequis** | OT vendu |

**Actions :**
1. Ouvrir l'OT vendu
2. Cliquer sur "Payer DUS"
3. Préparer le chèque DUS
4. Saisir le numéro de chèque
5. Valider

**Impact automatique :**
- ✅ L'OT passe en état "DUS payé"
- ✅ L'OT peut être terminé

---

### 📌 ÉTAPE 11 : Création du Bon de Livraison (BL)

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 🚢 Shipping |
| **Menu** | `Potting > Ordres de Transit > [OT] > Créer un BL` |
| **Prérequis** | OT en cours, lots empotés |

**Actions :**
1. Ouvrir l'OT
2. Cliquer sur "Créer un BL"
3. Sélectionner les lots à livrer
4. Confirmer le BL

---

### 📌 ÉTAPE 12 : Terminer l'OT

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 👔 Manager / Agent Exportation |
| **Menu** | `Potting > Ordres de Transit > [OT] > Terminer` |
| **Prérequis** | DUS payé |

**Actions :**
1. Vérifier que toutes les conditions sont remplies
2. Cliquer sur "Terminer"
3. L'OT passe en état "Terminé"

---

### 📌 ÉTAPE 13 : Facturation

| Attribut | Valeur |
|----------|--------|
| **Acteur** | 💰 Comptable |
| **Menu** | `Potting > Ordres de Transit > [OT] > Créer Facture` |
| **Prérequis** | OT terminé |

**Actions :**
1. Ouvrir l'OT terminé
2. Cliquer sur "Créer Facture"
3. La facture client est générée automatiquement

---

## 4. FLUX DE PAIEMENTS

### 💳 Paiements liés à la Formule

```
┌─────────────────────────────────────────────────────────────────┐
│                    FORMULE (FO)                                  │
│                                                                  │
│  Montant Brut = Prix × Tonnage                                  │
│  Montant Net = Montant Brut - Taxes prélevées                   │
│                                                                  │
│  ┌─────────────────────────────────┐                                  │
│  │ PAIEMENT PRODUCTEURS (100%)  │                                  │
│  │                              │                                  │
│  │ Montant = Montant Net        │                                  │
│  │                              │                                  │
│  │ Chèque → Producteurs         │                                  │
│  └─────────────┬──────────────────┘                                  │
│              │                                                     │
│              ▼                                                     │
│  ┌──────────────────┐                                              │
│  │ Formule: Payée  │                                              │
│  └──────────────────┘                                              │
└─────────────────────────────────────────────────────────────────┘
```

> **Note** : Le DUS (Droit Unique de Sortie) est géré séparément sur l'OT après la vente.

### 💰 Synchronisation automatique Formule ↔ OT

| Action sur Formule | Impact sur OT |
|--------------------|---------------|
| Paiement producteurs effectué | Formule marquée "Payée" |

---

## 5. GESTION DES TRANSITAIRES

### 📋 Workflow Factures Transitaires

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│ BROUILLON  │───►│  SOUMISE   │───►│  VALIDÉE   │───►│   PAYÉE    │
│ [Shipping] │    │ [Shipping] │    │[Comptable] │    │[Comptable] │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
                         │
                         └───► REJETÉE → BROUILLON
```

### 📎 Pièces jointes requises

| Document | Obligatoire | Format |
|----------|-------------|--------|
| Facture transitaire | ✅ Oui | PDF/Image |
| Justificatifs | Optionnel | PDF/Image |

### 💵 Informations financières transitaire

| Champ | Description |
|-------|-------------|
| **Total facturé** | Somme des factures validées/payées |
| **Total payé** | Somme des paiements confirmés |
| **Solde dû** | Montant restant à payer |
| **Montant à reverser** | Trop-perçu (si paiements > factures) |

---

## 6. DIAGRAMME DE FLUX COMPLET

```
                                    ┌─────────────┐
                                    │  CAMPAGNE   │
                                    │  [Manager]  │
                                    └──────┬──────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
           ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
           │     CV      │        │   CONTRAT   │        │  FORMULE    │
           │ [Agent CCC] │        │[Commercial] │        │ [Gest. FO]  │
           └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
                  │                      │                      │
                  │                      │                      │
                  └──────────────────────┼──────────────────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │       OT        │
                                │  [Gest. OT]     │
                                │                 │
                                │ État: Brouillon │
                                └────────┬────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
                    ▼                                         ▼
           ┌─────────────────┐                      ┌─────────────────┐
           │ PAIEMENT 100%   │                      │ GÉNÉRER LOTS    │
           │   [Comptable]   │                      │   [Shipping]    │
           └────────┬────────┘                      └────────┬────────┘
                    │                                        │
                    ▼                                        ▼
           ┌─────────────────┐                      ┌─────────────────┐
           │ Formule: Payée │                      │ OT: Lots générés│
           └────────┬────────┘                      └────────┬────────┘
                    │                                        │
                    └────────────────┬───────────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │    EMPOTAGE     │
                            │  [Agent Exp.]   │
                            │                 │
                            │ OT: En cours    │
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │  MARQUER VENDU  │
                            │   [Manager]     │
                            │                 │
                            │ OT: Vendu       │
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │   PAIEMENT DUS  │
                            │  [Comptable]    │
                            │                 │
                            │ OT: DUS payé    │
                            └────────┬────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
           ┌─────────────────┐              ┌─────────────────┐
           │   CRÉER BL      │              │   TERMINER OT   │
           │   [Shipping]    │              │    [Manager]    │
           └────────┬────────┘              └────────┬────────┘
                    │                                │
                    ▼                                ▼
           ┌─────────────────┐              ┌─────────────────┐
           │  Bon Livraison  │              │  OT: Terminé    │
           └─────────────────┘              └────────┬────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │    FACTURE      │
                                            │  [Comptable]    │
                                            └─────────────────┘
```

---

## 7. CAS D'USAGE PRATIQUES

### 🎯 Cas 1 : Exportation standard de Tourteau de Cacao

**Contexte** : ICP souhaite exporter 100 tonnes de tourteau vers l'Égypte.

| Étape | Acteur | Action | Résultat |
|-------|--------|--------|----------|
| 1 | Agent CCC | Créer CV pour 150 T | CV-2026-001 active |
| 2 | Commercial | Créer contrat 100 T avec client égyptien | Contrat CON-2026-050 |
| 3 | Gest. Formules | Créer FO avec taxes CCC | FO-2026-100 validée |
| 4 | Gest. OT | Créer OT lié au contrat et à la FO | OT-CAKE/2026/00001 |
| 5 | Comptable | Paiement producteurs (100%) | FO payée |
| 6 | Shipping | Générer 4 lots de 25 T | Lots créés |
| 7 | Agent Exp. | Empoter les lots | Lots empotés |
| 8 | Manager | Marquer vendu | OT vendu |
| 9 | Comptable | Paiement DUS (sur OT) | OT DUS payé |
| 10 | Manager | Terminer l'OT | OT terminé |
| 11 | Comptable | Créer facture | Facture générée |

### 🎯 Cas 2 : Paiement Transitaire

| Étape | Acteur | Action |
|-------|--------|--------|
| 1 | Shipping | Créer facture transitaire avec PDF joint |
| 2 | Shipping | Soumettre pour validation |
| 3 | Comptable | Valider la facture |
| 4 | Comptable | Créer le paiement |

---

## 📞 CONTACTS & SUPPORT

Pour toute question sur ce workflow :
- **Email** : support@icp-ci.com
- **Documentation** : `/potting_management/docs/`

---

*Document généré le 9 février 2026*  
*Module Potting Management v17.0.2.0*
