# -*- coding: utf-8 -*-
"""
Wizards de paiement pour les OT - Taxes et DUS

Ces wizards permettent au comptable de créer des demandes de paiement
par chèque pour :
- La 1ère partie (taxes/redevances) - dès que la formule est liée
- La 2ème partie (DUS) - après la vente de l'OT
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingOtTaxesPaymentWizard(models.TransientModel):
    """Wizard de paiement des taxes (1ère partie de la Formule)"""
    _name = 'potting.ot.taxes.payment.wizard'
    _description = 'Paiement Taxes OT (1ère partie)'

    # =========================================================================
    # CHAMPS - OT ET FORMULE
    # =========================================================================
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        readonly=True
    )
    
    ot_name = fields.Char(
        string="N° OT",
        related='transit_order_id.name',
        readonly=True
    )
    
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
    
    # =========================================================================
    # CHAMPS - MONTANTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='formule_id.currency_id',
        readonly=True
    )
    
    montant_taxes = fields.Monetary(
        string="Montant des taxes",
        compute='_compute_montant_taxes',
        currency_field='currency_id',
        readonly=True,
        help="Montant total des taxes et redevances à payer"
    )
    
    amount = fields.Monetary(
        string="Montant à payer",
        currency_field='currency_id',
        required=True,
        help="Montant du chèque à émettre (modifiable si nécessaire)"
    )
    
    # =========================================================================
    # CHAMPS - DÉTAIL DES TAXES
    # =========================================================================
    
    taxes_detail = fields.Html(
        string="Détail des taxes",
        compute='_compute_taxes_detail',
        readonly=True
    )
    
    # =========================================================================
    # CHAMPS - CHÈQUE
    # =========================================================================
    
    check_number = fields.Char(
        string="Numéro de chèque",
        required=True,
        help="Numéro du chèque (saisie manuelle obligatoire)"
    )
    
    check_date = fields.Date(
        string="Date du chèque",
        default=fields.Date.context_today,
        required=True
    )
    
    # =========================================================================
    # CHAMPS - BANQUE
    # =========================================================================
    
    bank_id = fields.Many2one(
        'res.bank',
        string="Banque émettrice",
        required=True,
        help="Banque de la société pour l'émission du chèque"
    )
    
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string="Compte émetteur",
        domain="[('bank_id', '=', bank_id)]",
        help="Compte bancaire de la société"
    )
    
    # =========================================================================
    # CHAMPS - BÉNÉFICIAIRE
    # =========================================================================
    
    beneficiary_name = fields.Char(
        string="Bénéficiaire",
        required=True,
        default="Trésor Public - Côte d'Ivoire",
        help="Nom du bénéficiaire sur le chèque"
    )
    
    beneficiary_id = fields.Many2one(
        'res.partner',
        string="Partenaire bénéficiaire",
        help="Partenaire associé (optionnel)"
    )
    
    # =========================================================================
    # CHAMPS - NOTES
    # =========================================================================
    
    notes = fields.Text(
        string="Notes",
        help="Notes ou justification du paiement"
    )

    # =========================================================================
    # MÉTHODES COMPUTE
    # =========================================================================
    
    @api.depends('formule_id')
    def _compute_montant_taxes(self):
        for wizard in self:
            if wizard.formule_id:
                # Calculer le montant total des taxes depuis la formule
                wizard.montant_taxes = wizard.formule_id.total_taxes_a_payer or 0
                if not wizard.amount:
                    wizard.amount = wizard.montant_taxes
            else:
                wizard.montant_taxes = 0
    
    @api.depends('formule_id')
    def _compute_taxes_detail(self):
        for wizard in self:
            if wizard.formule_id and wizard.formule_id.taxe_ids:
                lines = ["<table class='table table-sm'>"]
                lines.append("<thead><tr><th>Taxe</th><th class='text-end'>Montant</th></tr></thead>")
                lines.append("<tbody>")
                for taxe in wizard.formule_id.taxe_ids.filtered(lambda t: not t.is_paid):
                    lines.append(f"<tr><td>{taxe.type_id.name}</td><td class='text-end'>{taxe.montant:,.0f} FCFA</td></tr>")
                lines.append("</tbody></table>")
                wizard.taxes_detail = ''.join(lines)
            else:
                wizard.taxes_detail = "<p><em>Aucune taxe à payer</em></p>"
    
    # =========================================================================
    # MÉTHODES ONCHANGE
    # =========================================================================
    
    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        self.bank_account_id = False
        if self.bank_id:
            company = self.env.company
            default_account = self.env['res.partner.bank'].search([
                ('bank_id', '=', self.bank_id.id),
                ('partner_id', '=', company.partner_id.id),
            ], limit=1)
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
    
    @api.constrains('check_number')
    def _check_check_number(self):
        for wizard in self:
            if not wizard.check_number or not wizard.check_number.strip():
                raise ValidationError(_("Le numéro de chèque est obligatoire."))

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_confirm_payment(self):
        """Créer la demande de paiement et confirmer le paiement des taxes"""
        self.ensure_one()
        
        # Créer la demande de paiement
        payment_request = self._create_payment_request()
        
        # Mettre à jour l'OT
        self.transit_order_id.write({
            'taxes_paid': True,
            'taxes_check_number': self.check_number,
            'taxes_payment_date': self.check_date,
            'taxes_payment_request_id': payment_request.id,
            'state': 'taxes_paid',
        })
        
        # Message dans le chatter
        self.transit_order_id.message_post(
            body=_(
                "<strong>Taxes payées</strong><br/>"
                "Montant: %s FCFA<br/>"
                "N° Chèque: %s<br/>"
                "Banque: %s<br/>"
                "Bénéficiaire: %s"
            ) % (
                f"{self.amount:,.0f}",
                self.check_number,
                self.bank_id.name,
                self.beneficiary_name
            ),
            subject=_("Taxes payées"),
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
        """Créer une demande de paiement via payment_request_validation"""
        subject = _("Taxes OT %s - Formule %s") % (
            self.transit_order_id.name,
            self.formule_id.name
        )
        
        justification = _(
            "<p><strong>Paiement des taxes et redevances</strong></p>"
            "<ul>"
            "<li>OT: %s</li>"
            "<li>Formule: %s</li>"
            "<li>Montant: %s FCFA</li>"
            "</ul>"
        ) % (
            self.transit_order_id.name,
            self.formule_id.name,
            f"{self.amount:,.0f}"
        )
        
        if self.notes:
            justification += f"<p><strong>Notes:</strong> {self.notes}</p>"
        
        payment_request = self.env['payment.request'].create({
            'subject': subject,
            'bank_id': self.bank_id.id,
            'bank_account_id': self.bank_account_id.id if self.bank_account_id else False,
            'expected_payment_date': self.check_date,
            'justification': justification,
            'urgency_level': 'normal',
        })
        
        # Créer le chèque
        self._create_check(payment_request)
        
        return payment_request
    
    def _create_check(self, payment_request):
        """Créer le chèque dans la demande de paiement"""
        partner = self.beneficiary_id
        if not partner:
            partner = self.env['res.partner'].search([
                ('name', '=ilike', self.beneficiary_name)
            ], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': self.beneficiary_name,
                    'is_company': True,
                })
        
        check_vals = {
            'payment_request_id': payment_request.id,
            'beneficiary': self.beneficiary_name,
            'partner_id': partner.id,
            'amount': self.amount,
            'check_date': self.check_date,
            'check_number': self.check_number,
            'number_generation_method': 'manual',
            'memo': _("Taxes OT %s") % self.transit_order_id.name,
        }
        
        return self.env['payment.request.check'].create(check_vals)


class PottingOtDusPaymentWizard(models.TransientModel):
    """Wizard de paiement du DUS (2ème partie - après vente)"""
    _name = 'potting.ot.dus.payment.wizard'
    _description = 'Paiement DUS OT (2ème partie)'

    # =========================================================================
    # CHAMPS - OT ET FORMULE
    # =========================================================================
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        readonly=True
    )
    
    ot_name = fields.Char(
        string="N° OT",
        related='transit_order_id.name',
        readonly=True
    )
    
    date_sold = fields.Date(
        string="Date de vente",
        related='transit_order_id.date_sold',
        readonly=True
    )
    
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
    
    # =========================================================================
    # CHAMPS - MONTANTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='formule_id.currency_id',
        readonly=True
    )
    
    montant_dus = fields.Monetary(
        string="Montant DUS calculé",
        compute='_compute_montant_dus',
        currency_field='currency_id',
        readonly=True,
        help="Montant du Droit Unique de Sortie (14,6% du montant)"
    )
    
    amount = fields.Monetary(
        string="Montant à payer",
        currency_field='currency_id',
        required=True,
        help="Montant du chèque à émettre"
    )
    
    # =========================================================================
    # CHAMPS - CHÈQUE
    # =========================================================================
    
    check_number = fields.Char(
        string="Numéro de chèque",
        required=True,
        help="Numéro du chèque (saisie manuelle obligatoire)"
    )
    
    check_date = fields.Date(
        string="Date du chèque",
        default=fields.Date.context_today,
        required=True
    )
    
    # =========================================================================
    # CHAMPS - BANQUE
    # =========================================================================
    
    bank_id = fields.Many2one(
        'res.bank',
        string="Banque émettrice",
        required=True,
        help="Banque de la société pour l'émission du chèque"
    )
    
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string="Compte émetteur",
        domain="[('bank_id', '=', bank_id)]",
        help="Compte bancaire de la société"
    )
    
    # =========================================================================
    # CHAMPS - BÉNÉFICIAIRE
    # =========================================================================
    
    beneficiary_name = fields.Char(
        string="Bénéficiaire",
        required=True,
        default="Conseil Café-Cacao",
        help="Nom du bénéficiaire sur le chèque"
    )
    
    beneficiary_id = fields.Many2one(
        'res.partner',
        string="Partenaire bénéficiaire",
        help="Partenaire associé (optionnel)"
    )
    
    # =========================================================================
    # CHAMPS - NOTES
    # =========================================================================
    
    notes = fields.Text(
        string="Notes",
        help="Notes ou justification du paiement"
    )

    # =========================================================================
    # MÉTHODES COMPUTE
    # =========================================================================
    
    @api.depends('formule_id', 'transit_order_id')
    def _compute_montant_dus(self):
        """Calculer le montant du DUS (Droit Unique de Sortie = 14,6%)"""
        for wizard in self:
            if wizard.formule_id:
                # DUS = 14,6% du montant brut de la formule
                taux_dus = 14.6
                montant_base = wizard.formule_id.montant_brut or 0
                wizard.montant_dus = montant_base * (taux_dus / 100)
                if not wizard.amount:
                    wizard.amount = wizard.montant_dus
            else:
                wizard.montant_dus = 0
    
    # =========================================================================
    # MÉTHODES ONCHANGE
    # =========================================================================
    
    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        self.bank_account_id = False
        if self.bank_id:
            company = self.env.company
            default_account = self.env['res.partner.bank'].search([
                ('bank_id', '=', self.bank_id.id),
                ('partner_id', '=', company.partner_id.id),
            ], limit=1)
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
    
    @api.constrains('check_number')
    def _check_check_number(self):
        for wizard in self:
            if not wizard.check_number or not wizard.check_number.strip():
                raise ValidationError(_("Le numéro de chèque est obligatoire."))

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_confirm_payment(self):
        """Créer la demande de paiement et confirmer le paiement du DUS"""
        self.ensure_one()
        
        # Vérifier que l'OT est bien vendu
        if self.transit_order_id.state != 'sold':
            raise UserError(_("L'OT doit être vendu pour pouvoir payer le DUS."))
        
        # Créer la demande de paiement
        payment_request = self._create_payment_request()
        
        # Mettre à jour l'OT
        self.transit_order_id.write({
            'dus_paid': True,
            'dus_check_number': self.check_number,
            'dus_payment_date': self.check_date,
            'dus_payment_request_id': payment_request.id,
            'state': 'dus_paid',
        })
        
        # Message dans le chatter
        self.transit_order_id.message_post(
            body=_(
                "<strong>DUS payé</strong><br/>"
                "Montant: %s FCFA<br/>"
                "N° Chèque: %s<br/>"
                "Banque: %s<br/>"
                "Bénéficiaire: %s"
            ) % (
                f"{self.amount:,.0f}",
                self.check_number,
                self.bank_id.name,
                self.beneficiary_name
            ),
            subject=_("DUS payé"),
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
        """Créer une demande de paiement via payment_request_validation"""
        subject = _("DUS OT %s - Formule %s") % (
            self.transit_order_id.name,
            self.formule_id.name
        )
        
        justification = _(
            "<p><strong>Paiement du Droit Unique de Sortie (DUS)</strong></p>"
            "<ul>"
            "<li>OT: %s</li>"
            "<li>Formule: %s</li>"
            "<li>Date de vente: %s</li>"
            "<li>Montant DUS: %s FCFA</li>"
            "</ul>"
        ) % (
            self.transit_order_id.name,
            self.formule_id.name,
            self.transit_order_id.date_sold,
            f"{self.amount:,.0f}"
        )
        
        if self.notes:
            justification += f"<p><strong>Notes:</strong> {self.notes}</p>"
        
        payment_request = self.env['payment.request'].create({
            'subject': subject,
            'bank_id': self.bank_id.id,
            'bank_account_id': self.bank_account_id.id if self.bank_account_id else False,
            'expected_payment_date': self.check_date,
            'justification': justification,
            'urgency_level': 'normal',
        })
        
        # Créer le chèque
        self._create_check(payment_request)
        
        return payment_request
    
    def _create_check(self, payment_request):
        """Créer le chèque dans la demande de paiement"""
        partner = self.beneficiary_id
        if not partner:
            partner = self.env['res.partner'].search([
                ('name', '=ilike', self.beneficiary_name)
            ], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': self.beneficiary_name,
                    'is_company': True,
                })
        
        check_vals = {
            'payment_request_id': payment_request.id,
            'beneficiary': self.beneficiary_name,
            'partner_id': partner.id,
            'amount': self.amount,
            'check_date': self.check_date,
            'check_number': self.check_number,
            'number_generation_method': 'manual',
            'memo': _("DUS OT %s") % self.transit_order_id.name,
        }
        
        return self.env['payment.request.check'].create(check_vals)
