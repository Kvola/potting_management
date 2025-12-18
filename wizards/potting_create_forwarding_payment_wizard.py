# -*- coding: utf-8 -*-
"""
Wizard pour créer des paiements de transitaires via le module payment_request_validation.

Ce wizard permet de créer des demandes de paiement pour les transitaires,
avec support des paiements par chèques, paiements partiels et avances.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingCreateForwardingPaymentWizard(models.TransientModel):
    """Wizard pour créer un paiement transitaire"""
    _name = 'potting.create.forwarding.payment.wizard'
    _description = 'Créer un Paiement Transitaire'

    # =========================================================================
    # CHAMPS - TRANSITAIRE
    # =========================================================================
    
    forwarding_agent_id = fields.Many2one(
        'potting.forwarding.agent',
        string="Transitaire",
        required=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string="Partenaire",
        related='forwarding_agent_id.partner_id',
        readonly=True
    )
    
    payment_line_id = fields.Many2one(
        'potting.forwarding.agent.payment',
        string="Ligne de paiement",
        help="Ligne de paiement existante à associer"
    )
    
    # =========================================================================
    # CHAMPS - MONTANTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='forwarding_agent_id.currency_id',
        readonly=True
    )
    
    balance_due = fields.Monetary(
        string="Solde dû",
        currency_field='currency_id',
        related='forwarding_agent_id.balance_due',
        readonly=True
    )
    
    amount = fields.Monetary(
        string="Montant à payer",
        currency_field='currency_id',
        required=True
    )
    
    # =========================================================================
    # CHAMPS - TYPE DE PAIEMENT
    # =========================================================================
    
    payment_type = fields.Selection([
        ('advance', 'Avance'),
        ('partial', 'Paiement partiel'),
        ('final', 'Paiement final'),
    ], string="Type de paiement",
    required=True,
    default='partial'
    )
    
    payment_method = fields.Selection([
        ('check', 'Chèque'),
        ('bank_transfer', 'Virement bancaire'),
    ], string="Mode de paiement",
    required=True,
    default='check'
    )
    
    # =========================================================================
    # CHAMPS - DEMANDE DE PAIEMENT
    # =========================================================================
    
    create_payment_request = fields.Boolean(
        string="Créer une demande de paiement",
        default=True,
        help="Créer une demande de paiement dans le module payment_request_validation"
    )
    
    existing_payment_request_id = fields.Many2one(
        'payment.request',
        string="Demande existante",
        domain="[('state', 'in', ['draft', 'submitted', 'in_progress'])]",
        help="Ajouter le paiement à une demande existante"
    )
    
    subject = fields.Char(
        string="Objet",
        help="Objet de la demande de paiement"
    )
    
    expected_payment_date = fields.Date(
        string="Date de paiement souhaitée",
        default=fields.Date.context_today
    )
    
    # =========================================================================
    # CHAMPS - ORDRES DE TRANSIT
    # =========================================================================
    
    transit_order_ids = fields.Many2many(
        'potting.transit.order',
        'potting_fwd_pay_wiz_transit_order_rel',  # Nom court pour éviter limite PostgreSQL 63 chars
        'wizard_id',
        'transit_order_id',
        string="Ordres de Transit",
        domain="[('forwarding_agent_id', '=', forwarding_agent_id), ('state', 'in', ['in_progress', 'ready_validation', 'done'])]",
        help="OT concernés par ce paiement"
    )
    
    notes = fields.Text(
        string="Notes"
    )

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('forwarding_agent_id')
    def _onchange_forwarding_agent(self):
        if self.forwarding_agent_id:
            self.amount = self.forwarding_agent_id.balance_due
            self.subject = _("Paiement transitaire - %s") % self.forwarding_agent_id.name
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type == 'final':
            self.amount = self.forwarding_agent_id.balance_due
    
    @api.onchange('transit_order_ids')
    def _onchange_transit_orders(self):
        if self.transit_order_ids:
            total = sum(self.transit_order_ids.mapped('forwarding_agent_fee'))
            self.amount = total

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if wizard.amount <= 0:
                raise ValidationError(_("Le montant doit être supérieur à 0."))

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_create_payment(self):
        """Create the payment and optionally a payment request"""
        self.ensure_one()
        
        # Check if payment_request module is installed
        payment_request_available = 'payment.request' in self.env
        
        if self.create_payment_request and not payment_request_available:
            raise UserError(_(
                "Le module 'payment_request_validation' doit être installé "
                "pour créer des demandes de paiement."
            ))
        
        # Create the forwarding agent payment line
        payment_line_vals = {
            'forwarding_agent_id': self.forwarding_agent_id.id,
            'payment_type': self.payment_type,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'payment_date': self.expected_payment_date or fields.Date.today(),
            'notes': self.notes,
            'state': 'draft',
        }
        
        if self.transit_order_ids:
            # Link to first transit order if multiple
            payment_line_vals['transit_order_id'] = self.transit_order_ids[0].id
        
        payment_line = self.env['potting.forwarding.agent.payment'].create(payment_line_vals)
        
        # Create or update payment request
        if self.create_payment_request and payment_request_available:
            if self.existing_payment_request_id:
                payment_request = self.existing_payment_request_id
            else:
                payment_request = self._create_payment_request()
            
            # Add payment to request based on payment method
            if self.payment_method == 'check':
                check = self._create_check(payment_request)
                payment_line.check_id = check
            else:
                transfer = self._create_transfer(payment_request)
                payment_line.transfer_id = transfer
            
            payment_line.payment_request_id = payment_request
            payment_line.state = 'pending'
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Demande de paiement'),
                'res_model': 'payment.request',
                'view_mode': 'form',
                'res_id': payment_request.id,
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paiement transitaire'),
            'res_model': 'potting.forwarding.agent.payment',
            'view_mode': 'form',
            'res_id': payment_line.id,
        }
    
    def _create_payment_request(self):
        """Create a new payment request"""
        subject = self.subject or _("Paiement transitaire - %s") % self.forwarding_agent_id.name
        
        # Build justification
        justification_lines = [
            _("<p><strong>Paiement transitaire</strong></p>"),
            _("<ul>"),
            _("<li>Transitaire: %s</li>") % self.forwarding_agent_id.name,
            _("<li>Type: %s</li>") % dict(self._fields['payment_type'].selection).get(self.payment_type),
            _("<li>Montant: %s %s</li>") % (self.amount, self.currency_id.symbol),
        ]
        
        if self.transit_order_ids:
            ot_names = ', '.join(self.transit_order_ids.mapped('name'))
            justification_lines.append(_("<li>Ordres de Transit: %s</li>") % ot_names)
        
        justification_lines.append(_("</ul>"))
        
        if self.notes:
            justification_lines.append(_("<p><strong>Notes:</strong> %s</p>") % self.notes)
        
        payment_request = self.env['payment.request'].create({
            'subject': subject,
            'expected_payment_date': self.expected_payment_date,
            'justification': ''.join(justification_lines),
            'urgency_level': 'normal',
        })
        
        return payment_request
    
    def _create_check(self, payment_request):
        """Create a check in the payment request"""
        check_vals = {
            'payment_request_id': payment_request.id,
            'beneficiary_id': self.partner_id.id,
            'amount': self.amount,
            'payment_reason': _("Paiement transitaire - %s") % self.forwarding_agent_id.name,
        }
        
        return self.env['payment.request.check'].create(check_vals)
    
    def _create_transfer(self, payment_request):
        """Create a transfer in the payment request"""
        # Get default bank account
        bank_account = self.forwarding_agent_id.default_bank_account_id
        if not bank_account and self.partner_id.bank_ids:
            bank_account = self.partner_id.bank_ids[0]
        
        transfer_vals = {
            'payment_request_id': payment_request.id,
            'beneficiary_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'payment_reason': _("Paiement transitaire - %s") % self.forwarding_agent_id.name,
        }
        
        if bank_account:
            transfer_vals['beneficiary_bank_id'] = bank_account.id
        
        return self.env['payment.request.transfer'].create(transfer_vals)
