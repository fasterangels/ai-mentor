import { useState, useEffect } from "react";
import { getPredictionHistory } from "@/api/evaluation";
import { PredictionsTable } from "@/components/Tables/PredictionsTable";
import type { HistoryRow } from "@/types/api";

export function PredictionHistory() {
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "hits" | "misses">("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPredictionHistory({ filter })
      .then((res) => setRows(res.items ?? []))
      .catch(() => {
        setError("Δεν ήταν δυνατή η φόρτωση του ιστορικού.");
        setRows([]);
      })
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex gap-2 items-center">
        <span className="text-sm font-medium text-gray-700">Φίλτρο:</span>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as "all" | "hits" | "misses")}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="all">Όλες</option>
          <option value="hits">Επιτυχίες</option>
          <option value="misses">Αποτυχίες</option>
        </select>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
          {error}
        </div>
      )}

      <PredictionsTable rows={rows} loading={loading} />
    </div>
  );
}
