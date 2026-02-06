# -*- coding: utf-8 -*-
"""
Wizard pour créer des paiements de formules via le module payment_request_validation.

Ce wizard permet de créer des demandes de paiement par chèque pour les formules,
avec distinction entre paiement avant-vente et après-vente.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingFormulePaymentWizard(models.TransientModel):
    """Wizard pour créer un paiement de formule par chèque"""
    _name = 'potting.formule.payment.wizard'
    _description = 'Paiement Formule par Chèque'

    # =========================================================================
    # CHAMPS - FORMULE
    # =========================================================================
    
    formule_id = fields.Many2one(
        'potting.formule',
        string="Formule",
        required=True,
        readonly=True
    )
    
    formule_name = fields.Char(
        string="N° Formule",
        related='formule_id.name',
        readonly=True
    )
    
    confirmation_vente_id = fields.Many2one(
        'potting.confirmation.vente',
        string="Confirmation de Vente",
        related='formule_id.confirmation_vente_id',
        readonly=True
    )
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        related='formule_id.transit_order_id',
        readonly=True
    )
    
    # =========================================================================
    # CHAMPS - TYPE DE PAIEMENT
    # =========================================================================
    
    payment_type = fields.Selection([
        ('avant_vente', 'Paiement Avant-Vente'),
        ('apres_vente', 'Paiement Après-Vente'),
    ], string="Type de paiement",
       required=True,
       help="Avant-vente: avance avant commercialisation | Après-vente: solde après vente OT"
    )
    
    # =========================================================================
    # CHAMPS - INFORMATIONS ÉTAT FORMULE
    # =========================================================================
    
    avant_vente_paye = fields.Boolean(
        string="Avant-vente déjà payé",
        related='formule_id.avant_vente_paye',
        readonly=True
    )
    
    apres_vente_paye = fields.Boolean(
        string="Après-vente déjà payé",
        related='formule_id.apres_vente_paye',
        readonly=True
    )
    
    montant_avant_vente = fields.Monetary(
        string="Montant avant-vente",
        related='formule_id.montant_avant_vente',
        readonly=True,
        currency_field='currency_id'
    )
    
    montant_apres_vente = fields.Monetary(
        string="Montant après-vente",
        related='formule_id.montant_apres_vente',
        readonly=True,
        currency_field='currency_id'
    )
    
    # =========================================================================
    # CHAMPS - MONTANTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='formule_id.currency_id',
        readonly=True
    )
    
    amount = fields.Monetary(
        string="Montant à payer",
        currency_field='currency_id',
        required=True
    )
    
    # =========================================================================
    # CHAMPS - BANQUE ÉMETTRICE
    # =========================================================================
    
    bank_id = fields.Many2one(
        'res.bank',
        string="Banque émettrice",
        required=True,
        domain="[('is_active', '=', True), ('supports_checks', '=', True)]",
        help="Banque de la société pour l'émission du chèque"
    )
    
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string="Compte émetteur",
        required=True,
        domain="[('bank_id', '=', bank_id)]",
        help="Compte bancaire de la société"
    )
    
    # =========================================================================
    # CHAMPS - CHÈQUE
    # =========================================================================
    
    check_number = fields.Char(
        string="Numéro de chèque",
        required=True,
        help="Numéro du chèque à utiliser (saisie manuelle obligatoire)"
    )
    
    check_date = fields.Date(
        string="Date du chèque",
        default=fields.Date.context_today,
        required=True
    )
    
    # =========================================================================
    # CHAMPS - BÉNÉFICIAIRE
    # =========================================================================
    
    beneficiary_name = fields.Char(
        string="Bénéficiaire",
        required=True,
        help="Nom du bénéficiaire sur le chèque"
    )
    
    beneficiary_id = fields.Many2one(
        'res.partner',
        string="Partenaire bénéficiaire",
        help="Partenaire associé (optionnel)"
    )
    
    # =========================================================================
    # CHAMPS - DEMANDE DE PAIEMENT
    # =========================================================================
    
    create_new_request = fields.Boolean(
        string="Créer nouvelle demande",
        default=True,
        help="Créer une nouvelle demande de paiement ou ajouter à une existante"
    )
    
    existing_payment_request_id = fields.Many2one(
        'payment.request',
        string="Demande existante",
        domain="[('state', 'in', ['draft']), ('bank_id', '=', bank_id)]",
        help="Ajouter le chèque à une demande existante"
    )
    
    expected_payment_date = fields.Date(
        string="Date de paiement souhaitée",
        default=fields.Date.context_today
    )
    
    # =========================================================================
    # CHAMPS - NOTES
    # =========================================================================
    
    notes = fields.Text(
        string="Notes",
        help="Notes ou justification du paiement"
    )

    # =========================================================================
    # MÉTHODES ONCHANGE
    # =========================================================================
    
    @api.onchange('formule_id')
    def _onchange_formule(self):
        """Initialiser les valeurs depuis la formule"""
        if self.formule_id:
            # Déterminer le type de paiement par défaut
            if not self.formule_id.avant_vente_paye:
                self.payment_type = 'avant_vente'
                self.amount = self.formule_id.montant_avant_vente
            elif not self.formule_id.apres_vente_paye:
                self.payment_type = 'apres_vente'
                self.amount = self.formule_id.montant_apres_vente
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Mettre à jour le montant selon le type de paiement"""
        if self.formule_id and self.payment_type:
            if self.payment_type == 'avant_vente':
                self.amount = self.formule_id.montant_avant_vente
            else:
                self.amount = self.formule_id.montant_apres_vente
    
    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        """Sélectionner le compte par défaut de la banque"""
        self.bank_account_id = False
        if self.bank_id:
            # Chercher un compte par défaut pour les chèques
            company = self.env.company
            default_account = self.env['res.partner.bank'].search([
                ('bank_id', '=', self.bank_id.id),
                ('partner_id', '=', company.partner_id.id),
                '|',
                ('is_default_for_checks', '=', True),
                ('id', '!=', False),  # Fallback sur n'importe quel compte
            ], limit=1, order='is_default_for_checks desc')
            
            if default_account:
                self.bank_account_id = default_account.id

    # =========================================================================
    # MÉTHODES DE CONTRAINTE
    # =========================================================================
    
    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if wizard.amount <= 0:
                raise ValidationError(_("Le montant doit être supérieur à 0."))
    
    @api.constrains('payment_type', 'formule_id')
    def _check_payment_type(self):
        for wizard in self:
            if wizard.payment_type == 'avant_vente' and wizard.formule_id.avant_vente_paye:
                raise ValidationError(_(
                    "Le paiement avant-vente a déjà été effectué pour cette formule."
                ))
            if wizard.payment_type == 'apres_vente' and wizard.formule_id.apres_vente_paye:
                raise ValidationError(_(
                    "Le paiement après-vente a déjà été effectué pour cette formule."
                ))
            if wizard.payment_type == 'apres_vente' and not wizard.formule_id.avant_vente_paye:
                raise ValidationError(_(
                    "Le paiement avant-vente doit être effectué avant le paiement après-vente."
                ))

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_create_payment(self):
        """Créer la demande de paiement avec le chèque"""
        self.ensure_one()
        
        # Vérifier que le paiement après-vente a une facture client OT
        if self.payment_type == 'apres_vente':
            if not self.formule_id.transit_order_id:
                raise UserError(_(
                    "La formule doit être liée à un Ordre de Transit pour le paiement après-vente."
                ))
            # Optionnel: vérifier qu'une facture client existe pour l'OT
            # if not self.formule_id.transit_order_id.invoice_ids:
            #     raise UserError(_("Une facture client doit être créée pour l'OT avant le paiement après-vente."))
        
        # Créer ou récupérer la demande de paiement
        if self.create_new_request or not self.existing_payment_request_id:
            payment_request = self._create_payment_request()
        else:
            payment_request = self.existing_payment_request_id
            # Vérifier que la banque correspond
            if payment_request.bank_id != self.bank_id:
                payment_request.write({'bank_id': self.bank_id.id})
        
        # Créer le chèque dans la demande
        check = self._create_check(payment_request)
        
        # Lier la demande à la formule
        self._link_payment_to_formule(payment_request)
        
        # Message dans le chatter de la formule
        self.formule_id.message_post(
            body=_(
                "Demande de paiement créée:\n"
                "- Type: %s\n"
                "- Montant: %s %s\n"
                "- N° Chèque: %s\n"
                "- Banque: %s\n"
                "- Référence: %s"
            ) % (
                dict(self._fields['payment_type'].selection).get(self.payment_type),
                self.amount,
                self.currency_id.symbol,
                self.check_number,
                self.bank_id.name,
                payment_request.reference
            ),
            subject=_("Paiement formule créé"),
            subtype_xmlid='mail.mt_comment'
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Demande de paiement'),
            'res_model': 'payment.request',
            'view_mode': 'form',
            'res_id': payment_request.id,
        }
    
    def _create_payment_request(self):
        """Créer une nouvelle demande de paiement"""
        payment_type_label = dict(self._fields['payment_type'].selection).get(self.payment_type)
        
        subject = _("Paiement Formule %s - %s") % (
            self.formule_id.name,
            payment_type_label
        )
        
        # Construire la justification
        justification_lines = [
            "<p><strong>Paiement de Formule</strong></p>",
            "<ul>",
            f"<li>Formule: {self.formule_id.name}</li>",
            f"<li>CV: {self.formule_id.confirmation_vente_id.name if self.formule_id.confirmation_vente_id else 'N/A'}</li>",
            f"<li>Type: {payment_type_label}</li>",
            f"<li>Montant: {self.amount:,.0f} {self.currency_id.symbol}</li>",
            f"<li>Bénéficiaire: {self.beneficiary_name}</li>",
        ]
        
        if self.formule_id.transit_order_id:
            justification_lines.append(
                f"<li>OT: {self.formule_id.transit_order_id.name}</li>"
            )
        
        justification_lines.append("</ul>")
        
        if self.notes:
            justification_lines.append(f"<p><strong>Notes:</strong> {self.notes}</p>")
        
        payment_request = self.env['payment.request'].create({
            'subject': subject,
            'bank_id': self.bank_id.id,
            'bank_account_id': self.bank_account_id.id,
            'expected_payment_date': self.expected_payment_date,
            'justification': ''.join(justification_lines),
            'urgency_level': 'normal',
        })
        
        return payment_request
    
    def _create_check(self, payment_request):
        """Créer le chèque dans la demande de paiement"""
        
        # Trouver ou créer le partenaire bénéficiaire
        partner = self.beneficiary_id
        if not partner:
            # Chercher un partenaire existant avec ce nom
            partner = self.env['res.partner'].search([
                ('name', '=ilike', self.beneficiary_name)
            ], limit=1)
            
            if not partner:
                # Créer un nouveau partenaire
                partner = self.env['res.partner'].create({
                    'name': self.beneficiary_name,
                    'is_company': False,
                })
        
        payment_type_label = dict(self._fields['payment_type'].selection).get(self.payment_type)
        
        check_vals = {
            'payment_request_id': payment_request.id,
            'beneficiary': self.beneficiary_name,
            'partner_id': partner.id,
            'amount': self.amount,
            'check_date': self.check_date,
            'check_number': self.check_number,
            'number_generation_method': 'manual',
            'memo': _("Formule %s - %s") % (self.formule_id.name, payment_type_label),
        }
        
        check = self.env['payment.request.check'].create(check_vals)
        return check
    
    def _link_payment_to_formule(self, payment_request):
        """Lier la demande de paiement à la formule"""
        if self.payment_type == 'avant_vente':
            self.formule_id.write({
                'payment_request_avant_vente_id': payment_request.id,
            })
        else:
            self.formule_id.write({
                'payment_request_apres_vente_id': payment_request.id,
            })
