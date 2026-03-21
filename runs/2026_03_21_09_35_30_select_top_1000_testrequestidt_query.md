# Run Log — Query Optimization
**Date:** 2026-03-21 09:35:30
**Label:** (none)
**Run type:** query

---

## Original Query
```sql
SELECT TOP (1000) [testRequestID],[testRequestDateCreated],[testRequestNumber],[testSpecID],[testSpecDateCreated],[testSpecName],[testSpecTypeId],[testSpecType],[partID],[partName],[partTypeID],[partTypeName],[manufacturerID],[manufacturerName],[clientID],[clientName],[userIdCreated],[userFullName],[parts],[archived],[labels],[labelIDs],[labelTypeID],[labelID] FROM [VEXA].[dbo].[View_LabeledTestRequestsAndLabelIDs] WHERE labels IS NOT NULL
```

## Schema Context
### Table: `Labels`
Estimated rows: ~9

| Column | Type | PK | Nullable |
|--------|------|----|---------|
| id | int | ✓ | NOT NULL |
| name | nvarchar |  | NULL |
| parentID | int |  | NULL |

**Existing indexes:**
- `PK_Labels` (CLUSTERED) — keys: `id`

### Table: `Parts`
Estimated rows: ~872

| Column | Type | PK | Nullable |
|--------|------|----|---------|
| id | int | ✓ | NOT NULL |
| name | nvarchar |  | NULL |
| manufacturerID | int |  | NULL |
| partTypeID | int |  | NULL |
| dateCreated | datetime |  | NULL |

**Existing indexes:**
- `PK_Products` (CLUSTERED) — keys: `id`

### Table: `TestRequests`
Estimated rows: ~1666

| Column | Type | PK | Nullable |
|--------|------|----|---------|
| id | int | ✓ | NOT NULL |
| dateCreated | datetime |  | NULL |
| testRequestNumber | nvarchar |  | NULL |
| clientID | int |  | NULL |
| testSpecID | int |  | NULL |
| partID | int |  | NULL |
| userIdCreated | int |  | NULL |
| userIdModified | int |  | NULL |
| dateModified | datetime |  | NULL |
| parts | nvarchar |  | NULL |
| archived | bit |  | NULL |

**Existing indexes:**
- `PK_TestRequests` (CLUSTERED) — keys: `id`

### Table: `Tests`
Estimated rows: ~42372

| Column | Type | PK | Nullable |
|--------|------|----|---------|
| id | int | ✓ | NOT NULL |
| date | datetime |  | NULL |
| userID | int |  | NULL |
| dataPath | nvarchar |  | NULL |
| partSerialNumber | nvarchar |  | NULL |
| testRequestID | int |  | NULL |
| testMachineID | int |  | NULL |
| completed | bit |  | NULL |
| vexaID | nvarchar |  | NULL |
| archived | bit |  | NULL |

**Existing indexes:**
- `PK_Tests` (CLUSTERED) — keys: `id`

### Table: `ItemLabels`
Estimated rows: ~175

| Column | Type | PK | Nullable |
|--------|------|----|---------|
| id | int | ✓ | NOT NULL |
| labelTypeID | int |  | NULL |
| itemID | int |  | NULL |
| labelID | int |  | NULL |

**Existing indexes:**
- `PK_ProjectLabels` (CLUSTERED) — keys: `id`

---

## Execution Plan
**Plan type:** actual
**Execution time:** 19732.81ms
**Rows returned:** 175

**Flagged operators:**
- [MEDIUM] `Sort` (est: 175) — Explicit sort — index could eliminate this
- [MEDIUM] `Hash Match` (est: 175) — Large data join — index on join columns may help
- [HIGH] `Clustered Index Scan` (est: 9) — Full index scan — filter may not be sargable
- [HIGH] `Clustered Index Scan` (est: 175) — Full index scan — filter may not be sargable
- [MEDIUM] `Sort` (est: 175) — Explicit sort — index could eliminate this
- [MEDIUM] `Hash Match` (est: 175) — Large data join — index on join columns may help
- [HIGH] `Clustered Index Scan` (est: 9) — Full index scan — filter may not be sargable
- [HIGH] `Clustered Index Scan` (est: 175) — Full index scan — filter may not be sargable
- [HIGH] `Clustered Index Scan` (est: 5) — Full index scan — filter may not be sargable
- [MEDIUM] `Sort` (est: 175) — Explicit sort — index could eliminate this
- [MEDIUM] `Hash Match` (est: 175) — Large data join — index on join columns may help
- [HIGH] `Clustered Index Scan` (est: 9) — Full index scan — filter may not be sargable
- [HIGH] `Clustered Index Scan` (est: 175) — Full index scan — filter may not be sargable
- [MEDIUM] `Sort` (est: 175) — Explicit sort — index could eliminate this
- [MEDIUM] `Hash Match` (est: 175) — Large data join — index on join columns may help
- [HIGH] `Clustered Index Scan` (est: 9) — Full index scan — filter may not be sargable
- [HIGH] `Clustered Index Scan` (est: 175) — Full index scan — filter may not be sargable
- [HIGH] `Clustered Index Scan` (est: 175) — Full index scan — filter may not be sargable

---

## AI Diagnosis (DeepSeek-R1)

Here's a step-by-step explanation of the performance issues in the provided SQL query and their potential fixes:

---

### **1. Non-sargable Predicate on Clustered Index Scan (Labels Table)**

- **Problem**: The execution plan shows a full scan on the Labels table with an estimated 9 rows. A "WHERE labels IS NOT NULL" clause may not be sargable, preventing efficient index usage.
  
- **Performance Impact**: Full scans on small tables are inefficient because every row must be read, causing significant latency.

- **Fix**: Ensure the predicate is written to allow for sargability. For example, avoid functions or operators that prevent index usage and consider adding an index if necessary.

---

### **2. Non-sargable Predicate on Clustered Index Scan (ItemLabels Table)**

- **Problem**: Another full scan occurs on ItemLabels (~175 rows), likely due to a non-sargable condition in the query.

- **Performance Impact**: Similar to the Labels table, this leads to unnecessary row reads and increased execution time.

- **Fix**: Modify the WHERE clause to be sargable and consider adding an index if not already present.

---

### **3. Sort Operators Causing Overhead**

- **Problem**: Multiple explicit sort operations are identified in the execution plan.

- **Performance Impact**: Sorting large datasets is resource-intensive, leading to increased CPU usage and longer query times.

- **Fix**: Use covering indexes or adjust join order to avoid sorting by ensuring that joins use indexed columns.

---

### **4. Hash Match Operations Leading to High Costs**

- **Problem**: The execution plan shows multiple hash matches with high costs.

- **Performance Impact**: Hash joins are expensive because they require building hash tables, especially on large datasets.

- **Fix**: Optimize join operations by adding indexes on the joining columns or restructuring the query to use more efficient join types.

---

### **5. Cardinality Estimation Errors Leading to Poor Plan Selection**

- **Problem**: The optimizer may not accurately estimate row counts, leading to suboptimal execution plans.

- **Performance Impact**: Inaccurate estimates can result in choosing a less efficient plan, such as a full scan instead of an index seek.

- **Fix**: Gather accurate statistics on columns and indexes to help the optimizer make better decisions. Consider using query hints if necessary.

---

### **Summary**

The primary issues causing slow performance are non-sargable predicates leading to full scans on small tables and inefficient join operations resulting in costly sorts and hash matches. Addressing these by ensuring sargability, adding appropriate indexes, and optimizing join strategies can significantly improve query performance.

---

## Optimized Query (Qwen2.5-Coder)
```sql
SELECT TOP (1000) 
    tr.testRequestID,
    tr.dateCreated AS testRequestDateCreated,
    tr.testRequestNumber,
    tr.testSpecID,
    ts.date AS testSpecDateCreated,  -- Assuming testSpecDateCreated is from Tests table
    ts.name AS testSpecName,        -- Assuming testSpecName is from Tests table
    p.partTypeID,                  -- Assuming partTypeID is from Parts table
    l.name AS partTypeName,         -- Assuming partTypeName is from Labels table
    p.manufacturerID,
    m.name AS manufacturerName,     -- Assuming manufacturerName is from Manufacturers table (not provided in schema)
    tr.clientID,
    c.name AS clientName,           -- Assuming clientName is from Clients table (not provided in schema)
    tr.userIdCreated,
    u.fullName AS userFullName,     -- Assuming userFullName is from Users table (not provided in schema)
    tr.parts,
    tr.archived,
    il.labels,
    il.labelIDs,
    il.labelTypeID,
    il.labelID
FROM 
    TestRequests tr
JOIN 
    ItemLabels il ON tr.id = il.itemID
LEFT JOIN 
    Parts p ON tr.partID = p.id
LEFT JOIN 
    Labels l ON p.partTypeID = l.id
LEFT JOIN 
    Tests ts ON tr.testRequestID = ts.testRequestID
LEFT JOIN 
    Manufacturers m ON p.manufacturerID = m.id  -- Assuming Manufacturers table exists
LEFT JOIN 
    Clients c ON tr.clientID = c.id             -- Assuming Clients table exists
LEFT JOIN 
    Users u ON tr.userIdCreated = u.id           -- Assuming Users table exists
WHERE 
    il.labels IS NOT NULL;
```

## Index Scripts

### Index 1
```sql
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
```

---

## Full AI Response (raw)
<details>
<summary>Click to expand</summary>

### Optimized Query

```sql
SELECT TOP (1000) 
    tr.testRequestID,
    tr.dateCreated AS testRequestDateCreated,
    tr.testRequestNumber,
    tr.testSpecID,
    ts.date AS testSpecDateCreated,  -- Assuming testSpecDateCreated is from Tests table
    ts.name AS testSpecName,        -- Assuming testSpecName is from Tests table
    p.partTypeID,                  -- Assuming partTypeID is from Parts table
    l.name AS partTypeName,         -- Assuming partTypeName is from Labels table
    p.manufacturerID,
    m.name AS manufacturerName,     -- Assuming manufacturerName is from Manufacturers table (not provided in schema)
    tr.clientID,
    c.name AS clientName,           -- Assuming clientName is from Clients table (not provided in schema)
    tr.userIdCreated,
    u.fullName AS userFullName,     -- Assuming userFullName is from Users table (not provided in schema)
    tr.parts,
    tr.archived,
    il.labels,
    il.labelIDs,
    il.labelTypeID,
    il.labelID
FROM 
    TestRequests tr
JOIN 
    ItemLabels il ON tr.id = il.itemID
LEFT JOIN 
    Parts p ON tr.partID = p.id
LEFT JOIN 
    Labels l ON p.partTypeID = l.id
LEFT JOIN 
    Tests ts ON tr.testRequestID = ts.testRequestID
LEFT JOIN 
    Manufacturers m ON p.manufacturerID = m.id  -- Assuming Manufacturers table exists
LEFT JOIN 
    Clients c ON tr.clientID = c.id             -- Assuming Clients table exists
LEFT JOIN 
    Users u ON tr.userIdCreated = u.id           -- Assuming Users table exists
WHERE 
    il.labels IS NOT NULL;
```

### What Changed and Why

1. **Join Order**: Reordered joins to ensure that the most selective tables are joined first.
2. **Sargable Predicate**: The `IS NOT NULL` condition on `il.labels` is already sargable, but it's important to ensure all join conditions are indexed properly.
3. **Added Aliases**: Added table aliases to improve readability and reduce the length of column references in the query.

### CREATE INDEX Scripts

```sql
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
```

### Explanation of Indices

1. **IX_ItemLabels_itemID_labelTypeID**: This index targets the join between `TestRequests` and `ItemLabels` on `itemID`. It also includes `labelTypeID` to cover any subsequent queries that might need these columns.
2. **IX_Parts_partTypeID**: This index targets the join between `Parts` and `Labels` on `partTypeID`.
3. **IX_Labels_id**: This index targets the join between `Parts` and `Labels` on `id`.
4. **IX_Tests_testRequestID**: This index targets the join between `TestRequests` and `Tests` on `testRequestID`.
5. **IX_Manufacturers_id, IX_Clients_id, IX_Users_id**: These indexes are assumed to target joins with `Manufacturers`, `Clients`, and `Users` tables respectively.

These indices should help reduce full table scans and improve the overall performance of the query by allowing more efficient seek operations.

</details>

---
*Generated by SQL Optimization Agent · 2026-03-21 09:35:30*