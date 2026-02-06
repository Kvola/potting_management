# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingQuickProductionWizard(models.TransientModel):
    """
    Wizard de production rapide pour les Agents Exportation (CEO Agent).
    Affiche une vue d'ensemble des lots en production et permet
    d'enregistrer plusieurs productions rapidement.
    """
    _name = 'potting.quick.production.wizard'
    _description = 'Wizard de production rapide'

    # =========================================================================
    # CHAMPS PRINCIPAUX
    # =========================================================================
    
    # Champs pour le mode liste
    lots_in_production_count = fields.Integer(
        string="Lots en production",
        compute='_compute_stats',
    )
    
    today_productions_count = fields.Integer(
        string="Productions du jour",
        compute='_compute_stats',
    )
    
    today_tonnage = fields.Float(
        string="Tonnage du jour",
        compute='_compute_stats',
        digits='Product Unit of Measure',
    )
    
    # Champ pour la sélection du lot
    selected_lot_id = fields.Many2one(
        'potting.lot',
        string="Lot",
        domain="[('state', 'in', ['draft', 'in_production']), ('is_full', '=', False)]",
    )
    
    selected_lot_name = fields.Char(
        related='selected_lot_id.name',
        string="Nom du lot",
    )
    
    selected_lot_product_type = fields.Selection(
        related='selected_lot_id.product_type',
        string="Type de produit",
    )
    
    selected_lot_product_type_display = fields.Char(
        string="Type",
        compute='_compute_product_type_display',
    )
    
    selected_lot_fill_percentage = fields.Float(
        related='selected_lot_id.fill_percentage',
        string="Remplissage (%)",
    )
    
    selected_lot_remaining_units = fields.Integer(
        related='selected_lot_id.remaining_units',
        string="Unités restantes",
    )
    
    selected_lot_packaging_unit_name = fields.Char(
        related='selected_lot_id.packaging_unit_name',
        string="Unité d'emballage",
    )
    
    selected_lot_packaging_unit_weight = fields.Float(
        related='selected_lot_id.packaging_unit_weight',
        string="Poids unitaire (T)",
    )
    
    selected_lot_target_tonnage = fields.Float(
        related='selected_lot_id.target_tonnage',
        string="Tonnage cible",
    )
    
    selected_lot_current_tonnage = fields.Float(
        related='selected_lot_id.current_tonnage',
        string="Tonnage actuel",
    )
    
    selected_lot_transit_order_id = fields.Many2one(
        related='selected_lot_id.transit_order_id',
        string="Ordre de Transit",
    )
    
    # Champs de saisie de production
    date = fields.Date(
        string="Date de production",
        required=True,
        default=fields.Date.context_today,
    )
    
    units_produced = fields.Integer(
        string="Unités produites",
        default=1,
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
    
    # Champs calculés pour la production
    production_tonnage = fields.Float(
        string="Tonnage ajouté",
        compute='_compute_production_info',
        digits='Product Unit of Measure',
    )
    
    new_fill_percentage = fields.Float(
        string="Nouveau remplissage (%)",
        compute='_compute_production_info',
    )
    
    will_exceed_capacity = fields.Boolean(
        string="Dépassera la capacité",
        compute='_compute_production_info',
    )
    
    can_confirm = fields.Boolean(
        string="Peut confirmer",
        compute='_compute_can_confirm',
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company,
    )
    
    # HTML summary
    summary_html = fields.Html(
        string="Résumé",
        compute='_compute_summary_html',
        sanitize=False,
    )
    
    # Liste des lots HTML
    lots_list_html = fields.Html(
        string="Lots disponibles",
        compute='_compute_lots_list_html',
        sanitize=False,
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('company_id')
    def _compute_stats(self):
        """Calcule les statistiques du jour"""
        for wizard in self:
            # Lots en production
            wizard.lots_in_production_count = self.env['potting.lot'].search_count([
                ('state', 'in', ['draft', 'in_production']),
                ('is_full', '=', False),
            ])
            
            # Productions du jour
            today = fields.Date.context_today(self)
            today_productions = self.env['potting.production.line'].search([
                ('date', '=', today),
            ])
            wizard.today_productions_count = len(today_productions)
            wizard.today_tonnage = sum(today_productions.mapped('tonnage'))
    
    @api.depends('selected_lot_product_type')
    def _compute_product_type_display(self):
        """Affiche le type de produit en français"""
        type_labels = {
            'cocoa_mass': '🍫 Masse de cacao',
            'cocoa_butter': '🧈 Beurre de cacao',
            'cocoa_cake': '🥧 Cake de cacao',
            'cocoa_powder': '☕ Poudre de cacao',
        }
        for wizard in self:
            wizard.selected_lot_product_type_display = type_labels.get(
                wizard.selected_lot_product_type, '') if wizard.selected_lot_product_type else ''
    
    @api.depends('units_produced', 'selected_lot_packaging_unit_weight', 
                 'selected_lot_current_tonnage', 'selected_lot_target_tonnage')
    def _compute_production_info(self):
        """Calcule les informations de production"""
        for wizard in self:
            if wizard.selected_lot_packaging_unit_weight and wizard.units_produced:
                wizard.production_tonnage = wizard.units_produced * wizard.selected_lot_packaging_unit_weight
                
                new_tonnage = (wizard.selected_lot_current_tonnage or 0) + wizard.production_tonnage
                if wizard.selected_lot_target_tonnage:
                    wizard.new_fill_percentage = (new_tonnage / wizard.selected_lot_target_tonnage) * 100
                    wizard.will_exceed_capacity = wizard.new_fill_percentage > 110
                else:
                    wizard.new_fill_percentage = 0
                    wizard.will_exceed_capacity = False
            else:
                wizard.production_tonnage = 0
                wizard.new_fill_percentage = wizard.selected_lot_fill_percentage or 0
                wizard.will_exceed_capacity = False
    
    @api.depends('selected_lot_id', 'units_produced', 'will_exceed_capacity')
    def _compute_can_confirm(self):
        """Vérifie si on peut confirmer la production"""
        for wizard in self:
            wizard.can_confirm = (
                wizard.selected_lot_id and 
                wizard.units_produced > 0 and 
                not wizard.will_exceed_capacity
            )
    
    @api.depends('lots_in_production_count', 'today_productions_count', 'today_tonnage')
    def _compute_summary_html(self):
        """Génère le résumé HTML"""
        for wizard in self:
            wizard.summary_html = f"""
            <div class="row text-center mb-4">
                <div class="col-4">
                    <div class="card bg-primary text-white p-2">
                        <div class="fs-2 fw-bold">{wizard.lots_in_production_count}</div>
                        <div class="small">📦 Lots disponibles</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="card bg-success text-white p-2">
                        <div class="fs-2 fw-bold">{wizard.today_productions_count}</div>
                        <div class="small">✅ Productions aujourd'hui</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="card bg-info text-white p-2">
                        <div class="fs-2 fw-bold">{wizard.today_tonnage:.2f} T</div>
                        <div class="small">⚖️ Tonnage du jour</div>
                    </div>
                </div>
            </div>
            """
    
    @api.depends('company_id')
    def _compute_lots_list_html(self):
        """Génère la liste HTML des lots disponibles"""
        for wizard in self:
            lots = self.env['potting.lot'].search([
                ('state', 'in', ['draft', 'in_production']),
                ('is_full', '=', False),
            ], order='fill_percentage desc', limit=20)
            
            if not lots:
                wizard.lots_list_html = """
                <div class="alert alert-info text-center">
                    <i class="fa fa-info-circle fa-2x mb-2"></i>
                    <p class="mb-0">Aucun lot en production pour le moment.</p>
                </div>
                """
                continue
            
            type_labels = {
                'cocoa_mass': '🍫 Masse',
                'cocoa_butter': '🧈 Beurre',
                'cocoa_cake': '🥧 Cake',
                'cocoa_powder': '☕ Poudre',
            }
            
            rows = []
            for lot in lots:
                fill_pct = lot.fill_percentage
                fill_color = '#28a745' if fill_pct < 80 else '#ffc107' if fill_pct < 95 else '#dc3545'
                type_label = type_labels.get(lot.product_type, lot.product_type or '-')
                ot_name = lot.transit_order_id.name if lot.transit_order_id else '-'
                
                rows.append(f"""
                <tr style="cursor: default;">
                    <td class="fw-bold text-primary">{lot.name}</td>
                    <td>{type_label}</td>
                    <td><small class="text-muted">{ot_name}</small></td>
                    <td class="text-center">
                        <div class="progress" style="height: 20px; min-width: 100px;">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: {min(fill_pct, 100):.0f}%; background-color: {fill_color};"
                                 aria-valuenow="{fill_pct:.0f}" aria-valuemin="0" aria-valuemax="100">
                                {fill_pct:.0f}%
                            </div>
                        </div>
                    </td>
                    <td class="text-end">
                        <span class="badge bg-secondary">{lot.remaining_units} {lot.packaging_unit_name}</span>
                    </td>
                </tr>
                """)
            
            wizard.lots_list_html = f"""
            <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                <table class="table table-sm table-hover mb-0">
                    <thead class="table-light sticky-top">
                        <tr>
                            <th>Lot</th>
                            <th>Type</th>
                            <th>OT</th>
                            <th class="text-center">Remplissage</th>
                            <th class="text-end">Restant</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
            <div class="text-muted small text-center mt-2">
                <i class="fa fa-lightbulb-o me-1"></i>
                Sélectionnez un lot ci-dessus pour enregistrer une production
            </div>
            """

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('selected_lot_id')
    def _onchange_selected_lot_id(self):
        """Met à jour les suggestions quand on sélectionne un lot"""
        if self.selected_lot_id:
            # Suggérer le nombre d'unités restantes (max 10)
            suggested_units = min(self.selected_lot_remaining_units or 10, 10)
            if suggested_units > 0:
                self.units_produced = suggested_units
    
    @api.onchange('units_produced')
    def _onchange_units_produced(self):
        """Validation en temps réel"""
        if self.units_produced < 0:
            self.units_produced = 0
            return {
                'warning': {
                    'title': _('Valeur invalide'),
                    'message': _('Le nombre d\'unités ne peut pas être négatif.')
                }
            }

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_confirm_production(self):
        """Confirme et enregistre la production"""
        self.ensure_one()
        
        if not self.selected_lot_id:
            raise UserError(_("Veuillez sélectionner un lot."))
        
        if self.units_produced <= 0:
            raise UserError(_("Le nombre d'unités produites doit être supérieur à 0."))
        
        if self.will_exceed_capacity:
            raise UserError(_(
                "Cette production dépasserait la capacité du lot de plus de 10%%.\n"
                "Capacité: %.2f T, Total après: %.2f T"
            ) % (self.selected_lot_target_tonnage, 
                 self.selected_lot_current_tonnage + self.production_tonnage))
        
        # Créer la ligne de production
        production_line = self.env['potting.production.line'].create({
            'lot_id': self.selected_lot_id.id,
            'date': self.date,
            'units_produced': self.units_produced,
            'shift': self.shift,
            'operator_id': self.operator_id.id if self.operator_id else False,
            'note': self.note,
            'company_id': self.company_id.id,
        })
        
        lot_name = self.selected_lot_name
        units = self.units_produced
        unit_name = self.selected_lot_packaging_unit_name or 'unités'
        tonnage = self.production_tonnage
        fill_pct = self.new_fill_percentage
        
        # Message de succès
        message = _(
            "✅ Production enregistrée!\n\n"
            "📦 Lot: %(lot)s\n"
            "📊 %(units)d %(unit_name)s (%(tonnage).3f T)\n"
            "📈 Remplissage: %(fill).1f%%"
        ) % {
            'lot': lot_name,
            'units': units,
            'unit_name': unit_name,
            'tonnage': tonnage,
            'fill': fill_pct,
        }
        
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
    
    def action_confirm_and_continue(self):
        """Confirme la production et reste sur le wizard pour en ajouter d'autres"""
        self.ensure_one()
        
        if not self.selected_lot_id:
            raise UserError(_("Veuillez sélectionner un lot."))
        
        if self.units_produced <= 0:
            raise UserError(_("Le nombre d'unités produites doit être supérieur à 0."))
        
        if self.will_exceed_capacity:
            raise UserError(_(
                "Cette production dépasserait la capacité du lot."
            ))
        
        # Stocker les infos pour le message
        lot_name = self.selected_lot_name
        units = self.units_produced
        unit_name = self.selected_lot_packaging_unit_name or 'unités'
        tonnage = self.production_tonnage
        
        # Créer la ligne de production
        self.env['potting.production.line'].create({
            'lot_id': self.selected_lot_id.id,
            'date': self.date,
            'units_produced': self.units_produced,
            'shift': self.shift,
            'operator_id': self.operator_id.id if self.operator_id else False,
            'note': self.note,
            'company_id': self.company_id.id,
        })
        
        # Réinitialiser pour une nouvelle production (garder date et shift)
        self.note = False
        self.selected_lot_id = False
        self.units_produced = 1
        
        # Retourner un nouveau wizard pour rafraîchir les données
        return {
            'type': 'ir.actions.act_window',
            'name': _('⚡ Production Rapide'),
            'res_model': 'potting.quick.production.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_date': str(self.date),
                'default_shift': self.shift,
                'default_operator_id': self.operator_id.id if self.operator_id else False,
            },
        }


class PottingQuickProductionLine(models.TransientModel):
    """
    Ligne virtuelle pour afficher les lots dans le wizard.
    Non utilisé directement, juste pour définition.
    """
    _name = 'potting.quick.production.line'
    _description = 'Ligne de production rapide'
    
    wizard_id = fields.Many2one(
        'potting.quick.production.wizard',
        string="Wizard",
    )
    
    lot_id = fields.Many2one(
        'potting.lot',
        string="Lot",
    )
