# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PottingProductionLine(models.Model):
    _name = 'potting.production.line'
    _description = 'Ligne de production'
    _order = 'date desc, id desc'

    lot_id = fields.Many2one(
        'potting.lot',
        string="Lot",
        required=True,
        ondelete='cascade'
    )
    
    transit_order_id = fields.Many2one(
        related='lot_id.transit_order_id',
        string="Ordre de Transit",
        store=True
    )
    
    date = fields.Date(
        string="Date de production",
        required=True,
        default=fields.Date.context_today
    )
    
    tonnage = fields.Float(
        string="Tonnage (T)",
        required=True
    )
    
    batch_number = fields.Char(
        string="Numéro de batch"
    )
    
    shift = fields.Selection([
        ('morning', 'Matin'),
        ('afternoon', 'Après-midi'),
        ('night', 'Nuit'),
    ], string="Équipe")
    
    operator_id = fields.Many2one(
        'res.users',
        string="Opérateur",
        default=lambda self: self.env.user
    )
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Update lot state to in_production if still in draft
        for record in records:
            if record.lot_id.state == 'draft':
                record.lot_id.action_start_production()
            # Also update transit order state
            if record.transit_order_id.state == 'lots_generated':
                record.transit_order_id.action_start_production()
        return records
