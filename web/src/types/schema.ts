// src/types/schema.ts

export interface ColumnDef {
  name: string;
  type: string;
  max_length: number | null;
  nullable: "YES" | "NO";
  primary_key: "YES" | "NO";
}

export interface IndexDef {
  name: string;
  type: string;
  unique: boolean;
  key_columns: string;
  included_columns: string | null;
}

export interface TableSchema {
  table_name: string;
  estimated_row_count: number | "unknown";
  columns: ColumnDef[];
  indexes: IndexDef[];
}

export interface ViewDefinition {
  view_name: string;
  definition: string;
  referenced_tables: string[];
}

export interface SchemaAll {
  tables: string[];
  views: string[];
  table_count: number;
  view_count: number;
}
