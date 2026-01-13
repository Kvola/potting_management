# Guide Utilisateur - Module Potting Management

## 📋 Vue d'ensemble

Le module **Potting Management** est un système complet de gestion des opérations d'exportation de produits semi-finis du cacao pour les entreprises de transformation en Côte d'Ivoire. Il gère l'ensemble du processus depuis les autorisations du Conseil Café-Cacao (CCC) jusqu'à la facturation des exportations.

### Principaux flux de travail

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Confirmation de │───▶│   Contrat       │───▶│    Formule      │
│   Vente (CV)    │    │   Client        │    │     (FO)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Facture      │◀───│  Bon de         │◀───│  Ordre de       │
│                 │    │  Livraison (BL) │    │  Transit (OT)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 📚 Concepts clés

### 1. Confirmation de Vente (CV)

La **Confirmation de Vente** est une autorisation délivrée par le Conseil Café-Cacao (CCC) de Côte d'Ivoire. Elle définit :
- Le tonnage maximum autorisé pour l'exportation
- La période de validité
- Le prix garanti par le CCC
- Le type de produit autorisé

**États possibles :**
| État | Description |
|------|-------------|
| Brouillon | CV en cours de création |
| Active | CV validée et utilisable |
| Consommée | Tonnage entièrement utilisé |
| Expirée | Date de validité dépassée |
| Annulée | CV annulée |

**Bonnes pratiques :**
- Créer une CV dès réception de l'autorisation du CCC
- Surveiller régulièrement les CV qui expirent bientôt (alertes à 30 jours)
- Ne pas dépasser le tonnage autorisé

---

### 2. Contrat Client

Le **Contrat Client** représente un accord commercial avec un acheteur pour l'exportation de produits cacao. Il est obligatoirement lié à une Confirmation de Vente.

**Caractéristiques :**
- Tonnage contractuel
- Prix unitaire par tonne
- Droits d'exportation (généralement 14.6%)
- Date de livraison prévue

**États possibles :**
| État | Description |
|------|-------------|
| Brouillon | Contrat en cours de négociation |
| Confirmé | Contrat validé |
| En cours | Expéditions en cours |
| Terminé | Contrat entièrement exécuté |
| Annulé | Contrat annulé |

---

### 3. Formule (FO)

La **Formule** (aussi appelée FO ou FO1) est un document du CCC qui fixe le prix d'achat aux producteurs et détaille les taxes et redevances applicables.

**Informations clés :**
- Numéro FO1 (référence CCC)
- Prix au kilogramme (FCFA/kg)
- Tonnage concerné
- Détail des taxes prélevées

**Système de taxes CCC :**
| Code | Libellé | Type |
|------|---------|------|
| CCC | Redevance Conseil Café-Cacao | FCFA/kg |
| DIUS | Droit Indicatif à l'Usine | % |
| FIMR | Fonds d'Investissement en Milieu Rural | FCFA/kg |
| SACHERIE | Redevance sacherie | FCFA/kg |
| DUS | Droit Unique de Sortie | % |
| FDPCC | Fonds de Développement Café-Cacao | FCFA/kg |

**Paiement en deux phases :**
1. **Avant-vente (60%)** : Payé avant l'embarquement
2. **Après-vente (40%)** : Payé après l'embarquement

---

### 4. Ordre de Transit (OT)

L'**Ordre de Transit** gère l'expédition physique des marchandises. Chaque OT est lié à une Formule et génère des lots d'empotage.

**Caractéristiques :**
- Tonnage à expédier
- Navire et port de destination
- Numéro de booking
- Transitaire responsable

**Génération des lots :**
L'OT génère automatiquement des lots en fonction du tonnage et du type d'emballage (cartons, sacs).

---

## 🔄 Flux de travail typique

### Étape 1 : Réception d'une Confirmation de Vente

1. Aller dans **Potting > Références CCC > Confirmations de Vente**
2. Cliquer sur **Créer**
3. Remplir les informations :
   - Référence CCC officielle
   - Campagne café-cacao
   - Dates de validité
   - Tonnage autorisé
   - Prix au tonnage
4. Cliquer sur **Activer** pour rendre la CV utilisable

### Étape 2 : Création d'un contrat client

1. Aller dans **Potting > Commercial > Contrats clients**
2. Cliquer sur **Créer**
3. Sélectionner la **Confirmation de Vente**
4. Choisir le **Client** et le **Type de produit**
5. Définir le **Tonnage** et le **Prix unitaire**
6. Cliquer sur **Confirmer**

### Étape 3 : Création d'une Formule

1. Depuis le contrat, cliquer sur **Créer Formule** ou
2. Aller dans **Potting > Références CCC > Formules**
3. Lier la formule à la CV correspondante
4. Saisir les informations du document FO1 :
   - Numéro FO1
   - Prix au kg
   - Taxes applicables
5. Cliquer sur **Valider**

### Étape 4 : Création d'un Ordre de Transit

1. Depuis le contrat, cliquer sur **Créer OT** ou
2. Aller dans **Potting > Logistique > Ordres de Transit**
3. Lier l'OT au contrat et à la formule
4. Saisir les informations d'expédition :
   - Tonnage
   - Transitaire
   - Navire
   - Port de destination
5. Cliquer sur **Générer les lots**

### Étape 5 : Empotage et livraison

1. Suivre l'empotage des lots
2. Créer les **Bons de Livraison** pour les lots prêts
3. Valider les BL une fois les marchandises expédiées

### Étape 6 : Facturation

1. Depuis l'OT, cliquer sur **Créer Facture**
2. Vérifier les montants
3. Valider et envoyer la facture

---

## 📊 Tableaux de bord

### Dashboard Commercial

Accessible via **Potting > Tableaux de bord > Commercial**

**Indicateurs disponibles :**
- État des contrats (brouillon, confirmé, en cours, terminé)
- Statistiques CV (actives, consommées, expirées, expirant bientôt)
- Statistiques Formules (en attente de paiement, payées)
- Tonnage par type de produit
- Top clients

### Dashboard Expédition

Accessible via **Potting > Tableaux de bord > Expédition**

**Indicateurs disponibles :**
- OT en cours
- Lots à empoter
- Progression des empotages
- Bons de livraison en attente

---

## ⚙️ Configuration

### Types de taxes

Les types de taxes sont préconfigurés mais peuvent être modifiés via :
**Potting > Configuration > Types de Taxes**

### Campagnes

Une campagne café-cacao représente une saison d'exportation (généralement octobre à septembre).
**Potting > Configuration > Campagnes**

### Transitaires

Gérer les transitaires responsables des expéditions :
**Potting > Configuration > Transitaires**

---

## ⚠️ Alertes et notifications

Le système affiche des alertes visuelles :

- **CV expirant bientôt** : Alerte jaune si expiration dans moins de 30 jours
- **CV expirée** : Ruban rouge sur la fiche
- **Tonnage épuisé** : Alerte rouge si tonnage CV à 0
- **Tonnage presque épuisé** : Alerte si utilisation > 80%

---

## 🔐 Droits d'accès

| Groupe | Description |
|--------|-------------|
| Potting / Utilisateur | Accès en lecture, création de base |
| Potting / Responsable | Validation, modification, suppression |
| Potting / Manager | Administration complète |

---

## 📝 Conseils et astuces

1. **Anticipez les CV** : Demandez de nouvelles CV avant l'expiration des actuelles
2. **Vérifiez les taxes** : Assurez-vous que les taxes FO correspondent au document officiel
3. **Utilisez les filtres** : Les vues liste ont des filtres prédéfinis pratiques
4. **Suivez le dashboard** : Consultez régulièrement le tableau de bord commercial
5. **Exportez les données** : Utilisez les exports Excel pour vos rapports

---

## 🆘 Support

Pour toute question ou problème :
- Consultez d'abord ce guide
- Vérifiez les messages d'erreur affichés
- Contactez votre administrateur système

---

*Module Potting Management v17.0.1.3.0*
*Dernière mise à jour : Janvier 2025*
