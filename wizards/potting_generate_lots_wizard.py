# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math


class PottingGenerateLotsWizard(models.TransientModel):
    """Wizard to generate lots with custom max tonnage per lot."""
    
    _name = 'potting.generate.lots.wizard'
    _description = 'Wizard de génération de lots'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        readonly=True,
    )
    
    product_type = fields.Selection(
        related='transit_order_id.product_type',
        string="Type de produit",
        readonly=True,
    )
    
    product_type_display = fields.Char(
        string="Produit",
        compute='_compute_product_type_display',
    )
    
    total_tonnage = fields.Float(
        related='transit_order_id.tonnage',
        string="Tonnage total de l'OT",
        readonly=True,
    )
    
    max_tonnage_per_lot = fields.Float(
        string="Tonnage maximum par lot",
        required=True,
        help="Tonnage maximum pour chaque lot généré. "
             "Les lots seront créés avec ce tonnage maximum, "
             "sauf le dernier qui contiendra le reste.",
    )
    
    default_max_tonnage = fields.Float(
        string="Tonnage par défaut (paramètres)",
        readonly=True,
        help="Valeur par défaut définie dans les paramètres du module.",
    )
    
    estimated_lots_count = fields.Integer(
        string="Nombre de lots estimés",
        compute='_compute_estimated_lots_count',
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('product_type')
    def _compute_product_type_display(self):
        """Compute display name for product type."""
        product_labels = {
            'cocoa_mass': 'Masse de cacao',
            'cocoa_butter': 'Beurre de cacao',
            'cocoa_cake': 'Tourteau de cacao',
            'cocoa_powder': 'Poudre de cacao',
        }
        for wizard in self:
            wizard.product_type_display = product_labels.get(
                wizard.product_type, 
                wizard.product_type or ''
            )

    @api.depends('total_tonnage', 'max_tonnage_per_lot')
    def _compute_estimated_lots_count(self):
        """Compute estimated number of lots to be created."""
        for wizard in self:
            if wizard.max_tonnage_per_lot and wizard.max_tonnage_per_lot > 0:
                wizard.estimated_lots_count = math.ceil(
                    wizard.total_tonnage / wizard.max_tonnage_per_lot
                )
            else:
                wizard.estimated_lots_count = 0

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('max_tonnage_per_lot')
    def _onchange_max_tonnage_per_lot(self):
        """Validate max tonnage per lot."""
        if self.max_tonnage_per_lot and self.max_tonnage_per_lot <= 0:
            return {
                'warning': {
                    'title': _("Attention"),
                    'message': _("Le tonnage maximum par lot doit être supérieur à 0."),
                }
            }

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        """Set default values based on transit order context."""
        res = super().default_get(fields_list)
        
        # Get transit order from context
        transit_order_id = self._context.get('active_id')
        if transit_order_id:
            transit_order = self.env['potting.transit.order'].browse(transit_order_id)
            res['transit_order_id'] = transit_order_id
            
            # Get default max tonnage from settings for this product type
            if transit_order.product_type:
                default_tonnage = self.env['res.config.settings'].get_max_tonnage_for_product(
                    transit_order.product_type
                )
                res['max_tonnage_per_lot'] = default_tonnage
                res['default_max_tonnage'] = default_tonnage
        
        return res

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_generate_lots(self):
        """Generate lots with the specified max tonnage per lot."""
        self.ensure_one()
        
        transit_order = self.transit_order_id
        
        # Validations
        if transit_order.state != 'draft':
            raise UserError(_("Les lots ne peuvent être générés que pour les OT en brouillon."))
        
        if transit_order.lot_ids:
            raise UserError(_("Des lots existent déjà pour cet OT. Supprimez-les d'abord."))
        
        if not self.max_tonnage_per_lot or self.max_tonnage_per_lot <= 0:
            raise UserError(_("Le tonnage maximum par lot doit être supérieur à 0."))
        
        if not transit_order.tonnage or transit_order.tonnage <= 0:
            raise UserError(_("Le tonnage de l'OT doit être supérieur à 0."))
        
        if not transit_order.product_type:
            raise UserError(_("Veuillez sélectionner un type de produit."))
        
        # Calculate number of lots needed
        max_tonnage = self.max_tonnage_per_lot
        num_lots = math.ceil(transit_order.tonnage / max_tonnage)
        
        # Create lots
        lot_vals_list = []
        remaining_tonnage = transit_order.tonnage
        
        for i in range(num_lots):
            lot_tonnage = min(max_tonnage, remaining_tonnage)
            remaining_tonnage -= lot_tonnage
            
            # Get unique lot name from sequence
            lot_name = transit_order._get_unique_lot_name()
            
            lot_vals_list.append({
                'name': lot_name,
                'base_name': lot_name,  # Référence de base sans suffixe de certification
                'transit_order_id': transit_order.id,
                'product_type': transit_order.product_type,
                'product_id': transit_order.product_id.id if transit_order.product_id else False,
                'target_tonnage': lot_tonnage,
                'state': 'draft',
            })
        
        self.env['potting.lot'].create(lot_vals_list)
        transit_order.state = 'lots_generated'
        transit_order.message_post(
            body=_("%d lots générés pour cet OT (tonnage max par lot: %.2f T).") % (
                num_lots, max_tonnage
            )
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Lots générés'),
                'message': _('%d lots ont été créés avec un tonnage max de %.2f T par lot.') % (
                    num_lots, max_tonnage
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_cancel(self):
        """Cancel the wizard."""
        return {'type': 'ir.actions.act_window_close'}
