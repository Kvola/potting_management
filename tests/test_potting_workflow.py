# -*- coding: utf-8 -*-
"""Tests d'intégration pour le workflow complet de Potting Management

Ce module teste:
- Workflow complet CV → Contrat → FO → OT → Lots → BL → Facture
- Interactions entre les modèles
- Scénarios métier réels
- Cas limites et erreurs
"""

from datetime import date, timedelta
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('potting', 'potting_workflow', '-at_install', 'post_install')
class TestPottingWorkflow(TransactionCase):
    """Tests d'intégration pour le workflow complet"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration des données de test"""
        super().setUpClass()
        
        # Devise XOF
        cls.currency_xof = cls.env['res.currency'].search(
            [('name', '=', 'XOF')], limit=1
        )
        if not cls.currency_xof:
            cls.currency_xof = cls.env['res.currency'].create({
                'name': 'XOF',
                'symbol': 'FCFA',
                'rounding': 1,
            })
        
        # Campagne de test
        cls.campaign = cls.env['potting.campaign'].create({
            'name': 'Campagne Workflow Test 2024-2025',
            'date_start': date.today() - timedelta(days=30),
            'date_end': date.today() + timedelta(days=335),
            'state': 'active',
        })
        
        # Client de test
        cls.customer = cls.env['res.partner'].create({
            'name': 'Client Workflow Test',
            'is_company': True,
        })
        
        # Consignee de test
        cls.consignee = cls.env['res.partner'].create({
            'name': 'Consignee Workflow Test',
            'is_company': True,
        })
    
    # =========================================================================
    # TESTS WORKFLOW COMPLET
    # =========================================================================
    
    def test_01_complete_export_workflow(self):
        """Test du workflow complet d'exportation"""
        
        # Étape 1: Créer une Confirmation de Vente (CV)
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-WORKFLOW-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        self.assertEqual(cv.state, 'draft')
        
        # Activer la CV
        cv.action_activate()
        self.assertEqual(cv.state, 'active')
        
        # Étape 2: Créer un contrat client basé sur la CV
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_ids': [(4, cv.id)],
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'export_duty_rate': 14.6,
            'date_order': date.today(),
        })
        self.assertEqual(order.state, 'draft')
        
        # Confirmer le contrat
        order.action_confirm()
        self.assertEqual(order.state, 'confirmed')
        
        # Vérifier que le tonnage de la CV est mis à jour
        cv.invalidate_recordset()
        self.assertEqual(cv.tonnage_utilise, 100.0)
        self.assertEqual(cv.tonnage_restant, 400.0)
        
        # Étape 3: Créer une Formule (FO) pour le contrat
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        self.assertEqual(formule.state, 'draft')
        
        # Soumettre et valider la formule
        formule.action_submit()
        self.assertEqual(formule.state, 'submitted')
        
        formule.action_validate()
        self.assertEqual(formule.state, 'validated')
        
        # Étape 4: Créer un Ordre de Transit (OT) lié à la formule
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': order.id,
            'formule_id': formule.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        self.assertEqual(ot.state, 'draft')
        
        # Vérifier les relations
        self.assertEqual(ot.confirmation_vente_id.id, cv.id)
        self.assertEqual(ot.formule_prix_tonnage, 1500000)
        
        # Étape 5: Générer les lots (si la méthode existe)
        if hasattr(ot, 'action_generate_lots'):
            ot.action_generate_lots()
            self.assertEqual(ot.state, 'lots_generated')
            self.assertGreater(ot.lot_count, 0)
    
    def test_02_cv_tonnage_tracking(self):
        """Test suivi du tonnage CV à travers plusieurs contrats"""
        
        # Créer une CV
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-TRACKING-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 200.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        # Premier contrat: 80 T
        order1 = self.env['potting.customer.order'].create({
            'confirmation_vente_ids': [(4, cv.id)],
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 80.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        cv.invalidate_recordset()
        self.assertEqual(cv.tonnage_utilise, 80.0)
        self.assertEqual(cv.tonnage_restant, 120.0)
        self.assertEqual(cv.tonnage_progress, 40.0)  # 80/200 = 40%
        
        # Deuxième contrat: 70 T
        order2 = self.env['potting.customer.order'].create({
            'confirmation_vente_ids': [(4, cv.id)],
            'customer_id': self.customer.id,
            'product_type': 'cocoa_butter',
            'contract_tonnage': 70.0,
            'unit_price': 2200000,
            'date_order': date.today(),
        })
        
        cv.invalidate_recordset()
        self.assertEqual(cv.tonnage_utilise, 150.0)
        self.assertEqual(cv.tonnage_restant, 50.0)
        self.assertEqual(cv.tonnage_progress, 75.0)  # 150/200 = 75%
        
        # Tenter un troisième contrat qui dépasse: 60 T
        with self.assertRaises(ValidationError):
            self.env['potting.customer.order'].create({
                'confirmation_vente_ids': [(4, cv.id)],
                'customer_id': self.customer.id,
                'product_type': 'cocoa_mass',
                'contract_tonnage': 60.0,  # 150 + 60 > 200
                'unit_price': 1800000,
                'date_order': date.today(),
            })
    
    def test_03_formule_to_ot_single_link(self):
        """Test qu'une Formule ne peut être liée qu'à un seul OT"""
        
        # Setup
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-SINGLE-LINK',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_ids': [(4, cv.id)],
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 200.0,
            'unit_price': 1800000,
            'date_order': date.today(),
            'state': 'confirmed',
        })
        
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        # Premier OT avec la formule
        ot1 = self.env['potting.transit.order'].create({
            'customer_order_id': order.id,
            'formule_id': formule.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        # Tenter un second OT avec la même formule
        with self.assertRaises(ValidationError):
            self.env['potting.transit.order'].create({
                'customer_order_id': order.id,
                'formule_id': formule.id,  # Même formule
                'campaign_id': self.campaign.id,
                'consignee_id': self.consignee.id,
                'product_type': 'cocoa_mass',
                'tonnage': 30.0,
            })
    
    def test_04_cv_expiration_check(self):
        """Test vérification de l'expiration des CV"""
        
        # Créer une CV expirée
        cv_expired = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-EXPIRED-TEST',
            'campaign_id': self.campaign.id,
            'date_emission': date.today() - timedelta(days=100),
            'date_start': date.today() - timedelta(days=100),
            'date_end': date.today() - timedelta(days=10),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        # Vérifier que la CV est marquée comme expirée
        self.assertTrue(cv_expired.is_expired)
        self.assertEqual(cv_expired.days_remaining, 0)
        
        # Vérifier que check_can_use_tonnage lève une erreur
        with self.assertRaises(ValidationError):
            cv_expired.check_can_use_tonnage(50.0)
    
    def test_05_product_type_consistency(self):
        """Test cohérence du type de produit à travers le workflow"""
        
        # CV restreinte à cocoa_mass
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-PRODUCT-TYPE',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'cocoa_mass',  # Restreint
            'state': 'active',
        })
        
        # Contrat avec cocoa_mass: OK
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_ids': [(4, cv.id)],
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        self.assertTrue(order.id)
        
        # Contrat avec cocoa_butter: ERREUR
        with self.assertRaises(ValidationError):
            self.env['potting.customer.order'].create({
                'confirmation_vente_ids': [(4, cv.id)],
                'customer_id': self.customer.id,
                'product_type': 'cocoa_butter',  # Différent de cocoa_mass
                'contract_tonnage': 50.0,
                'unit_price': 2200000,
                'date_order': date.today(),
            })
    
    def test_06_cancel_cv_with_orders(self):
        """Test annulation d'une CV avec des contrats actifs"""
        
        # Créer CV et contrat
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-CANCEL-TEST',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_ids': [(4, cv.id)],
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
            'state': 'confirmed',  # Contrat confirmé (actif)
        })
        
        # Tenter d'annuler la CV: doit échouer
        with self.assertRaises(UserError):
            cv.action_cancel()
    
    def test_07_formule_taxes_calculation(self):
        """Test calcul des taxes sur une formule"""
        
        # Setup
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-TAXES-TEST',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'tonnage_brut': 100.0,
        })
        
        # Ajouter une taxe CCC
        tax_type_ccc = self.env['potting.taxe.type'].search(
            [('code', '=', 'CCC')], limit=1
        )
        if tax_type_ccc:
            self.env['potting.formule.taxe'].create({
                'formule_id': formule.id,
                'taxe_type_id': tax_type_ccc.id,
                'taux_fcfa_kg': 1.245,  # 1.245 FCFA/kg
            })
            
            # Vérifier le résumé des taxes
            summary = formule.get_taxes_summary()
            self.assertGreater(summary['total_taxes'], 0)
            
            # Montant attendu: 100 T × 1000 kg × 1.245 = 124,500 FCFA
            expected = 100 * 1000 * 1.245
            self.assertAlmostEqual(summary['total_taxes'], expected, places=0)
    
    def test_08_ot_export_duty_requirement(self):
        """Test exigence des droits d'export avant validation OT"""
        
        # Setup complet
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-DUTY-TEST',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_ids': [(4, cv.id)],
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 200.0,
            'unit_price': 1800000,
            'export_duty_rate': 14.6,
            'date_order': date.today(),
            'state': 'confirmed',
        })
        
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': order.id,
            'formule_id': formule.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
            'export_duty_collected': False,  # Pas collecté
        })
        
        # Exportation ne doit pas être autorisée
        self.assertFalse(ot.export_allowed)
        
        # Collecter les droits
        ot.write({
            'export_duty_collected': True,
            'export_duty_collection_date': date.today(),
        })
        
        # Maintenant l'exportation est autorisée
        self.assertTrue(ot.export_allowed)


@tagged('potting', 'potting_workflow_cron', '-at_install', 'post_install')
class TestPottingCron(TransactionCase):
    """Tests pour les tâches planifiées (cron)"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration des données de test"""
        super().setUpClass()
        
        cls.campaign = cls.env['potting.campaign'].create({
            'name': 'Campagne Cron Test',
            'date_start': date.today() - timedelta(days=365),
            'date_end': date.today() + timedelta(days=365),
            'state': 'active',
        })
    
    def test_01_cron_check_expiration(self):
        """Test du cron de vérification des expirations"""
        
        # Créer une CV expirée mais avec state='active'
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-CRON-EXPIRE',
            'campaign_id': self.campaign.id,
            'date_emission': date.today() - timedelta(days=100),
            'date_start': date.today() - timedelta(days=100),
            'date_end': date.today() - timedelta(days=10),  # Expirée
            'tonnage_autorise': 100.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',  # Encore marquée active
        })
        
        # Exécuter le cron
        self.env['potting.confirmation.vente']._cron_check_expiration()
        
        # Vérifier que la CV est maintenant expirée
        cv.invalidate_recordset()
        self.assertEqual(cv.state, 'expired')
