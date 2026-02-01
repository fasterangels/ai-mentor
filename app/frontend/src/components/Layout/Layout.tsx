import { useState, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { getHealth } from "@/api/client";
import { isTauri } from "@/api/backendBaseUrl";
import type { PageTitle } from "@/types/ui";

const pathToTitle: Record<string, PageTitle> = {
  "/": "Αρχική",
  "/new-prediction": "Νέα Πρόβλεψη",
  "/prediction-result": "Αποτέλεσμα Πρόβλεψης",
  "/performance": "Σύνοψη Απόδοσης",
  "/history": "Ιστορικό Προβλέψεων",
  "/settings": "Ρυθμίσεις",
};

export function Layout() {
  const location = useLocation();
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tryHealth = () =>
      getHealth()
        .then(() => { if (!cancelled) setBackendOnline(true); })
        .catch(async () => {
          if (cancelled) return;
          if (isTauri()) {
            try {
              const { invoke } = await import("@tauri-apps/api/core");
              await invoke("run_backend_task");
              await new Promise((r) => setTimeout(r, 10000));
              if (cancelled) return;
              await getHealth();
              if (!cancelled) setBackendOnline(true);
            } catch {
              if (!cancelled) setBackendOnline(false);
            }
          } else {
            setBackendOnline(false);
          }
        });
    tryHealth();
    return () => { cancelled = true; };
  }, []);

  const title = pathToTitle[location.pathname] ?? "Αρχική";

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col pl-56">
        <Topbar title={title} backendOnline={backendOnline} />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
