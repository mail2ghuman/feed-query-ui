import { AskResponse, ConversationEntry, SchemaResponse } from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function askQuestion(
  question: string,
  conversationHistory: ConversationEntry[] = [],
): Promise<AskResponse> {
  const response = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_history: conversationHistory }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API error: ${response.status} - ${detail}`);
  }
  return response.json();
}

export async function getSchema(): Promise<SchemaResponse> {
  const response = await fetch(`${API_URL}/api/schema`);
  if (!response.ok) {
    throw new Error(`Failed to fetch schema: ${response.status}`);
  }
  return response.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/healthz`);
    return response.ok;
  } catch {
    return false;
  }
}
