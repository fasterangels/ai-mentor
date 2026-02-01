import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";
import App from "./App";
import { getBackendBaseUrl, isTauri } from "./api/backendBaseUrl";
import "./index.css";

function Root() {
  const [ready, setReady] = useState(!isTauri());
  useEffect(() => {
    if (!isTauri()) {
      setReady(true);
      return;
    }
    getBackendBaseUrl().then(() => setReady(true));
  }, []);
  if (!ready) {
    return (
      <div style={{ padding: 24, fontFamily: "system-ui" }}>
        Starting backend…
      </div>
    );
  }
  return <App />;
}

createRoot(document.getElementById("root")!).render(<Root />);
