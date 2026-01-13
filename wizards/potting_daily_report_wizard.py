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
        string="Destinataire (PDG)",
        required=True,
        domain="[('email', '!=', False)]",
        help="Le PDG/Directeur Général destinataire du rapport",
        default=lambda self: self._get_default_ceo()
    )
    
    @api.model
    def _get_default_ceo(self):
        """Get default CEO from settings."""
        ceo_id = self.env['ir.config_parameter'].sudo().get_param(
            'potting_management.ceo_partner_id', False
        )
        if ceo_id:
            try:
                return int(ceo_id)
            except (ValueError, TypeError):
                return False
        return False
    
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
    
    exclude_fully_delivered = fields.Boolean(
        string="Exclure les OT entièrement livrés",
        default=True,
        help="Si coché, les OT dont tous les lots ont été livrés ne seront pas inclus dans le rapport"
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
    
    @api.depends('date_from', 'date_to', 'exclude_fully_delivered')
    def _compute_transit_order_ids(self):
        for wizard in self:
            domain = [('state', 'not in', ['draft', 'cancelled'])]
            if wizard.date_from:
                domain.append(('date_created', '>=', wizard.date_from))
            if wizard.date_to:
                domain.append(('date_created', '<=', wizard.date_to))
            
            # Exclude fully delivered OTs if option is enabled
            if wizard.exclude_fully_delivered:
                domain.append(('delivery_status', '!=', 'fully_delivered'))
            
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
            
            # Compter par statut de livraison
            partial_delivery_count = len(wizard.transit_order_ids.filtered(lambda o: o.delivery_status == 'partial'))
            fully_delivered_count = len(wizard.transit_order_ids.filtered(lambda o: o.delivery_status == 'fully_delivered'))
            not_delivered_count = len(wizard.transit_order_ids.filtered(lambda o: o.delivery_status == 'not_delivered'))
            
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
                    <h4>� Statut de livraison</h4>
                    <ul>
                        <li><span style="color: orange;">●</span> <strong>Livraison partielle:</strong> {partial_delivery_count} OT</li>
                        <li><span style="color: gray;">●</span> <strong>Non livrés:</strong> {not_delivered_count} OT</li>
                        <li><span style="color: blue;">●</span> <strong>Entièrement livrés:</strong> {fully_delivered_count} OT</li>
                    </ul>
                    <h4>�👥 Clients ({len(ot_by_customer)})</h4>
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
        
        # Calcul des statistiques
        total_tonnage_kg = sum(self.transit_order_ids.mapped('tonnage')) * 1000
        total_current_kg = sum(self.transit_order_ids.mapped('current_tonnage')) * 1000
        avg_progress = sum(self.transit_order_ids.mapped('progress_percentage')) / len(self.transit_order_ids) if self.transit_order_ids else 0
        
        # Comptage par état
        in_tc_count = len(self.transit_order_ids.filtered(lambda o: o.state == 'done'))
        prod_100_count = len(self.transit_order_ids.filtered(lambda o: o.progress_percentage >= 100 and o.state != 'done'))
        in_prod_count = len(self.transit_order_ids.filtered(lambda o: o.progress_percentage < 100 and o.state not in ['done', 'cancelled']))
        
        # Préparer le corps de l'email avec design professionnel
        body_html = f'''
        <div style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellspacing="0" cellpadding="0" style="max-width: 700px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <!-- En-tête -->
                <tr>
                    <td style="background: linear-gradient(135deg, #1a5f2a 0%, #27ae60 100%); padding: 25px 30px;">
                        <table width="100%" cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="vertical-align: middle;">
                                    <span style="color: #90EE90; font-size: 20px; font-weight: bold;">IVORY</span><br/>
                                    <span style="color: #D2691E; font-size: 20px; font-weight: bold;">COCOA</span>
                                    <span style="color: #ffffff; font-size: 20px; font-weight: bold;">PRODUCTS</span><br/>
                                    <span style="color: #ffffff; font-size: 11px;">Côte d'Ivoire</span>
                                </td>
                                <td style="text-align: right; vertical-align: middle;">
                                    <span style="color: #ffffff; font-size: 20px; font-weight: bold;">📊 OT DAILY REPORT</span><br/>
                                    <span style="color: #e8f5e9; font-size: 13px;">{self.report_date.strftime('%A %d %B %Y')}</span>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                
                <!-- Corps -->
                <tr>
                    <td style="padding: 30px;">
                        <p style="margin: 0 0 20px 0; color: #333333; font-size: 15px;">
                            Bonjour <strong>{self.recipient_id.name}</strong>,
                        </p>
                        <p style="margin: 0 0 25px 0; color: #333333; font-size: 15px;">
                            Veuillez trouver ci-joint le rapport quotidien OT du <strong style="color: #1a5f2a;">{self.report_date.strftime('%d/%m/%Y')}</strong>.
                        </p>
                        
                        <!-- Tableau de bord statistiques -->
                        <table width="100%" cellspacing="8" cellpadding="0" style="margin-bottom: 25px;">
                            <tr>
                                <td style="width: 25%; text-align: center; background: linear-gradient(180deg, #1a5f2a, #27ae60); padding: 15px 10px; border-radius: 8px;">
                                    <span style="color: #fff; font-size: 28px; font-weight: bold;">{len(self.transit_order_ids)}</span><br/>
                                    <span style="color: #e8f5e9; font-size: 11px; text-transform: uppercase;">Total OT</span>
                                </td>
                                <td style="width: 25%; text-align: center; background: linear-gradient(180deg, #8B4513, #D2691E); padding: 15px 10px; border-radius: 8px;">
                                    <span style="color: #fff; font-size: 22px; font-weight: bold;">{total_tonnage_kg:,.0f}</span><br/>
                                    <span style="color: #ffe4c4; font-size: 11px; text-transform: uppercase;">Tonnage (Kg)</span>
                                </td>
                                <td style="width: 25%; text-align: center; background: linear-gradient(180deg, #2980b9, #3498db); padding: 15px 10px; border-radius: 8px;">
                                    <span style="color: #fff; font-size: 22px; font-weight: bold;">{avg_progress:.1f}%</span><br/>
                                    <span style="color: #e3f2fd; font-size: 11px; text-transform: uppercase;">Progression Moy.</span>
                                </td>
                                <td style="width: 25%; text-align: center; background: linear-gradient(180deg, #7b1fa2, #9c27b0); padding: 15px 10px; border-radius: 8px;">
                                    <span style="color: #fff; font-size: 22px; font-weight: bold;">{total_current_kg:,.0f}</span><br/>
                                    <span style="color: #f3e5f5; font-size: 11px; text-transform: uppercase;">Produit (Kg)</span>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Répartition par état -->
                        <table width="100%" cellspacing="0" cellpadding="12" style="background-color: #f8f9fa; border-radius: 8px; margin-bottom: 25px;">
                            <tr>
                                <td colspan="3" style="background-color: #1a5f2a; color: #ffffff; font-weight: bold; border-radius: 8px 8px 0 0; padding: 12px; font-size: 14px;">
                                    📦 RÉPARTITION PAR ÉTAT DE PRODUCTION
                                </td>
                            </tr>
                            <tr>
                                <td style="text-align: center; padding: 15px; border-right: 1px solid #e0e0e0;">
                                    <span style="display: inline-block; width: 16px; height: 16px; background-color: #27ae60; border-radius: 50%; vertical-align: middle;"></span>
                                    <span style="font-size: 20px; font-weight: bold; color: #27ae60; margin-left: 8px;">{in_tc_count}</span><br/>
                                    <span style="font-size: 12px; color: #666;">100% In TC</span>
                                </td>
                                <td style="text-align: center; padding: 15px; border-right: 1px solid #e0e0e0;">
                                    <span style="display: inline-block; width: 16px; height: 16px; background-color: #f9a825; border-radius: 50%; vertical-align: middle;"></span>
                                    <span style="font-size: 20px; font-weight: bold; color: #f9a825; margin-left: 8px;">{prod_100_count}</span><br/>
                                    <span style="font-size: 12px; color: #666;">100% Production</span>
                                </td>
                                <td style="text-align: center; padding: 15px;">
                                    <span style="display: inline-block; width: 16px; height: 16px; background-color: #e53935; border-radius: 50%; vertical-align: middle;"></span>
                                    <span style="font-size: 20px; font-weight: bold; color: #e53935; margin-left: 8px;">{in_prod_count}</span><br/>
                                    <span style="font-size: 12px; color: #666;">En Production</span>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Plage OT -->
                        <div style="background-color: #e8f5e9; border-left: 4px solid #27ae60; padding: 12px 15px; margin-bottom: 20px; border-radius: 0 8px 8px 0;">
                            <strong style="color: #1a5f2a;">📋 Plage des OT:</strong> 
                            <span style="color: #333; font-size: 14px;">{ot_range}</span>
                        </div>
        '''
        
        if self.note:
            body_html += f'''
                        <div style="background-color: #fff8e1; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 0 8px 8px 0;">
                            <strong style="color: #f57c00;">📝 Message:</strong><br/>
                            <span style="color: #333333;">{self.note}</span>
                        </div>
            '''
        
        body_html += f'''
                        <p style="margin: 25px 0 0 0; color: #333333; font-size: 15px;">
                            Cordialement,
                        </p>
                        <p style="margin: 5px 0 0 0; color: #1a5f2a; font-size: 15px; font-weight: bold;">
                            {self.env.user.name}<br/>
                            <span style="font-size: 13px; font-weight: normal; color: #666666;">{self.env.user.email or ''}</span>
                        </p>
                    </td>
                </tr>
                
                <!-- Pied de page -->
                <tr>
                    <td style="background-color: #333333; padding: 20px 30px; text-align: center;">
                        <span style="color: #ffffff; font-size: 12px;">
                            IVORY COCOA PRODUCTS - Côte d'Ivoire<br/>
                            <span style="color: #888888;">Ce rapport a été généré automatiquement</span>
                        </span>
                    </td>
                </tr>
            </table>
        </div>
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
                # Delivery status info
                'delivery_status': ot.delivery_status,
                'is_partial_delivery': ot.delivery_status == 'partial',
                'delivered_lot_count': ot.delivered_lot_count,
                'delivered_tonnage_kg': ot.delivered_tonnage * 1000,
                'remaining_to_deliver_kg': ot.remaining_to_deliver_tonnage * 1000,
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
    
    def get_report_statistics(self):
        """Retourne les statistiques globales du rapport pour l'en-tête"""
        self.ensure_one()
        
        total_ot = len(self.transit_order_ids)
        total_tonnage_kg = sum(self.transit_order_ids.mapped('tonnage')) * 1000
        total_current_kg = sum(self.transit_order_ids.mapped('current_tonnage')) * 1000
        
        # Calcul de la progression moyenne
        if total_ot > 0:
            avg_progress = sum(self.transit_order_ids.mapped('progress_percentage')) / total_ot
        else:
            avg_progress = 0
        
        # Comptage par état
        in_tc_count = len(self.transit_order_ids.filtered(lambda o: o.state == 'done'))
        prod_100_count = len(self.transit_order_ids.filtered(
            lambda o: o.progress_percentage >= 100 and o.state != 'done'
        ))
        in_prod_count = len(self.transit_order_ids.filtered(
            lambda o: o.progress_percentage < 100 and o.state not in ['done', 'cancelled']
        ))
        
        # Comptage par statut de livraison
        partial_delivery_count = len(self.transit_order_ids.filtered(
            lambda o: o.delivery_status == 'partial'
        ))
        fully_delivered_count = len(self.transit_order_ids.filtered(
            lambda o: o.delivery_status == 'fully_delivered'
        ))
        not_delivered_count = len(self.transit_order_ids.filtered(
            lambda o: o.delivery_status == 'not_delivered'
        ))
        
        return {
            'total_ot': total_ot,
            'total_tonnage_kg': total_tonnage_kg,
            'total_current_kg': total_current_kg,
            'avg_progress': avg_progress,
            'in_tc_count': in_tc_count,
            'prod_100_count': prod_100_count,
            'in_prod_count': in_prod_count,
            'partial_delivery_count': partial_delivery_count,
            'fully_delivered_count': fully_delivered_count,
            'not_delivered_count': not_delivered_count,
        }
