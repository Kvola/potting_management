# -*- coding: utf-8 -*-
"""
Modèle pour la gestion des factures transitaires.

Les factures transitaires doivent être validées par le comptable
avant que le paiement puisse être effectué.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingForwardingAgentInvoice(models.Model):
    """Facture Transitaire
    
    Représente une facture émise par un transitaire pour ses services.
    La facture doit être validée par le comptable avant paiement.
    """
    _name = 'potting.forwarding.agent.invoice'
    _description = 'Facture Transitaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'invoice_date desc, name desc'
    _check_company_auto = True

    _sql_constraints = [
        ('invoice_number_transitaire_uniq', 
         'UNIQUE(invoice_number, forwarding_agent_id, company_id)',
         'Le numéro de facture doit être unique par transitaire !'),
    ]

    # =========================================================================
    # CHAMPS - IDENTIFICATION
    # =========================================================================
    
    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
        index=True,
        help="Référence interne de la facture"
    )
    
    invoice_number = fields.Char(
        string="N° Facture",
        required=True,
        tracking=True,
        index=True,
        help="Numéro de la facture du transitaire (doit être unique par transitaire)"
    )
    
    invoice_date = fields.Date(
        string="Date Facture",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Date d'émission de la facture"
    )
    
    received_date = fields.Date(
        string="Date Réception",
        default=fields.Date.context_today,
        tracking=True,
        help="Date de réception de la facture"
    )
    
    # =========================================================================
    # CHAMPS - RELATIONS
    # =========================================================================
    
    forwarding_agent_id = fields.Many2one(
        'potting.forwarding.agent',
        string="Transitaire",
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        help="Transitaire émetteur de la facture"
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string="Partenaire",
        related='forwarding_agent_id.partner_id',
        store=True,
        readonly=True
    )
    
    transit_order_ids = fields.Many2many(
        'potting.transit.order',
        'potting_fwd_invoice_ot_rel',
        'invoice_id',
        'transit_order_id',
        string="Ordres de Transit",
        help="OT concernés par cette facture"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    # =========================================================================
    # CHAMPS - MONTANTS
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='forwarding_agent_id.currency_id',
        store=True,
        readonly=True
    )
    
    amount_untaxed = fields.Monetary(
        string="Montant HT",
        currency_field='currency_id',
        required=True,
        tracking=True,
        help="Montant hors taxes"
    )
    
    amount_tax = fields.Monetary(
        string="Montant TVA",
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help="Montant de la TVA"
    )
    
    amount_total = fields.Monetary(
        string="Montant Total",
        currency_field='currency_id',
        compute='_compute_amount_total',
        store=True,
        tracking=True,
        help="Montant total TTC"
    )
    
    # =========================================================================
    # CHAMPS - PIÈCE JOINTE
    # =========================================================================
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'potting_fwd_invoice_attachment_rel',
        'invoice_id',
        'attachment_id',
        string="Pièces jointes",
        help="Scan de la facture et documents justificatifs"
    )
    
    invoice_file = fields.Binary(
        string="Fichier Facture",
        attachment=True,
        help="Fichier principal de la facture (PDF ou image)"
    )
    
    invoice_filename = fields.Char(
        string="Nom fichier"
    )
    
    # =========================================================================
    # CHAMPS - ÉTAT ET VALIDATION
    # =========================================================================
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumise'),
        ('validated', 'Validée'),
        ('paid', 'Payée'),
        ('cancelled', 'Annulée'),
    ], string="État",
       default='draft',
       tracking=True,
       index=True,
       copy=False,
       help="État de la facture transitaire"
    )
    
    submitted_by_id = fields.Many2one(
        'res.users',
        string="Soumise par",
        readonly=True,
        copy=False,
        help="Utilisateur shipping ayant soumis la facture"
    )
    
    submitted_date = fields.Datetime(
        string="Date Soumission",
        readonly=True,
        copy=False
    )
    
    validated_by_id = fields.Many2one(
        'res.users',
        string="Validée par",
        readonly=True,
        copy=False,
        help="Comptable ayant validé la facture"
    )
    
    validation_date = fields.Datetime(
        string="Date Validation",
        readonly=True,
        copy=False
    )
    
    rejection_reason = fields.Text(
        string="Motif de rejet",
        copy=False
    )
    
    # =========================================================================
    # CHAMPS - PAIEMENT
    # =========================================================================
    
    payment_id = fields.Many2one(
        'potting.forwarding.agent.payment',
        string="Paiement associé",
        readonly=True,
        copy=False,
        help="Paiement effectué pour cette facture"
    )
    
    payment_request_id = fields.Many2one(
        'payment.request',
        string="Demande de paiement",
        related='payment_id.payment_request_id',
        store=True,
        readonly=True
    )
    
    is_paid = fields.Boolean(
        string="Payée",
        compute='_compute_is_paid',
        store=True
    )
    
    # =========================================================================
    # CHAMPS - NOTES
    # =========================================================================
    
    description = fields.Text(
        string="Description",
        help="Description des services facturés"
    )
    
    notes = fields.Text(
        string="Notes internes"
    )

    # =========================================================================
    # MÉTHODES COMPUTE
    # =========================================================================
    
    @api.depends('amount_untaxed', 'amount_tax')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = record.amount_untaxed + record.amount_tax
    
    @api.depends('state', 'payment_id', 'payment_id.state')
    def _compute_is_paid(self):
        for record in self:
            record.is_paid = (
                record.state == 'paid' or 
                (record.payment_id and record.payment_id.state == 'confirmed')
            )

    # =========================================================================
    # MÉTHODES CRUD
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'potting.forwarding.agent.invoice'
                ) or _('Nouveau')
        return super().create(vals_list)

    # =========================================================================
    # ACTIONS - WORKFLOW
    # =========================================================================
    
    def action_submit(self):
        """Soumettre la facture pour validation par le comptable"""
        self.ensure_one()
        
        if not self.invoice_file and not self.attachment_ids:
            raise UserError(_(
                "Vous devez joindre la facture (fichier ou pièce jointe) "
                "avant de la soumettre."
            ))
        
        if self.amount_total <= 0:
            raise UserError(_("Le montant total doit être supérieur à 0."))
        
        self.write({
            'state': 'submitted',
            'submitted_by_id': self.env.user.id,
            'submitted_date': fields.Datetime.now(),
        })
        
        # Créer une activité pour le comptable
        self._create_validation_activity()
        
        self.message_post(
            body=_("Facture soumise pour validation par %s") % self.env.user.name,
            subject=_("Facture soumise"),
            subtype_xmlid='mail.mt_comment'
        )
        
        return True
    
    def action_validate(self):
        """Valider la facture (action comptable)"""
        self.ensure_one()
        
        # Vérifier que l'utilisateur est comptable ou manager
        if not self.env.user.has_group('potting_management.group_potting_accountant') and \
           not self.env.user.has_group('potting_management.group_potting_manager'):
            raise UserError(_(
                "Seul un comptable ou un responsable peut valider les factures."
            ))
        
        self.write({
            'state': 'validated',
            'validated_by_id': self.env.user.id,
            'validation_date': fields.Datetime.now(),
            'rejection_reason': False,
        })
        
        # Marquer l'activité comme terminée
        self._done_validation_activity()
        
        self.message_post(
            body=_("Facture validée par %s - Prête pour paiement") % self.env.user.name,
            subject=_("Facture validée"),
            subtype_xmlid='mail.mt_comment'
        )
        
        return True
    
    def action_reject(self):
        """Rejeter la facture (action comptable)"""
        self.ensure_one()
        
        # Vérifier que l'utilisateur est comptable ou manager
        if not self.env.user.has_group('potting_management.group_potting_accountant') and \
           not self.env.user.has_group('potting_management.group_potting_manager'):
            raise UserError(_(
                "Seul un comptable ou un responsable peut rejeter les factures."
            ))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rejeter la facture'),
            'res_model': 'potting.forwarding.invoice.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_invoice_id': self.id},
        }
    
    def action_set_to_draft(self):
        """Remettre en brouillon"""
        self.ensure_one()
        
        if self.state == 'paid':
            raise UserError(_(
                "Impossible de remettre en brouillon une facture payée."
            ))
        
        self.write({
            'state': 'draft',
            'submitted_by_id': False,
            'submitted_date': False,
            'validated_by_id': False,
            'validation_date': False,
            'rejection_reason': False,
        })
        
        return True
    
    def action_cancel(self):
        """Annuler la facture"""
        self.ensure_one()
        
        if self.state == 'paid':
            raise UserError(_(
                "Impossible d'annuler une facture payée."
            ))
        
        self.write({'state': 'cancelled'})
        
        return True
    
    def action_view_invoice_file(self):
        """Afficher/télécharger le fichier facture"""
        self.ensure_one()
        
        if self.invoice_file:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s/%s/invoice_file/%s?download=true' % (
                    self._name, self.id, self.invoice_filename or 'facture'
                ),
                'target': 'new',
            }
        elif self.attachment_ids:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=true' % self.attachment_ids[0].id,
                'target': 'new',
            }
        else:
            raise UserError(_("Aucun fichier de facture attaché."))
    
    def action_create_payment(self):
        """Ouvrir le wizard de création de paiement"""
        self.ensure_one()
        
        if self.state != 'validated':
            raise UserError(_(
                "La facture doit être validée avant de pouvoir créer un paiement."
            ))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Créer un paiement'),
            'res_model': 'potting.create.forwarding.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_forwarding_agent_id': self.forwarding_agent_id.id,
                'default_invoice_id': self.id,
                'default_amount': self.amount_total,
                'default_transit_order_ids': [(6, 0, self.transit_order_ids.ids)],
            },
        }

    # =========================================================================
    # MÉTHODES HELPER
    # =========================================================================
    
    def _create_validation_activity(self):
        """Créer une activité de validation pour les comptables"""
        self.ensure_one()
        
        # Trouver les utilisateurs comptables
        accountant_group = self.env.ref('potting_management.group_potting_accountant', raise_if_not_found=False)
        if accountant_group:
            accountants = accountant_group.users
            if accountants:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_("Valider facture transitaire %s") % self.invoice_number,
                    note=_(
                        "Facture transitaire à valider:\n"
                        "- Transitaire: %s\n"
                        "- N° Facture: %s\n"
                        "- Montant: %s %s"
                    ) % (
                        self.forwarding_agent_id.name,
                        self.invoice_number,
                        self.amount_total,
                        self.currency_id.symbol
                    ),
                    user_id=accountants[0].id,
                )
    
    def _done_validation_activity(self):
        """Marquer l'activité de validation comme terminée"""
        activities = self.activity_ids.filtered(
            lambda a: 'valider' in (a.summary or '').lower() or 
                      'facture' in (a.summary or '').lower()
        )
        activities.action_done()


class PottingForwardingInvoiceRejectWizard(models.TransientModel):
    """Wizard pour rejeter une facture transitaire avec motif"""
    _name = 'potting.forwarding.invoice.reject.wizard'
    _description = 'Rejeter Facture Transitaire'
    
    invoice_id = fields.Many2one(
        'potting.forwarding.agent.invoice',
        string="Facture",
        required=True,
        readonly=True
    )
    
    rejection_reason = fields.Text(
        string="Motif du rejet",
        required=True,
        help="Expliquez pourquoi la facture est rejetée"
    )
    
    def action_confirm_reject(self):
        """Confirmer le rejet"""
        self.ensure_one()
        
        self.invoice_id.write({
            'state': 'draft',
            'rejection_reason': self.rejection_reason,
            'validated_by_id': False,
            'validation_date': False,
        })
        
        # Marquer l'activité comme terminée
        self.invoice_id._done_validation_activity()
        
        self.invoice_id.message_post(
            body=_("Facture rejetée par %s\n\nMotif: %s") % (
                self.env.user.name, 
                self.rejection_reason
            ),
            subject=_("Facture rejetée"),
            subtype_xmlid='mail.mt_comment'
        )
        
        return {'type': 'ir.actions.act_window_close'}
