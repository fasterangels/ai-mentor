const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

export interface AnalyzeMatchResponse {
  match: { match_id: string; home: string; away: string; league?: string; kickoff_iso?: string };
  analysis: Record<string, unknown>;
}

export interface AnalyzeMatchError {
  error: string;
}

export async function analyzeFootballMatch(query: string): Promise<AnalyzeMatchResponse | AnalyzeMatchError> {
  const res = await fetch(`${BASE_URL}/football/analyze_match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: query.trim() }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail ?? `HTTP ${res.status}`);
  return data as AnalyzeMatchResponse | AnalyzeMatchError;
}
