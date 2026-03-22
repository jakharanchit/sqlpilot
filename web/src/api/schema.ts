// src/api/schema.ts
import { api } from "./client";
import type { TableSchema, ViewDefinition, SchemaAll } from "@/types/schema";

export const schemaApi = {
  getAll:     ()           => api.get<SchemaAll>("/api/schema/all"),
  getTables:  ()           => api.get<{ tables: string[]; count: number }>("/api/schema/tables"),
  getViews:   ()           => api.get<{ views: string[]; count: number }>("/api/schema/views"),
  getTable:   (name: string) => api.get<TableSchema>(`/api/schema/table/${encodeURIComponent(name)}`),
  getView:    (name: string) => api.get<ViewDefinition>(`/api/schema/view/${encodeURIComponent(name)}`),
};
