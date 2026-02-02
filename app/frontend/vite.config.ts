import path from "path"
import { readFileSync } from "fs"
import { fileURLToPath } from "url"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const pkg = JSON.parse(
  readFileSync(path.resolve(__dirname, "package.json"), "utf-8")
)

export default defineConfig({
  plugins: [react()],
  define: {
    __BUILD__: JSON.stringify(process.env.VITE_BUILD ?? "dev"),
    __COMMIT__: JSON.stringify(process.env.VITE_COMMIT ?? "unknown"),
    __APP_VERSION__: JSON.stringify(process.env.VITE_APP_VERSION ?? pkg.version ?? "0.0.0"),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  build: {
    rollupOptions: {
      external: [
        "@tauri-apps/plugin-fs",
        "@tauri-apps/plugin-dialog",
        "jspdf"
      ]
    }
  }
})