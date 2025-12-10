# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PottingProductionLine(models.Model):
    _name = 'potting.production.line'
    _description = 'Ligne de production'
    _order = 'date desc, id desc'
    _check_company_auto = True

    # SQL Constraints
    _sql_constraints = [
        ('tonnage_positive', 'CHECK(tonnage > 0)', 
         'Le tonnage doit être supérieur à 0!'),
    ]

    lot_id = fields.Many2one(
        'potting.lot',
        string="Lot",
        required=True,
        ondelete='cascade',
        check_company=True,
        index=True
    )
    
    transit_order_id = fields.Many2one(
        related='lot_id.transit_order_id',
        string="Ordre de Transit",
        store=True,
        index=True
    )
    
    customer_order_id = fields.Many2one(
        related='lot_id.customer_order_id',
        string="Commande client",
        store=True
    )
    
    product_type = fields.Selection(
        related='lot_id.product_type',
        string="Type de produit",
        store=True
    )
    
    date = fields.Date(
        string="Date de production",
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    
    tonnage = fields.Float(
        string="Tonnage (T)",
        required=True,
        digits='Product Unit of Measure'
    )
    
    batch_number = fields.Char(
        string="Numéro de batch",
        index=True
    )
    
    shift = fields.Selection([
        ('morning', 'Matin (6h-14h)'),
        ('afternoon', 'Après-midi (14h-22h)'),
        ('night', 'Nuit (22h-6h)'),
    ], string="Équipe", default='morning')
    
    operator_id = fields.Many2one(
        'res.users',
        string="Opérateur",
        default=lambda self: self.env.user,
        index=True
    )
    
    quality_ok = fields.Boolean(
        string="Qualité OK",
        default=True
    )
    
    note = fields.Text(string="Notes")
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    # Computed fields for reporting
    lot_fill_after = fields.Float(
        string="Remplissage après (%)",
        compute='_compute_lot_fill_after',
        digits=(5, 2)
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('tonnage')
    def _check_tonnage(self):
        # Récupérer la limite configurable (défaut: 10 tonnes)
        max_production = float(
            self.env['ir.config_parameter'].sudo().get_param(
                'potting_management.max_daily_production', '10.0'
            )
        )
        for line in self:
            if line.tonnage <= 0:
                raise ValidationError(_("Le tonnage doit être supérieur à 0."))
            if line.tonnage > max_production:
                raise ValidationError(
                    _("Le tonnage par production ne peut pas dépasser %.1f tonnes.") % max_production
                )

    @api.constrains('date')
    def _check_date(self):
        today = fields.Date.context_today(self)
        for line in self:
            if line.date > today:
                raise ValidationError(_("La date de production ne peut pas être dans le futur."))

    @api.constrains('lot_id', 'tonnage')
    def _check_lot_capacity(self):
        for line in self:
            lot = line.lot_id
            # Check if this would overfill the lot by too much (> 110%)
            other_tonnage = sum(lot.production_line_ids.filtered(lambda l: l.id != line.id).mapped('tonnage'))
            total = other_tonnage + line.tonnage
            if total > lot.target_tonnage * 1.1:
                raise ValidationError(_(
                    "Cette production dépasserait la capacité du lot de plus de 10%%. "
                    "Capacité: %.2f T, Total après: %.2f T"
                ) % (lot.target_tonnage, total))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('lot_id.fill_percentage')
    def _compute_lot_fill_after(self):
        for line in self:
            line.lot_fill_after = line.lot_id.fill_percentage if line.lot_id else 0

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """Show warning if lot is almost full"""
        if self.lot_id and self.lot_id.fill_percentage >= 90:
            return {
                'warning': {
                    'title': _("Lot presque plein"),
                    'message': _(
                        "Le lot %s est rempli à %.1f%%. "
                        "Capacité restante: %.2f T"
                    ) % (
                        self.lot_id.name, 
                        self.lot_id.fill_percentage, 
                        self.lot_id.remaining_tonnage
                    ),
                }
            }

    @api.onchange('tonnage')
    def _onchange_tonnage(self):
        """Warn if tonnage would overfill the lot"""
        if self.lot_id and self.tonnage:
            new_total = self.lot_id.current_tonnage + self.tonnage
            if new_total > self.lot_id.target_tonnage:
                overfill = new_total - self.lot_id.target_tonnage
                return {
                    'warning': {
                        'title': _("Dépassement de capacité"),
                        'message': _(
                            "Cette production dépasserait la capacité cible de %.2f T."
                        ) % overfill,
                    }
                }

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        for record in records:
            lot = record.lot_id
            transit_order = record.transit_order_id
            
            # Update lot state to in_production if still in draft
            if lot.state == 'draft':
                lot.action_start_production()
            
            # Also update transit order state
            if transit_order.state == 'lots_generated':
                transit_order.action_start_production()
            
            # Post message on lot
            lot.message_post(body=_(
                "Production ajoutée: %.2f T (Batch: %s, Équipe: %s)"
            ) % (record.tonnage, record.batch_number or '-', record.shift or '-'))
        
        return records

    def write(self, vals):
        # Check if we're modifying tonnage
        if 'tonnage' in vals:
            for line in self:
                if line.lot_id.state == 'potted':
                    raise UserError(_(
                        "Impossible de modifier la production d'un lot déjà empoté."
                    ))
        return super().write(vals)

    def unlink(self):
        for line in self:
            if line.lot_id.state == 'potted':
                raise UserError(_(
                    "Impossible de supprimer la production d'un lot déjà empoté."
                ))
        
        # Store lot references for message posting
        lots_to_notify = {}
        for line in self:
            if line.lot_id.id not in lots_to_notify:
                lots_to_notify[line.lot_id.id] = {
                    'lot': line.lot_id,
                    'tonnage': 0,
                }
            lots_to_notify[line.lot_id.id]['tonnage'] += line.tonnage
        
        result = super().unlink()
        
        # Notify lots
        for lot_data in lots_to_notify.values():
            lot_data['lot'].message_post(body=_(
                "Production supprimée: %.2f T"
            ) % lot_data['tonnage'])
        
        return result

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    @api.model
    def get_daily_production_summary(self, date=None):
        """Get summary of production for a specific date"""
        if not date:
            date = fields.Date.context_today(self)
        
        productions = self.search([('date', '=', date)])
        
        summary = {
            'date': date,
            'total_tonnage': sum(productions.mapped('tonnage')),
            'production_count': len(productions),
            'by_product_type': {},
            'by_shift': {},
            'by_operator': {},
        }
        
        for prod in productions:
            # By product type
            pt = prod.product_type
            if pt not in summary['by_product_type']:
                summary['by_product_type'][pt] = 0
            summary['by_product_type'][pt] += prod.tonnage
            
            # By shift
            shift = prod.shift or 'unknown'
            if shift not in summary['by_shift']:
                summary['by_shift'][shift] = 0
            summary['by_shift'][shift] += prod.tonnage
            
            # By operator
            op_name = prod.operator_id.name if prod.operator_id else 'Non assigné'
            if op_name not in summary['by_operator']:
                summary['by_operator'][op_name] = 0
            summary['by_operator'][op_name] += prod.tonnage
        
        return summary

    def name_get(self):
        result = []
        for line in self:
            name = _("%.2f T - %s") % (line.tonnage, line.lot_id.name)
            if line.batch_number:
                name = f"[{line.batch_number}] {name}"
            result.append((line.id, name))
        return result
