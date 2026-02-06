# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import math


class PottingGenerateOTFromOrderWizard(models.TransientModel):
    """Wizard pour générer automatiquement des OT depuis une commande client.
    
    Ce wizard permet de:
    - Sélectionner des Formules disponibles (validées, sans OT)
    - Générer 1 OT par Formule sélectionnée
    - Chaque OT hérite des données de sa Formule (tonnage, type produit, etc.)
    """
    _name = 'potting.generate.ot.from.order.wizard'
    _description = "Assistant de génération automatique d'OT depuis Formules"

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
    
    campaign_id = fields.Many2one(
        'potting.campaign',
        string="Campagne Café-Cacao",
        required=True,
        domain="[('state', 'in', ['draft', 'active'])]",
        default=lambda self: self._get_default_campaign(),
        help="Campagne café-cacao pour les OT générés"
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
    # FIELDS - Sélection des Formules
    # =========================================================================
    
    formule_ids = fields.Many2many(
        'potting.formule',
        'potting_generate_ot_wizard_formule_rel',
        'wizard_id',
        'formule_id',
        string="Formules à utiliser",
        help="Sélectionnez les Formules disponibles pour générer les OT. "
             "1 OT sera créé par Formule sélectionnée."
    )
    
    available_formule_ids = fields.Many2many(
        'potting.formule',
        string="Formules disponibles",
        compute='_compute_available_formules',
        help="Formules validées et non encore liées à un OT"
    )
    
    formule_count = fields.Integer(
        string="Formules sélectionnées",
        compute='_compute_formule_stats',
        help="Nombre de formules sélectionnées"
    )
    
    total_formule_tonnage = fields.Float(
        string="Tonnage total Formules (T)",
        compute='_compute_formule_stats',
        digits='Product Unit of Measure',
        help="Tonnage total des formules sélectionnées"
    )
    
    # =========================================================================
    # FIELDS - Configuration commune (optionnel)
    # =========================================================================
    
    consignee_id = fields.Many2one(
        'res.partner',
        string="Destinataire (Consignee)",
        help="Destinataire commun à tous les OT (si vide, utilise le client)"
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
    
    # Champs obsolètes conservés pour compatibilité (non utilisés dans la nouvelle logique)
    total_tonnage = fields.Float(
        string="Tonnage à générer (T)",
        digits='Product Unit of Measure',
        compute='_compute_formule_stats',
        help="Calculé automatiquement depuis les formules sélectionnées"
    )
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit", 
       help="Information - le type de produit est défini par chaque Formule")
    
    product_id = fields.Many2one(
        'product.product',
        string="Produit",
        domain="[('potting_product_type', '=', product_type)]",
        help="Produit spécifique (optionnel)"
    )
    
    tonnage_per_ot = fields.Float(
        string="Tonnage par OT (T)",
        digits='Product Unit of Measure',
        default=0.0,
        help="Non utilisé - le tonnage est défini par chaque Formule"
    )
    
    ot_count_to_generate = fields.Integer(
        string="Nombre d'OT à générer",
        compute='_compute_formule_stats',
        help="Nombre d'OT qui seront créés (= nombre de formules sélectionnées)"
    )
    
    last_ot_tonnage = fields.Float(
        string="Tonnage dernier OT (T)",
        compute='_compute_formule_stats',
        digits='Product Unit of Measure',
        help="Non utilisé dans le nouveau mode"
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
    
    @api.depends('company_id')
    def _compute_available_formules(self):
        """Calcule les formules disponibles (validées, sans OT)."""
        for wizard in self:
            domain = [
                ('state', 'in', ['validated', 'partial_paid']),
                ('transit_order_id', '=', False),
                ('company_id', '=', wizard.company_id.id),
            ]
            wizard.available_formule_ids = self.env['potting.formule'].search(domain)
    
    @api.depends('formule_ids')
    def _compute_formule_stats(self):
        """Calcule les statistiques des formules sélectionnées."""
        for wizard in self:
            wizard.formule_count = len(wizard.formule_ids)
            wizard.total_formule_tonnage = sum(wizard.formule_ids.mapped('tonnage'))
            wizard.total_tonnage = wizard.total_formule_tonnage
            wizard.ot_count_to_generate = len(wizard.formule_ids)
            # last_ot_tonnage non pertinent dans ce mode, on met 0
            wizard.last_ot_tonnage = 0.0

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================
    
    @api.onchange('formule_ids')
    def _onchange_formule_ids(self):
        """Met à jour les statistiques quand les formules changent."""
        if self.formule_ids:
            # Vérifier que toutes les formules sont du même type de produit
            product_types = set(self.formule_ids.mapped('product_type'))
            if len(product_types) == 1:
                self.product_type = list(product_types)[0]
            else:
                self.product_type = False  # Plusieurs types = pas de type dominant

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def action_generate_ots(self):
        """Génère les OT depuis les Formules sélectionnées et retourne à la commande."""
        self.ensure_one()
        
        # Validations
        if not self.formule_ids:
            raise ValidationError(_("Veuillez sélectionner au moins une Formule."))
        
        # Vérifier que les formules sont toujours disponibles
        for formule in self.formule_ids:
            if formule.transit_order_id:
                raise ValidationError(_(
                    "La Formule %s est déjà liée à l'OT %s. "
                    "Veuillez la retirer de la sélection."
                ) % (formule.display_name, formule.transit_order_id.name))
            
            if formule.state not in ('validated', 'partial_paid'):
                raise ValidationError(_(
                    "La Formule %s n'est pas dans un état valide (état actuel: %s). "
                    "Seules les formules validées peuvent être utilisées."
                ) % (formule.display_name, formule.state))
        
        # Déterminer le destinataire par défaut
        default_consignee = self.consignee_id or self.customer_order_id.customer_id
        if not default_consignee:
            raise ValidationError(_("Veuillez spécifier un destinataire."))
        
        # Générer les OT (1 OT par Formule)
        created_ots = self.env['potting.transit.order']
        
        for formule in self.formule_ids:
            # Créer l'OT avec les données de la Formule
            ot_vals = {
                'formule_id': formule.id,
                'customer_order_id': self.customer_order_id.id,
                'campaign_id': self.campaign_id.id,
                'consignee_id': default_consignee.id,
                'product_type': formule.product_type,
                'tonnage': formule.tonnage,
                'vessel_id': self.vessel_id.id if self.vessel_id else False,
                'pod': self.pod or formule.port_destination,
                'container_size': self.container_size,
                'note': self.note,
                'is_created_from_order': True,
            }
            
            ot = self.env['potting.transit.order'].create(ot_vals)
            created_ots |= ot
        
        # Message de succès sur la commande
        self.customer_order_id.message_post(
            body=_("✅ <b>%d Ordre(s) de Transit</b> généré(s) automatiquement depuis Formules:<br/>"
                   "• Tonnage total: %.2f T<br/>"
                   "• Formules: %s<br/>"
                   "• OT créés: %s") % (
                len(created_ots),
                self.total_formule_tonnage,
                ', '.join(self.formule_ids.mapped('name')),
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
    
    def action_select_all_formules(self):
        """Sélectionne toutes les formules disponibles."""
        self.ensure_one()
        self.formule_ids = self.available_formule_ids
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_clear_formules(self):
        """Désélectionne toutes les formules."""
        self.ensure_one()
        self.formule_ids = [(5, 0, 0)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_preview(self):
        """Affiche un aperçu des OT qui seront générés."""
        self.ensure_one()
        
        if not self.formule_ids:
            raise ValidationError(_("Veuillez sélectionner au moins une Formule."))
        
        # Construire l'aperçu
        preview_lines = []
        total = 0
        
        for i, formule in enumerate(self.formule_ids, 1):
            product_type_label = dict(self.env['potting.formule']._fields['product_type'].selection).get(formule.product_type, '')
            preview_lines.append(
                f"OT {i}: {formule.name} → {formule.tonnage:.2f} T ({product_type_label})"
            )
            total += formule.tonnage
        
        preview_lines.append(f"\n📊 Total: {len(self.formule_ids)} OT pour {total:.2f} T")
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
