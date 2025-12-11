# Gestion des Empotages (Potting Management)

Module Odoo 17 pour la gestion des empotages de produits semi-finis du cacao.

## Description

Ce module permet de gérer le flux complet d'empotage des produits semi-finis du cacao :
- Masse de cacao (Cocoa Mass/Liquor)
- Beurre de cacao (Cocoa Butter)
- Cake/Tourteau de cacao (Cocoa Cake)
- Poudre de cacao (Cocoa Powder)

## Fonctionnalités

### 1. Gestion des commandes clients
- Création de commandes avec client par défaut configurable
- Suivi de l'état des commandes (Brouillon → Confirmée → En cours → Terminée)
- Vue d'ensemble des Ordres de Transit associés

### 2. Gestion des Ordres de Transit (OT)
- Création des OT avec informations complètes (destinataire, produit, tonnage, navire, port...)
- Génération automatique des lots selon le tonnage et le type de produit
- Suivi de la progression (lots empotés / total)

### 3. Gestion des lots
- Calcul automatique du nombre de lots selon les tonnages maximum configurés
- Suivi du remplissage en temps réel
- Gestion des lignes de production
- Empotage dans les conteneurs
- **Calcul automatique du conditionnement** (cartons, big bags, sacs)

### 4. Gestion des conteneurs
- Création et suivi des conteneurs
- Association des lots aux conteneurs
- Suivi des états (Disponible → En chargement → Chargé → Expédié)

### 5. Rapports
- Rapport par OT (PDF)
- Rapport de synthèse par commande
- Envoi automatique par email au PDG avec copies configurables

### 6. Tableaux de bord OWL
- **Tableau de bord Shipping** : Vue d'ensemble des commandes et OT
- **Tableau de bord Agent PDG** : Gestion des productions et validations

## Configuration

### Conditionnement par type de produit

Le module gère automatiquement le conditionnement selon le type de produit :

| Produit | Type de conditionnement | Poids unitaire |
|---------|------------------------|----------------|
| **Masse de cacao** | Cartons | 25 kg |
| **Beurre de cacao** | Cartons | 25 kg |
| **Cake de cacao** | Big bags | 1 tonne (1000 kg) |
| **Poudre de cacao** | Sacs | 25 kg |

Le calcul du nombre d'unités est automatique :
- **Exemple Masse** : 10 tonnes = 400 cartons (10000 kg ÷ 25 kg)
- **Exemple Cake** : 10 tonnes = 10 big bags (10 T ÷ 1 T)
- **Exemple Poudre** : 5 tonnes = 200 sacs (5000 kg ÷ 25 kg)

### Tonnages maximum par défaut
- Masse de cacao : 25 T (alternatif : 20 T)
- Beurre de cacao : 22 T
- Cake de cacao : 25 T
- Poudre de cacao : 22.5 T

Ces valeurs sont configurables dans les paramètres du module.

### Client par défaut
Configurable dans les paramètres pour être automatiquement sélectionné lors de la création d'une commande.

### Destinataires en copie
Liste configurable des personnes à mettre en copie lors de l'envoi des rapports au PDG.

## Groupes d'utilisateurs

1. **Shipping - Utilisateur** : Création et gestion des commandes et OT
2. **Agent PDG** : Gestion des lots, productions et validations
3. **Responsable** : Accès complet au module

## Installation

1. Placer le module dans le dossier addons d'Odoo
2. Mettre à jour la liste des applications
3. Installer le module "Gestion des Empotages"
4. Configurer les paramètres selon vos besoins

## Données de démonstration

Le module inclut des données de démonstration avec :
- Partenaires (Barry Brasil, Barry USA, Barry Asia)
- Commandes clients
- Ordres de Transit
- Lots et productions

## Dépendances

- base
- mail
- product
- stock

## Auteur

ICP

## Licence

LGPL-3
