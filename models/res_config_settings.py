# -*- coding: utf-8 -*-

import logging
import ast

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    """Configuration settings for the Potting Management module.
    
    This model extends Odoo's configuration settings to provide:
    - Default customer selection for new orders
    - Maximum tonnage limits per product type
    - Default CC recipients for reports
    - Container type configurations
    """
    _inherit = 'res.config.settings'

    # =========================================================================
    # DEFAULT CUSTOMER
    # =========================================================================
    
    potting_default_customer_id = fields.Many2one(
        'res.partner',
        string="Client par défaut",
        config_parameter='potting_management.default_customer_id',
        domain="[('is_company', '=', True)]",
        help="Client qui sera sélectionné par défaut lors de la création d'une commande"
    )
    
    # =========================================================================
    # SHIPPING USER OPTIONS
    # =========================================================================
    
    potting_enable_generate_ot_from_order = fields.Boolean(
        string="Activer la génération d'OT depuis les commandes",
        config_parameter='potting_management.enable_generate_ot_from_order',
        default=True,
        help="Permet aux utilisateurs Shipping de générer automatiquement des OT "
             "depuis une commande client en fonction du tonnage total."
    )

    # =========================================================================
    # DEFAULT OT TONNAGE BY PRODUCT TYPE
    # =========================================================================
    
    potting_default_ot_tonnage_cocoa_mass = fields.Float(
        string="Tonnage OT par défaut - Masse de cacao (T)",
        config_parameter='potting_management.default_ot_tonnage_cocoa_mass',
        default=22.0,
        help="Tonnage par défaut pour un OT de Masse de cacao lors de la génération automatique"
    )
    
    potting_default_ot_tonnage_cocoa_butter = fields.Float(
        string="Tonnage OT par défaut - Beurre de cacao (T)",
        config_parameter='potting_management.default_ot_tonnage_cocoa_butter',
        default=22.0,
        help="Tonnage par défaut pour un OT de Beurre de cacao lors de la génération automatique"
    )
    
    potting_default_ot_tonnage_cocoa_cake = fields.Float(
        string="Tonnage OT par défaut - Cake de cacao (T)",
        config_parameter='potting_management.default_ot_tonnage_cocoa_cake',
        default=20.0,
        help="Tonnage par défaut pour un OT de Cake (Tourteau) de cacao lors de la génération automatique"
    )
    
    potting_default_ot_tonnage_cocoa_powder = fields.Float(
        string="Tonnage OT par défaut - Poudre de cacao (T)",
        config_parameter='potting_management.default_ot_tonnage_cocoa_powder',
        default=22.5,
        help="Tonnage par défaut pour un OT de Poudre de cacao lors de la génération automatique"
    )

    # =========================================================================
    # MAXIMUM TONNAGE PER LOT BY PRODUCT TYPE
    # =========================================================================
    
    potting_max_tonnage_cocoa_mass = fields.Float(
        string="Tonnage max - Masse de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_mass',
        default=25.0,
        help="Tonnage maximum par lot pour la Masse de cacao (22 tonnes standard)"
    )

    potting_max_tonnage_cocoa_mass_alt = fields.Float(
        string="Tonnage max alternatif - Masse de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_mass_alt',
        default=20.0,
        help="Tonnage maximum alternatif par lot pour la Masse de cacao"
    )

    potting_max_tonnage_cocoa_butter = fields.Float(
        string="Tonnage max - Beurre de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_butter',
        default=22.0,
        help="Tonnage maximum par lot pour le Beurre de cacao"
    )

    potting_max_tonnage_cocoa_cake = fields.Float(
        string="Tonnage max - Cake de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_cake',
        default=20.0,
        help="Tonnage maximum par lot pour le Cake (Tourteau) de cacao"
    )

    potting_max_tonnage_cocoa_powder = fields.Float(
        string="Tonnage max - Poudre de cacao (T)",
        config_parameter='potting_management.max_tonnage_cocoa_powder',
        default=22.5,
        help="Tonnage maximum par lot pour la Poudre de cacao"
    )

    # =========================================================================
    # PRODUCTION CONFIGURATION
    # =========================================================================
    
    potting_max_daily_production = fields.Float(
        string="Production max par ligne (T)",
        config_parameter='potting_management.max_daily_production',
        default=10.0,
        help="Tonnage maximum autorisé par ligne de production. "
             "Cette valeur limite le tonnage qu'un opérateur peut saisir pour une seule ligne de production."
    )

    # =========================================================================
    # CONTAINER CONFIGURATION
    # =========================================================================
    
    potting_container_20_capacity = fields.Float(
        string="Capacité conteneur 20' (T)",
        config_parameter='potting_management.container_20_capacity',
        default=22.0,
        help="Capacité maximale en tonnes pour un conteneur 20 pieds"
    )
    
    potting_container_40_capacity = fields.Float(
        string="Capacité conteneur 40' (T)",
        config_parameter='potting_management.container_40_capacity',
        default=27.0,
        help="Capacité maximale en tonnes pour un conteneur 40 pieds"
    )
    
    potting_container_40hc_capacity = fields.Float(
        string="Capacité conteneur 40' HC (T)",
        config_parameter='potting_management.container_40hc_capacity',
        default=27.0,
        help="Capacité maximale en tonnes pour un conteneur 40 pieds High Cube"
    )

    # =========================================================================
    # DEFAULT CC RECIPIENTS FOR REPORTS
    # =========================================================================
    
    potting_default_cc_partner_ids = fields.Many2many(
        'res.partner',
        string="Destinataires en copie par défaut",
        domain="[('email', '!=', False)]",
        help="Liste des personnes à mettre en copie par défaut lors de l'envoi des rapports"
    )
    
    # =========================================================================
    # NOTIFICATION SETTINGS
    # =========================================================================
    
    potting_notify_on_ot_confirm = fields.Boolean(
        string="Notifier à la confirmation OT",
        config_parameter='potting_management.notify_on_ot_confirm',
        default=True,
        help="Envoyer une notification lors de la confirmation d'un Ordre de Transit"
    )
    
    potting_notify_on_container_sealed = fields.Boolean(
        string="Notifier au scellage du conteneur",
        config_parameter='potting_management.notify_on_container_sealed',
        default=True,
        help="Envoyer une notification lorsqu'un conteneur est scellé"
    )
    
    # =========================================================================
    # CAMPAIGN CONFIGURATION (Campagne Café-Cacao)
    # =========================================================================
    
    potting_campaign_year = fields.Char(
        string="Période campagne",
        config_parameter='potting_management.campaign_year',
        default='2025-2026',
        help="Période de la campagne Café-Cacao au format AAAA-AAAA (ex: 2025-2026). "
             "Utilisé dans la numérotation des OT."
    )

    # =========================================================================
    # SEQUENCE CONFIGURATION
    # =========================================================================
    
    potting_ot_initial_number = fields.Integer(
        string="Numéro OT initial",
        config_parameter='potting_management.ot_initial_number',
        default=1,
        help="Numéro de départ pour la numérotation des OT. "
             "Les nouveaux OT seront numérotés à partir de ce numéro."
    )
    
    potting_lot_initial_number = fields.Integer(
        string="Numéro lot initial",
        config_parameter='potting_management.lot_initial_number',
        default=10001,
        help="Numéro à partir duquel commence la numérotation automatique des lots. "
             "Ce paramètre met à jour la séquence des lots lorsqu'il est modifié."
    )

    # =========================================================================
    # LOT PREFIX PER PRODUCT TYPE
    # =========================================================================
    
    potting_lot_prefix_cocoa_mass = fields.Char(
        string="Préfixe lot - Masse de cacao",
        config_parameter='potting_management.lot_prefix_cocoa_mass',
        default='M0',
        help="Préfixe pour les numéros de lot de Masse de cacao (ex: M10001)"
    )
    
    potting_lot_prefix_cocoa_butter = fields.Char(
        string="Préfixe lot - Beurre de cacao",
        config_parameter='potting_management.lot_prefix_cocoa_butter',
        default='B0',
        help="Préfixe pour les numéros de lot de Beurre de cacao (ex: B10001)"
    )
    
    potting_lot_prefix_cocoa_cake = fields.Char(
        string="Préfixe lot - Cake de cacao",
        config_parameter='potting_management.lot_prefix_cocoa_cake',
        default='T0',
        help="Préfixe pour les numéros de lot de Cake/Tourteau de cacao (ex: T10001)"
    )
    
    potting_lot_prefix_cocoa_powder = fields.Char(
        string="Préfixe lot - Poudre de cacao",
        config_parameter='potting_management.lot_prefix_cocoa_powder',
        default='P0',
        help="Préfixe pour les numéros de lot de Poudre de cacao (ex: P10001)"
    )

    # =========================================================================
    # COMPUTED INFO FIELDS
    # =========================================================================
    
    potting_stats_total_ot = fields.Integer(
        compute='_compute_potting_stats',
        string="Total OT"
    )
    
    potting_stats_total_lots = fields.Integer(
        compute='_compute_potting_stats',
        string="Total Lots"
    )
    
    potting_stats_total_tonnage = fields.Float(
        compute='_compute_potting_stats',
        string="Tonnage Total"
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends_context('uid')
    def _compute_potting_stats(self):
        """Calcule les statistiques globales du module."""
        for record in self:
            try:
                record.potting_stats_total_ot = self.env['potting.transit.order'].search_count([])
                record.potting_stats_total_lots = self.env['potting.lot'].search_count([])
                
                lots = self.env['potting.lot'].search([])
                record.potting_stats_total_tonnage = sum(lots.mapped('tonnage'))
            except Exception as e:
                _logger.warning("Erreur calcul statistiques: %s", e)
                record.potting_stats_total_ot = 0
                record.potting_stats_total_lots = 0
                record.potting_stats_total_tonnage = 0.0

    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    
    @api.constrains('potting_max_tonnage_cocoa_mass', 'potting_max_tonnage_cocoa_butter',
                    'potting_max_tonnage_cocoa_cake', 'potting_max_tonnage_cocoa_powder',
                    'potting_max_tonnage_cocoa_mass_alt')
    def _check_tonnage_values(self):
        """Vérifie que les valeurs de tonnage sont positives et raisonnables."""
        for record in self:
            tonnage_fields = [
                ('potting_max_tonnage_cocoa_mass', "Masse de cacao"),
                ('potting_max_tonnage_cocoa_mass_alt', "Masse de cacao (alt)"),
                ('potting_max_tonnage_cocoa_butter', "Beurre de cacao"),
                ('potting_max_tonnage_cocoa_cake', "Cake de cacao"),
                ('potting_max_tonnage_cocoa_powder', "Poudre de cacao"),
            ]
            
            for field_name, label in tonnage_fields:
                value = getattr(record, field_name, 0)
                if value is not None and value <= 0:
                    raise ValidationError(_(
                        "Le tonnage maximum pour '%s' doit être supérieur à zéro."
                    ) % label)
                if value is not None and value > 50:
                    raise ValidationError(_(
                        "Le tonnage maximum pour '%s' semble trop élevé (%.2f T). "
                        "Maximum recommandé: 50 T."
                    ) % (label, value))
    
    @api.constrains('potting_container_20_capacity', 'potting_container_40_capacity',
                    'potting_container_40hc_capacity')
    def _check_container_capacities(self):
        """Vérifie que les capacités de conteneur sont valides."""
        for record in self:
            if record.potting_container_20_capacity and record.potting_container_20_capacity > 25:
                raise ValidationError(_(
                    "La capacité d'un conteneur 20' ne peut pas dépasser 25 T."
                ))
            if record.potting_container_40_capacity and record.potting_container_40_capacity > 30:
                raise ValidationError(_(
                    "La capacité d'un conteneur 40' ne peut pas dépasser 30 T."
                ))
            if record.potting_container_40hc_capacity and record.potting_container_40hc_capacity > 30:
                raise ValidationError(_(
                    "La capacité d'un conteneur 40' HC ne peut pas dépasser 30 T."
                ))

    # =========================================================================
    # GET/SET VALUES
    # =========================================================================

    @api.model
    def get_values(self):
        """Récupère les valeurs des paramètres de configuration."""
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Get CC partners from config parameter
        cc_partner_ids = self._safe_get_partner_ids(
            ICP.get_param('potting_management.default_cc_partner_ids', '[]')
        )
        
        # Get current lot sequence number
        lot_sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', 'potting.lot')
        ], limit=1)
        current_lot_number = lot_sequence.number_next_actual if lot_sequence else 10001
        
        res.update(
            potting_default_cc_partner_ids=[(6, 0, cc_partner_ids)],
            potting_lot_initial_number=current_lot_number,
        )
        return res

    def set_values(self):
        """Enregistre les valeurs des paramètres de configuration."""
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Save CC partners as string list
        ICP.set_param(
            'potting_management.default_cc_partner_ids',
            str(self.potting_default_cc_partner_ids.ids)
        )
        
        # Update lot sequence if initial number changed
        if self.potting_lot_initial_number:
            self._update_lot_sequence_number(self.potting_lot_initial_number)
        
        _logger.info(
            "Configuration Potting Management mise à jour par %s",
            self.env.user.name
        )
    
    def _update_lot_sequence_number(self, new_number):
        """Met à jour le numéro suivant de la séquence des lots.
        
        Args:
            new_number: Le nouveau numéro à utiliser pour le prochain lot
        """
        if not new_number or new_number <= 0:
            return
        
        # Find the lot sequence
        lot_sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', 'potting.lot')
        ], limit=1)
        
        if lot_sequence:
            lot_sequence.write({
                'number_next': new_number
            })
            _logger.info(
                "Séquence des lots mise à jour: prochain numéro = %s",
                new_number
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _safe_get_partner_ids(self, param_value):
        """Parse safely a string representation of partner IDs list."""
        try:
            partner_ids = ast.literal_eval(param_value) if param_value else []
            if isinstance(partner_ids, list):
                # Vérifier que les partenaires existent toujours
                existing_partners = self.env['res.partner'].sudo().browse(partner_ids).exists()
                return existing_partners.ids
        except (ValueError, SyntaxError) as e:
            _logger.warning(
                "Erreur parsing partenaires CC: %s (valeur: %s)", 
                e, param_value
            )
        return []

    @api.model
    def get_max_tonnage_for_product(self, product_type):
        """Get the maximum tonnage for a given product type.
        
        Args:
            product_type: One of 'cocoa_mass', 'cocoa_butter', 'cocoa_cake', 
                         'cocoa_powder'
        
        Returns:
            float: Maximum tonnage for the product type, or default 25.0
        """
        if not product_type:
            _logger.warning("get_max_tonnage_for_product called without product_type")
            return 25.0
        
        ICP = self.env['ir.config_parameter'].sudo()
        
        tonnage_map = {
            'cocoa_mass': 'potting_management.max_tonnage_cocoa_mass',
            'cocoa_butter': 'potting_management.max_tonnage_cocoa_butter',
            'cocoa_cake': 'potting_management.max_tonnage_cocoa_cake',
            'cocoa_powder': 'potting_management.max_tonnage_cocoa_powder',
        }
        
        default_values = {
            'cocoa_mass': 25.0,
            'cocoa_butter': 22.0,
            'cocoa_cake': 25.0,
            'cocoa_powder': 22.5,
        }
        
        param_key = tonnage_map.get(product_type)
        default_value = default_values.get(product_type, 25.0)
        
        if not param_key:
            _logger.warning(
                "Type de produit inconnu pour tonnage max: %s", 
                product_type
            )
            return default_value
        
        try:
            return float(ICP.get_param(param_key, str(default_value)))
        except (ValueError, TypeError) as e:
            _logger.error(
                "Erreur conversion tonnage pour %s: %s", 
                product_type, e
            )
            return default_value
    
    @api.model
    def get_container_capacity(self, container_type):
        """Get the maximum capacity for a container type.
        
        Args:
            container_type: One of '20', '40', '40hc'
        
        Returns:
            float: Maximum capacity in tonnes
        """
        ICP = self.env['ir.config_parameter'].sudo()
        
        capacity_map = {
            '20': ('potting_management.container_20_capacity', 22.0),
            '40': ('potting_management.container_40_capacity', 27.0),
            '40hc': ('potting_management.container_40hc_capacity', 27.0),
        }
        
        if container_type not in capacity_map:
            _logger.warning("Type de conteneur inconnu: %s", container_type)
            return 22.0
        
        param_key, default_value = capacity_map[container_type]
        
        try:
            return float(ICP.get_param(param_key, str(default_value)))
        except (ValueError, TypeError) as e:
            _logger.error(
                "Erreur conversion capacité pour conteneur %s: %s",
                container_type, e
            )
            return default_value

    @api.model
    def get_lot_prefix_for_product(self, product_type):
        """Get the lot prefix for a given product type.
        
        Args:
            product_type: One of 'cocoa_mass', 'cocoa_butter', 'cocoa_cake', 
                         'cocoa_powder'
        
        Returns:
            str: Prefix for the product type (M, B, T, P)
        """
        if not product_type:
            _logger.warning("get_lot_prefix_for_product called without product_type")
            return 'X'
        
        ICP = self.env['ir.config_parameter'].sudo()
        
        prefix_map = {
            'cocoa_mass': 'potting_management.lot_prefix_cocoa_mass',
            'cocoa_butter': 'potting_management.lot_prefix_cocoa_butter',
            'cocoa_cake': 'potting_management.lot_prefix_cocoa_cake',
            'cocoa_powder': 'potting_management.lot_prefix_cocoa_powder',
        }
        
        default_prefixes = {
            'cocoa_mass': 'M',      # Masse
            'cocoa_butter': 'B',    # Beurre
            'cocoa_cake': 'T',      # Tourteau (Cake)
            'cocoa_powder': 'P',    # Poudre
        }
        
        param_key = prefix_map.get(product_type)
        default_value = default_prefixes.get(product_type, 'X')
        
        if not param_key:
            _logger.warning(
                "Type de produit inconnu pour préfixe lot: %s", 
                product_type
            )
            return default_value
        
        return ICP.get_param(param_key, default_value) or default_value

    @api.model
    def get_ot_prefix_for_product(self, product_type):
        """Get the OT prefix code for a given product type.
        
        Args:
            product_type: One of 'cocoa_mass', 'cocoa_butter', 'cocoa_cake', 
                         'cocoa_powder'
        
        Returns:
            str: Code for the product type used in OT numbering
        """
        product_codes = {
            'cocoa_mass': 'MA',      # Masse
            'cocoa_butter': 'BE',    # Beurre
            'cocoa_cake': 'TO',      # Tourteau (Cake)
            'cocoa_powder': 'PO',    # Poudre
        }
        return product_codes.get(product_type, 'XX')

    @api.model
    def get_campaign_year(self):
        """Get the current campaign year.
        
        Returns:
            str: Campaign year in format AABB (e.g., '2425' for 2024-2025)
        """
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param('potting_management.campaign_year', '2425') or '2425'

    @api.model
    def get_default_cc_partners(self):
        """Get the default CC partners for reports.
        
        Returns:
            res.partner recordset: Partners to CC on reports
        """
        ICP = self.env['ir.config_parameter'].sudo()
        cc_partner_ids_str = ICP.get_param(
            'potting_management.default_cc_partner_ids', '[]'
        )
        
        partner_ids = self._safe_get_partner_ids(cc_partner_ids_str)
        return self.env['res.partner'].sudo().browse(partner_ids)

    @api.model
    def get_ot_initial_number(self):
        """Get the initial OT number from settings.
        
        Returns:
            int: The initial OT number (default 1)
        """
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            return int(ICP.get_param('potting_management.ot_initial_number', '1'))
        except (ValueError, TypeError):
            return 1

    @api.model
    def get_next_ot_number_for_product(self, product_type, campaign_period=None):
        """Get the next OT number for a specific product type and campaign.
        
        Args:
            product_type: One of 'cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder'
            campaign_period: The campaign period (e.g., '2025-2026'). If None, uses default.
        
        Returns:
            int: The next OT number to use for this product type and campaign
        """
        import re
        
        campaign_year = campaign_period or self.get_campaign_year()
        product_code = self.get_ot_prefix_for_product(product_type)
        
        # Récupérer le numéro initial configuré
        initial_number = self.get_ot_initial_number()
        
        # Chercher le plus grand numéro OT existant pour ce type de produit et cette campagne
        # Format attendu: NNNN/AAAA-AAAA-XX (ex: 3734/2025-2026-MA)
        # Pattern pour trouver tous les OT de cette campagne et ce produit
        search_pattern = f"/{campaign_year}-{product_code}"
        
        existing_ots = self.env['potting.transit.order'].sudo().search([
            ('name', 'like', search_pattern)
        ], order='name desc', limit=100)
        
        max_number = 0
        for ot in existing_ots:
            if ot.name and search_pattern in ot.name:
                # Extraire le numéro au début (ex: "3734/2025-2026-MA" -> 3734)
                match = re.search(r'^(\d+)/', ot.name)
                if match:
                    try:
                        num = int(match.group(1))
                        if num > max_number:
                            max_number = num
                    except (ValueError, TypeError):
                        pass
        
        # Si aucun OT n'existe, utiliser le numéro initial, sinon incrémenter le max
        if max_number == 0:
            return initial_number
        return max_number + 1

    @api.model
    def generate_ot_name(self, product_type=None, campaign_period=None, customer_ref=None):
        """Generate the next OT name based on campaign year and product type.
        
        Args:
            product_type: One of 'cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder'
            campaign_period: The campaign period (e.g., '2025-2026'). If None, uses default.
            customer_ref: The customer reference (e.g., 'CLI001'). If provided, will be prefixed.
        
        Returns:
            str: The complete OT name (e.g., "CLI001-3734/2025-2026-MA" or "3734/2025-2026-MA")
        """
        if not product_type:
            # Fallback: generate a generic OT name
            import time
            base_name = f"{int(time.time()) % 100000}"
            if customer_ref:
                return f"{customer_ref}-{base_name}"
            return base_name
        
        campaign_year = campaign_period or self.get_campaign_year()
        product_code = self.get_ot_prefix_for_product(product_type)
        next_number = self.get_next_ot_number_for_product(product_type, campaign_year)
        
        # Format: [REF-]NNNN/AAAA-AAAA-XX (ex: CLI001-3734/2025-2026-MA ou 3734/2025-2026-MA)
        base_ot_name = f"{next_number}/{campaign_year}-{product_code}"
        if customer_ref:
            return f"{customer_ref}-{base_ot_name}"
        return base_ot_name
    
    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_reset_default_tonnages(self):
        """Réinitialise les tonnages aux valeurs par défaut."""
        self.ensure_one()
        
        self.potting_max_tonnage_cocoa_mass = 25.0
        self.potting_max_tonnage_cocoa_mass_alt = 20.0
        self.potting_max_tonnage_cocoa_butter = 22.0
        self.potting_max_tonnage_cocoa_cake = 25.0
        self.potting_max_tonnage_cocoa_powder = 22.5
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("✅ Valeurs réinitialisées"),
                'message': _("Les tonnages ont été réinitialisés aux valeurs par défaut."),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_view_all_transit_orders(self):
        """Ouvre la liste de tous les ordres de transit."""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tous les Ordres de Transit"),
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,form,kanban',
            'target': 'current',
        }
    
    def action_view_all_lots(self):
        """Ouvre la liste de tous les lots."""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tous les Lots"),
            'res_model': 'potting.lot',
            'view_mode': 'tree,form,kanban',
            'target': 'current',
        }