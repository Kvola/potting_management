# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingLot(models.Model):
    _name = 'potting.lot'
    _description = 'Lot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _check_company_auto = True

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
        readonly=True
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
    def add_production(self, tonnage, batch_number=None, shift=None, operator_id=None, note=None):
        """Add a production line to the lot"""
        self.ensure_one()
        if self.state not in ('draft', 'in_production'):
            raise UserError(_("Impossible d'ajouter de la production à un lot %s.") % self.state)
        
        if tonnage <= 0:
            raise ValidationError(_("Le tonnage doit être supérieur à 0."))
        
        # Check if this would overfill the lot by too much
        if self.current_tonnage + tonnage > self.target_tonnage * 1.1:  # 10% tolerance
            raise UserError(_(
                "Cette production dépasserait la capacité du lot de plus de 10%%. "
                "Capacité: %.2f T, Actuel: %.2f T, Production: %.2f T"
            ) % (self.target_tonnage, self.current_tonnage, tonnage))
        
        vals = {
            'lot_id': self.id,
            'tonnage': tonnage,
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
            'productions': [{
                'date': prod.date,
                'tonnage': prod.tonnage,
                'batch': prod.batch_number,
                'shift': prod.shift,
            } for prod in self.production_line_ids.sorted('date')],
        }
