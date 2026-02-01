import { Button } from "@/components/ui/button";
import { 
  BarChart3, 
  TrendingUp, 
  Calendar, 
  History,
  CheckCircle2
} from "lucide-react";

interface AnalyticsSidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

export default function AnalyticsSidebar({ activeView, onViewChange }: AnalyticsSidebarProps) {
  const views = [
    { id: "predictions", label: "Προβλέψεις", icon: CheckCircle2 },
    { id: "results", label: "Αποτελέσματα", icon: BarChart3 },
    { id: "statistics", label: "Στατιστικά Απόδοσης", icon: TrendingUp },
    { id: "weekly", label: "Εβδομαδιαία Σύνοψη", icon: Calendar },
    { id: "history", label: "Ιστορικό Αγώνων", icon: History }
  ];

  return (
    <div className="w-64 bg-card border-r border-border p-4 space-y-2">
      <h2 className="text-lg font-semibold mb-4 px-2">Ανάλυση</h2>
      {views.map((view) => {
        const Icon = view.icon;
        return (
          <Button
            key={view.id}
            variant={activeView === view.id ? "default" : "ghost"}
            className="w-full justify-start"
            onClick={() => onViewChange(view.id)}
          >
            <Icon className="mr-2 h-4 w-4" />
            {view.label}
          </Button>
        );
      })}
    </div>
  );
}