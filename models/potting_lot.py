# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingLot(models.Model):
    _name = 'potting.lot'
    _description = 'Lot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _check_company_auto = True

    # -------------------------------------------------------------------------
    # CONSTANTES DE CONDITIONNEMENT PAR TYPE DE PRODUIT
    # -------------------------------------------------------------------------
    # Masse de cacao : cartons de 25 kg
    # Beurre de cacao : cartons de 25 kg
    # Cake de cacao : big bags de 1 tonne (1000 kg)
    # Poudre de cacao : sacs de 25 kg
    PACKAGING_CONFIG = {
        'cocoa_mass': {'unit_weight': 0.025, 'unit_name': 'carton', 'unit_name_plural': 'cartons'},  # 25 kg = 0.025 T
        'cocoa_butter': {'unit_weight': 0.025, 'unit_name': 'carton', 'unit_name_plural': 'cartons'},  # 25 kg = 0.025 T
        'cocoa_cake': {'unit_weight': 1.0, 'unit_name': 'big bag', 'unit_name_plural': 'big bags'},  # 1000 kg = 1 T
        'cocoa_powder': {'unit_weight': 0.025, 'unit_name': 'sac', 'unit_name_plural': 'sacs'},  # 25 kg = 0.025 T
    }

    # SQL Constraints
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 
         'Le numéro de lot doit être unique par société!'),
        ('target_tonnage_positive', 'CHECK(target_tonnage > 0)', 
         'Le tonnage cible doit être supérieur à 0!'),
    ]

    name = fields.Char(
        string="Numéro de lot",
        required=True,
        tracking=True,
        index=True,
        copy=False,
        readonly=True,
        help="Référence complète du lot incluant le suffixe de certification (ex: T10582RA)"
    )
    
    base_name = fields.Char(
        string="Référence de base",
        required=True,
        index=True,
        copy=False,
        readonly=True,
        help="Référence du lot sans le suffixe de certification (ex: T10582)"
    )
    
    # -------------------------------------------------------------------------
    # CHAMPS DE CERTIFICATION
    # -------------------------------------------------------------------------
    certification_id = fields.Many2one(
        'potting.certification',
        string="Certification",
        tracking=True,
        index=True,
        help="Certification du lot (Fair Trade, Rain Forest, etc.). Le suffixe sera ajouté à la référence."
    )
    
    certification_suffix = fields.Char(
        string="Suffixe certification",
        related='certification_id.suffix',
        store=True
    )
    
    has_certification = fields.Boolean(
        string="Certifié",
        compute='_compute_has_certification',
        store=True,
        index=True
    )
    
    display_name_with_certification = fields.Char(
        string="Référence lot",
        compute='_compute_display_name_with_certification',
        store=True,
        help="Numéro de lot avec suffixe de certification si défini"
    )
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        ondelete='cascade',
        tracking=True,
        check_company=True,
        index=True
    )
    
    customer_order_id = fields.Many2one(
        related='transit_order_id.customer_order_id',
        string="Commande client",
        store=True,
        index=True
    )
    
    customer_id = fields.Many2one(
        related='transit_order_id.customer_id',
        string="Client",
        store=True,
        index=True
    )
    
    consignee_id = fields.Many2one(
        related='transit_order_id.consignee_id',
        string="Destinataire",
        store=True
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit", required=True, tracking=True, index=True)
    
    product_type_display = fields.Char(
        string="Type produit",
        compute='_compute_product_type_display'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        tracking=True,
        domain="[('potting_product_type', '=', product_type)]"
    )
    
    target_tonnage = fields.Float(
        string="Tonnage cible (T)",
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Capacité maximale du lot"
    )
    
    current_tonnage = fields.Float(
        string="Tonnage actuel (T)",
        compute='_compute_current_tonnage',
        store=True,
        tracking=True,
        digits='Product Unit of Measure'
    )
    
    remaining_tonnage = fields.Float(
        string="Tonnage restant (T)",
        compute='_compute_current_tonnage',
        store=True,
        digits='Product Unit of Measure'
    )
    
    # -------------------------------------------------------------------------
    # CHAMPS DE CONDITIONNEMENT
    # -------------------------------------------------------------------------
    packaging_unit_name = fields.Char(
        string="Unité de conditionnement",
        compute='_compute_packaging_info',
        store=True,
        help="Type d'unité de conditionnement (carton, big bag, sac)"
    )
    
    packaging_unit_weight = fields.Float(
        string="Poids unitaire (T)",
        compute='_compute_packaging_info',
        store=True,
        digits=(10, 4),
        help="Poids d'une unité de conditionnement en tonnes"
    )
    
    packaging_unit_weight_kg = fields.Float(
        string="Poids unitaire (kg)",
        compute='_compute_packaging_info',
        store=True,
        digits=(10, 2),
        help="Poids d'une unité de conditionnement en kilogrammes"
    )
    
    target_units = fields.Integer(
        string="Unités cibles",
        compute='_compute_packaging_units',
        store=True,
        help="Nombre d'unités de conditionnement à produire"
    )
    
    current_units = fields.Integer(
        string="Unités produites",
        compute='_compute_packaging_units',
        store=True,
        help="Nombre d'unités de conditionnement actuellement produites"
    )
    
    remaining_units = fields.Integer(
        string="Unités restantes",
        compute='_compute_packaging_units',
        store=True,
        help="Nombre d'unités de conditionnement restant à produire"
    )
    
    packaging_display = fields.Char(
        string="Conditionnement",
        compute='_compute_packaging_display',
        help="Affichage formaté du conditionnement"
    )
    
    fill_percentage = fields.Float(
        string="Remplissage (%)",
        compute='_compute_current_tonnage',
        store=True
    )
    
    is_full = fields.Boolean(
        string="Capacité atteinte",
        compute='_compute_current_tonnage',
        store=True,
        index=True
    )
    
    overfill_warning = fields.Boolean(
        string="Dépassement",
        compute='_compute_current_tonnage',
        store=True
    )
    
    production_line_ids = fields.One2many(
        'potting.production.line',
        'lot_id',
        string="Lignes de production"
    )
    
    production_count = fields.Integer(
        string="Nombre de productions",
        compute='_compute_production_count',
        store=True
    )
    
    container_id = fields.Many2one(
        'potting.container',
        string="Conteneur",
        tracking=True,
        index=True
    )
    
    date_potted = fields.Datetime(
        string="Date d'empotage",
        tracking=True,
        readonly=True,
        copy=False
    )
    
    potted_by_id = fields.Many2one(
        'res.users',
        string="Empoté par",
        readonly=True,
        copy=False
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_production', 'En production'),
        ('ready', 'Prêt pour empotage'),
        ('potted', 'Empoté'),
    ], string="État", default='draft', tracking=True, index=True, copy=False)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    # Quality fields
    quality_check = fields.Boolean(
        string="Contrôle qualité effectué",
        tracking=True
    )
    
    quality_note = fields.Text(
        string="Notes qualité"
    )
    
    quality_approved = fields.Boolean(
        string="Qualité approuvée",
        tracking=True
    )
    
    # Tolerance for considering lot as full (in percentage)
    FILL_TOLERANCE = 95.0

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('target_tonnage')
    def _check_target_tonnage(self):
        for lot in self:
            if lot.target_tonnage <= 0:
                raise ValidationError(_("Le tonnage cible doit être supérieur à 0."))
            # Max 50 tonnes per lot
            if lot.target_tonnage > 50:
                raise ValidationError(_("Le tonnage cible ne peut pas dépasser 50 tonnes par lot."))

    @api.constrains('product_type', 'product_id')
    def _check_product_type_consistency(self):
        for lot in self:
            if lot.product_id and lot.product_id.potting_product_type != lot.product_type:
                raise ValidationError(_(
                    "Le produit sélectionné ne correspond pas au type de produit du lot."
                ))

    @api.constrains('container_id', 'state')
    def _check_container_state(self):
        for lot in self:
            if lot.state == 'potted' and not lot.container_id:
                raise ValidationError(_(
                    "Un lot empoté doit avoir un conteneur assigné."
                ))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('certification_id')
    def _compute_has_certification(self):
        for lot in self:
            lot.has_certification = bool(lot.certification_id)

    @api.depends('base_name', 'certification_id', 'certification_id.suffix')
    def _compute_display_name_with_certification(self):
        for lot in self:
            base = lot.base_name or lot.name or ''
            if lot.certification_id and lot.certification_id.suffix:
                suffix = lot.certification_id.suffix.upper()
                lot.display_name_with_certification = f"{base}{suffix}"
            else:
                lot.display_name_with_certification = base

    @api.onchange('certification_id')
    def _onchange_certification_id(self):
        """Met à jour le numéro de lot quand la certification change."""
        if self.base_name:
            if self.certification_id and self.certification_id.suffix:
                self.name = f"{self.base_name}{self.certification_id.suffix.upper()}"
            else:
                self.name = self.base_name

    @api.model_create_multi
    def create(self, vals_list):
        """Override create pour initialiser base_name si non fourni."""
        for vals in vals_list:
            # Si base_name n'est pas fourni, utiliser name comme base_name
            if 'base_name' not in vals and 'name' in vals:
                vals['base_name'] = vals['name']
            # Si une certification est fournie, mettre à jour le name avec le suffixe
            if vals.get('certification_id') and vals.get('base_name'):
                certification = self.env['potting.certification'].browse(vals['certification_id'])
                if certification.suffix:
                    vals['name'] = f"{vals['base_name']}{certification.suffix.upper()}"
        return super().create(vals_list)

    def write(self, vals):
        """Override write pour mettre à jour le name quand la certification change."""
        result = super().write(vals)
        if 'certification_id' in vals:
            for lot in self:
                if lot.base_name:
                    if lot.certification_id and lot.certification_id.suffix:
                        new_name = f"{lot.base_name}{lot.certification_id.suffix.upper()}"
                    else:
                        new_name = lot.base_name
                    if lot.name != new_name:
                        super(PottingLot, lot).write({'name': new_name})
        return result

    @api.depends('product_type')
    def _compute_product_type_display(self):
        selection_dict = dict(self._fields['product_type'].selection)
        for lot in self:
            lot.product_type_display = selection_dict.get(lot.product_type, '')

    @api.depends('production_line_ids.tonnage', 'target_tonnage')
    def _compute_current_tonnage(self):
        for lot in self:
            lot.current_tonnage = sum(lot.production_line_ids.mapped('tonnage'))
            lot.remaining_tonnage = max(0, lot.target_tonnage - lot.current_tonnage)
            
            if lot.target_tonnage > 0:
                lot.fill_percentage = (lot.current_tonnage / lot.target_tonnage) * 100
            else:
                lot.fill_percentage = 0
            
            # Consider lot as full if at least 95% filled
            lot.is_full = lot.fill_percentage >= self.FILL_TOLERANCE
            
            # Warning if overfilled (more than 105%)
            lot.overfill_warning = lot.fill_percentage > 105

    @api.depends('production_line_ids')
    def _compute_production_count(self):
        for lot in self:
            lot.production_count = len(lot.production_line_ids)

    @api.depends('product_type')
    def _compute_packaging_info(self):
        """Calcul des informations de conditionnement basé sur le type de produit"""
        for lot in self:
            config = self.PACKAGING_CONFIG.get(lot.product_type, {})
            lot.packaging_unit_name = config.get('unit_name_plural', '')
            lot.packaging_unit_weight = config.get('unit_weight', 0)
            lot.packaging_unit_weight_kg = config.get('unit_weight', 0) * 1000  # Conversion T -> kg

    @api.depends('target_tonnage', 'current_tonnage', 'packaging_unit_weight')
    def _compute_packaging_units(self):
        """Calcul du nombre d'unités de conditionnement (cartons, big bags, sacs)"""
        for lot in self:
            if lot.packaging_unit_weight and lot.packaging_unit_weight > 0:
                lot.target_units = int(lot.target_tonnage / lot.packaging_unit_weight)
                lot.current_units = int(lot.current_tonnage / lot.packaging_unit_weight)
                lot.remaining_units = max(0, lot.target_units - lot.current_units)
            else:
                lot.target_units = 0
                lot.current_units = 0
                lot.remaining_units = 0

    @api.depends('current_units', 'target_units', 'packaging_unit_name', 'packaging_unit_weight_kg')
    def _compute_packaging_display(self):
        """Affichage formaté du conditionnement"""
        for lot in self:
            if lot.packaging_unit_name and lot.target_units > 0:
                lot.packaging_display = _(
                    "%(current)d / %(target)d %(unit)s (%(weight).0f kg/unité)"
                ) % {
                    'current': lot.current_units,
                    'target': lot.target_units,
                    'unit': lot.packaging_unit_name,
                    'weight': lot.packaging_unit_weight_kg,
                }
            else:
                lot.packaging_display = ''

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('transit_order_id')
    def _onchange_transit_order_id(self):
        if self.transit_order_id:
            self.product_type = self.transit_order_id.product_type
            self.product_id = self.transit_order_id.product_id

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    def unlink(self):
        for lot in self:
            # Protection contre la suppression si pas en brouillon
            if lot.state not in ('draft',):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les lots en brouillon. "
                    "Le lot '%s' est en état '%s'."
                ) % (lot.name, dict(lot._fields['state'].selection).get(lot.state)))
            if lot.current_tonnage > 0:
                raise UserError(_(
                    "Vous ne pouvez pas supprimer un lot avec de la production. "
                    "Supprimez d'abord les lignes de production."
                ))
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': _('%s (Copie)') % self.name,
            'state': 'draft',
            'container_id': False,
            'date_potted': False,
        })
        return super().copy(default)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_start_production(self):
        for lot in self:
            if lot.state != 'draft':
                raise UserError(_("Seuls les lots en brouillon peuvent démarrer la production."))
            lot.state = 'in_production'
            lot.message_post(body=_("Production démarrée."))

    def action_mark_ready(self):
        """Mark lot as ready for potting when capacity is reached"""
        for lot in self:
            if lot.state != 'in_production':
                raise UserError(_("Le lot doit être en production."))
            if not lot.is_full:
                raise UserError(_(
                    "Le lot %s n'a pas atteint sa capacité minimale (%.1f%%). "
                    "Remplissage actuel: %.2f%%"
                ) % (lot.name, self.FILL_TOLERANCE, lot.fill_percentage))
            lot.state = 'ready'
            lot.message_post(body=_("Lot prêt pour empotage (%.2f%% rempli).") % lot.fill_percentage)

    def action_force_ready(self):
        """Force lot as ready even if not full (manager action)"""
        for lot in self:
            if lot.state != 'in_production':
                raise UserError(_("Le lot doit être en production."))
            if lot.current_tonnage <= 0:
                raise UserError(_("Le lot doit avoir au moins une production."))
            lot.state = 'ready'
            lot.message_post(body=_(
                "Lot forcé comme prêt par %s (%.2f%% rempli)."
            ) % (self.env.user.name, lot.fill_percentage))

    def action_pot(self):
        """Open wizard to pot the lot into a container"""
        self.ensure_one()
        if self.state != 'ready':
            raise UserError(_("Le lot doit être prêt pour l'empotage."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Empotage du lot %s') % self.name,
            'res_model': 'potting.pot.lot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lot_id': self.id,
                'default_transit_order_id': self.transit_order_id.id,
            },
        }

    def action_confirm_potting(self, container_id):
        """Confirm potting of the lot into a container"""
        self.ensure_one()
        if not container_id:
            raise UserError(_("Un conteneur doit être sélectionné."))
        
        self.write({
            'container_id': container_id,
            'date_potted': fields.Datetime.now(),
            'potted_by_id': self.env.user.id,
            'state': 'potted',
        })
        self.message_post(body=_(
            "Lot empoté dans le conteneur %s par %s."
        ) % (self.container_id.name, self.env.user.name))
        
        # Check if all lots of the OT are potted
        transit_order = self.transit_order_id
        if all(lot.state == 'potted' for lot in transit_order.lot_ids):
            transit_order.action_mark_ready()

    def action_view_productions(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Productions - %s') % self.name,
            'res_model': 'potting.production.line',
            'view_mode': 'tree,form',
            'domain': [('lot_id', '=', self.id)],
            'context': {
                'default_lot_id': self.id,
                'default_transit_order_id': self.transit_order_id.id,
            },
        }
        return action

    def action_view_transit_order(self):
        """View the parent transit order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.transit_order_id.name,
            'res_model': 'potting.transit.order',
            'view_mode': 'form',
            'res_id': self.transit_order_id.id,
        }

    def action_draft(self):
        """Remettre le lot en brouillon de façon sécurisée"""
        for lot in self:
            # Ne peut remettre en brouillon que depuis certains états
            if lot.state == 'potted':
                raise UserError(_(
                    "Les lots empotés ne peuvent pas être remis en brouillon. "
                    "Le lot '%s' est déjà empoté dans le conteneur '%s'."
                ) % (lot.name, lot.container_id.name if lot.container_id else '-'))
            if lot.state == 'draft':
                continue  # Déjà en brouillon
            
            # Si le lot a de la production, on le laisse en in_production
            if lot.current_tonnage > 0:
                lot.state = 'in_production'
                lot.message_post(body=_("🔄 Lot remis en production par %s.") % self.env.user.name)
            else:
                lot.state = 'draft'
                lot.message_post(body=_("🔄 Lot remis en brouillon par %s.") % self.env.user.name)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def add_production(self, units_produced, batch_number=None, shift=None, operator_id=None, note=None):
        """
        Add a production line to the lot by specifying the number of units.
        The tonnage is calculated automatically based on the packaging configuration.
        
        :param units_produced: Number of units (cartons, big bags, sacs) produced
        :param batch_number: Optional batch number
        :param shift: Optional shift (morning, afternoon, night)
        :param operator_id: Optional operator user ID
        :param note: Optional note
        :return: Created production line record
        """
        self.ensure_one()
        if self.state not in ('draft', 'in_production'):
            raise UserError(_("Impossible d'ajouter de la production à un lot %s.") % self.state)
        
        if units_produced <= 0:
            raise ValidationError(_("Le nombre d'unités produites doit être supérieur à 0."))
        
        # Calculate tonnage from units
        tonnage = units_produced * self.packaging_unit_weight
        
        # Check if this would overfill the lot by too much
        if self.current_tonnage + tonnage > self.target_tonnage * 1.1:  # 10% tolerance
            max_units = int((self.target_tonnage * 1.1 - self.current_tonnage) / self.packaging_unit_weight) if self.packaging_unit_weight else 0
            raise UserError(_(
                "Cette production dépasserait la capacité du lot de plus de 10%%.\n"
                "Capacité: %.2f T, Actuel: %.2f T, Production: %.2f T (%d %s)\n"
                "Maximum: %d %s"
            ) % (
                self.target_tonnage, self.current_tonnage, tonnage, 
                units_produced, self.packaging_unit_name,
                max_units, self.packaging_unit_name
            ))
        
        vals = {
            'lot_id': self.id,
            'units_produced': units_produced,
            'date': fields.Date.context_today(self),
        }
        if batch_number:
            vals['batch_number'] = batch_number
        if shift:
            vals['shift'] = shift
        if operator_id:
            vals['operator_id'] = operator_id
        if note:
            vals['note'] = note
        
        return self.env['potting.production.line'].create(vals)

    def add_production_by_tonnage(self, tonnage, batch_number=None, shift=None, operator_id=None, note=None):
        """
        Add a production line by specifying tonnage directly.
        The number of units is calculated automatically.
        This method is kept for backward compatibility.
        
        :param tonnage: Tonnage to add
        :return: Created production line record
        """
        self.ensure_one()
        if not self.packaging_unit_weight or self.packaging_unit_weight <= 0:
            raise UserError(_("Impossible de calculer les unités : poids unitaire non défini."))
        
        units_produced = int(tonnage / self.packaging_unit_weight)
        if units_produced <= 0:
            raise ValidationError(_(
                "Le tonnage %.3f T correspond à moins d'une unité de %s (%.0f kg)."
            ) % (tonnage, self.packaging_unit_name, self.packaging_unit_weight_kg))
        
        return self.add_production(units_produced, batch_number, shift, operator_id, note)

    def get_fill_status(self):
        """Get the fill status of the lot"""
        self.ensure_one()
        if self.fill_percentage >= 100:
            return 'full'
        elif self.fill_percentage >= self.FILL_TOLERANCE:
            return 'near_full'
        elif self.fill_percentage > 0:
            return 'in_progress'
        else:
            return 'empty'

    def get_summary_data(self):
        """Get summary data for reporting"""
        self.ensure_one()
        return {
            'name': self.name,
            'transit_order': self.transit_order_id.name,
            'product_type': self.product_type_display,
            'target_tonnage': self.target_tonnage,
            'current_tonnage': self.current_tonnage,
            'remaining_tonnage': self.remaining_tonnage,
            'fill_percentage': self.fill_percentage,
            'is_full': self.is_full,
            'state': self.state,
            'container': self.container_id.name if self.container_id else None,
            'date_potted': self.date_potted,
            # Informations de conditionnement
            'packaging_unit_name': self.packaging_unit_name,
            'packaging_unit_weight_kg': self.packaging_unit_weight_kg,
            'target_units': self.target_units,
            'current_units': self.current_units,
            'remaining_units': self.remaining_units,
            'packaging_display': self.packaging_display,
            'productions': [{
                'date': prod.date,
                'tonnage': prod.tonnage,
                'batch': prod.batch_number,
                'shift': prod.shift,
                'units_produced': prod.units_produced if hasattr(prod, 'units_produced') else 0,
            } for prod in self.production_line_ids.sorted('date')],
        }

    @api.model
    def get_packaging_config(self, product_type=None):
        """
        Retourne la configuration de conditionnement pour un type de produit.
        Si aucun type n'est spécifié, retourne toute la configuration.
        
        Configuration :
        - Masse de cacao : cartons de 25 kg
        - Beurre de cacao : cartons de 25 kg
        - Cake de cacao : big bags de 1 tonne
        - Poudre de cacao : sacs de 25 kg
        """
        if product_type:
            return self.PACKAGING_CONFIG.get(product_type, {})
        return self.PACKAGING_CONFIG

    def get_units_from_tonnage(self, tonnage):
        """
        Convertit un tonnage en nombre d'unités de conditionnement.
        Retourne un tuple (nombre_unités, reste_en_tonnes)
        """
        self.ensure_one()
        if not self.packaging_unit_weight or self.packaging_unit_weight <= 0:
            return (0, tonnage)
        
        units = int(tonnage / self.packaging_unit_weight)
        remainder = tonnage - (units * self.packaging_unit_weight)
        return (units, remainder)

    def get_tonnage_from_units(self, units):
        """
        Convertit un nombre d'unités en tonnage.
        """
        self.ensure_one()
        if not self.packaging_unit_weight:
            return 0
        return units * self.packaging_unit_weight
