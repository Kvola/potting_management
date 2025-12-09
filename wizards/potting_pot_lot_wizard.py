# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PottingPotLotWizard(models.TransientModel):
    _name = 'potting.pot.lot.wizard'
    _description = "Assistant d'empotage de lot"

    lot_id = fields.Many2one(
        'potting.lot',
        string="Lot",
        required=True,
        readonly=True
    )
    
    container_id = fields.Many2one(
        'potting.container',
        string="Conteneur",
        domain="[('state', 'in', ('available', 'loading'))]"
    )
    
    create_new_container = fields.Boolean(
        string="Créer un nouveau conteneur",
        default=False
    )
    
    new_container_name = fields.Char(
        string="Numéro de conteneur"
    )
    
    new_container_type = fields.Selection([
        ('20', "20' (Twenty-foot)"),
        ('40', "40' (Forty-foot)"),
        ('40hc', "40' HC (High Cube)"),
    ], string="Type de conteneur", default='20')
    
    new_seal_number = fields.Char(
        string="Numéro de scellé"
    )

    @api.onchange('create_new_container')
    def _onchange_create_new_container(self):
        if self.create_new_container:
            self.container_id = False
        else:
            self.new_container_name = False
            self.new_container_type = '20'
            self.new_seal_number = False

    def action_confirm(self):
        self.ensure_one()
        
        if self.create_new_container:
            # Create new container
            container = self.env['potting.container'].create({
                'name': self.new_container_name,
                'container_type': self.new_container_type,
                'seal_number': self.new_seal_number,
                'state': 'loading',
            })
        else:
            container = self.container_id
            if container.state == 'available':
                container.action_start_loading()
        
        # Confirm potting
        self.lot_id.action_confirm_potting(container.id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Empotage confirmé'),
                'message': _('Le lot %s a été empoté dans le conteneur %s.') % (
                    self.lot_id.name, container.name
                ),
                'type': 'success',
                'sticky': False,
            }
        }
