// web/src/components/visualizer/PlanTree.tsx
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
} from 'react';
import * as d3 from 'd3';
import * as ReactDOM from 'react-dom/client';
import type { PlanOperator, StructuredPlan } from '../../types';
import OperatorNode from './OperatorNode';

// ── Public handle exposed via ref ──────────────────────────────────────────────
export interface PlanTreeHandle {
  zoomIn:    () => void;
  zoomOut:   () => void;
  fitScreen: () => void;
}

// ── Props ──────────────────────────────────────────────────────────────────────
interface Props {
  plan:             StructuredPlan;
  selectedId:       string | null;
  onSelectOperator: (op: PlanOperator | null) => void;
}

// ── Constants ──────────────────────────────────────────────────────────────────
const NODE_W = 160;
const NODE_H = 56;

// ── Styles ─────────────────────────────────────────────────────────────────────
const _styles = `
.plan-tree-wrapper {
  width: 100%;
  height: 480px;
  position: relative;
  background: #F8FAFC;
  border-radius: 8px;
  overflow: hidden;
}

.plan-tree-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.plan-tree-svg .link {
  pointer-events: none;
}
`;

if (typeof document !== 'undefined') {
  const id = 'plan-tree-styles';
  if (!document.getElementById(id)) {
    const el = document.createElement('style');
    el.id = id;
    el.textContent = _styles;
    document.head.appendChild(el);
  }
}

// ── Helper: fit the tree into the SVG viewport ─────────────────────────────────
function fitTree(
  svg:  d3.Selection<SVGSVGElement, unknown, null, undefined>,
  g:    d3.Selection<SVGGElement, unknown, null, undefined>,
  zoom: d3.ZoomBehavior<SVGSVGElement, unknown>,
) {
  const svgNode = svg.node();
  const gNode   = g.node();
  if (!svgNode || !gNode) return;

  const svgW   = svgNode.clientWidth  || 800;
  const svgH   = svgNode.clientHeight || 480;
  const bounds = (gNode as SVGGElement).getBBox();

  if (bounds.width === 0 || bounds.height === 0) return;

  const scale = Math.min(0.9, Math.min(svgW / (bounds.width + 40), svgH / (bounds.height + 80)));
  const tx    = (svgW - bounds.width  * scale) / 2 - bounds.x * scale;
  const ty    = 40;

  svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}

// ── Component ──────────────────────────────────────────────────────────────────
const PlanTree = forwardRef<PlanTreeHandle, Props>(
  ({ plan, selectedId, onSelectOperator }, ref) => {
    const svgRef       = useRef<SVGSVGElement>(null);
    const zoomRef      = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
    const gRef         = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null);
    // Track roots created for each foreignObject so we can update without recreating
    const rootsRef     = useRef<Map<string, ReactDOM.Root>>(new Map());

    // ── Expose handle ──────────────────────────────────────────────────────────
    useImperativeHandle(ref, () => ({
      zoomIn: () => {
        if (!zoomRef.current || !svgRef.current) return;
        d3.select(svgRef.current).call(zoomRef.current.scaleBy, 1.3);
      },
      zoomOut: () => {
        if (!zoomRef.current || !svgRef.current) return;
        d3.select(svgRef.current).call(zoomRef.current.scaleBy, 0.77);
      },
      fitScreen: () => {
        if (!zoomRef.current || !svgRef.current || !gRef.current) return;
        fitTree(
          d3.select(svgRef.current),
          gRef.current,
          zoomRef.current,
        );
      },
    }));

    // ── Build tree when plan changes ───────────────────────────────────────────
    useEffect(() => {
      if (!plan || !svgRef.current) return;

      // Unmount any existing React roots before clearing SVG
      rootsRef.current.forEach(root => { try { root.unmount(); } catch { /* ignore */ } });
      rootsRef.current.clear();

      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();

      const g = svg.append('g').attr('class', 'tree-root');
      gRef.current = g;

      // D3 hierarchy + tree layout
      const root       = d3.hierarchy<PlanOperator>(plan.tree, d => d.children);
      const treeLayout = d3.tree<PlanOperator>().nodeSize([NODE_W + 40, NODE_H + 54]);
      treeLayout(root);

      // Draw links (behind nodes)
      g.selectAll('.link')
        .data(root.links())
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('fill', 'none')
        .attr('stroke', '#CBD5E1')
        .attr('stroke-width', 1.5)
        .attr('d', d3.linkVertical<d3.HierarchyLink<PlanOperator>, d3.HierarchyPointNode<PlanOperator>>()
          .x(d => (d as any).x)
          .y(d => (d as any).y),
        );

      // Draw nodes as foreignObject (embeds React components)
      const nodeData = root.descendants();

      nodeData.forEach(d => {
        const fo = g.append('foreignObject')
          .attr('class', 'node')
          .attr('width',  NODE_W)
          .attr('height', NODE_H)
          .attr('x', (d as any).x - NODE_W / 2)
          .attr('y', (d as any).y - NODE_H / 2)
          .attr('overflow', 'visible')
          .node()!;

        const reactRoot = ReactDOM.createRoot(fo as unknown as Element);
        rootsRef.current.set(d.data.id, reactRoot);
        reactRoot.render(
          <OperatorNode
            operator={d.data}
            selected={selectedId === d.data.id}
            onClick={() => onSelectOperator(d.data.id === selectedId ? null : d.data)}
          />,
        );
      });

      // Zoom behaviour
      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.15, 3])
        .on('zoom', e => g.attr('transform', e.transform));
      zoomRef.current = zoom;
      svg.call(zoom);

      // Auto-fit on first render (after a tick so getBBox has real dimensions)
      requestAnimationFrame(() => fitTree(svg, g, zoom));

      // Cleanup on unmount / re-render
      return () => {
        rootsRef.current.forEach(root => { try { root.unmount(); } catch { /* ignore */ } });
        rootsRef.current.clear();
      };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [plan]);

    // ── Re-render nodes when selection changes (no tree rebuild) ───────────────
    useEffect(() => {
      if (!gRef.current) return;

      const nodes = gRef.current.selectAll<SVGForeignObjectElement, d3.HierarchyPointNode<PlanOperator>>('.node');

      nodes.each(function(d) {
        const existingRoot = rootsRef.current.get(d.data.id);
        if (!existingRoot) return;
        existingRoot.render(
          <OperatorNode
            operator={d.data}
            selected={selectedId === d.data.id}
            onClick={() => onSelectOperator(d.data.id === selectedId ? null : d.data)}
          />,
        );
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedId]);

    return (
      <div className="plan-tree-wrapper">
        <svg
          ref={svgRef}
          className="plan-tree-svg"
        />
      </div>
    );
  },
);

PlanTree.displayName = 'PlanTree';
export default PlanTree;
