import { useState, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";

interface QueryInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
}

const SUGGESTIONS = [
  "Was feed 4001 generated today?",
  "Show monthly volume for each feed",
  "List all files generated on the latest day",
  "Which feeds had INACTIVE versions yesterday?",
  "Show total source count by feed for January 2025",
  "How many FULL vs INCR versions were created?",
];

export default function QueryInput({ onSubmit, isLoading }: QueryInputProps) {
  const [question, setQuestion] = useState("");

  const handleSubmit = () => {
    if (question.trim() && !isLoading) {
      onSubmit(question.trim());
      setQuestion("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full space-y-3">
      <div className="flex items-end gap-2 bg-white border border-gray-300 rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 p-3">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your feed data..."
          className="flex-1 resize-none border-0 outline-none bg-transparent text-gray-900 placeholder-gray-400 text-sm min-h-10 max-h-32"
          rows={1}
          disabled={isLoading}
        />
        <button
          onClick={handleSubmit}
          disabled={!question.trim() || isLoading}
          className="flex-shrink-0 p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              setQuestion(s);
            }}
            className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-blue-50 hover:text-blue-700 transition-colors border border-gray-200"
            disabled={isLoading}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
