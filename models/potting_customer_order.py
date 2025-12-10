# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingCustomerOrder(models.Model):
    _name = 'potting.customer.order'
    _description = 'Commande Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _check_company_auto = True

    # SQL Constraints
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 
         'La référence de la commande doit être unique par société!'),
    ]

    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        index=True
    )
    
    customer_id = fields.Many2one(
        'res.partner',
        string="Client",
        required=True,
        tracking=True,
        default=lambda self: self._get_default_customer(),
        domain="[('is_company', '=', True)]",
        check_company=True
    )
    
    date_order = fields.Date(
        string="Date de commande",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True
    )
    
    date_expected = fields.Date(
        string="Date de livraison prévue",
        tracking=True
    )
    
    transit_order_ids = fields.One2many(
        'potting.transit.order',
        'customer_order_id',
        string="Ordres de Transit",
        copy=True
    )
    
    transit_order_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_transit_order_count',
        store=True
    )
    
    total_tonnage = fields.Float(
        string="Tonnage total (T)",
        compute='_compute_total_tonnage',
        store=True,
        digits='Product Unit of Measure'
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
        ('cancelled', 'Annulée'),
    ], string="État", default='draft', tracking=True, index=True, copy=False)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string="Responsable",
        default=lambda self: self.env.user,
        tracking=True,
        index=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    
    # Computed fields for statistics
    potted_tonnage = fields.Float(
        string="Tonnage empoté (T)",
        compute='_compute_potted_stats',
        store=True,
        digits='Product Unit of Measure'
    )
    
    progress_percentage = fields.Float(
        string="Progression (%)",
        compute='_compute_potted_stats',
        store=True
    )
    
    is_late = fields.Boolean(
        string="En retard",
        compute='_compute_is_late',
        store=True
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('date_expected', 'date_order')
    def _check_dates(self):
        for order in self:
            if order.date_expected and order.date_order and order.date_expected < order.date_order:
                raise ValidationError(_(
                    "La date de livraison prévue ne peut pas être antérieure à la date de commande."
                ))

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    @api.model
    def _get_default_customer(self):
        """Get the default customer from settings"""
        try:
            default_customer_id = self.env['ir.config_parameter'].sudo().get_param(
                'potting_management.default_customer_id'
            )
            if default_customer_id:
                partner = self.env['res.partner'].browse(int(default_customer_id))
                if partner.exists():
                    return partner
        except (ValueError, TypeError):
            pass
        return False

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('potting.customer.order') or _('Nouveau')
        return super().create(vals_list)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'name': _('Nouveau'),
            'state': 'draft',
            'date_order': fields.Date.context_today(self),
        })
        return super().copy(default)

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les commandes en brouillon ou annulées. "
                    "La commande '%s' est en état '%s'."
                ) % (order.name, dict(order._fields['state'].selection).get(order.state)))
            # Vérifier qu'aucun OT n'a de lots avec production
            for ot in order.transit_order_ids:
                if any(lot.current_tonnage > 0 for lot in ot.lot_ids):
                    raise UserError(_(
                        "Impossible de supprimer la commande '%s': "
                        "l'OT '%s' a des lots avec de la production."
                    ) % (order.name, ot.name))
        return super().unlink()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('transit_order_ids')
    def _compute_transit_order_count(self):
        for order in self:
            order.transit_order_count = len(order.transit_order_ids)

    @api.depends('transit_order_ids.tonnage')
    def _compute_total_tonnage(self):
        for order in self:
            order.total_tonnage = sum(order.transit_order_ids.mapped('tonnage'))

    @api.depends('transit_order_ids.lot_ids.current_tonnage', 'transit_order_ids.lot_ids.state', 'total_tonnage')
    def _compute_potted_stats(self):
        for order in self:
            potted_lots = order.transit_order_ids.lot_ids.filtered(lambda l: l.state == 'potted')
            order.potted_tonnage = sum(potted_lots.mapped('current_tonnage'))
            if order.total_tonnage > 0:
                order.progress_percentage = (order.potted_tonnage / order.total_tonnage) * 100
            else:
                order.progress_percentage = 0.0

    @api.depends('date_expected', 'state')
    def _compute_is_late(self):
        today = fields.Date.context_today(self)
        for order in self:
            order.is_late = (
                order.date_expected and 
                order.date_expected < today and 
                order.state not in ('done', 'cancelled')
            )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """Update consignee on transit orders when customer changes"""
        if self.customer_id and self.transit_order_ids:
            for ot in self.transit_order_ids:
                if not ot.consignee_id:
                    ot.consignee_id = self.customer_id

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_("Seules les commandes en brouillon peuvent être confirmées."))
            if not order.transit_order_ids:
                raise UserError(_("Vous devez ajouter au moins un Ordre de Transit avant de confirmer."))
            order.state = 'confirmed'
            order.message_post(body=_("Commande confirmée."))

    def action_start(self):
        for order in self:
            if order.state != 'confirmed':
                raise UserError(_("Seules les commandes confirmées peuvent être démarrées."))
            order.state = 'in_progress'
            order.message_post(body=_("Production démarrée."))

    def action_done(self):
        for order in self:
            if order.state != 'in_progress':
                raise UserError(_("Seules les commandes en cours peuvent être terminées."))
            # Check if all transit orders are done
            if any(ot.state != 'done' for ot in order.transit_order_ids):
                raise UserError(_("Tous les Ordres de Transit doivent être terminés avant de clôturer la commande."))
            order.state = 'done'
            order.message_post(body=_("Commande terminée avec succès."))

    def action_cancel(self):
        for order in self:
            if order.state == 'done':
                raise UserError(_("Les commandes terminées ne peuvent pas être annulées."))
            # Cancel all transit orders
            order.transit_order_ids.filtered(lambda ot: ot.state != 'cancelled').action_cancel()
            order.state = 'cancelled'
            order.message_post(body=_("Commande annulée."))

    def action_draft(self):
        """Remettre la commande en brouillon de façon sécurisée"""
        for order in self:
            # Ne peut remettre en brouillon que depuis certains états
            if order.state == 'done':
                raise UserError(_(
                    "Les commandes terminées ne peuvent pas être remises en brouillon. "
                    "Veuillez d'abord les annuler."
                ))
            if order.state == 'draft':
                continue  # Déjà en brouillon
            
            # Vérifier qu'aucun OT n'a des lots empotés
            for ot in order.transit_order_ids:
                potted_lots = ot.lot_ids.filtered(lambda l: l.state == 'potted')
                if potted_lots:
                    raise UserError(_(
                        "Impossible de remettre la commande en brouillon: "
                        "l'OT '%s' a %d lot(s) empoté(s)."
                    ) % (ot.name, len(potted_lots)))
            
            # Remettre les OT en brouillon aussi
            for ot in order.transit_order_ids:
                if ot.state not in ('draft', 'cancelled'):
                    ot.action_draft()
            
            order.state = 'draft'
            order.message_post(body=_("🔄 Commande remise en brouillon par %s.") % self.env.user.name)

    def action_view_transit_orders(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Ordres de Transit'),
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,kanban,form',
            'domain': [('customer_order_id', '=', self.id)],
            'context': {
                'default_customer_order_id': self.id,
                'default_consignee_id': self.customer_id.id,
            },
        }
        if len(self.transit_order_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.transit_order_ids.id
        return action

    def action_view_lots(self):
        """View all lots linked to this customer order"""
        self.ensure_one()
        lots = self.transit_order_ids.lot_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Lots'),
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('id', 'in', lots.ids)],
        }
        return action

    def action_open_create_ot_wizard(self):
        """Ouvrir le wizard de création d'OT"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Créer des Ordres de Transit"),
            'res_model': 'potting.create.ot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_order_id': self.id,
            },
        }

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def get_summary_data(self):
        """Get summary data for reporting"""
        self.ensure_one()
        return {
            'name': self.name,
            'customer': self.customer_id.name,
            'date_order': self.date_order,
            'date_expected': self.date_expected,
            'total_tonnage': self.total_tonnage,
            'potted_tonnage': self.potted_tonnage,
            'progress': self.progress_percentage,
            'transit_orders': [{
                'name': ot.name,
                'product_type': ot.product_type,
                'tonnage': ot.tonnage,
                'lots': len(ot.lot_ids),
                'potted_lots': ot.potted_lot_count,
                'state': ot.state,
            } for ot in self.transit_order_ids],
        }
