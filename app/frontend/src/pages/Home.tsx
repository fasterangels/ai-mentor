import { PlusCircle, FileResult, BarChart3, History } from "lucide-react";
import { NavCard } from "@/components/Cards/NavCard";

export function Home() {
  return (
    <div className="space-y-6">
      <p className="text-gray-600">
        Επιλέξτε μια ενέργεια από τις κάρτες παρακάτω.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <NavCard
          title="Νέα Πρόβλεψη"
          description="Εκτέλεση νέας ανάλυσης αγώνα"
          to="/new-prediction"
          icon={<PlusCircle size={24} />}
        />
        <NavCard
          title="Αποτέλεσμα Πρόβλεψης"
          description="Προβολή αποτελέσματος τελευταίας ανάλυσης"
          to="/prediction-result"
          icon={<FileResult size={24} />}
        />
        <NavCard
          title="Σύνοψη Απόδοσης"
          description="ΚΠΙ ανά ημέρα, εβδομάδα, μήνα"
          to="/performance"
          icon={<BarChart3 size={24} />}
        />
        <NavCard
          title="Ιστορικό Προβλέψεων"
          description="Λίστα αξιολογημένων προβλέψεων"
          to="/history"
          icon={<History size={24} />}
        />
      </div>
    </div>
  );
}
