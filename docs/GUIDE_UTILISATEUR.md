# 📋 Guide Utilisateur - Module Gestion des Exportations (Potting Management)

> **Version** : 17.0.1.3.0  
> **Dernière mise à jour** : Janvier 2026  
> **Auteur** : ICP - Ivory Cocoa Products

---

## 📑 Table des matières

1. [Introduction](#1-introduction)
2. [Concepts clés et Réglementation CCC](#2-concepts-clés-et-réglementation-ccc)
3. [Rôles et Permissions](#3-rôles-et-permissions)
4. [Confirmations de Vente (CV)](#4-confirmations-de-vente-cv)
5. [Contrats Clients](#5-contrats-clients)
6. [Formules (FO)](#6-formules-fo)
7. [Ordres de Transit (OT)](#7-ordres-de-transit-ot)
8. [Gestion des Lots](#8-gestion-des-lots)
9. [Bons de Livraison (BL)](#9-bons-de-livraison-bl)
10. [Facturation](#10-facturation)
11. [Transitaires et Paiements](#11-transitaires-et-paiements)
12. [Campagnes Café-Cacao](#12-campagnes-café-cacao)
13. [Certifications](#13-certifications)
14. [Tableaux de Bord](#14-tableaux-de-bord)
15. [API Mobile (PDG)](#15-api-mobile-pdg)
16. [Rapports et Envoi par Email](#16-rapports-et-envoi-par-email)
17. [Configuration](#17-configuration)
18. [FAQ et Support](#18-faq-et-support)

---

## 1. Introduction

Le module **Gestion des Exportations (Potting Management)** est un système complet de gestion des opérations d'exportation de **produits semi-finis du cacao** pour les entreprises de transformation en Côte d'Ivoire. Il gère l'ensemble du processus depuis les autorisations réglementaires du **Conseil Café-Cacao (CCC)** jusqu'à la facturation des exportations.

### 🎯 Fonctionnalités principales

| Module | Description |
|--------|-------------|
| **📜 Confirmations de Vente (CV)** | Autorisations d'exportation du CCC |
| **📝 Contrats Clients** | Accords commerciaux avec les acheteurs |
| **🧮 Formules (FO)** | Fixation des prix et taxes CCC |
| **🚚 Ordres de Transit (OT)** | Expéditions physiques des marchandises |
| **📦 Lots** | Suivi des productions et conditionnements |
| **📋 Bons de Livraison** | Documents d'expédition |
| **💰 Facturation** | Génération des factures clients |
| **👷 Transitaires** | Gestion des agents et leurs paiements |
| **📊 Tableaux de bord** | Vue d'ensemble des opérations |
| **📱 API Mobile** | Application PDG pour suivi en temps réel |

### 🏭 Produits gérés

| Produit | Code | Conditionnement | Poids unitaire |
|---------|------|-----------------|----------------|
| **Masse de cacao** | `cocoa_mass` | Carton | 25 kg |
| **Beurre de cacao** | `cocoa_butter` | Carton | 25 kg |
| **Cake (Tourteau)** | `cocoa_cake` | Big bag | 1 000 kg |
| **Poudre de cacao** | `cocoa_powder` | Sac | 25 kg |

### 📊 Flux de travail global

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Confirmation de │ ──► │    Contrat      │ ──► │    Formule      │
│   Vente (CV)    │     │    Client       │     │     (FO)        │
│   [CCC]         │     │  [Commercial]   │     │    [CCC]        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Facture      │ ◄── │  Bon de         │ ◄── │  Ordre de       │
│   [Finance]     │     │  Livraison (BL) │     │  Transit (OT)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │     Lots        │
                                                │  [Production]   │
                                                └─────────────────┘
```

---

## 2. Concepts clés et Réglementation CCC

### 🏛️ Le Conseil Café-Cacao (CCC)

Le **Conseil du Café-Cacao** est l'organe de régulation de la filière cacao en Côte d'Ivoire. Toute exportation de produits cacao nécessite des autorisations officielles du CCC.

### 📄 Documents réglementaires

| Document | Sigle | Émetteur | Description |
|----------|-------|----------|-------------|
| **Confirmation de Vente** | CV | CCC | Autorisation d'exportation avec tonnage et prix |
| **Formule** | FO / FO1 | CCC | Fixation du prix et détail des taxes |

### 💰 Système de taxes CCC

Les exportations sont soumises à différentes taxes et redevances prélevées par le CCC :

#### Redevances (montant par kg)

| Code | Libellé | Type | Description |
|------|---------|------|-------------|
| **CCC** | Redevance Conseil Café-Cacao | FCFA/kg | Contribution au fonctionnement du CCC |
| **FIMR** | Fonds d'Investissement en Milieu Rural | FCFA/kg | Développement agricole |
| **SACHERIE** | Redevance sacherie | FCFA/kg | Financement des emballages |
| **FDPCC** | Fonds de Développement Café-Cacao | FCFA/kg | Développement de la filière |

#### Taxes (pourcentage)

| Code | Libellé | Taux | Description |
|------|---------|------|-------------|
| **DIUS** | Droit Indicatif à l'Usine | 14.6% | Taxe de transformation |
| **DUS** | Droit Unique de Sortie | 5% | Taxe d'exportation |

### 💳 Système de paiement en deux temps

Les formules CCC prévoient un paiement en deux phases :

| Phase | Pourcentage | Moment | Description |
|-------|-------------|--------|-------------|
| **Avant-vente** | 60% | Avant embarquement | Avance versée aux producteurs |
| **Après-vente** | 40% | Après embarquement | Solde après réalisation de la vente |

---

## 3. Rôles et Permissions

### 📊 Groupes d'utilisateurs

Le module définit plusieurs niveaux d'accès :

| Groupe | Description | Accès |
|--------|-------------|-------|
| **Shipping - Utilisateur** | Agent logistique | CV, Contrats, OT (création) |
| **Agent Exportation** | Agent de production | Lots, Productions, Validations |
| **Responsable** | Superviseur | Accès complet, Configuration |
| **Manager** | Direction | Administration, Rapports, API Mobile |

### 📋 Matrice des permissions

| Fonctionnalité | Utilisateur | Agent Export | Responsable | Manager |
|----------------|-------------|--------------|-------------|---------|
| Voir les CV | ✅ | ✅ | ✅ | ✅ |
| Créer des CV | ❌ | ❌ | ✅ | ✅ |
| Créer des contrats | ✅ | ❌ | ✅ | ✅ |
| Créer des OT | ✅ | ❌ | ✅ | ✅ |
| Gérer les lots | ❌ | ✅ | ✅ | ✅ |
| Valider les OT | ❌ | ✅ | ✅ | ✅ |
| Générer des factures | ❌ | ❌ | ✅ | ✅ |
| Accès API Mobile | ❌ | ❌ | ❌ | ✅ |

---

## 4. Confirmations de Vente (CV)

### 📄 Présentation

La **Confirmation de Vente (CV)** est une autorisation délivrée par le Conseil Café-Cacao. Elle définit :
- Le **tonnage maximum** autorisé pour l'exportation
- La **période de validité**
- Le **prix garanti** par le CCC
- Le **type de produit** autorisé

### 📝 Créer une Confirmation de Vente

1. **Menu** : `Potting > Références CCC > Confirmations de Vente > Créer`
2. Remplir les informations :
   - **Référence CCC** : Référence officielle attribuée par le CCC
   - **Campagne** : Saison café-cacao concernée
   - **Date d'émission** : Date du document CCC
   - **Début de validité** : Première date utilisable
   - **Fin de validité** : Date limite d'utilisation
   - **Tonnage autorisé** : Quantité maximale en tonnes
   - **Prix au tonnage** : Prix garanti par tonne
   - **Type de produit** : Masse, Beurre, Cake ou Poudre
3. Cliquer sur **Enregistrer**
4. Cliquer sur **Activer** pour rendre la CV utilisable

### 🔄 États de la CV

| État | Description | Actions possibles |
|------|-------------|-------------------|
| **Brouillon** | CV en cours de création | Modifier, Activer |
| **Active** | CV validée et utilisable | Créer contrats, Annuler |
| **Consommée** | Tonnage entièrement utilisé | Consultation |
| **Expirée** | Date de validité dépassée | Consultation |
| **Annulée** | CV annulée | Consultation |

### 📊 Suivi du tonnage

Le système calcule automatiquement :
- **Tonnage utilisé** : Somme des contrats liés
- **Tonnage restant** : Tonnage autorisé - Tonnage utilisé
- **Progression (%)** : Pourcentage d'utilisation

### ⚠️ Alertes automatiques

| Alerte | Condition | Action recommandée |
|--------|-----------|-------------------|
| 🟡 **Expiration proche** | Moins de 30 jours | Planifier l'utilisation |
| 🔴 **Expirée** | Date dépassée | Demander une nouvelle CV |
| 🟠 **Tonnage épuisé** | Utilisation > 80% | Anticiper nouvelle CV |
| 🔴 **Tonnage atteint** | Restant = 0 | CV devient "Consommée" |

---

## 5. Contrats Clients

### 📄 Présentation

Le **Contrat Client** représente un accord commercial avec un acheteur pour l'exportation de produits cacao. Chaque contrat est **obligatoirement lié à une Confirmation de Vente**.

### 📝 Créer un contrat client

1. **Menu** : `Potting > Commercial > Contrats clients > Créer`
2. Remplir les informations :
   - **Confirmation de Vente** : Sélectionner la CV (obligatoire)
   - **Client** : Sélectionner l'acheteur
   - **Numéro de contrat** : Référence commerciale
   - **Type de produit** : Hérité de la CV ou à définir
   - **Tonnage** : Quantité contractuelle (≤ tonnage CV restant)
   - **Prix unitaire** : Prix par tonne négocié
   - **Date de livraison prévue** : Date cible
3. Optionnel : Ajouter des **certifications** (Fair Trade, Rainforest, etc.)
4. Cliquer sur **Enregistrer**
5. Cliquer sur **Confirmer** pour valider le contrat

### 🔄 États du contrat

| État | Description | Actions possibles |
|------|-------------|-------------------|
| **Brouillon** | Contrat en négociation | Modifier, Confirmer, Annuler |
| **Confirmé** | Contrat validé | Créer OT, Créer Formule |
| **En cours** | Expéditions en cours | Suivi OT, BL |
| **Terminé** | Contrat entièrement exécuté | Consultation, Facturation |
| **Annulé** | Contrat annulé | Consultation |

### 💰 Calculs automatiques

| Champ | Formule |
|-------|---------|
| **Sous-total** | Prix unitaire × Tonnage |
| **Prime certification** | Somme des primes des certifications |
| **Total** | Sous-total + Prime certification |
| **Droits d'exportation** | Total × Taux (ex: 14.6%) |
| **Montant net** | Total - Droits d'exportation |

### 📊 Suivi des OT

Depuis le contrat, vous pouvez voir :
- Nombre d'OT créés
- Tonnage total des OT
- Progression globale des expéditions
- Statut de facturation

---

## 6. Formules (FO)

### 📄 Présentation

La **Formule (FO ou FO1)** est un document du CCC qui fixe le prix d'achat aux producteurs et détaille les taxes et redevances applicables. Chaque formule est liée à une CV et peut être attachée à un OT.

### 📝 Créer une formule

1. **Menu** : `Potting > Références CCC > Formules > Créer`
2. Remplir les informations principales :
   - **Confirmation de Vente** : CV associée (obligatoire)
   - **Référence CCC** : Référence complète (ex: FO1/F025/327/0020/0084)
   - **Numéro FO1** : Numéro court (ex: 22-3276)
   - **Date FO1** : Date d'émission par le CCC
   - **Type de produit** : Produit concerné
3. Informations qualité :
   - **Grade** : GF, F, SS ou Limite
   - **Nomenclature douanière** : Code douanier
4. Informations prix :
   - **Prix au kg** : Prix effectif FCFA/kg
   - **Tonnage** : Quantité couverte
5. Détail des taxes (section dédiée)
6. Configuration du paiement :
   - **Pourcentage avant-vente** : Défaut 60%
7. Cliquer sur **Enregistrer**
8. Cliquer sur **Valider** pour activer la formule

### 🧮 Grades qualité

| Grade | Signification | Description |
|-------|---------------|-------------|
| **GF** | Good Fermented | Qualité supérieure, bien fermenté |
| **F** | Fair Fermented | Qualité standard |
| **SS** | Sub-Standard | Qualité inférieure |
| **LIMIT** | Limite | Qualité limite acceptable |

### 💰 Détail des taxes

La formule inclut le détail de toutes les taxes prélevées :

| Champ | Description |
|-------|-------------|
| **Type de taxe** | Sélection parmi les taxes CCC prédéfinies |
| **Montant/Taux** | Valeur de la taxe |
| **Base de calcul** | Par kg ou pourcentage |
| **Montant calculé** | Taxe × Tonnage |

### 🔄 États de la formule

| État | Description | Actions possibles |
|------|-------------|-------------------|
| **Brouillon** | Formule en saisie | Modifier, Valider |
| **Validée** | Formule active | Lier à un OT |
| **Paiement partiel** | Avant-vente payé | Enregistrer après-vente |
| **Payée** | Tous paiements effectués | Consultation |
| **Annulée** | Formule annulée | Consultation |

### 💳 Gestion des paiements

#### Paiement avant-vente (60%)
1. Ouvrir la formule validée
2. Cliquer sur **Enregistrer paiement avant-vente**
3. Sélectionner le mode de paiement (chèque, virement)
4. Renseigner les informations bancaires
5. Valider

#### Paiement après-vente (40%)
1. Ouvrir la formule en "Paiement partiel"
2. Cliquer sur **Enregistrer paiement après-vente**
3. Compléter les informations
4. Valider

---

## 7. Ordres de Transit (OT)

### 📄 Présentation

L'**Ordre de Transit (OT)** gère l'expédition physique des marchandises. Chaque OT est obligatoirement lié à :
- Un **Contrat client**
- Une **Formule (FO)** validée

L'OT génère automatiquement les **lots** d'empotage en fonction du tonnage.

### 📝 Créer un OT

#### Méthode 1 : Depuis le contrat

1. Ouvrir le contrat confirmé
2. Cliquer sur **Créer OT**
3. Suivre l'assistant de création

#### Méthode 2 : Création directe

1. **Menu** : `Potting > Logistique > Ordres de Transit > Créer`
2. Remplir les informations :
   - **Commande client** : Sélectionner le contrat
   - **Formule (FO)** : Sélectionner une formule validée non utilisée
   - **Campagne** : Saison café-cacao
   - **Destinataire (Consignee)** : Destinataire final
   - **Tonnage** : Quantité à expédier
   - **Type de produit** : Produit à exporter
3. Informations logistiques :
   - **Transitaire** : Agent d'exportation
   - **Navire** : Nom du navire
   - **Port de déchargement (POD)** : Port de destination
   - **Numéro de booking** : Référence de réservation
   - **Taille conteneur** : 20' ou 40'
4. Cliquer sur **Enregistrer**

### 📦 Génération des lots

Après création de l'OT :

1. Cliquer sur **Générer les lots**
2. Le système calcule automatiquement :
   - Nombre de lots selon le tonnage maximum par lot
   - Tonnage cible par lot
   - Numéros de lot séquentiels
3. Les lots sont créés et liés à l'OT

#### Tonnages maximum par défaut

| Produit | Tonnage max/lot | Alternatif |
|---------|-----------------|------------|
| Masse de cacao | 25 T | 20 T |
| Beurre de cacao | 22 T | - |
| Cake de cacao | 25 T | - |
| Poudre de cacao | 22.5 T | - |

### 🔄 États de l'OT

| État | Description | Actions possibles |
|------|-------------|-------------------|
| **Brouillon** | OT en création | Modifier, Générer lots |
| **Lots générés** | Lots créés | Démarrer production |
| **En cours** | Production en cours | Ajouter productions, Créer BL |
| **Prêt validation** | Production terminée | Valider |
| **Validé (Done)** | OT terminé | Facturer |
| **Annulé** | OT annulé | Consultation |

### 📊 Suivi de progression

Le tableau de bord de l'OT affiche :
- **Tonnage cible** vs **Tonnage actuel**
- **Progression (%)** de remplissage
- **Lots empotés** / **Total lots**
- **Statut de livraison** : Non livré / Partiel / Complet
- **Statut de facturation** : Non facturé / Partiel / Complet

---

## 8. Gestion des Lots

### 📄 Présentation

Un **Lot** représente une unité de production à empoter. Chaque lot est lié à un OT et a un tonnage cible défini.

### 📊 Structure d'un lot

| Champ | Description |
|-------|-------------|
| **Numéro de lot** | Référence unique (ex: T10582RA) |
| **Référence de base** | Sans suffixe certification (ex: T10582) |
| **OT** | Ordre de Transit parent |
| **Type de produit** | Masse, Beurre, Cake ou Poudre |
| **Tonnage cible** | Capacité maximale |
| **Tonnage actuel** | Productions enregistrées |
| **Tonnage restant** | Cible - Actuel |
| **Certification** | Fair Trade, Rainforest, etc. |

### 📦 Conditionnement automatique

Le système calcule automatiquement le conditionnement selon le produit :

| Produit | Unité | Poids unitaire | Exemple |
|---------|-------|----------------|---------|
| Masse de cacao | Carton | 25 kg | 10T = 400 cartons |
| Beurre de cacao | Carton | 25 kg | 10T = 400 cartons |
| Cake de cacao | Big bag | 1 000 kg | 10T = 10 big bags |
| Poudre de cacao | Sac | 25 kg | 5T = 200 sacs |

### 📝 Ajouter une production

1. Ouvrir le lot concerné
2. Cliquer sur **Ajouter production**
3. Remplir :
   - **Date de production** : Date effective
   - **Tonnage** : Quantité produite
   - **Numéro de batch** : Référence production (optionnel)
   - **Notes** : Observations
4. Valider

Le tonnage actuel du lot est automatiquement mis à jour.

### 🔄 États du lot

| État | Description | Condition |
|------|-------------|-----------|
| **En cours** | Production en cours | Tonnage actuel < Tonnage cible |
| **Complet** | Production terminée | Tonnage actuel ≥ Tonnage cible |
| **Empoté** | Chargé en conteneur | Lié à un conteneur |
| **Expédié** | Lot expédié | BL validé |

### 🏷️ Certifications

Les lots peuvent porter des certifications qui ajoutent un suffixe au numéro :

| Certification | Suffixe | Exemple |
|---------------|---------|---------|
| Fair Trade | FT | T10582FT |
| Rainforest Alliance | RA | T10582RA |
| UTZ | UTZ | T10582UTZ |
| Bio | BIO | T10582BIO |

---

## 9. Bons de Livraison (BL)

### 📄 Présentation

Le **Bon de Livraison (BL)** est le document qui formalise l'expédition des lots vers le client. Chaque BL est lié à un OT et contient un ou plusieurs lots.

### 📝 Créer un bon de livraison

#### Méthode 1 : Depuis l'OT

1. Ouvrir l'OT en cours ou terminé
2. Cliquer sur **Créer BL**
3. Sélectionner les lots à inclure
4. Compléter les informations
5. Valider

#### Méthode 2 : Création directe

1. **Menu** : `Potting > Logistique > Bons de Livraison > Créer`
2. Remplir :
   - **Ordre de Transit** : OT concerné
   - **Date de livraison** : Date effective
   - **Lots** : Sélectionner les lots à livrer
3. Informations complémentaires :
   - **Conteneur** : Numéro du conteneur
   - **Plombs** : Numéros de scellés
   - **Notes** : Observations
4. Valider

### 📊 Informations du BL

Le BL hérite automatiquement des informations de l'OT :
- Client et destinataire
- Navire et port de destination
- Numéro de booking
- Produit et tonnage

### 🔄 États du BL

| État | Description | Actions possibles |
|------|-------------|-------------------|
| **Brouillon** | BL en création | Modifier, Confirmer |
| **Confirmé** | BL validé | Expédier |
| **Expédié** | Marchandise partie | Consultation |
| **Annulé** | BL annulé | Consultation |

### 📋 Documents générés

Depuis le BL, vous pouvez générer :
- **Bon de livraison PDF** : Document officiel
- **Packing list** : Liste de colisage
- **Documents douaniers** : Formulaires d'export

---

## 10. Facturation

### 📄 Présentation

Le module permet de générer des **factures clients** directement depuis les OT. La facturation partielle est supportée.

### 📝 Générer une facture

1. Ouvrir l'OT validé (état "Done")
2. Cliquer sur **Créer Facture**
3. Vérifier les informations :
   - Client et adresse de facturation
   - Produit et quantité
   - Prix unitaire et montant
   - Taxes applicables
4. Cliquer sur **Créer**

La facture est créée en brouillon dans le module Comptabilité.

### 💰 Facturation partielle

Il est possible de facturer partiellement un OT :

1. Lors de la création de facture, modifier le tonnage
2. Le système enregistre le tonnage facturé
3. Les factures suivantes porteront sur le reste

### 📊 Suivi de facturation

Pour chaque OT, le système affiche :
- **Tonnage facturé** : Quantité déjà facturée
- **Reste à facturer** : Quantité non facturée
- **Progression facturation (%)** : Pourcentage facturé
- **Nombre de factures** : Total des factures générées

### 🔗 Lien avec la comptabilité

Les factures générées sont intégrées au module comptable Odoo :
- Numérotation automatique
- Intégration journal des ventes
- Suivi des paiements
- Relances clients

---

## 11. Transitaires et Paiements

### 📄 Présentation

Le module gère les **transitaires** (agents d'exportation) et leurs **frais**.

### 📝 Créer un transitaire

1. **Menu** : `Potting > Configuration > Transitaires > Créer`
2. Remplir :
   - **Nom** : Raison sociale
   - **Contact** : Personne à contacter
   - **Téléphone** / **Email**
   - **Adresse**
   - **Tarif par tonne** : Frais standard
   - **Compte bancaire** : Pour les paiements
3. Enregistrer

### 💰 Calcul des frais

Les frais transitaire sont calculés automatiquement sur chaque OT :

```
Frais = Tarif par tonne × Tonnage OT
```

### 💳 Paiements des transitaires

Le module permet de suivre les paiements aux transitaires :

1. Depuis le transitaire, voir tous les OT associés
2. Calculer le montant dû
3. Créer un paiement (intégration avec `bank_payment_management`)
4. Suivre le statut du paiement

---

## 12. Campagnes Café-Cacao

### 📄 Présentation

Une **Campagne café-cacao** représente une saison d'exportation, généralement d'octobre à septembre de l'année suivante.

### 📝 Créer une campagne

1. **Menu** : `Potting > Configuration > Campagnes > Créer`
2. Remplir :
   - **Nom** : Ex: "Campagne 2025-2026"
   - **Date de début** : Début de la saison
   - **Date de fin** : Fin de la saison
   - **Description** : Notes
3. Enregistrer
4. **Activer** la campagne pour la rendre utilisable

### 🔄 États de la campagne

| État | Description |
|------|-------------|
| **Brouillon** | En préparation |
| **Active** | Campagne en cours |
| **Terminée** | Campagne clôturée |

### 📊 Statistiques par campagne

Pour chaque campagne, le système calcule :
- Total des CV émises
- Total des contrats
- Tonnage total exporté
- Répartition par produit
- Répartition par client

---

## 13. Certifications

### 📄 Présentation

Le module gère les **certifications** de durabilité applicables aux produits cacao.

### 🏷️ Certifications disponibles

| Certification | Code | Suffixe | Prime (FCFA/T) |
|---------------|------|---------|----------------|
| Fair Trade | FAIRTRADE | FT | Variable |
| Rainforest Alliance | RA | RA | Variable |
| UTZ Certified | UTZ | UTZ | Variable |
| Biologique | BIO | BIO | Variable |

### 📝 Configurer les certifications

1. **Menu** : `Potting > Configuration > Certifications`
2. Modifier ou créer une certification :
   - **Nom** : Nom complet
   - **Code** : Code court
   - **Suffixe** : Ajouté aux numéros de lot
   - **Prime** : Montant par tonne
   - **Description** : Détails
3. Enregistrer

### 💰 Impact sur les prix

Les primes de certification sont ajoutées au prix de vente :

```
Prix total = (Prix unitaire × Tonnage) + (Prime certification × Tonnage)
```

---

## 14. Tableaux de Bord

Le module propose deux tableaux de bord OWL interactifs.

### 📊 Tableau de bord Commercial (Shipping)

**Menu** : `Potting > Tableaux de bord > Commercial`

#### Indicateurs affichés

| Indicateur | Description |
|------------|-------------|
| **Contrats** | Par état (brouillon, confirmé, en cours, terminé) |
| **CV actives** | Confirmations de Vente utilisables |
| **CV expirées** | CV ayant dépassé leur validité |
| **CV expirant bientôt** | CV expirant dans moins de 30 jours |
| **Formules** | En attente de paiement / Payées |
| **Tonnage par produit** | Répartition des exportations |
| **Top clients** | Clients par volume |

### 📊 Tableau de bord Expédition (Agent)

**Menu** : `Potting > Tableaux de bord > Expédition`

#### Indicateurs affichés

| Indicateur | Description |
|------------|-------------|
| **OT en cours** | Ordres de Transit actifs |
| **Lots à empoter** | Lots en attente de production |
| **Progression empotages** | Pourcentage de complétion |
| **BL en attente** | Bons de livraison à créer |
| **Productions du jour** | Tonnage produit aujourd'hui |

### 🔄 Filtres disponibles

Les deux tableaux de bord permettent de filtrer par :
- Période (date de/à)
- Campagne
- Type de produit
- Client
- État

---

## 15. API Mobile (PDG)

### 📱 Présentation

Le module inclut une **API REST** permettant au PDG de consulter les activités d'exportation depuis une application mobile.

**Base URL** : `/api/v1/potting`  
**Authentification** : Bearer Token  
**Format** : JSON

### 🔐 Authentification

```http
POST /api/v1/potting/auth/login
Content-Type: application/json

{
    "login": "pdg@icp.ci",
    "password": "mot_de_passe"
}
```

**Réponse** :
```json
{
    "success": true,
    "data": {
        "token": "eyJ...",
        "expires_at": "2026-01-20T12:00:00",
        "user": {
            "id": 2,
            "name": "PDG ICP",
            "roles": ["manager"]
        }
    }
}
```

### 📋 Endpoints principaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/login` | Connexion |
| POST | `/auth/logout` | Déconnexion |
| GET | `/dashboard` | Tableau de bord global |
| GET | `/dashboard/transit-orders` | Liste des OT |
| GET | `/transit-orders/{id}` | Détail d'un OT |
| GET | `/reports/daily` | Rapport quotidien |
| GET | `/reports/daily/download` | Télécharger PDF |

### 📊 Données du dashboard

L'endpoint `/dashboard` retourne :

```json
{
    "summary": {
        "total_transit_orders": 45,
        "total_tonnage": 1250.5,
        "current_tonnage": 980.3,
        "average_progress": 78.4
    },
    "transit_orders_by_state": {
        "done": 20,
        "in_progress": 15,
        "ready_validation": 10
    },
    "by_product_type": {
        "cocoa_mass": { "count": 15, "tonnage": 450.0 },
        "cocoa_butter": { "count": 12, "tonnage": 380.0 }
    },
    "top_customers": [
        { "name": "Cargill", "count": 10, "tonnage": 350.0 }
    ]
}
```

### 📖 Documentation complète

Voir le fichier [MOBILE_API_DOCUMENTATION.md](./MOBILE_API_DOCUMENTATION.md) pour la documentation détaillée.

---

## 16. Rapports et Envoi par Email

### 📊 Rapports disponibles

| Rapport | Description | Format |
|---------|-------------|--------|
| **Rapport OT** | Détail d'un Ordre de Transit | PDF |
| **Rapport quotidien** | Synthèse journalière | PDF |
| **Rapport par contrat** | Synthèse par commande | PDF |
| **État des CV** | Liste des CV avec statuts | Excel |
| **État des formules** | Formules et paiements | Excel |

### 🖨️ Générer un rapport

1. Ouvrir l'enregistrement concerné (OT, Contrat, etc.)
2. **Imprimer > [Nom du rapport]**
3. Le PDF est généré et téléchargé

### 📧 Envoi par email

Le module permet d'envoyer automatiquement les rapports par email :

#### Configurer les destinataires

1. **Menu** : `Potting > Configuration > Paramètres`
2. Définir :
   - **Email PDG** : Destinataire principal
   - **Emails en copie** : Liste des personnes en CC
3. Enregistrer

#### Envoyer un rapport

1. Ouvrir l'OT ou le rapport
2. Cliquer sur **Envoyer par email**
3. Vérifier les destinataires
4. Personnaliser le message (optionnel)
5. Envoyer

#### Envoi automatique

Le système peut être configuré pour envoyer automatiquement :
- Le rapport quotidien chaque soir
- Les alertes CV expirant

---

## 17. Configuration

### ⚙️ Paramètres généraux

**Menu** : `Potting > Configuration > Paramètres`

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| **Client par défaut** | Pré-sélection lors de création | - |
| **Taux droits export** | Pourcentage standard | 14.6% |
| **Devise par défaut** | Devise des transactions | XOF |
| **Email PDG** | Destinataire rapports | - |
| **Emails en copie** | CC pour les rapports | - |

### 📦 Tonnages maximum par lot

| Produit | Champ | Défaut |
|---------|-------|--------|
| Masse de cacao | Tonnage max | 25 T |
| Beurre de cacao | Tonnage max | 22 T |
| Cake de cacao | Tonnage max | 25 T |
| Poudre de cacao | Tonnage max | 22.5 T |

### 🔢 Séquences

Les séquences sont configurables pour :
- Numéros de CV
- Numéros de contrat
- Numéros d'OT
- Numéros de lot
- Numéros de BL
- Numéros de formule

**Menu** : `Paramètres > Technique > Séquences`

---

## 18. FAQ et Support

### ❓ Questions fréquentes

#### CV et Contrats

**Q : Je ne trouve pas de CV disponible pour mon contrat ?**
> ✅ Vérifiez que la CV est à l'état "Active", n'est pas expirée, et a du tonnage restant.

**Q : Le tonnage du contrat dépasse le tonnage CV restant ?**
> ✅ Réduisez le tonnage du contrat ou utilisez une autre CV avec plus de capacité.

**Q : Comment annuler un contrat confirmé ?**
> ✅ Seul un Responsable peut annuler un contrat. Les OT liés doivent être annulés d'abord.

#### Formules

**Q : Je ne peux pas lier une formule à mon OT ?**
> ✅ La formule doit être à l'état "Validée" et ne pas être déjà liée à un autre OT.

**Q : Comment enregistrer un paiement partiel ?**
> ✅ Utilisez les boutons "Paiement avant-vente" puis "Paiement après-vente" dans l'ordre.

#### OT et Lots

**Q : Les lots ne se génèrent pas ?**
> ✅ Vérifiez que le tonnage de l'OT est > 0 et que le type de produit est défini.

**Q : Comment modifier le tonnage d'un lot ?**
> ✅ Les lots générés ne peuvent pas être modifiés. Supprimez-les et régénérez.

**Q : Le total des lots ne correspond pas au tonnage OT ?**
> ✅ Normal si le tonnage n'est pas divisible exactement par le tonnage max par lot.

#### Facturation

**Q : Le bouton "Créer Facture" n'apparaît pas ?**
> ✅ L'OT doit être à l'état "Validé" (Done) pour pouvoir facturer.

**Q : Comment facturer partiellement ?**
> ✅ Lors de la création de facture, modifiez le tonnage à facturer avant de valider.

### 📞 Support technique

- 📧 **Email** : support@ivorycocoa.ci
- 📞 **Téléphone** : +225 XX XX XX XX
- 🌐 **Site web** : https://www.ivorycocoa.ci
- 📝 **Tickets** : Créer un ticket dans `Helpdesk > Nouveau Ticket`

---

## 📚 Annexes

### A. Glossaire

| Terme | Définition |
|-------|------------|
| **CCC** | Conseil du Café-Cacao de Côte d'Ivoire |
| **CV** | Confirmation de Vente |
| **FO / FO1** | Formule (document de fixation des prix) |
| **OT** | Ordre de Transit |
| **BL** | Bon de Livraison |
| **POD** | Port of Discharge (Port de déchargement) |
| **DIUS** | Droit Indicatif à l'Usine |
| **DUS** | Droit Unique de Sortie |
| **FIMR** | Fonds d'Investissement en Milieu Rural |

### B. Codes produits

| Code | Produit | Type |
|------|---------|------|
| `cocoa_mass` | Masse de cacao | Semi-fini |
| `cocoa_butter` | Beurre de cacao | Semi-fini |
| `cocoa_cake` | Cake/Tourteau de cacao | Semi-fini |
| `cocoa_powder` | Poudre de cacao | Semi-fini |

### C. Nomenclatures douanières

| Code | Produit |
|------|---------|
| 1803 10 00 00 | Pâte de cacao non dégraissée |
| 1803 20 00 00 | Pâte de cacao dégraissée |
| 1804 00 00 00 | Beurre, graisse et huile de cacao |
| 1802 00 00 00 | Coques, pellicules et déchets de cacao |

### D. Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Alt + C` | Créer un nouvel enregistrement |
| `Alt + E` | Modifier l'enregistrement |
| `Alt + S` | Sauvegarder |
| `Alt + D` | Supprimer |
| `Alt + Q` | Annuler |

---

> **Module Gestion des Exportations (Potting Management)** - Version 17.0.1.3.0  
> Développé avec ❤️ par **ICP - Ivory Cocoa Products** pour **Odoo 17**  
> *Dernière mise à jour : Janvier 2026*
