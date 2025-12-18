# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PottingCertification(models.Model):
    """Certification produit avec prix associé
    
    Les certifications (Fair Trade, Rain Forest Alliance, UTZ, etc.)
    peuvent avoir un prix par tonne qui impacte le prix global du contrat.
    """
    _name = 'potting.certification'
    _description = 'Certification produit'
    _order = 'sequence, name'

    _sql_constraints = [
        ('suffix_uniq', 'unique(suffix)', 
         'Le suffixe de certification doit être unique!'),
        ('name_uniq', 'unique(name)', 
         'Le nom de la certification doit être unique!'),
    ]

    name = fields.Char(
        string="Nom",
        required=True,
        translate=True,
        help="Nom complet de la certification (ex: Fair Trade, Rain Forest Alliance)"
    )
    
    suffix = fields.Char(
        string="Suffixe",
        required=True,
        size=10,
        help="Suffixe ajouté à la référence du lot (ex: FT, RA, UTZ)"
    )
    
    code = fields.Char(
        string="Code",
        compute='_compute_code',
        store=True,
        help="Code de la certification (suffixe en majuscules)"
    )
    
    description = fields.Text(
        string="Description",
        translate=True,
        help="Description détaillée de la certification"
    )
    
    # =========================================================================
    # CHAMPS - PRIX
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self._get_default_currency(),
        required=True,
        help="Devise utilisée pour les primes de cette certification."
    )
    
    price_per_ton = fields.Monetary(
        string="Prime par tonne",
        currency_field='currency_id',
        help="Prime de certification par tonne de produit. "
             "Ce montant s'ajoute au prix de base du contrat."
    )
    
    price_type = fields.Selection([
        ('fixed', 'Montant fixe par tonne'),
        ('percentage', 'Pourcentage du prix de base'),
    ], string="Type de prime",
    default='fixed',
    help="Méthode de calcul de la prime de certification"
    )
    
    price_percentage = fields.Float(
        string="Pourcentage (%)",
        help="Pourcentage du prix de base à ajouter comme prime"
    )
    
    # =========================================================================
    # CHAMPS - AFFICHAGE
    # =========================================================================
    
    color = fields.Integer(
        string="Couleur",
        default=0,
        help="Couleur pour l'affichage dans les badges"
    )
    
    active = fields.Boolean(
        string="Actif",
        default=True,
        help="Désactiver pour masquer la certification sans la supprimer"
    )
    
    sequence = fields.Integer(
        string="Séquence",
        default=10,
        help="Ordre d'affichage"
    )
    
    logo = fields.Binary(
        string="Logo",
        attachment=True,
        help="Logo de la certification"
    )
    
    lot_count = fields.Integer(
        string="Nombre de lots",
        compute='_compute_lot_count'
    )
    
    total_premium_amount = fields.Monetary(
        string="Total primes générées",
        currency_field='currency_id',
        compute='_compute_total_premium',
        help="Montant total des primes générées par cette certification"
    )

    total_tonnage = fields.Float(
        string="Tonnage total certifié",
        compute='_compute_total_premium',
        digits='Product Unit of Measure',
        help="Tonnage total de produit utilisant cette certification"
    )

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    @api.model
    def _get_default_currency(self):
        """Get the default currency for the potting module.
        
        Returns the configured default currency if set, otherwise falls back
        to the company currency.
        
        Returns:
            res.currency: The default currency record
        """
        return self.env['res.config.settings'].get_default_currency()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('suffix')
    def _compute_code(self):
        for cert in self:
            cert.code = cert.suffix.upper() if cert.suffix else ''

    def _compute_lot_count(self):
        for cert in self:
            cert.lot_count = self.env['potting.lot'].search_count([
                ('certification_id', '=', cert.id)
            ])

    def _compute_total_premium(self):
        """Calculate total premium amount and tonnage for this certification"""
        for cert in self:
            total = 0.0
            total_tons = 0.0
            lots = self.env['potting.lot'].search([
                ('certification_id', '=', cert.id),
                ('state', '=', 'potted')
            ])
            for lot in lots:
                total_tons += lot.current_tonnage or 0.0
                if cert.price_type == 'fixed':
                    total += cert.price_per_ton * lot.current_tonnage
                elif cert.price_type == 'percentage' and lot.transit_order_id.customer_order_id:
                    base_price = lot.transit_order_id.customer_order_id.unit_price or 0.0
                    total += (base_price * cert.price_percentage / 100) * lot.current_tonnage
            cert.total_premium_amount = total
            cert.total_tonnage = total_tons

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def get_premium_for_tonnage(self, tonnage, base_price=0.0):
        """Calculate the premium amount for a given tonnage
        
        Args:
            tonnage: The tonnage in tons
            base_price: The base price per ton (used for percentage calculations)
        
        Returns:
            The premium amount in the certification's currency
        """
        self.ensure_one()
        if self.price_type == 'fixed':
            return self.price_per_ton * tonnage
        elif self.price_type == 'percentage' and base_price:
            return (base_price * self.price_percentage / 100) * tonnage
        return 0.0

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('suffix')
    def _check_suffix(self):
        for cert in self:
            if cert.suffix:
                # Vérifier que le suffixe ne contient que des lettres et chiffres
                if not cert.suffix.replace('-', '').replace('_', '').isalnum():
                    raise ValidationError(_(
                        "Le suffixe ne peut contenir que des lettres, chiffres, tirets et underscores."
                    ))
                # Limiter la longueur
                if len(cert.suffix) > 10:
                    raise ValidationError(_("Le suffixe ne peut pas dépasser 10 caractères."))

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    def unlink(self):
        for cert in self:
            if cert.lot_count > 0:
                raise ValidationError(_(
                    "Impossible de supprimer la certification '%s' car elle est utilisée par %d lot(s)."
                ) % (cert.name, cert.lot_count))
        return super().unlink()

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_view_lots(self):
        """Ouvre la liste des lots liés à cette certification"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lots - %s') % self.name,
            'res_model': 'potting.lot',
            'view_mode': 'tree,kanban,form',
            'domain': [('certification_id', '=', self.id)],
            'context': {'search_default_certification_id': self.id},
        }

    # -------------------------------------------------------------------------
    # DISPLAY METHODS
    # -------------------------------------------------------------------------
    def name_get(self):
        result = []
        for cert in self:
            name = f"{cert.name} ({cert.suffix})"
            result.append((cert.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('suffix', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)