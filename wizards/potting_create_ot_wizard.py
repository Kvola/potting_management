# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingCreateOTWizard(models.TransientModel):
    """Wizard pour créer un ou plusieurs OT depuis une commande client.
    
    Ce wizard permet de:
    - Renseigner les informations d'un OT rapidement
    - Créer plusieurs OT en une seule opération
    - Pré-remplir les informations depuis la commande
    """
    _name = 'potting.create.ot.wizard'
    _description = "Assistant de création d'OT"

    # =========================================================================
    # FIELDS
    # =========================================================================
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        required=True,
        readonly=True,
        ondelete='cascade',
        help="La commande client pour laquelle créer les OT."
    )
    
    customer_id = fields.Many2one(
        related='customer_order_id.customer_id',
        string="Client",
        readonly=True
    )
    
    company_id = fields.Many2one(
        related='customer_order_id.company_id',
        string="Société",
        readonly=True
    )
    
    line_ids = fields.One2many(
        'potting.create.ot.wizard.line',
        'wizard_id',
        string="Lignes OT",
        help="Les OT à créer pour cette commande."
    )
    
    # Champs pour ajout rapide d'une ligne
    quick_consignee_id = fields.Many2one(
        'res.partner',
        string="Destinataire",
        domain="[('is_potting_consignee', '=', True)]"
    )
    
    quick_product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit")
    
    quick_tonnage = fields.Float(
        string="Tonnage (T)",
        digits='Product Unit of Measure'
    )
    
    quick_vessel_name = fields.Char(
        string="Nom du navire"
    )
    
    quick_pod = fields.Char(
        string="Port de déchargement"
    )
    
    quick_container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string="Taille conteneur", default='20')
    
    quick_booking_number = fields.Char(
        string="N° Booking"
    )
    
    total_tonnage = fields.Float(
        string="Tonnage total",
        compute='_compute_total_tonnage',
        digits='Product Unit of Measure'
    )
    
    line_count = fields.Integer(
        string="Nombre d'OT",
        compute='_compute_line_count'
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('line_ids.tonnage')
    def _compute_total_tonnage(self):
        """Calcule le tonnage total des lignes."""
        for wizard in self:
            wizard.total_tonnage = sum(wizard.line_ids.mapped('tonnage'))
    
    @api.depends('line_ids')
    def _compute_line_count(self):
        """Calcule le nombre de lignes."""
        for wizard in self:
            wizard.line_count = len(wizard.line_ids)

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('customer_order_id')
    def _onchange_customer_order_id(self):
        """Pré-remplit le destinataire avec le client de la commande."""
        if self.customer_order_id and self.customer_order_id.customer_id:
            self.quick_consignee_id = self.customer_order_id.customer_id

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_add_line(self):
        """Ajoute une ligne OT avec les valeurs rapides."""
        self.ensure_one()
        
        # Validation des champs obligatoires
        if not self.quick_consignee_id:
            raise UserError(_("Veuillez sélectionner un destinataire."))
        if not self.quick_product_type:
            raise UserError(_("Veuillez sélectionner un type de produit."))
        if not self.quick_tonnage or self.quick_tonnage <= 0:
            raise UserError(_("Veuillez saisir un tonnage valide (supérieur à 0)."))
        
        # Créer la ligne
        self.env['potting.create.ot.wizard.line'].create({
            'wizard_id': self.id,
            'consignee_id': self.quick_consignee_id.id,
            'product_type': self.quick_product_type,
            'tonnage': self.quick_tonnage,
            'vessel_name': self.quick_vessel_name,
            'pod': self.quick_pod,
            'container_size': self.quick_container_size,
            'booking_number': self.quick_booking_number,
        })
        
        # Réinitialiser les champs de saisie rapide (sauf destinataire et navire)
        self.quick_product_type = False
        self.quick_tonnage = 0
        self.quick_booking_number = False
        
        # Retourner l'action pour rester sur le wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'potting.create.ot.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
    
    def action_create_ot(self):
        """Crée les OT à partir des lignes du wizard."""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_("Veuillez ajouter au moins une ligne OT."))
        
        created_ots = self.env['potting.transit.order']
        
        for line in self.line_ids:
            # Validation de la ligne
            if line.tonnage <= 0:
                raise ValidationError(_(
                    "Le tonnage de la ligne pour '%s' doit être supérieur à 0."
                ) % line.consignee_id.name)
            
            # Créer l'OT
            ot_vals = {
                'customer_order_id': self.customer_order_id.id,
                'consignee_id': line.consignee_id.id,
                'product_type': line.product_type,
                'tonnage': line.tonnage,
                'vessel_name': line.vessel_name,
                'pod': line.pod,
                'container_size': line.container_size,
                'booking_number': line.booking_number,
                'is_created_from_order': True,
            }
            
            ot = self.env['potting.transit.order'].create(ot_vals)
            created_ots |= ot
        
        # Message de succès
        message = _("✅ %d Ordre(s) de Transit créé(s) avec succès pour la commande %s.") % (
            len(created_ots),
            self.customer_order_id.name
        )
        
        # Poster un message sur la commande
        self.customer_order_id.message_post(
            body=message,
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
        """Crée les OT et ouvre un nouveau wizard."""
        self.action_create_ot()
        
        # Ouvrir un nouveau wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'potting.create.ot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_order_id': self.customer_order_id.id,
            },
        }


class PottingCreateOTWizardLine(models.TransientModel):
    """Ligne de wizard pour la création d'OT."""
    _name = 'potting.create.ot.wizard.line'
    _description = "Ligne de création d'OT"

    wizard_id = fields.Many2one(
        'potting.create.ot.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade'
    )
    
    consignee_id = fields.Many2one(
        'res.partner',
        string="Destinataire",
        required=True
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit", required=True)
    
    tonnage = fields.Float(
        string="Tonnage (T)",
        required=True,
        digits='Product Unit of Measure'
    )
    
    vessel_name = fields.Char(
        string="Navire"
    )
    
    pod = fields.Char(
        string="POD"
    )
    
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string="TC", default='20')
    
    booking_number = fields.Char(
        string="N° Booking"
    )
