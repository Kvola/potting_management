# -*- coding: utf-8 -*-
"""
Migration script to convert confirmation_vente_id (Many2one) to confirmation_vente_ids (Many2many)
in potting.customer.order model.

This pre-migration script:
1. Creates the Many2many relation table
2. Migrates existing data from the Many2one field to the Many2many relation
"""

import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Pre-migration: Create the M2M relation table and migrate data before ORM loads.
    """
    if not version:
        return
    
    _logger.info("Starting migration from confirmation_vente_id to confirmation_vente_ids")
    
    # Check if the old column exists
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'potting_customer_order' 
        AND column_name = 'confirmation_vente_id'
    """)
    
    if not cr.fetchone():
        _logger.info("Column confirmation_vente_id not found, skipping migration")
        return
    
    # Create the Many2many relation table if it doesn't exist
    cr.execute("""
        CREATE TABLE IF NOT EXISTS potting_customer_order_confirmation_vente_rel (
            customer_order_id INTEGER NOT NULL,
            confirmation_vente_id INTEGER NOT NULL,
            PRIMARY KEY (customer_order_id, confirmation_vente_id),
            FOREIGN KEY (customer_order_id) 
                REFERENCES potting_customer_order(id) ON DELETE CASCADE,
            FOREIGN KEY (confirmation_vente_id) 
                REFERENCES potting_confirmation_vente(id) ON DELETE CASCADE
        )
    """)
    
    # Migrate existing data from Many2one to Many2many
    cr.execute("""
        INSERT INTO potting_customer_order_confirmation_vente_rel 
            (customer_order_id, confirmation_vente_id)
        SELECT id, confirmation_vente_id 
        FROM potting_customer_order 
        WHERE confirmation_vente_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)
    
    cr.execute("SELECT COUNT(*) FROM potting_customer_order_confirmation_vente_rel")
    count = cr.fetchone()[0]
    _logger.info(f"Migrated {count} CV-Order relations to Many2many table")
    
    _logger.info("Pre-migration completed successfully")
