# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PottingContainer(models.Model):
    _name = 'potting.container'
    _description = 'Conteneur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string="Numéro de conteneur",
        required=True,
        tracking=True,
        index=True
    )
    
    container_type = fields.Selection([
        ('20', "20' (Twenty-foot)"),
        ('40', "40' (Forty-foot)"),
        ('40hc', "40' HC (High Cube)"),
    ], string="Type de conteneur", default='20', tracking=True)
    
    seal_number = fields.Char(
        string="Numéro de scellé",
        tracking=True
    )
    
    tare_weight = fields.Float(
        string="Tare (kg)",
        tracking=True
    )
    
    max_payload = fields.Float(
        string="Charge utile max (kg)",
        tracking=True
    )
    
    lot_ids = fields.One2many(
        'potting.lot',
        'container_id',
        string="Lots"
    )
    
    lot_count = fields.Integer(
        string="Nombre de lots",
        compute='_compute_lot_count',
        store=True
    )
    
    total_tonnage = fields.Float(
        string="Tonnage total (T)",
        compute='_compute_total_tonnage',
        store=True
    )
    
    transit_order_ids = fields.Many2many(
        'potting.transit.order',
        compute='_compute_transit_orders',
        string="Ordres de Transit"
    )
    
    vessel_name = fields.Char(
        string="Nom du navire",
        tracking=True
    )
    
    booking_number = fields.Char(
        string="Numéro de réservation",
        tracking=True
    )
    
    date_potting = fields.Datetime(
        string="Date d'empotage",
        tracking=True
    )
    
    date_departure = fields.Date(
        string="Date de départ",
        tracking=True
    )
    
    port_loading = fields.Char(
        string="Port de chargement (POL)",
        tracking=True
    )
    
    port_discharge = fields.Char(
        string="Port de déchargement (POD)",
        tracking=True
    )
    
    state = fields.Selection([
        ('available', 'Disponible'),
        ('loading', 'En chargement'),
        ('loaded', 'Chargé'),
        ('shipped', 'Expédié'),
    ], string="État", default='available', tracking=True)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )

    @api.depends('lot_ids')
    def _compute_lot_count(self):
        for container in self:
            container.lot_count = len(container.lot_ids)

    @api.depends('lot_ids.current_tonnage')
    def _compute_total_tonnage(self):
        for container in self:
            container.total_tonnage = sum(container.lot_ids.mapped('current_tonnage'))

    @api.depends('lot_ids.transit_order_id')
    def _compute_transit_orders(self):
        for container in self:
            container.transit_order_ids = container.lot_ids.mapped('transit_order_id')

    def action_start_loading(self):
        self.write({
            'state': 'loading',
            'date_potting': fields.Datetime.now(),
        })

    def action_finish_loading(self):
        self.write({'state': 'loaded'})

    def action_ship(self):
        self.write({'state': 'shipped'})

    def action_view_lots(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lots'),
            'res_model': 'potting.lot',
            'view_mode': 'tree,form',
            'domain': [('container_id', '=', self.id)],
        }
