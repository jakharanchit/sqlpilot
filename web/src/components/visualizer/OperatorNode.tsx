// web/src/components/visualizer/OperatorNode.tsx
import React from 'react';
import type { PlanOperator } from '../../types';

interface Props {
  operator:  PlanOperator;
  selected:  boolean;
  onClick:   () => void;
}

// Color maps by severity
const SEVERITY_COLORS: Record<string, { bg: string; border: string; text: string; bar: string }> = {
  HIGH:   { bg: '#FEE2E2', border: '#DC2626', text: '#DC2626', bar: '#DC2626' },
  MEDIUM: { bg: '#FEF3C7', border: '#D97706', text: '#D97706', bar: '#D97706' },
  INFO:   { bg: '#DBEAFE', border: '#2563EB', text: '#2563EB', bar: '#2563EB' },
};

const NORMAL_COLORS = { bg: '#FFFFFF', border: '#E2E8F0', text: '#0F172A', bar: '#CBD5E1' };

export default function OperatorNode({ operator, selected, onClick }: Props) {
  const colors = operator.severity ? SEVERITY_COLORS[operator.severity] ?? NORMAL_COLORS : NORMAL_COLORS;
  const truncatedName = operator.name.length > 18 ? operator.name.slice(0, 17) + '…' : operator.name;

  const containerStyle: React.CSSProperties = {
    width:         '160px',
    height:        '56px',
    background:    colors.bg,
    border:        selected ? `2px solid var(--accent, #2563EB)` : `1px solid ${colors.border}`,
    borderRadius:  '6px',
    cursor:        'pointer',
    overflow:      'hidden',
    fontFamily:    'DM Sans, system-ui, sans-serif',
    boxSizing:     'border-box',
    display:       'flex',
    flexDirection: 'column',
    padding:       '6px 8px 0',
    userSelect:    'none',
    boxShadow:     selected ? '0 0 0 2px rgba(37,99,235,0.25)' : 'none',
  };

  return (
    <div style={containerStyle} onClick={onClick}>
      {/* Top row: name + severity badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flex: 1 }}>
        <span style={{
          fontSize:    '11px',
          fontWeight:  600,
          color:       colors.text,
          whiteSpace:  'nowrap',
          overflow:    'hidden',
          textOverflow:'ellipsis',
          maxWidth:    operator.severity ? '95px' : '140px',
        }}>
          {truncatedName}
        </span>
        {operator.severity && (
          <span style={{
            fontSize:   '9px',
            fontWeight: 700,
            color:      colors.border,
            background: 'transparent',
            letterSpacing: '0.03em',
          }}>
            {operator.severity}
          </span>
        )}
      </div>

      {/* Cost bar row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
        {/* Bar track */}
        <div style={{
          flex:         1,
          height:       '4px',
          background:   '#E2E8F0',
          borderRadius: '2px',
          overflow:     'hidden',
        }}>
          <div style={{
            width:        `${Math.min(100, operator.cost_pct)}%`,
            height:       '100%',
            background:   colors.bar,
            borderRadius: '2px',
            transition:   'width 0.3s ease',
          }} />
        </div>
        {/* Percentage label */}
        <span style={{
          fontSize:   '10px',
          color:      colors.text,
          fontWeight: 500,
          minWidth:   '30px',
          textAlign:  'right',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          {operator.cost_pct}%
        </span>
      </div>
    </div>
  );
}
