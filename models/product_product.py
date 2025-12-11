# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    potting_product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit empotage")
    
    # Informations de conditionnement (calculées selon le type de produit)
    packaging_unit_name = fields.Char(
        string="Unité de conditionnement",
        compute='_compute_packaging_info',
        help="Type d'emballage utilisé pour ce produit"
    )
    
    packaging_unit_weight_kg = fields.Float(
        string="Poids par unité (kg)",
        compute='_compute_packaging_info',
        help="Poids d'une unité de conditionnement en kilogrammes"
    )
    
    packaging_description = fields.Char(
        string="Description conditionnement",
        compute='_compute_packaging_info',
        help="Description complète du conditionnement"
    )

    # Configuration des conditionnements par type de produit
    PACKAGING_CONFIG = {
        'cocoa_mass': {'unit_name': 'cartons', 'weight_kg': 25, 'description': 'Cartons de 25 kg'},
        'cocoa_butter': {'unit_name': 'cartons', 'weight_kg': 25, 'description': 'Cartons de 25 kg'},
        'cocoa_cake': {'unit_name': 'big bags', 'weight_kg': 1000, 'description': 'Big bags de 1 tonne'},
        'cocoa_powder': {'unit_name': 'sacs', 'weight_kg': 25, 'description': 'Sacs de 25 kg'},
    }

    @api.depends('potting_product_type')
    def _compute_packaging_info(self):
        """Calcul des informations de conditionnement basé sur le type de produit"""
        for product in self:
            config = self.PACKAGING_CONFIG.get(product.potting_product_type, {})
            product.packaging_unit_name = config.get('unit_name', '')
            product.packaging_unit_weight_kg = config.get('weight_kg', 0)
            product.packaging_description = config.get('description', '')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    potting_product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit empotage")
    
    # Informations de conditionnement (calculées selon le type de produit)
    packaging_unit_name = fields.Char(
        string="Unité de conditionnement",
        compute='_compute_packaging_info',
        help="Type d'emballage utilisé pour ce produit"
    )
    
    packaging_unit_weight_kg = fields.Float(
        string="Poids par unité (kg)",
        compute='_compute_packaging_info',
        help="Poids d'une unité de conditionnement en kilogrammes"
    )
    
    packaging_description = fields.Char(
        string="Description conditionnement",
        compute='_compute_packaging_info',
        help="Description complète du conditionnement"
    )

    # Configuration des conditionnements par type de produit
    PACKAGING_CONFIG = {
        'cocoa_mass': {'unit_name': 'cartons', 'weight_kg': 25, 'description': 'Cartons de 25 kg'},
        'cocoa_butter': {'unit_name': 'cartons', 'weight_kg': 25, 'description': 'Cartons de 25 kg'},
        'cocoa_cake': {'unit_name': 'big bags', 'weight_kg': 1000, 'description': 'Big bags de 1 tonne'},
        'cocoa_powder': {'unit_name': 'sacs', 'weight_kg': 25, 'description': 'Sacs de 25 kg'},
    }

    @api.depends('potting_product_type')
    def _compute_packaging_info(self):
        """Calcul des informations de conditionnement basé sur le type de produit"""
        for product in self:
            config = self.PACKAGING_CONFIG.get(product.potting_product_type, {})
            product.packaging_unit_name = config.get('unit_name', '')
            product.packaging_unit_weight_kg = config.get('weight_kg', 0)
            product.packaging_description = config.get('description', '')
