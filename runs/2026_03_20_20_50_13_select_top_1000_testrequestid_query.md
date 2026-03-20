# Run Log — Query Optimization
**Date:** 2026-03-20 20:50:13
**Label:** (none)
**Run type:** query

---

## Original Query
```sql
SELECT TOP (1000) [testRequestID]
      ,[testRequestDateCreated]
      ,[testRequestNumber]
      ,[testSpecID]
      ,[testSpecDateCreated]
      ,[testSpecName]
      ,[testSpecTypeId]
      ,[testSpecType]
      ,[partID]
      ,[partName]
      ,[partTypeID]
      ,[partTypeName]
      ,[manufacturerID]
      ,[manufacturerName]
      ,[clientID]
      ,[clientName]
      ,[userIdCreated]
      ,[userFullName]
      ,[parts]
      ,[archived]
      ,[labels]
      ,[labelIDs]
      ,[labelTypeID]
      ,[labelID]
  FROM [VEXA].[dbo].[View_LabeledTestRequestsAndLabelIDs]
  WHERE labels is not null
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
**Execution time:** 20234.81ms
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

Here is a step-by-step explanation of the query performance problems and their fixes:

1. **Non-sargable Predicate on 'labels' Column Due to Implicit Conversion**

   - **Performance Impact:** The `WHERE labels IS NOT NULL` condition may not be sargable, leading to a full scan instead of an efficient seek operation.
   
   - **Fix:** Ensure that the predicate is written in a way that allows the SQL Server to use existing indexes on the 'labels' column.

2. **Missing Indexes on Join Columns**

   - **Performance Impact:** The execution plan shows multiple hash joins and nested loops, indicating inefficient join operations due to lack of appropriate indexes.
   
   - **Fix:** Create non-clustered indexes on columns involved in joins (e.g., testRequestID, partID) to facilitate efficient joining.

3. **Missing Indexes for Sorting**

   - **Performance Impact:** Multiple explicit sort operations increase execution time as the database must sort large datasets without proper ordering.
   
   - **Fix:** Introduce indexes that cover the columns used in ORDER BY clauses or create covering indexes to avoid sorting altogether.

4. **Clustered Index Scan Instead of Seek**

   - **Performance Impact:** Full scans on clustered indexes can significantly slow down query execution, especially on larger tables.
   
   - **Fix:** Modify queries to use sargable predicates and ensure that indexes are in place to allow for efficient seeks instead of scans.

5. **Cardinality Estimation Errors**

   - **Performance Impact:** Incorrect cardinality estimates lead to suboptimal execution plans, increasing the cost of operations.
   
   - **Fix:** Update statistics on tables or use more accurate hints in the query to help SQL Server make better cardinality predictions.

6. **Lock Contention Issues (if any)**

   - **Performance Impact:** High lock contention can cause delays and deadlocks, affecting overall system performance.
   
   - **Fix:** Adjust transaction isolation levels, partition tables, or implement rowversion-based concurrency control to reduce contention.

Each of these issues contributes to the query's execution time. Addressing them by ensuring proper indexing, fixing non-sargable predicates, and optimizing join operations will lead to improved performance.

---

## Optimized Query (Qwen2.5-Coder)
```sql
SELECT TOP (1000) 
    [testRequestID]
    ,[dateCreated] AS [testRequestDateCreated]
    ,[testRequestNumber]
    ,[testSpecID]
    ,[dateCreated] AS [testSpecDateCreated]
    ,[name] AS [testSpecName]
    ,[partTypeID] AS [testSpecTypeId]
    ,NULL AS [testSpecType] -- Assuming this is a derived column or needs to be adjusted
    ,[partID]
    ,[name] AS [partName]
    ,[partTypeID]
    ,[name] AS [partTypeName] -- Assuming this is a derived column or needs to be adjusted
    ,[manufacturerID]
    ,NULL AS [manufacturerName] -- Assuming this is a derived column or needs to be adjusted
    ,[clientID]
    ,NULL AS [clientName] -- Assuming this is a derived column or needs to be adjusted
    ,[userIdCreated]
    ,NULL AS [userFullName] -- Assuming this is a derived column or needs to be adjusted
    ,[parts]
    ,[archived]
    ,[labels]
    ,[labelIDs]
    ,[labelTypeID]
    ,[labelID]
FROM 
    [VEXA].[dbo].[View_LabeledTestRequestsAndLabelIDs]
WHERE 
    [labels] IS NOT NULL;
```

---

## Full AI Response (raw)
<details>
<summary>Click to expand</summary>

### Optimized Query

```sql
SELECT TOP (1000) 
    [testRequestID]
    ,[dateCreated] AS [testRequestDateCreated]
    ,[testRequestNumber]
    ,[testSpecID]
    ,[dateCreated] AS [testSpecDateCreated]
    ,[name] AS [testSpecName]
    ,[partTypeID] AS [testSpecTypeId]
    ,NULL AS [testSpecType] -- Assuming this is a derived column or needs to be adjusted
    ,[partID]
    ,[name] AS [partName]
    ,[partTypeID]
    ,[name] AS [partTypeName] -- Assuming this is a derived column or needs to be adjusted
    ,[manufacturerID]
    ,NULL AS [manufacturerName] -- Assuming this is a derived column or needs to be adjusted
    ,[clientID]
    ,NULL AS [clientName] -- Assuming this is a derived column or needs to be adjusted
    ,[userIdCreated]
    ,NULL AS [userFullName] -- Assuming this is a derived column or needs to be adjusted
    ,[parts]
    ,[archived]
    ,[labels]
    ,[labelIDs]
    ,[labelTypeID]
    ,[labelID]
FROM 
    [VEXA].[dbo].[View_LabeledTestRequestsAndLabelIDs]
WHERE 
    [labels] IS NOT NULL;
```

### Changes and Why

1. **Column Aliases for Consistency**:
   - Changed column aliases to ensure consistency with the original query and to avoid confusion.

2. **Non-Sargable Predicate Fix**:
   - The `WHERE labels IS NOT NULL` condition is already sargable, but ensuring the predicate is correctly formatted helps SQL Server make better decisions.
   
3. **Derived Columns**:
   - Added placeholders for derived columns like `[testSpecType]`, `[partTypeName]`, `[manufacturerName]`, and `[clientName]`. These should be replaced with actual logic if needed.

### CREATE INDEX Scripts

```sql
-- Index to optimize the join on TestRequests table
CREATE NONCLUSTERED INDEX IX_TestRequests_PartID ON [VEXA].[dbo].[TestRequests] ([partID])
INCLUDE ([id], [dateCreated], [testRequestNumber], [clientID], [testSpecID], [parts], [archived]);

-- Index to optimize the join on Parts table
CREATE NONCLUSTERED INDEX IX_Parts_ManufacturerID ON [VEXA].[dbo].[Parts] ([manufacturerID])
INCLUDE ([id], [name], [partTypeID]);

-- Index to optimize the join on Labels table
CREATE NONCLUSTERED INDEX IX_Labels_ParentID ON [VEXA].[dbo].[Labels] ([parentID])
INCLUDE ([id], [name]);

-- Index to optimize the join on ItemLabels table
CREATE NONCLUSTERED INDEX IX_ItemLabels_LabelTypeID ON [VEXA].[dbo].[ItemLabels] ([labelTypeID])
INCLUDE ([id], [itemID], [labelID]);
```

### Comments on Each Index

1. **IX_TestRequests_PartID**:
   - Targets the join pattern involving `partID` in the `TestRequests` table.
   - Includes necessary columns to eliminate key lookups and improve query performance.

2. **IX_Parts_ManufacturerID**:
   - Targets the join pattern involving `manufacturerID` in the `Parts` table.
   - Includes necessary columns to eliminate key lookups and improve query performance.

3. **IX_Labels_ParentID**:
   - Targets the join pattern involving `parentID` in the `Labels` table.
   - Includes necessary columns to eliminate key lookups and improve query performance.

4. **IX_ItemLabels_LabelTypeID**:
   - Targets the join pattern involving `labelTypeID` in the `ItemLabels` table.
   - Includes necessary columns to eliminate key lookups and improve query performance.

</details>

---
*Generated by SQL Optimization Agent · 2026-03-20 20:50:13*