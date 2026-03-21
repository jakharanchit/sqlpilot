-- ============================================================
-- ROLLBACK.SQL — UNDO ALL CHANGES
-- Client:    client_example
-- Database:  VEXA
-- Generated: 2026-03-21 10:28:39
-- ============================================================

-- ⚠  THIS UNDOES ALL CHANGES FROM THIS DEPLOYMENT PACKAGE
-- ⚠  Run this ONLY if something went wrong after deploy.sql

-- SAFETY CHECK
IF DB_NAME() != 'VEXA'
BEGIN
    RAISERROR('Wrong database! Expected VEXA, got %s', 20, 1, DB_NAME()) WITH LOG;
    RETURN;
END

PRINT 'Starting rollback on: ' + DB_NAME();
PRINT '==================================================';

-- Rollback migration 002: optimize: SELECT TOP (1000) [testRequestID],[testRequestDate
PRINT 'Rolling back migration 002...';

DROP INDEX IF EXISTS IX_ItemLabels_itemID_labelTypeID ON ItemLabels;
PRINT 'Migration 002 rolled back.';

-- Rollback migration 001: optimize: SELECT TOP (1000) [testRequestID]
PRINT 'Rolling back migration 001...';

DROP INDEX IF EXISTS idx_Labels_labels ON Labels;
PRINT 'Migration 001 rolled back.';

-- ============================================================
PRINT 'Rollback complete. Database restored to previous state.';
-- ============================================================