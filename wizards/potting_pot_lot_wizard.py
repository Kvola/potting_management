# -*- coding: utf-8 -*-

import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PottingPotLotWizard(models.TransientModel):
    """Wizard pour l'empotage d'un lot dans un conteneur.
    
    Ce wizard permet de:
    - Sélectionner un conteneur existant disponible
    - Créer un nouveau conteneur à la volée
    - Valider et confirmer l'opération d'empotage
    """
    _name = 'potting.pot.lot.wizard'
    _description = "Assistant d'empotage de lot"

    # =========================================================================
    # FIELDS
    # =========================================================================
    
    lot_id = fields.Many2one(
        'potting.lot',
        string="Lot",
        required=True,
        readonly=True,
        ondelete='cascade',
        help="Le lot à empoter dans le conteneur."
    )
    
    lot_tonnage = fields.Float(
        related='lot_id.target_tonnage',
        string="Tonnage du lot",
        readonly=True
    )
    
    container_id = fields.Many2one(
        'potting.container',
        string="Conteneur",
        domain="[('state', 'in', ('available', 'loading'))]",
        help="Sélectionnez un conteneur disponible ou en cours de chargement."
    )
    
    container_available_capacity = fields.Float(
        compute='_compute_container_available_capacity',
        string="Capacité disponible",
        help="Capacité restante dans le conteneur sélectionné."
    )
    
    create_new_container = fields.Boolean(
        string="Créer un nouveau conteneur",
        default=False,
        help="Cochez pour créer un nouveau conteneur au lieu d'en sélectionner un existant."
    )
    
    new_container_name = fields.Char(
        string="Numéro de conteneur",
        help="Le numéro unique d'identification du conteneur (ex: MSKU1234567)."
    )
    
    new_container_type = fields.Selection([
        ('20', "20' (Twenty-foot) - 22T max"),
        ('40', "40' (Forty-foot) - 27T max"),
        ('40hc', "40' HC (High Cube) - 27T max"),
    ], string="Type de conteneur", default='20',
       help="Le type de conteneur détermine sa capacité maximale.")
    
    new_seal_number = fields.Char(
        string="Numéro de scellé",
        help="Le numéro de scellé officiel du conteneur."
    )
    
    can_confirm = fields.Boolean(
        compute='_compute_can_confirm',
        string="Peut confirmer",
        help="Indique si toutes les conditions sont remplies pour confirmer l'empotage."
    )
    
    warning_message = fields.Char(
        compute='_compute_warning_message',
        string="Avertissement"
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================
    
    @api.depends('container_id', 'container_id.total_tonnage', 'container_id.max_capacity')
    def _compute_container_available_capacity(self):
        """Calcule la capacité disponible dans le conteneur sélectionné."""
        for wizard in self:
            if wizard.container_id:
                wizard.container_available_capacity = (
                    wizard.container_id.max_capacity - 
                    wizard.container_id.total_tonnage
                )
            else:
                wizard.container_available_capacity = 0.0
    
    @api.depends('create_new_container', 'container_id', 'new_container_name', 
                 'lot_id', 'container_available_capacity', 'lot_tonnage')
    def _compute_can_confirm(self):
        """Vérifie si l'empotage peut être confirmé."""
        for wizard in self:
            can_confirm = True
            
            if not wizard.lot_id:
                can_confirm = False
            elif wizard.create_new_container:
                if not wizard.new_container_name or not wizard.new_container_name.strip():
                    can_confirm = False
            else:
                if not wizard.container_id:
                    can_confirm = False
                elif wizard.container_available_capacity < wizard.lot_tonnage:
                    can_confirm = False
            
            wizard.can_confirm = can_confirm
    
    @api.depends('container_id', 'lot_tonnage', 'container_available_capacity')
    def _compute_warning_message(self):
        """Génère un message d'avertissement si nécessaire."""
        for wizard in self:
            wizard.warning_message = False
            
            if wizard.container_id and wizard.lot_tonnage:
                if wizard.container_available_capacity < wizard.lot_tonnage:
                    wizard.warning_message = _(
                        "⚠️ Le conteneur n'a pas assez de capacité disponible! "
                        "Disponible: %.2f T, Requis: %.2f T"
                    ) % (wizard.container_available_capacity, wizard.lot_tonnage)
                elif wizard.container_available_capacity < wizard.lot_tonnage * 1.1:
                    wizard.warning_message = _(
                        "ℹ️ Le conteneur sera presque plein après cet empotage."
                    )

    # =========================================================================
    # ONCHANGE METHODS
    # =========================================================================

    @api.onchange('create_new_container')
    def _onchange_create_new_container(self):
        """Réinitialise les champs selon le mode de création."""
        if self.create_new_container:
            self.container_id = False
        else:
            self.new_container_name = False
            self.new_container_type = '20'
            self.new_seal_number = False
    
    @api.onchange('new_container_name')
    def _onchange_new_container_name(self):
        """Formate et valide le numéro de conteneur."""
        if self.new_container_name:
            # Convertir en majuscules et supprimer les espaces
            self.new_container_name = self.new_container_name.strip().upper()
            
            # Vérifier le format standard ISO 6346
            pattern = r'^[A-Z]{4}\d{7}$'
            if not re.match(pattern, self.new_container_name):
                return {
                    'warning': {
                        'title': _("Format non standard"),
                        'message': _(
                            "Le numéro de conteneur '%s' ne correspond pas au format "
                            "ISO 6346 standard (4 lettres + 7 chiffres). "
                            "Exemple: MSKU1234567"
                        ) % self.new_container_name
                    }
                }

    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    
    def _validate_lot(self):
        """Valide que le lot peut être empoté."""
        self.ensure_one()
        
        if not self.lot_id:
            raise UserError(_("Aucun lot sélectionné."))
        
        if self.lot_id.state not in ('pending', 'ready'):
            raise UserError(_(
                "Le lot '%s' ne peut pas être empoté car son état est '%s'. "
                "Seuls les lots en attente ou prêts peuvent être empotés."
            ) % (self.lot_id.name, self.lot_id.state))
        
        if self.lot_id.current_tonnage <= 0:
            raise UserError(_(
                "Le lot '%s' a un tonnage invalide (%s T). "
                "Le tonnage doit être supérieur à zéro."
            ) % (self.lot_id.name, self.lot_id.current_tonnage))
        
        return True
    
    def _validate_container_selection(self):
        """Valide la sélection ou création de conteneur."""
        self.ensure_one()
        
        if self.create_new_container:
            if not self.new_container_name or not self.new_container_name.strip():
                raise UserError(_(
                    "Veuillez saisir un numéro de conteneur valide."
                ))
            
            # Vérifier l'unicité du numéro de conteneur
            existing = self.env['potting.container'].search([
                ('name', '=ilike', self.new_container_name.strip())
            ], limit=1)
            if existing:
                raise UserError(_(
                    "Un conteneur avec le numéro '%s' existe déjà (ID: %s, État: %s)."
                ) % (self.new_container_name, existing.id, existing.state))
        else:
            if not self.container_id:
                raise UserError(_(
                    "Veuillez sélectionner un conteneur ou cocher "
                    "'Créer un nouveau conteneur'."
                ))
            
            if self.container_id.state not in ('available', 'loading'):
                raise UserError(_(
                    "Le conteneur '%s' n'est pas disponible (état: %s)."
                ) % (self.container_id.name, self.container_id.state))
            
            # Vérifier la capacité
            available = self.container_available_capacity
            if available < self.lot_tonnage:
                raise UserError(_(
                    "Le conteneur '%s' n'a pas assez de capacité disponible. "
                    "Capacité disponible: %.2f T, Tonnage du lot: %.2f T."
                ) % (self.container_id.name, available, self.lot_tonnage))
        
        return True

    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def _create_new_container(self):
        """Crée un nouveau conteneur avec les données du wizard."""
        self.ensure_one()
        
        container_vals = {
            'name': self.new_container_name.strip().upper(),
            'container_type': self.new_container_type,
            'seal_number': self.new_seal_number.strip() if self.new_seal_number else False,
            'state': 'loading',
        }
        
        container = self.env['potting.container'].create(container_vals)
        _logger.info(
            "Nouveau conteneur créé via wizard: %s (type: %s)", 
            container.name, container.container_type
        )
        
        return container
    
    def _get_or_create_container(self):
        """Retourne le conteneur à utiliser (existant ou nouveau)."""
        self.ensure_one()
        
        if self.create_new_container:
            return self._create_new_container()
        else:
            container = self.container_id
            if container.state == 'available':
                container.action_start_loading()
                _logger.info(
                    "Conteneur %s passé en mode chargement", 
                    container.name
                )
            return container

    def action_confirm(self):
        """Confirme l'empotage du lot dans le conteneur."""
        self.ensure_one()
        
        _logger.info(
            "Début confirmation empotage - Lot: %s, Mode: %s", 
            self.lot_id.name,
            'nouveau conteneur' if self.create_new_container else 'conteneur existant'
        )
        
        # Validations
        self._validate_lot()
        self._validate_container_selection()
        
        try:
            # Obtenir ou créer le conteneur
            container = self._get_or_create_container()
            
            # Confirmer l'empotage
            self.lot_id.action_confirm_potting(container.id)
            
            _logger.info(
                "Empotage confirmé avec succès - Lot: %s -> Conteneur: %s",
                self.lot_id.name, container.name
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Empotage confirmé'),
                    'message': _(
                        'Le lot %s (%.2f T) a été empoté dans le conteneur %s.'
                    ) % (self.lot_id.name, self.lot_id.current_tonnage, container.name),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            
        except Exception as e:
            _logger.exception(
                "Erreur lors de l'empotage du lot %s: %s",
                self.lot_id.name, str(e)
            )
            raise UserError(_(
                "Une erreur est survenue lors de l'empotage: %s"
            ) % str(e))
    
    def action_cancel(self):
        """Annule le wizard et retourne à la vue précédente."""
        return {'type': 'ir.actions.act_window_close'}
