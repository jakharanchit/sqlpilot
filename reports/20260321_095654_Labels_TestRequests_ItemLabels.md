# Optimization Report
**Date:** 2026-03-21 09:56:54  
**Tables:** Labels, TestRequests, ItemLabels

## Performance Result

| Before | After | Improvement |
|--------|-------|-------------|
| 14891.7ms | 1.49ms | **100.0% faster** |

## Original Query
```sql
SELECT * FROM View_LabeledTestRequestsAndLabelIDs WHERE labels is not null
```

## Optimized Query
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

## Diagnosis

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
