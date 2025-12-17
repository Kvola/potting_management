# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PottingCreateDeliveryNoteWizard(models.TransientModel):
    """Wizard to create a delivery note from a transit order with lot selection."""
    
    _name = 'potting.create.delivery.note.wizard'
    _description = 'Wizard de création de bon de livraison'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        readonly=True,
    )
    
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
    
    product_type_display = fields.Char(
        string="Produit",
        compute='_compute_product_type_display',
    )
    
    ot_total_tonnage = fields.Float(
        related='transit_order_id.tonnage',
        string="Tonnage total OT",
        readonly=True,
    )
    
    ot_lot_count = fields.Integer(
        related='transit_order_id.lot_count',
        string="Nombre de lots OT",
        readonly=True,
    )
    
    # -------------------------------------------------------------------------
    # LOT SELECTION
    # -------------------------------------------------------------------------
    lot_ids = fields.Many2many(
        'potting.lot',
        'potting_create_delivery_note_wizard_lot_rel',
        'wizard_id',
        'lot_id',
        string="Lots à inclure",
        required=True,
        help="Sélectionnez les lots à inclure dans le bon de livraison. "
             "Par défaut, tous les lots de l'OT sont sélectionnés."
    )
    
    available_lot_ids = fields.Many2many(
        'potting.lot',
        'potting_create_delivery_note_wizard_available_lot_rel',
        'wizard_id',
        'lot_id',
        string="Lots disponibles",
        compute='_compute_available_lot_ids',
    )
    
    selected_lot_count = fields.Integer(
        string="Lots sélectionnés",
        compute='_compute_selected_totals',
    )
    
    selected_tonnage = fields.Float(
        string="Tonnage sélectionné (T)",
        compute='_compute_selected_totals',
        digits='Product Unit of Measure',
    )
    
    selected_units = fields.Integer(
        string="Unités sélectionnées",
        compute='_compute_selected_totals',
    )
    
    # -------------------------------------------------------------------------
    # DELIVERY INFORMATION
    # -------------------------------------------------------------------------
    date_delivery = fields.Date(
        string="Date de livraison",
        default=fields.Date.context_today,
        required=True,
    )
    
    bl_number = fields.Char(
        string="N° Bill of Lading",
        help="Numéro du connaissement"
    )
    
    bl_date = fields.Date(
        string="Date BL",
    )
    
    contract_number = fields.Char(
        string="N° Contrat",
    )
    
    destination = fields.Char(
        string="Destination",
    )
    
    transport_mode = fields.Selection([
        ('maritime', 'Maritime'),
        ('road', 'Routier'),
        ('air', 'Aérien'),
        ('rail', 'Ferroviaire'),
    ], string="Mode de transport", default='maritime')
    
    carrier_name = fields.Char(
        string="Transporteur",
    )
    
    note = fields.Text(
        string="Notes",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('product_type')
    def _compute_product_type_display(self):
        """Compute display name for product type."""
        product_labels = {
            'cocoa_mass': 'Masse de cacao',
            'cocoa_butter': 'Beurre de cacao',
            'cocoa_cake': 'Tourteau de cacao',
            'cocoa_powder': 'Poudre de cacao',
        }
        for wizard in self:
            wizard.product_type_display = product_labels.get(
                wizard.product_type, 
                wizard.product_type or ''
            )

    @api.depends('transit_order_id')
    def _compute_available_lot_ids(self):
        """Compute available lots from the transit order."""
        for wizard in self:
            if wizard.transit_order_id:
                # Get all lots from the OT (optionally filter by state)
                wizard.available_lot_ids = wizard.transit_order_id.lot_ids
            else:
                wizard.available_lot_ids = False

    @api.depends('lot_ids', 'lot_ids.current_tonnage', 'lot_ids.current_units')
    def _compute_selected_totals(self):
        """Compute totals for selected lots."""
        for wizard in self:
            wizard.selected_lot_count = len(wizard.lot_ids)
            wizard.selected_tonnage = sum(wizard.lot_ids.mapped('current_tonnage'))
            wizard.selected_units = sum(wizard.lot_ids.mapped('current_units'))

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        """Set default values, including all lots from the OT."""
        res = super().default_get(fields_list)
        
        # Get the transit order from context
        transit_order_id = self.env.context.get('active_id')
        if transit_order_id and self.env.context.get('active_model') == 'potting.transit.order':
            transit_order = self.env['potting.transit.order'].browse(transit_order_id)
            if transit_order.exists():
                res['transit_order_id'] = transit_order.id
                # By default, select all lots from the OT
                res['lot_ids'] = [(6, 0, transit_order.lot_ids.ids)]
                
                # Pre-fill destination from OT if available
                if transit_order.pod:
                    res['destination'] = transit_order.pod
        
        return res

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_create_delivery_note(self):
        """Create the delivery note with selected lots."""
        self.ensure_one()
        
        if not self.lot_ids:
            raise UserError(_("Veuillez sélectionner au moins un lot."))
        
        if not self.transit_order_id:
            raise UserError(_("Aucun Ordre de Transit sélectionné."))
        
        # Create the delivery note
        delivery_note_vals = {
            'transit_order_id': self.transit_order_id.id,
            'lot_ids': [(6, 0, self.lot_ids.ids)],
            'date_delivery': self.date_delivery,
            'bl_number': self.bl_number,
            'bl_date': self.bl_date,
            'contract_number': self.contract_number,
            'destination': self.destination,
            'transport_mode': self.transport_mode,
            'carrier_name': self.carrier_name,
            'note': self.note,
        }
        
        delivery_note = self.env['potting.delivery.note'].create(delivery_note_vals)
        
        # Post message on the transit order
        self.transit_order_id.message_post(
            body=_("📦 Bon de livraison <a href='#' data-oe-model='potting.delivery.note' "
                   "data-oe-id='%d'>%s</a> créé avec %d lot(s) pour un total de %.3f T.") % (
                delivery_note.id, delivery_note.name, 
                len(self.lot_ids), self.selected_tonnage
            )
        )
        
        # Return action to view the created delivery note
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bon de Livraison'),
            'res_model': 'potting.delivery.note',
            'res_id': delivery_note.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_select_all_lots(self):
        """Select all available lots."""
        self.ensure_one()
        self.lot_ids = [(6, 0, self.transit_order_id.lot_ids.ids)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'potting.create.delivery.note.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_deselect_all_lots(self):
        """Deselect all lots."""
        self.ensure_one()
        self.lot_ids = [(5, 0, 0)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'potting.create.delivery.note.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_potted_lots(self):
        """Select only potted lots."""
        self.ensure_one()
        potted_lots = self.transit_order_id.lot_ids.filtered(lambda l: l.state == 'potted')
        self.lot_ids = [(6, 0, potted_lots.ids)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'potting.create.delivery.note.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
