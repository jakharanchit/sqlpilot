// web/src/api/plan.ts
import { apiFetch } from './client';
import type { StructuredPlan, PlanFromQueryRequest } from '../types';

export interface OperatorCatalogueEntry {
  name:     string;
  severity: string;
  reason:   string;
}

export const planApi = {
  /** Analyze a SQL query and return the structured plan tree. */
  fromQuery: (body: PlanFromQueryRequest): Promise<StructuredPlan> =>
    apiFetch('/api/plan/from-query', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }),

  /** Returns the known expensive operator types for the legend. */
  operators: (): Promise<OperatorCatalogueEntry[]> =>
    apiFetch('/api/plan/operators'),
};
