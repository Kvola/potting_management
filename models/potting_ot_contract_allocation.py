# -*- coding: utf-8 -*-
"""
Allocation OT-Contrats : Répartition du tonnage d'un OT sur plusieurs Contrats

Ce modèle permet à un OT de bénéficier du tonnage de plusieurs contrats
(indépendamment de la campagne). Le prix de vente de l'OT devient alors
la somme pondérée des prix des différents contrats utilisés.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingOtContractAllocation(models.Model):
    """Allocation de tonnage Contrat vers OT
    
    Permet de répartir le tonnage d'un OT sur plusieurs contrats, avec calcul
    automatique du prix moyen pondéré.
    """
    _name = 'potting.ot.contract.allocation'
    _description = 'Allocation Tonnage Contrat → OT'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'transit_order_id, sequence, id'
    _rec_name = 'display_name'

    # =========================================================================
    # CONTRAINTES SQL
    # =========================================================================
    _sql_constraints = [
        ('unique_contract_ot', 'unique(customer_order_id, transit_order_id)',
         'Une seule allocation par combinaison Contrat/OT est autorisée !'),
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
    
    # Relation vers l'OT
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    
    ot_name = fields.Char(
        string="N° OT",
        related='transit_order_id.name',
        store=True
    )
    
    ot_state = fields.Selection(
        related='transit_order_id.state',
        string="État OT",
        store=True
    )
    
    ot_tonnage_total = fields.Float(
        string="Tonnage total OT",
        related='transit_order_id.tonnage',
        digits='Product Unit of Measure'
    )
    
    # Relation vers le Contrat
    customer_order_id = fields.Many2one(
        'potting.customer.order',
        string="Contrat",
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        domain="[('state', 'in', ['confirmed', 'in_progress']), ('remaining_contract_tonnage', '>', 0)]"
    )
    
    contract_name = fields.Char(
        string="Réf. Contrat",
        related='customer_order_id.name',
        store=True
    )
    
    contract_number = fields.Char(
        string="N° Contrat",
        related='customer_order_id.contract_number',
        store=True
    )
    
    contract_state = fields.Selection(
        related='customer_order_id.state',
        string="État contrat",
        store=True
    )
    
    contract_tonnage = fields.Float(
        string="Tonnage contrat total",
        related='customer_order_id.contract_tonnage',
        digits='Product Unit of Measure'
    )
    
    contract_tonnage_restant = fields.Float(
        string="Tonnage contrat disponible",
        related='customer_order_id.remaining_contract_tonnage',
        digits='Product Unit of Measure'
    )
    
    contract_unit_price = fields.Monetary(
        string="Prix unitaire contrat",
        related='customer_order_id.unit_price',
        currency_field='currency_id'
    )
    
    # Devise
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='customer_order_id.currency_id',
        store=True
    )
    
    # Tonnage alloué (saisi manuellement)
    tonnage_alloue = fields.Float(
        string="Tonnage alloué (T)",
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Tonnage du contrat alloué à cet OT. "
             "Ce tonnage sera déduit du tonnage disponible du contrat."
    )
    
    # Montant calculé pour cette allocation
    montant_alloue = fields.Monetary(
        string="Montant (FCFA)",
        compute='_compute_montant',
        store=True,
        currency_field='currency_id',
        help="Montant = Tonnage alloué × Prix unitaire du contrat"
    )
    
    # Pourcentage de l'OT couvert par cette allocation
    pourcentage_ot = fields.Float(
        string="% de l'OT",
        compute='_compute_pourcentage',
        store=True,
        digits=(5, 2),
        help="Pourcentage du tonnage total de l'OT couvert par cette allocation"
    )
    
    # Note
    note = fields.Text(
        string="Notes",
        help="Notes sur cette allocation"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        related='transit_order_id.company_id',
        store=True
    )
    
    # =========================================================================
    # MÉTHODES COMPUTED
    # =========================================================================
    
    @api.depends('transit_order_id.name', 'customer_order_id.name', 'tonnage_alloue')
    def _compute_display_name(self):
        for record in self:
            if record.transit_order_id and record.customer_order_id:
                record.display_name = f"{record.transit_order_id.name} ← {record.customer_order_id.name} ({record.tonnage_alloue:.2f}T)"
            else:
                record.display_name = _("Nouvelle allocation")
    
    @api.depends('tonnage_alloue', 'customer_order_id.unit_price')
    def _compute_montant(self):
        for record in self:
            record.montant_alloue = record.tonnage_alloue * record.customer_order_id.unit_price
    
    @api.depends('tonnage_alloue', 'transit_order_id.tonnage')
    def _compute_pourcentage(self):
        for record in self:
            if record.transit_order_id and record.transit_order_id.tonnage > 0:
                record.pourcentage_ot = (record.tonnage_alloue / record.transit_order_id.tonnage) * 100
            else:
                record.pourcentage_ot = 0
    
    # =========================================================================
    # CONTRAINTES
    # =========================================================================
    
    @api.constrains('tonnage_alloue', 'customer_order_id')
    def _check_tonnage_disponible(self):
        """Vérifie que le tonnage alloué ne dépasse pas le tonnage disponible du contrat"""
        for record in self:
            if record.customer_order_id and record.tonnage_alloue:
                # Calculer le tonnage déjà alloué de ce contrat (excluant cette allocation)
                other_allocations = self.search([
                    ('customer_order_id', '=', record.customer_order_id.id),
                    ('id', '!=', record.id)
                ])
                total_deja_alloue = sum(a.tonnage_alloue for a in other_allocations)
                disponible = record.customer_order_id.contract_tonnage - total_deja_alloue
                
                if record.tonnage_alloue > disponible * 1.05:  # Tolérance 5%
                    raise ValidationError(_(
                        "Le tonnage alloué (%.2f T) dépasse le tonnage disponible du contrat %s (%.2f T).",
                        record.tonnage_alloue,
                        record.customer_order_id.name,
                        disponible
                    ))
    
    @api.constrains('tonnage_alloue', 'transit_order_id')
    def _check_tonnage_ot(self):
        """Vérifie que le total des allocations ne dépasse pas le tonnage de l'OT"""
        for record in self:
            if record.transit_order_id and record.tonnage_alloue:
                # Calculer le total alloué pour cet OT
                all_allocations = self.search([
                    ('transit_order_id', '=', record.transit_order_id.id)
                ])
                total_alloue = sum(a.tonnage_alloue for a in all_allocations)
                
                if total_alloue > record.transit_order_id.tonnage * 1.05:  # Tolérance 5%
                    raise ValidationError(_(
                        "Le total des allocations (%.2f T) dépasse le tonnage de l'OT %s (%.2f T).",
                        total_alloue,
                        record.transit_order_id.name,
                        record.transit_order_id.tonnage
                    ))
    
    @api.constrains('transit_order_id', 'customer_order_id')
    def _check_product_type(self):
        """Vérifie que le type de produit est cohérent"""
        for record in self:
            if record.transit_order_id and record.customer_order_id:
                if record.transit_order_id.product_type != record.customer_order_id.product_type:
                    raise ValidationError(_(
                        "Le type de produit de l'OT (%s) doit correspondre "
                        "au type de produit du contrat (%s).",
                        record.transit_order_id.product_type,
                        record.customer_order_id.product_type
                    ))
    
    # =========================================================================
    # MÉTHODES ONCHANGE
    # =========================================================================
    
    @api.onchange('customer_order_id')
    def _onchange_customer_order(self):
        """Suggère un tonnage basé sur le disponible"""
        if self.customer_order_id and self.transit_order_id:
            disponible_contrat = self.customer_order_id.remaining_contract_tonnage
            restant_ot = self.transit_order_id.tonnage - sum(
                a.tonnage_alloue for a in self.transit_order_id.contract_allocation_ids
                if a.id != self._origin.id
            )
            # Proposer le minimum entre ce qui est disponible et ce qui reste à allouer
            self.tonnage_alloue = min(disponible_contrat, restant_ot)
