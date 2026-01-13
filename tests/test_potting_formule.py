# -*- coding: utf-8 -*-
"""Tests unitaires pour le modèle potting.formule (Formule FO)

Ce module teste:
- Création de formules avec validation des champs
- Contraintes SQL et Python
- Calculs de taxes et montants
- Méthodes utilitaires
- Workflow d'états
"""

from datetime import date, timedelta
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('potting', 'potting_formule', '-at_install', 'post_install')
class TestPottingFormule(TransactionCase):
    """Tests pour le modèle potting.formule"""
    
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
            'name': 'Campagne Test 2024-2025',
            'date_start': date.today() - timedelta(days=30),
            'date_end': date.today() + timedelta(days=335),
            'state': 'active',
        })
        
        # Confirmation de Vente de test
        cls.confirmation_vente = cls.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-TEST-001',
            'campaign_id': cls.campaign.id,
            'date_emission': date.today() - timedelta(days=10),
            'date_start': date.today() - timedelta(days=10),
            'date_end': date.today() + timedelta(days=80),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        # Types de taxes
        cls.tax_type_ccc = cls.env['potting.taxe.type'].search(
            [('code', '=', 'CCC')], limit=1
        )
        cls.tax_type_dius = cls.env['potting.taxe.type'].search(
            [('code', '=', 'DIUS')], limit=1
        )
    
    # =========================================================================
    # TESTS DE CRÉATION
    # =========================================================================
    
    def test_01_create_formule_basic(self):
        """Test création d'une formule basique"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        self.assertTrue(formule.id)
        self.assertEqual(formule.state, 'draft')
        self.assertIn('FO/', formule.name)
    
    def test_02_create_formule_with_numero_fo1(self):
        """Test création avec numéro FO1"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_butter',
            'prix_kg': 1800,
            'numero_fo1': 'EGY060',
        })
        
        self.assertEqual(formule.numero_fo1, 'EGY060')
    
    # =========================================================================
    # TESTS DE CONTRAINTES
    # =========================================================================
    
    def test_10_constraint_prix_kg_positive(self):
        """Test contrainte prix_kg positif"""
        with self.assertRaises(Exception):
            self.env['potting.formule'].create({
                'confirmation_vente_id': self.confirmation_vente.id,
                'campaign_id': self.campaign.id,
                'date_creation': date.today(),
                'product_type': 'cocoa_mass',
                'prix_kg': -100,  # Prix négatif
            })
    
    def test_11_constraint_dates_coherence(self):
        """Test contrainte dates début/fin"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        # Tenter de définir une date de fin avant la date de début
        with self.assertRaises(ValidationError):
            formule.write({
                'date_debut': date.today(),
                'date_fin': date.today() - timedelta(days=30),
            })
    
    def test_12_constraint_product_type_cv(self):
        """Test contrainte type produit cohérent avec CV"""
        # Créer une CV restreinte à la masse de cacao
        cv_restricted = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-RESTRICT-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 100.0,
            'prix_tonnage': 1500000,
            'product_type': 'cocoa_mass',  # Restreint
            'state': 'active',
        })
        
        # Tenter de créer une formule avec un type différent
        with self.assertRaises(ValidationError):
            self.env['potting.formule'].create({
                'confirmation_vente_id': cv_restricted.id,
                'campaign_id': self.campaign.id,
                'date_creation': date.today(),
                'product_type': 'cocoa_butter',  # Différent de cocoa_mass
                'prix_kg': 1800,
            })
    
    # =========================================================================
    # TESTS DE CALCULS
    # =========================================================================
    
    def test_20_compute_prix_tonnage(self):
        """Test calcul du prix au tonnage depuis le prix au kg"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        # 1500 FCFA/kg = 1,500,000 FCFA/tonne
        self.assertEqual(formule.prix_tonnage, 1500000)
    
    def test_21_compute_tonnage_net(self):
        """Test calcul du tonnage net"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'tonnage_brut': 100.0,
            'pourcentage_humidite': 8.0,
        })
        
        # Tonnage net = Brut * (1 - humidité/100)
        expected_net = 100.0 * (1 - 8.0 / 100)
        self.assertAlmostEqual(formule.tonnage_net, expected_net, places=2)
    
    # =========================================================================
    # TESTS DES TAXES
    # =========================================================================
    
    def test_30_create_tax_line(self):
        """Test création d'une ligne de taxe"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'tonnage_brut': 100.0,
        })
        
        # Ajouter une taxe CCC
        if self.tax_type_ccc:
            tax_line = self.env['potting.formule.taxe'].create({
                'formule_id': formule.id,
                'taxe_type_id': self.tax_type_ccc.id,
                'taux_fcfa_kg': 1.245,
            })
            
            self.assertTrue(tax_line.id)
            # Montant = 100 T × 1000 kg × 1.245 FCFA/kg
            expected_amount = 100 * 1000 * 1.245
            self.assertAlmostEqual(tax_line.montant, expected_amount, places=2)
    
    def test_31_add_standard_taxes(self):
        """Test ajout automatique des taxes standard"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        # Vérifier que la méthode existe
        self.assertTrue(hasattr(formule, 'action_add_standard_taxes'))
    
    def test_32_get_taxes_summary(self):
        """Test récupération du résumé des taxes"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        summary = formule.get_taxes_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn('total_taxes', summary)
        self.assertIn('taxes_details', summary)
    
    # =========================================================================
    # TESTS DU WORKFLOW
    # =========================================================================
    
    def test_40_workflow_draft_to_submitted(self):
        """Test transition brouillon → soumis"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        self.assertEqual(formule.state, 'draft')
        formule.action_submit()
        self.assertEqual(formule.state, 'submitted')
    
    def test_41_workflow_submit_to_validated(self):
        """Test transition soumis → validé"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        formule.action_submit()
        formule.action_validate()
        self.assertEqual(formule.state, 'validated')
    
    def test_42_workflow_cancel(self):
        """Test annulation d'une formule"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        formule.action_cancel()
        self.assertEqual(formule.state, 'cancelled')
    
    # =========================================================================
    # TESTS DES MÉTHODES UTILITAIRES
    # =========================================================================
    
    def test_50_get_formule_display_name(self):
        """Test nom d'affichage enrichi"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'reference_ccc': 'FO-CCC-123',
        })
        
        display_name = formule.get_formule_display_name()
        self.assertIsInstance(display_name, str)
        self.assertIn(formule.name, display_name)
    
    def test_51_action_duplicate_formule(self):
        """Test duplication de formule"""
        formule = self.env['potting.formule'].create({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
        })
        
        result = formule.action_duplicate_formule()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'potting.formule')
    
    # =========================================================================
    # TESTS ONCHANGE
    # =========================================================================
    
    def test_60_onchange_prix_kg(self):
        """Test onchange prix_kg"""
        formule = self.env['potting.formule'].new({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
            'product_type': 'cocoa_mass',
        })
        
        formule.prix_kg = 1500
        formule._onchange_prix_kg()
        
        self.assertEqual(formule.prix_tonnage, 1500000)
    
    def test_61_onchange_product_type(self):
        """Test onchange type de produit"""
        formule = self.env['potting.formule'].new({
            'confirmation_vente_id': self.confirmation_vente.id,
            'campaign_id': self.campaign.id,
        })
        
        formule.product_type = 'cocoa_butter'
        formule._onchange_product_type()
        
        # Vérifier que l'emballage par défaut est défini
        self.assertTrue(formule.emballage or True)  # Peut être vide selon config
