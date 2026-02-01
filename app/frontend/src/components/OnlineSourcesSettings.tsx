import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Edit, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useBackendBaseUrl } from "@/hooks/useBackendBaseUrl";

interface DataSource {
  id: number;
  name: string;
  url: string;
  category: string;
  reliability_score: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

const CATEGORIES = {
  fixtures: "Πρόγραμμα Αγώνων",
  news: "Νέα/Απουσίες",
  statistics: "Στατιστικά",
  odds: "Αποδόσεις"
};

const RELIABILITY_COLORS = {
  1.0: "bg-green-500 hover:bg-green-600",
  0.8: "bg-yellow-500 hover:bg-yellow-600",
  0.6: "bg-orange-500 hover:bg-orange-600"
};

export default function OnlineSourcesSettings() {
  const { apiBase, loading: baseLoading, error: baseError } = useBackendBaseUrl();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("fixtures");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [deleteSourceId, setDeleteSourceId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    url: "",
    category: "fixtures",
    reliability_score: 1.0,
    active: true
  });

  useEffect(() => {
    if (!apiBase) return;
    fetchSources();
  }, [selectedCategory, apiBase]);

  const fetchSources = async () => {
    if (!apiBase) return;
    try {
      const response = await fetch(
        `${apiBase}/api/v1/sources?category=${selectedCategory}`
      );
      const data = await response.json();
      setSources(data);
    } catch (error) {
      console.error("Error fetching sources:", error);
      toast.error("Σφάλμα φόρτωσης πηγών");
    } finally {
      setLoading(false);
    }
  };

  const handleAddSource = async () => {
    if (!apiBase) return;
    try {
      const response = await fetch(`${apiBase}/api/v1/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        toast.success("Η πηγή προστέθηκε επιτυχώς");
        setIsAddDialogOpen(false);
        resetForm();
        fetchSources();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Σφάλμα προσθήκης πηγής");
      }
    } catch (error) {
      console.error("Error adding source:", error);
      toast.error("Σφάλμα προσθήκης πηγής");
    }
  };

  const handleUpdateSource = async () => {
    if (!editingSource || !apiBase) return;

    try {
      const response = await fetch(
        `${apiBase}/api/v1/sources/${editingSource.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(formData)
        }
      );

      if (response.ok) {
        toast.success("Η πηγή ενημερώθηκε επιτυχώς");
        setEditingSource(null);
        resetForm();
        fetchSources();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Σφάλμα ενημέρωσης πηγής");
      }
    } catch (error) {
      console.error("Error updating source:", error);
      toast.error("Σφάλμα ενημέρωσης πηγής");
    }
  };

  const handleDeleteSource = async () => {
    if (!deleteSourceId || !apiBase) return;

    try {
      const response = await fetch(
        `${apiBase}/api/v1/sources/${deleteSourceId}`,
        { method: "DELETE" }
      );

      if (response.ok) {
        toast.success("Η πηγή διαγράφηκε επιτυχώς");
        setDeleteSourceId(null);
        fetchSources();
      } else {
        toast.error("Σφάλμα διαγραφής πηγής");
      }
    } catch (error) {
      console.error("Error deleting source:", error);
      toast.error("Σφάλμα διαγραφής πηγής");
    }
  };

  const handleToggleActive = async (id: number) => {
    if (!apiBase) return;
    try {
      const response = await fetch(
        `${apiBase}/api/v1/sources/${id}/toggle`,
        { method: "PATCH" }
      );

      if (response.ok) {
        fetchSources();
      } else {
        toast.error("Σφάλμα αλλαγής κατάστασης");
      }
    } catch (error) {
      console.error("Error toggling source:", error);
      toast.error("Σφάλμα αλλαγής κατάστασης");
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      url: "",
      category: "fixtures",
      reliability_score: 1.0,
      active: true
    });
  };

  const openEditDialog = (source: DataSource) => {
    setEditingSource(source);
    setFormData({
      name: source.name,
      url: source.url,
      category: source.category,
      reliability_score: source.reliability_score,
      active: source.active
    });
  };

  const closeEditDialog = () => {
    setEditingSource(null);
    resetForm();
  };

  if (baseLoading || loading) {
    return <div className="p-6">Φόρτωση...</div>;
  }
  if (baseError) {
    return <div className="p-6 text-destructive">Σφάλμα backend: {baseError}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Online Πηγές</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Διαχείριση πηγών δεδομένων για προβλέψεις
          </p>
        </div>
        <Button onClick={() => setIsAddDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Προσθήκη Πηγής
        </Button>
      </div>

      {/* Category Tabs */}
      <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="fixtures">Πρόγραμμα Αγώνων</TabsTrigger>
          <TabsTrigger value="news">Νέα/Απουσίες</TabsTrigger>
          <TabsTrigger value="statistics">Στατιστικά</TabsTrigger>
          <TabsTrigger value="odds">Αποδόσεις</TabsTrigger>
        </TabsList>

        <TabsContent value={selectedCategory} className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sources.map((source) => (
              <Card key={source.id} className={!source.active ? "opacity-50" : ""}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{source.name}</CardTitle>
                      <CardDescription className="text-xs mt-1 break-all">
                        {source.url}
                      </CardDescription>
                    </div>
                    <Badge
                      className={`ml-2 ${
                        RELIABILITY_COLORS[source.reliability_score as keyof typeof RELIABILITY_COLORS]
                      }`}
                    >
                      {source.reliability_score}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={source.active}
                        onCheckedChange={() => handleToggleActive(source.id)}
                      />
                      <span className="text-sm">
                        {source.active ? "Ενεργή" : "Ανενεργή"}
                      </span>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(source)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setDeleteSourceId(source.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {sources.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              Δεν υπάρχουν πηγές σε αυτή την κατηγορία
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Add/Edit Dialog */}
      <Dialog
        open={isAddDialogOpen || editingSource !== null}
        onOpenChange={(open) => {
          if (!open) {
            setIsAddDialogOpen(false);
            closeEditDialog();
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingSource ? "Επεξεργασία Πηγής" : "Προσθήκη Πηγής"}
            </DialogTitle>
            <DialogDescription>
              Συμπληρώστε τα στοιχεία της πηγής δεδομένων
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Όνομα</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="π.χ. Football-Data.org"
              />
            </div>

            <div>
              <Label htmlFor="url">URL</Label>
              <Input
                id="url"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                placeholder="https://..."
              />
            </div>

            <div>
              <Label htmlFor="category">Κατηγορία</Label>
              <Select
                value={formData.category}
                onValueChange={(value) => setFormData({ ...formData, category: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CATEGORIES).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="reliability">Αξιοπιστία</Label>
              <Select
                value={formData.reliability_score.toString()}
                onValueChange={(value) =>
                  setFormData({ ...formData, reliability_score: parseFloat(value) })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1.0">1.0 (Υψηλή)</SelectItem>
                  <SelectItem value="0.8">0.8 (Μέτρια)</SelectItem>
                  <SelectItem value="0.6">0.6 (Χαμηλή)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                checked={formData.active}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, active: checked })
                }
              />
              <Label>Ενεργή</Label>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsAddDialogOpen(false);
                closeEditDialog();
              }}
            >
              Ακύρωση
            </Button>
            <Button
              onClick={editingSource ? handleUpdateSource : handleAddSource}
            >
              {editingSource ? "Ενημέρωση" : "Προσθήκη"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteSourceId !== null}
        onOpenChange={(open) => !open && setDeleteSourceId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Διαγραφή Πηγής</AlertDialogTitle>
            <AlertDialogDescription>
              Είστε σίγουροι ότι θέλετε να διαγράψετε αυτή την πηγή; Αυτή η ενέργεια
              δεν μπορεί να αναιρεθεί.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Ακύρωση</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteSource}>
              Διαγραφή
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}