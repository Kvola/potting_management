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
    # CHAMPS - BANQUE ÉMETTRICE (pour paiement par chèque)
    # =========================================================================
    
    bank_id = fields.Many2one(
        'res.bank',
        string="Banque émettrice",
        domain="[('is_active', '=', True), ('supports_checks', '=', True)]",
        help="Banque de la société pour l'émission du chèque"
    )
    
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string="Compte émetteur",
        domain="[('bank_id', '=', bank_id)]",
        help="Compte bancaire de la société"
    )
    
    check_number = fields.Char(
        string="Numéro de chèque",
        help="Numéro du chèque (obligatoire pour paiement par chèque)"
    )
    
    check_date = fields.Date(
        string="Date du chèque",
        default=fields.Date.context_today
    )
    
    # =========================================================================
    # CHAMPS - FACTURE TRANSITAIRE
    # =========================================================================
    
    invoice_id = fields.Many2one(
        'potting.forwarding.agent.invoice',
        string="Facture transitaire",
        domain="[('forwarding_agent_id', '=', forwarding_agent_id), ('state', '=', 'validated')]",
        help="Facture transitaire validée à payer (obligatoire)"
    )
    
    invoice_amount = fields.Monetary(
        string="Montant facture",
        related='invoice_id.amount_total',
        readonly=True,
        currency_field='currency_id'
    )
    
    invoice_state = fields.Selection(
        related='invoice_id.state',
        readonly=True
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
    
    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        """Réinitialiser les champs bancaires si changement de méthode"""
        if self.payment_method != 'check':
            self.bank_id = False
            self.bank_account_id = False
            self.check_number = False
    
    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        """Sélectionner le compte par défaut de la banque"""
        self.bank_account_id = False
        if self.bank_id:
            company = self.env.company
            default_account = self.env['res.partner.bank'].search([
                ('bank_id', '=', self.bank_id.id),
                ('partner_id', '=', company.partner_id.id),
                '|',
                ('is_default_for_checks', '=', True),
                ('id', '!=', False),
            ], limit=1, order='is_default_for_checks desc')
            
            if default_account:
                self.bank_account_id = default_account.id
    
    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Mettre à jour le montant depuis la facture sélectionnée"""
        if self.invoice_id:
            self.amount = self.invoice_id.amount_total
            self.transit_order_ids = self.invoice_id.transit_order_ids

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if wizard.amount <= 0:
                raise ValidationError(_("Le montant doit être supérieur à 0."))
    
    @api.constrains('payment_method', 'bank_id', 'check_number')
    def _check_check_fields(self):
        """Vérifier les champs obligatoires pour paiement par chèque"""
        for wizard in self:
            if wizard.payment_method == 'check' and wizard.create_payment_request:
                if not wizard.bank_id:
                    raise ValidationError(_("La banque émettrice est obligatoire pour un paiement par chèque."))
                if not wizard.check_number:
                    raise ValidationError(_("Le numéro de chèque est obligatoire pour un paiement par chèque."))
    
    @api.constrains('invoice_id')
    def _check_invoice(self):
        """Vérifier que la facture est validée"""
        for wizard in self:
            if wizard.create_payment_request and not wizard.invoice_id:
                raise ValidationError(_(
                    "Une facture transitaire validée est requise pour créer une demande de paiement."
                ))
            if wizard.invoice_id and wizard.invoice_id.state != 'validated':
                raise ValidationError(_(
                    "La facture transitaire doit être validée par le comptable avant de créer un paiement."
                ))

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
        
        # Vérifier la facture pour les demandes de paiement
        if self.create_payment_request and not self.invoice_id:
            raise UserError(_(
                "Une facture transitaire validée est requise pour créer une demande de paiement.\n"
                "Veuillez d'abord créer et faire valider une facture transitaire."
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
            
            # Lier la facture au paiement (le payment_request_id sera calculé via related)
            if self.invoice_id:
                self.invoice_id.write({'payment_id': payment_line.id})
            
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
        
        # Ajouter les informations de la facture
        if self.invoice_id:
            justification_lines.append(_("<li>N° Facture: %s</li>") % self.invoice_id.invoice_number)
            justification_lines.append(_("<li>Date facture: %s</li>") % self.invoice_id.invoice_date)
        
        if self.transit_order_ids:
            ot_names = ', '.join(self.transit_order_ids.mapped('name'))
            justification_lines.append(_("<li>Ordres de Transit: %s</li>") % ot_names)
        
        justification_lines.append(_("</ul>"))
        
        if self.notes:
            justification_lines.append(_("<p><strong>Notes:</strong> %s</p>") % self.notes)
        
        vals = {
            'subject': subject,
            'expected_payment_date': self.expected_payment_date,
            'justification': ''.join(justification_lines),
            'urgency_level': 'normal',
        }
        
        # Ajouter la banque si paiement par chèque
        if self.payment_method == 'check' and self.bank_id:
            vals['bank_id'] = self.bank_id.id
            if self.bank_account_id:
                vals['bank_account_id'] = self.bank_account_id.id
        
        payment_request = self.env['payment.request'].create(vals)
        
        return payment_request
    
    def _create_check(self, payment_request):
        """Create a check in the payment request"""
        check_vals = {
            'payment_request_id': payment_request.id,
            'beneficiary': self.partner_id.name,
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'check_date': self.check_date or fields.Date.today(),
            'check_number': self.check_number,
            'number_generation_method': 'manual',
            'memo': _("Paiement transitaire - %s - Facture %s") % (
                self.forwarding_agent_id.name,
                self.invoice_id.invoice_number if self.invoice_id else ''
            ),
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
            'recipient_name': self.partner_id.name,
            'beneficiary_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'payment_reason': _("Paiement transitaire - %s - Facture %s") % (
                self.forwarding_agent_id.name,
                self.invoice_id.invoice_number if self.invoice_id else ''
            ),
        }
        
        if bank_account:
            transfer_vals['beneficiary_bank_id'] = bank_account.id
        
        return self.env['payment.request.transfer'].create(transfer_vals)

