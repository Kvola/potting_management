# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class PottingFormule(models.Model):
    """Formule (FO) - Mécanisme de fixation du prix du cacao
    
    La Formule est un document lié à une Confirmation de Vente qui définit
    le prix et les conditions de paiement pour les producteurs. Elle peut
    être attachée à un Ordre de Transit (OT).
    
    Les paiements se font en 2 temps:
    - Paiement avant-vente: Avance versée avant la commercialisation
    - Paiement après-vente: Solde versé après réalisation de la vente
    
    Certaines taxes/redevances sont prélevées directement sur la formule.
    """
    _name = 'potting.formule'
    _description = 'Formule (FO)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_emission desc, name desc'
    _check_company_auto = True

    # =========================================================================
    # CONTRAINTES SQL
    # =========================================================================
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 
         'Le numéro de formule doit être unique!'),
        ('tonnage_positive', 'CHECK(tonnage > 0)', 
         'Le tonnage doit être supérieur à 0!'),
        ('prix_tonnage_positive', 'CHECK(prix_tonnage >= 0)', 
         'Le prix au tonnage doit être positif ou nul!'),
        ('pourcentage_valid', 'CHECK(pourcentage_avant_vente >= 0 AND pourcentage_avant_vente <= 100)', 
         'Le pourcentage avant-vente doit être entre 0 et 100!'),
        ('coefficient_positive', 'CHECK(coefficient_conversion > 0)', 
         'Le coefficient de conversion doit être supérieur à 0!'),
        ('numero_fo1_uniq', 'unique(numero_fo1, company_id)', 
         'Le numéro FO1 doit être unique!'),
        # Contrainte: apres_vente_paye ne peut pas être True si avant_vente_paye est False
        ('apres_vente_requires_avant_vente', 
         'CHECK(NOT (apres_vente_paye = TRUE AND avant_vente_paye = FALSE))',
         'Le paiement après-vente nécessite que le paiement avant-vente soit effectué en premier!'),
    ]

    # =========================================================================
    # CHAMPS - IDENTIFICATION
    # =========================================================================
    
    name = fields.Char(
        string="Numéro FO",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau'),
        tracking=True,
        index=True,
        help="Numéro de séquence interne de la Formule"
    )
    
    reference_ccc = fields.Char(
        string="Référence CCC",
        tracking=True,
        index=True,
        help="Référence officielle complète (ex: FO1/F025/327/0020/0084/0084)"
    )
    
    numero_fo1 = fields.Char(
        string="Numéro FO1",
        tracking=True,
        index=True,
        help="Numéro court de la formule (ex: 22-3276)"
    )
    
    date_fo1 = fields.Date(
        string="Date FO1",
        tracking=True,
        help="Date d'émission de la formule FO1 par le CCC"
    )
    
    # =========================================================================
    # CHAMPS - GRADE ET NOMENCLATURE
    # =========================================================================
    
    grade = fields.Selection([
        ('GF', 'GF - Good Fermented'),
        ('F', 'F - Fair Fermented'),
        ('SS', 'SS - Sub-Standard'),
        ('LIMIT', 'Limite'),
    ], string="Grade",
       tracking=True,
       help="Grade qualité du produit (ex: GF = Good Fermented)")
    
    nomenclature_douaniere = fields.Char(
        string="Nomenclature douanière",
        tracking=True,
        help="Code nomenclature douanière (ex: 1802 00 00 00 pour Tourteaux)"
    )
    
    # =========================================================================
    # CHAMPS - CONTRAT COMMERCIAL
    # =========================================================================
    
    numero_contrat = fields.Char(
        string="N° Contrat",
        tracking=True,
        index=True,
        help="Numéro du contrat commercial (ex: EIFC-TC012/25)"
    )
    
    numero_contrat_detail = fields.Char(
        string="N° Contrat détail",
        tracking=True,
        help="Numéro de contrat détaillé CCC (ex: 327-21416)"
    )
    
    date_contrat = fields.Date(
        string="Date contrat",
        tracking=True,
        help="Date du contrat commercial"
    )
    
    confirmation_vente_numero = fields.Char(
        string="N° Confirmation vente",
        tracking=True,
        help="Numéro de la confirmation de vente (ex: 327-21553)"
    )
    
    date_confirmation_vente = fields.Date(
        string="Date confirmation",
        tracking=True,
        help="Date de la confirmation de vente"
    )
    
    # =========================================================================
    # CHAMPS - RELATIONS
    # =========================================================================
    
    confirmation_vente_id = fields.Many2one(
        'potting.confirmation.vente',
        string="Confirmation de Vente",
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
        domain="[('state', '=', 'active')]",
        help="CV associée à cette formule"
    )
    
    transit_order_id = fields.Many2one(
        'potting.transit.order',
        string="Ordre de Transit",
        ondelete='set null',
        tracking=True,
        index=True,
        help="OT lié à cette formule (optionnel - une FO peut exister sans OT)"
    )
    
    campaign_id = fields.Many2one(
        'potting.campaign',
        string="Campagne",
        related='confirmation_vente_id.campaign_id',
        store=True,
        help="Campagne café-cacao (héritée de la CV)"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    
    # =========================================================================
    # CHAMPS - DATES
    # =========================================================================
    
    date_emission = fields.Date(
        string="Date d'émission",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
        help="Date d'émission de la Formule"
    )
    
    date_validite = fields.Date(
        string="Date de validité",
        tracking=True,
        help="Date limite de validité de la formule"
    )
    
    # =========================================================================
    # CHAMPS - TYPE DE PRODUIT
    # =========================================================================
    
    product_type = fields.Selection([
        ('cocoa_mass', 'Masse de cacao'),
        ('cocoa_butter', 'Beurre de cacao'),
        ('cocoa_cake', 'Cake (Tourteau) de cacao'),
        ('cocoa_powder', 'Poudre de cacao'),
    ], string="Type de produit",
       required=True,
       tracking=True,
       help="Type de produit semi-fini concerné par cette formule")
    
    # =========================================================================
    # CHAMPS - PRIX ET DEVISE
    # =========================================================================
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self._get_default_currency(),
        required=True,
        tracking=True
    )
    
    currency_usd_id = fields.Many2one(
        'res.currency',
        string="Devise USD",
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
        help="Devise USD pour les conversions"
    )
    
    prix_tonnage = fields.Monetary(
        string="Prix au tonnage (FCFA)",
        currency_field='currency_id',
        required=True,
        tracking=True,
        help="Prix par tonne de cacao (FCFA/tonne)"
    )
    
    prix_tonnage_usd = fields.Monetary(
        string="Prix au tonnage (USD)",
        currency_field='currency_usd_id',
        tracking=True,
        help="Prix par tonne en USD (référence marché international)"
    )
    
    taux_change = fields.Float(
        string="Taux de change",
        digits=(12, 6),
        tracking=True,
        help="Taux de change USD/XOF appliqué"
    )
    
    prix_reference = fields.Monetary(
        string="Prix de référence (FCFA/Kg)",
        currency_field='currency_id',
        tracking=True,
        help="Prix de référence CCC en FCFA/Kg (ex: 3 929,751 Frs CFA/Kg)"
    )
    
    prix_kg = fields.Monetary(
        string="Prix effectif (FCFA/Kg)",
        currency_field='currency_id',
        tracking=True,
        help="Prix effectif de vente en FCFA/Kg (ex: 3 300 Frs CFA/Kg)"
    )
    
    # =========================================================================
    # CHAMPS - TRANSITAIRE ET NAVIRE
    # =========================================================================
    
    transitaire_id = fields.Many2one(
        'potting.forwarding.agent',
        string="Transitaire",
        tracking=True,
        help="Transitaire responsable de l'exportation"
    )
    
    transitaire_name = fields.Char(
        string="Nom transitaire",
        related='transitaire_id.name',
        store=True
    )
    
    navire = fields.Char(
        string="Navire",
        tracking=True,
        help="Nom du navire d'exportation (ex: MSC SORAYA)"
    )
    
    # =========================================================================
    # CHAMPS - DESTINATION ET PORTS
    # =========================================================================
    
    exportateur = fields.Char(
        string="Exportateur",
        tracking=True,
        default="IVORY COCOA PRODUCTS",
        help="Nom de l'exportateur"
    )
    
    destinataire_nom = fields.Char(
        string="Destinataire",
        tracking=True,
        help="Nom complet du destinataire"
    )
    
    destinataire_adresse = fields.Char(
        string="Adresse destinataire",
        tracking=True,
        help="Adresse complète du destinataire"
    )
    
    destination_country_id = fields.Many2one(
        'res.country',
        string="Pays destination",
        tracking=True,
        help="Pays de destination de l'exportation"
    )
    
    destination_code = fields.Char(
        string="Code destination",
        tracking=True,
        help="Code destination CCC (ex: Egypt AF1)"
    )
    
    port_destination = fields.Char(
        string="Port de destination",
        tracking=True,
        help="Port de destination (ex: Alexandrie)"
    )
    
    port_embarquement = fields.Selection([
        ('abidjan', 'Abidjan'),
        ('san_pedro', 'San Pedro'),
    ], string="Port d'embarquement",
       default='san_pedro',
       tracking=True,
       help="Port d'embarquement en Côte d'Ivoire")
    
    # =========================================================================
    # CHAMPS - PÉRIODE D'EMBARQUEMENT
    # =========================================================================
    
    periode_embarquement_debut = fields.Selection([
        ('01', 'Janvier'),
        ('02', 'Février'),
        ('03', 'Mars'),
        ('04', 'Avril'),
        ('05', 'Mai'),
        ('06', 'Juin'),
        ('07', 'Juillet'),
        ('08', 'Août'),
        ('09', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre'),
    ], string="Début période embarquement",
       tracking=True,
       help="Mois de début de la période d'embarquement")
    
    periode_embarquement_fin = fields.Selection([
        ('01', 'Janvier'),
        ('02', 'Février'),
        ('03', 'Mars'),
        ('04', 'Avril'),
        ('05', 'Mai'),
        ('06', 'Juin'),
        ('07', 'Juillet'),
        ('08', 'Août'),
        ('09', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre'),
    ], string="Fin période embarquement",
       tracking=True,
       help="Mois de fin de la période d'embarquement")
    
    periode_embarquement_display = fields.Char(
        string="Période d'embarquement",
        compute='_compute_periode_embarquement',
        store=True,
        help="Affichage de la période d'embarquement"
    )
    
    # =========================================================================
    # CHAMPS - TONNAGE
    # =========================================================================
    
    tonnage = fields.Float(
        string="Tonnage net (T)",
        required=True,
        tracking=True,
        digits='Product Unit of Measure',
        help="Tonnage net couvert par cette formule (en tonnes)"
    )
    
    tonnage_kg = fields.Float(
        string="Tonnage (Kg)",
        compute='_compute_tonnage_kg',
        store=True,
        digits=(16, 0),
        help="Tonnage en kilogrammes"
    )
    
    tonnage_converti = fields.Float(
        string="Tonnage converti (Kg)",
        tracking=True,
        digits=(16, 0),
        help="Tonnage converti selon coefficient (ex: 60 000 kg → 75 000 kg)"
    )
    
    tonnage_brut = fields.Float(
        string="Tonnage brut (Kg)",
        tracking=True,
        digits=(16, 0),
        help="Tonnage brut incluant emballage (ex: 60 180 kg)"
    )
    
    coefficient_conversion = fields.Float(
        string="Coefficient conversion",
        digits=(5, 4),
        default=1.0,
        tracking=True,
        help="Coefficient de conversion pour le tonnage (ex: 1.25)"
    )
    
    # =========================================================================
    # CHAMPS - EMBALLAGE
    # =========================================================================
    
    emballage_type = fields.Selection([
        ('big_bag', 'Big Bags'),
        ('sacs', 'Sacs'),
        ('cartons', 'Cartons'),
        ('vrac', 'Vrac'),
    ], string="Type d'emballage",
       tracking=True,
       help="Type d'emballage utilisé pour l'export")
    
    nombre_conteneurs = fields.Integer(
        string="Nombre de conteneurs",
        tracking=True,
        help="Nombre de conteneurs pour cette formule"
    )
    
    type_transit = fields.Selection([
        ('conteneur', 'Produits transformés en conteneurs'),
        ('vrac', 'Vrac'),
        ('conventionnel', 'Conventionnel'),
    ], string="Type de transit",
       default='conteneur',
       tracking=True,
       help="Type de transit pour l'exportation")
    
    # =========================================================================
    # CHAMPS - DIFFÉRENTIEL QUALITÉ
    # =========================================================================
    
    differentiel_qualite = fields.Monetary(
        string="Différentiel qualité",
        currency_field='currency_id',
        tracking=True,
        help="Prime (+) ou décote (-) liée à la qualité du cacao"
    )
    
    differentiel_type = fields.Selection([
        ('prime', 'Prime qualité'),
        ('decote', 'Décote'),
        ('neutre', 'Neutre'),
    ], string="Type de différentiel",
       default='neutre',
       tracking=True)
    
    # =========================================================================
    # CHAMPS - MONTANTS CALCULÉS
    # =========================================================================
    
    montant_brut = fields.Monetary(
        string="Montant brut",
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help="Montant brut = Prix × Tonnage"
    )
    
    montant_total = fields.Monetary(
        string="Montant total",
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help="Montant total incluant le différentiel qualité"
    )
    
    # =========================================================================
    # CHAMPS - TAXES ET REDEVANCES PRÉLEVÉES
    # =========================================================================
    
    taxe_ids = fields.One2many(
        'potting.formule.taxe',
        'formule_id',
        string="Taxes/Redevances",
        copy=True,
        help="Taxes et redevances prélevées sur cette formule"
    )
    
    total_taxes_prelevees = fields.Monetary(
        string="Total taxes prélevées",
        currency_field='currency_id',
        compute='_compute_taxes',
        store=True,
        help="Total des taxes déjà prélevées (marquées comme payées)"
    )
    
    total_taxes_a_payer = fields.Monetary(
        string="Total taxes à payer",
        currency_field='currency_id',
        compute='_compute_taxes',
        store=True,
        help="Total des taxes restant à payer par chèque"
    )
    
    montant_net = fields.Monetary(
        string="Montant net",
        currency_field='currency_id',
        compute='_compute_amounts',
        store=True,
        help="Montant net après déduction des taxes prélevées"
    )
    
    # =========================================================================
    # CHAMPS - PAIEMENT AVANT-VENTE
    # =========================================================================
    
    montant_avant_vente = fields.Monetary(
        string="Montant avant-vente",
        currency_field='currency_id',
        compute='_compute_paiements',
        store=True,
        help="Montant du premier paiement (avant commercialisation des produits)"
    )
    
    pourcentage_avant_vente = fields.Float(
        string="% Avant-vente",
        default=60.0,
        tracking=True,
        help="Pourcentage du montant net versé avant la vente"
    )
    
    date_paiement_avant_vente_prevue = fields.Date(
        string="Date prévue (avant-vente)",
        tracking=True,
        help="Date prévue pour le paiement avant-vente"
    )
    
    date_paiement_avant_vente = fields.Date(
        string="Date effective (avant-vente)",
        tracking=True,
        help="Date effective du paiement avant-vente"
    )
    
    avant_vente_paye = fields.Boolean(
        string="Avant-vente payé",
        default=False,
        tracking=True,
        help="Indique si le paiement avant-vente a été effectué"
    )
    
    payment_request_avant_vente_id = fields.Many2one(
        'payment.request',
        string="Demande paiement (avant-vente)",
        tracking=True,
        copy=False,
        help="Demande de paiement par chèque pour le versement avant-vente"
    )
    
    # =========================================================================
    # CHAMPS - PAIEMENT APRÈS-VENTE
    # =========================================================================
    
    montant_apres_vente = fields.Monetary(
        string="Montant après-vente",
        currency_field='currency_id',
        compute='_compute_paiements',
        store=True,
        help="Montant du second paiement (après commercialisation des produits)"
    )
    
    pourcentage_apres_vente = fields.Float(
        string="% Après-vente",
        compute='_compute_pourcentage_apres_vente',
        store=True,
        help="Pourcentage du montant net versé après la vente (= 100 - % avant-vente)"
    )
    
    date_paiement_apres_vente_prevue = fields.Date(
        string="Date prévue (après-vente)",
        tracking=True,
        help="Date prévue pour le paiement après-vente"
    )
    
    date_paiement_apres_vente = fields.Date(
        string="Date effective (après-vente)",
        tracking=True,
        help="Date effective du paiement après-vente"
    )
    
    apres_vente_paye = fields.Boolean(
        string="Après-vente payé",
        default=False,
        tracking=True,
        help="Indique si le paiement après-vente a été effectué"
    )
    
    payment_request_apres_vente_id = fields.Many2one(
        'payment.request',
        string="Demande paiement (après-vente)",
        tracking=True,
        copy=False,
        help="Demande de paiement par chèque pour le versement après-vente"
    )
    
    # =========================================================================
    # CHAMPS - TOTAL PAIEMENTS
    # =========================================================================
    
    total_paye = fields.Monetary(
        string="Total payé",
        currency_field='currency_id',
        compute='_compute_total_paye',
        store=True,
        help="Total des montants déjà versés"
    )
    
    reste_a_payer = fields.Monetary(
        string="Reste à payer",
        currency_field='currency_id',
        compute='_compute_total_paye',
        store=True,
        help="Montant restant à verser"
    )
    
    paiement_progress = fields.Float(
        string="Progression paiement (%)",
        compute='_compute_total_paye',
        store=True
    )
    
    # =========================================================================
    # CHAMPS - ÉTAT
    # =========================================================================
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validée'),
        ('partial_paid', 'Partiellement payée'),
        ('paid', 'Entièrement payée'),
        ('cancelled', 'Annulée'),
    ], string="État",
       default='draft',
       tracking=True,
       index=True,
       copy=False)
    
    note = fields.Text(
        string="Notes",
        help="Notes et observations internes"
    )
    
    # =========================================================================
    # MÉTHODES PAR DÉFAUT
    # =========================================================================
    
    def _get_default_currency(self):
        """Retourne XOF (FCFA) par défaut"""
        xof = self.env['res.currency'].search([('name', '=', 'XOF')], limit=1)
        return xof or self.env.company.currency_id
    
    # =========================================================================
    # MÉTHODES COMPUTED
    # =========================================================================
    
    @api.depends('tonnage')
    def _compute_tonnage_kg(self):
        """Convertir le tonnage en kilogrammes"""
        for record in self:
            record.tonnage_kg = record.tonnage * 1000
    
    @api.depends('periode_embarquement_debut', 'periode_embarquement_fin')
    def _compute_periode_embarquement(self):
        """Afficher la période d'embarquement lisiblement"""
        mois_labels = {
            '01': 'Janvier', '02': 'Février', '03': 'Mars', '04': 'Avril',
            '05': 'Mai', '06': 'Juin', '07': 'Juillet', '08': 'Août',
            '09': 'Septembre', '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
        }
        for record in self:
            if record.periode_embarquement_debut and record.periode_embarquement_fin:
                debut = mois_labels.get(record.periode_embarquement_debut, '')
                fin = mois_labels.get(record.periode_embarquement_fin, '')
                if debut == fin:
                    record.periode_embarquement_display = debut
                else:
                    record.periode_embarquement_display = f"{debut} - {fin}"
            elif record.periode_embarquement_debut:
                record.periode_embarquement_display = mois_labels.get(
                    record.periode_embarquement_debut, '')
            else:
                record.periode_embarquement_display = False
    
    @api.depends('prix_tonnage', 'tonnage', 'differentiel_qualite', 
                 'total_taxes_prelevees')
    def _compute_amounts(self):
        for record in self:
            record.montant_brut = record.prix_tonnage * record.tonnage
            record.montant_total = record.montant_brut + (record.differentiel_qualite or 0)
            record.montant_net = record.montant_total - record.total_taxes_prelevees
    
    @api.depends('taxe_ids', 'taxe_ids.montant', 'taxe_ids.is_preleve')
    def _compute_taxes(self):
        for record in self:
            taxes_prelevees = record.taxe_ids.filtered(lambda t: t.is_preleve)
            taxes_a_payer = record.taxe_ids.filtered(lambda t: not t.is_preleve)
            record.total_taxes_prelevees = sum(taxes_prelevees.mapped('montant'))
            record.total_taxes_a_payer = sum(taxes_a_payer.mapped('montant'))
    
    @api.depends('pourcentage_avant_vente')
    def _compute_pourcentage_apres_vente(self):
        for record in self:
            record.pourcentage_apres_vente = 100.0 - record.pourcentage_avant_vente
    
    @api.depends('montant_net', 'pourcentage_avant_vente', 'pourcentage_apres_vente')
    def _compute_paiements(self):
        for record in self:
            if record.montant_net:
                record.montant_avant_vente = record.montant_net * (record.pourcentage_avant_vente / 100)
                record.montant_apres_vente = record.montant_net * (record.pourcentage_apres_vente / 100)
            else:
                record.montant_avant_vente = 0
                record.montant_apres_vente = 0
    
    @api.depends('montant_net', 'avant_vente_paye', 'apres_vente_paye',
                 'montant_avant_vente', 'montant_apres_vente')
    def _compute_total_paye(self):
        for record in self:
            total = 0
            if record.avant_vente_paye:
                total += record.montant_avant_vente
            if record.apres_vente_paye:
                total += record.montant_apres_vente
            record.total_paye = total
            record.reste_a_payer = record.montant_net - total
            if record.montant_net > 0:
                record.paiement_progress = (total / record.montant_net) * 100
            else:
                record.paiement_progress = 0
    
    # =========================================================================
    # ONCHANGE
    # =========================================================================
    
    @api.onchange('confirmation_vente_id')
    def _onchange_confirmation_vente(self):
        """Pré-remplir les champs depuis la CV sélectionnée"""
        if self.confirmation_vente_id:
            cv = self.confirmation_vente_id
            self.prix_tonnage = cv.prix_tonnage
            self.product_type = cv.product_type if cv.product_type != 'all' else False
            # Pré-remplir le numéro de confirmation
            if cv.reference_ccc and not self.confirmation_vente_numero:
                self.confirmation_vente_numero = cv.reference_ccc
            if cv.date_emission and not self.date_confirmation_vente:
                self.date_confirmation_vente = cv.date_emission
    
    @api.onchange('prix_kg')
    def _onchange_prix_kg(self):
        """Calculer le prix au tonnage depuis le prix au kg"""
        if self.prix_kg:
            self.prix_tonnage = self.prix_kg * 1000
    
    @api.onchange('tonnage', 'coefficient_conversion')
    def _onchange_tonnage_conversion(self):
        """Calculer le tonnage converti automatiquement"""
        if self.tonnage and self.coefficient_conversion:
            self.tonnage_converti = self.tonnage * 1000 * self.coefficient_conversion
    
    @api.onchange('destination_country_id')
    def _onchange_destination_country(self):
        """Pré-remplir le code destination depuis le pays"""
        if self.destination_country_id and not self.destination_code:
            self.destination_code = self.destination_country_id.name
    
    @api.onchange('transitaire_id')
    def _onchange_transitaire(self):
        """Mettre à jour les infos transitaire"""
        if self.transitaire_id:
            # Le nom est déjà related, pas besoin de le remplir
            pass
    
    @api.onchange('differentiel_type', 'differentiel_qualite')
    def _onchange_differentiel(self):
        if self.differentiel_type == 'decote' and self.differentiel_qualite > 0:
            self.differentiel_qualite = -abs(self.differentiel_qualite)
        elif self.differentiel_type == 'prime' and self.differentiel_qualite < 0:
            self.differentiel_qualite = abs(self.differentiel_qualite)
        elif self.differentiel_type == 'neutre':
            self.differentiel_qualite = 0
    
    @api.onchange('product_type')
    def _onchange_product_type(self):
        """Pré-remplir la nomenclature douanière selon le type de produit"""
        nomenclatures = {
            'cocoa_mass': '1803 10 00 00',
            'cocoa_butter': '1804 00 00 00',
            'cocoa_cake': '1802 00 00 00',
            'cocoa_powder': '1805 00 00 00',
        }
        if self.product_type and not self.nomenclature_douaniere:
            self.nomenclature_douaniere = nomenclatures.get(self.product_type, '')
    
    @api.onchange('emballage_type', 'product_type')
    def _onchange_emballage(self):
        """Suggérer le type d'emballage selon le produit"""
        if self.product_type and not self.emballage_type:
            emballages = {
                'cocoa_mass': 'cartons',
                'cocoa_butter': 'cartons',
                'cocoa_cake': 'big_bag',
                'cocoa_powder': 'sacs',
            }
            self.emballage_type = emballages.get(self.product_type)
    
    # =========================================================================
    # CONTRAINTES
    # =========================================================================
    
    @api.constrains('pourcentage_avant_vente')
    def _check_pourcentage(self):
        for record in self:
            if not 0 <= record.pourcentage_avant_vente <= 100:
                raise ValidationError(_(
                    "Le pourcentage avant-vente doit être entre 0 et 100."
                ))
    
    @api.constrains('tonnage', 'confirmation_vente_id')
    def _check_tonnage_cv(self):
        """Vérifier que le tonnage ne dépasse pas celui disponible sur la CV"""
        for record in self:
            if record.confirmation_vente_id and record.tonnage:
                # Calculer le tonnage déjà utilisé par d'autres formules de cette CV
                other_formules = self.search([
                    ('confirmation_vente_id', '=', record.confirmation_vente_id.id),
                    ('id', '!=', record.id),
                    ('state', '!=', 'cancelled')
                ])
                tonnage_other = sum(other_formules.mapped('tonnage'))
                tonnage_total = tonnage_other + record.tonnage
                
                if tonnage_total > record.confirmation_vente_id.tonnage_autorise:
                    raise ValidationError(_(
                        "Le tonnage total des formules (%.2f T) dépasse "
                        "le tonnage autorisé par la CV (%.2f T).",
                        tonnage_total, 
                        record.confirmation_vente_id.tonnage_autorise
                    ))
    
    @api.constrains('date_emission', 'date_validite')
    def _check_dates(self):
        """Vérifier la cohérence des dates"""
        for record in self:
            if record.date_emission and record.date_validite:
                if record.date_validite < record.date_emission:
                    raise ValidationError(_(
                        "La date de validité ne peut pas être antérieure à la date d'émission."
                    ))
    
    @api.constrains('date_fo1', 'date_emission')
    def _check_date_fo1(self):
        """La date FO1 ne peut pas être dans le futur"""
        for record in self:
            if record.date_fo1 and record.date_fo1 > date.today():
                raise ValidationError(_(
                    "La date FO1 ne peut pas être dans le futur."
                ))
    
    @api.constrains('periode_embarquement_debut', 'periode_embarquement_fin')
    def _check_periode_embarquement(self):
        """Vérifier que la période d'embarquement est cohérente"""
        for record in self:
            if record.periode_embarquement_debut and record.periode_embarquement_fin:
                if record.periode_embarquement_fin < record.periode_embarquement_debut:
                    raise ValidationError(_(
                        "Le mois de fin de période d'embarquement ne peut pas être "
                        "antérieur au mois de début."
                    ))
    
    @api.constrains('tonnage_brut', 'tonnage_kg')
    def _check_tonnage_brut(self):
        """Le tonnage brut doit être >= tonnage net"""
        for record in self:
            if record.tonnage_brut and record.tonnage_kg:
                if record.tonnage_brut < record.tonnage_kg:
                    raise ValidationError(_(
                        "Le tonnage brut (%.0f kg) ne peut pas être inférieur "
                        "au tonnage net (%.0f kg).",
                        record.tonnage_brut, record.tonnage_kg
                    ))
    
    @api.constrains('confirmation_vente_id', 'product_type')
    def _check_product_type_cv(self):
        """Vérifier que le type de produit est compatible avec la CV"""
        for record in self:
            if record.confirmation_vente_id and record.product_type:
                cv_type = record.confirmation_vente_id.product_type
                if cv_type and cv_type != 'all' and cv_type != record.product_type:
                    raise ValidationError(_(
                        "Le type de produit '%s' n'est pas autorisé par la CV. "
                        "Type autorisé: %s",
                        dict(record._fields['product_type'].selection).get(record.product_type),
                        dict(record.confirmation_vente_id._fields['product_type'].selection).get(cv_type)
                    ))
    
    # =========================================================================
    # MÉTHODES CRUD
    # =========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'potting.formule'
                ) or _('Nouveau')
        return super().create(vals_list)
    
    def unlink(self):
        for record in self:
            if record.state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "Vous ne pouvez supprimer que les formules en brouillon ou annulées."
                ))
            if record.transit_order_id:
                raise UserError(_(
                    "Cette formule est liée à un OT. Détachez d'abord l'OT."
                ))
        return super().unlink()
    
    def write(self, vals):
        result = super().write(vals)
        # Mettre à jour l'état en fonction des paiements
        if 'avant_vente_paye' in vals or 'apres_vente_paye' in vals:
            for record in self:
                record._update_payment_state()
        return result
    
    # =========================================================================
    # MÉTHODES D'ACTION
    # =========================================================================
    
    def action_validate(self):
        """Valider la formule"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Seules les formules en brouillon peuvent être validées."))
            if not record.taxe_ids:
                raise UserError(_("Veuillez ajouter au moins une ligne de taxe/redevance."))
            record.state = 'validated'
    
    def action_cancel(self):
        """Annuler la formule"""
        for record in self:
            if record.transit_order_id:
                raise UserError(_(
                    "Impossible d'annuler cette formule. "
                    "Elle est liée à l'OT %s.", record.transit_order_id.name
                ))
            if record.avant_vente_paye or record.apres_vente_paye:
                raise UserError(_(
                    "Impossible d'annuler une formule avec des paiements effectués."
                ))
            record.state = 'cancelled'
    
    def action_draft(self):
        """Remettre en brouillon"""
        for record in self:
            if record.state == 'cancelled':
                record.state = 'draft'
    
    def _update_payment_state(self):
        """Met à jour l'état en fonction des paiements.
        
        Logique métier:
        - avant_vente_paye seul = partial_paid
        - avant_vente_paye + apres_vente_paye = paid (complet)
        - Le paiement avant-vente doit TOUJOURS être fait en premier
        - Impossible d'avoir apres_vente_paye sans avant_vente_paye
        """
        for record in self:
            if record.state in ('draft', 'cancelled'):
                continue
            if record.avant_vente_paye and record.apres_vente_paye:
                record.state = 'paid'
            elif record.avant_vente_paye:
                # Seul le paiement avant-vente déclenche l'état partial_paid
                record.state = 'partial_paid'
            else:
                record.state = 'validated'
    
    # =========================================================================
    # MÉTHODES UTILITAIRES
    # =========================================================================
    
    def get_taxes_summary(self):
        """Retourne un résumé des taxes par catégorie"""
        self.ensure_one()
        summary = {
            'redevances': {'total': 0, 'items': []},
            'taxes': {'total': 0, 'items': []},
            'soutien': {'total': 0, 'items': []},
        }
        for taxe in self.taxe_ids:
            cat = taxe.categorie or 'redevances'
            cat_key = cat + 's' if cat == 'redevance' else ('taxes' if cat == 'taxe' else 'soutien')
            if cat_key in summary:
                summary[cat_key]['total'] += taxe.montant
                summary[cat_key]['items'].append({
                    'name': taxe.name,
                    'code': taxe.code,
                    'montant': taxe.montant,
                    'is_preleve': taxe.is_preleve,
                })
        return summary
    
    def get_formule_display_name(self):
        """Retourne un nom d'affichage complet pour la formule"""
        self.ensure_one()
        parts = [self.name]
        if self.numero_fo1:
            parts.append(f"(FO1: {self.numero_fo1})")
        if self.reference_ccc:
            parts.append(f"[{self.reference_ccc}]")
        return " ".join(parts)
    
    def action_add_standard_taxes(self):
        """Ajouter automatiquement les taxes standards depuis les types prédéfinis"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Les taxes ne peuvent être ajoutées que sur une formule en brouillon."))
        
        # Récupérer tous les types de taxes actifs
        taxe_types = self.env['potting.taxe.type'].search([('active', '=', True)])
        
        if not taxe_types:
            raise UserError(_("Aucun type de taxe prédéfini n'est configuré. "
                            "Veuillez d'abord configurer les types de taxes."))
        
        existing_codes = self.taxe_ids.mapped('code')
        taxes_added = 0
        
        for taxe_type in taxe_types:
            if taxe_type.code not in existing_codes:
                self.env['potting.formule.taxe'].create({
                    'formule_id': self.id,
                    'taxe_type_id': taxe_type.id,
                    'name': taxe_type.name,
                    'code': taxe_type.code,
                    'categorie': taxe_type.categorie,
                    'taux_pourcentage': taxe_type.taux_pourcentage,
                    'taux_par_kg': taxe_type.taux_par_kg,
                    'is_preleve': taxe_type.is_preleve_default,
                    'sequence': taxe_type.sequence,
                })
                taxes_added += 1
        
        if taxes_added:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Taxes ajoutées'),
                    'message': _('%d taxes standards ont été ajoutées.') % taxes_added,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Information'),
                    'message': _('Toutes les taxes standards sont déjà présentes.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
    
    def action_duplicate_formule(self):
        """Dupliquer la formule avec un nouveau numéro"""
        self.ensure_one()
        new_formule = self.copy({
            'state': 'draft',
            'avant_vente_paye': False,
            'apres_vente_paye': False,
            'date_paiement_avant_vente': False,
            'date_paiement_apres_vente': False,
            'payment_request_avant_vente_id': False,
            'payment_request_apres_vente_id': False,
            'transit_order_id': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nouvelle Formule'),
            'res_model': 'potting.formule',
            'res_id': new_formule.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_print_formule(self):
        """Imprimer le rapport de la formule"""
        self.ensure_one()
        return self.env.ref('potting_management.action_report_potting_formule').report_action(self)
    
    # =========================================================================
    # ACTIONS DE PAIEMENT PAR CHÈQUE
    # =========================================================================
    
    def action_open_payment_wizard(self):
        """Ouvrir le wizard de paiement de formule"""
        self.ensure_one()
        
        if self.state not in ('validated', 'partial_paid'):
            raise UserError(_("La formule doit être validée pour créer un paiement."))
        
        # Déterminer le type de paiement par défaut
        if not self.avant_vente_paye:
            default_type = 'avant_vente'
        elif not self.apres_vente_paye:
            default_type = 'apres_vente'
        else:
            raise UserError(_("Cette formule a déjà été entièrement payée."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paiement Formule par Chèque'),
            'res_model': 'potting.formule.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_formule_id': self.id,
                'default_payment_type': default_type,
            },
        }
    
    def action_create_payment_request_avant_vente(self):
        """Créer une demande de paiement pour le versement avant-vente via wizard"""
        self.ensure_one()
        if self.state not in ('validated', 'partial_paid'):
            raise UserError(_("La formule doit être validée pour créer un paiement."))
        if self.avant_vente_paye:
            raise UserError(_("Le paiement avant-vente a déjà été effectué."))
        if self.payment_request_avant_vente_id:
            raise UserError(_(
                "Une demande de paiement existe déjà pour le versement avant-vente."
            ))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paiement Avant-Vente'),
            'res_model': 'potting.formule.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_formule_id': self.id,
                'default_payment_type': 'avant_vente',
            },
        }
    
    def action_create_payment_request_apres_vente(self):
        """Créer une demande de paiement pour le versement après-vente via wizard"""
        self.ensure_one()
        if self.state not in ('validated', 'partial_paid'):
            raise UserError(_("La formule doit être validée pour créer un paiement."))
        if not self.avant_vente_paye:
            raise UserError(_("Le paiement avant-vente doit être effectué en premier."))
        if self.apres_vente_paye:
            raise UserError(_("Le paiement après-vente a déjà été effectué."))
        if self.payment_request_apres_vente_id:
            raise UserError(_(
                "Une demande de paiement existe déjà pour le versement après-vente."
            ))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Paiement Après-Vente'),
            'res_model': 'potting.formule.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_formule_id': self.id,
                'default_payment_type': 'apres_vente',
            },
        }

    def _create_payment_request(self, payment_type, amount, subject):
        """Créer une demande de paiement par chèque"""
        self.ensure_one()
        
        # Rechercher le partenaire CCC (Conseil Café-Cacao)
        ccc_partner = self.env['res.partner'].search([
            ('name', 'ilike', 'Conseil Café-Cacao')
        ], limit=1)
        if not ccc_partner:
            ccc_partner = self.env['res.partner'].search([
                ('name', 'ilike', 'CCC')
            ], limit=1)
        if not ccc_partner:
            raise UserError(_(
                "Partenaire 'Conseil Café-Cacao' non trouvé. "
                "Veuillez créer ce partenaire dans le système."
            ))
        
        # Créer la demande de paiement
        payment_request = self.env['payment.request'].create({
            'subject': subject,
            'auto_subject': False,
            'urgency_level': 'normal',
            'justification': _(
                "<p>Reversement de redevances pour la Formule <strong>%s</strong></p>"
                "<ul>"
                "<li>CV: %s</li>"
                "<li>Tonnage: %.2f T</li>"
                "<li>Type de paiement: %s</li>"
                "</ul>"
            ) % (
                self.name,
                self.confirmation_vente_id.name,
                self.tonnage,
                _("Avant-vente") if payment_type == 'avant_vente' else _("Après-vente")
            ),
        })
        
        # Créer la ligne de chèque
        check_vals = {
            'payment_request_id': payment_request.id,
            'partner_id': ccc_partner.id,
            'beneficiary': ccc_partner.name,
            'amount': amount,
            'memo': _("FO %s - %s") % (
                self.name,
                _("Avant-vente") if payment_type == 'avant_vente' else _("Après-vente")
            ),
        }
        
        # Ajouter les lignes de taxes non prélevées comme chèques séparés si avant-vente
        if payment_type == 'avant_vente':
            taxes_a_payer = self.taxe_ids.filtered(lambda t: not t.is_preleve)
            if taxes_a_payer:
                # Un seul chèque pour le reversement principal
                check_vals['amount'] = self.montant_avant_vente
                self.env['payment.request.check'].create(check_vals)
                
                # Chèques séparés pour chaque taxe à payer
                for taxe in taxes_a_payer:
                    self.env['payment.request.check'].create({
                        'payment_request_id': payment_request.id,
                        'partner_id': ccc_partner.id,
                        'beneficiary': ccc_partner.name,
                        'amount': taxe.montant,
                        'memo': _("FO %s - Taxe: %s") % (self.name, taxe.name),
                    })
            else:
                self.env['payment.request.check'].create(check_vals)
        else:
            self.env['payment.request.check'].create(check_vals)
        
        return payment_request
    
    def action_mark_avant_vente_paid(self):
        """Marquer le paiement avant-vente comme effectué et synchroniser avec l'OT"""
        for record in self:
            record.avant_vente_paye = True
            record.date_paiement_avant_vente = date.today()
            record._update_payment_state()
            
            # Synchroniser avec l'OT lié
            if record.transit_order_id:
                record.transit_order_id.write({
                    'taxes_paid': True,
                    'taxes_payment_date': date.today(),
                })
                # Mettre à jour l'état de l'OT si nécessaire
                if record.transit_order_id.state in ('draft', 'formule_linked'):
                    record.transit_order_id.state = 'taxes_paid'
                record.transit_order_id.message_post(
                    body=_("Taxes payées via la Formule %s") % record.name,
                    subject=_("Taxes payées"),
                    subtype_xmlid='mail.mt_comment'
                )
    
    def action_mark_apres_vente_paid(self):
        """Marquer le paiement après-vente comme effectué.
        
        Le paiement avant-vente doit OBLIGATOIREMENT être fait en premier.
        """
        for record in self:
            if not record.avant_vente_paye:
                raise UserError(_(
                    "Impossible de marquer le paiement après-vente comme effectué.\n"
                    "Le paiement avant-vente de la Formule %s doit être fait en premier."
                ) % record.name)
            record.apres_vente_paye = True
            record.date_paiement_apres_vente = date.today()
            record._update_payment_state()
    
    # =========================================================================
    # ACTIONS DE VUE
    # =========================================================================
    
    def action_view_transit_order(self):
        """Afficher l'OT lié"""
        self.ensure_one()
        if not self.transit_order_id:
            raise UserError(_("Aucun Ordre de Transit lié à cette formule."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordre de Transit'),
            'res_model': 'potting.transit.order',
            'res_id': self.transit_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_payment_requests(self):
        """Voir les demandes de paiement liées"""
        self.ensure_one()
        payment_ids = []
        if self.payment_request_avant_vente_id:
            payment_ids.append(self.payment_request_avant_vente_id.id)
        if self.payment_request_apres_vente_id:
            payment_ids.append(self.payment_request_apres_vente_id.id)
        
        if not payment_ids:
            raise UserError(_("Aucune demande de paiement liée à cette formule."))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Demandes de Paiement'),
            'res_model': 'payment.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payment_ids)],
            'target': 'current',
        }


class PottingFormuleTaxe(models.Model):
    """Ligne de taxe/redevance sur une Formule
    
    Représente les différentes taxes et redevances prélevées ou à payer
    sur une formule. Certaines taxes sont prélevées directement (is_preleve=True)
    et leur montant est affiché, d'autres doivent être payées par chèque.
    
    Types de taxes selon le document CCC:
    - Redevances: Conseil Café-Cacao, Investissement agricole, FIMR, Sacherie
    - Taxes: Taxe d'enregistrement, DIUS
    - Soutien/Reversement: Montant reversé aux producteurs
    """
    _name = 'potting.formule.taxe'
    _description = 'Taxe/Redevance sur Formule'
    _order = 'sequence, id'

    formule_id = fields.Many2one(
        'potting.formule',
        string="Formule",
        required=True,
        ondelete='cascade',
        index=True
    )
    
    taxe_type_id = fields.Many2one(
        'potting.taxe.type',
        string="Type de taxe",
        ondelete='restrict',
        help="Type de taxe prédéfini (optionnel)"
    )
    
    sequence = fields.Integer(
        string="Séquence",
        default=10
    )
    
    categorie = fields.Selection([
        ('redevance', 'Redevance'),
        ('taxe', 'Taxe'),
        ('soutien', 'Soutien/Reversement'),
    ], string="Catégorie",
       default='redevance',
       required=True,
       help="Catégorie de la taxe/redevance")
    
    name = fields.Char(
        string="Nom de la taxe",
        required=True,
        help="Nom de la taxe ou redevance (ex: Conseil du Café-Cacao, DIUS...)"
    )
    
    code = fields.Char(
        string="Code",
        help="Code de la taxe (ex: CCC, FIMR, DIUS...)"
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        related='formule_id.currency_id',
        store=True
    )
    
    # Taux par pourcentage (pour Taxe d'enregistrement 5%, DIUS 14.6%)
    taux_pourcentage = fields.Float(
        string="Taux (%)",
        digits=(5, 3),
        help="Taux de la taxe en pourcentage (ex: 5% pour taxe d'enregistrement)"
    )
    
    # Taux par kg (pour redevances CCC: 1.245 FCFA/kg, etc.)
    taux_par_kg = fields.Float(
        string="Taux (FCFA/Kg)",
        digits=(10, 3),
        help="Taux par kilogramme (ex: 1.245 FCFA/kg pour CCC)"
    )
    
    # Ancien champ conservé pour compatibilité
    taux = fields.Float(
        string="Taux (ancien)",
        digits=(5, 2),
        help="[Déprécié] Utiliser taux_pourcentage ou taux_par_kg"
    )
    
    montant_unitaire = fields.Monetary(
        string="Montant/Tonne",
        currency_field='currency_id',
        help="Montant fixe par tonne (alternative au taux)"
    )
    
    montant_fixe = fields.Monetary(
        string="Montant fixe",
        currency_field='currency_id',
        help="Montant fixe total (pour soutien/reversement)"
    )
    
    montant = fields.Monetary(
        string="Montant calculé",
        currency_field='currency_id',
        compute='_compute_montant',
        store=True,
        help="Montant total de la taxe (calculé automatiquement)"
    )
    
    is_preleve = fields.Boolean(
        string="Prélevé",
        default=False,
        help="Indique si cette taxe est prélevée directement sur la formule"
    )
    
    date_prelevement = fields.Date(
        string="Date prélèvement",
        help="Date du prélèvement de la taxe"
    )
    
    # Informations de paiement (chèques)
    numero_cheque = fields.Char(
        string="N° Chèque",
        help="Numéro du chèque de paiement"
    )
    
    date_paiement = fields.Date(
        string="Date paiement",
        help="Date du paiement par chèque"
    )
    
    banque_id = fields.Many2one(
        'res.bank',
        string="Banque",
        help="Banque émettrice du chèque"
    )
    
    banque_name = fields.Char(
        string="Nom banque",
        help="Nom de la banque (si non référencée)"
    )
    
    note = fields.Char(
        string="Note",
        help="Information complémentaire"
    )
    
    @api.depends('formule_id.montant_brut', 'formule_id.tonnage', 'formule_id.tonnage_kg',
                 'taux_pourcentage', 'taux_par_kg', 'taux', 'montant_unitaire', 'montant_fixe')
    def _compute_montant(self):
        """Calculer le montant de la taxe selon le type de taux utilisé"""
        for record in self:
            montant = 0
            tonnage_kg = record.formule_id.tonnage_kg or (record.formule_id.tonnage * 1000)
            
            if record.montant_fixe:
                # Montant fixe total (pour soutien/reversement)
                montant = record.montant_fixe
            elif record.taux_pourcentage:
                # Calcul par pourcentage (ex: 5% taxe d'enregistrement)
                montant = (record.formule_id.montant_brut or 0) * (record.taux_pourcentage / 100)
            elif record.taux_par_kg:
                # Calcul par kg (ex: 1.245 FCFA/kg pour CCC)
                montant = record.taux_par_kg * tonnage_kg
            elif record.montant_unitaire:
                # Montant fixe par tonne
                montant = record.montant_unitaire * (record.formule_id.tonnage or 0)
            elif record.taux:
                # Ancien calcul (compatibilité)
                montant = (record.formule_id.montant_brut or 0) * (record.taux / 100)
            
            record.montant = montant
    
    @api.onchange('taxe_type_id')
    def _onchange_taxe_type(self):
        """Remplir automatiquement les champs depuis le type de taxe sélectionné"""
        if self.taxe_type_id:
            self.name = self.taxe_type_id.name
            self.code = self.taxe_type_id.code
            self.categorie = self.taxe_type_id.categorie
            self.taux_pourcentage = self.taxe_type_id.taux_pourcentage
            self.taux_par_kg = self.taxe_type_id.taux_par_kg
            self.is_preleve = self.taxe_type_id.is_preleve_default
    
    @api.onchange('is_preleve')
    def _onchange_is_preleve(self):
        if self.is_preleve and not self.date_prelevement:
            self.date_prelevement = date.today()


class PottingTaxeType(models.Model):
    """Types de taxes prédéfinies selon la réglementation CCC
    
    Permet de définir les taxes standards avec leurs taux par défaut
    pour faciliter la saisie des formules.
    """
    _name = 'potting.taxe.type'
    _description = 'Type de Taxe/Redevance CCC'
    _order = 'sequence, name'
    
    name = fields.Char(
        string="Nom",
        required=True,
        help="Nom de la taxe/redevance"
    )
    
    code = fields.Char(
        string="Code",
        required=True,
        help="Code court de la taxe"
    )
    
    sequence = fields.Integer(
        string="Séquence",
        default=10
    )
    
    categorie = fields.Selection([
        ('redevance', 'Redevance'),
        ('taxe', 'Taxe'),
        ('soutien', 'Soutien/Reversement'),
    ], string="Catégorie",
       default='redevance',
       required=True)
    
    taux_pourcentage = fields.Float(
        string="Taux (%)",
        digits=(5, 3),
        help="Taux par défaut en pourcentage"
    )
    
    taux_par_kg = fields.Float(
        string="Taux (FCFA/Kg)",
        digits=(10, 3),
        help="Taux par défaut en FCFA/kg"
    )
    
    is_preleve_default = fields.Boolean(
        string="Prélevé par défaut",
        default=False,
        help="Si coché, cette taxe sera marquée comme prélevée par défaut"
    )
    
    description = fields.Text(
        string="Description",
        help="Description détaillée de la taxe"
    )
    
    active = fields.Boolean(
        string="Actif",
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string="Société",
        default=lambda self: self.env.company
    )
    
    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 
         'Le code de la taxe doit être unique par société!')
    ]
