# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    """Extension of res.partner to add consignee functionality"""
    _inherit = 'res.partner'

    is_potting_consignee = fields.Boolean(
        string="Est un destinataire (Consignee)",
        default=False,
        help="Cochez cette case si ce contact est un destinataire pour les empotages"
    )
    
    potting_consignee_code = fields.Char(
        string="Code destinataire",
        help="Code unique pour identifier le destinataire"
    )
    
    potting_transit_order_ids = fields.One2many(
        'potting.transit.order',
        'consignee_id',
        string="Ordres de transit"
    )
    
    potting_transit_order_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_potting_transit_order_count',
        store=True
    )
    
    @api.depends('potting_transit_order_ids')
    def _compute_potting_transit_order_count(self):
        for partner in self:
            partner.potting_transit_order_count = len(partner.potting_transit_order_ids)
    
    def action_view_potting_transit_orders(self):
        """Open the list of transit orders for this consignee"""
        self.ensure_one()
        return {
            'name': f'OT - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,form',
            'domain': [('consignee_id', '=', self.id)],
            'context': {'default_consignee_id': self.id},
        }
