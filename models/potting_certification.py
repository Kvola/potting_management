# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PottingCertification(models.Model):
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