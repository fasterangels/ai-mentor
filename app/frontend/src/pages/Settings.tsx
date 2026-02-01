import { getBaseUrl } from "@/api/client";

export function Settings() {
  return (
    <div className="max-w-xl space-y-6">
      <section className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">
          Backend URL
        </h2>
        <p className="text-sm text-gray-700 font-mono bg-gray-50 p-2 rounded">
          {getBaseUrl()}
        </p>
        <p className="text-xs text-gray-500 mt-1">Μόνο για ανάγνωση (MVP).</p>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">
          Έκδοση
        </h2>
        <p className="text-sm text-gray-700">Frontend MVP · analyzer_v1</p>
      </section>
      <section className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-500 uppercase mb-2">
          Πολιτικές
        </h2>
        <p className="text-sm text-gray-500">
          Θα προστεθούν σε μελλοντική έκδοση.
        </p>
      </section>
    </div>
  );
}
