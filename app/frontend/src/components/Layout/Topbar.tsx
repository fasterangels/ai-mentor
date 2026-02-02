import { t } from "@/i18n";
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
        <span className="text-sm text-gray-500">{t("topbar.backend_label")}</span>
        {backendOnline === null ? (
          <span className="text-sm text-gray-400">{t("topbar.checking")}</span>
        ) : backendOnline ? (
          <span className="text-sm text-green-600 font-medium">{t("topbar.online")}</span>
        ) : (
          <span className="text-sm text-red-600 font-medium" title={t("topbar.offline_title")}>{t("topbar.offline_message")}</span>
        )}
      </div>
    </header>
  );
}
