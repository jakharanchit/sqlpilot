# Benchmark: full-run
**Date:** 2026-03-21 09:56:54
**Runs:** 10 per query

## Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Average | 14891.7ms | 1.49ms | **100.0% faster** |
| Fastest | 13861.92ms | 0.4ms | — |
| Slowest | 15506.1ms | 10.68ms | — |
| Median  | 15061.29ms | 0.44ms | — |
| Std Dev | 609.05ms | 3.23ms | — |
| Rows returned | 175 | 175 | ✓ Match |

**Speedup: 9994.4x faster**

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