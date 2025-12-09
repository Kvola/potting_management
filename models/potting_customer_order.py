# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PottingCustomerOrder(models.Model):
    _name = 'potting.customer.order'
    _description = 'Commande Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    
    customer_id = fields.Many2one(
        'res.partner',
        string="Client",
        required=True,
        tracking=True,
        default=lambda self: self._get_default_customer()
    )
    
    date_order = fields.Date(
        string="Date de commande",
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    
    date_expected = fields.Date(
        string="Date de livraison prévue",
        tracking=True
    )
    
    transit_order_ids = fields.One2many(
        'potting.transit.order',
        'customer_order_id',
        string="Ordres de Transit"
    )
    
    transit_order_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_transit_order_count',
        store=True
    )
    
    total_tonnage = fields.Float(
        string="Tonnage total (T)",
        compute='_compute_total_tonnage',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string="État", default='draft', tracking=True)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )
    
    user_id = fields.Many2one(
        'res.users',
        string="Responsable",
        default=lambda self: self.env.user,
        tracking=True
    )

    @api.model
    def _get_default_customer(self):
        """Get the default customer from settings"""
        default_customer_id = self.env['ir.config_parameter'].sudo().get_param(
            'potting_management.default_customer_id'
        )
        if default_customer_id:
            return self.env['res.partner'].browse(int(default_customer_id))
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('potting.customer.order') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('transit_order_ids')
    def _compute_transit_order_count(self):
        for order in self:
            order.transit_order_count = len(order.transit_order_ids)

    @api.depends('transit_order_ids.tonnage')
    def _compute_total_tonnage(self):
        for order in self:
            order.total_tonnage = sum(order.transit_order_ids.mapped('tonnage'))

    def action_confirm(self):
        for order in self:
            if not order.transit_order_ids:
                raise UserError(_("Vous devez ajouter au moins un Ordre de Transit avant de confirmer."))
            order.state = 'confirmed'

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        for order in self:
            # Check if all transit orders are done
            if any(ot.state != 'done' for ot in order.transit_order_ids):
                raise UserError(_("Tous les Ordres de Transit doivent être terminés avant de clôturer la commande."))
            order.state = 'done'

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_transit_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordres de Transit'),
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,form',
            'domain': [('customer_order_id', '=', self.id)],
            'context': {'default_customer_order_id': self.id},
        }
