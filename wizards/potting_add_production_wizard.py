# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingAddProductionWizard(models.TransientModel):
    """
    Wizard amélioré pour ajouter une production à un lot.
    Interface utilisateur optimisée pour les agents d'exportation (CEO Agent).
    """
    _name = 'potting.add.production.wizard'
    _description = 'Ajouter une production'

    # =========================================================================
    # CHAMPS PRINCIPAUX
    # =========================================================================
    lot_id = fields.Many2one(
        'potting.lot',
        string="Lot",
        required=True,
        domain="[('is_full', '=', False), ('state', 'in', ['draft', 'in_production'])]",
        help="Sélectionnez un lot qui n'est pas encore rempli"
    )
    
    date = fields.Date(
        string="Date de production",
        required=True,
        default=fields.Date.context_today,
    )
    
    units_produced = fields.Integer(
        string="Unités produites",
        required=True,
        default=1,
        help="Nombre d'unités de conditionnement produites"
    )
    
    shift = fields.Selection([
        ('morning', '🌅 Matin (6h-14h)'),
        ('afternoon', '☀️ Après-midi (14h-22h)'),
        ('night', '🌙 Nuit (22h-6h)'),
    ], string="Équipe", default='morning', required=True)
    
    operator_id = fields.Many2one(
        'res.users',
        string="Opérateur",
        default=lambda self: self.env.user,
    )
    
    note = fields.Text(string="Notes")
    
    # =========================================================================
    # CHAMPS INFORMATIFS (COMPUTED)
    # =========================================================================
    lot_info_html = fields.Html(
        string="Informations du lot",
        compute='_compute_lot_info',
        sanitize=False
    )
    
    transit_order_id = fields.Many2one(
        related='lot_id.transit_order_id',
        string="Ordre de Transit",
    )
    
    customer_order_id = fields.Many2one(
        related='lot_id.customer_order_id',
        string="Commande client",
    )
    
    product_type = fields.Selection(
        related='lot_id.product_type',
        string="Type de produit",
    )
    
    product_type_display = fields.Char(
        string="Type de produit",
        compute='_compute_product_type_display'
    )
    
    packaging_unit_name = fields.Char(
        related='lot_id.packaging_unit_name',
        string="Unité"
    )
    
    packaging_unit_weight = fields.Float(
        related='lot_id.packaging_unit_weight',
        string="Poids unitaire (T)"
    )
    
    packaging_unit_weight_kg = fields.Float(
        related='lot_id.packaging_unit_weight_kg',
        string="Poids unitaire (kg)"
    )
    
    # Capacité du lot
    target_tonnage = fields.Float(
        related='lot_id.target_tonnage',
        string="Tonnage cible"
    )
    
    current_tonnage = fields.Float(
        related='lot_id.current_tonnage',
        string="Tonnage actuel"
    )
    
    remaining_tonnage = fields.Float(
        related='lot_id.remaining_tonnage',
        string="Restant (T)"
    )
    
    fill_percentage = fields.Float(
        related='lot_id.fill_percentage',
        string="Remplissage (%)"
    )
    
    remaining_units = fields.Integer(
        related='lot_id.remaining_units',
        string="Unités restantes"
    )
    
    # Tonnage calculé pour cette production
    production_tonnage = fields.Float(
        string="Tonnage de cette production (T)",
        compute='_compute_production_tonnage',
        digits='Product Unit of Measure'
    )
    
    production_tonnage_kg = fields.Float(
        string="Poids (kg)",
        compute='_compute_production_tonnage',
        digits=(10, 2)
    )
    
    # Nouveau remplissage après production
    new_fill_percentage = fields.Float(
        string="Remplissage après (%)",
        compute='_compute_production_tonnage'
    )
    
    new_tonnage = fields.Float(
        string="Nouveau tonnage (T)",
        compute='_compute_production_tonnage'
    )
    
    will_exceed_capacity = fields.Boolean(
        string="Dépassera la capacité",
        compute='_compute_production_tonnage'
    )
    
    can_confirm = fields.Boolean(
        string="Peut confirmer",
        compute='_compute_can_confirm'
    )
    
    warning_message = fields.Char(
        string="Avertissement",
        compute='_compute_warning_message'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    @api.depends('lot_id')
    def _compute_lot_info(self):
        """Génère un résumé HTML des informations du lot"""
        for wizard in self:
            if wizard.lot_id:
                lot = wizard.lot_id
                fill_color = '#28a745' if lot.fill_percentage < 90 else '#ffc107' if lot.fill_percentage < 100 else '#dc3545'
                
                wizard.lot_info_html = f"""
                <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="font-size: 1.2em; font-weight: bold; color: #495057;">
                            📦 {lot.name}
                        </span>
                        <span style="background: {fill_color}; color: white; padding: 3px 10px; border-radius: 15px; font-weight: bold;">
                            {lot.fill_percentage:.1f}%
                        </span>
                    </div>
                    <div style="background: #e9ecef; border-radius: 4px; height: 20px; overflow: hidden; margin-bottom: 10px;">
                        <div style="background: linear-gradient(90deg, {fill_color}, {fill_color}); width: {min(lot.fill_percentage, 100):.1f}%; height: 100%; transition: width 0.3s;"></div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-size: 0.9em;">
                        <div style="text-align: center; padding: 8px; background: white; border-radius: 6px;">
                            <div style="color: #6c757d;">Cible</div>
                            <div style="font-weight: bold; color: #212529;">{lot.target_tonnage:.2f} T</div>
                        </div>
                        <div style="text-align: center; padding: 8px; background: white; border-radius: 6px;">
                            <div style="color: #6c757d;">Actuel</div>
                            <div style="font-weight: bold; color: #212529;">{lot.current_tonnage:.2f} T</div>
                        </div>
                        <div style="text-align: center; padding: 8px; background: white; border-radius: 6px;">
                            <div style="color: #6c757d;">Restant</div>
                            <div style="font-weight: bold; color: #28a745;">{lot.remaining_tonnage:.2f} T</div>
                        </div>
                    </div>
                    <div style="margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 6px; text-align: center;">
                        <span style="color: #1976d2;">
                            📊 {lot.remaining_units} {lot.packaging_unit_name}s restants à produire
                        </span>
                    </div>
                </div>
                """
            else:
                wizard.lot_info_html = """
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; text-align: center;">
                    <span style="font-size: 2em;">📋</span>
                    <p style="margin: 10px 0 0 0; color: #856404;">
                        Sélectionnez un lot pour voir ses informations
                    </p>
                </div>
                """

    @api.depends('lot_id')
    def _compute_product_type_display(self):
        """Affiche le type de produit en français"""
        type_labels = {
            'cocoa_mass': '🍫 Masse de cacao',
            'cocoa_butter': '🧈 Beurre de cacao',
            'cocoa_cake': '🥧 Cake de cacao',
            'cocoa_powder': '☕ Poudre de cacao',
        }
        for wizard in self:
            wizard.product_type_display = type_labels.get(wizard.lot_id.product_type, '') if wizard.lot_id else ''

    @api.depends('units_produced', 'packaging_unit_weight', 'current_tonnage', 'target_tonnage')
    def _compute_production_tonnage(self):
        """Calcule le tonnage de cette production et le nouveau remplissage"""
        for wizard in self:
            if wizard.packaging_unit_weight and wizard.units_produced:
                wizard.production_tonnage = wizard.units_produced * wizard.packaging_unit_weight
                wizard.production_tonnage_kg = wizard.production_tonnage * 1000
                
                if wizard.target_tonnage:
                    wizard.new_tonnage = wizard.current_tonnage + wizard.production_tonnage
                    wizard.new_fill_percentage = (wizard.new_tonnage / wizard.target_tonnage) * 100
                    wizard.will_exceed_capacity = wizard.new_fill_percentage > 110  # 10% tolérance
                else:
                    wizard.new_tonnage = wizard.current_tonnage + wizard.production_tonnage
                    wizard.new_fill_percentage = 0
                    wizard.will_exceed_capacity = False
            else:
                wizard.production_tonnage = 0
                wizard.production_tonnage_kg = 0
                wizard.new_tonnage = wizard.current_tonnage
                wizard.new_fill_percentage = wizard.fill_percentage
                wizard.will_exceed_capacity = False

    @api.depends('lot_id', 'units_produced', 'will_exceed_capacity')
    def _compute_can_confirm(self):
        """Vérifie si on peut confirmer la production"""
        for wizard in self:
            wizard.can_confirm = (
                wizard.lot_id and 
                wizard.units_produced > 0 and 
                not wizard.will_exceed_capacity
            )

    @api.depends('will_exceed_capacity', 'new_fill_percentage', 'remaining_units', 'units_produced')
    def _compute_warning_message(self):
        """Génère un message d'avertissement si nécessaire"""
        for wizard in self:
            if wizard.will_exceed_capacity:
                wizard.warning_message = _("⚠️ Cette production dépasserait la capacité du lot de plus de 10%!")
            elif wizard.units_produced > wizard.remaining_units and wizard.remaining_units > 0:
                wizard.warning_message = _("⚠️ Vous produisez plus que les %d unités restantes.") % wizard.remaining_units
            elif wizard.new_fill_percentage >= 100:
                wizard.warning_message = _("✅ Ce lot sera complet après cette production!")
            else:
                wizard.warning_message = False

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """Met à jour les suggestions quand on change de lot"""
        if self.lot_id:
            # Suggérer le nombre d'unités restantes (max 10 par défaut)
            suggested_units = min(self.lot_id.remaining_units, 10)
            if suggested_units > 0:
                self.units_produced = suggested_units

    @api.onchange('units_produced')
    def _onchange_units_produced(self):
        """Validation en temps réel du nombre d'unités"""
        if self.units_produced < 0:
            self.units_produced = 0
            return {
                'warning': {
                    'title': _('Valeur invalide'),
                    'message': _('Le nombre d\'unités ne peut pas être négatif.')
                }
            }

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================
    @api.constrains('units_produced')
    def _check_units_produced(self):
        for wizard in self:
            if wizard.units_produced <= 0:
                raise ValidationError(_("Le nombre d'unités produites doit être supérieur à 0."))

    # =========================================================================
    # ACTIONS
    # =========================================================================
    def action_confirm(self):
        """Confirme et crée la ligne de production"""
        self.ensure_one()
        
        if not self.lot_id:
            raise UserError(_("Veuillez sélectionner un lot."))
        
        if self.units_produced <= 0:
            raise UserError(_("Le nombre d'unités produites doit être supérieur à 0."))
        
        if self.will_exceed_capacity:
            raise UserError(_(
                "Cette production dépasserait la capacité du lot de plus de 10%%.\n"
                "Capacité: %.2f T, Total après: %.2f T"
            ) % (self.target_tonnage, self.new_tonnage))
        
        # Créer la ligne de production
        production_line = self.env['potting.production.line'].create({
            'lot_id': self.lot_id.id,
            'date': self.date,
            'units_produced': self.units_produced,
            'shift': self.shift,
            'operator_id': self.operator_id.id if self.operator_id else False,
            'note': self.note,
            'company_id': self.company_id.id,
        })
        
        # Message de succès
        message = _(
            "✅ Production ajoutée avec succès!\n\n"
            "📦 Lot: %s\n"
            "📊 Unités: %d %s\n"
            "⚖️ Tonnage: %.3f T\n"
            "📈 Remplissage: %.1f%%"
        ) % (
            self.lot_id.name,
            self.units_produced,
            self.packaging_unit_name or 'unités',
            self.production_tonnage,
            self.new_fill_percentage
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Production ajoutée'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }

    def action_confirm_and_new(self):
        """Confirme et ouvre un nouveau wizard pour continuer"""
        self.action_confirm()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle production'),
            'res_model': 'potting.add.production.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shift': self.shift,
                'default_operator_id': self.operator_id.id if self.operator_id else False,
            }
        }
