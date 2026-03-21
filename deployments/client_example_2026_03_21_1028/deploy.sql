-- ============================================================
-- DEPLOY.SQL
-- Client:    client_example
-- Database:  VEXA
-- Generated: 2026-03-21 10:28:39
-- Migrations: 1, 2
-- ============================================================

-- SAFETY CHECK: confirm you are on the correct database
-- before running this script.
IF DB_NAME() != 'VEXA'
BEGIN
    RAISERROR('Wrong database! Expected VEXA, got %s', 20, 1, DB_NAME()) WITH LOG;
    RETURN;
END

PRINT 'Starting deployment on: ' + DB_NAME();
PRINT 'Time: ' + CONVERT(VARCHAR, GETDATE(), 120);
PRINT '==================================================';

-- ------------------------------------------------------------
-- Migration 001: optimize: SELECT TOP (1000) [testRequestID]
-- Reason:  Here's a step-by-step explanation of the issues affecting the query performance:
-- ------------------------------------------------------------

PRINT 'Applying migration 001: optimize: SELECT TOP (1000) [testRequestID]...';

-- Index on Labels.labels to handle the WHERE clause efficiently
CREATE INDEX idx_Labels_labels ON Labels (labels);

-- Indexes for join columns in TestRequests table
CREATE INDEX idx_TestRequests_partID ON TestRequests (partID);
CREATE INDEX idx_TestRequests_testRequestID ON TestRequests (testRequestID);
CREATE INDEX idx_TestRequests_clientID ON TestRequests (clientID);
CREATE INDEX idx_TestRequests_userIdCreated ON TestRequests (userIdCreated);

-- Indexes for join columns in Parts table
CREATE INDEX idx_Parts_manufacturerID ON Parts (manufacturerID);
CREATE INDEX idx_Parts_partTypeID ON Parts (partTypeID);

-- Indexes for join columns in Tests table
CREATE INDEX idx_Tests_testRequestID ON Tests (testRequestID);

-- Indexes for join columns in Manufacturers and PartTypes tables
CREATE INDEX idx_Manufacturers_id ON Manufacturers (id);
CREATE INDEX idx_PartTypes_id ON PartTypes (id);

-- Indexes for join columns in Clients and Users tables
CREATE INDEX idx_Clients_id ON Clients (id);
CREATE INDEX idx_Users_id ON Users (id);

-- Include additional columns to eliminate Key Lookups
CREATE INDEX idx_ItemLabels_itemID_labelTypeID 
ON ItemLabels (itemID, labelTypeID)
INCLUDE (labelID, labelTypeID);

-- Optimized query (reference — not a schema change):
-- Apply this in your application code, not in SQL Server
-- SELECT TOP (1000) 
--     tr.testRequestID,
--     tr.dateCreated AS testRequestDateCreated,
--     tr.testRequestNumber,
--     tr.testSpecID,
--     ts.dateCreated AS testSpecDateCreated,
--     ts.name AS testSpecName,
--     ts.partTypeID AS testSpecTypeId,
--     ts.type AS testSpecType,
--     p.id AS partID,
--     p.name AS partName,
--     p.partTypeID,
--     pt.name AS partTypeName,
--     p.manufacturerID,
--     m.name AS manufacturerName,
--     tr.clientID,
--     c.name AS clientName,
--     tr.userIdCreated,
--     u.fullName AS userFullName,
--     tr.parts,
--     tr.archived,
--     lbl.labels,
--     lbl.labelIDs,
--     lbl.labelTypeID,
--     lbl.labelID
-- FROM TestRequests tr
-- INNER JOIN Parts p ON tr.partID = p.id
-- INNER JOIN Tests ts ON tr.testRequestID = ts.testRequestID
-- INNER JOIN Manufacturers m ON p.manufacturerID = m.id
-- INNER JOIN PartTypes pt ON p.partTypeID = pt.id
-- INNER JOIN Clients c ON tr.clientID = c.id
-- INNER JOIN Users u ON tr.userIdCreated = u.id
-- LEFT JOIN (
--     SELECT 
--         il.itemID,
--         STRING_AGG(l.name, ',') AS labels,
--         STRING_AGG(il.labelID, ',') AS labelIDs,
--         il.labelTypeID
--     FROM ItemLabels il
--     INNER JOIN Labels l ON il.labelID = l.id
--     GROUP BY il.itemID, il.labelTypeID
-- ) lbl ON tr.id = lbl.itemID
-- WHERE lbl.labels IS NOT NULL;

PRINT 'Migration 001 complete.';

-- ------------------------------------------------------------
-- Migration 002: optimize: SELECT TOP (1000) [testRequestID],[testRequestDate
-- Reason:  Here's a step-by-step explanation of the performance issues in the provided SQL query and their potential fixes:
-- ------------------------------------------------------------

PRINT 'Applying migration 002: optimize: SELECT TOP (1000) [testRequestID],[testRequestDate...';

-- Index for ItemLabels table on itemID and labelTypeID to optimize JOIN
CREATE INDEX IX_ItemLabels_itemID_labelTypeID 
ON ItemLabels (itemID, labelTypeID);

-- Index for Parts table on partTypeID to optimize JOIN
CREATE INDEX IX_Parts_partTypeID 
ON Parts (partTypeID);

-- Index for Labels table on id to optimize JOIN
CREATE INDEX IX_Labels_id 
ON Labels (id);

-- Index for Tests table on testRequestID to optimize JOIN
CREATE INDEX IX_Tests_testRequestID 
ON Tests (testRequestID);

-- Assuming Manufacturers, Clients, and Users tables exist
-- Index for Manufacturers table on id to optimize JOIN
CREATE INDEX IX_Manufacturers_id 
ON Manufacturers (id);

-- Index for Clients table on id to optimize JOIN
CREATE INDEX IX_Clients_id 
ON Clients (id);

-- Index for Users table on id to optimize JOIN
CREATE INDEX IX_Users_id 
ON Users (id);

-- Optimized query (reference — not a schema change):
-- Apply this in your application code, not in SQL Server
-- SELECT TOP (1000) 
--     tr.testRequestID,
--     tr.dateCreated AS testRequestDateCreated,
--     tr.testRequestNumber,
--     tr.testSpecID,
--     ts.date AS testSpecDateCreated,  -- Assuming testSpecDateCreated is from Tests table
--     ts.name AS testSpecName,        -- Assuming testSpecName is from Tests table
--     p.partTypeID,                  -- Assuming partTypeID is from Parts table
--     l.name AS partTypeName,         -- Assuming partTypeName is from Labels table
--     p.manufacturerID,
--     m.name AS manufacturerName,     -- Assuming manufacturerName is from Manufacturers table (not provided in schema)
--     tr.clientID,
--     c.name AS clientName,           -- Assuming clientName is from Clients table (not provided in schema)
--     tr.userIdCreated,
--     u.fullName AS userFullName,     -- Assuming userFullName is from Users table (not provided in schema)
--     tr.parts,
--     tr.archived,
--     il.labels,
--     il.labelIDs,
--     il.labelTypeID,
--     il.labelID
-- FROM 
--     TestRequests tr
-- JOIN 
--     ItemLabels il ON tr.id = il.itemID
-- LEFT JOIN 
--     Parts p ON tr.partID = p.id
-- LEFT JOIN 
--     Labels l ON p.partTypeID = l.id
-- LEFT JOIN 
--     Tests ts ON tr.testRequestID = ts.testRequestID
-- LEFT JOIN 
--     Manufacturers m ON p.manufacturerID = m.id  -- Assuming Manufacturers table exists
-- LEFT JOIN 
--     Clients c ON tr.clientID = c.id             -- Assuming Clients table exists
-- LEFT JOIN 
--     Users u ON tr.userIdCreated = u.id           -- Assuming Users table exists
-- WHERE 
--     il.labels IS NOT NULL;

PRINT 'Migration 002 complete.';

-- ============================================================
PRINT '==================================================';
PRINT 'All migrations applied successfully.';
PRINT 'Run verify.sql or test your application to confirm.';
-- ============================================================