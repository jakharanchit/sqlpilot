# Run Log — Query Optimization
**Date:** 2026-03-21 10:26:51
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
**Execution time:** 20044.36ms
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

### Problems in Query Performance:

1. **Non-sargable Predicate on Clustered Index Scan (Labels Table)**
   - **Performance Impact**: The query is performing a full scan on the Labels table with an estimated 9 rows, which could be optimized using an index if the predicate were sargable.
   - **Fix**: Ensure predicates are written without functions and that indexes exist on the involved columns.

2. **Non-sargable Predicate on Clustered Index Scan (ItemLabels Table)**
   - **Performance Impact**: Similar to the first issue, this scan on ItemLabels with 175 rows is inefficient.
   - **Fix**: Modify the predicate or add an index if possible.

3. **Inefficient Join Operations Leading to Sorts and Hash Matches**
   - **Performance Impact**: These operations are costly and suggest a lack of appropriate indexes.
   - **Fix**: Add non-clustered indexes on join columns across all tables involved.

### Summary:

The main performance issues stem from inefficient index usage and costly join operations. Prioritizing the creation of appropriate indexes and ensuring sargable predicates will likely improve query performance significantly.

---

## Optimized Query (Qwen2.5-Coder)
```sql
SELECT tr.*
FROM TestRequests tr
JOIN ItemLabels il ON tr.id = il.itemID
JOIN Labels l ON il.labelID = l.id
WHERE l.name IS NOT NULL;
```

---

## Full AI Response (raw)
<details>
<summary>Click to expand</summary>

### Optimized Query

```sql
SELECT tr.*
FROM TestRequests tr
JOIN ItemLabels il ON tr.id = il.itemID
JOIN Labels l ON il.labelID = l.id
WHERE l.name IS NOT NULL;
```

### Changes and Why

1. **Removed the View**: The original query involved a view (`View_LabeledTestRequestsAndLabelIDs`), which was not provided. Assuming the view performs joins similar to what's in the optimized query, removing the view and writing out the joins explicitly allows for more granular index creation.
2. **Direct Join Conditions**: By directly specifying the join conditions, SQL Server can better utilize indexes on these columns.
3. **Filter Condition**: Changed `WHERE labels is not null` to `WHERE l.name IS NOT NULL`, assuming that "labels" refers to the `name` column in the `Labels` table. This ensures the predicate is sargable.

### CREATE INDEX Scripts

```sql
-- Index for Labels Table on 'name' (sargability issue)
CREATE NONCLUSTERED INDEX idx_Labels_name ON Labels(name);

-- Composite index on ItemLabels Table to optimize join with TestRequests and Labels
CREATE NONCLUSTERED INDEX idx_ItemLabels_itemID_labelID ON ItemLabels(itemID, labelID) INCLUDE (id);

-- Composite index on TestRequests Table to optimize join with ItemLabels
CREATE NONCLUSTERED INDEX idx_TestRequests_id ON TestRequests(id) INCLUDE (dateCreated, testRequestNumber, clientID, testSpecID, partID, userIdCreated, userIdModified, dateModified, parts, archived);
```

### Index Comments

1. **idx_Labels_name**: Targets the sargability issue by allowing efficient filtering on the `name` column.
2. **idx_ItemLabels_itemID_labelID**: Optimizes the join between `TestRequests` and `ItemLabels`, as well as between `ItemLabels` and `Labels`.
3. **idx_TestRequests_id**: Optimizes the join with `ItemLabels` by including all columns from `TestRequests` to eliminate key lookups.

</details>

---
*Generated by SQL Optimization Agent · 2026-03-21 10:26:51*