import { useState, useEffect, useRef } from "react";
import { Database } from "lucide-react";
import QueryInput from "./components/QueryInput";
import ChatMessage from "./components/ChatMessage";
import SchemaPanel from "./components/SchemaPanel";
import StatusBadge from "./components/StatusBadge";
import { ChatMessage as ChatMessageType, SchemaColumn } from "./types";
import { askQuestion, getSchema, healthCheck } from "./api";

function App() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<
    "connected" | "disconnected" | "connecting"
  >("connecting");
  const [schema, setSchema] = useState<SchemaColumn[]>([]);
  const [tableName, setTableName] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkBackend = async () => {
      setBackendStatus("connecting");
      const ok = await healthCheck();
      setBackendStatus(ok ? "connected" : "disconnected");
      if (ok) {
        try {
          const schemaData = await getSchema();
          setSchema(schemaData.columns);
          setTableName(schemaData.table_name);
        } catch (err) {
          console.error("Failed to fetch schema:", err);
        }
      }
    };
    checkBackend();
    const interval = setInterval(async () => {
      const ok = await healthCheck();
      setBackendStatus(ok ? "connected" : "disconnected");
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAsk = async (question: string) => {
    const questionMsg: ChatMessageType = {
      id: crypto.randomUUID(),
      type: "question",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, questionMsg]);
    setIsLoading(true);

    try {
      const result = await askQuestion(question);
      const answerMsg: ChatMessageType = {
        id: crypto.randomUUID(),
        type: "answer",
        content: result.error ? `Error: ${result.error}` : "Query results:",
        data: result,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, answerMsg]);
    } catch (err) {
      const errorMsg: ChatMessageType = {
        id: crypto.randomUUID(),
        type: "answer",
        content: `Failed to get response: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="w-6 h-6 text-blue-600" />
          <div>
            <h1 className="text-lg font-semibold text-gray-900">
              Feed Query UI
            </h1>
            <p className="text-xs text-gray-500">
              Ask questions about your batch feed data using natural language
            </p>
          </div>
        </div>
        <StatusBadge status={backendStatus} />
      </header>

      {/* Schema Panel */}
      {schema.length > 0 && (
        <div className="px-6 pt-4">
          <SchemaPanel columns={schema} tableName={tableName} />
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <Database className="w-12 h-12 text-gray-300 mb-4" />
            <h2 className="text-lg font-medium text-gray-600 mb-2">
              Ask anything about your feed data
            </h2>
            <p className="text-sm text-gray-400 max-w-md">
              Try questions like &ldquo;Was feed 4001 generated today?&rdquo; or
              &ldquo;Show monthly volume for each feed&rdquo;. Your question
              will be converted to SQL and run against the Hive table.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
              <Database className="w-4 h-4 text-blue-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-500">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div
                    className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                </div>
                Generating SQL and querying data...
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <QueryInput onSubmit={handleAsk} isLoading={isLoading} />
      </div>
    </div>
  );
}

export default App;
