import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  PlusCircle,
  FileResult,
  BarChart3,
  History,
  Settings,
} from "lucide-react";
import type { NavItem } from "@/types/ui";

const navItems: NavItem[] = [
  { path: "/", label: "Αρχική", icon: "dashboard" },
  { path: "/new-prediction", label: "Νέα Πρόβλεψη", icon: "new" },
  { path: "/prediction-result", label: "Αποτέλεσμα Πρόβλεψης", icon: "result" },
  { path: "/performance", label: "Σύνοψη Απόδοσης", icon: "performance" },
  { path: "/history", label: "Ιστορικό Προβλέψεων", icon: "history" },
  { path: "/settings", label: "Ρυθμίσεις", icon: "settings" },
];

const iconMap: Record<string, React.ReactNode> = {
  dashboard: <LayoutDashboard size={20} />,
  new: <PlusCircle size={20} />,
  result: <FileResult size={20} />,
  performance: <BarChart3 size={20} />,
  history: <History size={20} />,
  settings: <Settings size={20} />,
};

export function Sidebar() {
  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col fixed left-0 top-0 bottom-0 z-10">
      <div className="p-4 border-b border-gray-200">
        <span className="font-semibold text-gray-800">Ανάλυση Αγώνων</span>
      </div>
      <nav className="flex-1 p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm ${
                isActive
                  ? "bg-gray-100 text-gray-900 font-medium"
                  : "text-gray-600 hover:bg-gray-50"
              }`
            }
          >
            {item.icon && iconMap[item.icon]}
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
