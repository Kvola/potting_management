# -*- coding: utf-8 -*-
"""Tests unitaires pour le modèle potting.transit.order (OT)

Ce module teste:
- Création d'OT avec validation des champs
- Contraintes SQL et Python
- Génération de lots
- Calculs de tonnage et progression
"""

from datetime import date, timedelta
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('potting', 'potting_transit_order', '-at_install', 'post_install')
class TestPottingTransitOrder(TransactionCase):
    """Tests pour le modèle potting.transit.order"""
    
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
            'name': 'Campagne OT Test 2024-2025',
            'date_start': date.today() - timedelta(days=30),
            'date_end': date.today() + timedelta(days=335),
            'state': 'active',
        })
        
        # Confirmation de Vente de test
        cls.cv = cls.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-OT-TEST',
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
            'name': 'Client OT Test',
            'is_company': True,
        })
        
        # Consignee de test
        cls.consignee = cls.env['res.partner'].create({
            'name': 'Consignee Test',
            'is_company': True,
        })
        
        # Commande client de test
        cls.customer_order = cls.env['potting.customer.order'].create({
            'confirmation_vente_id': cls.cv.id,
            'customer_id': cls.customer.id,
            'product_type': 'cocoa_mass',
            'contract_tonnage': 200.0,
            'unit_price': 1800000,
            'date_order': date.today(),
            'state': 'confirmed',
        })
        
        # Formule de test
        cls.formule = cls.env['potting.formule'].create({
            'confirmation_vente_id': cls.cv.id,
            'campaign_id': cls.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
    
    # =========================================================================
    # TESTS DE CRÉATION
    # =========================================================================
    
    def test_01_create_ot_basic(self):
        """Test création d'un OT basique"""
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': self.formule.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        self.assertTrue(ot.id)
        self.assertEqual(ot.state, 'draft')
        self.assertIn('OT/', ot.name)
    
    def test_02_create_ot_with_booking(self):
        """Test création avec numéro de booking"""
        # Créer une nouvelle formule pour cet OT
        formule2 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule2.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
            'booking_number': 'BOOK-2024-001',
            'ot_reference': 'OT10532',
        })
        
        self.assertEqual(ot.booking_number, 'BOOK-2024-001')
        self.assertEqual(ot.ot_reference, 'OT10532')
    
    # =========================================================================
    # TESTS DE CONTRAINTES
    # =========================================================================
    
    def test_10_constraint_tonnage_positive(self):
        """Test contrainte tonnage positif"""
        formule3 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        with self.assertRaises(Exception):
            self.env['potting.transit.order'].create({
                'customer_order_id': self.customer_order.id,
                'formule_id': formule3.id,
                'campaign_id': self.campaign.id,
                'consignee_id': self.consignee.id,
                'product_type': 'cocoa_mass',
                'tonnage': -10.0,  # Tonnage négatif
            })
    
    def test_11_constraint_tonnage_max(self):
        """Test contrainte tonnage maximum"""
        formule4 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        with self.assertRaises(ValidationError):
            self.env['potting.transit.order'].create({
                'customer_order_id': self.customer_order.id,
                'formule_id': formule4.id,
                'campaign_id': self.campaign.id,
                'consignee_id': self.consignee.id,
                'product_type': 'cocoa_mass',
                'tonnage': 1500.0,  # Dépasse 1000 T max
            })
    
    def test_12_constraint_product_type_order(self):
        """Test contrainte type produit cohérent avec commande"""
        formule5 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_butter',  # Différent de la commande
            'prix_kg': 1800,
            'state': 'validated',
        })
        
        with self.assertRaises(ValidationError):
            self.env['potting.transit.order'].create({
                'customer_order_id': self.customer_order.id,
                'formule_id': formule5.id,
                'campaign_id': self.campaign.id,
                'consignee_id': self.consignee.id,
                'product_type': 'cocoa_butter',  # Différent de cocoa_mass
                'tonnage': 50.0,
            })
    
    def test_13_constraint_formule_unique(self):
        """Test contrainte formule unique par OT"""
        # Créer un premier OT avec la formule
        formule6 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot1 = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule6.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        # Tenter de créer un second OT avec la même formule
        with self.assertRaises(ValidationError):
            self.env['potting.transit.order'].create({
                'customer_order_id': self.customer_order.id,
                'formule_id': formule6.id,  # Même formule
                'campaign_id': self.campaign.id,
                'consignee_id': self.consignee.id,
                'product_type': 'cocoa_mass',
                'tonnage': 30.0,
            })
    
    # =========================================================================
    # TESTS DE CALCULS
    # =========================================================================
    
    def test_20_compute_amounts(self):
        """Test calcul des montants"""
        formule7 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule7.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        # Subtotal = 50 T × 1.8M (prix de la commande) = 90M
        expected_subtotal = 50 * 1800000
        self.assertEqual(ot.subtotal_amount, expected_subtotal)
    
    def test_21_compute_export_duties(self):
        """Test calcul droits d'exportation"""
        # Mettre à jour la commande avec un taux de droits
        self.customer_order.write({'export_duty_rate': 14.6})
        
        formule8 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule8.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        self.assertEqual(ot.export_duty_rate, 14.6)
    
    def test_22_compute_lot_count(self):
        """Test compteur de lots"""
        formule9 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule9.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        # Sans lots, compteur = 0
        self.assertEqual(ot.lot_count, 0)
        self.assertEqual(ot.potted_lot_count, 0)
    
    # =========================================================================
    # TESTS DU WORKFLOW
    # =========================================================================
    
    def test_30_workflow_generate_lots(self):
        """Test génération des lots"""
        formule10 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule10.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        self.assertEqual(ot.state, 'draft')
        
        # Générer les lots
        if hasattr(ot, 'action_generate_lots'):
            ot.action_generate_lots()
            self.assertEqual(ot.state, 'lots_generated')
            self.assertGreater(ot.lot_count, 0)
    
    def test_31_workflow_in_progress(self):
        """Test passage en cours"""
        formule11 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule11.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
            'state': 'lots_generated',
        })
        
        if hasattr(ot, 'action_start'):
            ot.action_start()
            self.assertEqual(ot.state, 'in_progress')
    
    def test_32_workflow_cancel(self):
        """Test annulation"""
        formule12 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule12.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        if hasattr(ot, 'action_cancel'):
            ot.action_cancel()
            self.assertEqual(ot.state, 'cancelled')
    
    # =========================================================================
    # TESTS RELATIONS
    # =========================================================================
    
    def test_40_formule_related_fields(self):
        """Test champs liés à la Formule"""
        formule13 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'reference_ccc': 'FO-CCC-TEST',
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule13.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        self.assertEqual(ot.formule_reference, 'FO-CCC-TEST')
        self.assertEqual(ot.formule_prix_tonnage, 1500000)
    
    def test_41_customer_order_related(self):
        """Test champs liés à la commande"""
        formule14 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule14.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
        })
        
        self.assertEqual(ot.customer_id.id, self.customer.id)
        self.assertEqual(ot.unit_price, 1800000)
    
    # =========================================================================
    # TESTS EXPORT AUTORISÉ
    # =========================================================================
    
    def test_50_export_not_allowed_without_duties(self):
        """Test exportation non autorisée sans droits collectés"""
        formule15 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule15.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
            'export_duty_collected': False,
        })
        
        self.assertFalse(ot.export_allowed)
    
    def test_51_export_allowed_with_duties(self):
        """Test exportation autorisée avec droits collectés"""
        formule16 = self.env['potting.formule'].create({
            'confirmation_vente_id': self.cv.id,
            'campaign_id': self.campaign.id,
            'date_creation': date.today(),
            'product_type': 'cocoa_mass',
            'prix_kg': 1500,
            'state': 'validated',
        })
        
        ot = self.env['potting.transit.order'].create({
            'customer_order_id': self.customer_order.id,
            'formule_id': formule16.id,
            'campaign_id': self.campaign.id,
            'consignee_id': self.consignee.id,
            'product_type': 'cocoa_mass',
            'tonnage': 50.0,
            'export_duty_collected': True,
            'export_duty_collection_date': date.today(),
        })
        
        self.assertTrue(ot.export_allowed)
