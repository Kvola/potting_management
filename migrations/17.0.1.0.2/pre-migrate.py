# -*- coding: utf-8 -*-
"""
Migration script to initialize base_name field for existing lots.
This migration runs BEFORE the module update to prepare the data.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Initialize base_name for existing lots that don't have it."""
    if not version:
        return
    
    _logger.info("Starting migration: initializing base_name for existing lots")
    
    # Add base_name column if it doesn't exist
    cr.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'potting_lot' AND column_name = 'base_name'
            ) THEN
                ALTER TABLE potting_lot ADD COLUMN base_name VARCHAR;
            END IF;
        END $$;
    """)
    
    # Initialize base_name with name for all existing lots
    cr.execute("""
        UPDATE potting_lot
        SET base_name = name
        WHERE base_name IS NULL
    """)
    
    _logger.info("Migration complete: base_name initialized for all existing lots")
