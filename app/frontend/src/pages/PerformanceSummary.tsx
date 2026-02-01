import { useState, useEffect } from "react";
import { getKpis } from "@/api/evaluation";
import { PERIOD_LABELS, type PeriodTab } from "@/types/ui";
import type { KPIReport } from "@/types/api";

export function PerformanceSummary() {
  const [period, setPeriod] = useState<PeriodTab>("DAY");
  const [kpis, setKpis] = useState<KPIReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const referenceDate = new Date().toISOString();

  useEffect(() => {
    setLoading(true);
    setError(null);
    getKpis(period, referenceDate)
      .then(setKpis)
      .catch(() => setError("Δεν ήταν δυνατή η φόρτωση των ΚΠΙ."))
      .finally(() => setLoading(false));
  }, [period, referenceDate]);

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        {(["DAY", "WEEK", "MONTH"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              period === p
                ? "bg-gray-800 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
          {error}
        </div>
      )}

      {loading && <div className="text-gray-500">Φόρτωση...</div>}

      {!loading && kpis && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-500">Σύνολο Προγνωστικών</p>
              <p className="text-2xl font-semibold text-gray-900">{kpis.total_predictions}</p>
            </div>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-500">Ποσοστό Επιτυχίας</p>
              <p className="text-2xl font-semibold text-green-600">
                {(kpis.hit_rate * 100).toFixed(1)}%
              </p>
            </div>
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-500">Ποσοστό Αποτυχίας</p>
              <p className="text-2xl font-semibold text-red-600">
                {(kpis.miss_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Επιτυχίες vs Αποτυχίες</h3>
            <div className="flex h-8 gap-1">
              <div
                className="bg-green-500 rounded-l"
                style={{
                  width: kpis.total_predictions
                    ? `${kpis.hit_rate * 100}%`
                    : "0%",
                  minWidth: kpis.hits ? "4px" : "0",
                }}
                title={`${kpis.hits} επιτυχίες`}
              />
              <div
                className="bg-red-500 rounded-r"
                style={{
                  width: kpis.total_predictions
                    ? `${kpis.miss_rate * 100}%`
                    : "0%",
                  minWidth: kpis.misses ? "4px" : "0",
                }}
                title={`${kpis.misses} αποτυχίες`}
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {kpis.hits} επιτυχίες · {kpis.misses} αποτυχίες
            </p>
          </div>

          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Περίοδος
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Επιτυχίες
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Αποτυχίες
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    Ποσοστό
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {PERIOD_LABELS[period]} ({new Date(kpis.reference_date_utc).toLocaleDateString("el-GR")})
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">{kpis.hits}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">{kpis.misses}</td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {(kpis.hit_rate * 100).toFixed(1)}%
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
