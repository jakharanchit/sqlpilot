# Optimization Report
**Date:** 2026-03-21 09:48:51  
**Tables:** Labels, TestRequests, ItemLabels

## Original Query
```sql
SELECT * FROM View_LabeledTestRequestsAndLabelIDs WHERE labels is not null
```

## Optimized Query
```sql
SELECT 
    ltlr.id,
    ltlr.dateCreated,
    ltlr.testRequestNumber,
    ltlr.clientID,
    ltlr.testSpecID,
    ltlr.partID,
    ltlr.userIdCreated,
    ltlr.userIdModified,
    ltlr.dateModified,
    ltlr.parts,
    ltlr.archived,
    il.labelTypeID,
    il.itemID,
    il.labelID
FROM 
    View_LabeledTestRequestsAndLabelIDs ltlr
JOIN 
    ItemLabels il ON ltlr.id = il.itemID
WHERE 
    ltlr.labels IS NOT NULL;
```

## Diagnosis

Here’s the analysis and fixes for the query performance problems:

---

### 1. **Non-sargable Predicate on Clustered Index Scan (Labels Table)**  
   - **Problem:** The `WHERE labels IS NOT NULL` predicate may not be sargable, causing a full clustered index scan instead of an efficient seek operation.  
   - **Performance Impact:** A full table scan on the `Labels` table (~9 rows) is unnecessary and causes extra I/O operations, increasing latency.  
   - **Fix Concept:** Ensure the predicate is sargable by avoiding implicit conversions or using column types consistently. Consider adding a non-clustered index on the `name` or `parentID` columns if they are used in predicates.

---

### 2. **Missing Indexes on Join Columns (ItemLabels Table)**  
   - **Problem:** The `ItemLabels` table lacks indexes on `labelTypeID`, `itemID`, or `labelID`, leading to full scans during joins.  
   - **Performance Impact:** Full scans on the `ItemLabels` table (~175 rows) increase join costs and contribute to expensive hash matches in the execution plan.  
   - **Fix Concept:** Add non-clustered indexes on frequently used columns like `itemID` or `labelTypeID` to enable efficient joins.

---

### 3. **Cardinality Estimation Errors Leading to Hash Joins**  
   - **Problem:** The optimizer’s cardinality estimates suggest it expects fewer rows than actual, leading to suboptimal join strategies (e.g., hash matches instead of nested loops).  
   - **Performance Impact:** Hash joins require significant memory and processing time, especially with large intermediate datasets.  
   - **Fix Concept:** Collect accurate statistics on columns used in predicates and joins. Consider creating histogram statistics if the optimizer underestimates row distributions.

---

### 4. **Explicit Sorts Causing Performance Bottlenecks**  
   - **Problem:** Multiple explicit sort operations are present in the execution plan, contributing to high latency.  
   - **Performance Impact:** Sorting is resource-intensive and can lead to disk spools if memory pressure is high.  
   - **Fix Concept:** Use covering indexes or modify queries to avoid sorting by ensuring data is already ordered (e.g., via index ordering).

---

### 5. **Excessive Nested Loops Causing High Join Costs**  
   - **Problem:** The execution plan shows multiple nested loops with high costs, indicating inefficient join strategies.  
   - **Performance Impact:** Each nested loop adds to the overall query cost, especially when combined with hash matches and sorts.  
   - **Fix Concept:** Optimize join order or introduce indexes on columns involved in joins (e.g., `itemID` or `labelTypeID`) to reduce nested loop costs.

---

### Summary of Recommendations:
1. **Ensure Sargability:** Verify that predicates are sargable and avoid implicit type conversions.
2. **Add Missing Indexes:** Create non-clustered indexes on frequently used columns in `ItemLabels` (e.g., `itemID`, `labelTypeID`).  
3. **Improve Cardinality Estimates:** Collect statistics on columns involved in joins and filters to help the optimizer make better decisions.  
4. **Reduce Sorts:** Use covering indexes or modify queries to avoid explicit sorts by leveraging pre-sorted data.  
5. **Optimize Joins:** Introduce indexes on join columns and consider reordering joins to minimize nested loop costs.

By addressing these issues, you can significantly improve the query’s performance.
