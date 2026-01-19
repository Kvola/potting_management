# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingCvAllocation(models.Model):
    """Allocation de tonnage CV-Contrat
    
    Ce modèle gère la répartition du tonnage d'une Confirmation de Vente (CV)
    entre plusieurs contrats d'exportation. Il permet de :
    
    1. Répartir un contrat sur plusieurs CV (ex: contrat de 300T sur 2 CV de 200T)
    2. Utiliser une CV pour plusieurs contrats (split de CV)
    3. Suivre le tonnage exact alloué à chaque combinaison contrat/CV
    
    Le tonnage alloué est le tonnage planifié, le tonnage utilisé est calculé
    à partir des OT effectivement créés.
    """
    _name = 'potting.cv.allocation'
    _description = 'Allocation CV-Contrat'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'customer_order_id, sequence, id'
    _rec_name = 'display_name'

    # =========================================================================
    # CONTRAINTES SQL
    # =========================================================================
    _sql_constraints = [
        ('unique_cv_order', 'unique(confirmation_vente_id, customer_order_id)',
         'Une seule allocation par combinaison CV/Contrat est autorisée !'),
        ('tonnage_positive', 'CHECK(tonnage_alloue > 0)',
         'Le tonnage alloué doit être supérieur à 0 !'),
    ]

    # =========================================================================
    # CHAMPS
    # =========================================================================
    
    sequence = fields.Integer(
        string="Séquence",
        default=10,
        help="Ordre d'affichage des allocations"
    )
    
    display_name = fields.Char(
        string="Nom",
        compute='_compute_display_name',
        store=True
    )
    
    # Relation vers la CV
    confirmation_vente_id = fields.Many2one(
        'potting.confirmation.vente',
        string="Confirmation de Vente",
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        domain="[('state', '=', 'active')]"
    )
    
    cv_name = fields.Char(
        string="N° CV",
        related='confirmation_vente_id.name',
        store=True
    )
    
    cv_reference_ccc = fields.Char(
        string="Réf. CCC",
        related='confirmation_vente_id.reference_ccc',
        store=True
    )
    
    cv_state = fields.Selection(
        related='confirmation_vente_id.state',
        string="État CV",
        store=True
    )
    
    cv_tonnage_autorise = fields.Float(
        string="Tonnage CV autorisé",
        related='confirmation_vente_id.tonnage_autorise',
        digits='Product Unit of Measure'
    )
    
    cv_tonnage_restant = fields.Float(
        string="Tonnage CV restant",
        related='confirmation_vente_id.tonnage_restant',
        digits='Product Unit of Measure'
    )
    
    cv_date_end = fields.Date(
        string="Fin validité CV",
        related='confirmation_vente_id.date_end'
    )
    
    cv_campaign_id = fields.Many2one(
        related='confirmation_vente_id.campaign_id',
        string="Campagne CV"
    )
    
    # Relation vers le Contrat
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Contrat",
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    
    order_name = fields.Char(
        string="Réf. Contrat",
        related='customer_order_id.name',
        store=True
    )
    
    order_state = fields.Selection(
        related='customer_order_id.state',
        string="État contrat",
        store=True
    )
    
    contract_tonnage = fields.Float(
        string="Tonnage contrat",
        related='customer_order_id.contract_tonnage',
        digits='Product Unit of Measure'
    )
    
    # Tonnage alloué (saisi manuellement)
    tonnage_alloue = fields.Float(
        string="Tonnage alloué (T)",
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Tonnage de la CV alloué à ce contrat. "
             "Ce tonnage est réservé et sera déduit du tonnage disponible de la CV."
    )
    
    # Tonnage effectivement utilisé (calculé à partir des OT)
    tonnage_utilise = fields.Float(
        string="Tonnage utilisé (T)",
        compute='_compute_tonnage_utilise',
        store=True,
        digits='Product Unit of Measure',
        help="Tonnage réellement consommé par les OT liés à cette allocation"
    )
    
    tonnage_restant = fields.Float(
        string="Tonnage restant (T)",
        compute='_compute_tonnage_utilise',
        store=True,
        digits='Product Unit of Measure',
        help="Différence entre tonnage alloué et tonnage utilisé"
    )
    
    progress = fields.Float(
        string="Progression (%)",
        compute='_compute_tonnage_utilise',
        store=True,
        help="Pourcentage d'utilisation du tonnage alloué"
    )
    
    # Société
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        related='customer_order_id.company_id',
        store=True,
        index=True
    )
    
    # Notes
    note = fields.Text(
        string="Notes",
        help="Notes sur cette allocation"
    )
    
    # État calculé
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'Active'),
        ('consumed', 'Consommée'),
        ('cancelled', 'Annulée'),
    ], string="État",
       compute='_compute_state',
       store=True,
       help="État de l'allocation basé sur les états de la CV et du contrat"
    )

    # =========================================================================
    # MÉTHODES COMPUTED
    # =========================================================================
    
    @api.depends('confirmation_vente_id.name', 'customer_order_id.name', 'tonnage_alloue')
    def _compute_display_name(self):
        for record in self:
            if record.confirmation_vente_id and record.customer_order_id:
                record.display_name = _(
                    "%(cv)s → %(order)s (%(tonnage).1f T)",
                    cv=record.confirmation_vente_id.name,
                    order=record.customer_order_id.name,
                    tonnage=record.tonnage_alloue or 0
                )
            else:
                record.display_name = _("Nouvelle allocation")
    
    @api.depends('customer_order_id.transit_order_ids.tonnage', 
                 'customer_order_id.transit_order_ids.state',
                 'tonnage_alloue')
    def _compute_tonnage_utilise(self):
        """Calcule le tonnage utilisé à partir des OT du contrat
        
        Pour répartir l'utilisation entre plusieurs CV, on utilise 
        une allocation proportionnelle basée sur les tonnages alloués.
        """
        for record in self:
            if not record.customer_order_id or not record.tonnage_alloue:
                record.tonnage_utilise = 0
                record.tonnage_restant = record.tonnage_alloue or 0
                record.progress = 0
                continue
            
            # Tonnage total des OT du contrat (non annulés)
            total_ot_tonnage = sum(
                ot.tonnage or 0 
                for ot in record.customer_order_id.transit_order_ids
                if ot.state not in ('cancelled',)
            )
            
            # Total des allocations pour ce contrat
            all_allocations = self.search([
                ('customer_order_id', '=', record.customer_order_id.id)
            ])
            total_alloue = sum(a.tonnage_alloue for a in all_allocations)
            
            # Répartition proportionnelle du tonnage OT utilisé
            if total_alloue > 0:
                proportion = record.tonnage_alloue / total_alloue
                record.tonnage_utilise = min(
                    total_ot_tonnage * proportion,
                    record.tonnage_alloue  # Ne peut pas dépasser l'allocation
                )
            else:
                record.tonnage_utilise = 0
            
            record.tonnage_restant = record.tonnage_alloue - record.tonnage_utilise
            
            if record.tonnage_alloue > 0:
                record.progress = (record.tonnage_utilise / record.tonnage_alloue) * 100
            else:
                record.progress = 0
    
    @api.depends('confirmation_vente_id.state', 'customer_order_id.state', 
                 'tonnage_utilise', 'tonnage_alloue')
    def _compute_state(self):
        """Calcule l'état de l'allocation"""
        for record in self:
            if record.customer_order_id.state == 'cancelled':
                record.state = 'cancelled'
            elif record.confirmation_vente_id.state in ('cancelled', 'expired'):
                record.state = 'cancelled'
            elif record.confirmation_vente_id.state == 'draft':
                record.state = 'draft'
            elif record.tonnage_utilise >= record.tonnage_alloue:
                record.state = 'consumed'
            else:
                record.state = 'active'
    
    # =========================================================================
    # CONTRAINTES
    # =========================================================================
    
    @api.constrains('tonnage_alloue', 'confirmation_vente_id')
    def _check_tonnage_allocation(self):
        """Vérifie que le tonnage alloué ne dépasse pas le tonnage disponible de la CV"""
        for record in self:
            if not record.confirmation_vente_id or not record.tonnage_alloue:
                continue
            
            # Calcul du tonnage déjà alloué sur cette CV (hors cette allocation)
            other_allocations = self.search([
                ('confirmation_vente_id', '=', record.confirmation_vente_id.id),
                ('id', '!=', record.id),
                ('customer_order_id.state', 'not in', ['cancelled'])
            ])
            total_other_alloue = sum(a.tonnage_alloue for a in other_allocations)
            
            available = record.confirmation_vente_id.tonnage_autorise - total_other_alloue
            
            if record.tonnage_alloue > available:
                raise ValidationError(_(
                    "Le tonnage alloué (%(alloue).2f T) dépasse le tonnage disponible "
                    "sur la CV %(cv)s (%(available).2f T disponible).\n\n"
                    "Tonnage autorisé CV : %(autorise).2f T\n"
                    "Déjà alloué à d'autres contrats : %(other).2f T",
                    alloue=record.tonnage_alloue,
                    cv=record.confirmation_vente_id.name,
                    available=available,
                    autorise=record.confirmation_vente_id.tonnage_autorise,
                    other=total_other_alloue
                ))
    
    @api.constrains('confirmation_vente_id', 'customer_order_id')
    def _check_product_type(self):
        """Vérifie la cohérence du type de produit entre CV et contrat"""
        for record in self:
            if not record.confirmation_vente_id or not record.customer_order_id:
                continue
            
            cv_type = record.confirmation_vente_id.product_type
            order_type = record.customer_order_id.product_type
            
            if cv_type != 'all' and cv_type != order_type:
                raise ValidationError(_(
                    "Le type de produit du contrat (%(order_type)s) ne correspond pas "
                    "au type autorisé par la CV %(cv)s (%(cv_type)s).",
                    order_type=dict(
                        record.customer_order_id._fields['product_type'].selection
                    ).get(order_type),
                    cv=record.confirmation_vente_id.name,
                    cv_type=dict(
                        record.confirmation_vente_id._fields['product_type'].selection
                    ).get(cv_type)
                ))
    
    # =========================================================================
    # MÉTHODES CRUD
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Lors de la création, ajoute automatiquement la CV aux Many2many du contrat"""
        records = super().create(vals_list)
        for record in records:
            # Synchronise avec le champ Many2many existant
            if record.confirmation_vente_id not in record.customer_order_id.confirmation_vente_ids:
                record.customer_order_id.write({
                    'confirmation_vente_ids': [(4, record.confirmation_vente_id.id)]
                })
        return records
    
    def unlink(self):
        """Avant suppression, nettoie les relations Many2many si nécessaire"""
        for record in self:
            # Vérifie s'il reste d'autres allocations pour cette combinaison
            remaining = self.search([
                ('confirmation_vente_id', '=', record.confirmation_vente_id.id),
                ('customer_order_id', '=', record.customer_order_id.id),
                ('id', '!=', record.id)
            ])
            if not remaining:
                # Plus d'allocation, retire la CV du Many2many
                record.customer_order_id.write({
                    'confirmation_vente_ids': [(3, record.confirmation_vente_id.id)]
                })
        return super().unlink()
    
    # =========================================================================
    # MÉTHODES D'ACTION
    # =========================================================================
    
    def action_view_transit_orders(self):
        """Affiche les OT liés à cette allocation"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordres de Transit'),
            'res_model': 'potting.transit.order',
            'view_mode': 'tree,form',
            'domain': [('customer_order_id', '=', self.customer_order_id.id)],
            'context': {'default_customer_order_id': self.customer_order_id.id}
        }
