import { useState, useEffect } from "react";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI__" in window;
}

const FIXED_BASE = "http://127.0.0.1:8000";

export function useBackendBaseUrl(): {
  apiBase: string;
  loading: boolean;
  error: string | null;
} {
  const [apiBase, setApiBase] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isTauri()) {
      setApiBase(import.meta.env.VITE_BACKEND_BASE_URL || FIXED_BASE);
      setLoading(false);
      return;
    }
    let cancelled = false;
    import("@tauri-apps/api/core")
      .then(({ invoke }) => invoke<string>("get_backend_base_url"))
      .then((url) => {
        if (!cancelled) {
          setApiBase(url && typeof url === "string" ? url : FIXED_BASE);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiBase(FIXED_BASE);
          setError(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { apiBase: apiBase || FIXED_BASE, loading, error };
}
