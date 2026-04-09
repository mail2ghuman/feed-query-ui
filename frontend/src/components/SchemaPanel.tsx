import { SchemaColumn } from "../types";
import { Database, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface SchemaPanelProps {
  columns: SchemaColumn[];
  tableName: string;
}

export default function SchemaPanel({ columns, tableName }: SchemaPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-gray-700">
            Table: {tableName}
          </span>
          <span className="text-xs text-gray-400">
            ({columns.length} columns)
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>
      {isOpen && (
        <div className="border-t border-gray-100 p-3">
          <div className="grid grid-cols-2 gap-1 text-xs">
            {columns.map((col) => (
              <div
                key={col.name}
                className="flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-50"
              >
                <span className="font-mono font-medium text-gray-800">
                  {col.name}
                </span>
                <span className="text-gray-400">{col.type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
