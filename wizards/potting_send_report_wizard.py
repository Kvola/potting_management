# -*- coding: utf-8 -*-

import logging
import ast

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PottingSendReportWizard(models.TransientModel):
    """Wizard pour l'envoi de rapports par email.
    
    Ce wizard permet d'envoyer différents types de rapports:
    - Rapport journalier: activité sur une période donnée
    - Rapport par OT: détails d'ordres de transit spécifiques
    - Rapport de synthèse: résumé d'une commande client
    """
    _name = 'potting.send.report.wizard'
    _description = "Assistant d'envoi de rapport"

    # =========================================================================
    # FIELDS
    # =========================================================================

    report_type = fields.Selection([
        ('daily', '📅 Rapport journalier'),
        ('ot', '📦 Rapport par OT'),
        ('summary', '📊 Rapport de synthèse'),
    ], string="Type de rapport", required=True, default='daily',
       help="Sélectionnez le type de rapport à envoyer.")
    
    date_from = fields.Date(
        string="Date début",
        default=fields.Date.context_today,
        help="Date de début pour le rapport journalier."
    )
    
    date_to = fields.Date(
        string="Date fin",
        default=fields.Date.context_today,
        help="Date de fin pour le rapport journalier."
    )
    
    transit_order_ids = fields.Many2many(
        'potting.transit.order',
        string="Ordres de Transit",
        domain="[('state', 'not in', ('draft', 'cancelled'))]",
        help="Sélectionnez les OT à inclure dans le rapport."
    )
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        domain="[('state', 'not in', ('draft', 'cancelled'))]",
        help="Commande client pour le rapport de synthèse."
    )
    
    recipient_id = fields.Many2one(
        'res.partner',
        string="Destinataire principal",
        required=True,
        domain="[('email', '!=', False)]",
        help="Le destinataire principal du rapport (doit avoir une adresse email)."
    )
    
    cc_partner_ids = fields.Many2many(
        'res.partner',
        'potting_send_report_wizard_cc_partner_rel',
        'wizard_id',
        'partner_id',
        string="En copie (CC)",
        domain="[('email', '!=', False)]",
        default=lambda self: self._get_default_cc_partners(),
        help="Destinataires en copie du rapport."
    )
    
    include_pdf = fields.Boolean(
        string="Joindre PDF",
        default=True,
        help="Joindre le rapport au format PDF à l'email."
    )
    
    note = fields.Text(
        string="Message personnalisé",
        help="Message optionnel à inclure dans l'email."
    )
    
    # Champs calculés pour l'interface
    ot_count = fields.Integer(
        compute='_compute_preview_info',
        string="Nombre d'OT"
    )
    
    preview_info = fields.Html(
        compute='_compute_preview_info',
        string="Aperçu"
    )
    
    can_send = fields.Boolean(
        compute='_compute_can_send',
        string="Peut envoyer"
    )

    # =========================================================================
    # DEFAULT METHODS
    # =========================================================================

    @api.model
    def _get_default_cc_partners(self):
        """Récupère les partenaires CC par défaut depuis les paramètres."""
        ICP = self.env['ir.config_parameter'].sudo()
        cc_partner_ids_str = ICP.get_param(
            'potting_management.default_cc_partner_ids', '[]'
        )
        
        try:
            cc_partner_ids = ast.literal_eval(cc_partner_ids_str)
            if isinstance(cc_partner_ids, list):
                # Vérifier que les partenaires existent et ont des emails
                valid_partners = self.env['res.partner'].browse(cc_partner_ids).filtered('email')
                return [(6, 0, valid_partners.ids)]
        except (ValueError, SyntaxError) as e:
            _logger.warning(
                "Erreur lors de la lecture des partenaires CC par défaut: %s", e
            )
        
        return []

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('report_type', 'date_from', 'date_to', 'transit_order_ids', 
                 'customer_order_id')
    def _compute_preview_info(self):
        """Calcule les informations de prévisualisation du rapport."""
        for wizard in self:
            ot_count = 0
            preview_html = ""
            
            if wizard.report_type == 'daily':
                domain = [('state', 'not in', ('draft', 'cancelled'))]
                if wizard.date_from:
                    domain.append(('date_created', '>=', wizard.date_from))
                if wizard.date_to:
                    domain.append(('date_created', '<=', wizard.date_to))
                
                ot_count = self.env['potting.transit.order'].search_count(domain)
                preview_html = _(
                    "<p><strong>📅 Rapport journalier</strong></p>"
                    "<p>Période: %s à %s</p>"
                    "<p>OT concernés: <strong>%d</strong></p>"
                ) % (
                    wizard.date_from or '-',
                    wizard.date_to or '-',
                    ot_count
                )
                
            elif wizard.report_type == 'ot':
                ot_count = len(wizard.transit_order_ids)
                ot_names = ', '.join(wizard.transit_order_ids.mapped('name')[:5])
                if len(wizard.transit_order_ids) > 5:
                    ot_names += '...'
                preview_html = _(
                    "<p><strong>📦 Rapport par OT</strong></p>"
                    "<p>OT sélectionnés: <strong>%d</strong></p>"
                    "<p>%s</p>"
                ) % (ot_count, ot_names)
                
            elif wizard.report_type == 'summary':
                if wizard.customer_order_id:
                    ot_count = len(wizard.customer_order_id.transit_order_ids)
                    preview_html = _(
                        "<p><strong>📊 Rapport de synthèse</strong></p>"
                        "<p>Commande: <strong>%s</strong></p>"
                        "<p>Tonnage: %.2f T</p>"
                        "<p>OT associés: %d</p>"
                    ) % (
                        wizard.customer_order_id.name,
                        wizard.customer_order_id.tonnage or 0,
                        ot_count
                    )
                else:
                    preview_html = _(
                        "<p><strong>📊 Rapport de synthèse</strong></p>"
                        "<p><em>Sélectionnez une commande client</em></p>"
                    )
            
            wizard.ot_count = ot_count
            wizard.preview_info = preview_html
    
    @api.depends('report_type', 'recipient_id', 'date_from', 'date_to',
                 'transit_order_ids', 'customer_order_id')
    def _compute_can_send(self):
        """Vérifie si le rapport peut être envoyé."""
        for wizard in self:
            can_send = bool(wizard.recipient_id and wizard.recipient_id.email)
            
            if can_send:
                if wizard.report_type == 'daily':
                    can_send = bool(wizard.date_from and wizard.date_to)
                elif wizard.report_type == 'ot':
                    can_send = bool(wizard.transit_order_ids)
                elif wizard.report_type == 'summary':
                    can_send = bool(wizard.customer_order_id)
            
            wizard.can_send = can_send

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================

    @api.onchange('report_type')
    def _onchange_report_type(self):
        """Réinitialise les champs selon le type de rapport sélectionné."""
        if self.report_type == 'daily':
            self.transit_order_ids = False
            self.customer_order_id = False
            # Réinitialiser les dates si elles sont vides
            if not self.date_from:
                self.date_from = fields.Date.context_today(self)
            if not self.date_to:
                self.date_to = fields.Date.context_today(self)
        elif self.report_type == 'ot':
            self.date_from = False
            self.date_to = False
            self.customer_order_id = False
        elif self.report_type == 'summary':
            self.date_from = False
            self.date_to = False
            self.transit_order_ids = False
    
    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        """Valide la cohérence des dates."""
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                return {
                    'warning': {
                        'title': _("Dates incohérentes"),
                        'message': _(
                            "La date de début ne peut pas être postérieure "
                            "à la date de fin."
                        )
                    }
                }

    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    
    def _validate_recipient(self):
        """Valide que le destinataire principal a une adresse email."""
        self.ensure_one()
        
        if not self.recipient_id:
            raise UserError(_("Veuillez sélectionner un destinataire principal."))
        
        if not self.recipient_id.email:
            raise UserError(_(
                "Le destinataire principal '%s' n'a pas d'adresse email configurée."
            ) % self.recipient_id.name)
        
        # Vérifier le format de l'email
        email = self.recipient_id.email
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise UserError(_(
                "L'adresse email '%s' semble invalide."
            ) % email)
        
        return True
    
    def _validate_report_data(self):
        """Valide que les données nécessaires au rapport sont présentes."""
        self.ensure_one()
        
        if self.report_type == 'daily':
            if not self.date_from or not self.date_to:
                raise UserError(_(
                    "Veuillez spécifier les dates de début et de fin "
                    "pour le rapport journalier."
                ))
            
            if self.date_from > self.date_to:
                raise UserError(_(
                    "La date de début (%s) ne peut pas être postérieure "
                    "à la date de fin (%s)."
                ) % (self.date_from, self.date_to))
            
            # Vérifier qu'il y a des OT dans la période
            domain = [
                ('state', 'not in', ('draft', 'cancelled')),
                ('date_created', '>=', self.date_from),
                ('date_created', '<=', self.date_to),
            ]
            ot_count = self.env['potting.transit.order'].search_count(domain)
            if ot_count == 0:
                raise UserError(_(
                    "Aucun OT actif trouvé pour la période du %s au %s. "
                    "Veuillez sélectionner une autre période."
                ) % (self.date_from, self.date_to))
            
        elif self.report_type == 'ot':
            if not self.transit_order_ids:
                raise UserError(_(
                    "Veuillez sélectionner au moins un Ordre de Transit (OT) "
                    "pour le rapport."
                ))
            
        elif self.report_type == 'summary':
            if not self.customer_order_id:
                raise UserError(_(
                    "Veuillez sélectionner une commande client "
                    "pour le rapport de synthèse."
                ))
        
        return True
    
    def _get_email_template(self, report_type):
        """Retourne le template email approprié selon le type de rapport."""
        template_ref_map = {
            'daily': 'potting_management.mail_template_potting_daily_report',
            'ot': 'potting_management.mail_template_potting_daily_report',
            'summary': 'potting_management.mail_template_potting_summary_report',
        }
        
        template_ref = template_ref_map.get(report_type)
        if not template_ref:
            raise UserError(_(
                "Type de rapport non reconnu: %s"
            ) % report_type)
        
        try:
            template = self.env.ref(template_ref)
        except ValueError:
            raise UserError(_(
                "Le template email '%s' n'existe pas. "
                "Veuillez contacter l'administrateur."
            ) % template_ref)
        
        return template

    # =========================================================================
    # EMAIL BUILDING METHODS
    # =========================================================================
    
    def _build_email_context(self):
        """Construit le contexte pour l'envoi d'email."""
        self.ensure_one()
        
        cc_emails = self.cc_partner_ids.filtered('email').mapped('email')
        
        return {
            'recipient_email': self.recipient_id.email,
            'recipient_name': self.recipient_id.name,
            'cc_emails': ','.join(cc_emails) if cc_emails else '',
            'custom_note': self.note or '',
            'include_pdf': self.include_pdf,
        }
    
    def _send_single_report(self, template, record, ctx):
        """Envoie un rapport pour un enregistrement unique."""
        try:
            template.with_context(ctx).send_mail(record.id, force_send=True)
            _logger.info(
                "Rapport envoyé avec succès - Type: %s, Record: %s, Dest: %s",
                self.report_type, record.name, self.recipient_id.email
            )
            return True
        except Exception as e:
            _logger.exception(
                "Erreur envoi rapport - Type: %s, Record: %s, Erreur: %s",
                self.report_type, record.name, str(e)
            )
            return False

    # =========================================================================
    # ACTION METHODS
    # =========================================================================

    def action_send_report(self):
        """Envoie le rapport par email."""
        self.ensure_one()
        
        _logger.info(
            "Début envoi rapport - Type: %s, Destinataire: %s",
            self.report_type, self.recipient_id.email
        )
        
        # Validations
        self._validate_recipient()
        self._validate_report_data()
        
        # Préparer le contexte email
        ctx = self._build_email_context()
        
        # Compteurs pour le résumé
        sent_count = 0
        failed_count = 0
        
        try:
            if self.report_type == 'daily':
                template = self._get_email_template('daily')
                
                domain = [
                    ('state', 'not in', ('draft', 'cancelled')),
                    ('date_created', '>=', self.date_from),
                    ('date_created', '<=', self.date_to),
                ]
                transit_orders = self.env['potting.transit.order'].search(domain)
                
                for ot in transit_orders:
                    if self._send_single_report(template, ot, ctx):
                        sent_count += 1
                    else:
                        failed_count += 1
                        
            elif self.report_type == 'ot':
                template = self._get_email_template('ot')
                
                for ot in self.transit_order_ids:
                    if self._send_single_report(template, ot, ctx):
                        sent_count += 1
                    else:
                        failed_count += 1
                        
            elif self.report_type == 'summary':
                template = self._get_email_template('summary')
                
                if self._send_single_report(template, self.customer_order_id, ctx):
                    sent_count += 1
                else:
                    failed_count += 1
            
            # Message de résultat
            if failed_count > 0:
                message = _(
                    "Envoi partiellement réussi: %d rapport(s) envoyé(s), "
                    "%d échec(s)."
                ) % (sent_count, failed_count)
                notification_type = 'warning'
            else:
                message = _(
                    "%d rapport(s) envoyé(s) avec succès à %s."
                ) % (sent_count, self.recipient_id.name)
                notification_type = 'success'
            
            _logger.info(
                "Fin envoi rapport - Envoyés: %d, Échoués: %d",
                sent_count, failed_count
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('📧 Rapport envoyé') if notification_type == 'success' 
                             else _('⚠️ Envoi partiel'),
                    'message': message,
                    'type': notification_type,
                    'sticky': failed_count > 0,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            
        except Exception as e:
            _logger.exception("Erreur critique lors de l'envoi du rapport: %s", str(e))
            raise UserError(_(
                "Une erreur est survenue lors de l'envoi du rapport: %s"
            ) % str(e))
    
    def action_preview_report(self):
        """Prévisualise le rapport sans l'envoyer."""
        self.ensure_one()
        
        # Valider les données
        self._validate_report_data()
        
        # Déterminer l'action de prévisualisation selon le type
        if self.report_type == 'summary' and self.customer_order_id:
            return self.env.ref(
                'potting_management.action_report_potting_summary'
            ).report_action(self.customer_order_id)
        
        elif self.report_type in ('daily', 'ot'):
            records = self.transit_order_ids if self.report_type == 'ot' else False
            
            if not records and self.report_type == 'daily':
                domain = [
                    ('state', 'not in', ('draft', 'cancelled')),
                    ('date_created', '>=', self.date_from),
                    ('date_created', '<=', self.date_to),
                ]
                records = self.env['potting.transit.order'].search(domain, limit=10)
            
            if records:
                return self.env.ref(
                    'potting_management.action_report_potting_daily'
                ).report_action(records)
        
        raise UserError(_(
            "Impossible de prévisualiser le rapport. "
            "Veuillez vérifier les paramètres sélectionnés."
        ))
    
    def action_cancel(self):
        """Annule le wizard et retourne à la vue précédente."""
        return {'type': 'ir.actions.act_window_close'}
