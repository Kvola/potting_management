# -*- coding: utf-8 -*-
"""
Extension du modèle payment.request pour intégration avec potting_management.

Ajoute des hooks pour mettre à jour automatiquement le statut de paiement
des formules et des transitaires quand le payment.request est validé/signé.
"""

from odoo import api, fields, models, _
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class PaymentRequestPotting(models.Model):
    """Extension de payment.request pour potting_management"""
    _inherit = 'payment.request'

    # =========================================================================
    # CHAMPS - LIENS POTTING
    # =========================================================================
    
    potting_formule_ids = fields.One2many(
        'potting.formule',
        compute='_compute_potting_links',
        string="Formules liées"
    )
    
    potting_formule_count = fields.Integer(
        string="Nb Formules",
        compute='_compute_potting_links'
    )
    
    potting_fwd_payment_ids = fields.One2many(
        'potting.forwarding.agent.payment',
        'payment_request_id',
        string="Paiements transitaires"
    )
    
    potting_fwd_payment_count = fields.Integer(
        string="Nb Paiements transitaires",
        compute='_compute_potting_links'
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    def _compute_potting_links(self):
        """Calculer les liens avec les objets potting"""
        for record in self:
            # Formules liées via paiement producteurs
            formules = self.env['potting.formule'].search([
                ('payment_request_avant_vente_id', '=', record.id)
            ])
            record.potting_formule_ids = formules
            record.potting_formule_count = len(formules)
            
            # Paiements transitaires
            record.potting_fwd_payment_count = len(record.potting_fwd_payment_ids)

    # =========================================================================
    # OVERRIDE WRITE - DÉTECTER CHANGEMENT D'ÉTAT VERS SIGNED
    # =========================================================================
    
    def write(self, vals):
        """Surcharge de write pour détecter le passage à l'état 'signed'"""
        # Sauvegarder les anciens états pour détecter le changement
        old_states = {record.id: record.state for record in self}
        
        # Appeler le write parent
        result = super().write(vals)
        
        # Vérifier si l'état a changé vers 'signed'
        if 'state' in vals and vals['state'] == 'signed':
            for record in self:
                if old_states.get(record.id) != 'signed':
                    # L'état vient de passer à 'signed'
                    _logger.info(
                        f"🖊️ Payment.request {record.reference} signé - "
                        f"Mise à jour automatique des formules liées"
                    )
                    record._on_signature_complete_hook()
        
        return result

    # =========================================================================
    # HOOK SIGNATURE COMPLÈTE
    # =========================================================================
    
    def _on_signature_complete_hook(self):
        """Hook appelé après signature complète - Met à jour potting"""
        # Mettre à jour les formules liées
        self._update_potting_formules_payment_status()
        
        # Mettre à jour les paiements transitaires
        self._update_potting_forwarding_payments_status()

    # =========================================================================
    # OVERRIDE VALIDATION HOOKS
    # =========================================================================
    
    def _on_validation_complete_hook(self):
        """Hook appelé après validation complète - Met à jour potting"""
        # Appeler le parent (peut retourner None)
        try:
            super()._on_validation_complete_hook()
        except Exception as e:
            _logger.warning(f"Erreur dans parent _on_validation_complete_hook: {e}")
        
        _logger.info(
            f"🔔 _on_validation_complete_hook appelé pour payment.request {self.mapped('reference')}"
        )
        
        # Mettre à jour les formules liées
        self._update_potting_formules_payment_status()
        
        # Mettre à jour les paiements transitaires
        self._update_potting_forwarding_payments_status()
    
    def _update_potting_formules_payment_status(self):
        """Mettre à jour le statut de paiement des formules liées"""
        for record in self:
            _logger.info(
                f"🔍 Recherche formules liées à payment.request {record.reference} (id={record.id})"
            )
            
            # Formules avec paiement avant-vente lié à cette demande
            formules_avant_vente = self.env['potting.formule'].search([
                ('payment_request_avant_vente_id', '=', record.id),
                ('avant_vente_paye', '=', False)
            ])
            
            _logger.info(
                f"   📋 Formules avant-vente trouvées: {formules_avant_vente.mapped('name')}"
            )
            
            for formule in formules_avant_vente:
                formule.write({
                    'avant_vente_paye': True,
                    'date_paiement_avant_vente': fields.Date.today(),
                })
                formule._update_payment_state()
                
                _logger.info(
                    f"✅ Formule {formule.name} - Paiement avant-vente marqué comme payé "
                    f"(payment.request {record.reference})"
                )
                
                # ✅ Mettre à jour l'OT lié : droits d'exportation encaissés
                if formule.transit_order_id and not formule.transit_order_id.export_duty_collected:
                    formule.transit_order_id.write({
                        'export_duty_collected': True,
                        'export_duty_collection_date': fields.Date.today(),
                    })
                    formule.transit_order_id.message_post(
                        body=_(
                            "✅ <b>Droits d'exportation encaissés</b><br/>"
                            "Via paiement avant-vente de la Formule %s<br/>"
                            "Demande de paiement: %s"
                        ) % (formule.name, record.reference),
                        subject=_("Droits d'exportation encaissés"),
                        subtype_xmlid='mail.mt_comment'
                    )
                    _logger.info(
                        f"✅ OT {formule.transit_order_id.name} - Droits d'exportation encaissés "
                        f"via Formule {formule.name}"
                    )
                
                # Message dans le chatter
                formule.message_post(
                    body=_(
                        "💰 <b>Paiement producteurs validé</b><br/>"
                        "Demande de paiement: %s<br/>"
                        "Montant: %s %s<br/>"
                        "Date: %s"
                    ) % (
                        record.reference,
                        formule.montant_avant_vente,
                        formule.currency_id.symbol,
                        fields.Date.today()
                    ),
                    subject=_("Paiement producteurs validé"),
                    subtype_xmlid='mail.mt_comment'
                )
    
    def _update_potting_forwarding_payments_status(self):
        """Mettre à jour le statut des paiements transitaires liés"""
        for record in self:
            # Paiements transitaires liés à cette demande
            fwd_payments = record.potting_fwd_payment_ids.filtered(
                lambda p: p.state in ('draft', 'pending')
            )
            
            for payment in fwd_payments:
                payment.write({
                    'state': 'confirmed',
                    'payment_date': fields.Date.today(),
                })
                
                _logger.info(
                    f"✅ Paiement transitaire {payment.name} confirmé "
                    f"(payment.request {record.reference})"
                )
                
                # Mettre à jour la facture transitaire si liée
                invoice = self.env['potting.forwarding.agent.invoice'].search([
                    ('payment_id', '=', payment.id)
                ], limit=1)
                
                if not invoice:
                    # Chercher par payment_request_id
                    invoice = self.env['potting.forwarding.agent.invoice'].search([
                        ('payment_request_id', '=', record.id),
                        ('state', '=', 'validated')
                    ], limit=1)
                
                if invoice:
                    invoice.write({
                        'state': 'paid',
                        'payment_id': payment.id,
                    })
                    
                    invoice.message_post(
                        body=_(
                            "💰 <b>Facture payée</b><br/>"
                            "Demande de paiement: %s<br/>"
                            "Montant: %s %s"
                        ) % (
                            record.reference,
                            payment.amount,
                            payment.currency_id.symbol
                        ),
                        subject=_("Facture payée"),
                        subtype_xmlid='mail.mt_comment'
                    )
                
                # Message sur le transitaire
                if payment.forwarding_agent_id:
                    payment.forwarding_agent_id.message_post(
                        body=_(
                            "💰 <b>Paiement confirmé</b><br/>"
                            "Type: %s<br/>"
                            "Montant: %s %s<br/>"
                            "Demande: %s"
                        ) % (
                            dict(payment._fields['payment_type'].selection).get(payment.payment_type),
                            payment.amount,
                            payment.currency_id.symbol,
                            record.reference
                        ),
                        subject=_("Paiement transitaire confirmé"),
                        subtype_xmlid='mail.mt_comment'
                    )
