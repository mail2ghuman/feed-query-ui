export interface AskResponse {
  question: string;
  generated_sql: string;
  columns: string[];
  rows: Record<string, string | number | boolean | null>[];
  row_count: number;
  error: string | null;
}

export interface SchemaColumn {
  name: string;
  type: string;
}

export interface SchemaResponse {
  table_name: string;
  columns: SchemaColumn[];
}

export interface ChatMessage {
  id: string;
  type: "question" | "answer";
  content: string;
  data?: AskResponse;
  timestamp: Date;
}
