# -*- coding: utf-8 -*-
{
    'name': 'Gestion des Exportations',
    'version': '17.0.1.5.0',
    'category': 'Inventory/Logistics',
    'summary': 'Gestion des exportations de produits semi-finis du cacao',
    'description': """
        Module de gestion des exportations pour les produits semi-finis du cacao :
        - Masse de cacao
        - Beurre de cacao
        - Cake/Tourteau de cacao
        - Poudre de cacao
        
        Fonctionnalités :
        - Gestion des Contrats clients (contrats)
        - Gestion des Ordres de Transit (OT)
        - Génération automatique des OT depuis les Contrats clients
        - Génération automatique des lots selon le tonnage
        - Suivi des productions et exportations
        - Gestion des transitaires et leurs paiements
        - Calcul des droits d'exportation
        - Génération de factures depuis les OT
        - Tableaux de bord dédiés (Shipping et Agent Exportation)
        - Rapports et envoi par email
        
        Réglementation CCC (Conseil Café-Cacao) :
        - Confirmations de Vente (CV) : autorisations d'exportation
          * Support multi-CV par contrat
          * Allocation de tonnage flexible entre CV et contrats
          * Split de CV sur plusieurs contrats
        - Formules (FO1) : fixation des prix et paiements producteurs
          * Référence complète FO1, numéro FO1, grade, nomenclature douanière
          * Transitaire, navire, période d'embarquement, ports
          * Prix de référence et prix effectif (FCFA/kg)
          * Tonnages net, converti, brut
        - Types de taxes CCC prédéfinis :
          * Redevances (taux/kg): CCC, Investissement agricole, FIMR, Sacherie
          * Taxes (%): Taxe d'enregistrement (5%), DIUS (14,6%)
          * Soutien/Reversement producteurs
        - Gestion des paiements par chèques multiples
        - Paiements en 2 temps (avant-vente / après-vente)
        - Intégration avec le module de paiements par chèques
    """,
    'author': 'ICP',
    'website': 'https://www.icp.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'account',
        'web_responsive',
        'payment_request_validation',
    ],
    'data': [
        # Security
        'security/potting_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'data/potting_certification_data.xml',
        'data/potting_cv_fo_data.xml',
        # Wizards (must be before menus that reference them)
        'wizards/potting_send_report_wizard_views.xml',
        'wizards/potting_create_ot_wizard_views.xml',
        'wizards/potting_generate_lots_wizard_views.xml',
        'wizards/potting_generate_ot_from_order_wizard_views.xml',
        'wizards/potting_daily_report_wizard_views.xml',
        'wizards/potting_create_delivery_note_wizard_views.xml',
        'wizards/potting_import_contracts_wizard_views.xml',
        'wizards/potting_add_production_wizard_views.xml',
        'wizards/potting_formule_payment_wizard_views.xml',
        'wizards/potting_forwarding_invoice_reject_wizard_views.xml',
        'wizards/potting_ot_payment_wizards_views.xml',
        'wizards/potting_cv_tonnage_transfer_wizard_views.xml',
        # Views - CV et Formules (avant les contrats qui les référencent)
        'views/potting_confirmation_vente_views.xml',
        'views/potting_confirmation_vente_transfer_views.xml',
        'views/potting_ot_contract_allocation_views.xml',
        'views/potting_formule_views.xml',
        # Views - Autres
        'views/potting_certification_views.xml',
        'views/potting_customer_order_views.xml',
        'views/potting_transit_order_views.xml',
        'views/potting_transit_order_export_views.xml',
        'views/potting_lot_views.xml',
        'views/potting_container_views.xml',
        'views/potting_delivery_note_views.xml',
        'views/potting_consignee_views.xml',
        'views/potting_forwarding_agent_views.xml',
        'views/potting_forwarding_agent_invoice_views.xml',
        'views/potting_campaign_views.xml',
        'views/res_config_settings_views.xml',
        # Menu must be last (references actions from other views)
        'views/potting_menu_views.xml',
        # Reports (must be before mail templates)
        'reports/potting_report_templates.xml',
        'reports/potting_report_actions.xml',
        # Mail Templates (after reports)
        'data/mail_template_data.xml',
        # Cron for alerts
        'data/potting_alert_cron.xml',
    ],
    'demo': [
        'demo/potting_demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'potting_management/static/src/js/**/*',
            'potting_management/static/src/xml/**/*',
            'potting_management/static/src/css/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}