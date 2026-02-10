# -*- coding: utf-8 -*-
"""Tests unitaires pour le modèle potting.confirmation.vente (CV)

Ce module teste:
- Création de CV avec validation des champs
- Contraintes SQL et Python
- Calculs de tonnage et progression
- Méthodes de vérification de disponibilité
- Workflow d'états et expiration
"""

from datetime import date, timedelta
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('potting', 'potting_cv', '-at_install', 'post_install')
class TestPottingConfirmationVente(TransactionCase):
    """Tests pour le modèle potting.confirmation.vente"""
    
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
            'name': 'Campagne CV Test 2024-2025',
            'date_start': date.today() - timedelta(days=30),
            'date_end': date.today() + timedelta(days=335),
            'state': 'active',
        })
    
    # =========================================================================
    # TESTS DE CRÉATION
    # =========================================================================
    
    def test_01_create_cv_basic(self):
        """Test création d'une CV basique"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-BASIC-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        
        self.assertTrue(cv.id)
        self.assertEqual(cv.state, 'draft')
        self.assertIn('CV/', cv.name)
    
    def test_02_create_cv_complete(self):
        """Test création CV complète"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-COMPLETE-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 300.0,
            'prix_tonnage': 1600000,
            'product_type': 'cocoa_mass',
        })
        
        self.assertTrue(cv.id)
        self.assertEqual(cv.state, 'draft')
    
    # =========================================================================
    # TESTS DE CONTRAINTES
    # =========================================================================
    
    def test_10_constraint_tonnage_positive(self):
        """Test contrainte tonnage positif"""
        with self.assertRaises(Exception):
            self.env['potting.confirmation.vente'].create({
                'reference_ccc': 'CV-NEG-001',
                'campaign_id': self.campaign.id,
                'date_emission': date.today(),
                'date_start': date.today(),
                'date_end': date.today() + timedelta(days=90),
                'tonnage_autorise': -100.0,  # Tonnage négatif
                'prix_tonnage': 1500000,
                'product_type': 'all',
            })
    
    def test_11_constraint_dates_coherence(self):
        """Test contrainte dates début/fin"""
        with self.assertRaises(Exception):
            self.env['potting.confirmation.vente'].create({
                'reference_ccc': 'CV-DATE-001',
                'campaign_id': self.campaign.id,
                'date_emission': date.today(),
                'date_start': date.today() + timedelta(days=90),  # Après date_end
                'date_end': date.today(),
                'tonnage_autorise': 500.0,
                'prix_tonnage': 1500000,
                'product_type': 'all',
            })
    
    def test_12_constraint_reference_unique(self):
        """Test contrainte référence CCC unique"""
        self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-UNIQUE-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        
        # Tenter de créer une autre CV avec la même référence
        with self.assertRaises(Exception):
            self.env['potting.confirmation.vente'].create({
                'reference_ccc': 'CV-UNIQUE-001',  # Doublon
                'campaign_id': self.campaign.id,
                'date_emission': date.today(),
                'date_start': date.today(),
                'date_end': date.today() + timedelta(days=90),
                'tonnage_autorise': 300.0,
                'prix_tonnage': 1500000,
                'product_type': 'all',
            })
    
    # =========================================================================
    # TESTS DE CALCULS
    # =========================================================================
    
    def test_20_compute_is_expired(self):
        """Test calcul expiration"""
        # CV non expirée
        cv_active = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-ACTIVE-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        self.assertFalse(cv_active.is_expired)
        
        # CV expirée
        cv_expired = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-EXPIRED-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today() - timedelta(days=100),
            'date_start': date.today() - timedelta(days=100),
            'date_end': date.today() - timedelta(days=10),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        self.assertTrue(cv_expired.is_expired)
    
    def test_21_compute_days_remaining(self):
        """Test calcul jours restants"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-DAYS-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=30),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        
        self.assertEqual(cv.days_remaining, 30)
    
    def test_22_compute_tonnage_progress(self):
        """Test calcul progression tonnage"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-PROG-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 100.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        
        # Sans contrats liés, progression = 0
        self.assertEqual(cv.tonnage_progress, 0)
        self.assertEqual(cv.tonnage_restant, 100.0)
    
    # =========================================================================
    # TESTS DU WORKFLOW
    # =========================================================================
    
    def test_30_workflow_draft_to_active(self):
        """Test transition brouillon → active"""
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
        cv.action_activate()
        self.assertEqual(cv.state, 'active')
    
    def test_31_workflow_active_to_expired(self):
        """Test transition active → expirée"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-EXPIRE-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        cv.action_expire()
        self.assertEqual(cv.state, 'expired')
    
    def test_32_workflow_cancel_blocked_with_orders(self):
        """Test annulation bloquée si contrats actifs"""
        # Ce test nécessite la création d'un contrat
        pass  # Implémenté dans test_potting_workflow
    
    # =========================================================================
    # TESTS DES MÉTHODES UTILITAIRES
    # =========================================================================
    
    def test_40_check_can_use_tonnage_valid(self):
        """Test vérification tonnage disponible - cas valide"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-AVAIL-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        result = cv.check_can_use_tonnage(100.0)
        self.assertTrue(result)
    
    def test_41_check_can_use_tonnage_exceeds(self):
        """Test vérification tonnage disponible - dépassement"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-EXCEED-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 100.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        with self.assertRaises(ValidationError):
            cv.check_can_use_tonnage(150.0)  # Dépasse le disponible
    
    def test_42_check_can_use_tonnage_inactive(self):
        """Test vérification tonnage - CV inactive"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-INACTIVE-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'draft',  # Pas active
        })
        
        with self.assertRaises(ValidationError):
            cv.check_can_use_tonnage(100.0)
    
    def test_43_get_utilization_status(self):
        """Test récupération statut utilisation"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-STATUS-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        
        status, message = cv.get_utilization_status()
        self.assertIn(status, ['available', 'normal', 'warning', 'full'])
        self.assertIsInstance(message, str)
    
    def test_44_get_validity_status(self):
        """Test récupération statut validité"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-VALID-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
        })
        
        status, message = cv.get_validity_status()
        self.assertIn(status, ['valid', 'warning', 'critical', 'expired'])
    
    def test_45_action_extend_validity(self):
        """Test extension de validité"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-EXTEND-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=10),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        original_end = cv.date_end
        cv.action_extend_validity()
        
        # La date de fin devrait être prolongée d'un mois
        self.assertGreater(cv.date_end, original_end)
    
    # =========================================================================
    # TESTS SUPPRESSION
    # =========================================================================
    
    def test_50_unlink_draft(self):
        """Test suppression CV en brouillon"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-DELETE-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'draft',
        })
        
        cv_id = cv.id
        cv.unlink()
        
        # Vérifier que la CV est supprimée
        self.assertFalse(self.env['potting.confirmation.vente'].browse(cv_id).exists())
    
    def test_51_unlink_active_blocked(self):
        """Test suppression bloquée pour CV active"""
        cv = self.env['potting.confirmation.vente'].create({
            'reference_ccc': 'CV-NODELETE-001',
            'campaign_id': self.campaign.id,
            'date_emission': date.today(),
            'date_start': date.today(),
            'date_end': date.today() + timedelta(days=90),
            'tonnage_autorise': 500.0,
            'prix_tonnage': 1500000,
            'product_type': 'all',
            'state': 'active',
        })
        
        with self.assertRaises(UserError):
            cv.unlink()
