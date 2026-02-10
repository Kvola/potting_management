# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PottingQuickDeliveryWizard(models.TransientModel):
    """Wizard de livraison rapide - Sélection d'OT pour créer un BL."""
    
    _name = 'potting.quick.delivery.wizard'
    _description = 'Wizard de livraison rapide'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        domain="[('id', 'in', available_ot_ids)]",
        help="Sélectionnez l'OT pour lequel créer un bon de livraison"
    )
    
    available_ot_ids = fields.Many2many(
        'potting.transit.order',
        string="OT disponibles",
        compute='_compute_available_ot_ids',
    )
    
    # OT Info (readonly display)
    customer_id = fields.Many2one(
        related='transit_order_id.customer_id',
        string="Client",
        readonly=True,
    )
    
    consignee_id = fields.Many2one(
        related='transit_order_id.consignee_id',
        string="Destinataire",
        readonly=True,
    )
    
    product_type = fields.Selection(
        related='transit_order_id.product_type',
        string="Type de produit",
        readonly=True,
    )
    
    tonnage = fields.Float(
        related='transit_order_id.tonnage',
        string="Tonnage total",
        readonly=True,
    )
    
    lot_count = fields.Integer(
        related='transit_order_id.lot_count',
        string="Nombre de lots",
        readonly=True,
    )
    
    shipped_lot_count = fields.Integer(
        string="Lots expédiés",
        compute='_compute_shipped_info',
    )
    
    shipped_tonnage = fields.Float(
        string="Tonnage expédié (T)",
        compute='_compute_shipped_info',
    )
    
    pending_delivery_count = fields.Integer(
        string="Lots en attente livraison",
        compute='_compute_shipped_info',
    )
    
    delivery_status = fields.Selection(
        related='transit_order_id.delivery_status',
        string="Statut livraison",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends_context('uid')
    def _compute_available_ot_ids(self):
        """
        Compute available OTs for delivery.
        OT must have shipped lots (lots in containers with state 'shipped').
        """
        for wizard in self:
            # Get OTs that have shipped lots ready for delivery
            ots = self.env['potting.transit.order'].search([
                ('state', 'in', ['in_progress', 'ready_validation', 'done']),
                ('delivery_status', 'in', ['none', 'partial']),  # Not fully delivered
            ])
            
            # Filter OTs that have shipped containers with lots
            eligible_ots = self.env['potting.transit.order']
            for ot in ots:
                # Check if OT has lots in shipped containers
                shipped_lots = ot.lot_ids.filtered(
                    lambda l: l.container_id and l.container_id.state == 'shipped'
                )
                if shipped_lots:
                    eligible_ots |= ot
            
            wizard.available_ot_ids = eligible_ots

    @api.depends('transit_order_id')
    def _compute_shipped_info(self):
        """Compute shipped lots information."""
        for wizard in self:
            if wizard.transit_order_id:
                # Lots in shipped containers
                shipped_lots = wizard.transit_order_id.lot_ids.filtered(
                    lambda l: l.container_id and l.container_id.state == 'shipped'
                )
                wizard.shipped_lot_count = len(shipped_lots)
                wizard.shipped_tonnage = sum(shipped_lots.mapped('current_tonnage'))
                
                # Lots pending delivery (shipped but not yet delivered via BL)
                delivered_bl_lots = self.env['potting.delivery.note'].search([
                    ('transit_order_id', '=', wizard.transit_order_id.id),
                    ('state', '=', 'delivered'),
                ]).mapped('lot_ids')
                
                pending_lots = shipped_lots - delivered_bl_lots
                wizard.pending_delivery_count = len(pending_lots)
            else:
                wizard.shipped_lot_count = 0
                wizard.shipped_tonnage = 0
                wizard.pending_delivery_count = 0

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_open_delivery_wizard(self):
        """Open the delivery note creation wizard for the selected OT."""
        self.ensure_one()
        
        if not self.transit_order_id:
            raise UserError(_("Veuillez sélectionner un Ordre de Transit."))
        
        # Open the existing delivery note wizard with the selected OT
        return {
            'type': 'ir.actions.act_window',
            'name': _('Créer Bon de Livraison'),
            'res_model': 'potting.create.delivery.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.transit_order_id.id,
                'active_model': 'potting.transit.order',
                'default_transit_order_id': self.transit_order_id.id,
            },
        }

    def action_view_pending_deliveries(self):
        """View all OTs pending delivery."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('OT en attente de livraison'),
            'res_model': 'potting.transit.order',
            'view_mode': 'list,form',
            'domain': [
                ('state', 'in', ['in_progress', 'ready_validation', 'done']),
                ('delivery_status', 'in', ['none', 'partial']),
            ],
            'context': {'search_default_filter_pending_delivery': 1},
        }

    def action_view_delivery_notes(self):
        """View all delivery notes."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bons de Livraison'),
            'res_model': 'potting.delivery.note',
            'view_mode': 'list,form',
            'context': {},
        }
