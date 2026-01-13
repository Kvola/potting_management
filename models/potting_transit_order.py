# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import math


class PottingTransitOrder(models.Model):
    _name = 'potting.transit.order'
    _description = 'Ordre de Transit (OT)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _check_company_auto = True

    # SQL Constraints
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 
         'Le numéro OT doit être unique!'),
        ('tonnage_positive', 'CHECK(tonnage > 0)', 
         'Le tonnage doit être supérieur à 0!'),
        ('ot_reference_uniq', 'unique(ot_reference)',
         'La référence OT doit être unique!'),
        ('booking_number_company_uniq', 'unique(booking_number, company_id)',
         'Le numéro de booking doit être unique par société!'),
    ]

    name = fields.Char(
        string="Numéro OT",
        required=True,
        tracking=True,
        index=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    
    ot_reference = fields.Char(
        string="Référence OT",
        tracking=True,
        index=True,
        copy=True,
        help="Référence alternative de l'OT (ex: OT10532)"
    )
    
    # Champ technique pour savoir si l'OT a été créé depuis une commande
    is_created_from_order = fields.Boolean(
        string="Créé depuis une commande",
        default=False,
        copy=False,
        help="Indique si l'OT a été créé directement depuis une commande client"
    )
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        required=True,
        ondelete='cascade',
        tracking=True,
        check_company=True,
        domain="[('state', 'not in', ['done', 'cancelled'])]"
    )
    
    # =========================================================================
    # CHAMP - FORMULE (FO) - OBLIGATOIRE
    # =========================================================================
    
    formule_id = fields.Many2one(
        'potting.formule',
        string="Formule (FO)",
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        domain="[('state', 'in', ['validated', 'partial_paid']), "
               "('transit_order_id', '=', False)]",
        help="Formule du Conseil Café-Cacao obligatoire pour cet OT. "
             "Une FO ne peut être liée qu'à un seul OT."
    )
    
    formule_reference = fields.Char(
        string="Réf. FO",
        related='formule_id.reference_ccc',
        store=True,
        help="Référence CCC de la Formule"
    )
    
    formule_prix_tonnage = fields.Monetary(
        string="Prix FO (FCFA/T)",
        related='formule_id.prix_tonnage',
        currency_field='formule_currency_id',
        help="Prix au tonnage défini dans la Formule"
    )
    
    formule_currency_id = fields.Many2one(
        'res.currency',
        related='formule_id.currency_id',
        string="Devise FO"
    )
    
    confirmation_vente_id = fields.Many2one(
        'potting.confirmation.vente',
        string="Confirmation de Vente",
        related='formule_id.confirmation_vente_id',
        store=True,
        help="CV liée via la Formule"
    )
    
    campaign_id = fields.Many2one(
        'potting.campaign',
        string="Campagne Café-Cacao",
        required=True,
        tracking=True,
        default=lambda self: self._get_default_campaign(),
        domain="[('state', 'in', ['draft', 'active'])]",
        help="Campagne café-cacao pour cet OT. Détermine la période et les statistiques."
    )
    
    campaign_period = fields.Char(
        string="Période Campagne",
        compute='_compute_campaign_period',
        store=True,
        help="Période de la campagne Café-Cacao (ex: 2025-2026). "
             "Calculée automatiquement depuis la campagne sélectionnée."
    )
    
    customer_id = fields.Many2one(
        related='customer_order_id.customer_id',
        string="Client",
        store=True,
        index=True
    )
    
    consignee_id = fields.Many2one(
        'res.partner',
        string="Destinataire (Consignee)",
        required=True,
        tracking=True
    )
    
    # =========================================================================
    # CHAMPS - TRANSITAIRE
    # =========================================================================
    
    forwarding_agent_id = fields.Many2one(
        'potting.forwarding.agent',
        string="Transitaire",
        tracking=True,
        help="Transitaire responsable de l'exportation"
    )
    
    forwarding_agent_fee = fields.Monetary(
        string="Frais transitaire",
        currency_field='currency_id',
        compute='_compute_forwarding_agent_fee',
        store=True,
        help="Frais du transitaire pour cet OT"
    )
    
    # =========================================================================
    # CHAMPS - PRIX ET MONTANTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='customer_order_id.currency_id',
        store=True
    )
    
    unit_price = fields.Monetary(
        string="Prix unitaire (par tonne)",
        currency_field='currency_id',
        related='customer_order_id.unit_price',
        store=True
    )
    
    subtotal_amount = fields.Monetary(
        string="Sous-total",
        currency_field='currency_id',
        compute='_compute_ot_amounts',
        store=True,
        help="Prix × Tonnage"
    )
    
    certification_premium = fields.Monetary(
        string="Prime certification",
        currency_field='currency_id',
        compute='_compute_ot_amounts',
        store=True
    )
    
    total_amount = fields.Monetary(
        string="Montant total",
        currency_field='currency_id',
        compute='_compute_ot_amounts',
        store=True
    )
    
    # =========================================================================
    # CHAMPS - DROITS D'EXPORTATION
    # =========================================================================
    
    export_duty_rate = fields.Float(
        string="Taux droits d'export (%)",
        related='customer_order_id.export_duty_rate',
        store=True
    )
    
    export_duty_amount = fields.Monetary(
        string="Droits d'exportation",
        currency_field='currency_id',
        compute='_compute_export_duties',
        store=True,
        help="Droits d'exportation calculés sur le poids de l'OT (reversés à l'État)"
    )
    
    export_duty_collected = fields.Boolean(
        string="Droits encaissés",
        default=False,
        tracking=True,
        help="Les droits d'exportation doivent être encaissés avant l'exportation"
    )
    
    export_duty_collection_date = fields.Date(
        string="Date encaissement droits",
        tracking=True
    )
    
    export_allowed = fields.Boolean(
        string="Exportation autorisée",
        compute='_compute_export_allowed',
        store=True,
        help="L'exportation n'est autorisée que si les droits ont été encaissés"
    )
    
    net_amount = fields.Monetary(
        string="Montant net",
        currency_field='currency_id',
        compute='_compute_ot_amounts',
        store=True,
        help="Montant après déduction des droits d'exportation"
    )
    
    # =========================================================================
    # CHAMPS - FACTURATION (Facturation partielle supportée)
    # =========================================================================
    
    invoice_ids = fields.One2many(
        'account.move',
        'potting_transit_order_id',
        string="Factures",
        copy=False,
        help="Factures générées pour cet OT (facturation partielle possible)"
    )
    
    invoice_count = fields.Integer(
        string="Nombre de factures",
        compute='_compute_invoice_info',
        store=True
    )
    
    invoiced_tonnage = fields.Float(
        string="Tonnage facturé (T)",
        compute='_compute_invoice_info',
        store=True,
        digits='Product Unit of Measure',
        help="Tonnage total déjà facturé"
    )
    
    remaining_to_invoice = fields.Float(
        string="Reste à facturer (T)",
        compute='_compute_invoice_info',
        store=True,
        digits='Product Unit of Measure',
        help="Tonnage restant à facturer"
    )
    
    invoicing_progress = fields.Float(
        string="Progression facturation (%)",
        compute='_compute_invoice_info',
        store=True,
        help="Pourcentage du tonnage facturé"
    )
    
    is_fully_invoiced = fields.Boolean(
        string="Entièrement facturé",
        compute='_compute_invoice_info',
        store=True,
        help="Indique si tout le tonnage a été facturé"
    )
    
    is_invoiced = fields.Boolean(
        string="Partiellement facturé",
        compute='_compute_invoice_info',
        store=True,
        help="Indique si au moins une facture existe"
    )
    
    # Champ de compatibilité (dernière facture)
    invoice_id = fields.Many2one(
        'account.move',
        string="Dernière facture",
        compute='_compute_invoice_info',
        store=True,
        help="Dernière facture générée (compatibilité)"
    )
    
    invoice_state = fields.Selection(
        string="État dernière facture",
        related='invoice_id.state',
        store=True
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit", required=True, tracking=True, index=True)
    
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        domain="[('potting_product_type', '=', product_type)]",
        tracking=True
    )
    
    tonnage = fields.Float(
        string="Tonnage (T)",
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Tonnage total de l'OT"
    )
    
    max_tonnage_per_lot = fields.Float(
        string="Tonnage max/lot (T)",
        compute='_compute_max_tonnage_per_lot',
        store=True,
        digits='Product Unit of Measure'
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
        readonly=True,
        help="Nom du navire (automatiquement rempli depuis le navire sélectionné)"
    )
    
    pod = fields.Char(
        string="Port de déchargement (POD)",
        tracking=True
    )
    
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string="Taille conteneur (TC)", default='20', tracking=True)
    
    lot_range = fields.Char(
        string="Plage de lots",
        compute='_compute_lot_range',
        store=True
    )
    
    booking_number = fields.Char(
        string="Numéro de réservation (Booking)",
        tracking=True,
        index=True
    )
    
    lot_ids = fields.One2many(
        'potting.lot',
        'transit_order_id',
        string="Lots",
        copy=False
    )
    
    delivery_note_ids = fields.One2many(
        'potting.delivery.note',
        'transit_order_id',
        string="Bons de Livraison",
        copy=False
    )
    
    delivery_note_count = fields.Integer(
        string="Nombre de BL",
        compute='_compute_delivery_note_count',
        store=True
    )
    
    lot_count = fields.Integer(
        string="Nombre de lots",
        compute='_compute_lot_count',
        store=True
    )
    
    potted_lot_count = fields.Integer(
        string="Lots empotés",
        compute='_compute_lot_count',
        store=True
    )
    
    pending_lot_count = fields.Integer(
        string="Lots en attente",
        compute='_compute_lot_count',
        store=True
    )
    
    progress_percentage = fields.Float(
        string="Progression (%)",
        compute='_compute_progress',
        store=True
    )
    
    current_tonnage = fields.Float(
        string="Tonnage actuel (T)",
        compute='_compute_current_tonnage',
        store=True,
        digits='Product Unit of Measure'
    )
    
    # -------------------------------------------------------------------------
    # DELIVERY STATUS FIELDS
    # -------------------------------------------------------------------------
    delivery_status = fields.Selection([
        ('not_delivered', 'Non livré'),
        ('partial', 'Livraison partielle'),
        ('fully_delivered', 'Entièrement livré'),
    ], string="Statut de livraison", 
       compute='_compute_delivery_status', 
       store=True, 
       index=True,
       help="Statut de livraison basé sur les bons de livraison")
    
    delivered_lot_count = fields.Integer(
        string="Lots livrés",
        compute='_compute_delivery_status',
        store=True,
        help="Nombre de lots ayant fait l'objet d'au moins un bon de livraison"
    )
    
    delivered_tonnage = fields.Float(
        string="Tonnage livré (T)",
        compute='_compute_delivery_status',
        store=True,
        digits='Product Unit of Measure',
        help="Tonnage total des lots livrés"
    )
    
    remaining_to_deliver_tonnage = fields.Float(
        string="Tonnage restant à livrer (T)",
        compute='_compute_delivery_status',
        store=True,
        digits='Product Unit of Measure'
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('lots_generated', 'Lots générés'),
        ('in_progress', 'En cours'),
        ('ready_validation', 'Prêt pour validation'),
        ('done', 'Validé'),
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
        index=True
    )
    
    date_validated = fields.Datetime(
        string="Date de validation",
        readonly=True,
        copy=False
    )
    
    validated_by_id = fields.Many2one(
        'res.users',
        string="Validé par",
        readonly=True,
        copy=False
    )

    # =========================================================================
    # CHAMPS - CONVERSION DEVISE SOCIÉTÉ
    # =========================================================================
    
    company_currency_id = fields.Many2one(
        'res.currency',
        string="Devise société",
        related='company_id.currency_id',
        readonly=True,
        help="Devise de la société"
    )
    
    total_amount_company_currency = fields.Monetary(
        string="Montant total (devise société)",
        currency_field='company_currency_id',
        compute='_compute_amount_company_currency',
        store=True,
        help="Montant total de l'OT converti dans la devise de la société"
    )
    
    net_amount_company_currency = fields.Monetary(
        string="Montant net (devise société)",
        currency_field='company_currency_id',
        compute='_compute_amount_company_currency',
        store=True,
        help="Montant net de l'OT converti dans la devise de la société"
    )
    
    conversion_rate_display = fields.Char(
        string="Taux de conversion",
        compute='_compute_amount_company_currency',
        help="Taux de conversion appliqué"
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('tonnage')
    def _check_tonnage(self):
        for order in self:
            if order.tonnage <= 0:
                raise ValidationError(_("Le tonnage doit être supérieur à 0."))
            if order.tonnage > 1000:  # Max 1000 tonnes per OT
                raise ValidationError(_("Le tonnage ne peut pas dépasser 1000 tonnes par OT."))

    @api.constrains('product_type', 'product_id')
    def _check_product_type_consistency(self):
        for order in self:
            if order.product_id and order.product_id.potting_product_type != order.product_type:
                raise ValidationError(_(
                    "Le produit sélectionné ne correspond pas au type de produit de l'OT."
                ))
    
    @api.constrains('formule_id', 'tonnage')
    def _check_formule_tonnage(self):
        """Vérifie que le tonnage de l'OT est cohérent avec la Formule"""
        for order in self:
            if order.formule_id and order.tonnage:
                # Vérifier si d'autres OT utilisent cette formule
                other_ots = self.search([
                    ('formule_id', '=', order.formule_id.id),
                    ('id', '!=', order.id),
                    ('state', '!=', 'cancelled')
                ])
                if other_ots:
                    raise ValidationError(_(
                        "La Formule %s est déjà utilisée par l'OT %s. "
                        "Une Formule ne peut être liée qu'à un seul OT.",
                        order.formule_id.name,
                        other_ots[0].name
                    ))
    
    @api.constrains('customer_order_id', 'product_type')
    def _check_product_type_order(self):
        """Vérifie la cohérence du type de produit avec la commande"""
        for order in self:
            if order.customer_order_id and order.product_type:
                if order.customer_order_id.product_type != order.product_type:
                    raise ValidationError(_(
                        "Le type de produit de l'OT (%s) doit correspondre "
                        "au type de produit de la commande (%s).",
                        dict(order._fields['product_type'].selection).get(order.product_type),
                        dict(order.customer_order_id._fields['product_type'].selection).get(
                            order.customer_order_id.product_type
                        )
                    ))
    
    @api.constrains('export_duty_collected', 'state')
    def _check_export_duty_before_validation(self):
        """Vérifie que les droits d'export sont collectés avant validation"""
        for order in self:
            if order.state == 'done' and not order.export_duty_collected:
                raise ValidationError(_(
                    "Les droits d'exportation doivent être encaissés avant "
                    "la validation de l'OT %s.",
                    order.name
                ))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.model
    def _get_default_campaign(self):
        """Get the default campaign (current active campaign).
        
        Returns:
            potting.campaign: The current active campaign or False
        """
        return self.env['potting.campaign'].get_current_campaign()
    
    @api.depends('campaign_id', 'campaign_id.name')
    def _compute_campaign_period(self):
        """Calcule la période de campagne depuis la campagne sélectionnée."""
        for order in self:
            if order.campaign_id:
                order.campaign_period = order.campaign_id.name
            else:
                order.campaign_period = False
    
    @api.depends('product_type')
    def _compute_max_tonnage_per_lot(self):
        for order in self:
            order.max_tonnage_per_lot = self.env['res.config.settings'].get_max_tonnage_for_product(
                order.product_type
            )

    @api.depends('lot_ids', 'lot_ids.state')
    def _compute_lot_count(self):
        for order in self:
            lots = order.lot_ids
            order.lot_count = len(lots)
            order.potted_lot_count = len(lots.filtered(lambda l: l.state == 'potted'))
            order.pending_lot_count = len(lots.filtered(lambda l: l.state in ('draft', 'in_production', 'ready')))

    @api.depends('delivery_note_ids')
    def _compute_delivery_note_count(self):
        for order in self:
            order.delivery_note_count = len(order.delivery_note_ids)

    @api.depends('delivery_note_ids', 'delivery_note_ids.state', 'delivery_note_ids.lot_ids', 'lot_ids', 'current_tonnage')
    def _compute_delivery_status(self):
        """Compute delivery status based on delivery notes."""
        for order in self:
            # Get all delivered lots (from confirmed or delivered BLs)
            delivered_bls = order.delivery_note_ids.filtered(
                lambda bl: bl.state in ('confirmed', 'delivered')
            )
            delivered_lot_ids = set()
            for bl in delivered_bls:
                delivered_lot_ids.update(bl.lot_ids.ids)
            
            delivered_lots = order.lot_ids.filtered(lambda l: l.id in delivered_lot_ids)
            order.delivered_lot_count = len(delivered_lots)
            order.delivered_tonnage = sum(delivered_lots.mapped('current_tonnage'))
            order.remaining_to_deliver_tonnage = order.current_tonnage - order.delivered_tonnage
            
            # Determine delivery status
            total_lots = len(order.lot_ids)
            if total_lots == 0:
                order.delivery_status = 'not_delivered'
            elif len(delivered_lot_ids) == 0:
                order.delivery_status = 'not_delivered'
            elif len(delivered_lot_ids) >= total_lots:
                order.delivery_status = 'fully_delivered'
            else:
                order.delivery_status = 'partial'

    @api.depends('lot_ids.name')
    def _compute_lot_range(self):
        for order in self:
            if order.lot_ids:
                lot_names = sorted(order.lot_ids.mapped('name'))
                if lot_names:
                    order.lot_range = f"{lot_names[0]} → {lot_names[-1]}"
                else:
                    order.lot_range = False
            else:
                order.lot_range = False

    @api.depends('lot_count', 'potted_lot_count')
    def _compute_progress(self):
        for order in self:
            if order.lot_count > 0:
                order.progress_percentage = (order.potted_lot_count / order.lot_count) * 100
            else:
                order.progress_percentage = 0

    @api.depends('lot_ids.current_tonnage')
    def _compute_current_tonnage(self):
        for order in self:
            order.current_tonnage = sum(order.lot_ids.mapped('current_tonnage'))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS - PRIX, DROITS ET TRANSITAIRE
    # -------------------------------------------------------------------------
    
    @api.depends('forwarding_agent_id', 'tonnage', 'lot_ids.container_id')
    def _compute_forwarding_agent_fee(self):
        """Calculate forwarding agent fees based on commission and fixed fees"""
        for order in self:
            fee = 0.0
            if order.forwarding_agent_id:
                agent = order.forwarding_agent_id
                # Commission based on tonnage
                if agent.commission_rate:
                    base_amount = order.subtotal_amount or (order.tonnage * (order.unit_price or 0))
                    fee += base_amount * (agent.commission_rate / 100)
                # Fixed fee per container
                if agent.fixed_fee_per_container:
                    container_count = len(order.lot_ids.mapped('container_id'))
                    fee += agent.fixed_fee_per_container * max(container_count, 1)
            order.forwarding_agent_fee = fee
    
    @api.depends('unit_price', 'tonnage', 'lot_ids.certification_id', 'lot_ids.current_tonnage', 'export_duty_amount')
    def _compute_ot_amounts(self):
        """Calculate OT amounts: subtotal, certification premium, total and net"""
        for order in self:
            # Subtotal = price × tonnage
            order.subtotal_amount = (order.unit_price or 0) * order.tonnage
            
            # Certification premium
            cert_premium = 0.0
            for lot in order.lot_ids:
                if lot.certification_id and lot.certification_id.price_per_ton:
                    cert_premium += lot.certification_id.price_per_ton * lot.current_tonnage
            order.certification_premium = cert_premium
            
            # Total amount
            order.total_amount = order.subtotal_amount + order.certification_premium
            
            # Net amount (after export duties)
            order.net_amount = order.total_amount - (order.export_duty_amount or 0)

    @api.depends('total_amount', 'net_amount', 'currency_id', 'company_id.currency_id', 'date_created')
    def _compute_amount_company_currency(self):
        """Convertit les montants de l'OT dans la devise de la société.
        
        Cette méthode calcule automatiquement les montants convertis en utilisant
        le taux de change à la date de création de l'OT.
        """
        for order in self:
            company_currency = order.company_id.currency_id
            contract_currency = order.currency_id
            
            # Si pas de devise définie ou mêmes devises, pas de conversion
            if not company_currency or not contract_currency:
                order.total_amount_company_currency = order.total_amount
                order.net_amount_company_currency = order.net_amount
                order.conversion_rate_display = ""
                continue
                
            if company_currency == contract_currency:
                order.total_amount_company_currency = order.total_amount
                order.net_amount_company_currency = order.net_amount
                order.conversion_rate_display = _("Même devise")
                continue
            
            # Convertir les montants à la date de création
            date = order.date_created or fields.Date.context_today(order)
            
            # Conversion du montant total
            order.total_amount_company_currency = contract_currency._convert(
                order.total_amount or 0.0,
                company_currency,
                order.company_id,
                date
            )
            
            # Conversion du montant net
            order.net_amount_company_currency = contract_currency._convert(
                order.net_amount or 0.0,
                company_currency,
                order.company_id,
                date
            )
            
            # Affichage du taux de conversion
            rate = contract_currency._get_conversion_rate(
                contract_currency,
                company_currency,
                order.company_id,
                date
            )
            order.conversion_rate_display = _("1 %s = %.4f %s") % (
                contract_currency.name,
                rate,
                company_currency.name
            )
    
    @api.depends('total_amount', 'export_duty_rate', 'current_tonnage')
    def _compute_export_duties(self):
        """Calculate export duties based on weight and rate
        
        Les droits d'exportation sont calculés sur le poids de l'OT.
        Ces droits sont reversés à l'État.
        """
        for order in self:
            if order.total_amount and order.export_duty_rate:
                # Calcul basé sur le montant total
                order.export_duty_amount = order.total_amount * (order.export_duty_rate / 100)
            else:
                order.export_duty_amount = 0.0
    
    @api.depends('export_duty_collected')
    def _compute_export_allowed(self):
        """Check if export is allowed (duties must be collected first)"""
        for order in self:
            order.export_allowed = order.export_duty_collected
    
    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.potting_invoiced_tonnage', 'current_tonnage')
    def _compute_invoice_info(self):
        """Compute invoice-related fields for partial invoicing support"""
        for order in self:
            # Filtrer les factures non annulées
            valid_invoices = order.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
            
            order.invoice_count = len(valid_invoices)
            order.invoiced_tonnage = sum(valid_invoices.mapped('potting_invoiced_tonnage'))
            order.remaining_to_invoice = max(0, order.current_tonnage - order.invoiced_tonnage)
            
            if order.current_tonnage > 0:
                order.invoicing_progress = (order.invoiced_tonnage / order.current_tonnage) * 100
            else:
                order.invoicing_progress = 0
            
            order.is_invoiced = order.invoice_count > 0
            order.is_fully_invoiced = order.remaining_to_invoice <= 0 and order.is_invoiced
            
            # Dernière facture (compatibilité)
            order.invoice_id = valid_invoices[-1] if valid_invoices else False

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('vessel_id')
    def _onchange_vessel_id(self):
        if self.vessel_id:
            self.vessel_name = self.vessel_id.name

    @api.onchange('product_type')
    def _onchange_product_type(self):
        """Reset product when product type changes"""
        if self.product_id and self.product_id.potting_product_type != self.product_type:
            self.product_id = False

    @api.onchange('customer_order_id')
    def _onchange_customer_order_id(self):
        """Set default consignee from customer"""
        if self.customer_order_id and not self.consignee_id:
            self.consignee_id = self.customer_order_id.customer_id

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Vérifier que le tonnage du contrat n'est pas dépassé
            customer_order_id = vals.get('customer_order_id')
            if customer_order_id:
                customer_order = self.env['potting.customer.order'].browse(customer_order_id)
                if customer_order.exists():
                    new_tonnage = vals.get('tonnage', 0)
                    if customer_order.contract_tonnage > 0:
                        current_ot_tonnage = sum(customer_order.transit_order_ids.mapped('tonnage'))
                        if current_ot_tonnage + new_tonnage > customer_order.contract_tonnage:
                            raise ValidationError(_(
                                "Impossible d'ajouter cet OT: le tonnage total des OT (%.2f T + %.2f T = %.2f T) "
                                "dépasserait le tonnage du contrat (%.2f T).\n\n"
                                "Tonnage restant disponible: %.2f T"
                            ) % (
                                current_ot_tonnage, 
                                new_tonnage, 
                                current_ot_tonnage + new_tonnage,
                                customer_order.contract_tonnage,
                                customer_order.contract_tonnage - current_ot_tonnage
                            ))
            
            # Générer automatiquement le numéro OT si non fourni ou si 'Nouveau'
            if vals.get('name', _('Nouveau')) == _('Nouveau') or not vals.get('name'):
                # Le nom de l'OT dépend du type de produit et de la campagne de la commande
                product_type = vals.get('product_type')
                
                # Récupérer la campagne depuis vals ou depuis la campagne par défaut
                campaign_period = None
                campaign_id = vals.get('campaign_id')
                if campaign_id:
                    campaign = self.env['potting.campaign'].browse(campaign_id)
                    if campaign.exists():
                        campaign_period = campaign.name
                
                # Récupérer la référence client depuis la commande
                customer_ref = None
                if customer_order_id:
                    customer_order = self.env['potting.customer.order'].browse(customer_order_id)
                    if customer_order.exists():
                        # Récupérer la référence du client si elle existe
                        if customer_order.customer_id and customer_order.customer_id.ref:
                            customer_ref = customer_order.customer_id.ref
                
                vals['name'] = self.env['res.config.settings'].generate_ot_name(
                    product_type, 
                    campaign_period,
                    customer_ref
                )
            
            # Marquer si l'OT est créé depuis le contexte d'une commande
            if self.env.context.get('default_customer_order_id') or vals.get('customer_order_id'):
                vals['is_created_from_order'] = True
        
        records = super().create(vals_list)
        
        # Lier les formules aux OT créés
        for record in records:
            if record.formule_id and not record.formule_id.transit_order_id:
                record.formule_id.transit_order_id = record.id
        
        return records

    def write(self, vals):
        """Vérifie que le tonnage du contrat n'est pas dépassé lors de la modification."""
        # Gérer le changement de formule
        if 'formule_id' in vals:
            old_formule_ids = self.mapped('formule_id')
            
        if 'tonnage' in vals:
            for order in self:
                if order.customer_order_id and order.customer_order_id.contract_tonnage > 0:
                    new_tonnage = vals.get('tonnage', order.tonnage)
                    # Calculer le total des autres OT (sans l'OT actuel)
                    other_ot_tonnage = sum(
                        ot.tonnage for ot in order.customer_order_id.transit_order_ids 
                        if ot.id != order.id
                    )
                    if other_ot_tonnage + new_tonnage > order.customer_order_id.contract_tonnage:
                        raise ValidationError(_(
                            "Impossible de modifier le tonnage: le total (%.2f T + %.2f T = %.2f T) "
                            "dépasserait le tonnage du contrat (%.2f T).\n\n"
                            "Tonnage maximum pour cet OT: %.2f T"
                        ) % (
                            other_ot_tonnage,
                            new_tonnage,
                            other_ot_tonnage + new_tonnage,
                            order.customer_order_id.contract_tonnage,
                            order.customer_order_id.contract_tonnage - other_ot_tonnage
                        ))
        
        result = super().write(vals)
        
        # Mettre à jour les liens formule-OT si la formule a changé
        if 'formule_id' in vals:
            # Délier les anciennes formules
            old_formule_ids.filtered(lambda f: f.transit_order_id not in self).write({
                'transit_order_id': False
            })
            # Lier les nouvelles formules
            for record in self:
                if record.formule_id and record.formule_id.transit_order_id != record:
                    record.formule_id.transit_order_id = record.id
        
        return result

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': _('Nouveau'),
            'state': 'draft',
            'date_created': fields.Date.context_today(self),
            'is_created_from_order': False,
        })
        return super().copy(default)

    def unlink(self):
        # Délier les formules avant suppression
        formule_ids = self.mapped('formule_id')
        
        for order in self:
            if order.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les OT en brouillon ou annulés. "
                    "L'OT '%s' est en état '%s'."
                ) % (order.name, dict(order._fields['state'].selection).get(order.state)))
            # Vérifier qu'aucun lot n'a de production
            if any(lot.current_tonnage > 0 for lot in order.lot_ids):
                raise UserError(_(
                    "Impossible de supprimer l'OT '%s': certains lots ont déjà de la production."
                ) % order.name)
        
        result = super().unlink()
        
        # Délier les formules après suppression réussie
        formule_ids.write({'transit_order_id': False})
        
        return result

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_generate_lots(self):
        """Open wizard to generate lots with custom max tonnage."""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_("Les lots ne peuvent être générés que pour les OT en brouillon."))
        
        if self.lot_ids:
            raise UserError(_("Des lots existent déjà pour cet OT. Supprimez-les d'abord."))
        
        if not self.tonnage or self.tonnage <= 0:
            raise UserError(_("Le tonnage doit être supérieur à 0."))
        
        if not self.product_type:
            raise UserError(_("Veuillez sélectionner un type de produit."))
        
        # Open the wizard
        return {
            'name': _('Générer les lots'),
            'type': 'ir.actions.act_window',
            'res_model': 'potting.generate.lots.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'potting.transit.order',
            },
        }

    def _get_unique_lot_name(self):
        """Get a unique lot name using sequence and product-specific prefix.
        
        Format: [Prefix][Number] where Prefix depends on product type:
        - M for Masse (cocoa_mass)
        - B for Beurre (cocoa_butter)  
        - T for Tourteau/Cake (cocoa_cake)
        - P for Poudre (cocoa_powder)
        """
        import re
        
        # Get prefix for this product type from configuration
        prefix = self.env['res.config.settings'].get_lot_prefix_for_product(self.product_type)
        
        sequence = self.env['ir.sequence'].next_by_code('potting.lot')
        if sequence:
            # Extract number from sequence
            numbers = re.findall(r'\d+', sequence)
            if numbers:
                return f"{prefix}{numbers[0]}"
        
        # Fallback: use timestamp-based unique name
        import time
        return f"{prefix}{int(time.time() * 1000) % 100000}"

    def _get_next_lot_sequence_number(self):
        """Get the next lot sequence number"""
        sequence = self.env['ir.sequence'].next_by_code('potting.lot')
        if sequence:
            try:
                # Extract number from sequence like "LOT10001" or "T10001"
                import re
                numbers = re.findall(r'\d+', sequence)
                if numbers:
                    return int(numbers[0])
            except (ValueError, TypeError):
                pass
        return 10001

    def action_regenerate_lots(self):
        """Delete existing lots and regenerate"""
        self.ensure_one()
        if self.state not in ('draft', 'lots_generated'):
            raise UserError(_("Les lots ne peuvent être régénérés que pour les OT en brouillon ou avec lots générés."))
        
        # Check if any lot has production
        if any(lot.current_tonnage > 0 for lot in self.lot_ids):
            raise UserError(_("Impossible de régénérer les lots: certains lots ont déjà de la production."))
        
        self.lot_ids.unlink()
        self.state = 'draft'
        return self.action_generate_lots()

    def action_start_production(self):
        for order in self:
            if order.state != 'lots_generated':
                raise UserError(_("L'OT doit avoir des lots générés pour démarrer la production."))
            order.state = 'in_progress'
            order.lot_ids.filtered(lambda l: l.state == 'draft').write({'state': 'in_production'})
            order.message_post(body=_("Production démarrée."))
            # Also update customer order state
            if order.customer_order_id.state == 'confirmed':
                order.customer_order_id.action_start()

    def action_mark_ready(self):
        """Mark OT as ready for validation when all lots are potted"""
        for order in self:
            if order.state != 'in_progress':
                raise UserError(_("L'OT doit être en cours pour être marqué prêt."))
            if any(lot.state != 'potted' for lot in order.lot_ids):
                raise UserError(_("Tous les lots doivent être empotés avant de marquer l'OT comme prêt."))
            order.state = 'ready_validation'
            order.message_post(body=_("OT prêt pour validation."))

    def action_validate(self):
        """CEO Agent validates the OT"""
        for order in self:
            if order.state != 'ready_validation':
                raise UserError(_("L'OT doit être prêt pour validation."))
            order.write({
                'state': 'done',
                'date_validated': fields.Datetime.now(),
                'validated_by_id': self.env.user.id,
            })
            order.message_post(body=_("OT validé par %s.") % self.env.user.name)
            
            # Check if all OT of the customer order are done
            customer_order = order.customer_order_id
            if all(ot.state == 'done' for ot in customer_order.transit_order_ids):
                customer_order.action_done()

    def action_cancel(self):
        for order in self:
            if order.state == 'done':
                raise UserError(_("Les OT validés ne peuvent pas être annulés."))
            order.lot_ids.filtered(lambda l: l.state != 'potted').write({'state': 'draft'})
            order.state = 'cancelled'
            order.message_post(body=_("OT annulé."))

    def action_draft(self):
        """Remettre l'OT en brouillon de façon sécurisée"""
        for order in self:
            # Ne peut remettre en brouillon que depuis certains états
            if order.state == 'done':
                raise UserError(_(
                    "Les OT validés ne peuvent pas être remis en brouillon. "
                    "Veuillez d'abord les annuler."
                ))
            if order.state == 'draft':
                continue  # Déjà en brouillon
            
            # Vérifier qu'aucun lot n'est empoté
            potted_lots = order.lot_ids.filtered(lambda l: l.state == 'potted')
            if potted_lots:
                raise UserError(_(
                    "Impossible de remettre l'OT '%s' en brouillon: "
                    "%d lot(s) sont déjà empoté(s)."
                ) % (order.name, len(potted_lots)))
            
            # Remettre les lots en brouillon aussi
            order.lot_ids.filtered(lambda l: l.state != 'potted').write({'state': 'draft'})
            order.state = 'draft'
            order.message_post(body=_("🔄 OT remis en brouillon par %s.") % self.env.user.name)

    def action_view_lots(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Lots - %s') % self.name,
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('transit_order_id', '=', self.id)],
            'context': {
                'default_transit_order_id': self.id,
                'default_product_type': self.product_type,
                'default_product_id': self.product_id.id if self.product_id else False,
            },
        }
        return action

    def action_view_potted_lots(self):
        """View only potted lots"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lots empotés - %s') % self.name,
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('transit_order_id', '=', self.id), ('state', '=', 'potted')],
        }

    def action_create_delivery_note(self):
        """Open wizard to create a delivery note with lot selection."""
        self.ensure_one()
        
        if self.state not in ('in_progress', 'ready_validation', 'done'):
            raise UserError(_("Les bons de livraison ne peuvent être créés que pour les OT en cours, prêts ou validés."))
        
        if not self.lot_ids:
            raise UserError(_("Aucun lot disponible pour créer un bon de livraison."))
        
        return {
            'name': _('Créer un Bon de Livraison'),
            'type': 'ir.actions.act_window',
            'res_model': 'potting.create.delivery.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'potting.transit.order',
            },
        }

    def action_view_delivery_notes(self):
        """View delivery notes for this transit order."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bons de Livraison - %s') % self.name,
            'res_model': 'potting.delivery.note',
            'view_mode': 'tree,kanban,form',
            'domain': [('transit_order_id', '=', self.id)],
            'context': {
                'default_transit_order_id': self.id,
            },
        }

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def get_production_summary(self):
        """Get production summary for reporting"""
        self.ensure_one()
        return {
            'name': self.name,
            'product_type': dict(self._fields['product_type'].selection).get(self.product_type),
            'total_tonnage': self.tonnage,
            'current_tonnage': self.current_tonnage,
            'remaining': self.tonnage - self.current_tonnage,
            'progress': self.progress_percentage,
            'lots': [{
                'name': lot.name,
                'target': lot.target_tonnage,
                'current': lot.current_tonnage,
                'fill': lot.fill_percentage,
                'state': lot.state,
            } for lot in self.lot_ids.sorted('name')],
        }

    # -------------------------------------------------------------------------
    # INVOICE METHODS (Facturation partielle supportée)
    # -------------------------------------------------------------------------
    def action_create_invoice(self):
        """Create an invoice for the remaining tonnage of this transit order"""
        self.ensure_one()
        
        if self.is_fully_invoiced:
            raise UserError(_("Cet OT est déjà entièrement facturé."))
        
        if self.state not in ('in_progress', 'ready_validation', 'done'):
            raise UserError(_("L'OT doit être en cours, prêt pour validation ou validé pour générer une facture."))
        
        if not self.export_duty_collected:
            raise UserError(_(
                "Les droits d'exportation doivent être encaissés avant de générer la facture. "
                "Veuillez d'abord encaisser les droits d'exportation."
            ))
        
        # Check if account module is installed
        if 'account.move' not in self.env:
            raise UserError(_(
                "Le module de comptabilité doit être installé pour créer des factures."
            ))
        
        # Facturer le reste à facturer
        return self._create_invoice(tonnage=self.remaining_to_invoice)
    
    def _create_invoice(self, tonnage=None, delivery_note=None):
        """
        Internal method to create an invoice.
        
        Args:
            tonnage: Tonnage à facturer (si None, facture le tonnage total restant)
            delivery_note: Bon de livraison associé (si facture partielle par BL)
        
        Returns:
            dict: Action pour ouvrir la facture créée
        """
        self.ensure_one()
        
        # Déterminer le tonnage à facturer
        if tonnage is None:
            tonnage = self.remaining_to_invoice
        
        if tonnage <= 0:
            raise UserError(_("Aucun tonnage à facturer."))
        
        # Vérifier qu'on ne dépasse pas le reste à facturer
        if tonnage > self.remaining_to_invoice + 0.001:  # Tolérance pour arrondis
            raise UserError(_(
                "Le tonnage à facturer (%.3f T) dépasse le reste à facturer (%.3f T)."
            ) % (tonnage, self.remaining_to_invoice))
        
        # Préparer les lignes de facture
        invoice_lines = self._prepare_invoice_lines(tonnage=tonnage)
        
        # Construire la référence
        if delivery_note:
            origin = f"{self.name} / {delivery_note.name}"
            ref = f"OT {self.name} - BL {delivery_note.name}"
        else:
            origin = self.name
            ref = f"OT {self.name}"
        
        # Préparer les valeurs de la facture
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': origin,
            'ref': ref,
            'potting_transit_order_id': self.id,
            'potting_delivery_note_id': delivery_note.id if delivery_note else False,
            'potting_invoiced_tonnage': tonnage,
            'invoice_line_ids': [(0, 0, line) for line in invoice_lines],
            'narration': _(
                "Facture pour l'Ordre de Transit %s\n"
                "Contrat: %s\n"
                "Produit: %s\n"
                "Tonnage facturé: %.3f T%s"
            ) % (
                self.name,
                self.customer_order_id.contract_number or self.customer_order_id.name,
                dict(self._fields['product_type'].selection).get(self.product_type),
                tonnage,
                f"\nBon de livraison: {delivery_note.name}" if delivery_note else ""
            ),
        }
        
        # Créer la facture
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Lier la facture au BL si applicable
        if delivery_note:
            delivery_note.invoice_id = invoice
        
        # Message dans le chatter
        msg = _("Facture %s créée pour %.3f T.") % (invoice.name, tonnage)
        if delivery_note:
            msg += _(" (BL: %s)") % delivery_note.name
        self.message_post(body=msg)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }
    
    def _prepare_invoice_lines(self, tonnage=None):
        """
        Prepare invoice lines for the OT invoice.
        
        Args:
            tonnage: Tonnage à facturer (si None, utilise current_tonnage)
        """
        self.ensure_one()
        lines = []
        
        if tonnage is None:
            tonnage = self.current_tonnage
        
        # Main product line
        product = self.product_id or self.env.ref('potting_management.product_cocoa_mass', raise_if_not_found=False)
        
        lines.append({
            'name': _("%s - OT %s") % (
                dict(self._fields['product_type'].selection).get(self.product_type),
                self.name
            ),
            'product_id': product.id if product else False,
            'quantity': tonnage,
            'price_unit': self.unit_price or 0,
            'product_uom_id': self.env.ref('uom.product_uom_ton', raise_if_not_found=False).id if self.env.ref('uom.product_uom_ton', raise_if_not_found=False) else False,
        })
        
        # Certification premium line (proportionnel au tonnage facturé)
        if self.certification_premium > 0 and self.current_tonnage > 0:
            # Calculer la prime au prorata du tonnage facturé
            prorata_premium = (tonnage / self.current_tonnage) * self.certification_premium
            lines.append({
                'name': _("Prime de certification (prorata %.1f%%)") % ((tonnage / self.current_tonnage) * 100),
                'quantity': 1,
                'price_unit': prorata_premium,
            })
        
        return lines
    
    def action_view_invoice(self):
        """View invoices for this OT"""
        self.ensure_one()
        if not self.invoice_ids:
            raise UserError(_("Aucune facture n'a été créée pour cet OT."))
        
        if len(self.invoice_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Facture'),
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_ids[0].id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Factures - %s') % self.name,
                'res_model': 'account.move',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.invoice_ids.ids)],
            }
    
    def action_collect_export_duties(self):
        """Mark export duties as collected"""
        for order in self:
            if order.export_duty_collected:
                continue
            if order.export_duty_amount <= 0:
                raise UserError(_("Aucun droit d'exportation à encaisser pour cet OT."))
            order.write({
                'export_duty_collected': True,
                'export_duty_collection_date': fields.Date.context_today(self),
            })
            order.message_post(body=_(
                "✅ Droits d'exportation encaissés: %s %s"
            ) % (order.export_duty_amount, order.currency_id.symbol))


class PottingVessel(models.Model):
    _name = 'potting.vessel'
    _description = 'Navire'
    _order = 'name'
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom du navire doit être unique!'),
        ('code_uniq', 'unique(code)', 'Le code du navire doit être unique!'),
    ]
    
    name = fields.Char(string="Nom du navire", required=True, index=True)
    code = fields.Char(string="Code", index=True)
    shipping_company = fields.Char(string="Compagnie maritime")
    active = fields.Boolean(string="Actif", default=True)
    
    def name_get(self):
        result = []
        for vessel in self:
            name = vessel.name
            if vessel.code:
                name = f"[{vessel.code}] {name}"
            result.append((vessel.id, name))
        return result
