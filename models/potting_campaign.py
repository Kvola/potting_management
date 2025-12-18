# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class PottingCampaign(models.Model):
    """Campagne Café-Cacao.
    
    Gère les périodes de campagne café-cacao avec leurs prix officiels.
    Une campagne représente une période (généralement octobre à septembre)
    pendant laquelle les prix du cacao sont fixés.
    """
    _name = 'potting.campaign'
    _description = 'Campagne Café-Cacao'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'
    _rec_name = 'name'

    # SQL Constraints
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom de la campagne doit être unique!'),
        ('code_uniq', 'unique(code)', 'Le code de la campagne doit être unique!'),
    ]

    # =========================================================================
    # CHAMPS PRINCIPAUX
    # =========================================================================
    
    name = fields.Char(
        string="Nom de la campagne",
        compute='_compute_name',
        store=True,
        readonly=False,
        tracking=True,
        index=True,
        help="Nom de la campagne (ex: 2024-2025). Calculé automatiquement depuis les dates."
    )
    
    code = fields.Char(
        string="Code",
        compute='_compute_code',
        store=True,
        readonly=False,
        tracking=True,
        index=True,
        help="Code court de la campagne utilisé dans les numérotations (ex: 2425). Calculé automatiquement."
    )
    
    date_start = fields.Date(
        string="Date de début",
        required=True,
        tracking=True,
        help="Date de début de la campagne (généralement 1er octobre)"
    )
    
    date_end = fields.Date(
        string="Date de fin",
        required=True,
        tracking=True,
        help="Date de fin de la campagne (généralement 30 septembre)"
    )
    
    active = fields.Boolean(
        string="Actif",
        default=True,
        tracking=True
    )
    
    is_current = fields.Boolean(
        string="Campagne en cours",
        compute='_compute_is_current',
        store=True,
        help="Indique si c'est la campagne actuellement en cours"
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Active'),
        ('closed', 'Clôturée'),
    ], string="État", default='draft', tracking=True, index=True)

    # =========================================================================
    # PRIX OFFICIELS DU CACAO
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self._get_default_currency(),
        required=True,
        tracking=True,
        help="Devise utilisée pour les prix de cette campagne. Modifiable par l'utilisateur."
    )
    
    official_price_cocoa_mass = fields.Monetary(
        string="Prix officiel - Masse de cacao (€/T)",
        currency_field='currency_id',
        tracking=True,
        help="Prix officiel par tonne pour la Masse de cacao"
    )
    
    official_price_cocoa_butter = fields.Monetary(
        string="Prix officiel - Beurre de cacao (€/T)",
        currency_field='currency_id',
        tracking=True,
        help="Prix officiel par tonne pour le Beurre de cacao"
    )
    
    official_price_cocoa_cake = fields.Monetary(
        string="Prix officiel - Cake de cacao (€/T)",
        currency_field='currency_id',
        tracking=True,
        help="Prix officiel par tonne pour le Cake (Tourteau) de cacao"
    )
    
    official_price_cocoa_powder = fields.Monetary(
        string="Prix officiel - Poudre de cacao (€/T)",
        currency_field='currency_id',
        tracking=True,
        help="Prix officiel par tonne pour la Poudre de cacao"
    )
    
    # Prix générique (pour compatibilité)
    official_cocoa_price = fields.Monetary(
        string="Prix officiel général (€/T)",
        currency_field='currency_id',
        tracking=True,
        help="Prix officiel général du cacao (utilisé si pas de prix spécifique par produit)"
    )

    # =========================================================================
    # TAUX ET DROITS
    # =========================================================================
    
    export_duty_rate = fields.Float(
        string="Taux droits d'exportation (%)",
        default=14.6,
        tracking=True,
        help="Taux des droits d'exportation en pourcentage pour cette campagne"
    )

    # =========================================================================
    # STATISTIQUES
    # =========================================================================
    
    transit_order_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_statistics',
        store=True
    )
    
    total_tonnage = fields.Float(
        string="Tonnage total (T)",
        compute='_compute_statistics',
        store=True,
        digits='Product Unit of Measure'
    )
    
    total_amount = fields.Monetary(
        string="Montant total",
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id'
    )
    
    customer_order_count = fields.Integer(
        string="Nombre de commandes",
        compute='_compute_statistics',
        store=True
    )

    # =========================================================================
    # NOTES
    # =========================================================================
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
        index=True
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        """Calcule le nom de la campagne à partir des dates.
        
        Format: YYYY1-YYYY2 où YYYY1 est l'année de début et YYYY2 l'année de fin.
        Ex: 2024-2025 pour une campagne du 01/10/2024 au 30/09/2025
        """
        for campaign in self:
            if campaign.date_start and campaign.date_end:
                year_start = campaign.date_start.year
                year_end = campaign.date_end.year
                campaign.name = f"{year_start}-{year_end}"
            elif campaign.date_start:
                campaign.name = f"{campaign.date_start.year}-{campaign.date_start.year + 1}"
            else:
                campaign.name = False
    
    @api.depends('date_start', 'date_end')
    def _compute_code(self):
        """Calcule le code court de la campagne à partir des dates.
        
        Format: YY1YY2 où YY1 sont les 2 derniers chiffres de l'année de début
        et YY2 les 2 derniers chiffres de l'année de fin.
        Ex: 2425 pour une campagne 2024-2025
        """
        for campaign in self:
            if campaign.date_start and campaign.date_end:
                year_start = campaign.date_start.year % 100
                year_end = campaign.date_end.year % 100
                campaign.code = f"{year_start:02d}{year_end:02d}"
            elif campaign.date_start:
                year_start = campaign.date_start.year % 100
                year_end = (campaign.date_start.year + 1) % 100
                campaign.code = f"{year_start:02d}{year_end:02d}"
            else:
                campaign.code = False
    
    @api.depends('date_start', 'date_end')
    def _compute_is_current(self):
        """Détermine si la campagne est actuellement en cours."""
        today = fields.Date.context_today(self)
        for campaign in self:
            if campaign.date_start and campaign.date_end:
                campaign.is_current = campaign.date_start <= today <= campaign.date_end
            else:
                campaign.is_current = False

    @api.depends('name')
    def _compute_statistics(self):
        """Calcule les statistiques de la campagne."""
        for campaign in self:
            # Rechercher les OT de cette campagne
            transit_orders = self.env['potting.transit.order'].search([
                ('campaign_period', '=', campaign.name)
            ])
            
            campaign.transit_order_count = len(transit_orders)
            campaign.total_tonnage = sum(transit_orders.mapped('current_tonnage'))
            campaign.total_amount = sum(transit_orders.mapped('total_amount'))
            
            # Rechercher les commandes de cette campagne
            customer_orders = self.env['potting.customer.order'].search([
                ('campaign_period', '=', campaign.name)
            ])
            campaign.customer_order_count = len(customer_orders)

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Vérifie que la date de fin est après la date de début."""
        for campaign in self:
            if campaign.date_start and campaign.date_end:
                if campaign.date_end <= campaign.date_start:
                    raise ValidationError(_(
                        "La date de fin doit être postérieure à la date de début."
                    ))

    @api.constrains('export_duty_rate')
    def _check_export_duty_rate(self):
        """Vérifie que le taux est valide."""
        for campaign in self:
            if campaign.export_duty_rate < 0 or campaign.export_duty_rate > 100:
                raise ValidationError(_(
                    "Le taux des droits d'exportation doit être compris entre 0 et 100%%."
                ))

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('name')
    def _onchange_name(self):
        """Génère automatiquement le code à partir du nom."""
        if self.name and not self.code:
            # Format attendu: "2024-2025" -> "2425"
            parts = self.name.split('-')
            if len(parts) == 2:
                try:
                    year1 = int(parts[0]) % 100
                    year2 = int(parts[1]) % 100
                    self.code = f"{year1:02d}{year2:02d}"
                except (ValueError, TypeError):
                    pass

    @api.onchange('date_start')
    def _onchange_date_start(self):
        """Génère automatiquement le nom et la date de fin."""
        if self.date_start:
            year = self.date_start.year
            # Si la date est après octobre, la campagne va jusqu'à l'année suivante
            if self.date_start.month >= 10:
                self.name = f"{year}-{year + 1}"
                self.date_end = date(year + 1, 9, 30)
            else:
                self.name = f"{year - 1}-{year}"
                self.date_end = date(year, 9, 30)

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_activate(self):
        """Active la campagne."""
        for campaign in self:
            if campaign.state == 'closed':
                raise UserError(_("Une campagne clôturée ne peut pas être réactivée."))
            campaign.state = 'active'
            campaign.message_post(body=_("✅ Campagne activée."))

    def action_close(self):
        """Clôture la campagne."""
        for campaign in self:
            campaign.state = 'closed'
            campaign.message_post(body=_("🔒 Campagne clôturée."))

    def action_draft(self):
        """Remet la campagne en brouillon."""
        for campaign in self:
            if campaign.state == 'closed':
                raise UserError(_("Une campagne clôturée ne peut pas être remise en brouillon."))
            campaign.state = 'draft'

    def action_view_transit_orders(self):
        """Affiche les OT de cette campagne."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('OT - Campagne %s') % self.name,
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,kanban,form',
            'domain': [('campaign_period', '=', self.name)],
            'context': {'default_campaign_period': self.name},
        }

    def action_view_customer_orders(self):
        """Affiche les commandes de cette campagne."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commandes - Campagne %s') % self.name,
            'res_model': 'potting.customer.order',
            'view_mode': 'tree,kanban,form',
            'domain': [('campaign_period', '=', self.name)],
            'context': {'default_campaign_period': self.name},
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def get_price_for_product(self, product_type):
        """Retourne le prix officiel pour un type de produit.
        
        Args:
            product_type: 'cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder'
        
        Returns:
            float: Prix officiel pour ce produit, ou prix général si non défini
        """
        self.ensure_one()
        
        price_map = {
            'cocoa_mass': self.official_price_cocoa_mass,
            'cocoa_butter': self.official_price_cocoa_butter,
            'cocoa_cake': self.official_price_cocoa_cake,
            'cocoa_powder': self.official_price_cocoa_powder,
        }
        
        specific_price = price_map.get(product_type, 0)
        return specific_price if specific_price else self.official_cocoa_price

    @api.model
    def _get_default_currency(self):
        """Get the default currency for the potting module.
        
        Returns the configured default currency if set, otherwise falls back
        to the company currency.
        
        Returns:
            res.currency: The default currency record
        """
        return self.env['res.config.settings'].get_default_currency()

    @api.model
    def get_current_campaign(self):
        """Retourne la campagne actuellement active.
        
        Returns:
            potting.campaign: La campagne en cours, ou False si aucune
        """
        today = fields.Date.context_today(self)
        campaign = self.search([
            ('date_start', '<=', today),
            ('date_end', '>=', today),
            ('state', '=', 'active'),
        ], limit=1)
        
        if not campaign:
            # Fallback: chercher la dernière campagne active
            campaign = self.search([
                ('state', '=', 'active'),
            ], order='date_start desc', limit=1)
        
        return campaign

    @api.model
    def get_campaign_by_name(self, name):
        """Retourne une campagne par son nom.
        
        Args:
            name: Nom de la campagne (ex: '2024-2025')
        
        Returns:
            potting.campaign: La campagne trouvée, ou False
        """
        return self.search([('name', '=', name)], limit=1)

    @api.model
    def create_campaign_for_year(self, year):
        """Crée une nouvelle campagne pour une année donnée.
        
        Args:
            year: Année de début de la campagne (ex: 2024 pour 2024-2025)
        
        Returns:
            potting.campaign: La campagne créée
        """
        name = f"{year}-{year + 1}"
        existing = self.search([('name', '=', name)], limit=1)
        if existing:
            return existing
        
        return self.create({
            'name': name,
            'code': f"{year % 100:02d}{(year + 1) % 100:02d}",
            'date_start': date(year, 10, 1),
            'date_end': date(year + 1, 9, 30),
            'state': 'draft',
        })
