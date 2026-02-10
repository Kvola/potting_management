# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PottingShippingCompany(models.Model):
    """Compagnie Maritime (Armateur / Shipping Line)."""
    
    _name = 'potting.shipping.company'
    _description = 'Compagnie Maritime'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # SQL Constraints
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom de la compagnie maritime doit être unique!'),
        ('code_uniq', 'unique(code)', 'Le code de la compagnie maritime doit être unique!'),
    ]

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string="Nom",
        required=True,
        tracking=True,
        index=True,
        help="Nom complet de la compagnie maritime (ex: Mediterranean Shipping Company)"
    )
    
    code = fields.Char(
        string="Code",
        tracking=True,
        index=True,
        help="Code abrégé de la compagnie (ex: MSC, MAERSK, CMA-CGM)"
    )
    
    logo = fields.Binary(
        string="Logo",
        attachment=True
    )
    
    active = fields.Boolean(
        string="Actif",
        default=True,
        tracking=True
    )
    
    # Contact Information
    street = fields.Char(string="Adresse")
    street2 = fields.Char(string="Adresse (suite)")
    city = fields.Char(string="Ville")
    country_id = fields.Many2one('res.country', string="Pays")
    phone = fields.Char(string="Téléphone")
    email = fields.Char(string="Email")
    website = fields.Char(string="Site web")
    
    # Local Representative
    local_contact_name = fields.Char(
        string="Contact local",
        help="Nom du représentant local"
    )
    local_contact_phone = fields.Char(string="Tél. contact local")
    local_contact_email = fields.Char(string="Email contact local")
    
    # Related Records
    vessel_ids = fields.One2many(
        'potting.vessel',
        'shipping_company_id',
        string="Navires"
    )
    
    container_ids = fields.One2many(
        'potting.container',
        'shipping_company_id',
        string="Conteneurs"
    )
    
    # Statistics
    vessel_count = fields.Integer(
        string="Nombre de navires",
        compute='_compute_statistics',
        store=True
    )
    
    container_count = fields.Integer(
        string="Nombre de conteneurs",
        compute='_compute_statistics',
        store=True
    )
    
    container_available_count = fields.Integer(
        string="Conteneurs disponibles",
        compute='_compute_statistics',
        store=True
    )
    
    container_in_use_count = fields.Integer(
        string="Conteneurs en utilisation",
        compute='_compute_statistics',
        store=True
    )
    
    total_capacity = fields.Float(
        string="Capacité totale (T)",
        compute='_compute_statistics',
        store=True,
        digits='Product Unit of Measure'
    )
    
    note = fields.Text(string="Notes")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('vessel_ids', 'container_ids', 'container_ids.state', 'container_ids.max_capacity')
    def _compute_statistics(self):
        """Compute statistics for the shipping company."""
        for company in self:
            company.vessel_count = len(company.vessel_ids)
            company.container_count = len(company.container_ids)
            
            available = company.container_ids.filtered(lambda c: c.state == 'available')
            company.container_available_count = len(available)
            
            in_use = company.container_ids.filtered(lambda c: c.state != 'available')
            company.container_in_use_count = len(in_use)
            
            company.total_capacity = sum(company.container_ids.mapped('max_capacity'))

    # -------------------------------------------------------------------------
    # DISPLAY METHODS
    # -------------------------------------------------------------------------
    def name_get(self):
        """Display name with code if available."""
        result = []
        for company in self:
            name = company.name
            if company.code:
                name = f"[{company.code}] {name}"
            result.append((company.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Search by name or code."""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_view_vessels(self):
        """Open vessels of this shipping company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Navires - %s') % self.name,
            'res_model': 'potting.vessel',
            'view_mode': 'list,form',
            'domain': [('shipping_company_id', '=', self.id)],
            'context': {'default_shipping_company_id': self.id},
        }

    def action_view_containers(self):
        """Open containers of this shipping company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Conteneurs - %s') % self.name,
            'res_model': 'potting.container',
            'view_mode': 'list,kanban,form',
            'domain': [('shipping_company_id', '=', self.id)],
            'context': {'default_shipping_company_id': self.id},
        }

    def action_view_available_containers(self):
        """Open available containers of this shipping company."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Conteneurs disponibles - %s') % self.name,
            'res_model': 'potting.container',
            'view_mode': 'list,kanban,form',
            'domain': [
                ('shipping_company_id', '=', self.id),
                ('state', '=', 'available'),
            ],
            'context': {'default_shipping_company_id': self.id},
        }
