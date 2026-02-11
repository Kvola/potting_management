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
    
    # -------------------------------------------------------------------------
    # BILL OF LADING - Informations externes (compagnie maritime)
    # -------------------------------------------------------------------------
    bl_external_number = fields.Char(
        string="N° BL (Compagnie maritime)",
        tracking=True,
        index=True,
        help="Numéro du Bill of Lading fourni par la compagnie maritime"
    )
    
    shipping_company_id = fields.Many2one(
        'potting.shipping.company',
        string="Compagnie maritime",
        tracking=True,
        index=True,
        ondelete='set null',
        help="Compagnie maritime qui a émis le BL"
    )
    
    port_of_loading = fields.Char(
        string="Port de chargement",
        tracking=True,
        default="Abidjan",
        help="Port où la marchandise a été embarquée"
    )
    
    port_of_discharge = fields.Char(
        string="Port de destination",
        tracking=True,
        help="Port de destination finale"
    )
    
    date_shipment = fields.Date(
        string="Date d'embarquement",
        tracking=True,
        help="Date effective d'embarquement sur le navire"
    )
    
    shipped_weight = fields.Float(
        string="Poids embarqué (T)",
        digits='Product Unit of Measure',
        tracking=True,
        help="Poids total embarqué en tonnes (tel qu'indiqué sur le BL)"
    )
    
    number_of_bags = fields.Integer(
        string="Nombre de sacs",
        tracking=True,
        help="Nombre total de sacs embarqués"
    )
    
    # Conteneurs liés au BL
    container_ids = fields.Many2many(
        'potting.container',
        'potting_delivery_note_container_rel',
        'delivery_note_id',
        'container_id',
        string="Conteneurs",
        tracking=True,
        help="Conteneurs spécifiques embarqués avec ce BL"
    )
    
    container_count = fields.Integer(
        string="Nombre de conteneurs",
        compute='_compute_container_count',
        store=True
    )
    
    # Pièces jointes BL (scans PDF)
    bl_attachment_ids = fields.Many2many(
        'ir.attachment',
        'potting_delivery_note_attachment_rel',
        'delivery_note_id',
        'attachment_id',
        string="Documents BL",
        help="Scans du Bill of Lading original (PDF)"
    )
    
    bl_attachment_count = fields.Integer(
        string="Nombre de documents",
        compute='_compute_bl_attachment_count'
    )
    
    campaign_period = fields.Char(
        related='transit_order_id.campaign_period',
        string="Campagne",
        store=True
    )
    
    # -------------------------------------------------------------------------
    # INFORMATIONS CONTRAT (auto-remplies depuis OT/Contrat)
    # -------------------------------------------------------------------------
    contract_number_display = fields.Char(
        string="N° Contrat (Ref)",
        related='customer_order_id.contract_number',
        store=True,
        readonly=True,
        help="Numéro du contrat client (depuis la commande)"
    )
    
    contract_tonnage = fields.Float(
        string="Tonnage contrat (T)",
        related='customer_order_id.contract_tonnage',
        store=True,
        readonly=True,
    )
    
    contract_unit_price = fields.Monetary(
        string="Prix unitaire contrat",
        related='customer_order_id.unit_price',
        store=True,
        readonly=True,
        currency_field='contract_currency_id',
    )
    
    contract_currency_id = fields.Many2one(
        'res.currency',
        string="Devise contrat",
        related='customer_order_id.currency_id',
        store=True,
        readonly=True,
    )
    
    ot_tonnage = fields.Float(
        string="Tonnage OT (T)",
        related='transit_order_id.tonnage',
        store=True,
        readonly=True,
    )
    
    ot_formule_reference = fields.Char(
        string="Réf. Formule",
        related='transit_order_id.formule_reference',
        store=True,
        readonly=True,
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
    # INVOICE INFORMATION (Facturation partielle)
    # -------------------------------------------------------------------------
    invoice_id = fields.Many2one(
        'account.move',
        string="Facture",
        copy=False,
        tracking=True,
        domain="[('move_type', '=', 'out_invoice'), ('potting_transit_order_id', '=', transit_order_id)]",
        help="Facture générée ou liée manuellement à ce bon de livraison"
    )
    
    invoice_state = fields.Selection(
        string="État facture",
        related='invoice_id.state',
        store=True
    )
    
    is_invoiced = fields.Boolean(
        string="Facturé",
        compute='_compute_is_invoiced',
        store=True
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

    @api.depends('invoice_id')
    def _compute_is_invoiced(self):
        for note in self:
            note.is_invoiced = bool(note.invoice_id)
    
    @api.depends('container_ids')
    def _compute_container_count(self):
        for note in self:
            note.container_count = len(note.container_ids)
    
    def _compute_bl_attachment_count(self):
        for note in self:
            note.bl_attachment_count = len(note.bl_attachment_ids)

    # -------------------------------------------------------------------------
    # ONCHANGE - AUTO-REMPLISSAGE DEPUIS OT/CONTRAT
    # -------------------------------------------------------------------------
    @api.onchange('transit_order_id')
    def _onchange_transit_order_id(self):
        """Auto-remplir les informations du contrat et de l'OT lors de la sélection."""
        if self.transit_order_id:
            ot = self.transit_order_id
            # Auto-remplir le numéro de contrat depuis la commande client
            if ot.customer_order_id and ot.customer_order_id.contract_number:
                self.contract_number = ot.customer_order_id.contract_number
            # Auto-remplir la destination depuis le port de déchargement de l'OT
            if ot.pod:
                self.destination = ot.pod
            # Auto-remplir le port de destination
            if ot.pod and not self.port_of_discharge:
                self.port_of_discharge = ot.pod
            # Auto-remplir la compagnie maritime depuis le navire
            if ot.vessel_id and ot.vessel_id.shipping_company_id and not self.shipping_company_id:
                self.shipping_company_id = ot.vessel_id.shipping_company_id

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
        
        records = super().create(vals_list)
        
        # Générer automatiquement la facture de l'OT lors de la création du BL
        for record in records:
            record._auto_create_invoice_for_transit_order()
        
        return records

    def _auto_create_invoice_for_transit_order(self):
        """
        Génère automatiquement une facture partielle pour le tonnage du BL.
        Facturation partielle : chaque BL génère sa propre facture pour le tonnage livré.
        """
        self.ensure_one()
        
        transit_order = self.transit_order_id
        if not transit_order:
            return
        
        # Vérifier si ce BL a déjà une facture
        if self.invoice_id:
            return
        
        # Vérifier si l'OT est dans un état permettant la facturation
        if transit_order.state not in ('ready_validation', 'done', 'in_progress'):
            return
        
        # Vérifier si les droits d'exportation ont été encaissés
        if not transit_order.export_duty_collected:
            self.message_post(body=_(
                "⚠️ La facture n'a pas été générée car les droits d'exportation "
                "de l'OT %s n'ont pas encore été encaissés."
            ) % transit_order.name)
            return
        
        # Vérifier si le module account est installé
        if 'account.move' not in self.env:
            return
        
        # Vérifier qu'il y a du tonnage à facturer
        if self.total_tonnage <= 0:
            self.message_post(body=_(
                "⚠️ Aucune facture générée : le tonnage du BL est de 0."
            ))
            return
        
        # Vérifier qu'on ne dépasse pas le reste à facturer de l'OT
        if self.total_tonnage > transit_order.remaining_to_invoice + 0.001:
            self.message_post(body=_(
                "⚠️ Le tonnage du BL (%.3f T) dépasse le reste à facturer de l'OT (%.3f T). "
                "Facture non générée automatiquement."
            ) % (self.total_tonnage, transit_order.remaining_to_invoice))
            return
        
        try:
            # Créer la facture partielle pour le tonnage de ce BL
            transit_order._create_invoice(tonnage=self.total_tonnage, delivery_note=self)
            self.message_post(body=_(
                "✅ Facture %s générée automatiquement pour %.3f T (OT: %s)."
            ) % (self.invoice_id.name, self.total_tonnage, transit_order.name))
        except Exception as e:
            self.message_post(body=_(
                "⚠️ Erreur lors de la génération automatique de la facture: %s"
            ) % str(e))

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
        """Mark the delivery note as delivered.
        
        Requires:
        - BL must be in 'confirmed' state
        - Invoice must exist (is_invoiced = True)
        """
        for note in self:
            if note.state != 'confirmed':
                raise UserError(_("Seuls les BL confirmés peuvent être marqués comme livrés."))
            
            # Vérification de la facture - condition obligatoire pour l'export
            if not note.is_invoiced:
                raise UserError(_(
                    "⚠️ Impossible de marquer comme livré !\n\n"
                    "La facture client est obligatoire avant l'envoi de la marchandise.\n\n"
                    "Actions requises :\n"
                    "1. Créer la facture client depuis l'OT ou ce BL\n"
                    "2. Lier la facture à ce bon de livraison\n\n"
                    "BL : %s"
                ) % note.name)
            
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
            
            # Vérifier si tous les lots des conteneurs concernés sont livrés
            # et marquer ces conteneurs comme "livrés"
            note._check_containers_delivery()

    def _check_containers_delivery(self):
        """Vérifie si tous les lots d'un conteneur sont livrés et marque le conteneur comme livré."""
        self.ensure_one()
        
        # Récupérer tous les conteneurs liés aux lots de ce BL
        containers = self.lot_ids.mapped('container_id').filtered(
            lambda c: c.state == 'shipped'
        )
        
        for container in containers:
            # Vérifier si tous les lots du conteneur sont livrés
            all_lots_delivered = True
            for lot in container.lot_ids:
                # Un lot est considéré livré s'il apparaît dans un BL à l'état 'delivered'
                delivered_bls = self.search([
                    ('lot_ids', 'in', lot.id),
                    ('state', '=', 'delivered')
                ])
                if not delivered_bls:
                    all_lots_delivered = False
                    break
            
            if all_lots_delivered and container.lot_ids:
                container.write({'state': 'delivered'})
                container.message_post(body=_(
                    "✅ Conteneur marqué comme livré automatiquement.\n"
                    "Tous les lots (%d) ont été livrés.\n"
                    "(Dernier BL: %s)"
                ) % (len(container.lot_ids), self.name))

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

    def action_view_containers(self):
        """View the containers of this delivery note."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Conteneurs - %s') % self.name,
            'res_model': 'potting.container',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.container_ids.ids)],
            'context': {'create': False},
        }

    def action_view_attachments(self):
        """View the BL attachments."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents BL - %s') % self.name,
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.bl_attachment_ids.ids)],
            'context': {
                'default_res_model': 'potting.delivery.note',
                'default_res_id': self.id,
            },
        }

    def action_view_invoice(self):
        """View the invoice for this delivery note."""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("Aucune facture n'a été créée pour ce BL."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_create_invoice(self):
        """Manually create an invoice for this delivery note."""
        self.ensure_one()
        
        if self.invoice_id:
            raise UserError(_("Une facture existe déjà pour ce BL."))
        
        if self.state == 'cancelled':
            raise UserError(_("Impossible de facturer un BL annulé."))
        
        transit_order = self.transit_order_id
        
        if not transit_order.export_duty_collected:
            raise UserError(_(
                "Les droits d'exportation de l'OT %s doivent être encaissés avant de facturer."
            ) % transit_order.name)
        
        if self.total_tonnage <= 0:
            raise UserError(_("Le tonnage du BL est de 0. Impossible de facturer."))
        
        if self.total_tonnage > transit_order.remaining_to_invoice + 0.001:
            raise UserError(_(
                "Le tonnage du BL (%.3f T) dépasse le reste à facturer de l'OT (%.3f T)."
            ) % (self.total_tonnage, transit_order.remaining_to_invoice))
        
        return transit_order._create_invoice(tonnage=self.total_tonnage, delivery_note=self)

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
