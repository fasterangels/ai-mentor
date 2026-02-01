import type { PageTitle } from "@/types/ui";

interface TopbarProps {
  title: PageTitle;
  backendOnline: boolean | null;
}

export function Topbar({ title, backendOnline }: TopbarProps) {
  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-gray-800">{title}</h1>
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Backend:</span>
        {backendOnline === null ? (
          <span className="text-sm text-gray-400">Έλεγχος...</span>
        ) : backendOnline ? (
          <span className="text-sm text-green-600 font-medium">Online</span>
        ) : (
          <span className="text-sm text-red-600 font-medium" title="Backend is not running. Please reinstall.">Offline — Backend is not running. Please reinstall.</span>
        )}
      </div>
    </header>
  );
}
