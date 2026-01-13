# -*- coding: utf-8 -*-
"""Tests unitaires pour le modèle potting.customer.order (Contrat Client)

Ce module teste:
- Création de contrats avec validation des champs
- Contraintes SQL et Python
- Calculs de montants et coûts
- Relations avec CV et OT
"""

from datetime import date, timedelta
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('potting', 'potting_customer_order', '-at_install', 'post_install')
class TestPottingCustomerOrder(TransactionCase):
    """Tests pour le modèle potting.customer.order"""
    
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
            'name': 'Campagne Order Test 2024-2025',
            'date_start': date.today() - timedelta(days=30),
            'date_end': date.today() + timedelta(days=335),
            'state': 'active',
        })
        
        # Confirmation de Vente de test
        cls.cv = cls.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-ORDER-TEST',
            'campaign_id': cls.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        # Client de test
        cls.customer = cls.env['res.partner'].create({
            'name': 'Client Test Export',
            'is_company': True,
        })
    
    # =========================================================================
    # TESTS DE CRÉATION
    # =========================================================================
    
    def test_01_create_order_basic(self):
        """Test création d'une commande basique"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        self.assertTrue(order.id)
        self.assertEqual(order.state, 'draft')
        self.assertIn('/', order.name)
    
    def test_02_create_order_with_all_fields(self):
        """Test création avec tous les champs"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'contract_number': 'CONT-2024-001',
            'product_type': 'cocoa_butter',
            'contract_tonnage': 50.0,
            'unit_price': 2200000,
            'date_order': date.today(),
            'date_expected': date.today() + timedelta(days=30),
            'export_duty_rate': 14.6,
            'transport_cost': 500000,
            'storage_cost': 200000,
            'insurance_cost': 100000,
        })
        
        self.assertEqual(order.contract_number, 'CONT-2024-001')
        self.assertEqual(order.export_duty_rate, 14.6)
    
    # =========================================================================
    # TESTS DE CONTRAINTES
    # =========================================================================
    
    def test_10_constraint_dates_order(self):
        """Test contrainte dates commande/livraison"""
        with self.assertRaises(ValidationError):
            self.env['potting.customer.order'].create({
                'confirmation_vente_id': self.cv.id,
                'customer_id': self.customer.id,
                'product_type': 'cocoa_mass',
                'contract_tonnage': 100.0,
                'unit_price': 1800000,
                'date_order': date.today(),
                'date_expected': date.today() - timedelta(days=10),  # Avant date_order
            })
    
    def test_11_constraint_cv_tonnage(self):
        """Test contrainte tonnage CV"""
        # Créer une commande qui utilise tout le tonnage
        order1 = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 400.0,  # 400 sur 500 T
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        # Tenter de créer une autre commande dépassant le disponible
        with self.assertRaises(ValidationError):
            self.env['potting.customer.order'].create({
                'confirmation_vente_id': self.cv.id,
                'customer_id': self.customer.id,
                'product_type': 'cocoa_mass',
                'contract_tonnage': 200.0,  # 400 + 200 > 500
                'unit_price': 1800000,
                'date_order': date.today(),
            })
    
    def test_12_constraint_product_type_cv(self):
        """Test contrainte type produit cohérent avec CV"""
        # Créer une CV restreinte
        cv_restricted = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-RESTRICTED-ORDER',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 200.0,
            'prix_tonnage': 1500000,
            'product_type': 'cocoa_mass',  # Restreint
            'state': 'active',
        })
        
        with self.assertRaises(ValidationError):
            self.env['potting.customer.order'].create({
                'confirmation_vente_id': cv_restricted.id,
                'customer_id': self.customer.id,
                'product_type': 'cocoa_butter',  # Différent
                'contract_tonnage': 50.0,
                'unit_price': 2200000,
                'date_order': date.today(),
            })
    
    def test_13_constraint_unit_price_positive(self):
        """Test contrainte prix unitaire positif"""
        with self.assertRaises(ValidationError):
            self.env['potting.customer.order'].create({
                'confirmation_vente_id': self.cv.id,
                'customer_id': self.customer.id,
                'product_type': 'cocoa_mass',
                'contract_tonnage': 50.0,
                'unit_price': -1000,  # Prix négatif
                'date_order': date.today(),
            })
    
    # =========================================================================
    # TESTS DE CALCULS
    # =========================================================================
    
    def test_20_compute_amounts(self):
        """Test calcul des montants"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,  # 1.8M FCFA/T
            'date_order': date.today(),
        })
        
        # Montant total = 100 T × 1.8M = 180M FCFA
        expected_subtotal = 100 * 1800000
        self.assertEqual(order.subtotal_amount, expected_subtotal)
    
    def test_21_compute_export_duties(self):
        """Test calcul des droits d'exportation"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'export_duty_rate': 14.6,  # 14.6%
            'date_order': date.today(),
        })
        
        # Droits = 180M × 14.6% = 26.28M
        subtotal = 100 * 1800000
        expected_duties = subtotal * 14.6 / 100
        self.assertAlmostEqual(order.export_duty_amount, expected_duties, places=0)
    
    def test_22_compute_total_costs(self):
        """Test calcul des coûts totaux"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
            'transport_cost': 1000000,
            'storage_cost': 500000,
            'insurance_cost': 200000,
            'other_costs': 300000,
        })
        
        expected_total_costs = 1000000 + 500000 + 200000 + 300000
        self.assertEqual(order.total_costs, expected_total_costs)
    
    def test_23_compute_remaining_contract_tonnage(self):
        """Test calcul tonnage restant à allouer"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        # Sans OT, tout le tonnage est à allouer
        self.assertEqual(order.remaining_contract_tonnage, 100.0)
    
    # =========================================================================
    # TESTS DU WORKFLOW
    # =========================================================================
    
    def test_30_workflow_confirm(self):
        """Test confirmation d'une commande"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        self.assertEqual(order.state, 'draft')
        order.action_confirm()
        self.assertEqual(order.state, 'confirmed')
    
    def test_31_workflow_in_progress(self):
        """Test passage en cours"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        order.action_confirm()
        order.action_in_progress()
        self.assertEqual(order.state, 'in_progress')
    
    def test_32_workflow_cancel(self):
        """Test annulation"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        order.action_cancel()
        self.assertEqual(order.state, 'cancelled')
    
    # =========================================================================
    # TESTS RELATIONS
    # =========================================================================
    
    def test_40_cv_related_fields(self):
        """Test champs liés à la CV"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        self.assertEqual(order.cv_reference, 'CV-ORDER-TEST')
    
    def test_41_transit_order_count(self):
        """Test compteur d'OT"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        self.assertEqual(order.transit_order_count, 0)
    
    # =========================================================================
    # TESTS SUPPRESSION
    # =========================================================================
    
    def test_50_unlink_draft(self):
        """Test suppression commande en brouillon"""
        order = self.env['potting.customer.order'].create({
            'confirmation_vente_id': self.cv.id,
            'customer_id': self.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 100.0,
            'unit_price': 1800000,
            'date_order': date.today(),
        })
        
        order_id = order.id
        order.unlink()
        
        self.assertFalse(self.env['potting.customer.order'].browse(order_id).exists())
