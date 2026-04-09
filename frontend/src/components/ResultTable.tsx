import { AskResponse } from "../types";

interface ResultTableProps {
  data: AskResponse;
}

export default function ResultTable({ data }: ResultTableProps) {
  if (data.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700 text-sm font-medium">Error</p>
        <p className="text-red-600 text-sm mt-1">{data.error}</p>
      </div>
    );
  }

  if (data.rows.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-700 text-sm">
          No results found for this query.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{data.row_count} row(s) returned</span>
      </div>
      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {data.columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data.rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 transition-colors">
                {data.columns.map((col) => (
                  <td
                    key={col}
                    className="px-4 py-2 text-gray-700 whitespace-nowrap"
                  >
                    {row[col] !== null && row[col] !== undefined
                      ? String(row[col])
                      : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
