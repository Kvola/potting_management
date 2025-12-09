# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Default customer
    potting_default_customer_id = fields.Many2one(
        'res.partner',
        string="Client par défaut",
        config_parameter='potting_management.default_customer_id',
        help="Client qui sera sélectionné par défaut lors de la création d'une commande"
    )

    # Maximum tonnage per lot by product type
    potting_max_tonnage_cocoa_mass = fields.Float(
        string="Tonnage max - Masse de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_mass',
        default=25.0,
        help="Tonnage maximum par lot pour la Masse de cacao"
    )

    potting_max_tonnage_cocoa_mass_alt = fields.Float(
        string="Tonnage max alternatif - Masse de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_mass_alt',
        default=20.0,
        help="Tonnage maximum alternatif par lot pour la Masse de cacao"
    )

    potting_max_tonnage_cocoa_butter = fields.Float(
        string="Tonnage max - Beurre de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_butter',
        default=22.0,
        help="Tonnage maximum par lot pour le Beurre de cacao"
    )

    potting_max_tonnage_cocoa_cake = fields.Float(
        string="Tonnage max - Cake de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_cake',
        default=25.0,
        help="Tonnage maximum par lot pour le Cake (Tourteau) de cacao"
    )

    potting_max_tonnage_cocoa_powder = fields.Float(
        string="Tonnage max - Poudre de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_powder',
        default=22.5,
        help="Tonnage maximum par lot pour la Poudre de cacao"
    )

    # Default CC recipients for reports (stored as computed field)
    potting_default_cc_partner_ids = fields.Many2many(
        'res.partner',
        string="Destinataires en copie par défaut",
        help="Liste des personnes à mettre en copie par défaut lors de l'envoi des rapports"
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Get CC partners from config parameter
        cc_partner_ids_str = ICP.get_param('potting_management.default_cc_partner_ids', '[]')
        try:
            cc_partner_ids = eval(cc_partner_ids_str) if cc_partner_ids_str else []
            # Vérifier que les partenaires existent toujours
            existing_partners = self.env['res.partner'].sudo().browse(cc_partner_ids).exists()
            cc_partner_ids = existing_partners.ids
        except Exception:
            cc_partner_ids = []
        
        res.update(
            potting_default_cc_partner_ids=[(6, 0, cc_partner_ids)],
        )
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Save CC partners as string list
        ICP.set_param(
            'potting_management.default_cc_partner_ids',
            str(self.potting_default_cc_partner_ids.ids)
        )

    @api.model
    def get_max_tonnage_for_product(self, product_type):
        """Get the maximum tonnage for a given product type"""
        ICP = self.env['ir.config_parameter'].sudo()
        
        tonnage_map = {
            'cocoa_mass': float(ICP.get_param('potting_management.max_tonnage_cocoa_mass', '25.0')),
            'cocoa_butter': float(ICP.get_param('potting_management.max_tonnage_cocoa_butter', '22.0')),
            'cocoa_cake': float(ICP.get_param('potting_management.max_tonnage_cocoa_cake', '25.0')),
            'cocoa_powder': float(ICP.get_param('potting_management.max_tonnage_cocoa_powder', '22.5')),
        }
        
        return tonnage_map.get(product_type, 25.0)

    @api.model
    def get_default_cc_partners(self):
        """Get the default CC partners for reports"""
        ICP = self.env['ir.config_parameter'].sudo()
        cc_partner_ids_str = ICP.get_param('potting_management.default_cc_partner_ids', '[]')
        try:
            cc_partner_ids = eval(cc_partner_ids_str) if cc_partner_ids_str else []
            return self.env['res.partner'].sudo().browse(cc_partner_ids).exists()
        except Exception:
            return self.env['res.partner']