import { Button } from "@/components/ui/button";
import { 
  MessageSquare, 
  Brain, 
  BookOpen, 
  Settings,
  BarChart3
} from "lucide-react";

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  const menuItems = [
    { id: 'conversations', label: 'Συνομιλίες', icon: MessageSquare },
    { id: 'analytics', label: 'Ανάλυση', icon: BarChart3 },
    { id: 'memory', label: 'Μνήμη', icon: Brain },
    { id: 'knowledge', label: 'Γνώση', icon: BookOpen },
    { id: 'settings', label: 'Ρυθμίσεις', icon: Settings },
  ];

  return (
    <div className="w-16 bg-gray-900 flex flex-col items-center py-4 space-y-4">
      <div className="text-white font-bold text-xl mb-4">AI</div>
      
      {menuItems.map((item) => {
        const Icon = item.icon;
        return (
          <Button
            key={item.id}
            variant={activeView === item.id ? "secondary" : "ghost"}
            size="icon"
            className={`w-12 h-12 ${
              activeView === item.id 
                ? 'bg-white text-gray-900 hover:bg-gray-100' 
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
            onClick={() => onViewChange(item.id)}
            title={item.label}
          >
            <Icon className="h-5 w-5" />
          </Button>
        );
      })}
    </div>
  );
}