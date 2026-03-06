import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Render app immediately; backend readiness is handled inside App (button disabled + "Starting backend..." state).
createRoot(document.getElementById("root")!).render(<App />);
