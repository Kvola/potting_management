# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import math


class PottingTransitOrder(models.Model):
    _name = 'potting.transit.order'
    _description = 'Ordre de Transit (OT)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _check_company_auto = True

    # SQL Constraints
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 
         'Le numéro OT doit être unique par société!'),
        ('tonnage_positive', 'CHECK(tonnage > 0)', 
         'Le tonnage doit être supérieur à 0!'),
    ]

    name = fields.Char(
        string="Numéro OT",
        required=True,
        tracking=True,
        index=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    
    # Champ technique pour savoir si l'OT a été créé depuis une commande
    is_created_from_order = fields.Boolean(
        string="Créé depuis une commande",
        default=False,
        copy=False,
        help="Indique si l'OT a été créé directement depuis une commande client"
    )
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        required=True,
        ondelete='cascade',
        tracking=True,
        check_company=True,
        domain="[('state', 'not in', ['done', 'cancelled'])]"
    )
    
    campaign_period = fields.Char(
        related='customer_order_id.campaign_period',
        string="Campagne",
        store=True,
        readonly=True,
        help="Période de la campagne Café-Cacao héritée de la commande"
    )
    
    customer_id = fields.Many2one(
        related='customer_order_id.customer_id',
        string="Client",
        store=True,
        index=True
    )
    
    consignee_id = fields.Many2one(
        'res.partner',
        string="Destinataire (Consignee)",
        required=True,
        tracking=True
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit", required=True, tracking=True, index=True)
    
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        domain="[('potting_product_type', '=', product_type)]",
        tracking=True
    )
    
    tonnage = fields.Float(
        string="Tonnage (T)",
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Tonnage total de l'OT"
    )
    
    max_tonnage_per_lot = fields.Float(
        string="Tonnage max/lot (T)",
        compute='_compute_max_tonnage_per_lot',
        store=True,
        digits='Product Unit of Measure'
    )
    
    vessel_id = fields.Many2one(
        'potting.vessel',
        string="Navire (Vessel)",
        tracking=True
    )
    
    vessel_name = fields.Char(
        string="Nom du navire",
        tracking=True
    )
    
    pod = fields.Char(
        string="Port de déchargement (POD)",
        tracking=True
    )
    
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string="Taille conteneur (TC)", default='20', tracking=True)
    
    lot_range = fields.Char(
        string="Plage de lots",
        compute='_compute_lot_range',
        store=True
    )
    
    booking_number = fields.Char(
        string="Numéro de réservation (Booking)",
        tracking=True,
        index=True
    )
    
    lot_ids = fields.One2many(
        'potting.lot',
        'transit_order_id',
        string="Lots",
        copy=False
    )
    
    lot_count = fields.Integer(
        string="Nombre de lots",
        compute='_compute_lot_count',
        store=True
    )
    
    potted_lot_count = fields.Integer(
        string="Lots empotés",
        compute='_compute_lot_count',
        store=True
    )
    
    pending_lot_count = fields.Integer(
        string="Lots en attente",
        compute='_compute_lot_count',
        store=True
    )
    
    progress_percentage = fields.Float(
        string="Progression (%)",
        compute='_compute_progress',
        store=True
    )
    
    current_tonnage = fields.Float(
        string="Tonnage actuel (T)",
        compute='_compute_current_tonnage',
        store=True,
        digits='Product Unit of Measure'
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('lots_generated', 'Lots générés'),
        ('in_progress', 'En cours'),
        ('ready_validation', 'Prêt pour validation'),
        ('done', 'Validé'),
        ('cancelled', 'Annulé'),
    ], string="État", default='draft', tracking=True, index=True, copy=False)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    date_created = fields.Date(
        string="Date de création",
        default=fields.Date.context_today,
        index=True
    )
    
    date_validated = fields.Datetime(
        string="Date de validation",
        readonly=True,
        copy=False
    )
    
    validated_by_id = fields.Many2one(
        'res.users',
        string="Validé par",
        readonly=True,
        copy=False
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('tonnage')
    def _check_tonnage(self):
        for order in self:
            if order.tonnage <= 0:
                raise ValidationError(_("Le tonnage doit être supérieur à 0."))
            if order.tonnage > 1000:  # Max 1000 tonnes per OT
                raise ValidationError(_("Le tonnage ne peut pas dépasser 1000 tonnes par OT."))

    @api.constrains('product_type', 'product_id')
    def _check_product_type_consistency(self):
        for order in self:
            if order.product_id and order.product_id.potting_product_type != order.product_type:
                raise ValidationError(_(
                    "Le produit sélectionné ne correspond pas au type de produit de l'OT."
                ))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('product_type')
    def _compute_max_tonnage_per_lot(self):
        for order in self:
            order.max_tonnage_per_lot = self.env['res.config.settings'].get_max_tonnage_for_product(
                order.product_type
            )

    @api.depends('lot_ids', 'lot_ids.state')
    def _compute_lot_count(self):
        for order in self:
            lots = order.lot_ids
            order.lot_count = len(lots)
            order.potted_lot_count = len(lots.filtered(lambda l: l.state == 'potted'))
            order.pending_lot_count = len(lots.filtered(lambda l: l.state in ('draft', 'in_production', 'ready')))

    @api.depends('lot_ids.name')
    def _compute_lot_range(self):
        for order in self:
            if order.lot_ids:
                lot_names = sorted(order.lot_ids.mapped('name'))
                if lot_names:
                    order.lot_range = f"{lot_names[0]} → {lot_names[-1]}"
                else:
                    order.lot_range = False
            else:
                order.lot_range = False

    @api.depends('lot_count', 'potted_lot_count')
    def _compute_progress(self):
        for order in self:
            if order.lot_count > 0:
                order.progress_percentage = (order.potted_lot_count / order.lot_count) * 100
            else:
                order.progress_percentage = 0

    @api.depends('lot_ids.current_tonnage')
    def _compute_current_tonnage(self):
        for order in self:
            order.current_tonnage = sum(order.lot_ids.mapped('current_tonnage'))

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('vessel_id')
    def _onchange_vessel_id(self):
        if self.vessel_id:
            self.vessel_name = self.vessel_id.name

    @api.onchange('product_type')
    def _onchange_product_type(self):
        """Reset product when product type changes"""
        if self.product_id and self.product_id.potting_product_type != self.product_type:
            self.product_id = False

    @api.onchange('customer_order_id')
    def _onchange_customer_order_id(self):
        """Set default consignee from customer"""
        if self.customer_order_id and not self.consignee_id:
            self.consignee_id = self.customer_order_id.customer_id

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Générer automatiquement le numéro OT si non fourni ou si 'Nouveau'
            if vals.get('name', _('Nouveau')) == _('Nouveau') or not vals.get('name'):
                # Le nom de l'OT dépend du type de produit et de la campagne de la commande
                product_type = vals.get('product_type')
                
                # Récupérer la campagne depuis la commande
                campaign_period = None
                customer_order_id = vals.get('customer_order_id')
                if customer_order_id:
                    customer_order = self.env['potting.customer.order'].browse(customer_order_id)
                    if customer_order.exists():
                        campaign_period = customer_order.campaign_period
                
                vals['name'] = self.env['res.config.settings'].generate_ot_name(
                    product_type, 
                    campaign_period
                )
            
            # Marquer si l'OT est créé depuis le contexte d'une commande
            if self.env.context.get('default_customer_order_id') or vals.get('customer_order_id'):
                vals['is_created_from_order'] = True
        
        return super().create(vals_list)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': _('Nouveau'),
            'state': 'draft',
            'date_created': fields.Date.context_today(self),
            'is_created_from_order': False,
        })
        return super().copy(default)

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les OT en brouillon ou annulés. "
                    "L'OT '%s' est en état '%s'."
                ) % (order.name, dict(order._fields['state'].selection).get(order.state)))
            # Vérifier qu'aucun lot n'a de production
            if any(lot.current_tonnage > 0 for lot in order.lot_ids):
                raise UserError(_(
                    "Impossible de supprimer l'OT '%s': certains lots ont déjà de la production."
                ) % order.name)
        return super().unlink()

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_generate_lots(self):
        """Open wizard to generate lots with custom max tonnage."""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_("Les lots ne peuvent être générés que pour les OT en brouillon."))
        
        if self.lot_ids:
            raise UserError(_("Des lots existent déjà pour cet OT. Supprimez-les d'abord."))
        
        if not self.tonnage or self.tonnage <= 0:
            raise UserError(_("Le tonnage doit être supérieur à 0."))
        
        if not self.product_type:
            raise UserError(_("Veuillez sélectionner un type de produit."))
        
        # Open the wizard
        return {
            'name': _('Générer les lots'),
            'type': 'ir.actions.act_window',
            'res_model': 'potting.generate.lots.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'potting.transit.order',
            },
        }

    def _get_unique_lot_name(self):
        """Get a unique lot name using sequence and product-specific prefix.
        
        Format: [Prefix][Number] where Prefix depends on product type:
        - M for Masse (cocoa_mass)
        - B for Beurre (cocoa_butter)  
        - T for Tourteau/Cake (cocoa_cake)
        - P for Poudre (cocoa_powder)
        """
        import re
        
        # Get prefix for this product type from configuration
        prefix = self.env['res.config.settings'].get_lot_prefix_for_product(self.product_type)
        
        sequence = self.env['ir.sequence'].next_by_code('potting.lot')
        if sequence:
            # Extract number from sequence
            numbers = re.findall(r'\d+', sequence)
            if numbers:
                return f"{prefix}{numbers[0]}"
        
        # Fallback: use timestamp-based unique name
        import time
        return f"{prefix}{int(time.time() * 1000) % 100000}"

    def _get_next_lot_sequence_number(self):
        """Get the next lot sequence number"""
        sequence = self.env['ir.sequence'].next_by_code('potting.lot')
        if sequence:
            try:
                # Extract number from sequence like "LOT10001" or "T10001"
                import re
                numbers = re.findall(r'\d+', sequence)
                if numbers:
                    return int(numbers[0])
            except (ValueError, TypeError):
                pass
        return 10001

    def action_regenerate_lots(self):
        """Delete existing lots and regenerate"""
        self.ensure_one()
        if self.state not in ('draft', 'lots_generated'):
            raise UserError(_("Les lots ne peuvent être régénérés que pour les OT en brouillon ou avec lots générés."))
        
        # Check if any lot has production
        if any(lot.current_tonnage > 0 for lot in self.lot_ids):
            raise UserError(_("Impossible de régénérer les lots: certains lots ont déjà de la production."))
        
        self.lot_ids.unlink()
        self.state = 'draft'
        return self.action_generate_lots()

    def action_start_production(self):
        for order in self:
            if order.state != 'lots_generated':
                raise UserError(_("L'OT doit avoir des lots générés pour démarrer la production."))
            order.state = 'in_progress'
            order.lot_ids.filtered(lambda l: l.state == 'draft').write({'state': 'in_production'})
            order.message_post(body=_("Production démarrée."))
            # Also update customer order state
            if order.customer_order_id.state == 'confirmed':
                order.customer_order_id.action_start()

    def action_mark_ready(self):
        """Mark OT as ready for validation when all lots are potted"""
        for order in self:
            if order.state != 'in_progress':
                raise UserError(_("L'OT doit être en cours pour être marqué prêt."))
            if any(lot.state != 'potted' for lot in order.lot_ids):
                raise UserError(_("Tous les lots doivent être empotés avant de marquer l'OT comme prêt."))
            order.state = 'ready_validation'
            order.message_post(body=_("OT prêt pour validation."))

    def action_validate(self):
        """CEO Agent validates the OT"""
        for order in self:
            if order.state != 'ready_validation':
                raise UserError(_("L'OT doit être prêt pour validation."))
            order.write({
                'state': 'done',
                'date_validated': fields.Datetime.now(),
                'validated_by_id': self.env.user.id,
            })
            order.message_post(body=_("OT validé par %s.") % self.env.user.name)
            
            # Check if all OT of the customer order are done
            customer_order = order.customer_order_id
            if all(ot.state == 'done' for ot in customer_order.transit_order_ids):
                customer_order.action_done()

    def action_cancel(self):
        for order in self:
            if order.state == 'done':
                raise UserError(_("Les OT validés ne peuvent pas être annulés."))
            order.lot_ids.filtered(lambda l: l.state != 'potted').write({'state': 'draft'})
            order.state = 'cancelled'
            order.message_post(body=_("OT annulé."))

    def action_draft(self):
        """Remettre l'OT en brouillon de façon sécurisée"""
        for order in self:
            # Ne peut remettre en brouillon que depuis certains états
            if order.state == 'done':
                raise UserError(_(
                    "Les OT validés ne peuvent pas être remis en brouillon. "
                    "Veuillez d'abord les annuler."
                ))
            if order.state == 'draft':
                continue  # Déjà en brouillon
            
            # Vérifier qu'aucun lot n'est empoté
            potted_lots = order.lot_ids.filtered(lambda l: l.state == 'potted')
            if potted_lots:
                raise UserError(_(
                    "Impossible de remettre l'OT '%s' en brouillon: "
                    "%d lot(s) sont déjà empoté(s)."
                ) % (order.name, len(potted_lots)))
            
            # Remettre les lots en brouillon aussi
            order.lot_ids.filtered(lambda l: l.state != 'potted').write({'state': 'draft'})
            order.state = 'draft'
            order.message_post(body=_("🔄 OT remis en brouillon par %s.") % self.env.user.name)

    def action_view_lots(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Lots - %s') % self.name,
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('transit_order_id', '=', self.id)],
            'context': {
                'default_transit_order_id': self.id,
                'default_product_type': self.product_type,
                'default_product_id': self.product_id.id if self.product_id else False,
            },
        }
        return action

    def action_view_potted_lots(self):
        """View only potted lots"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lots empotés - %s') % self.name,
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('transit_order_id', '=', self.id), ('state', '=', 'potted')],
        }

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def get_production_summary(self):
        """Get production summary for reporting"""
        self.ensure_one()
        return {
            'name': self.name,
            'product_type': dict(self._fields['product_type'].selection).get(self.product_type),
            'total_tonnage': self.tonnage,
            'current_tonnage': self.current_tonnage,
            'remaining': self.tonnage - self.current_tonnage,
            'progress': self.progress_percentage,
            'lots': [{
                'name': lot.name,
                'target': lot.target_tonnage,
                'current': lot.current_tonnage,
                'fill': lot.fill_percentage,
                'state': lot.state,
            } for lot in self.lot_ids.sorted('name')],
        }


class PottingVessel(models.Model):
    _name = 'potting.vessel'
    _description = 'Navire'
    _order = 'name'
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom du navire doit être unique!'),
        ('code_uniq', 'unique(code)', 'Le code du navire doit être unique!'),
    ]
    
    name = fields.Char(string="Nom du navire", required=True, index=True)
    code = fields.Char(string="Code", index=True)
    shipping_company = fields.Char(string="Compagnie maritime")
    active = fields.Boolean(string="Actif", default=True)
    
    def name_get(self):
        result = []
        for vessel in self:
            name = vessel.name
            if vessel.code:
                name = f"[{vessel.code}] {name}"
            result.append((vessel.id, name))
        return result
