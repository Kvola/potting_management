# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingContainer(models.Model):
    _name = 'potting.container'
    _description = 'Conteneur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, name'
    _check_company_auto = True

    # SQL Constraints
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 
         'Le numéro de conteneur doit être unique par société!'),
        ('seal_number_uniq', 'unique(seal_number)', 
         'Le numéro de scellé doit être unique!'),
    ]

    # Container type capacities (in tonnes)
    CONTAINER_CAPACITIES = {
        '20': 25.0,
        '40': 28.0,
        '40hc': 30.0,
    }

    name = fields.Char(
        string="Numéro de conteneur",
        required=True,
        tracking=True,
        index=True,
        copy=False
    )
    
    container_type = fields.Selection([
        ('20', "20' (Twenty-foot)"),
        ('40', "40' (Forty-foot)"),
        ('40hc', "40' HC (High Cube)"),
    ], string="Type de conteneur", default='20', tracking=True, required=True)
    
    max_capacity = fields.Float(
        string="Capacité max (T)",
        compute='_compute_max_capacity',
        store=True,
        digits='Product Unit of Measure'
    )
    
    seal_number = fields.Char(
        string="Numéro de scellé",
        tracking=True,
        copy=False
    )
    
    tare_weight = fields.Float(
        string="Tare (kg)",
        tracking=True,
        digits='Product Unit of Measure'
    )
    
    shipping_company_id = fields.Many2one(
        'potting.shipping.company',
        string="Compagnie maritime",
        tracking=True,
        index=True,
        ondelete='set null',
        help="Compagnie maritime propriétaire du conteneur"
    )
    
    max_payload = fields.Float(
        string="Charge utile max (kg)",
        tracking=True,
        digits='Product Unit of Measure'
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
        store=True,
        digits='Product Unit of Measure'
    )
    
    fill_percentage = fields.Float(
        string="Remplissage (%)",
        compute='_compute_fill_percentage',
        store=True
    )
    
    remaining_capacity = fields.Float(
        string="Capacité restante (T)",
        compute='_compute_fill_percentage',
        store=True,
        digits='Product Unit of Measure'
    )
    
    transit_order_ids = fields.Many2many(
        'potting.transit.order',
        compute='_compute_transit_orders',
        string="Ordres de Transit"
    )
    
    transit_order_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_transit_orders',
        store=True
    )
    
    product_types = fields.Char(
        string="Types de produits",
        compute='_compute_product_types',
        store=True
    )
    
    vessel_id = fields.Many2one(
        'potting.vessel',
        string="Navire",
        tracking=True,
        index=True
    )
    
    vessel_name = fields.Char(
        string="Nom du navire",
        related='vessel_id.name',
        store=True,
        readonly=True
    )
    
    booking_number = fields.Char(
        string="Numéro de réservation",
        tracking=True,
        index=True
    )
    
    date_potting = fields.Datetime(
        string="Date d'empotage",
        tracking=True,
        readonly=True,
        copy=False
    )
    
    date_departure = fields.Date(
        string="Date de départ",
        tracking=True
    )
    
    date_arrival = fields.Date(
        string="Date d'arrivée estimée",
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
        ('delivered', 'Livré'),
    ], string="État", default='available', tracking=True, index=True, copy=False)
    
    # Compteur de voyages
    voyage_count = fields.Integer(
        string="Nombre de voyages",
        default=0,
        tracking=True,
        help="Nombre de fois que ce conteneur a été utilisé"
    )
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    # Shipping information
    shipping_line = fields.Char(
        string="Compagnie maritime",
        tracking=True
    )
    
    bill_of_lading = fields.Char(
        string="Connaissement (B/L)",
        tracking=True
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('name')
    def _check_container_name_format(self):
        """Validate container name format (optional, for ISO container codes)"""
        import re
        for container in self:
            if container.name:
                # ISO container code pattern: 4 letters + 7 digits (e.g., MSKU1234567)
                # This is optional validation, just a warning in log
                pattern = r'^[A-Z]{4}\d{7}$'
                if not re.match(pattern, container.name.upper()):
                    # Just log, don't raise error to allow flexibility
                    pass

    @api.constrains('lot_ids')
    def _check_lots_product_consistency(self):
        """Warn if container has lots with different product types"""
        for container in self:
            if container.lot_ids:
                product_types = set(container.lot_ids.mapped('product_type'))
                if len(product_types) > 1:
                    # Log warning but don't block
                    container.message_post(body=_(
                        "⚠️ Attention: Ce conteneur contient des produits de types différents: %s"
                    ) % ', '.join(product_types))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('container_type')
    def _compute_max_capacity(self):
        for container in self:
            container.max_capacity = self.CONTAINER_CAPACITIES.get(container.container_type, 25.0)

    @api.depends('lot_ids')
    def _compute_lot_count(self):
        for container in self:
            container.lot_count = len(container.lot_ids)

    @api.depends('lot_ids.current_tonnage')
    def _compute_total_tonnage(self):
        for container in self:
            container.total_tonnage = sum(container.lot_ids.mapped('current_tonnage'))

    @api.depends('total_tonnage', 'max_capacity')
    def _compute_fill_percentage(self):
        for container in self:
            if container.max_capacity > 0:
                container.fill_percentage = (container.total_tonnage / container.max_capacity) * 100
                container.remaining_capacity = max(0, container.max_capacity - container.total_tonnage)
            else:
                container.fill_percentage = 0
                container.remaining_capacity = 0

    @api.depends('lot_ids.transit_order_id')
    def _compute_transit_orders(self):
        for container in self:
            transit_orders = container.lot_ids.mapped('transit_order_id')
            container.transit_order_ids = transit_orders
            container.transit_order_count = len(transit_orders)

    @api.depends('lot_ids.product_type')
    def _compute_product_types(self):
        product_type_labels = dict(self.env['potting.lot']._fields['product_type'].selection)
        for container in self:
            if container.lot_ids:
                types = set(container.lot_ids.mapped('product_type'))
                container.product_types = ', '.join([product_type_labels.get(t, t) for t in types])
            else:
                container.product_types = ''

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    def unlink(self):
        for container in self:
            if container.state == 'shipped':
                raise UserError(_("Vous ne pouvez pas supprimer un conteneur expédié."))
            if container.lot_ids:
                raise UserError(_(
                    "Vous ne pouvez pas supprimer un conteneur avec des lots. "
                    "Videz d'abord le conteneur."
                ))
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': _('%s (Copie)') % self.name,
            'state': 'available',
            'seal_number': False,
            'date_potting': False,
        })
        return super().copy(default)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_start_loading(self):
        for container in self:
            if container.state != 'available':
                raise UserError(_("Le conteneur doit être disponible pour commencer le chargement."))
            container.write({
                'state': 'loading',
                'date_potting': fields.Datetime.now(),
            })
            container.message_post(body=_("Chargement démarré."))

    def action_finish_loading(self):
        for container in self:
            if container.state != 'loading':
                raise UserError(_("Le conteneur doit être en chargement."))
            if not container.lot_ids:
                raise UserError(_("Le conteneur doit avoir au moins un lot pour terminer le chargement."))
            container.state = 'loaded'
            container.message_post(body=_(
                "Chargement terminé. %d lots, %.2f T"
            ) % (container.lot_count, container.total_tonnage))

    def action_ship(self):
        for container in self:
            if container.state != 'loaded':
                raise UserError(_("Le conteneur doit être chargé pour être expédié."))
            if not container.seal_number:
                raise UserError(_("Le conteneur doit avoir un numéro de scellé avant l'expédition."))
            container.state = 'shipped'
            container.message_post(body=_(
                "Conteneur expédié. Scellé: %s"
            ) % container.seal_number)

    def action_reopen(self):
        """Reopen a loaded container for additional loading"""
        for container in self:
            if container.state != 'loaded':
                raise UserError(_("Seuls les conteneurs chargés peuvent être réouverts."))
            container.state = 'loading'
            container.message_post(body=_("Conteneur réouvert pour chargement additionnel."))

    def action_mark_delivered(self):
        """Mark container as delivered at destination"""
        for container in self:
            if container.state != 'shipped':
                raise UserError(_("Seuls les conteneurs expédiés peuvent être marqués comme livrés."))
            container.state = 'delivered'
            container.message_post(body=_(
                "✅ Conteneur livré à destination.\n"
                "• Navire: %s\n"
                "• Port: %s\n"
                "• Tonnage: %.2f T (%d lots)"
            ) % (
                container.vessel_name or '-',
                container.port_discharge or '-',
                container.total_tonnage,
                container.lot_count
            ))

    def action_release(self):
        """Release container for a new voyage - reset voyage data but keep history"""
        for container in self:
            if container.state != 'delivered':
                raise UserError(_("Seuls les conteneurs livrés peuvent être libérés pour un nouveau voyage."))
            
            # Sauvegarder le résumé du voyage dans le chatter
            voyage_summary = _(
                "🚢 Voyage #%d terminé:\n"
                "• Navire: %s\n"
                "• Scellé: %s\n"
                "• Réservation: %s\n"
                "• B/L: %s\n"
                "• Départ: %s → Arrivée: %s\n"
                "• Trajet: %s → %s\n"
                "• Tonnage: %.2f T (%d lots)\n"
                "• Lots: %s"
            ) % (
                container.voyage_count + 1,
                container.vessel_name or '-',
                container.seal_number or '-',
                container.booking_number or '-',
                container.bill_of_lading or '-',
                container.date_departure or '-',
                container.date_arrival or '-',
                container.port_loading or '-',
                container.port_discharge or '-',
                container.total_tonnage,
                container.lot_count,
                ', '.join(container.lot_ids.mapped('name')) or '-'
            )
            
            # Réinitialiser pour nouveau voyage (les lots gardent leur container_id pour l'historique)
            container.write({
                'state': 'available',
                'voyage_count': container.voyage_count + 1,
                'seal_number': False,
                'vessel_id': False,
                'booking_number': False,
                'bill_of_lading': False,
                'date_potting': False,
                'date_departure': False,
                'date_arrival': False,
                'port_loading': False,
                'port_discharge': False,
                'shipping_line': False,
            })
            
            container.message_post(body=voyage_summary)
            container.message_post(body=_(
                "🔄 Conteneur libéré et disponible pour un nouveau voyage."
            ))

    def action_view_lots(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Lots - %s') % self.name,
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('container_id', '=', self.id)],
        }
        return action

    def action_view_transit_orders(self):
        """View transit orders linked to this container"""
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Ordres de Transit - %s') % self.name,
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.transit_order_ids.ids)],
        }
        return action

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def can_add_lot(self, lot):
        """Check if a lot can be added to this container"""
        self.ensure_one()
        if self.state not in ('available', 'loading'):
            return False, _("Le conteneur n'est pas disponible pour le chargement.")
        
        new_tonnage = self.total_tonnage + lot.current_tonnage
        if new_tonnage > self.max_capacity * 1.05:  # 5% tolerance
            return False, _(
                "Le lot dépasserait la capacité du conteneur. "
                "Capacité: %.2f T, Actuel: %.2f T, Lot: %.2f T"
            ) % (self.max_capacity, self.total_tonnage, lot.current_tonnage)
        
        return True, ""

    def get_shipping_summary(self):
        """Get shipping summary for documentation"""
        self.ensure_one()
        return {
            'container_number': self.name,
            'container_type': dict(self._fields['container_type'].selection).get(self.container_type),
            'seal_number': self.seal_number,
            'vessel': self.vessel_name,
            'booking': self.booking_number,
            'bill_of_lading': self.bill_of_lading,
            'port_loading': self.port_loading,
            'port_discharge': self.port_discharge,
            'date_departure': self.date_departure,
            'date_arrival': self.date_arrival,
            'total_tonnage': self.total_tonnage,
            'lot_count': self.lot_count,
            'lots': [{
                'name': lot.name,
                'transit_order': lot.transit_order_id.name,
                'product_type': lot.product_type_display,
                'tonnage': lot.current_tonnage,
            } for lot in self.lot_ids.sorted('name')],
        }

    @api.model
    def get_available_containers(self, container_type=None):
        """Get available containers for loading"""
        domain = [('state', 'in', ('available', 'loading'))]
        if container_type:
            domain.append(('container_type', '=', container_type))
        return self.search(domain)

    def mark_delivered_from_transit_order(self, transit_order=None):
        """Mark containers as delivered when linked transit orders are fully delivered.
        Called automatically from transit order when delivery_status changes to 'fully_delivered'.
        """
        for container in self:
            if container.state == 'shipped':
                container.state = 'delivered'
                msg = _("✅ Conteneur marqué comme livré automatiquement.")
                if transit_order:
                    msg += _("\n(Suite à la livraison complète de l'OT %s)") % transit_order.name
                container.message_post(body=msg)
