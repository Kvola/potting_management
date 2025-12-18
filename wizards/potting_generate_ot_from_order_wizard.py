# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import math


class PottingGenerateOTFromOrderWizard(models.TransientModel):
    """Wizard pour générer automatiquement des OT depuis une commande client.
    
    Ce wizard permet de:
    - Afficher le tonnage total de la commande client
    - Configurer le tonnage par défaut par OT (selon le produit)
    - Générer automatiquement plusieurs OT en fonction du tonnage total
    """
    _name = 'potting.generate.ot.from.order.wizard'
    _description = "Assistant de génération automatique d'OT"

    # =========================================================================
    # FIELDS - Informations de la commande (readonly)
    # =========================================================================
    
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Commande client",
        required=True,
        readonly=True,
        ondelete='cascade',
        help="La commande client pour laquelle générer les OT."
    )
    
    customer_id = fields.Many2one(
        related='customer_order_id.customer_id',
        string="Client",
        readonly=True
    )
    
    campaign_period = fields.Char(
        related='customer_order_id.campaign_period',
        string="Campagne",
        readonly=True,
        help="Période de la campagne Café-Cacao de la commande"
    )
    
    company_id = fields.Many2one(
        related='customer_order_id.company_id',
        string="Société",
        readonly=True
    )
    
    existing_ot_count = fields.Integer(
        string="OT existants",
        compute='_compute_existing_ot_count',
        help="Nombre d'OT déjà créés pour cette commande"
    )
    
    existing_tonnage = fields.Float(
        string="Tonnage existant (T)",
        compute='_compute_existing_ot_count',
        digits='Product Unit of Measure',
        help="Tonnage total des OT déjà créés pour cette commande"
    )
    
    contract_tonnage = fields.Float(
        string="Tonnage du contrat (T)",
        related='customer_order_id.contract_tonnage',
        readonly=True,
        digits='Product Unit of Measure'
    )
    
    remaining_contract_tonnage = fields.Float(
        string="Tonnage restant disponible (T)",
        compute='_compute_existing_ot_count',
        digits='Product Unit of Measure',
        help="Tonnage encore disponible pour créer des OT"
    )

    # =========================================================================
    # FIELDS - Configuration de la génération
    # =========================================================================
    
    total_tonnage = fields.Float(
        string="Tonnage à générer (T)",
        required=True,
        digits='Product Unit of Measure',
        help="Tonnage total pour lequel générer des OT (max = tonnage restant du contrat)"
    )
    
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
    ], string="Type de produit", required=True)
    
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        domain="[('potting_product_type', '=', product_type)]",
        help="Produit spécifique (optionnel). Permet de récupérer le tonnage par défaut."
    )
    
    tonnage_per_ot = fields.Float(
        string="Tonnage par OT (T)",
        required=True,
        digits='Product Unit of Measure',
        default=0.0,
        help="Tonnage pour chaque OT à générer. "
             "Peut être configuré par défaut sur le produit."
    )
    
    ot_count_to_generate = fields.Integer(
        string="Nombre d'OT à générer",
        compute='_compute_ot_count_to_generate',
        help="Nombre d'OT qui seront créés en fonction du tonnage total et du tonnage par OT"
    )
    
    last_ot_tonnage = fields.Float(
        string="Tonnage dernier OT (T)",
        compute='_compute_ot_count_to_generate',
        digits='Product Unit of Measure',
        help="Tonnage du dernier OT (peut être différent si le reste n'est pas exact)"
    )
    
    vessel_id = fields.Many2one(
        'potting.vessel',
        string="Navire",
        help="Navire pour le transport (appliqué à tous les OT générés)"
    )
    
    pod = fields.Char(
        string="Port de déchargement (POD)",
        help="Port of Discharge - Port de destination"
    )
    
    container_size = fields.Selection([
        ('20', "20'"),
        ('40', "40'"),
    ], string="Taille conteneur (TC)", default='20')
    
    note = fields.Text(
        string="Notes",
        help="Notes ou instructions particulières (appliquées à tous les OT)"
    )

    # =========================================================================
    # DEFAULT METHODS
    # =========================================================================
    
    @api.model
    def default_get(self, fields_list):
        """Pré-remplit le wizard avec les infos de la commande."""
        res = super().default_get(fields_list)
        
        # Récupérer la commande depuis le contexte
        customer_order_id = res.get('customer_order_id') or self.env.context.get('default_customer_order_id')
        if customer_order_id:
            order = self.env['potting.customer.order'].browse(customer_order_id)
            if order.exists():
                # Destinataire par défaut = client
                if order.customer_id:
                    res['consignee_id'] = order.customer_id.id
                
                # Tonnage par défaut = tonnage contrat - tonnage OT existants
                if order.contract_tonnage:
                    existing_tonnage = sum(order.transit_order_ids.mapped('tonnage'))
                    remaining = order.contract_tonnage - existing_tonnage
                    res['total_tonnage'] = max(0, remaining)
                
                # Type de produit par défaut
                if order.product_type:
                    res['product_type'] = order.product_type
        
        return res

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('customer_order_id', 'customer_order_id.contract_tonnage', 'customer_order_id.transit_order_ids.tonnage')
    def _compute_existing_ot_count(self):
        """Calcule le nombre et tonnage des OT existants, et le tonnage restant."""
        for wizard in self:
            if wizard.customer_order_id:
                wizard.existing_ot_count = len(wizard.customer_order_id.transit_order_ids)
                wizard.existing_tonnage = sum(wizard.customer_order_id.transit_order_ids.mapped('tonnage'))
                # Calculer le tonnage restant
                if wizard.customer_order_id.contract_tonnage > 0:
                    wizard.remaining_contract_tonnage = max(0, wizard.customer_order_id.contract_tonnage - wizard.existing_tonnage)
                else:
                    wizard.remaining_contract_tonnage = 0.0
            else:
                wizard.existing_ot_count = 0
                wizard.existing_tonnage = 0.0
                wizard.remaining_contract_tonnage = 0.0
    
    @api.depends('total_tonnage', 'tonnage_per_ot')
    def _compute_ot_count_to_generate(self):
        """Calcule le nombre d'OT à générer et le tonnage du dernier OT."""
        for wizard in self:
            if wizard.tonnage_per_ot > 0 and wizard.total_tonnage > 0:
                # Nombre d'OT complets
                full_ots = int(wizard.total_tonnage // wizard.tonnage_per_ot)
                # Tonnage restant pour le dernier OT
                remaining = wizard.total_tonnage % wizard.tonnage_per_ot
                
                if remaining > 0:
                    wizard.ot_count_to_generate = full_ots + 1
                    wizard.last_ot_tonnage = remaining
                else:
                    wizard.ot_count_to_generate = full_ots
                    wizard.last_ot_tonnage = wizard.tonnage_per_ot
            else:
                wizard.ot_count_to_generate = 0
                wizard.last_ot_tonnage = 0.0

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('product_type')
    def _onchange_product_type(self):
        """Reset product when product type changes and load default tonnage."""
        if self.product_id and self.product_id.potting_product_type != self.product_type:
            self.product_id = False
        
        # Charger le tonnage par défaut depuis la configuration par type de produit
        self._set_default_tonnage_from_config()
    
    def _set_default_tonnage_from_config(self):
        """Définit le tonnage par défaut depuis la configuration globale par type de produit."""
        if not self.product_type:
            return
        
        ICP = self.env['ir.config_parameter'].sudo()
        
        # Mapping type produit -> paramètre de config pour le tonnage OT par défaut
        tonnage_params = {
            'cocoa_mass': 'potting_management.default_ot_tonnage_cocoa_mass',
            'cocoa_butter': 'potting_management.default_ot_tonnage_cocoa_butter',
            'cocoa_cake': 'potting_management.default_ot_tonnage_cocoa_cake',
            'cocoa_powder': 'potting_management.default_ot_tonnage_cocoa_powder',
        }
        
        # Valeurs par défaut si le paramètre n'est pas défini
        default_values = {
            'cocoa_mass': 22.0,
            'cocoa_butter': 22.0,
            'cocoa_cake': 20.0,
            'cocoa_powder': 22.5,
        }
        
        param_name = tonnage_params.get(self.product_type)
        default_value = default_values.get(self.product_type, 22.0)
        
        if param_name:
            default_tonnage = float(ICP.get_param(param_name, str(default_value)))
            self.tonnage_per_ot = default_tonnage

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_generate_ots(self):
        """Génère les OT et retourne à la commande."""
        self.ensure_one()
        
        # Validations
        if self.total_tonnage <= 0:
            raise ValidationError(_("Le tonnage total doit être supérieur à 0."))
        
        if self.tonnage_per_ot <= 0:
            raise ValidationError(_("Le tonnage par OT doit être supérieur à 0."))
        
        if self.ot_count_to_generate <= 0:
            raise ValidationError(_("Aucun OT à générer."))
        
        # Vérifier que le tonnage ne dépasse pas le contrat
        if self.customer_order_id.contract_tonnage > 0:
            new_total = self.existing_tonnage + self.total_tonnage
            if new_total > self.customer_order_id.contract_tonnage:
                raise ValidationError(_(
                    "Le tonnage total (%.2f T existant + %.2f T nouveau = %.2f T) "
                    "dépasserait le tonnage du contrat (%.2f T).\n\n"
                    "Tonnage maximum à générer: %.2f T"
                ) % (
                    self.existing_tonnage,
                    self.total_tonnage,
                    new_total,
                    self.customer_order_id.contract_tonnage,
                    self.customer_order_id.contract_tonnage - self.existing_tonnage
                ))
        
        # Générer les OT
        created_ots = self.env['potting.transit.order']
        remaining_tonnage = self.total_tonnage
        
        for i in range(self.ot_count_to_generate):
            # Déterminer le tonnage de cet OT
            if remaining_tonnage >= self.tonnage_per_ot:
                ot_tonnage = self.tonnage_per_ot
            else:
                ot_tonnage = remaining_tonnage
            
            remaining_tonnage -= ot_tonnage
            
            # Créer l'OT
            ot_vals = {
                'customer_order_id': self.customer_order_id.id,
                'consignee_id': self.consignee_id.id,
                'product_type': self.product_type,
                'product_id': self.product_id.id if self.product_id else False,
                'tonnage': ot_tonnage,
                'vessel_id': self.vessel_id.id if self.vessel_id else False,
                'pod': self.pod,
                'container_size': self.container_size,
                'note': self.note,
                'is_created_from_order': True,
            }
            
            ot = self.env['potting.transit.order'].create(ot_vals)
            created_ots |= ot
        
        # Message de succès sur la commande
        product_type_label = dict(self._fields['product_type'].selection).get(self.product_type)
        self.customer_order_id.message_post(
            body=_("✅ <b>%d Ordre(s) de Transit</b> généré(s) automatiquement:<br/>"
                   "• Type de produit: %s<br/>"
                   "• Tonnage total: %.2f T<br/>"
                   "• Tonnage par OT: %.2f T<br/>"
                   "• OT créés: %s") % (
                len(created_ots),
                product_type_label,
                self.total_tonnage,
                self.tonnage_per_ot,
                ', '.join(created_ots.mapped('name'))
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
    
    def action_preview(self):
        """Affiche un aperçu des OT qui seront générés."""
        self.ensure_one()
        
        if self.total_tonnage <= 0:
            raise ValidationError(_("Le tonnage total doit être supérieur à 0."))
        
        if self.tonnage_per_ot <= 0:
            raise ValidationError(_("Le tonnage par OT doit être supérieur à 0."))
        
        # Construire l'aperçu
        preview_lines = []
        remaining_tonnage = self.total_tonnage
        
        for i in range(self.ot_count_to_generate):
            if remaining_tonnage >= self.tonnage_per_ot:
                ot_tonnage = self.tonnage_per_ot
            else:
                ot_tonnage = remaining_tonnage
            
            remaining_tonnage -= ot_tonnage
            preview_lines.append(f"OT {i+1}: {ot_tonnage:.2f} T")
        
        preview_text = "\n".join(preview_lines)
        
        # Afficher une notification avec l'aperçu
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Aperçu des OT à générer"),
                'message': preview_text,
                'type': 'info',
                'sticky': True,
            }
        }
