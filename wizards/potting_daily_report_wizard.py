# -*- coding: utf-8 -*-

import base64
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PottingDailyReportWizard(models.TransientModel):
    """Wizard pour générer et envoyer le rapport quotidien OT au DG.
    
    Ce rapport est destiné à être envoyé par les utilisateurs ayant le profil
    group_potting_ceo_agent (Agent Exportation).
    """
    _name = 'potting.daily.report.wizard'
    _description = "Assistant rapport quotidien OT"

    # =========================================================================
    # FIELDS
    # =========================================================================
    
    report_date = fields.Date(
        string="Date du rapport",
        default=fields.Date.context_today,
        required=True,
        help="Date du rapport quotidien"
    )
    
    date_from = fields.Date(
        string="Date début",
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30),
        help="Filtrer les OT créés à partir de cette date"
    )
    
    date_to = fields.Date(
        string="Date fin",
        default=fields.Date.context_today,
        help="Filtrer les OT créés jusqu'à cette date"
    )
    
    ot_from = fields.Integer(
        string="OT depuis (numéro)",
        help="Numéro OT de début (optionnel)"
    )
    
    ot_to = fields.Integer(
        string="OT jusqu'à (numéro)",
        help="Numéro OT de fin (optionnel)"
    )
    
    transit_order_ids = fields.Many2many(
        'potting.transit.order',
        'potting_daily_report_wizard_ot_rel',
        'wizard_id',
        'transit_order_id',
        string="Ordres de Transit",
        compute='_compute_transit_order_ids',
        store=True,
        readonly=False
    )
    
    ot_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_ot_count'
    )
    
    recipient_id = fields.Many2one(
        'res.partner',
        string="Destinataire (DG)",
        required=True,
        domain="[('email', '!=', False)]",
        help="Le Directeur Général destinataire du rapport"
    )
    
    cc_partner_ids = fields.Many2many(
        'res.partner',
        'potting_daily_report_wizard_cc_partner_rel',
        'wizard_id',
        'partner_id',
        string="En copie (CC)",
        domain="[('email', '!=', False)]",
        help="Destinataires en copie du rapport"
    )
    
    include_pdf = fields.Boolean(
        string="Joindre PDF",
        default=True,
        help="Joindre le rapport au format PDF à l'email"
    )
    
    note = fields.Text(
        string="Message personnalisé",
        help="Message optionnel à inclure dans l'email"
    )
    
    # Champs calculés pour l'aperçu
    preview_info = fields.Html(
        compute='_compute_preview_info',
        string="Aperçu du rapport"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('generated', 'Généré'),
        ('sent', 'Envoyé'),
    ], string="État", default='draft')

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('date_from', 'date_to')
    def _compute_transit_order_ids(self):
        for wizard in self:
            domain = [('state', 'not in', ['draft', 'cancelled'])]
            if wizard.date_from:
                domain.append(('date_created', '>=', wizard.date_from))
            if wizard.date_to:
                domain.append(('date_created', '<=', wizard.date_to))
            
            orders = self.env['potting.transit.order'].search(domain, order='name asc')
            wizard.transit_order_ids = orders
    
    @api.depends('transit_order_ids')
    def _compute_ot_count(self):
        for wizard in self:
            wizard.ot_count = len(wizard.transit_order_ids)
    
    @api.depends('transit_order_ids', 'report_date')
    def _compute_preview_info(self):
        for wizard in self:
            if not wizard.transit_order_ids:
                wizard.preview_info = '<p class="text-muted">Aucun OT sélectionné</p>'
                continue
            
            # Grouper les OT par client
            ot_by_customer = {}
            for ot in wizard.transit_order_ids:
                customer_key = (ot.customer_id.parent_id.name or ot.customer_id.name, 
                               ot.consignee_id.name if ot.consignee_id else '')
                if customer_key not in ot_by_customer:
                    ot_by_customer[customer_key] = []
                ot_by_customer[customer_key].append(ot)
            
            # Calculer les statistiques
            total_tonnage = sum(wizard.transit_order_ids.mapped('tonnage'))
            total_current = sum(wizard.transit_order_ids.mapped('current_tonnage'))
            avg_progress = sum(wizard.transit_order_ids.mapped('progress_percentage')) / len(wizard.transit_order_ids) if wizard.transit_order_ids else 0
            
            # Compter par état
            in_tc = len(wizard.transit_order_ids.filtered(lambda o: o.state == 'done'))
            in_prod_100 = len(wizard.transit_order_ids.filtered(lambda o: o.progress_percentage >= 100 and o.state != 'done'))
            in_prod = len(wizard.transit_order_ids.filtered(lambda o: o.progress_percentage < 100 and o.state not in ['done', 'cancelled']))
            
            # Trouver la plage de numéros OT
            ot_numbers = []
            for ot in wizard.transit_order_ids:
                # Extraire le numéro de l'OT (format: XXXX/YYYY-YYYY-XX ou REF-XXXX/YYYY-YYYY-XX)
                import re
                match = re.search(r'(\d+)/', ot.name)
                if match:
                    ot_numbers.append(int(match.group(1)))
            
            ot_range = ""
            if ot_numbers:
                ot_range = f"<strong>From OT:</strong> {min(ot_numbers)} <strong>to:</strong> {max(ot_numbers)}"
            
            html = f'''
            <div class="row">
                <div class="col-6">
                    <h4>📊 Résumé du rapport</h4>
                    <ul>
                        <li><strong>Date:</strong> {wizard.report_date}</li>
                        <li><strong>Nombre d'OT:</strong> {len(wizard.transit_order_ids)}</li>
                        <li>{ot_range}</li>
                        <li><strong>Tonnage total:</strong> {total_tonnage:,.0f} Kg</li>
                        <li><strong>Production actuelle:</strong> {total_current:,.0f} Kg</li>
                        <li><strong>Progression moyenne:</strong> {avg_progress:.1f}%</li>
                    </ul>
                </div>
                <div class="col-6">
                    <h4>📦 Répartition par état</h4>
                    <ul>
                        <li><span style="color: green;">●</span> <strong>100% In TC:</strong> {in_tc} OT</li>
                        <li><span style="color: #DAA520;">●</span> <strong>100% Production:</strong> {in_prod_100} OT</li>
                        <li><span style="color: red;">●</span> <strong>In Production:</strong> {in_prod} OT</li>
                    </ul>
                    <h4>👥 Clients ({len(ot_by_customer)})</h4>
                    <ul>
                        {"".join([f"<li>{c[0]} / {c[1]}: {len(ots)} OT</li>" for c, ots in list(ot_by_customer.items())[:5]])}
                        {"<li>...</li>" if len(ot_by_customer) > 5 else ""}
                    </ul>
                </div>
            </div>
            '''
            wizard.preview_info = html

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_preview_report(self):
        """Prévisualiser le rapport avant envoi"""
        self.ensure_one()
        
        if not self.transit_order_ids:
            raise UserError(_("Aucun OT sélectionné pour le rapport."))
        
        return self.env.ref('potting_management.action_report_ot_daily').report_action(self)
    
    def action_download_pdf(self):
        """Télécharger le rapport en PDF"""
        self.ensure_one()
        
        if not self.transit_order_ids:
            raise UserError(_("Aucun OT sélectionné pour le rapport."))
        
        return self.env.ref('potting_management.action_report_ot_daily').report_action(self)
    
    def action_send_email(self):
        """Envoyer le rapport par email au DG"""
        self.ensure_one()
        
        if not self.transit_order_ids:
            raise UserError(_("Aucun OT sélectionné pour le rapport."))
        
        if not self.recipient_id:
            raise UserError(_("Veuillez sélectionner un destinataire (DG)."))
        
        if not self.recipient_id.email:
            raise UserError(_("Le destinataire doit avoir une adresse email."))
        
        # Générer le PDF
        report = self.env.ref('potting_management.action_report_ot_daily')
        pdf_content, _ = report._render_qweb_pdf(report.id, [self.id])
        
        # Créer la pièce jointe
        attachment = self.env['ir.attachment'].create({
            'name': f'OT_Daily_Report_{self.report_date}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })
        
        # Trouver la plage des numéros OT
        import re
        ot_numbers = []
        for ot in self.transit_order_ids:
            match = re.search(r'(\d+)/', ot.name)
            if match:
                ot_numbers.append(int(match.group(1)))
        
        ot_range = ""
        if ot_numbers:
            ot_range = f"OT {min(ot_numbers)} à {max(ot_numbers)}"
        
        # Préparer le corps de l'email
        body_html = f'''
        <p>Bonjour,</p>
        <p>Veuillez trouver ci-joint le rapport quotidien OT du <strong>{self.report_date}</strong>.</p>
        <p><strong>Résumé:</strong></p>
        <ul>
            <li>Nombre d'OT: {len(self.transit_order_ids)}</li>
            <li>Plage: {ot_range}</li>
            <li>Tonnage total: {sum(self.transit_order_ids.mapped('tonnage')):,.0f} Kg</li>
        </ul>
        '''
        
        if self.note:
            body_html += f'<p><strong>Message:</strong></p><p>{self.note}</p>'
        
        body_html += f'''
        <p>Cordialement,<br/>{self.env.user.name}</p>
        '''
        
        # Créer et envoyer l'email
        mail_values = {
            'subject': f'OT Daily Report - {self.report_date}',
            'body_html': body_html,
            'email_to': self.recipient_id.email,
            'email_cc': ','.join(self.cc_partner_ids.mapped('email')) if self.cc_partner_ids else False,
            'attachment_ids': [(4, attachment.id)] if self.include_pdf else [],
            'author_id': self.env.user.partner_id.id,
        }
        
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
        
        self.state = 'sent'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Rapport envoyé'),
                'message': _('Le rapport quotidien OT a été envoyé à %s.') % self.recipient_id.name,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_refresh_ot_list(self):
        """Rafraîchir la liste des OT selon les filtres"""
        self.ensure_one()
        self._compute_transit_order_ids()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # =========================================================================
    # HELPER METHODS FOR REPORT
    # =========================================================================
    
    def get_ot_data_for_report(self):
        """Prépare les données groupées par OT pour le rapport"""
        self.ensure_one()
        
        result = []
        for ot in self.transit_order_ids.sorted(key=lambda o: o.name):
            # Extraire le numéro OT
            import re
            match = re.search(r'(\d+)/', ot.name)
            ot_number = match.group(1) if match else ot.name
            
            # Calculer les informations de production
            total_kg = ot.tonnage * 1000  # Convertir en kg
            current_kg = ot.current_tonnage * 1000
            progress = (current_kg / total_kg * 100) if total_kg > 0 else 0
            
            # Déterminer le type d'unité
            product_config = {
                'cocoa_mass': 'Box of liquor',
                'cocoa_butter': 'Box of butter',
                'cocoa_cake': 'Big Bag',
                'cocoa_powder': 'Sac'
            }
            unit_name = product_config.get(ot.product_type, 'Unités')
            
            # Calculer le nombre d'unités
            unit_weight = {
                'cocoa_mass': 25,  # kg
                'cocoa_butter': 25,
                'cocoa_cake': 1000,
                'cocoa_powder': 25
            }
            weight = unit_weight.get(ot.product_type, 25)
            total_units = int(total_kg / weight) if weight > 0 else 0
            
            # Déterminer l'état de couleur
            if ot.state == 'done':
                color_status = 'green'  # 100% In TC
            elif progress >= 100:
                color_status = 'yellow'  # 100% Production
            else:
                color_status = 'red'  # In Production
            
            # Client et consignee
            customer_name = ot.customer_id.parent_id.name if ot.customer_id.parent_id else ot.customer_id.name
            consignee_name = ot.consignee_id.name if ot.consignee_id else ''
            
            # Certification suffix
            cert_suffix = ''
            if ot.lot_ids and ot.lot_ids[0].certification_id:
                cert_suffix = ot.lot_ids[0].certification_id.suffix or ''
            
            # Préparer les données des lots
            lots_data = []
            for lot in ot.lot_ids.sorted(key=lambda l: l.name):
                lot_data = {
                    'name': lot.name,
                    'contract_number': lot.contract_number or '',
                    'bl_number': lot.bl_number or '',
                    'bl_date': lot.bl_date,
                    'container_number': lot.container_id.name if lot.container_id else '',
                    'vessel_name': ot.vessel_name or '',
                    'booking_number': ot.booking_number or '',
                    'eta': lot.container_id.date_arrival if lot.container_id else None,
                    'etd': lot.container_id.date_departure if lot.container_id else None,
                    'shipping_line': lot.container_id.shipping_line if lot.container_id else '',
                    'destination': lot.destination or ot.pod or '',
                    'date_potted': lot.date_potted.date() if lot.date_potted else None,
                    'date_production_end': lot.date_production_end,
                    'quantity_kg': lot.current_tonnage * 1000,
                }
                lots_data.append(lot_data)
            
            ot_data = {
                'ot_number': ot_number,
                'name': ot.name,
                'customer_name': customer_name,
                'consignee_name': consignee_name,
                'total_kg': total_kg,
                'total_units': total_units,
                'unit_name': unit_name,
                'certification': cert_suffix,
                'progress': progress,
                'current_kg': current_kg,
                'color_status': color_status,
                'lots': lots_data,
            }
            result.append(ot_data)
        
        return result
    
    def get_ot_number_range(self):
        """Retourne la plage des numéros OT"""
        import re
        ot_numbers = []
        for ot in self.transit_order_ids:
            match = re.search(r'(\d+)/', ot.name)
            if match:
                ot_numbers.append(int(match.group(1)))
        
        if ot_numbers:
            return {'from': min(ot_numbers), 'to': max(ot_numbers)}
        return {'from': 0, 'to': 0}
