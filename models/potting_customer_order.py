# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingCustomerOrder(models.Model):
    """Commande Client / Contrat d'exportation de cacao
    
    Le contrat représente une commande client avec:
    - Un numéro unique (référence)
    - Un tonnage total
    - Un prix unitaire et total
    - Des droits d'exportation
    - Un lien avec les Ordres de Transit (OT)
    """
    _name = 'potting.customer.order'
    _description = 'Contrat / Commande Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _check_company_auto = True

    # SQL Constraints
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 
         'La référence du contrat doit être unique par société!'),
        ('contract_number_uniq', 'unique(contract_number)', 
         'Le numéro de contrat doit être unique!'),
        ('contract_tonnage_positive', 'CHECK(contract_tonnage >= 0)',
         'Le tonnage du contrat doit être positif ou nul!'),
        ('unit_price_positive', 'CHECK(unit_price >= 0)',
         'Le prix unitaire doit être positif ou nul!'),
        ('export_duty_rate_valid', 'CHECK(export_duty_rate >= 0 AND export_duty_rate <= 100)',
         'Le taux des droits d\'export doit être entre 0 et 100%!'),
    ]

    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        index=True
    )
    
    contract_number = fields.Char(
        string="Numéro de contrat",
        copy=False,
        tracking=True,
        index=True,
        help="Numéro unique du contrat d'exportation"
    )
    
    # =========================================================================
    # NOTE: Le lien avec les CV se fait via OT → Formule → CV
    # Les champs confirmation_vente_ids ont été supprimés (v2.1)
    # =========================================================================
    
    customer_id = fields.Many2one(
        'res.partner',
        string="Client",
        required=True,
        tracking=True,
        default=lambda self: self._get_default_customer(),
        domain="[('is_company', '=', True)]",
        check_company=True
    )
    
    date_order = fields.Date(
        string="Date de commande",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True
    )
    
    date_expected = fields.Date(
        string="Date de livraison prévue",
        tracking=True
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit", required=True, tracking=True,
       help="Type de produit semi-fini du cacao pour ce contrat")
    
    # =========================================================================
    # CHAMPS - PRIX ET MONTANTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self._get_default_currency(),
        required=True,
        tracking=True,
        help="Devise utilisée pour ce contrat. Modifiable par l'utilisateur."
    )
    
    unit_price = fields.Monetary(
        string="Prix unitaire (par tonne)",
        currency_field='currency_id',
        tracking=True,
        help="Prix de vente par tonne de produit"
    )
    
    certification_ids = fields.Many2many(
        'potting.certification',
        'potting_customer_order_certification_rel',
        'order_id',
        'certification_id',
        string="Certifications",
        help="Certifications applicables à cette commande"
    )
    
    certification_premium = fields.Monetary(
        string="Prime de certification",
        currency_field='currency_id',
        compute='_compute_certification_premium',
        store=True,
        help="Montant total des primes de certification"
    )
    
    subtotal_amount = fields.Monetary(
        string="Sous-total",
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help="Montant avant déduction des droits d'exportation"
    )
    
    total_amount = fields.Monetary(
        string="Montant total",
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help="Montant total du contrat (prix × tonnage + primes)"
    )
    
    # =========================================================================
    # CHAMPS - DROITS D'EXPORTATION
    # =========================================================================
    
    export_duty_rate = fields.Float(
        string="Taux droits d'export (%)",
        default=lambda self: self._get_default_export_duty_rate(),
        tracking=True,
        help="Taux des droits d'exportation en pourcentage (reversés à l'État)"
    )
    
    export_duty_amount = fields.Monetary(
        string="Droits d'exportation",
        currency_field='currency_id',
        compute='_compute_export_duties',
        store=True,
        help="Montant des droits d'exportation à reverser à l'État"
    )
    
    export_duty_collected = fields.Boolean(
        string="Droits encaissés",
        default=False,
        tracking=True,
        help="Indique si les droits d'exportation ont été encaissés avant l'exportation"
    )
    
    export_duty_collection_date = fields.Date(
        string="Date d'encaissement droits",
        tracking=True,
        help="Date à laquelle les droits d'exportation ont été encaissés"
    )
    
    net_amount = fields.Monetary(
        string="Montant net",
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help="Montant après déduction des droits d'exportation"
    )
    
    # =========================================================================
    # CHAMPS - COÛTS
    # =========================================================================
    
    transport_cost = fields.Monetary(
        string="Coût de transport",
        currency_field='currency_id',
        tracking=True,
        help="Coût du transport des marchandises"
    )
    
    storage_cost = fields.Monetary(
        string="Coût de stockage",
        currency_field='currency_id',
        tracking=True,
        help="Coût de stockage des marchandises"
    )
    
    insurance_cost = fields.Monetary(
        string="Coût d'assurance",
        currency_field='currency_id',
        tracking=True,
        help="Coût de l'assurance des marchandises"
    )
    
    other_costs = fields.Monetary(
        string="Autres coûts",
        currency_field='currency_id',
        tracking=True,
        help="Autres coûts supplémentaires"
    )
    
    total_costs = fields.Monetary(
        string="Total des coûts",
        currency_field='currency_id',
        compute='_compute_total_costs',
        store=True,
        help="Total de tous les coûts supplémentaires"
    )
    
    estimated_cost = fields.Monetary(
        string="Coût estimé",
        currency_field='currency_id',
        compute='_compute_costs',
        store=True,
        help="Coût estimé basé sur les fèves de cacao utilisées"
    )
    
    actual_cost = fields.Monetary(
        string="Coût réel",
        currency_field='currency_id',
        compute='_compute_costs',
        store=True,
        help="Coût réel calculé à partir des lots de fèves consommées"
    )
    
    estimated_margin = fields.Monetary(
        string="Marge estimée",
        currency_field='currency_id',
        compute='_compute_costs',
        store=True
    )
    
    margin_percentage = fields.Float(
        string="Marge (%)",
        compute='_compute_costs',
        store=True
    )
    
    transit_order_ids = fields.One2many(
        'potting.transit.order',
        'customer_order_id',
        string="Ordres de Transit",
        copy=True
    )
    
    transit_order_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_transit_order_count',
        store=True
    )
    
    contract_tonnage = fields.Float(
        string="Tonnage du contrat (T)",
        digits='Product Unit of Measure',
        tracking=True,
        help="Tonnage total prévu dans le contrat d'exportation. "
             "Ce champ est saisi manuellement et sert de valeur par défaut "
             "pour la génération des OT."
    )
    
    total_tonnage = fields.Float(
        string="Tonnage total OT (T)",
        compute='_compute_total_tonnage',
        store=True,
        digits='Product Unit of Measure',
        help="Tonnage total des OT créés pour cette commande (calculé automatiquement)"
    )
    
    remaining_contract_tonnage = fields.Float(
        string="Tonnage restant à allouer (T)",
        compute='_compute_remaining_contract_tonnage',
        store=True,
        digits='Product Unit of Measure',
        help="Différence entre le tonnage du contrat et le tonnage des OT créés"
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string="État", default='draft', tracking=True, index=True, copy=False)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string="Responsable",
        default=lambda self: self.env.user,
        tracking=True,
        index=True
    )
    
    # Computed fields for statistics
    potted_tonnage = fields.Float(
        string="Tonnage empoté (T)",
        compute='_compute_potted_stats',
        store=True,
        digits='Product Unit of Measure'
    )
    
    progress_percentage = fields.Float(
        string="Progression (%)",
        compute='_compute_potted_stats',
        store=True
    )
    
    is_late = fields.Boolean(
        string="En retard",
        compute='_compute_is_late',
        store=True
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
        help="Montant total du contrat converti dans la devise de la société"
    )
    
    net_amount_company_currency = fields.Monetary(
        string="Montant net (devise société)",
        currency_field='company_currency_id',
        compute='_compute_amount_company_currency',
        store=True,
        help="Montant net du contrat converti dans la devise de la société"
    )
    
    conversion_rate_display = fields.Char(
        string="Taux de conversion",
        compute='_compute_amount_company_currency',
        help="Taux de conversion appliqué"
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('date_expected', 'date_order')
    def _check_dates(self):
        for order in self:
            if order.date_expected and order.date_order and order.date_expected < order.date_order:
                raise ValidationError(_(
                    "La date de livraison prévue ne peut pas être antérieure à la date de commande."
                ))
    
    @api.constrains('unit_price')
    def _check_unit_price(self):
        """Vérifie que le prix unitaire est raisonnable"""
        for order in self:
            if order.unit_price and order.unit_price <= 0:
                raise ValidationError(_(
                    "Le prix unitaire doit être supérieur à 0."
                ))

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    @api.model
    def _get_default_currency(self):
        """Get the default currency for the potting module.
        
        Returns the configured default currency if set, otherwise falls back
        to the company currency.
        
        Returns:
            res.currency: The default currency record
        """
        return self.env['res.config.settings'].get_default_currency()
    
    @api.model
    @api.model
    def _get_default_customer(self):
        """Get the default customer from settings"""
        try:
            default_customer_id = self.env['ir.config_parameter'].sudo().get_param(
                'potting_management.default_customer_id'
            )
            if default_customer_id:
                partner = self.env['res.partner'].browse(int(default_customer_id))
                if partner.exists():
                    return partner
        except (ValueError, TypeError):
            pass
        return False

    @api.model
    def _get_default_export_duty_rate(self):
        """Get the default export duty rate from settings"""
        ICP = self.env['ir.config_parameter'].sudo()
        rate = ICP.get_param('potting_management.export_duty_rate', '14.6')
        try:
            return float(rate)
        except (ValueError, TypeError):
            return 14.6  # Default rate

    # -------------------------------------------------------------------------
    # COMPUTE METHODS - PRIX & MONTANTS
    # -------------------------------------------------------------------------

    @api.depends('transit_order_ids.lot_ids.certification_id', 'certification_ids', 'total_tonnage')
    def _compute_certification_premium(self):
        """Calculate total certification premium based on lots and order certifications"""
        for order in self:
            total_premium = 0.0
            # Premium from lots certifications
            for ot in order.transit_order_ids:
                for lot in ot.lot_ids:
                    if lot.certification_id and lot.certification_id.price_per_ton:
                        total_premium += lot.certification_id.price_per_ton * lot.current_tonnage
            # Premium from order-level certifications
            for certification in order.certification_ids:
                if certification.price_per_ton:
                    total_premium += certification.price_per_ton * order.total_tonnage
            order.certification_premium = total_premium

    @api.depends('transport_cost', 'storage_cost', 'insurance_cost', 'other_costs')
    def _compute_total_costs(self):
        """Calculate total of all additional costs"""
        for order in self:
            order.total_costs = (
                (order.transport_cost or 0.0) +
                (order.storage_cost or 0.0) +
                (order.insurance_cost or 0.0) +
                (order.other_costs or 0.0)
            )

    @api.depends('unit_price', 'total_tonnage', 'certification_premium', 'export_duty_amount')
    def _compute_amounts(self):
        """Calculate subtotal, total and net amounts"""
        for order in self:
            # Use contract unit price
            base_price = order.unit_price or 0.0
            
            # Calculate subtotal (price × tonnage)
            order.subtotal_amount = base_price * order.total_tonnage
            
            # Calculate total (subtotal + certification premiums)
            order.total_amount = order.subtotal_amount + order.certification_premium
            
            # Calculate net amount (after export duties)
            order.net_amount = order.total_amount - order.export_duty_amount

    @api.depends('total_amount', 'export_duty_rate')
    def _compute_export_duties(self):
        """Calculate export duties based on total amount and rate"""
        for order in self:
            if order.total_amount and order.export_duty_rate:
                order.export_duty_amount = order.total_amount * (order.export_duty_rate / 100)
            else:
                order.export_duty_amount = 0.0

    @api.depends('total_amount', 'net_amount', 'currency_id', 'company_id.currency_id', 'date_order')
    def _compute_amount_company_currency(self):
        """Convertit les montants du contrat dans la devise de la société.
        
        Cette méthode calcule automatiquement les montants convertis en utilisant
        le taux de change à la date de la commande. Si la devise du contrat est
        la même que celle de la société, aucune conversion n'est effectuée.
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
            
            # Convertir les montants à la date de la commande
            date = order.date_order or fields.Date.context_today(order)
            
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
            
            # Affichage du taux de conversion (1 devise contrat = X devise société)
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

    @api.depends('transit_order_ids.lot_ids', 'total_amount', 'total_tonnage')
    def _compute_costs(self):
        """Calculate costs based on cocoa bean lots used"""
        for order in self:
            estimated_cost = 0.0
            actual_cost = 0.0
            
            # Calculate cost from linked bean lots (if cocoa_bean_management is installed)
            for ot in order.transit_order_ids:
                for lot in ot.lot_ids:
                    # Check if bean_lot_ids exists (from cocoa_bean_management module)
                    if hasattr(lot, 'bean_lot_ids') and lot.bean_lot_ids:
                        for bean_lot in lot.bean_lot_ids:
                            if hasattr(bean_lot, 'unit_cost') and hasattr(bean_lot, 'quantity_used'):
                                actual_cost += bean_lot.unit_cost * bean_lot.quantity_used
            
            order.actual_cost = actual_cost
            order.estimated_cost = actual_cost if actual_cost else order.total_tonnage * 1500  # Default estimation
            
            # Calculate margin
            order.estimated_margin = order.net_amount - order.estimated_cost
            if order.net_amount > 0:
                order.margin_percentage = (order.estimated_margin / order.net_amount) * 100
            else:
                order.margin_percentage = 0.0

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('potting.customer.order') or _('Nouveau')
            # Generate contract number if not provided
            if not vals.get('contract_number'):
                vals['contract_number'] = self.env['ir.sequence'].next_by_code('potting.contract') or False
        return super().create(vals_list)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': _('Nouveau'),
            'contract_number': False,
            'state': 'draft',
            'date_order': fields.Date.context_today(self),
            'export_duty_collected': False,
            'export_duty_collection_date': False,
        })
        return super().copy(default)

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les commandes en brouillon ou annulées. "
                    "La commande '%s' est en état '%s'."
                ) % (order.name, dict(order._fields['state'].selection).get(order.state)))
            # Vérifier qu'aucun OT n'a de lots avec production
            for ot in order.transit_order_ids:
                if any(lot.current_tonnage > 0 for lot in ot.lot_ids):
                    raise UserError(_(
                        "Impossible de supprimer la commande '%s': "
                        "l'OT '%s' a des lots avec de la production."
                    ) % (order.name, ot.name))
        return super().unlink()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS - STATISTIQUES
    # -------------------------------------------------------------------------
    @api.depends('transit_order_ids')
    def _compute_transit_order_count(self):
        for order in self:
            order.transit_order_count = len(order.transit_order_ids)

    @api.depends('transit_order_ids.tonnage')
    def _compute_total_tonnage(self):
        for order in self:
            order.total_tonnage = sum(order.transit_order_ids.mapped('tonnage'))

    @api.depends('contract_tonnage', 'total_tonnage')
    def _compute_remaining_contract_tonnage(self):
        """Calcule le tonnage restant à allouer (contrat - OT créés)."""
        for order in self:
            if order.contract_tonnage:
                order.remaining_contract_tonnage = order.contract_tonnage - order.total_tonnage
            else:
                order.remaining_contract_tonnage = 0.0

    @api.depends('transit_order_ids.lot_ids.current_tonnage', 'transit_order_ids.lot_ids.state', 'total_tonnage')
    def _compute_potted_stats(self):
        for order in self:
            potted_lots = order.transit_order_ids.lot_ids.filtered(lambda l: l.state == 'potted')
            order.potted_tonnage = sum(potted_lots.mapped('current_tonnage'))
            if order.total_tonnage > 0:
                order.progress_percentage = (order.potted_tonnage / order.total_tonnage) * 100
            else:
                order.progress_percentage = 0.0

    @api.depends('date_expected', 'state')
    def _compute_is_late(self):
        today = fields.Date.context_today(self)
        for order in self:
            order.is_late = (
                order.date_expected and 
                order.date_expected < today and 
                order.state not in ('done', 'cancelled')
            )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """Update consignee on transit orders when customer changes"""
        if self.customer_id and self.transit_order_ids:
            for ot in self.transit_order_ids:
                if not ot.consignee_id:
                    ot.consignee_id = self.customer_id

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_("Seules les commandes en brouillon peuvent être confirmées."))
            if not order.transit_order_ids:
                raise UserError(_("Vous devez ajouter au moins un Ordre de Transit avant de confirmer."))
            order.state = 'confirmed'
            order.message_post(body=_("Commande confirmée."))

    def action_start(self):
        for order in self:
            if order.state != 'confirmed':
                raise UserError(_("Seules les commandes confirmées peuvent être démarrées."))
            order.state = 'in_progress'
            order.message_post(body=_("Production démarrée."))

    def action_done(self):
        for order in self:
            if order.state != 'in_progress':
                raise UserError(_("Seules les commandes en cours peuvent être terminées."))
            # Check if all transit orders are done
            if any(ot.state != 'done' for ot in order.transit_order_ids):
                raise UserError(_("Tous les Ordres de Transit doivent être terminés avant de clôturer la commande."))
            order.state = 'done'
            order.message_post(body=_("Commande terminée avec succès."))

    def action_cancel(self):
        for order in self:
            if order.state == 'done':
                raise UserError(_("Les commandes terminées ne peuvent pas être annulées."))
            # Cancel all transit orders
            order.transit_order_ids.filtered(lambda ot: ot.state != 'cancelled').action_cancel()
            order.state = 'cancelled'
            order.message_post(body=_("Commande annulée."))

    def action_draft(self):
        """Remettre la commande en brouillon de façon sécurisée"""
        for order in self:
            # Ne peut remettre en brouillon que depuis certains états
            if order.state == 'done':
                raise UserError(_(
                    "Les commandes terminées ne peuvent pas être remises en brouillon. "
                    "Veuillez d'abord les annuler."
                ))
            if order.state == 'draft':
                continue  # Déjà en brouillon
            
            # Vérifier qu'aucun OT n'a des lots empotés
            for ot in order.transit_order_ids:
                potted_lots = ot.lot_ids.filtered(lambda l: l.state == 'potted')
                if potted_lots:
                    raise UserError(_(
                        "Impossible de remettre la commande en brouillon: "
                        "l'OT '%s' a %d lot(s) empoté(s)."
                    ) % (ot.name, len(potted_lots)))
            
            # Remettre les OT en brouillon aussi
            for ot in order.transit_order_ids:
                if ot.state not in ('draft', 'cancelled'):
                    ot.action_draft()
            
            order.state = 'draft'
            order.message_post(body=_("🔄 Commande remise en brouillon par %s.") % self.env.user.name)


    def action_view_transit_orders(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Ordres de Transit'),
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,kanban,form',
            'domain': [('customer_order_id', '=', self.id)],
            'context': {
                'default_customer_order_id': self.id,
                'default_consignee_id': self.customer_id.id,
            },
        }
        if len(self.transit_order_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.transit_order_ids.id
        return action

    def action_view_lots(self):
        """View all lots linked to this customer order"""
        self.ensure_one()
        lots = self.transit_order_ids.lot_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Lots'),
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('id', 'in', lots.ids)],
        }
        return action

    def action_open_create_ot_wizard(self):
        """Ouvrir le wizard de création d'OT"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Créer des Ordres de Transit"),
            'res_model': 'potting.create.ot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_order_id': self.id,
            },
        }
    
    def action_open_generate_ot_wizard(self):
        """Ouvrir le wizard de génération automatique d'OT.
        
        Cette fonctionnalité est optionnelle et peut être désactivée
        dans les paramètres du module.
        """
        self.ensure_one()
        
        # Vérifier si la fonctionnalité est activée
        ICP = self.env['ir.config_parameter'].sudo()
        is_enabled = ICP.get_param('potting_management.enable_generate_ot_from_order', 'True')
        
        if is_enabled.lower() not in ('true', '1'):
            raise UserError(_(
                "La génération automatique d'OT est désactivée. "
                "Veuillez contacter votre administrateur pour l'activer dans la configuration du module."
            ))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _("Générer des Ordres de Transit"),
            'res_model': 'potting.generate.ot.from.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_order_id': self.id,
            },
        }

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def get_summary_data(self):
        """Get summary data for reporting"""
        self.ensure_one()
        return {
            'name': self.name,
            'customer': self.customer_id.name,
            'date_order': self.date_order,
            'date_expected': self.date_expected,
            'total_tonnage': self.total_tonnage,
            'potted_tonnage': self.potted_tonnage,
            'progress': self.progress_percentage,
            'transit_orders': [{
                'name': ot.name,
                'product_type': ot.product_type,
                'tonnage': ot.tonnage,
                'lots': len(ot.lot_ids),
                'potted_lots': ot.potted_lot_count,
                'state': ot.state,
            } for ot in self.transit_order_ids],
        }
