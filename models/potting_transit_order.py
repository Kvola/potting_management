# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math


class PottingTransitOrder(models.Model):
    _name = 'potting.transit.order'
    _description = 'Ordre de Transit (OT)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string="Numéro OT",
        required=True,
        tracking=True,
        index=True
    )
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    customer_id = fields.Many2one(
        related='customer_order_id.customer_id',
        string="Client",
        store=True
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
    ], string="Type de produit", required=True, tracking=True)
    
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
        help="Tonnage total de l'OT"
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
        tracking=True
    )
    
    lot_ids = fields.One2many(
        'potting.lot',
        'transit_order_id',
        string="Lots"
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
    
    progress_percentage = fields.Float(
        string="Progression (%)",
        compute='_compute_progress',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('lots_generated', 'Lots générés'),
        ('in_progress', 'En cours'),
        ('ready_validation', 'Prêt pour validation'),
        ('done', 'Validé'),
        ('cancelled', 'Annulé'),
    ], string="État", default='draft', tracking=True)
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )
    
    date_created = fields.Date(
        string="Date de création",
        default=fields.Date.context_today
    )

    @api.depends('lot_ids', 'lot_ids.state')
    def _compute_lot_count(self):
        for order in self:
            order.lot_count = len(order.lot_ids)
            order.potted_lot_count = len(order.lot_ids.filtered(lambda l: l.state == 'potted'))

    @api.depends('lot_ids.name')
    def _compute_lot_range(self):
        for order in self:
            if order.lot_ids:
                lot_names = order.lot_ids.mapped('name')
                if lot_names:
                    order.lot_range = f"{min(lot_names)} à {max(lot_names)}"
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

    def action_generate_lots(self):
        """Generate lots based on tonnage and product type"""
        self.ensure_one()
        
        if self.lot_ids:
            raise UserError(_("Des lots existent déjà pour cet OT. Supprimez-les d'abord."))
        
        if not self.tonnage or self.tonnage <= 0:
            raise UserError(_("Le tonnage doit être supérieur à 0."))
        
        if not self.product_type:
            raise UserError(_("Veuillez sélectionner un type de produit."))
        
        # Get max tonnage for this product type
        max_tonnage = self.env['res.config.settings'].get_max_tonnage_for_product(self.product_type)
        
        # Calculate number of lots needed
        num_lots = math.ceil(self.tonnage / max_tonnage)
        
        # Get next lot sequence
        sequence = self.env['ir.sequence'].next_by_code('potting.lot')
        if sequence:
            base_number = int(sequence.replace('LOT', '').replace('T', ''))
        else:
            base_number = 10001
        
        # Create lots
        lot_vals_list = []
        remaining_tonnage = self.tonnage
        
        for i in range(num_lots):
            lot_tonnage = min(max_tonnage, remaining_tonnage)
            remaining_tonnage -= lot_tonnage
            
            lot_name = f"T{base_number + i}RA"
            
            lot_vals_list.append({
                'name': lot_name,
                'transit_order_id': self.id,
                'product_type': self.product_type,
                'product_id': self.product_id.id if self.product_id else False,
                'target_tonnage': lot_tonnage,
                'state': 'draft',
            })
        
        self.env['potting.lot'].create(lot_vals_list)
        self.state = 'lots_generated'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Lots générés'),
                'message': _('%d lots ont été créés pour cet OT.') % num_lots,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_start_production(self):
        self.write({'state': 'in_progress'})
        # Also update customer order state
        for order in self:
            if order.customer_order_id.state == 'confirmed':
                order.customer_order_id.state = 'in_progress'

    def action_mark_ready(self):
        """Mark OT as ready for validation when all lots are potted"""
        for order in self:
            if any(lot.state != 'potted' for lot in order.lot_ids):
                raise UserError(_("Tous les lots doivent être empotés avant de marquer l'OT comme prêt."))
            order.state = 'ready_validation'

    def action_validate(self):
        """CEO Agent validates the OT"""
        for order in self:
            if order.state != 'ready_validation':
                raise UserError(_("L'OT doit être prêt pour validation."))
            order.state = 'done'
            
            # Check if all OT of the customer order are done
            customer_order = order.customer_order_id
            if all(ot.state == 'done' for ot in customer_order.transit_order_ids):
                customer_order.action_done()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_view_lots(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lots'),
            'res_model': 'potting.lot',
            'view_mode': 'tree,form',
            'domain': [('transit_order_id', '=', self.id)],
            'context': {'default_transit_order_id': self.id},
        }


class PottingVessel(models.Model):
    _name = 'potting.vessel'
    _description = 'Navire'
    
    name = fields.Char(string="Nom du navire", required=True)
    code = fields.Char(string="Code")
    shipping_company = fields.Char(string="Compagnie maritime")
    active = fields.Boolean(string="Actif", default=True)
