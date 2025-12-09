# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PottingSendReportWizard(models.TransientModel):
    _name = 'potting.send.report.wizard'
    _description = "Assistant d'envoi de rapport"

    report_type = fields.Selection([
        ('daily', 'Rapport journalier'),
        ('ot', 'Rapport par OT'),
        ('summary', 'Rapport de synthèse'),
    ], string="Type de rapport", required=True, default='daily')
    
    date_from = fields.Date(
        string="Date début",
        default=fields.Date.context_today
    )
    
    date_to = fields.Date(
        string="Date fin",
        default=fields.Date.context_today
    )
    
    transit_order_ids = fields.Many2many(
        'potting.transit.order',
        string="Ordres de Transit",
        domain="[('state', 'not in', ('draft', 'cancelled'))]"
    )
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        domain="[('state', 'not in', ('draft', 'cancelled'))]"
    )
    
    recipient_id = fields.Many2one(
        'res.partner',
        string="Destinataire principal",
        required=True,
        help="PDG ou responsable principal"
    )
    
    cc_partner_ids = fields.Many2many(
        'res.partner',
        'potting_send_report_wizard_cc_partner_rel',
        'wizard_id',
        'partner_id',
        string="En copie (CC)",
        default=lambda self: self._get_default_cc_partners()
    )
    
    include_pdf = fields.Boolean(
        string="Joindre PDF",
        default=True
    )
    
    note = fields.Text(
        string="Message personnalisé"
    )

    @api.model
    def _get_default_cc_partners(self):
        """Get default CC partners from settings"""
        ICP = self.env['ir.config_parameter'].sudo()
        cc_partner_ids = ICP.get_param('potting_management.default_cc_partner_ids', '[]')
        try:
            cc_partner_ids = eval(cc_partner_ids)
            return [(6, 0, cc_partner_ids)]
        except:
            return []

    @api.onchange('report_type')
    def _onchange_report_type(self):
        if self.report_type == 'daily':
            self.transit_order_ids = False
            self.customer_order_id = False
        elif self.report_type == 'ot':
            self.date_from = False
            self.date_to = False
            self.customer_order_id = False
        elif self.report_type == 'summary':
            self.date_from = False
            self.date_to = False
            self.transit_order_ids = False

    def action_send_report(self):
        self.ensure_one()
        
        if not self.recipient_id.email:
            raise UserError(_("Le destinataire principal doit avoir une adresse email."))
        
        # Build context for email
        ctx = {
            'recipient_email': self.recipient_id.email,
            'cc_emails': ','.join(self.cc_partner_ids.filtered('email').mapped('email')),
        }
        
        if self.report_type == 'daily':
            # Send daily report for all OT with activity in the date range
            domain = [
                ('state', 'not in', ('draft', 'cancelled')),
            ]
            if self.date_from:
                domain.append(('date_created', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_created', '<=', self.date_to))
            
            transit_orders = self.env['potting.transit.order'].search(domain)
            
            if not transit_orders:
                raise UserError(_("Aucun OT trouvé pour la période sélectionnée."))
            
            for ot in transit_orders:
                template = self.env.ref('potting_management.mail_template_potting_daily_report')
                template.with_context(ctx).send_mail(ot.id, force_send=True)
                
        elif self.report_type == 'ot':
            if not self.transit_order_ids:
                raise UserError(_("Veuillez sélectionner au moins un OT."))
            
            for ot in self.transit_order_ids:
                template = self.env.ref('potting_management.mail_template_potting_daily_report')
                template.with_context(ctx).send_mail(ot.id, force_send=True)
                
        elif self.report_type == 'summary':
            if not self.customer_order_id:
                raise UserError(_("Veuillez sélectionner une commande client."))
            
            template = self.env.ref('potting_management.mail_template_potting_summary_report')
            template.with_context(ctx).send_mail(self.customer_order_id.id, force_send=True)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rapport envoyé'),
                'message': _('Le rapport a été envoyé avec succès à %s.') % self.recipient_id.name,
                'type': 'success',
                'sticky': False,
            }
        }
