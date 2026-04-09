import { useState } from "react";
import { User, Bot, ChevronDown, ChevronUp, Code } from "lucide-react";
import { ChatMessage as ChatMessageType } from "../types";
import ResultTable from "./ResultTable";

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [showSql, setShowSql] = useState(false);
  const isQuestion = message.type === "question";

  return (
    <div
      className={`flex gap-3 ${isQuestion ? "justify-end" : "justify-start"}`}
    >
      {!isQuestion && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
          <Bot className="w-4 h-4 text-blue-600" />
        </div>
      )}

      <div
        className={`max-w-4xl ${
          isQuestion ? "bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2.5" : "space-y-3 flex-1"
        }`}
      >
        {isQuestion ? (
          <p className="text-sm">{message.content}</p>
        ) : message.data ? (
          <div className="space-y-3">
            {message.data.generated_sql && (
              <button
                onClick={() => setShowSql(!showSql)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
              >
                <Code className="w-3.5 h-3.5" />
                {showSql ? "Hide" : "Show"} generated SQL
                {showSql ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </button>
            )}
            {showSql && message.data.generated_sql && (
              <pre className="bg-gray-900 text-green-400 text-xs p-3 rounded-lg overflow-x-auto">
                <code>{message.data.generated_sql}</code>
              </pre>
            )}
            <ResultTable data={message.data} />
          </div>
        ) : (
          <p className="text-sm text-gray-700">{message.content}</p>
        )}
      </div>

      {isQuestion && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
          <User className="w-4 h-4 text-gray-600" />
        </div>
      )}
    </div>
  );
}
