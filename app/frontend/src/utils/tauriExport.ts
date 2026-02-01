// tauriExport.ts — Tauri-only helpers (never imported by Vite at build time)

export async function saveJsonFile(path: string, contents: string) {
  const { writeFile } = await import(/* @vite-ignore */ "@tauri-apps/plugin-fs");
  await writeFile(path, contents);
}

export async function savePdfFile(path: string, bytes: Uint8Array) {
  const { writeFile } = await import(/* @vite-ignore */ "@tauri-apps/plugin-fs");
  await writeFile(path, bytes);
}

export async function openSaveDialog(defaultPath: string, filters: { name: string; extensions: string[] }[]) {
  const { save } = await import(/* @vite-ignore */ "@tauri-apps/plugin-dialog");
  return await save({
    defaultPath,
    filters,
  });
}
