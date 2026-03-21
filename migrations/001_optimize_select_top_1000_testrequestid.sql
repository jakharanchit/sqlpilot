-- ============================================================
-- Migration: 001
-- Description: optimize: SELECT TOP (1000) [testRequestID]
-- Date: 2026-03-21 09:25:35
-- Client: client_example1
-- Tables affected: Labels, Parts, TestRequests, Tests, ItemLabels
-- Reason: Here's a step-by-step explanation of the issues affecting the query performance:
-- -- Benchmark: not measured
-- ============================================================

-- Source query that triggered this migration:
--   SELECT TOP (1000) [testRequestID]
--   >>       ,[testRequestDateCreated]
--   >>       ,[testRequestNumber]
--   >>       ,[testSpecID]
--   >>       ,[testSpecDateCreated]
--   >>       ,[testSpecName]
--   >>       ,[testSpecTypeId]
--   >>       ,[testSpecType]
--   >>       ,[partID]
--   >>       ,[partName]
--   >>       ,[partTypeID]
--   >>       ,[partTypeName]
--   >>       ,[manufacturerID]
--   >>       ,[manufacturerName]
--   >>       ,[clientID]
--   >>       ,[clientName]
--   >>       ,[userIdCreated]
--   >>       ,[userFullName]
--   >>       ,[parts]
--   >>       ,[archived]
--   >>       ,[labels]
--   >>       ,[labelIDs]
--   >>       ,[labelTypeID]
--   >>       ,[labelID]
--   >>   FROM [VEXA].[dbo].[View_LabeledTestRequestsAndLabelIDs]
--   >>   WHERE labels is not null

-- ============================================================
-- ROLLBACK — run this section to undo this migration
-- ============================================================

DROP INDEX IF EXISTS idx_Labels_labels ON Labels;


-- ============================================================
-- APPLY — run this section to apply this migration
-- ============================================================

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


-- ============================================================
-- VERIFY — run after applying to confirm it worked
-- ============================================================

-- Check the object exists
-- (adjust object name and type as appropriate)
SELECT
    name,
    type_desc,
    create_date
FROM sys.objects
WHERE name IN ('Labels', 'Parts', 'TestRequests', 'Tests', 'ItemLabels')
ORDER BY create_date DESC;

-- Check execution plan no longer shows Table Scan
-- (paste your original query here and check the plan tab in SSMS)

-- ============================================================
-- Migration 001 end
-- Generated by SQL Optimization Agent · 2026-03-21
-- ============================================================
