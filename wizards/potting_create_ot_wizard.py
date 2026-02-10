# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingCreateOTWizard(models.TransientModel):
    """Wizard pour créer un OT depuis une commande client.
    
    Ce wizard affiche un formulaire complet pour créer un nouvel OT
    directement depuis la commande client, en sélectionnant une Formule.
    """
    _name = 'potting.create.ot.wizard'
    _description = "Assistant de création d'OT"

    # =========================================================================
    # FIELDS - Informations de la commande (readonly)
    # =========================================================================
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        required=True,
        readonly=True,
        ondelete='cascade',
        help="La commande client pour laquelle créer l'OT."
    )
    
    customer_id = fields.Many2one(
        related='customer_order_id.customer_id',
        string="Client",
        readonly=True
    )
    
    campaign_id = fields.Many2one(
        'potting.campaign',
        string="Campagne Café-Cacao",
        required=True,
        domain="[('state', 'in', ['draft', 'active'])]",
        default=lambda self: self._get_default_campaign(),
        help="Campagne café-cacao pour cet OT"
    )
    
    company_id = fields.Many2one(
        related='customer_order_id.company_id',
        string="Société",
        readonly=True
    )

    # =========================================================================
    # FIELDS - Sélection de la Formule (OBLIGATOIRE)
    # =========================================================================
    
    formule_id = fields.Many2one(
        'potting.formule',
        string="Formule (FO)",
        required=True,
        domain="[('state', 'in', ['validated', 'paid']), "
               "('transit_order_id', '=', False), "
               "('company_id', '=', company_id)]",
        help="Sélectionnez une Formule validée et non liée à un OT. "
             "La Formule définit le tonnage et le type de produit."
    )
    
    formule_tonnage = fields.Float(
        string="Tonnage Formule (T)",
        related='formule_id.tonnage',
        readonly=True,
        help="Tonnage défini dans la Formule"
    )
    
    formule_product_type = fields.Selection(
        related='formule_id.product_type',
        string="Type produit Formule",
        readonly=True
    )
    
    formule_reference = fields.Char(
        string="Réf. CCC",
        related='formule_id.reference_ccc',
        readonly=True
    )

    # =========================================================================
    # FIELDS - Informations de l'OT à créer
    # =========================================================================
    
    consignee_id = fields.Many2one(
        'res.partner',
        string="Destinataire (Consignee)",
        required=True,
        help="Le destinataire de la marchandise"
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit",
       compute='_compute_from_formule',
       store=True, readonly=False,
       help="Hérité de la Formule sélectionnée")
    
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        domain="[('potting_product_type', '=', product_type)]",
        help="Produit spécifique (optionnel)"
    )
    
    tonnage = fields.Float(
        string="Tonnage (T)",
        compute='_compute_from_formule',
        store=True, readonly=False,
        digits='Product Unit of Measure',
        help="Tonnage hérité de la Formule (modifiable)"
    )
    
    vessel_id = fields.Many2one(
        'potting.vessel',
        string="Navire",
        help="Navire pour le transport"
    )
    
    pod = fields.Char(
        string="Port de déchargement (POD)",
        help="Port of Discharge - Port de destination"
    )
    
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string="Taille conteneur (TC)", default='20')
    
    booking_number = fields.Char(
        string="Numéro de réservation (Booking)",
        help="Numéro de réservation du transporteur"
    )
    
    note = fields.Text(
        string="Notes",
        help="Notes ou instructions particulières"
    )

    # =========================================================================
    # DEFAULT METHODS
    # =========================================================================
    
    @api.model
    def _get_default_campaign(self):
        """Get the default campaign (current active campaign).
        
        Returns:
            potting.campaign: The current active campaign or False
        """
        return self.env['potting.campaign'].get_current_campaign()
    
    @api.model
    def default_get(self, fields_list):
        """Pré-remplit le destinataire avec le client de la commande."""
        res = super().default_get(fields_list)
        
        # Récupérer la commande depuis le contexte
        customer_order_id = res.get('customer_order_id') or self.env.context.get('default_customer_order_id')
        if customer_order_id:
            order = self.env['potting.customer.order'].browse(customer_order_id)
            if order.exists() and order.customer_id:
                res['consignee_id'] = order.customer_id.id
        
        return res

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('formule_id')
    def _compute_from_formule(self):
        """Hérite le tonnage et le type de produit de la Formule sélectionnée."""
        for wizard in self:
            if wizard.formule_id:
                wizard.tonnage = wizard.formule_id.tonnage
                wizard.product_type = wizard.formule_id.product_type
            else:
                wizard.tonnage = 0.0
                wizard.product_type = False

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('formule_id')
    def _onchange_formule_id(self):
        """Met à jour les champs quand la formule change."""
        if self.formule_id:
            # Récupérer le POD depuis la formule si disponible
            if self.formule_id.port_destination:
                self.pod = self.formule_id.port_destination
    
    @api.onchange('product_type')
    def _onchange_product_type(self):
        """Reset product when product type changes"""
        if self.product_id and self.product_id.potting_product_type != self.product_type:
            self.product_id = False

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_create_ot(self):
        """Crée l'OT et retourne à la commande."""
        self.ensure_one()
        
        # Validation
        if not self.formule_id:
            raise ValidationError(_("Veuillez sélectionner une Formule."))
        
        if self.tonnage <= 0:
            raise ValidationError(_("Le tonnage doit être supérieur à 0."))
        
        # Vérifier que la formule est toujours disponible
        if self.formule_id.transit_order_id:
            raise ValidationError(_(
                "La Formule %s est déjà liée à l'OT %s."
            ) % (self.formule_id.display_name, self.formule_id.transit_order_id.name))
        
        # Créer l'OT
        ot_vals = {
            'formule_id': self.formule_id.id,
            'customer_order_id': self.customer_order_id.id,
            'campaign_id': self.campaign_id.id,
            'consignee_id': self.consignee_id.id,
            'product_type': self.product_type,
            'product_id': self.product_id.id if self.product_id else False,
            'tonnage': self.tonnage,
            'vessel_id': self.vessel_id.id if self.vessel_id else False,
            'pod': self.pod,
            'container_size': self.container_size,
            'booking_number': self.booking_number,
            'note': self.note,
            'is_created_from_order': True,
        }
        
        ot = self.env['potting.transit.order'].create(ot_vals)
        
        # Message de succès sur la commande
        self.customer_order_id.message_post(
            body=_("✅ Ordre de Transit <b>%s</b> créé avec succès:<br/>"
                   "• Formule: %s<br/>"
                   "• Tonnage: %.2f T<br/>"
                   "• Produit: %s") % (
                ot.name,
                self.formule_id.name,
                self.tonnage,
                dict(self._fields['product_type'].selection).get(self.product_type)
            ),
            message_type='notification'
        )
        
        # Retourner à la commande
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'potting.customer.order',
            'res_id': self.customer_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_and_new(self):
        """Crée l'OT et ouvre un nouveau wizard pour en créer un autre."""
        self.ensure_one()
        
        # Validation
        if not self.formule_id:
            raise ValidationError(_("Veuillez sélectionner une Formule."))
        
        if self.tonnage <= 0:
            raise ValidationError(_("Le tonnage doit être supérieur à 0."))
        
        # Vérifier que la formule est toujours disponible
        if self.formule_id.transit_order_id:
            raise ValidationError(_(
                "La Formule %s est déjà liée à l'OT %s."
            ) % (self.formule_id.display_name, self.formule_id.transit_order_id.name))
        
        # Créer l'OT
        ot_vals = {
            'formule_id': self.formule_id.id,
            'customer_order_id': self.customer_order_id.id,
            'campaign_id': self.campaign_id.id,
            'consignee_id': self.consignee_id.id,
            'product_type': self.product_type,
            'product_id': self.product_id.id if self.product_id else False,
            'tonnage': self.tonnage,
            'vessel_id': self.vessel_id.id if self.vessel_id else False,
            'pod': self.pod,
            'container_size': self.container_size,
            'booking_number': self.booking_number,
            'note': self.note,
            'is_created_from_order': True,
        }
        
        ot = self.env['potting.transit.order'].create(ot_vals)
        
        # Message de succès sur la commande
        self.customer_order_id.message_post(
            body=_("✅ Ordre de Transit <b>%s</b> créé avec succès (Formule: %s, %.2f T).") % (
                ot.name,
                self.formule_id.name,
                self.tonnage
            ),
            message_type='notification'
        )
        
        # Ouvrir un nouveau wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _("Créer un Ordre de Transit"),
            'res_model': 'potting.create.ot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_order_id': self.customer_order_id.id,
                'default_consignee_id': self.consignee_id.id,
                'default_campaign_id': self.campaign_id.id,
                'default_vessel_id': self.vessel_id.id if self.vessel_id else False,
                'default_pod': self.pod,
                'default_container_size': self.container_size,
            },
        }
    
    def action_view_ot(self):
        """Crée l'OT et ouvre sa fiche."""
        self.ensure_one()
        
        # Validation
        if not self.formule_id:
            raise ValidationError(_("Veuillez sélectionner une Formule."))
        
        if self.tonnage <= 0:
            raise ValidationError(_("Le tonnage doit être supérieur à 0."))
        
        # Vérifier que la formule est toujours disponible
        if self.formule_id.transit_order_id:
            raise ValidationError(_(
                "La Formule %s est déjà liée à l'OT %s."
            ) % (self.formule_id.display_name, self.formule_id.transit_order_id.name))
        
        # Créer l'OT
        ot_vals = {
            'formule_id': self.formule_id.id,
            'customer_order_id': self.customer_order_id.id,
            'campaign_id': self.campaign_id.id,
            'consignee_id': self.consignee_id.id,
            'product_type': self.product_type,
            'product_id': self.product_id.id if self.product_id else False,
            'tonnage': self.tonnage,
            'vessel_id': self.vessel_id.id if self.vessel_id else False,
            'pod': self.pod,
            'container_size': self.container_size,
            'booking_number': self.booking_number,
            'note': self.note,
            'is_created_from_order': True,
        }
        
        ot = self.env['potting.transit.order'].create(ot_vals)
        
        # Message de succès sur la commande
        self.customer_order_id.message_post(
            body=_("✅ Ordre de Transit <b>%s</b> créé avec succès (Formule: %s, %.2f T).") % (
                ot.name,
                self.formule_id.name,
                self.tonnage
            ),
            message_type='notification'
        )
        
        # Ouvrir la fiche de l'OT créé
        return {
            'type': 'ir.actions.act_window',
            'name': ot.name,
            'res_model': 'potting.transit.order',
            'res_id': ot.id,
            'view_mode': 'form',
            'target': 'current',
        }