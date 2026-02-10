# Documentation Technique - Module Potting Management

## 🏗️ Architecture du Module

### Structure des répertoires

```
potting_management/
├── __init__.py
├── __manifest__.py
├── models/                    # Modèles Python
│   ├── potting_campaign.py           # Campagnes café-cacao
│   ├── potting_confirmation_vente.py # Confirmations de Vente (CV)
│   ├── potting_customer_order.py     # Contrats clients
│   ├── potting_formule.py            # Formules (FO) et Taxes
│   ├── potting_transit_order.py      # Ordres de Transit (OT)
│   ├── potting_lot.py                # Lots d'empotage
│   ├── potting_container.py          # Conteneurs
│   ├── potting_delivery_note.py      # Bons de livraison
│   └── ...
├── views/                     # Vues XML
├── wizards/                   # Assistants (transients)
├── reports/                   # Rapports QWeb
├── security/                  # Droits d'accès
│   ├── security.xml
│   └── ir.model.access.csv
├── data/                      # Données de référence
│   └── potting_cv_fo_data.xml        # Types de taxes
├── static/src/                # Assets frontend
│   ├── js/                           # Composants OWL
│   ├── xml/                          # Templates OWL
│   └── css/                          # Styles
├── tests/                     # Tests unitaires
│   ├── test_potting_formule.py
│   ├── test_potting_confirmation_vente.py
│   ├── test_potting_customer_order.py
│   ├── test_potting_transit_order.py
│   └── test_potting_workflow.py
└── docs/                      # Documentation
    ├── GUIDE_UTILISATEUR.md
    └── DOCUMENTATION_TECHNIQUE.md
```

---

## 📊 Diagramme des modèles

```
┌──────────────────────────────────────────────────────────────────┐
│                        potting.campaign                          │
│  (Campagne café-cacao - ex: 2024-2025)                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              potting.confirmation.vente (CV)                     │
│  - reference_ccc          - tonnage_autorise                    │
│  - date_start/end         - tonnage_utilise (computed)          │
│  - prix_tonnage           - state (draft/active/consumed/expired)│
└──────────────────────────────────────────────────────────────────┘
                │                              │
                ▼                              ▼
┌───────────────────────────┐    ┌───────────────────────────────────┐
│  potting.customer.order   │    │       potting.formule (FO)        │
│  (Contrat client)         │    │  - numero_fo1        - prix_kg    │
│  - contract_tonnage       │    │  - tonnage           - taxes      │
│  - unit_price             │◀──▶│  - state (draft/validated/paid)   │
│  - export_duty_rate       │    │  - avant_vente_paye              │
└───────────────────────────┘    │  - apres_vente_paye              │
                │                └───────────────────────────────────┘
                │                              │
                ▼                              │
┌───────────────────────────┐                  │
│  potting.transit.order    │◀─────────────────┘
│  (Ordre de Transit - OT)  │
│  - tonnage                │
│  - formule_id             │
│  - vessel_id              │
│  - booking_number         │
└───────────────────────────┘
                │
                ▼
┌───────────────────────────┐
│      potting.lot          │
│  (Lot d'empotage)         │
│  - current_tonnage        │
│  - container_id           │
│  - state                  │
└───────────────────────────┘
```

---

## 🔧 Modèles principaux

### potting.confirmation.vente

**Héritage :** `mail.thread`, `mail.activity.mixin`

**Champs clés :**
```python
name = fields.Char("Numéro CV")                    # Auto-généré
reference_ccc = fields.Char("Référence CCC")       # Unique
campaign_id = fields.Many2one('potting.campaign')
tonnage_autorise = fields.Float("Tonnage autorisé")
tonnage_utilise = fields.Float(compute='_compute_tonnage_utilise')
tonnage_restant = fields.Float(compute='_compute_tonnage_utilise')
prix_tonnage = fields.Monetary("Prix/tonne")
state = fields.Selection(['draft', 'active', 'consumed', 'expired', 'cancelled'])
```

**Contraintes SQL :**
- `name_uniq` : Numéro unique par société
- `reference_ccc_uniq` : Référence CCC unique
- `tonnage_positive` : Tonnage > 0
- `date_coherence` : date_start <= date_end

**Méthodes principales :**
- `check_can_use_tonnage(tonnage)` : Vérifie disponibilité
- `get_utilization_status()` : Retourne statut utilisation
- `action_extend_validity()` : Prolonge validité d'un mois
- `_cron_check_expiration()` : Vérifie expirations (cron)

---

### potting.formule

**Héritage :** `mail.thread`, `mail.activity.mixin`

**Champs clés :**
```python
name = fields.Char("Numéro")                       # Auto-généré
numero_fo1 = fields.Char("Numéro FO1")             # Ex: "EGY060"
confirmation_vente_id = fields.Many2one('potting.confirmation.vente')
product_type = fields.Selection([...])             # Type de produit
prix_kg = fields.Monetary("Prix/kg")
prix_tonnage = fields.Monetary(compute='_compute_prix_tonnage')
tonnage = fields.Float("Tonnage")
taxe_ids = fields.One2many('potting.formule.taxe') # Lignes de taxes
montant_net = fields.Monetary(compute='...')       # Après taxes
avant_vente_paye = fields.Boolean()                # Phase 1 (60%)
apres_vente_paye = fields.Boolean()                # Phase 2 (40%)
```

**Relations :**
- `confirmation_vente_id` → `potting.confirmation.vente`
- `transit_order_id` → `potting.transit.order` (One2One)
- `taxe_ids` → `potting.formule.taxe` (One2Many)

**Modèle lié : potting.formule.taxe**
```python
formule_id = fields.Many2one('potting.formule')
taxe_type_id = fields.Many2one('potting.taxe.type')
taux_pourcentage = fields.Float("Taux %")
taux_fcfa_kg = fields.Float("Taux FCFA/kg")
montant = fields.Monetary(compute='_compute_montant')
```

---

### potting.customer.order

**Champs clés :**
```python
confirmation_vente_id = fields.Many2one('potting.confirmation.vente')
customer_id = fields.Many2one('res.partner')
contract_tonnage = fields.Float("Tonnage contrat")
unit_price = fields.Monetary("Prix unitaire/T")
export_duty_rate = fields.Float("Taux droits export %")
total_amount = fields.Monetary(compute='...')
transit_order_ids = fields.One2many('potting.transit.order')
```

**Contraintes :**
- Tonnage ne peut pas dépasser le disponible sur la CV
- Type de produit doit correspondre à la CV
- Prix unitaire doit être positif

---

### potting.transit.order

**Champs clés :**
```python
customer_order_id = fields.Many2one('potting.customer.order')
formule_id = fields.Many2one('potting.formule')  # Unique
tonnage = fields.Float()
vessel_id = fields.Many2one('potting.vessel')
booking_number = fields.Char()
lot_ids = fields.One2many('potting.lot')
export_duty_collected = fields.Boolean()
export_allowed = fields.Boolean(compute='...')
```

**Contrainte clé :** Une Formule ne peut être liée qu'à un seul OT.

---

## 🧪 Tests

### Exécution des tests

```bash
# Tous les tests du module
./odoo-bin -c odoo.conf --test-enable --stop-after-init -d test_db -i potting_management

# Tests spécifiques (par tag)
./odoo-bin -c odoo.conf --test-enable --test-tags potting_formule -d test_db

# Tags disponibles
# - potting
# - potting_formule
# - potting_cv
# - potting_customer_order
# - potting_transit_order
# - potting_workflow
```

### Structure d'un test

```python
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError

@tagged('potting', 'potting_cv', '-at_install', 'post_install')
class TestPottingConfirmationVente(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Créer données de test
        cls.campaign = cls.env['potting.campaign'].create({...})
    
    def test_01_create_cv(self):
        cv = self.env['potting.confirmation.vente'].create({...})
        self.assertEqual(cv.state, 'draft')
    
    def test_02_constraint_tonnage(self):
        with self.assertRaises(ValidationError):
            self.env['potting.confirmation.vente'].create({
                'tonnage_autorise': -100,  # Invalide
            })
```

---

## 🎨 Composants Frontend (OWL)

### Dashboard Commercial

**Fichier JS :** `static/src/js/commercial_dashboard.js`

```javascript
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

export class PottingCommercialDashboard extends Component {
    static template = "potting_management.CommercialDashboard";
    
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            contracts: {},
            cvStats: {},
            formuleStats: {},
        });
        onWillStart(() => this.loadData());
    }
    
    async loadData() {
        // Charger statistiques via ORM
        const cvCount = await this.orm.searchCount(
            "potting.confirmation.vente", 
            [['state', '=', 'active']]
        );
        this.state.cvStats.active = cvCount;
    }
}

registry.category("actions").add("potting_commercial_dashboard", PottingCommercialDashboard);
```

**Template XML :** `static/src/xml/commercial_dashboard.xml`

---

## 🔄 Workflows et états

### Workflow CV

```
[draft] ──action_activate──▶ [active]
   │                           │
   │                           ├──action_consume──▶ [consumed]
   │                           │
   │                           └──action_expire──▶ [expired]
   │
   └──action_cancel──▶ [cancelled] ──action_draft──▶ [draft]
```

### Workflow Formule

```
[draft] ──action_validate──▶ [validated] ──paiement_producteurs──▶ [paid]
   │
   └──action_cancel──▶ [cancelled]
```

**Note:** Le paiement aux producteurs est de 100% du prix bord champ.
Le DUS (Droit Unique de Sortie) est géré séparément sur l'Ordre de Transit après la vente.

### Workflow OT

```
[draft] ──generate_lots──▶ [lots_generated] ──action_start──▶ [in_progress]
   │                                                              │
   │                                                              └──action_validate──▶ [done]
   │
   └──action_cancel──▶ [cancelled]
```

---

## 📋 Données de référence

### Types de taxes (potting.taxe.type)

Définis dans `data/potting_cv_fo_data.xml` :

| Code | Nom | Catégorie | Taux par défaut |
|------|-----|-----------|-----------------|
| CCC | Redevance CCC | Redevance | 1.245 FCFA/kg |
| INVEST_AGRI | Investissement Agricole | Redevance | - |
| FIMR | Fonds Investissement Rural | Redevance | - |
| SACHERIE | Redevance Sacherie | Redevance | - |
| DIUS | Droit Indicatif Usine | Taxe | 14.6% |
| DUS | Droit Unique de Sortie | Taxe | - |
| FDPCC | Fonds Développement | Redevance | - |

---

## 🔐 Sécurité

### Groupes définis

```xml
<record id="group_potting_user" model="res.groups">
    <field name="name">Potting / Utilisateur</field>
</record>

<record id="group_potting_manager" model="res.groups">
    <field name="name">Potting / Manager</field>
</record>
```

### Règles d'accès (ir.model.access.csv)

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_potting_cv_user,potting.confirmation.vente.user,model_potting_confirmation_vente,group_potting_user,1,1,1,0
access_potting_cv_manager,potting.confirmation.vente.manager,model_potting_confirmation_vente,group_potting_manager,1,1,1,1
```

---

## 📦 Dépendances

### Modules Odoo requis

- `base`
- `mail`
- `product`
- `account`

### Modules ICP requis

- `validation_generic` (workflow de validation)

---

## 🚀 Mise à jour du module

```bash
# Mise à jour simple
./odoo.sh update potting_management

# Mise à jour avec migration
./odoo-bin -c odoo.conf -u potting_management -d icp_dev_db

# Installation depuis zéro
./odoo.sh install potting_management
```

---

## 📝 Conventions de code

1. **Nommage des modèles :** `potting.nom_modele`
2. **Nommage des vues :** `potting_nom_modele_view_type`
3. **États en français :** 'brouillon' → 'draft', 'validé' → 'validated'
4. **Tracking :** Ajouter `tracking=True` aux champs importants
5. **Documentation :** Docstrings pour toutes les méthodes

---

*Module Potting Management v17.0.1.3.0*
*Dernière mise à jour : Janvier 2025*
