# -*- coding: utf-8 -*-
"""
Modèle pour la gestion des transitaires (Forwarding Agents).

Les transitaires sont responsables des opérations d'exportation et peuvent
recevoir des paiements via le module payment_request_validation.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingForwardingAgent(models.Model):
    """Transitaire d'exportation
    
    Gère les informations des transitaires qui s'occupent des exportations:
    - Informations de contact
    - Ordres de transit associés
    - Paiements (via payment.request)
    - Avances et paiements partiels
    """
    _name = 'potting.forwarding.agent'
    _description = 'Transitaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    _sql_constraints = [
        ('partner_uniq', 'unique(partner_id)', 
         'Ce partenaire est déjà enregistré comme transitaire!'),
    ]

    # =========================================================================
    # CHAMPS - IDENTIFICATION
    # =========================================================================
    
    name = fields.Char(
        string="Nom",
        related='partner_id.name',
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string="Partenaire",
        required=True,
        ondelete='restrict',
        tracking=True,
        domain="[('is_company', '=', True)]",
        help="Partenaire associé au transitaire"
    )
    
    code = fields.Char(
        string="Code",
        tracking=True,
        index=True,
        help="Code interne du transitaire"
    )
    
    active = fields.Boolean(
        string="Actif",
        default=True
    )
    
    # =========================================================================
    # CHAMPS - CONTACT
    # =========================================================================
    
    phone = fields.Char(
        string="Téléphone",
        related='partner_id.phone',
        readonly=False
    )
    
    email = fields.Char(
        string="Email",
        related='partner_id.email',
        readonly=False
    )
    
    address = fields.Char(
        string="Adresse",
        compute='_compute_address',
        store=True
    )
    
    # =========================================================================
    # CHAMPS - BANCAIRES
    # =========================================================================
    
    bank_account_ids = fields.One2many(
        related='partner_id.bank_ids',
        string="Comptes bancaires"
    )
    
    default_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string="Compte bancaire par défaut",
        domain="[('partner_id', '=', partner_id)]",
        help="Compte bancaire utilisé par défaut pour les paiements"
    )
    
    # =========================================================================
    # CHAMPS - ORDRES DE TRANSIT
    # =========================================================================
    
    transit_order_ids = fields.One2many(
        'potting.transit.order',
        'forwarding_agent_id',
        string="Ordres de Transit"
    )
    
    transit_order_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_transit_order_count',
        store=True
    )
    
    active_transit_order_count = fields.Integer(
        string="OT en cours",
        compute='_compute_transit_order_count',
        store=True
    )
    
    # =========================================================================
    # CHAMPS - PAIEMENTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self._get_default_currency(),
        required=True,
        help="Devise utilisée pour les paiements de ce transitaire."
    )
    
    payment_line_ids = fields.One2many(
        'potting.forwarding.agent.payment',
        'forwarding_agent_id',
        string="Lignes de paiement"
    )
    
    total_invoiced = fields.Monetary(
        string="Total facturé",
        currency_field='currency_id',
        compute='_compute_payment_stats',
        store=True,
        help="Montant total facturé au transitaire"
    )
    
    total_paid = fields.Monetary(
        string="Total payé",
        currency_field='currency_id',
        compute='_compute_payment_stats',
        store=True,
        help="Montant total payé au transitaire"
    )
    
    total_advances = fields.Monetary(
        string="Total avances",
        currency_field='currency_id',
        compute='_compute_payment_stats',
        store=True,
        help="Montant total des avances versées"
    )
    
    balance_due = fields.Monetary(
        string="Solde dû",
        currency_field='currency_id',
        compute='_compute_payment_stats',
        store=True,
        help="Montant restant à payer"
    )
    
    payment_progress = fields.Float(
        string="Progression paiement (%)",
        compute='_compute_payment_stats',
        store=True
    )
    
    # =========================================================================
    # CHAMPS - CONFIGURATION
    # =========================================================================
    
    commission_rate = fields.Float(
        string="Taux de commission (%)",
        default=0.0,
        help="Taux de commission du transitaire en pourcentage"
    )
    
    fixed_fee_per_container = fields.Monetary(
        string="Frais fixes par conteneur",
        currency_field='currency_id',
        help="Frais fixes appliqués par conteneur"
    )
    
    notes = fields.Text(
        string="Notes"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        required=True
    )

    # =========================================================================
    # DEFAULT METHODS
    # =========================================================================
    
    @api.model
    def _get_default_currency(self):
        """Get the default currency for the potting module.
        
        Returns the configured default currency if set, otherwise falls back
        to the company currency.
        
        Returns:
            res.currency: The default currency record
        """
        return self.env['res.config.settings'].get_default_currency()

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('partner_id', 'partner_id.street', 'partner_id.city', 'partner_id.country_id')
    def _compute_address(self):
        for agent in self:
            parts = []
            if agent.partner_id:
                if agent.partner_id.street:
                    parts.append(agent.partner_id.street)
                if agent.partner_id.city:
                    parts.append(agent.partner_id.city)
                if agent.partner_id.country_id:
                    parts.append(agent.partner_id.country_id.name)
            agent.address = ', '.join(parts) if parts else ''
    
    @api.depends('transit_order_ids', 'transit_order_ids.state')
    def _compute_transit_order_count(self):
        for agent in self:
            agent.transit_order_count = len(agent.transit_order_ids)
            agent.active_transit_order_count = len(
                agent.transit_order_ids.filtered(lambda o: o.state not in ('done', 'cancelled'))
            )
    
    @api.depends('payment_line_ids', 'payment_line_ids.amount', 'payment_line_ids.state', 'payment_line_ids.payment_type')
    def _compute_payment_stats(self):
        for agent in self:
            confirmed_payments = agent.payment_line_ids.filtered(lambda l: l.state == 'confirmed')
            
            # Total des avances
            advances = confirmed_payments.filtered(lambda l: l.payment_type == 'advance')
            agent.total_advances = sum(advances.mapped('amount'))
            
            # Total payé (tous types confondus)
            agent.total_paid = sum(confirmed_payments.mapped('amount'))
            
            # Total facturé (calculé depuis les OT)
            agent.total_invoiced = sum(
                agent.transit_order_ids.filtered(
                    lambda o: o.state in ('in_progress', 'ready_validation', 'done')
                ).mapped('forwarding_agent_fee')
            )
            
            # Solde dû
            agent.balance_due = agent.total_invoiced - agent.total_paid
            
            # Progression
            if agent.total_invoiced > 0:
                agent.payment_progress = (agent.total_paid / agent.total_invoiced) * 100
            else:
                agent.payment_progress = 0.0

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_view_transit_orders(self):
        """View transit orders for this forwarding agent"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordres de Transit - %s') % self.name,
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,kanban,form',
            'domain': [('forwarding_agent_id', '=', self.id)],
            'context': {'default_forwarding_agent_id': self.id},
        }
    
    def action_view_payments(self):
        """View payments for this forwarding agent"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paiements - %s') % self.name,
            'res_model': 'potting.forwarding.agent.payment',
            'view_mode': 'tree,form',
            'domain': [('forwarding_agent_id', '=', self.id)],
            'context': {'default_forwarding_agent_id': self.id},
        }
    
    def action_create_payment_request(self):
        """Create a payment request for this forwarding agent"""
        self.ensure_one()
        
        if self.balance_due <= 0:
            raise UserError(_("Le solde dû au transitaire est nul ou négatif."))
        
        # Check if payment_request_validation module is installed
        if 'payment.request' not in self.env:
            raise UserError(_(
                "Le module 'payment_request_validation' doit être installé "
                "pour créer des demandes de paiement."
            ))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Créer une demande de paiement'),
            'res_model': 'potting.create.forwarding.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_forwarding_agent_id': self.id,
                'default_amount': self.balance_due,
            },
        }

    # =========================================================================
    # BUSINESS METHODS
    # =========================================================================
    
    def get_payment_summary(self):
        """Get payment summary for reporting"""
        self.ensure_one()
        return {
            'name': self.name,
            'total_invoiced': self.total_invoiced,
            'total_paid': self.total_paid,
            'total_advances': self.total_advances,
            'balance_due': self.balance_due,
            'progress': self.payment_progress,
            'transit_orders': len(self.transit_order_ids),
            'payments': [{
                'date': p.payment_date,
                'type': p.payment_type,
                'amount': p.amount,
                'state': p.state,
            } for p in self.payment_line_ids.sorted('payment_date', reverse=True)]
        }


class PottingForwardingAgentPayment(models.Model):
    """Ligne de paiement pour un transitaire
    
    Permet de suivre les paiements effectués (avances et paiements partiels)
    similaire au modèle purchase.request.payment.line.
    """
    _name = 'potting.forwarding.agent.payment'
    _description = 'Paiement Transitaire'
    _order = 'payment_date desc, id desc'
    _inherit = ['mail.thread']

    # =========================================================================
    # CHAMPS - RELATIONS
    # =========================================================================
    
    forwarding_agent_id = fields.Many2one(
        'potting.forwarding.agent',
        string="Transitaire",
        required=True,
        ondelete='cascade',
        index=True
    )
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        help="OT spécifique pour lequel ce paiement est effectué"
    )
    
    payment_request_id = fields.Many2one(
        'payment.request',
        string="Demande de paiement",
        help="Demande de paiement associée (si applicable)",
        index=True
    )
    
    check_id = fields.Many2one(
        'payment.request.check',
        string="Chèque associé",
        help="Chèque créé dans la demande de paiement",
        readonly=True
    )
    
    transfer_id = fields.Many2one(
        'payment.request.transfer',
        string="Virement associé",
        help="Virement créé dans la demande de paiement",
        readonly=True
    )
    
    # =========================================================================
    # CHAMPS - INFORMATIONS DE PAIEMENT
    # =========================================================================
    
    name = fields.Char(
        string="Référence",
        required=True,
        default=lambda self: _('Nouveau'),
        copy=False,
        index=True
    )
    
    payment_type = fields.Selection([
        ('advance', 'Avance'),
        ('partial', 'Paiement partiel'),
        ('final', 'Paiement final'),
    ], string="Type de paiement",
    required=True,
    default='partial',
    tracking=True
    )
    
    payment_date = fields.Date(
        string="Date de paiement",
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='forwarding_agent_id.currency_id',
        store=True,
        readonly=True
    )
    
    amount = fields.Monetary(
        string="Montant",
        required=True,
        currency_field='currency_id',
        tracking=True
    )
    
    payment_method = fields.Selection([
        ('check', 'Chèque'),
        ('bank_transfer', 'Virement bancaire'),
        ('cash', 'Espèces'),
        ('other', 'Autre'),
    ], string="Mode de paiement",
    default='check',
    tracking=True
    )
    
    reference = fields.Char(
        string="Référence du paiement",
        help="Numéro de chèque, de virement, etc.",
        tracking=True
    )
    
    notes = fields.Text(
        string="Notes"
    )
    
    # =========================================================================
    # CHAMPS - ÉTAT
    # =========================================================================
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En attente de validation'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
    ], string="État",
    default='draft',
    tracking=True
    )
    
    confirmed_by_id = fields.Many2one(
        'res.users',
        string="Confirmé par",
        readonly=True,
        copy=False
    )
    
    confirmed_date = fields.Datetime(
        string="Date de confirmation",
        readonly=True,
        copy=False
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        related='forwarding_agent_id.company_id',
        store=True
    )
    
    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 
         'Le montant du paiement doit être positif!'),
        ('name_unique', 'UNIQUE(name)', 
         'La référence de paiement doit être unique!'),
    ]
    
    # =========================================================================
    # CRUD METHODS
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'potting.forwarding.agent.payment'
                ) or _('Nouveau')
        return super().create(vals_list)
    
    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_confirm(self):
        """Confirm the payment"""
        for payment in self:
            if payment.state != 'draft':
                raise UserError(_("Seuls les paiements en brouillon peuvent être confirmés."))
            payment.write({
                'state': 'confirmed',
                'confirmed_by_id': self.env.user.id,
                'confirmed_date': fields.Datetime.now(),
            })
            payment.message_post(body=_("Paiement confirmé."))
    
    def action_cancel(self):
        """Cancel the payment"""
        for payment in self:
            if payment.state == 'confirmed':
                raise UserError(_("Les paiements confirmés ne peuvent pas être annulés."))
            payment.state = 'cancelled'
            payment.message_post(body=_("Paiement annulé."))
    
    def action_draft(self):
        """Reset to draft"""
        for payment in self:
            if payment.state == 'confirmed':
                raise UserError(_("Les paiements confirmés ne peuvent pas être remis en brouillon."))
            payment.state = 'draft'
    
    def action_create_payment_request(self):
        """Create a payment request for this payment line"""
        self.ensure_one()
        
        if self.payment_request_id:
            raise UserError(_("Une demande de paiement existe déjà pour ce paiement."))
        
        # Check if payment_request_validation module is installed
        if 'payment.request' not in self.env:
            raise UserError(_(
                "Le module 'payment_request_validation' doit être installé "
                "pour créer des demandes de paiement."
            ))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Créer une demande de paiement'),
            'res_model': 'potting.create.forwarding.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_forwarding_agent_id': self.forwarding_agent_id.id,
                'default_payment_line_id': self.id,
                'default_amount': self.amount,
                'default_payment_method': self.payment_method,
            },
        }
