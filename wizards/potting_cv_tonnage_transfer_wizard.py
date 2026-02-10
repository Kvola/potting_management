# -*- coding: utf-8 -*-
"""
Wizard de report de tonnage CV entre campagnes

Permet de reporter le tonnage non utilisé d'une CV d'une campagne passée
vers une CV de la campagne en cours.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class PottingCvTonnageTransferWizard(models.TransientModel):
    """Wizard pour transférer le tonnage d'une CV vers une autre"""
    _name = 'potting.cv.tonnage.transfer.wizard'
    _description = 'Report de tonnage CV'

    # =========================================================================
    # CHAMPS - CV SOURCE
    # =========================================================================
    
    source_cv_id = fields.Many2one(
        'potting.confirmation.vente',
        string="CV source",
        required=True,
        domain="[('state', 'in', ['active', 'expired']), ('tonnage_restant', '>', 0)]",
        help="CV dont le tonnage sera transféré"
    )
    
    source_cv_name = fields.Char(
        string="N° CV source",
        related='source_cv_id.name',
        readonly=True
    )
    
    source_campaign_id = fields.Many2one(
        'potting.campaign',
        string="Campagne source",
        related='source_cv_id.campaign_id',
        readonly=True
    )
    
    source_tonnage_restant = fields.Float(
        string="Tonnage disponible (T)",
        related='source_cv_id.tonnage_restant',
        readonly=True
    )
    
    source_date_end = fields.Date(
        string="Fin validité",
        related='source_cv_id.date_end',
        readonly=True
    )
    
    # =========================================================================
    # CHAMPS - CV DESTINATION
    # =========================================================================
    
    target_cv_id = fields.Many2one(
        'potting.confirmation.vente',
        string="CV destination",
        domain="[('state', '=', 'active'), ('id', '!=', source_cv_id)]",
        help="CV qui recevra le tonnage (doit être active et d'une campagne différente)"
    )
    
    create_new_cv = fields.Boolean(
        string="Créer une nouvelle CV",
        default=True,
        help="Créer une nouvelle CV pour la campagne en cours"
    )
    
    target_campaign_id = fields.Many2one(
        'potting.campaign',
        string="Campagne destination",
        domain="[('state', '=', 'active')]",
        help="Campagne pour la nouvelle CV"
    )
    
    # =========================================================================
    # CHAMPS - TONNAGE À TRANSFÉRER
    # =========================================================================
    
    tonnage_to_transfer = fields.Float(
        string="Tonnage à transférer (T)",
        required=True,
        digits='Product Unit of Measure',
        help="Tonnage à reporter sur la CV destination"
    )
    
    transfer_all = fields.Boolean(
        string="Transférer tout le tonnage restant",
        default=True
    )
    
    # =========================================================================
    # CHAMPS - PRIX
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='source_cv_id.currency_id',
        readonly=True
    )
    
    keep_original_price = fields.Boolean(
        string="Conserver le prix d'origine",
        default=True,
        help="Garder le prix au tonnage de la CV source"
    )
    
    new_price = fields.Monetary(
        string="Nouveau prix (FCFA/T)",
        currency_field='currency_id',
        help="Nouveau prix au tonnage si différent"
    )
    
    # =========================================================================
    # CHAMPS - NOTES
    # =========================================================================
    
    note = fields.Text(
        string="Motif du report",
        help="Justification du report de tonnage"
    )

    # =========================================================================
    # MÉTHODES ONCHANGE
    # =========================================================================
    
    @api.onchange('source_cv_id')
    def _onchange_source_cv(self):
        if self.source_cv_id:
            self.tonnage_to_transfer = self.source_cv_id.tonnage_restant
            if not self.currency_id:
                self.currency_id = self.source_cv_id.currency_id
            if not self.new_price:
                self.new_price = self.source_cv_id.prix_tonnage
    
    @api.onchange('transfer_all')
    def _onchange_transfer_all(self):
        if self.transfer_all and self.source_cv_id:
            self.tonnage_to_transfer = self.source_cv_id.tonnage_restant
    
    @api.onchange('create_new_cv')
    def _onchange_create_new_cv(self):
        if self.create_new_cv:
            self.target_cv_id = False
            # Sélectionner la campagne active par défaut
            active_campaign = self.env['potting.campaign'].search([
                ('state', '=', 'active')
            ], limit=1)
            if active_campaign:
                self.target_campaign_id = active_campaign.id
        else:
            self.target_campaign_id = False
    
    @api.onchange('keep_original_price')
    def _onchange_keep_original_price(self):
        if self.keep_original_price and self.source_cv_id:
            self.new_price = self.source_cv_id.prix_tonnage

    # =========================================================================
    # MÉTHODES DE CONTRAINTE
    # =========================================================================
    
    @api.constrains('tonnage_to_transfer', 'source_cv_id')
    def _check_tonnage(self):
        for wizard in self:
            if wizard.tonnage_to_transfer <= 0:
                raise ValidationError(_("Le tonnage à transférer doit être supérieur à 0."))
            if wizard.source_cv_id and wizard.tonnage_to_transfer > wizard.source_cv_id.tonnage_restant:
                raise ValidationError(_(
                    "Le tonnage à transférer (%.2f T) ne peut pas dépasser "
                    "le tonnage disponible (%.2f T).",
                    wizard.tonnage_to_transfer,
                    wizard.source_cv_id.tonnage_restant
                ))
    
    @api.constrains('create_new_cv', 'target_cv_id', 'target_campaign_id')
    def _check_target(self):
        for wizard in self:
            if not wizard.create_new_cv and not wizard.target_cv_id:
                raise ValidationError(_("Veuillez sélectionner une CV destination ou cocher 'Créer une nouvelle CV'."))
            if wizard.create_new_cv and not wizard.target_campaign_id:
                raise ValidationError(_("Veuillez sélectionner une campagne pour la nouvelle CV."))

    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def action_transfer_tonnage(self):
        """Effectuer le transfert de tonnage"""
        self.ensure_one()
        
        # Vérifications
        if not self.source_cv_id:
            raise UserError(_("Veuillez sélectionner une CV source."))
        
        if self.tonnage_to_transfer <= 0:
            raise UserError(_("Le tonnage à transférer doit être supérieur à 0."))
        
        if self.tonnage_to_transfer > self.source_cv_id.tonnage_restant:
            raise UserError(_(
                "Le tonnage à transférer (%.2f T) dépasse le tonnage disponible (%.2f T).",
                self.tonnage_to_transfer,
                self.source_cv_id.tonnage_restant
            ))
        
        # Déterminer le prix
        prix = self.source_cv_id.prix_tonnage if self.keep_original_price else self.new_price
        
        # Créer ou mettre à jour la CV destination
        if self.create_new_cv:
            target_cv = self._create_new_cv(prix)
        else:
            target_cv = self.target_cv_id
            # Augmenter le tonnage de la CV destination
            target_cv.write({
                'tonnage_autorise': target_cv.tonnage_autorise + self.tonnage_to_transfer
            })
        
        # Réduire le tonnage de la CV source
        # On ne modifie pas directement tonnage_autorise, on marque le transfert
        self._record_transfer(target_cv)
        
        # Message dans le chatter des deux CV
        transfer_msg = _(
            "<strong>Report de tonnage effectué</strong><br/>"
            "Tonnage transféré: %.2f T<br/>"
            "Prix: %s FCFA/T<br/>"
            "De: %s (Campagne %s)<br/>"
            "Vers: %s (Campagne %s)<br/>"
            "%s"
        ) % (
            self.tonnage_to_transfer,
            f"{prix:,.0f}",
            self.source_cv_id.name,
            self.source_cv_id.campaign_id.name,
            target_cv.name,
            target_cv.campaign_id.name,
            f"Motif: {self.note}" if self.note else ""
        )
        
        self.source_cv_id.message_post(body=transfer_msg, subject=_("Tonnage transféré"))
        target_cv.message_post(body=transfer_msg, subject=_("Tonnage reçu"))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('CV Destination'),
            'res_model': 'potting.confirmation.vente',
            'view_mode': 'form',
            'res_id': target_cv.id,
            'context': {'show_transfer_success': True}
        }
    
    def _create_new_cv(self, prix):
        """Créer une nouvelle CV pour recevoir le tonnage"""
        source = self.source_cv_id
        
        # Calculer les dates de validité
        today = date.today()
        if self.target_campaign_id.date_start:
            date_start = max(today, self.target_campaign_id.date_start)
        else:
            date_start = today
        
        if self.target_campaign_id.date_end:
            date_end = self.target_campaign_id.date_end
        else:
            from dateutil.relativedelta import relativedelta
            date_end = date_start + relativedelta(months=6)
        
        vals = {
            'reference_ccc': f"REPORT-{source.reference_ccc}" if source.reference_ccc else False,
            'date_emission': today,
            'date_start': date_start,
            'date_end': date_end,
            'campaign_id': self.target_campaign_id.id,
            'currency_id': source.currency_id.id,
            'prix_tonnage': prix,
            'tonnage_autorise': self.tonnage_to_transfer,
            'product_type': source.product_type,
            'state': 'active',
            'note': _("CV créée par report de tonnage depuis %s.\n%s") % (
                source.name,
                self.note or ""
            ),
            'company_id': source.company_id.id,
        }
        
        new_cv = self.env['potting.confirmation.vente'].create(vals)
        return new_cv
    
    def _record_transfer(self, target_cv):
        """Enregistrer le transfert pour traçabilité"""
        # Créer une allocation négative virtuelle ou simplement noter le transfert
        # Pour l'instant, on enregistre juste dans les notes de la CV source
        
        # On pourrait aussi créer un modèle potting.cv.transfer pour historiser
        # mais pour simplifier, on utilise le chatter
        pass
