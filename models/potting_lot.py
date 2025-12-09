# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PottingLot(models.Model):
    _name = 'potting.lot'
    _description = 'Lot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string="Numéro de lot",
        required=True,
        tracking=True,
        index=True
    )
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    customer_order_id = fields.Many2one(
        related='transit_order_id.customer_order_id',
        string="Commande client",
        store=True
    )
    
    customer_id = fields.Many2one(
        related='transit_order_id.customer_id',
        string="Client",
        store=True
    )
    
    consignee_id = fields.Many2one(
        related='transit_order_id.consignee_id',
        string="Destinataire",
        store=True
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit", required=True, tracking=True)
    
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        tracking=True
    )
    
    target_tonnage = fields.Float(
        string="Tonnage cible (T)",
        required=True,
        tracking=True,
        help="Capacité maximale du lot"
    )
    
    current_tonnage = fields.Float(
        string="Tonnage actuel (T)",
        compute='_compute_current_tonnage',
        store=True,
        tracking=True
    )
    
    remaining_tonnage = fields.Float(
        string="Tonnage restant (T)",
        compute='_compute_current_tonnage',
        store=True
    )
    
    fill_percentage = fields.Float(
        string="Remplissage (%)",
        compute='_compute_current_tonnage',
        store=True
    )
    
    is_full = fields.Boolean(
        string="Capacité atteinte",
        compute='_compute_current_tonnage',
        store=True
    )
    
    production_line_ids = fields.One2many(
        'potting.production.line',
        'lot_id',
        string="Lignes de production"
    )
    
    container_id = fields.Many2one(
        'potting.container',
        string="Conteneur",
        tracking=True
    )
    
    date_potted = fields.Datetime(
        string="Date d'empotage",
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_production', 'En production'),
        ('ready', 'Prêt pour empotage'),
        ('potted', 'Empoté'),
    ], string="État", default='draft', tracking=True)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )
    
    # Quality fields
    quality_check = fields.Boolean(
        string="Contrôle qualité effectué",
        tracking=True
    )
    
    quality_note = fields.Text(
        string="Notes qualité"
    )

    @api.depends('production_line_ids.tonnage', 'target_tonnage')
    def _compute_current_tonnage(self):
        for lot in self:
            lot.current_tonnage = sum(lot.production_line_ids.mapped('tonnage'))
            lot.remaining_tonnage = max(0, lot.target_tonnage - lot.current_tonnage)
            if lot.target_tonnage > 0:
                lot.fill_percentage = (lot.current_tonnage / lot.target_tonnage) * 100
            else:
                lot.fill_percentage = 0
            # Consider lot as full if at least 95% filled
            lot.is_full = lot.fill_percentage >= 95

    def action_start_production(self):
        self.write({'state': 'in_production'})

    def action_mark_ready(self):
        """Mark lot as ready for potting when capacity is reached"""
        for lot in self:
            if not lot.is_full:
                raise UserError(_(
                    "Le lot %s n'a pas atteint sa capacité. "
                    "Remplissage actuel: %.2f%%"
                ) % (lot.name, lot.fill_percentage))
            lot.state = 'ready'

    def action_pot(self):
        """Open wizard to pot the lot into a container"""
        self.ensure_one()
        if self.state != 'ready':
            raise UserError(_("Le lot doit être prêt pour l'empotage."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Empotage du lot'),
            'res_model': 'potting.pot.lot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_lot_id': self.id},
        }

    def action_confirm_potting(self, container_id):
        """Confirm potting of the lot into a container"""
        self.ensure_one()
        self.write({
            'container_id': container_id,
            'date_potted': fields.Datetime.now(),
            'state': 'potted',
        })
        
        # Check if all lots of the OT are potted
        transit_order = self.transit_order_id
        if all(lot.state == 'potted' for lot in transit_order.lot_ids):
            transit_order.action_mark_ready()

    def action_view_productions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Productions'),
            'res_model': 'potting.production.line',
            'view_mode': 'tree,form',
            'domain': [('lot_id', '=', self.id)],
            'context': {'default_lot_id': self.id},
        }
