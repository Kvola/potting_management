# -*- coding: utf-8 -*-
"""
Service d'alertes critiques pour le Manager

Ce module gère les alertes critiques du processus d'exportation :
- OT avec formule liée mais taxes non payées
- OT vendus mais DUS non payé
- CV proches de l'expiration
- Contrats avec tonnage non couvert
- Formules non payées

Les alertes sont envoyées par email et affichées sur le dashboard.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class PottingAlertService(models.AbstractModel):
    """Service d'alertes critiques pour le module exportations"""
    _name = 'potting.alert.service'
    _description = 'Service Alertes Critiques Exportations'

    # =========================================================================
    # MÉTHODES PUBLIQUES - RÉCUPÉRATION DES ALERTES
    # =========================================================================
    
    @api.model
    def get_all_alerts(self):
        """Récupère toutes les alertes critiques pour le dashboard"""
        return {
            'critical': self._get_critical_alerts(),
            'warning': self._get_warning_alerts(),
            'info': self._get_info_alerts(),
            'summary': self._get_alert_summary(),
        }
    
    @api.model
    def get_alert_counts(self):
        """Récupère uniquement les compteurs d'alertes (plus rapide)"""
        return {
            'ot_taxes_pending': self._count_ot_taxes_pending(),
            'ot_dus_pending': self._count_ot_dus_pending(),
            'cv_expiring_7_days': self._count_cv_expiring(7),
            'cv_expiring_30_days': self._count_cv_expiring(30),
            'formules_unpaid': self._count_formules_unpaid(),
            'contracts_uncovered': self._count_contracts_uncovered(),
            'ot_pending_sale': self._count_ot_pending_sale(),
        }

    # =========================================================================
    # ALERTES CRITIQUES (Rouge)
    # =========================================================================
    
    def _get_critical_alerts(self):
        """Alertes critiques nécessitant une action immédiate"""
        alerts = []
        
        # OT avec formule liée mais taxes non payées depuis plus de 7 jours
        ots_taxes = self.env['potting.transit.order'].search([
            ('state', '=', 'formule_linked'),
            ('taxes_paid', '=', False),
            ('create_date', '<', fields.Datetime.now() - timedelta(days=7))
        ])
        for ot in ots_taxes:
            alerts.append({
                'type': 'critical',
                'category': 'ot_taxes',
                'title': _("Taxes non payées - OT %s") % ot.name,
                'message': _("L'OT %s attend le paiement des taxes depuis plus de 7 jours. "
                           "Formule: %s") % (ot.name, ot.formule_id.name if ot.formule_id else '-'),
                'model': 'potting.transit.order',
                'res_id': ot.id,
                'action': 'open_taxes_payment_wizard',
                'date': ot.create_date,
            })
        
        # OT vendus mais DUS non payé depuis plus de 3 jours
        ots_dus = self.env['potting.transit.order'].search([
            ('state', '=', 'sold'),
            ('dus_paid', '=', False),
            ('date_sold', '<', date.today() - timedelta(days=3))
        ])
        for ot in ots_dus:
            alerts.append({
                'type': 'critical',
                'category': 'ot_dus',
                'title': _("DUS non payé - OT %s") % ot.name,
                'message': _("L'OT %s a été vendu le %s mais le DUS n'est pas encore payé.") % (
                    ot.name, ot.date_sold),
                'model': 'potting.transit.order',
                'res_id': ot.id,
                'action': 'open_dus_payment_wizard',
                'date': ot.date_sold,
            })
        
        # CV expirant dans les 7 prochains jours
        cv_expiring = self.env['potting.confirmation.vente'].search([
            ('state', '=', 'active'),
            ('date_end', '>=', date.today()),
            ('date_end', '<=', date.today() + timedelta(days=7)),
            ('tonnage_restant', '>', 0)
        ])
        for cv in cv_expiring:
            alerts.append({
                'type': 'critical',
                'category': 'cv_expiring',
                'title': _("CV expire dans %d jours - %s") % (cv.days_remaining, cv.name),
                'message': _("La CV %s expire le %s avec encore %.2f T de tonnage non utilisé.") % (
                    cv.name, cv.date_end, cv.tonnage_restant),
                'model': 'potting.confirmation.vente',
                'res_id': cv.id,
                'action': 'open_cv_transfer_wizard',
                'date': cv.date_end,
            })
        
        return alerts

    # =========================================================================
    # ALERTES D'AVERTISSEMENT (Orange)
    # =========================================================================
    
    def _get_warning_alerts(self):
        """Alertes d'avertissement nécessitant attention"""
        alerts = []
        
        # OT avec formule liée récemment (rappel paiement taxes)
        ots_taxes_recent = self.env['potting.transit.order'].search([
            ('state', '=', 'formule_linked'),
            ('taxes_paid', '=', False),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=7))
        ])
        for ot in ots_taxes_recent:
            alerts.append({
                'type': 'warning',
                'category': 'ot_taxes_reminder',
                'title': _("Rappel taxes - OT %s") % ot.name,
                'message': _("L'OT %s attend le paiement des taxes.") % ot.name,
                'model': 'potting.transit.order',
                'res_id': ot.id,
            })
        
        # CV expirant dans les 30 prochains jours
        cv_expiring_30 = self.env['potting.confirmation.vente'].search([
            ('state', '=', 'active'),
            ('date_end', '>', date.today() + timedelta(days=7)),
            ('date_end', '<=', date.today() + timedelta(days=30)),
            ('tonnage_restant', '>', 0)
        ])
        for cv in cv_expiring_30:
            alerts.append({
                'type': 'warning',
                'category': 'cv_expiring_soon',
                'title': _("CV expire bientôt - %s") % cv.name,
                'message': _("La CV %s expire le %s. Pensez à reporter le tonnage restant (%.2f T).") % (
                    cv.name, cv.date_end, cv.tonnage_restant),
                'model': 'potting.confirmation.vente',
                'res_id': cv.id,
            })
        
        # OT prêts pour validation
        ots_validation = self.env['potting.transit.order'].search([
            ('state', '=', 'ready_validation')
        ], limit=10)
        for ot in ots_validation:
            alerts.append({
                'type': 'warning',
                'category': 'ot_validation',
                'title': _("OT prêt pour validation - %s") % ot.name,
                'message': _("L'OT %s est prêt pour validation finale.") % ot.name,
                'model': 'potting.transit.order',
                'res_id': ot.id,
            })
        
        return alerts

    # =========================================================================
    # ALERTES INFORMATIVES (Bleu)
    # =========================================================================
    
    def _get_info_alerts(self):
        """Alertes informatives"""
        alerts = []
        
        # OT récemment créés
        ots_recent = self.env['potting.transit.order'].search([
            ('state', '=', 'draft'),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=1))
        ], limit=5)
        for ot in ots_recent:
            alerts.append({
                'type': 'info',
                'category': 'ot_new',
                'title': _("Nouvel OT - %s") % ot.name,
                'message': _("OT %s créé, en attente de liaison avec une formule.") % ot.name,
                'model': 'potting.transit.order',
                'res_id': ot.id,
            })
        
        # Formules récemment créées
        formules_recent = self.env['potting.formule'].search([
            ('state', '=', 'validated'),
            ('transit_order_id', '=', False),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=3))
        ], limit=5)
        for fo in formules_recent:
            alerts.append({
                'type': 'info',
                'category': 'formule_available',
                'title': _("Formule disponible - %s") % fo.name,
                'message': _("Formule %s disponible pour liaison avec un OT.") % fo.name,
                'model': 'potting.formule',
                'res_id': fo.id,
            })
        
        return alerts

    # =========================================================================
    # COMPTEURS
    # =========================================================================
    
    def _count_ot_taxes_pending(self):
        return self.env['potting.transit.order'].search_count([
            ('state', '=', 'formule_linked'),
            ('taxes_paid', '=', False)
        ])
    
    def _count_ot_dus_pending(self):
        return self.env['potting.transit.order'].search_count([
            ('state', '=', 'sold'),
            ('dus_paid', '=', False)
        ])
    
    def _count_ot_pending_sale(self):
        return self.env['potting.transit.order'].search_count([
            ('state', '=', 'taxes_paid'),
            ('date_sold', '=', False)
        ])
    
    def _count_cv_expiring(self, days):
        return self.env['potting.confirmation.vente'].search_count([
            ('state', '=', 'active'),
            ('date_end', '>=', date.today()),
            ('date_end', '<=', date.today() + timedelta(days=days)),
            ('tonnage_restant', '>', 0)
        ])
    
    def _count_formules_unpaid(self):
        return self.env['potting.formule'].search_count([
            ('state', '=', 'validated'),
            ('avant_vente_paye', '=', False)
        ])
    
    def _count_contracts_uncovered(self):
        """Contrats dont le tonnage n'est pas entièrement couvert par des OT"""
        return self.env['potting.customer.order'].search_count([
            ('state', 'in', ['confirmed', 'in_progress']),
            ('remaining_contract_tonnage', '>', 0)
        ])
    
    def _get_alert_summary(self):
        """Résumé des alertes par catégorie"""
        return {
            'total_critical': len(self._get_critical_alerts()),
            'total_warning': len(self._get_warning_alerts()),
            'total_info': len(self._get_info_alerts()),
        }

    # =========================================================================
    # ENVOI D'EMAILS
    # =========================================================================
    
    @api.model
    def send_daily_alert_email(self):
        """Envoyer un email quotidien avec les alertes critiques aux managers"""
        alerts = self.get_all_alerts()
        
        if alerts['summary']['total_critical'] == 0 and alerts['summary']['total_warning'] == 0:
            return True  # Pas d'alertes, pas d'email
        
        # Récupérer les managers
        managers = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('potting_management.group_potting_manager').id)
        ])
        
        if not managers:
            return True
        
        # Construire le contenu de l'email
        html_content = self._build_alert_email_content(alerts)
        
        # Envoyer l'email à chaque manager
        for manager in managers:
            if manager.email:
                self._send_alert_email(manager, html_content, alerts['summary'])
        
        return True
    
    def _build_alert_email_content(self, alerts):
        """Construire le contenu HTML de l'email d'alertes"""
        lines = [
            "<h2>🚨 Alertes Exportations - %s</h2>" % date.today().strftime("%d/%m/%Y"),
        ]
        
        if alerts['critical']:
            lines.append("<h3 style='color: #dc3545;'>⚠️ Alertes Critiques (%d)</h3>" % len(alerts['critical']))
            lines.append("<ul>")
            for alert in alerts['critical']:
                lines.append("<li><strong>%s</strong><br/>%s</li>" % (alert['title'], alert['message']))
            lines.append("</ul>")
        
        if alerts['warning']:
            lines.append("<h3 style='color: #ffc107;'>⚡ Avertissements (%d)</h3>" % len(alerts['warning']))
            lines.append("<ul>")
            for alert in alerts['warning'][:10]:  # Limiter à 10
                lines.append("<li><strong>%s</strong><br/>%s</li>" % (alert['title'], alert['message']))
            if len(alerts['warning']) > 10:
                lines.append("<li><em>... et %d autres</em></li>" % (len(alerts['warning']) - 10))
            lines.append("</ul>")
        
        lines.append("<hr/>")
        lines.append("<p><a href='%s'>Accéder au tableau de bord</a></p>" % 
                    self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        
        return '\n'.join(lines)
    
    def _send_alert_email(self, user, html_content, summary):
        """Envoyer l'email d'alertes à un utilisateur"""
        subject = _("[Exportations] %d alerte(s) critique(s) - %s") % (
            summary['total_critical'],
            date.today().strftime("%d/%m/%Y")
        )
        
        mail_values = {
            'subject': subject,
            'body_html': html_content,
            'email_to': user.email,
            'email_from': self.env.company.email or 'noreply@icp.com',
            'auto_delete': True,
        }
        
        self.env['mail.mail'].sudo().create(mail_values).send()


class PottingTransitOrderAlerts(models.Model):
    """Extension de l'OT pour les alertes"""
    _inherit = 'potting.transit.order'
    
    has_pending_taxes_alert = fields.Boolean(
        string="Alerte taxes en attente",
        compute='_compute_alerts',
        store=False
    )
    
    has_pending_dus_alert = fields.Boolean(
        string="Alerte DUS en attente",
        compute='_compute_alerts',
        store=False
    )
    
    alert_level = fields.Selection([
        ('none', 'Aucune'),
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('critical', 'Critique'),
    ], string="Niveau d'alerte",
       compute='_compute_alerts',
       store=False)
    
    @api.depends('state', 'taxes_paid', 'dus_paid', 'create_date', 'date_sold')
    def _compute_alerts(self):
        for ot in self:
            ot.has_pending_taxes_alert = (
                ot.state == 'formule_linked' and 
                not ot.taxes_paid
            )
            ot.has_pending_dus_alert = (
                ot.state == 'sold' and 
                not ot.dus_paid
            )
            
            # Déterminer le niveau d'alerte
            if ot.has_pending_taxes_alert:
                if ot.create_date and ot.create_date < fields.Datetime.now() - timedelta(days=7):
                    ot.alert_level = 'critical'
                else:
                    ot.alert_level = 'warning'
            elif ot.has_pending_dus_alert:
                if ot.date_sold and ot.date_sold < date.today() - timedelta(days=3):
                    ot.alert_level = 'critical'
                else:
                    ot.alert_level = 'warning'
            else:
                ot.alert_level = 'none'
