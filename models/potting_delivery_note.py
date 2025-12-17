# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingDeliveryNote(models.Model):
    """Bon de Livraison (BL) pour les Ordres de Transit."""
    
    _name = 'potting.delivery.note'
    _description = 'Bon de Livraison'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _check_company_auto = True

    # SQL Constraints
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 
         'Le numéro de BL doit être unique par société!'),
    ]

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string="Numéro BL",
        required=True,
        tracking=True,
        index=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        ondelete='cascade',
        tracking=True,
        check_company=True,
        index=True,
        domain="[('state', 'in', ['in_progress', 'ready_validation', 'done'])]"
    )
    
    customer_order_id = fields.Many2one(
        related='transit_order_id.customer_order_id',
        string="Commande client",
        store=True,
        index=True
    )
    
    customer_id = fields.Many2one(
        related='transit_order_id.customer_id',
        string="Client",
        store=True,
        index=True
    )
    
    consignee_id = fields.Many2one(
        related='transit_order_id.consignee_id',
        string="Destinataire",
        store=True
    )
    
    product_type = fields.Selection(
        related='transit_order_id.product_type',
        string="Type de produit",
        store=True,
        index=True
    )
    
    product_id = fields.Many2one(
        related='transit_order_id.product_id',
        string="Produit",
        store=True
    )
    
    vessel_id = fields.Many2one(
        related='transit_order_id.vessel_id',
        string="Navire",
        store=True
    )
    
    vessel_name = fields.Char(
        related='transit_order_id.vessel_name',
        string="Nom du navire",
        store=True
    )
    
    pod = fields.Char(
        related='transit_order_id.pod',
        string="Port de déchargement",
        store=True
    )
    
    booking_number = fields.Char(
        related='transit_order_id.booking_number',
        string="N° Booking",
        store=True
    )
    
    campaign_period = fields.Char(
        related='transit_order_id.campaign_period',
        string="Campagne",
        store=True
    )
    
    # -------------------------------------------------------------------------
    # LOTS SELECTION
    # -------------------------------------------------------------------------
    lot_ids = fields.Many2many(
        'potting.lot',
        'potting_delivery_note_lot_rel',
        'delivery_note_id',
        'lot_id',
        string="Lots",
        required=True,
        tracking=True,
        domain="[('transit_order_id', '=', transit_order_id)]"
    )
    
    lot_count = fields.Integer(
        string="Nombre de lots",
        compute='_compute_lot_count',
        store=True
    )
    
    total_tonnage = fields.Float(
        string="Tonnage total (T)",
        compute='_compute_total_tonnage',
        store=True,
        digits='Product Unit of Measure'
    )
    
    total_units = fields.Integer(
        string="Unités totales",
        compute='_compute_total_tonnage',
        store=True,
        help="Nombre total d'unités de conditionnement"
    )
    
    # -------------------------------------------------------------------------
    # DELIVERY INFORMATION
    # -------------------------------------------------------------------------
    date_delivery = fields.Date(
        string="Date de livraison",
        default=fields.Date.context_today,
        tracking=True,
        index=True
    )
    
    bl_number = fields.Char(
        string="N° Bill of Lading",
        tracking=True,
        help="Numéro du connaissement"
    )
    
    bl_date = fields.Date(
        string="Date BL",
        tracking=True
    )
    
    contract_number = fields.Char(
        string="N° Contrat",
        tracking=True
    )
    
    destination = fields.Char(
        string="Destination",
        tracking=True
    )
    
    transport_mode = fields.Selection([
        ('maritime', 'Maritime'),
        ('road', 'Routier'),
        ('air', 'Aérien'),
        ('rail', 'Ferroviaire'),
    ], string="Mode de transport", default='maritime', tracking=True)
    
    carrier_name = fields.Char(
        string="Transporteur",
        tracking=True
    )
    
    driver_name = fields.Char(
        string="Nom du chauffeur",
        tracking=True
    )
    
    vehicle_number = fields.Char(
        string="N° Véhicule / Conteneur",
        tracking=True
    )
    
    # -------------------------------------------------------------------------
    # STATE AND METADATA
    # -------------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ], string="État", default='draft', tracking=True, index=True, copy=False)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    date_created = fields.Date(
        string="Date de création",
        default=fields.Date.context_today,
        readonly=True,
        index=True
    )
    
    created_by_id = fields.Many2one(
        'res.users',
        string="Créé par",
        default=lambda self: self.env.user,
        readonly=True
    )
    
    date_confirmed = fields.Datetime(
        string="Date de confirmation",
        readonly=True,
        copy=False
    )
    
    confirmed_by_id = fields.Many2one(
        'res.users',
        string="Confirmé par",
        readonly=True,
        copy=False
    )
    
    date_delivered = fields.Datetime(
        string="Date de livraison effective",
        readonly=True,
        copy=False
    )
    
    delivered_by_id = fields.Many2one(
        'res.users',
        string="Livré par",
        readonly=True,
        copy=False
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('lot_ids')
    def _compute_lot_count(self):
        for note in self:
            note.lot_count = len(note.lot_ids)

    @api.depends('lot_ids', 'lot_ids.current_tonnage', 'lot_ids.current_units')
    def _compute_total_tonnage(self):
        for note in self:
            note.total_tonnage = sum(note.lot_ids.mapped('current_tonnage'))
            note.total_units = sum(note.lot_ids.mapped('current_units'))

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('lot_ids', 'transit_order_id')
    def _check_lots_belong_to_ot(self):
        """Ensure all selected lots belong to the transit order."""
        for note in self:
            if note.lot_ids and note.transit_order_id:
                invalid_lots = note.lot_ids.filtered(
                    lambda l: l.transit_order_id != note.transit_order_id
                )
                if invalid_lots:
                    raise ValidationError(_(
                        "Les lots suivants n'appartiennent pas à l'OT sélectionné: %s"
                    ) % ', '.join(invalid_lots.mapped('name')))

    @api.constrains('lot_ids')
    def _check_lots_not_empty(self):
        """Ensure at least one lot is selected."""
        for note in self:
            if note.state != 'cancelled' and not note.lot_ids:
                raise ValidationError(_("Veuillez sélectionner au moins un lot."))

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau') or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('potting.delivery.note') or _('Nouveau')
        return super().create(vals_list)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': _('Nouveau'),
            'state': 'draft',
            'date_created': fields.Date.context_today(self),
            'date_confirmed': False,
            'confirmed_by_id': False,
            'date_delivered': False,
            'delivered_by_id': False,
        })
        return super().copy(default)

    def unlink(self):
        for note in self:
            if note.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les BL en brouillon ou annulés. "
                    "Le BL '%s' est en état '%s'."
                ) % (note.name, dict(note._fields['state'].selection).get(note.state)))
        return super().unlink()

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_confirm(self):
        """Confirm the delivery note."""
        for note in self:
            if note.state != 'draft':
                raise UserError(_("Seuls les BL en brouillon peuvent être confirmés."))
            if not note.lot_ids:
                raise UserError(_("Veuillez sélectionner au moins un lot avant de confirmer."))
            
            note.write({
                'state': 'confirmed',
                'date_confirmed': fields.Datetime.now(),
                'confirmed_by_id': self.env.user.id,
            })
            note.message_post(body=_("✅ Bon de livraison confirmé par %s.") % self.env.user.name)

    def action_deliver(self):
        """Mark the delivery note as delivered."""
        for note in self:
            if note.state != 'confirmed':
                raise UserError(_("Seuls les BL confirmés peuvent être marqués comme livrés."))
            
            note.write({
                'state': 'delivered',
                'date_delivered': fields.Datetime.now(),
                'delivered_by_id': self.env.user.id,
            })
            note.message_post(body=_("🚚 Bon de livraison marqué comme livré par %s.") % self.env.user.name)
            
            # Update BL info on selected lots
            for lot in note.lot_ids:
                lot.write({
                    'bl_number': note.bl_number or note.name,
                    'bl_date': note.bl_date or note.date_delivery,
                    'destination': note.destination,
                    'contract_number': note.contract_number,
                })

    def action_cancel(self):
        """Cancel the delivery note."""
        for note in self:
            if note.state == 'delivered':
                raise UserError(_("Les BL livrés ne peuvent pas être annulés."))
            note.state = 'cancelled'
            note.message_post(body=_("❌ Bon de livraison annulé par %s.") % self.env.user.name)

    def action_draft(self):
        """Reset to draft state."""
        for note in self:
            if note.state == 'delivered':
                raise UserError(_("Les BL livrés ne peuvent pas être remis en brouillon."))
            note.state = 'draft'
            note.message_post(body=_("🔄 Bon de livraison remis en brouillon par %s.") % self.env.user.name)

    def action_view_lots(self):
        """View the lots of this delivery note."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lots - %s') % self.name,
            'res_model': 'potting.lot',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.lot_ids.ids)],
            'context': {'create': False},
        }

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def get_delivery_summary(self):
        """Get delivery summary for reporting."""
        self.ensure_one()
        return {
            'name': self.name,
            'transit_order': self.transit_order_id.name,
            'customer': self.customer_id.name,
            'consignee': self.consignee_id.name,
            'product_type': dict(self._fields['product_type'].selection).get(self.product_type),
            'total_tonnage': self.total_tonnage,
            'total_units': self.total_units,
            'lot_count': self.lot_count,
            'date_delivery': self.date_delivery,
            'destination': self.destination,
            'lots': [{
                'name': lot.name,
                'tonnage': lot.current_tonnage,
                'units': lot.current_units,
                'container': lot.container_id.name if lot.container_id else '',
            } for lot in self.lot_ids.sorted('name')],
        }
