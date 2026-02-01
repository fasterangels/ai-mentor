import type { HistoryRow } from "@/types/api";

interface PredictionsTableProps {
  rows: HistoryRow[];
  loading?: boolean;
}

export function PredictionsTable({ rows, loading }: PredictionsTableProps) {
  if (loading) {
    return (
      <div className="text-center py-8 text-gray-500">Φόρτωση...</div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">Δεν υπάρχουν προβλέψεις.</div>
    );
  }

  return (
    <div className="overflow-x-auto border border-gray-200 rounded-lg">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ημερομηνία</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Αγώνας</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Πρόβλεψη</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Τελικό Σκορ</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Αποτέλεσμα</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {rows.map((row) => (
            <tr key={row.id}>
              <td className="px-4 py-3 text-sm text-gray-700">
                {new Date(row.evaluated_at_utc).toLocaleDateString("el-GR")}
              </td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {row.home_team} vs {row.away_team}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {row.market}: {row.decision}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {row.final_home_score} – {row.final_away_score}
              </td>
              <td className="px-4 py-3 text-center">
                {row.hit ? (
                  <span className="text-green-600" title="Επιτυχία">✔</span>
                ) : (
                  <span className="text-red-600" title="Αποτυχία">✖</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
