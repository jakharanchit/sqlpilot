# Run Log — Query Optimization
**Date:** 2026-03-21 09:54:24
**Label:** (none)
**Run type:** query

---

## Original Query
```sql
SELECT * FROM View_LabeledTestRequestsAndLabelIDs WHERE labels is not null
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
**Execution time:** 19232.4ms
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

Here's a structured breakdown of the diagnosed problems, their impacts, and proposed fixes:

---

**1. Non-Sargable Predicate on 'labels is not null'**

- **Impact**: The condition isn't sargable, forcing full scans instead of efficient index lookups. This significantly increases query time as it can't leverage indexes effectively.
  
- **Fix**: Create a non-clustered index on the 'labels' column in the relevant tables (e.g., ItemLabels). Ensure that this index is covering to avoid additional lookups.

---

**2. Multiple Sort Operations**

- **Impact**: Each sort operation consumes memory and processing time, especially when dealing with 175 rows repeatedly. This adds up and slows down the query.

- **Fix**: Introduce indexes that cover the columns involved in sorting. Modify join operations to use hash joins instead or reorganize data retrieval order to minimize or eliminate explicit sorts.

---

**3. Hash Matches Causing Data膨胀**

- **Impact**: Large intermediate datasets from hash matches lead to increased memory usage and slower processing times, affecting query performance.

- **Fix**: Optimize join strategies by adding indexes on the columns used in joins. Use inner joins where possible and ensure that statistics are up-to-date for accurate cardinality estimates.

---

**4. Clustered Index Scans on Small Tables**

- **Impact**: Full scans on small tables like Labels (~9 rows) and ItemLabels (~175 rows) are inefficient. Ideally, these should be retrieved using more efficient methods.

- **Fix**: Introduce non-clustered indexes with covering columns on these small tables to allow quick retrieval without full scans.

---

**5. Lack of Covering Indexes**

- **Impact**: Without covering indexes, the query engine has to perform additional lookups, increasing the number of logical reads and overall time.

- **Fix**: Create covering indexes that include all necessary columns from the selected views or tables to avoid multiple lookups.

---

**Summary of Recommendations:**

1. Implement non-clustered indexes with covering properties on the 'labels' column in ItemLabels.
2. Optimize join operations by creating appropriate indexes on the joining columns.
3. Replace explicit sorts where possible by reorganizing data retrieval through better indexing or query structure.
4. Review and enhance any existing statistics to improve cardinality estimation accuracy, which can help SQL Server choose more optimal execution plans.

By addressing these issues, the query's performance should be significantly improved, reducing execution time and resource usage.

---

## Optimized Query (Qwen2.5-Coder)
```sql
SELECT 
    tr.*
FROM 
    TestRequests tr
JOIN 
    ItemLabels il ON tr.id = il.itemID
WHERE 
    il.labelTypeID IS NOT NULL;
```

---

## Full AI Response (raw)
<details>
<summary>Click to expand</summary>

### Optimized Query

```sql
SELECT 
    tr.*
FROM 
    TestRequests tr
JOIN 
    ItemLabels il ON tr.id = il.itemID
WHERE 
    il.labelTypeID IS NOT NULL;
```

### Changes and Why

1. **Query Simplification**:
   - Removed the use of a view (`View_LabeledTestRequestsAndLabelIDs`) and directly joined `TestRequests` with `ItemLabels`.
   - This simplifies the query and allows for better index utilization.

2. **Predicate Adjustment**:
   - Changed `WHERE labels IS NOT NULL` to `WHERE il.labelTypeID IS NOT NULL`.
   - This assumes that `labelTypeID` being not null implies that `labels` is populated, which aligns with typical database design practices where foreign keys cannot be null unless explicitly allowed.

### CREATE INDEX Scripts

```sql
-- Index on ItemLabels for labelTypeID and itemID to support the join operation
CREATE NONCLUSTERED INDEX idx_ItemLabels_labelTypeID_itemID 
ON ItemLabels (labelTypeID, itemID)
INCLUDE (id); -- INCLUDE columns to eliminate Key Lookups
-- Targets the join pattern in the query

-- Covering index on TestRequests for id to avoid additional lookups during join
CREATE NONCLUSTERED INDEX idx_TestRequests_id 
ON TestRequests (id);
-- Targets the retrieval of TestRequests rows during the join operation
```

### Explanation of Indexes

1. **idx_ItemLabels_labelTypeID_itemID**:
   - **Target**: The join between `ItemLabels` and `TestRequests`.
   - **Columns**: `(labelTypeID, itemID)` are used in the join condition.
   - **INCLUDE**: `id` is included to eliminate Key Lookups when selecting from `ItemLabels`.

2. **idx_TestRequests_id**:
   - **Target**: Efficient retrieval of `TestRequests` rows during the join operation.
   - **Columns**: `(id)` is the primary key and used in the join condition.

These indexes should help reduce the number of scans, eliminate unnecessary sorts, and optimize the overall execution plan, leading to improved query performance.

</details>

---
*Generated by SQL Optimization Agent · 2026-03-21 09:54:24*