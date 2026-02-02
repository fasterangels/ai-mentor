import { useState } from 'react';
import { t } from '@/i18n';
import { useOllama } from '@/hooks/useOllama';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import OnlineSourcesSettings from './OnlineSourcesSettings';

export function SettingsPanel() {
  const { isConnected, isChecking, refresh } = useOllama();
  const [activeTab, setActiveTab] = useState("general");

  return (
    <div className="flex-1 overflow-auto bg-gray-50">
      <div className="p-6">
        <h2 className="text-2xl font-bold mb-6">Ρυθμίσεις</h2>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="general">Γενικά</TabsTrigger>
            <TabsTrigger value="sources">Online Πηγές</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="mt-6">
            <div className="space-y-6">
              <div className="border rounded-lg p-4 bg-white">
                <h3 className="font-semibold mb-3">Κατάσταση Συστήματος</h3>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Ollama (Local AI)</span>
                    <div className="flex items-center gap-2">
                      {isChecking ? (
                        <span className="text-sm text-gray-500">Έλεγχος...</span>
                      ) : isConnected ? (
                        <>
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                          <span className="text-sm text-green-600">Συνδεδεμένο</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-5 w-5 text-red-500" />
                          <span className="text-sm text-red-600">Αποσυνδεδεμένο</span>
                        </>
                      )}
                    </div>
                  </div>

                  <Button
                    onClick={refresh}
                    variant="outline"
                    size="sm"
                    disabled={isChecking}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${isChecking ? 'animate-spin' : ''}`} />
                    Ανανέωση Κατάστασης
                  </Button>
                </div>
              </div>

              <div className="border rounded-lg p-4 bg-white">
                <h3 className="font-semibold mb-3">Πληροφορίες</h3>
                <div className="space-y-2 text-sm text-gray-600">
                  <p><strong>Μοντέλο:</strong> llama3:latest</p>
                  <p><strong>{t("settings.backend_value")}</strong> http://127.0.0.1:8000</p>
                  <p><strong>Frontend:</strong> http://localhost:3000</p>
                  <p><strong>Ollama:</strong> http://127.0.0.1:11434</p>
                </div>
              </div>

              <div className="border rounded-lg p-4 bg-blue-50">
                <h3 className="font-semibold mb-2">Λειτουργία Online</h3>
                <p className="text-sm text-gray-700">
                  Το Online mode είναι απενεργοποιημένο by default. Ενεργοποίησέ το μόνο όταν χρειάζεσαι
                  online βοήθεια για ένα συγκεκριμένο μήνυμα. Μετά την αποστολή, απενεργοποιείται αυτόματα.
                </p>
                <p className="text-xs text-gray-500 mt-2">
                  Για να χρησιμοποιήσεις ChatGPT API, όρισε το OPENAI_API_KEY στις μεταβλητές περιβάλλοντος.
                </p>
              </div>

              <div className="border rounded-lg p-4 bg-white">
                <h3 className="font-semibold mb-2">Ιδιωτικότητα</h3>
                <p className="text-sm text-gray-700">
                  Όλα τα δεδομένα αποθηκεύονται τοπικά στη συσκευή σου. Το AI τρέχει offline by default.
                  Online λειτουργίες ενεργοποιούνται μόνο με τη ρητή σου εντολή.
                </p>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="sources" className="mt-6">
            <OnlineSourcesSettings />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}