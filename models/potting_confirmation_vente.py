# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class PottingConfirmationVente(models.Model):
    """Confirmation de Vente (CV) - Autorisation du Conseil Café-Cacao
    
    La Confirmation de Vente est un document délivré par le Conseil du Café-Cacao
    de Côte d'Ivoire qui autorise l'exécution d'un contrat d'exportation.
    Elle définit le tonnage autorisé, la période de validité et le prix garanti.
    """
    _name = 'potting.confirmation.vente'
    _description = 'Confirmation de Vente (CV)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_emission desc, name desc'
    _check_company_auto = True

    # =========================================================================
    # CONTRAINTES SQL
    # =========================================================================
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 
         'Le numéro de confirmation de vente doit être unique!'),
        ('reference_ccc_uniq', 'unique(reference_ccc)', 
         'La référence CCC doit être unique!'),
        ('tonnage_positive', 'CHECK(tonnage_autorise > 0)', 
         'Le tonnage autorisé doit être supérieur à 0!'),
        ('prix_tonnage_positive', 'CHECK(prix_tonnage >= 0)',
         'Le prix au tonnage doit être positif ou nul!'),
        ('date_coherence', 'CHECK(date_start <= date_end)',
         'La date de début doit être antérieure ou égale à la date de fin!'),
    ]

    # =========================================================================
    # CHAMPS - IDENTIFICATION
    # =========================================================================
    
    name = fields.Char(
        string="Numéro CV",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
        index=True,
        help="Numéro de séquence interne de la Confirmation de Vente"
    )
    
    reference_ccc = fields.Char(
        string="Référence CCC",
        tracking=True,
        index=True,
        help="Référence officielle attribuée par le Conseil Café-Cacao"
    )
    
    # =========================================================================
    # CHAMPS - DATES ET PÉRIODE
    # =========================================================================
    
    date_emission = fields.Date(
        string="Date d'émission",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
        help="Date d'émission de la Confirmation de Vente par le CCC"
    )
    
    date_start = fields.Date(
        string="Début de validité",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help="Date de début de la période couverte par la CV"
    )
    
    date_end = fields.Date(
        string="Fin de validité",
        required=True,
        tracking=True,
        help="Date de fin de la période couverte par la CV"
    )
    
    is_expired = fields.Boolean(
        string="Expirée",
        compute='_compute_is_expired',
        store=True,
        help="Indique si la CV a dépassé sa date de fin de validité"
    )
    
    days_remaining = fields.Integer(
        string="Jours restants",
        compute='_compute_days_remaining',
        help="Nombre de jours avant expiration de la CV"
    )
    
    # =========================================================================
    # CHAMPS - CAMPAGNE ET SOCIÉTÉ
    # =========================================================================
    
    campaign_id = fields.Many2one(
        'potting.campaign',
        string="Campagne Café-Cacao",
        required=True,
        tracking=True,
        domain="[('state', 'in', ['draft', 'active'])]",
        help="Campagne café-cacao associée à cette CV"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    # =========================================================================
    # CHAMPS - PRIX ET DEVISE
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self._get_default_currency(),
        required=True,
        tracking=True,
        help="Devise pour le prix au tonnage"
    )
    
    prix_tonnage = fields.Monetary(
        string="Prix au tonnage",
        currency_field='currency_id',
        required=True,
        tracking=True,
        help="Prix garanti par tonne de cacao fixé par le CCC (FCFA/tonne)"
    )
    
    # =========================================================================
    # CHAMPS - TONNAGE
    # =========================================================================
    
    tonnage_autorise = fields.Float(
        string="Tonnage autorisé (T)",
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Tonnage maximum autorisé par cette Confirmation de Vente"
    )
    
    tonnage_utilise = fields.Float(
        string="Tonnage utilisé (T)",
        compute='_compute_tonnage_utilise',
        store=True,
        digits='Product Unit of Measure',
        help="Tonnage consommé par les contrats liés à cette CV"
    )
    
    tonnage_restant = fields.Float(
        string="Tonnage restant (T)",
        compute='_compute_tonnage_utilise',
        store=True,
        digits='Product Unit of Measure',
        help="Tonnage encore disponible pour de nouveaux contrats"
    )
    
    tonnage_progress = fields.Float(
        string="Progression (%)",
        compute='_compute_tonnage_utilise',
        store=True,
        help="Pourcentage du tonnage autorisé déjà utilisé"
    )
    
    # =========================================================================
    # CHAMPS - DESTINATION
    # =========================================================================
    
    destination_country_id = fields.Many2one(
        'res.country',
        string="Pays de destination",
        tracking=True,
        help="Pays de destination autorisé pour cette CV"
    )
    
    destination_port = fields.Char(
        string="Port de destination",
        tracking=True,
        help="Port de destination pour l'exportation"
    )
    
    # =========================================================================
    # CHAMPS - TYPE DE PRODUIT
    # =========================================================================
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
        ('all', 'Tous produits'),
    ], string="Type de produit",
       default='all',
       required=True,
       tracking=True,
       help="Type de produit autorisé par cette CV")
    
    # =========================================================================
    # CHAMPS - RELATIONS
    # =========================================================================
    
    customer_order_ids = fields.Many2many(
        'potting.customer.order',
        'potting_customer_order_confirmation_vente_rel',
        'confirmation_vente_id',
        'customer_order_id',
        string="Contrats liés",
        copy=False
    )
    
    customer_order_count = fields.Integer(
        string="Nombre de contrats",
        compute='_compute_customer_order_count',
        store=True
    )
    
    formule_ids = fields.One2many(
        'potting.formule',
        'confirmation_vente_id',
        string="Formules",
        copy=False
    )
    
    formule_count = fields.Integer(
        string="Nombre de formules",
        compute='_compute_formule_count',
        store=True
    )
    
    # =========================================================================
    # CHAMPS - ÉTAT
    # =========================================================================
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Active'),
        ('consumed', 'Consommée'),
        ('expired', 'Expirée'),
        ('cancelled', 'Annulée'),
    ], string="État",
       default='draft',
       tracking=True,
       index=True,
       copy=False,
       help="État de la Confirmation de Vente")
    
    note = fields.Text(
        string="Notes",
        help="Notes et observations internes"
    )
    
    # =========================================================================
    # CHAMPS - FACTURE TRANSITAIRE JOINTE
    # =========================================================================
    
    forwarding_agent_invoice = fields.Binary(
        string="Facture Transitaire",
        attachment=True,
        help="Scan ou PDF de la facture du transitaire"
    )
    
    forwarding_agent_invoice_filename = fields.Char(
        string="Nom du fichier facture"
    )
    
    # =========================================================================
    # MÉTHODES PAR DÉFAUT
    # =========================================================================
    
    def _get_default_currency(self):
        """Retourne XOF (FCFA) par défaut"""
        xof = self.env['res.currency'].search([('name', '=', 'XOF')], limit=1)
        return xof or self.env.company.currency_id
    
    # =========================================================================
    # MÉTHODES ACTIONS
    # =========================================================================
    
    def action_download_invoice(self):
        """Ouvre la facture transitaire dans un nouvel onglet"""
        self.ensure_one()
        if not self.forwarding_agent_invoice:
            raise UserError(_("Aucune facture transitaire jointe."))
        
        # Chercher l'attachment correspondant
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('res_field', '=', 'forwarding_agent_invoice'),
        ], limit=1)
        
        if attachment:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%s?download=false' % attachment.id,
                'target': 'new',
            }
        else:
            # Fallback: télécharger directement
            import base64
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=%s&id=%s&field=forwarding_agent_invoice&filename=%s&download=false' % (
                    self._name, self.id, self.forwarding_agent_invoice_filename or 'facture'
                ),
                'target': 'new',
            }
    
    # =========================================================================
    # MÉTHODES COMPUTED
    # =========================================================================
    
    @api.depends('date_end')
    def _compute_is_expired(self):
        today = date.today()
        for record in self:
            record.is_expired = record.date_end and record.date_end < today
    
    def _compute_days_remaining(self):
        today = date.today()
        for record in self:
            if record.date_end:
                delta = record.date_end - today
                record.days_remaining = max(0, delta.days)
            else:
                record.days_remaining = 0
    
    @api.depends('customer_order_ids', 'customer_order_ids.contract_tonnage', 'customer_order_ids.state')
    def _compute_tonnage_utilise(self):
        """Calcule le tonnage utilisé basé sur les contrats liés"""
        for record in self:
            # Calcul basé sur le Many2many direct avec les contrats
            tonnage_utilise = sum(
                order.contract_tonnage 
                for order in record.customer_order_ids 
                if order.state not in ('cancelled',)
            )
            
            record.tonnage_utilise = tonnage_utilise
            record.tonnage_restant = record.tonnage_autorise - tonnage_utilise
            
            if record.tonnage_autorise > 0:
                record.tonnage_progress = (tonnage_utilise / record.tonnage_autorise) * 100
            else:
                record.tonnage_progress = 0
    
    @api.depends('customer_order_ids')
    def _compute_customer_order_count(self):
        for record in self:
            record.customer_order_count = len(record.customer_order_ids)
    
    @api.depends('formule_ids')
    def _compute_formule_count(self):
        for record in self:
            record.formule_count = len(record.formule_ids)
    
    # =========================================================================
    # CONTRAINTES
    # =========================================================================
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end:
                if record.date_start > record.date_end:
                    raise ValidationError(_(
                        "La date de fin de validité doit être postérieure à la date de début."
                    ))
    
    @api.constrains('tonnage_autorise', 'tonnage_utilise')
    def _check_tonnage(self):
        for record in self:
            if record.tonnage_utilise > record.tonnage_autorise:
                raise ValidationError(_(
                    "Le tonnage utilisé (%(used).2f T) ne peut pas dépasser "
                    "le tonnage autorisé (%(allowed).2f T).",
                    used=record.tonnage_utilise,
                    allowed=record.tonnage_autorise
                ))
    
    @api.constrains('date_emission', 'date_start')
    def _check_date_emission(self):
        """Vérifie que la date d'émission est cohérente avec la période"""
        for record in self:
            if record.date_emission and record.date_start:
                if record.date_emission > record.date_start:
                    raise ValidationError(_(
                        "La date d'émission (%s) doit être antérieure ou égale "
                        "à la date de début de validité (%s).",
                        record.date_emission, record.date_start
                    ))
    
    @api.constrains('prix_tonnage')
    def _check_prix_tonnage(self):
        """Vérifie que le prix au tonnage est raisonnable"""
        for record in self:
            if record.prix_tonnage <= 0:
                raise ValidationError(_(
                    "Le prix au tonnage doit être supérieur à 0."
                ))
            # Vérifier que le prix est dans une fourchette raisonnable (en FCFA)
            # Prix typique entre 500,000 et 3,000,000 FCFA/tonne
            if record.currency_id.name == 'XOF':
                if record.prix_tonnage < 100000 or record.prix_tonnage > 5000000:
                    # Warning plutôt que blocage
                    pass  # Juste une vérification, pas de blocage
    
    @api.constrains('campaign_id', 'date_start', 'date_end')
    def _check_campaign_period(self):
        """Vérifie que les dates sont cohérentes avec la campagne"""
        for record in self:
            if record.campaign_id and record.date_start and record.date_end:
                campaign = record.campaign_id
                if campaign.date_start and campaign.date_end:
                    if record.date_start < campaign.date_start or record.date_end > campaign.date_end:
                        # Avertissement mais pas blocage car certaines CV peuvent déborder
                        pass
    
    # =========================================================================
    # MÉTHODES CRUD
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'potting.confirmation.vente'
                ) or _('Nouveau')
        return super().create(vals_list)
    
    def unlink(self):
        for record in self:
            if record.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les CV en brouillon ou annulées."
                ))
            if record.customer_order_ids:
                raise UserError(_(
                    "Cette CV est liée à des contrats. "
                    "Supprimez d'abord les contrats associés."
                ))
        return super().unlink()
    
    # =========================================================================
    # MÉTHODES D'ACTION
    # =========================================================================
    
    def action_activate(self):
        """Activer la Confirmation de Vente"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Seules les CV en brouillon peuvent être activées."))
            record.state = 'active'
    
    def action_consume(self):
        """Marquer la CV comme consommée (tonnage épuisé)"""
        for record in self:
            if record.state != 'active':
                raise UserError(_("Seules les CV actives peuvent être marquées comme consommées."))
            record.state = 'consumed'
    
    def action_expire(self):
        """Marquer la CV comme expirée"""
        for record in self:
            record.state = 'expired'
    
    def action_cancel(self):
        """Annuler la Confirmation de Vente"""
        for record in self:
            if record.customer_order_ids.filtered(lambda o: o.state not in ('draft', 'cancelled')):
                raise UserError(_(
                    "Impossible d'annuler cette CV. "
                    "Des contrats actifs y sont rattachés."
                ))
            record.state = 'cancelled'
    
    def action_draft(self):
        """Remettre en brouillon"""
        for record in self:
            if record.state == 'cancelled':
                record.state = 'draft'
    
    # =========================================================================
    # ACTIONS DE VUE
    # =========================================================================
    
    def action_view_customer_orders(self):
        """Afficher les contrats liés à cette CV"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'potting_management.action_potting_customer_order'
        )
        action['domain'] = [('confirmation_vente_ids', 'in', self.id)]
        action['context'] = {'default_confirmation_vente_ids': [(4, self.id)]}
        return action
    
    def action_view_formules(self):
        """Afficher les formules liées à cette CV"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'potting_management.action_potting_formule'
        )
        action['domain'] = [('confirmation_vente_id', '=', self.id)]
        action['context'] = {'default_confirmation_vente_id': self.id}
        return action
    
    def action_create_formule(self):
        """Créer une nouvelle formule pour cette CV"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle Formule'),
            'res_model': 'potting.formule',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_confirmation_vente_id': self.id,
                'default_campaign_id': self.campaign_id.id,
            }
        }
    
    # =========================================================================
    # CRON - VÉRIFICATION DES EXPIRATIONS
    # =========================================================================
    
    @api.model
    def _cron_check_expiration(self):
        """Vérifier et mettre à jour les CV expirées"""
        today = date.today()
        expired_cvs = self.search([
            ('state', '=', 'active'),
            ('date_end', '<', today)
        ])
        expired_cvs.write({'state': 'expired'})
        
        # Consommer les CV dont le tonnage est épuisé
        for cv in self.search([('state', '=', 'active')]):
            if cv.tonnage_restant <= 0:
                cv.write({'state': 'consumed'})
        
        return True
    
    # =========================================================================
    # MÉTHODES UTILITAIRES
    # =========================================================================
    
    def check_can_use_tonnage(self, tonnage):
        """Vérifie si le tonnage demandé est disponible"""
        self.ensure_one()
        if self.state != 'active':
            raise ValidationError(_(
                "La CV %s n'est pas active. État actuel: %s",
                self.name, dict(self._fields['state'].selection).get(self.state)
            ))
        if self.is_expired:
            raise ValidationError(_(
                "La CV %s a expiré le %s.",
                self.name, self.date_end
            ))
        if tonnage > self.tonnage_restant:
            raise ValidationError(_(
                "Tonnage insuffisant sur la CV %s. "
                "Demandé: %.2f T | Disponible: %.2f T",
                self.name, tonnage, self.tonnage_restant
            ))
        return True
    
    def get_cv_display_name(self):
        """Retourne un nom d'affichage enrichi pour la CV"""
        self.ensure_one()
        parts = [self.name]
        if self.reference_ccc:
            parts.append(f"(CCC: {self.reference_ccc})")
        if self.product_type and self.product_type != 'all':
            product_label = dict(self._fields['product_type'].selection).get(self.product_type)
            parts.append(f"- {product_label}")
        parts.append(f"- {self.tonnage_restant:.2f}T restants")
        return ' '.join(parts)
    
    def get_utilization_status(self):
        """Retourne le statut d'utilisation de la CV"""
        self.ensure_one()
        if self.tonnage_progress >= 100:
            return 'full', _("Tonnage épuisé")
        elif self.tonnage_progress >= 80:
            return 'warning', _("Tonnage presque épuisé (%.1f%%)" % self.tonnage_progress)
        elif self.tonnage_progress >= 50:
            return 'normal', _("Utilisation normale (%.1f%%)" % self.tonnage_progress)
        else:
            return 'available', _("Tonnage disponible (%.1f%%)" % self.tonnage_progress)
    
    def get_validity_status(self):
        """Retourne le statut de validité de la CV"""
        self.ensure_one()
        if self.is_expired:
            return 'expired', _("Expirée depuis le %s" % self.date_end)
        elif self.days_remaining <= 7:
            return 'critical', _("Expire dans %d jour(s)" % self.days_remaining)
        elif self.days_remaining <= 30:
            return 'warning', _("Expire dans %d jour(s)" % self.days_remaining)
        else:
            return 'valid', _("Valide jusqu'au %s" % self.date_end)
    
    # =========================================================================
    # MÉTHODES ONCHANGE
    # =========================================================================
    
    @api.onchange('campaign_id')
    def _onchange_campaign_id(self):
        """Met à jour les dates par défaut basées sur la campagne"""
        if self.campaign_id:
            if self.campaign_id.date_start and not self.date_start:
                self.date_start = self.campaign_id.date_start
            if self.campaign_id.date_end and not self.date_end:
                self.date_end = self.campaign_id.date_end
    
    @api.onchange('date_start')
    def _onchange_date_start(self):
        """Suggère une date de fin basée sur la date de début"""
        if self.date_start and not self.date_end:
            # Par défaut, validité de 3 mois
            from dateutil.relativedelta import relativedelta
            self.date_end = self.date_start + relativedelta(months=3)
    
    @api.onchange('tonnage_autorise')
    def _onchange_tonnage_autorise(self):
        """Avertit si le tonnage semble anormal"""
        if self.tonnage_autorise:
            if self.tonnage_autorise > 10000:
                return {
                    'warning': {
                        'title': _("Tonnage élevé"),
                        'message': _("Le tonnage autorisé (%.2f T) semble élevé. "
                                   "Veuillez vérifier la valeur." % self.tonnage_autorise)
                    }
                }
            elif self.tonnage_autorise < 10:
                return {
                    'warning': {
                        'title': _("Tonnage faible"),
                        'message': _("Le tonnage autorisé (%.2f T) semble faible. "
                                   "Veuillez vérifier la valeur." % self.tonnage_autorise)
                    }
                }
    
    # =========================================================================
    # ACTIONS SUPPLÉMENTAIRES
    # =========================================================================
    
    def action_duplicate_cv(self):
        """Dupliquer la CV avec un nouveau numéro"""
        self.ensure_one()
        default = {
            'name': _('Nouveau'),
            'reference_ccc': False,
            'state': 'draft',
            'customer_order_ids': False,
            'formule_ids': False,
        }
        new_cv = self.copy(default=default)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle CV'),
            'res_model': 'potting.confirmation.vente',
            'view_mode': 'form',
            'res_id': new_cv.id,
            'target': 'current',
        }
    
    def action_print_cv(self):
        """Imprimer le rapport de la CV"""
        self.ensure_one()
        return self.env.ref('potting_management.action_report_confirmation_vente').report_action(self)
    
    def action_extend_validity(self):
        """Étendre la validité de la CV (action rapide)"""
        self.ensure_one()
        if self.state not in ('active', 'expired'):
            raise UserError(_("Seules les CV actives ou expirées peuvent être prolongées."))
        from dateutil.relativedelta import relativedelta
        new_date_end = max(self.date_end, date.today()) + relativedelta(months=1)
        self.write({
            'date_end': new_date_end,
            'state': 'active',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("CV Prolongée"),
                'message': _("Validité prolongée jusqu'au %s" % new_date_end),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_transfer_wizard(self):
        """Ouvrir l'assistant de transfert de tonnage vers une autre CV
        
        Permet de transférer le tonnage restant d'une CV (expirée ou active)
        vers une nouvelle CV ou une CV existante d'une autre campagne.
        """
        self.ensure_one()
        if self.state not in ('active', 'expired'):
            raise UserError(_("Seules les CV actives ou expirées peuvent être transférées."))
        if self.tonnage_restant <= 0:
            raise UserError(_("Cette CV n'a plus de tonnage disponible à transférer."))
        
        return {
            'name': _('Transférer tonnage CV'),
            'type': 'ir.actions.act_window',
            'res_model': 'potting.cv.tonnage.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_cv_id': self.id,
                'default_tonnage_to_transfer': self.tonnage_restant,
                'default_prix_tonnage': self.prix_tonnage,
            }
        }

    @api.model
    def _cron_check_cv_expiration(self):
        """Cron job pour vérifier les CV qui arrivent à expiration
        
        Crée des activités pour les CV actives qui expirent dans les 7 prochains jours
        et qui ont encore du tonnage disponible.
        """
        from datetime import timedelta
        
        today = date.today()
        expiry_threshold = today + timedelta(days=7)
        
        cvs_expiring = self.search([
            ('date_end', '<=', expiry_threshold),
            ('date_end', '>=', today),
            ('state', '=', 'active'),
            ('tonnage_restant', '>', 0)
        ])
        
        activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False)
        if not activity_type:
            return
        
        for cv in cvs_expiring:
            # Vérifier si une activité existe déjà
            existing_activity = self.env['mail.activity'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', cv.id),
                ('activity_type_id', '=', activity_type.id),
                ('summary', 'ilike', 'Expiration')
            ], limit=1)
            
            if not existing_activity:
                cv.activity_schedule(
                    'mail.mail_activity_data_warning',
                    date_deadline=cv.date_end,
                    summary='⚠️ Expiration CV imminente',
                    note=f'La CV {cv.name} expire le {cv.date_end}. Tonnage restant: {cv.tonnage_restant} T.'
                )
