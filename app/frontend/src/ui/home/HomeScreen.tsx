/**
 * Home screen (Αρχική) — welcome header + 2x2 action cards. PURE UI; buttons placeholder.
 */
import HomeActionCard from "./HomeActionCard";

const WELCOME_TITLE = "Καλώς ήρθες στο AI Μέντορας";
const WELCOME_SUBTITLE = "Επίλεξε μια ενέργεια για να ξεκινήσεις.";

export default function HomeScreen() {
  return (
    <div className="ai-home">
      <header className="ai-home-header">
        <h2 className="ai-home-title">{WELCOME_TITLE}</h2>
        <p className="ai-home-subtitle">{WELCOME_SUBTITLE}</p>
      </header>
      <div className="ai-home-grid">
        <HomeActionCard
          title="Νέα Πρόβλεψη"
          description="Δημιούργησε νέα ανάλυση αγώνα με ομάδες και παράθυρο kickoff."
          buttonLabel="Νέα Πρόβλεψη"
          primary
          onClick={() => {}}
        />
        <HomeActionCard
          title="Αποτέλεσμα Πρόβλεψης"
          description="Δες το τελευταίο αποτέλεσμα ανάλυσης και αποφάσεις αγορών."
          buttonLabel="Άνοιγμα αποτελέσματος"
          onClick={() => {}}
        />
        <HomeActionCard
          title="Σύνοψη Απόδοσης"
          description="Συνοπτικά KPIs και στατιστικά από τις προβλέψεις σου."
          buttonLabel="Άνοιγμα σύνοψης"
          onClick={() => {}}
        />
        <HomeActionCard
          title="Ιστορικό Προβλέψεων"
          description="Λίστα προηγούμενων αναλύσεων και αποτελεσμάτων."
          buttonLabel="Άνοιγμα ιστορικού"
          onClick={() => {}}
        />
      </div>
    </div>
  );
}
