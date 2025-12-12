# -*- coding: utf-8 -*-
{
    'name': 'Gestion des Empotages',
    'version': '17.0.1.0.2',
    'category': 'Inventory/Logistics',
    'summary': 'Gestion des empotages de produits semi-finis du cacao',
    'description': """
        Module de gestion des empotages pour les produits semi-finis du cacao :
        - Masse de cacao
        - Beurre de cacao
        - Cake/Tourteau de cacao
        - Poudre de cacao
        
        Fonctionnalités :
        - Gestion des commandes clients
        - Gestion des Ordres de Transit (OT)
        - Génération automatique des lots selon le tonnage
        - Suivi des productions et empotages
        - Tableaux de bord dédiés (Shipping et Agent Exportation)
        - Rapports et envoi par email
    """,
    'author': 'ICP',
    'website': 'https://www.icp.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'product',
        'web_responsive',
    ],
    'data': [
        # Security
        'security/potting_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'data/potting_certification_data.xml',
        # Wizards (must be before menus that reference them)
        'wizards/potting_send_report_wizard_views.xml',
        'wizards/potting_create_ot_wizard_views.xml',
        'wizards/potting_generate_lots_wizard_views.xml',
        # Views
        'views/res_config_settings_views.xml',
        'views/potting_certification_views.xml',
        'views/potting_customer_order_views.xml',
        'views/potting_transit_order_views.xml',
        'views/potting_lot_views.xml',
        'views/potting_container_views.xml',
        'views/potting_consignee_views.xml',
        'views/potting_menu_views.xml',
        # Reports (must be before mail templates)
        'reports/potting_report_templates.xml',
        'reports/potting_report_actions.xml',
        # Mail Templates (after reports)
        'data/mail_template_data.xml',
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