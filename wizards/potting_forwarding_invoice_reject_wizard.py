# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

##############################################################################
#  Wizard de Rejet de Facture Transitaire
#  Permet au comptable de rejeter une facture avec motif obligatoire
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PottingForwardingInvoiceRejectWizard(models.TransientModel):
    """Wizard pour rejeter une facture transitaire avec motif."""
    
    _name = 'potting.forwarding.invoice.reject.wizard'
    _description = 'Assistant de Rejet de Facture Transitaire'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    invoice_id = fields.Many2one(
        'potting.forwarding.agent.invoice',
        string='Facture',
        required=True,
        readonly=True,
    )
    
    invoice_number = fields.Char(
        related='invoice_id.invoice_number',
        string='N° Facture',
        readonly=True,
    )
    
    forwarding_agent_id = fields.Many2one(
        related='invoice_id.forwarding_agent_id',
        string='Transitaire',
        readonly=True,
    )
    
    amount_total = fields.Monetary(
        related='invoice_id.amount_total',
        string='Montant Total',
        readonly=True,
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string='Devise',
        readonly=True,
    )
    
    reject_reason = fields.Text(
        string='Motif du Rejet',
        required=True,
        help="Expliquez la raison du rejet de cette facture.",
    )

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    
    @api.model
    def default_get(self, fields_list):
        """Récupère la facture depuis le contexte."""
        res = super().default_get(fields_list)
        
        if self._context.get('active_model') == 'potting.forwarding.agent.invoice':
            invoice_id = self._context.get('active_id')
            if invoice_id:
                invoice = self.env['potting.forwarding.agent.invoice'].browse(invoice_id)
                if invoice.exists():
                    res['invoice_id'] = invoice.id
        
        return res

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    
    def action_reject(self):
        """Rejette la facture avec le motif indiqué."""
        self.ensure_one()
        
        if not self.reject_reason:
            raise UserError(_("Veuillez saisir un motif de rejet."))
        
        if not self.invoice_id:
            raise UserError(_("Aucune facture sélectionnée."))
        
        if self.invoice_id.state != 'submitted':
            raise UserError(_("Seules les factures soumises peuvent être rejetées."))
        
        # Rejeter la facture
        self.invoice_id.action_reject(self.reject_reason)
        
        return {'type': 'ir.actions.act_window_close'}
