# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
    """Extension de account.move pour la facturation partielle des OT."""
    
    _inherit = 'account.move'
    
    # -------------------------------------------------------------------------
    # CHAMPS - LIEN AVEC POTTING MANAGEMENT
    # -------------------------------------------------------------------------
    potting_transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        copy=False,
        readonly=True,
        index=True,
        help="Ordre de Transit associé à cette facture"
    )
    
    potting_delivery_note_id = fields.Many2one(
        'potting.delivery.note',
        string="Bon de Livraison",
        copy=False,
        readonly=True,
        index=True,
        help="Bon de livraison associé à cette facture (facturation partielle)"
    )
    
    potting_invoiced_tonnage = fields.Float(
        string="Tonnage facturé (T)",
        digits='Product Unit of Measure',
        copy=False,
        readonly=True,
        help="Tonnage facturé dans cette facture"
    )
    
    # -------------------------------------------------------------------------
    # COMPUTED FIELDS
    # -------------------------------------------------------------------------
    is_potting_invoice = fields.Boolean(
        string="Facture Potting",
        compute='_compute_is_potting_invoice',
        store=True,
        help="Indique si cette facture est liée à un Ordre de Transit"
    )
    
    @api.depends('potting_transit_order_id')
    def _compute_is_potting_invoice(self):
        for move in self:
            move.is_potting_invoice = bool(move.potting_transit_order_id)
