# Spec: SQL Execution Plan Visualizer (React + D3)

## 1. Data Contract (JSON Tree)
The parser must output a `PlanNode` structure:
```typescript
interface PlanNode {
  name: string;          // e.g., "Index Seek"
  physicalOp: string;    // e.g., "Clustered Index Seek"
  logicalOp: string;
  estimateRows: number;
  nodeCost: number;      // Calculated: Subtree - Sum(Children Subtree)
  relativeCost: number;  // % of total plan cost
  isParallel: boolean;
  warnings: string[];    // e.g., "Type Conversion", "No Join Predicate"
  children: PlanNode[];
}
```

## 2. Visualization Components

### A. The Operator Node (SVG Group)
*   **Shape:** Rectangular cards with rounded corners.
*   **Color-Coding:**
    *   `nodeCost < 10%`: Neutral Blue/Gray border.
    *   `10% - 30%`: Yellow border (Warning).
    *   `> 30%`: Red thick border (Bottleneck).
*   **Iconography:** Map `physicalOp` to standard SQL icons (Nested Loops = two overlapping circles, Table Scan = cylinder).
*   **Dynamic Width Paths:** The thickness of the lines (edges) connecting nodes should be proportional to the `estimateRows` attribute (Visualizing data volume flow).

### B. The Layout Engine
*   **D3 Algorithm:** `d3.tree()` or `d3.cluster()`.
*   **Orientation:** Right-to-Left (Flowing from data sources on the right to the Result Set on the left).
*   **Separation:** Fixed 200px horizontal separation to allow for label room.

## 3. Interactive 'Diff' Features

### Synchronized Pan/Zoom
*   Wrap two SVG components in a `PlanDiffContainer`.
*   Use a shared `useRef` for the D3 Zoom behavior. 
*   **User Action:** When the user pans the "Before" plan, the "After" plan follows identically.

### Delta Highlighting
*   **Cost Improvement:** Highlight the `relativeCost` label in green if it is lower than the corresponding node in the baseline plan.
*   **Plan Pruning:** If the AI optimization removed a node (e.g., turned a Hash Join into a Nested Loop), the removed subtree in the "Before" view should have a light red semi-transparent overlay.

## 4. Implementation Steps for AI

1.  **Phase 1: XML Parser Utility**
    *   Use `fast-xml-parser` to ingest `.sqlplan`.
    *   Extract `BatchSequence > Batch > Statements > StmtSimple > QueryPlan`.
    *   Flatten the `RelOp` hierarchy into the `PlanNode` format.

2.  **Phase 2: D3 Hierarchy Root**
    *   Initialize `d3.hierarchy(data)`.
    *   Implement the `d3.tree()` layout.

3.  **Phase 3: React SVG Component**
    *   Map through `root.descendants()` to render `<Node />` components.
    *   Map through `root.links()` to render `<Edge />` (diagonal paths).

4.  **Phase 4: Optimization Summary Overlay**
    *   Create a floating card comparing `StatementEstimatedTotalFullCost` for both plans.
    *   Calculate: `((OldCost - NewCost) / OldCost) * 100` to show total percentage gain.

## 5. CSS Theme (Dark Mode)
```css
.node-bottleneck { stroke: #ff4d4f; stroke-width: 3px; filter: drop-shadow(0 0 5px #ff4d4f); }
.node-optimized { stroke: #52c41a; stroke-width: 3px; }
.edge-heavy-flow { stroke: #666; stroke-width: 5px; }
.edge-light-flow { stroke: #ccc; stroke-width: 1px; }
```
