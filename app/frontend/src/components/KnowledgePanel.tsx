import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Plus, Trash2, Edit2, Save, X } from 'lucide-react';
import { apiClient } from '@/services/api';
import { Knowledge } from '@/types';
import { toast } from 'sonner';

export function KnowledgePanel() {
  const [knowledgeList, setKnowledgeList] = useState<Knowledge[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    title: '',
    summary: '',
    content: '',
    tags: '',
    sources: '',
  });

  useEffect(() => {
    loadKnowledge();
  }, []);

  const loadKnowledge = async () => {
    try {
      const data = await apiClient.getKnowledge();
      setKnowledgeList(data);
    } catch (error) {
      toast.error('Σφάλμα φόρτωσης γνώσης');
      console.error(error);
    }
  };

  const handleCreate = async () => {
    if (!formData.title.trim() || !formData.summary.trim()) {
      toast.error('Συμπλήρωσε τίτλο και σύνοψη');
      return;
    }

    try {
      await apiClient.createKnowledge(
        formData.title,
        formData.summary,
        formData.content,
        formData.tags,
        formData.sources
      );
      await loadKnowledge();
      setFormData({ title: '', summary: '', content: '', tags: '', sources: '' });
      setIsCreating(false);
      toast.success('Η γνώση αποθηκεύτηκε');
    } catch (error) {
      toast.error('Σφάλμα αποθήκευσης γνώσης');
      console.error(error);
    }
  };

  const handleUpdate = async (id: number) => {
    try {
      await apiClient.updateKnowledge(
        id,
        formData.title,
        formData.summary,
        formData.content,
        formData.tags,
        formData.sources
      );
      await loadKnowledge();
      setEditingId(null);
      setFormData({ title: '', summary: '', content: '', tags: '', sources: '' });
      toast.success('Η γνώση ενημερώθηκε');
    } catch (error) {
      toast.error('Σφάλμα ενημέρωσης γνώσης');
      console.error(error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Είσαι σίγουρος ότι θέλεις να διαγράψεις αυτή τη γνώση;')) {
      return;
    }

    try {
      await apiClient.deleteKnowledge(id);
      await loadKnowledge();
      toast.success('Η γνώση διαγράφηκε');
    } catch (error) {
      toast.error('Σφάλμα διαγραφής γνώσης');
      console.error(error);
    }
  };

  const startEdit = (knowledge: Knowledge) => {
    setEditingId(knowledge.id);
    setFormData({
      title: knowledge.title,
      summary: knowledge.summary,
      content: knowledge.content || '',
      tags: knowledge.tags,
      sources: knowledge.sources || '',
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setIsCreating(false);
    setFormData({ title: '', summary: '', content: '', tags: '', sources: '' });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Γνώση / Έρευνα</h2>
          <Button
            onClick={() => setIsCreating(true)}
            size="sm"
            disabled={isCreating}
          >
            <Plus className="h-4 w-4 mr-2" />
            Νέα Γνώση
          </Button>
        </div>
        <p className="text-xs text-gray-500">
          Αποθηκεύει πληροφορίες και συμπεράσματα από έρευνες
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isCreating && (
          <div className="border rounded-lg p-4 bg-blue-50">
            <h3 className="font-medium mb-3">Νέα Γνώση</h3>
            <Input
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="Τίτλος"
              className="mb-3"
            />
            <Textarea
              value={formData.summary}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              placeholder="Σύνοψη..."
              className="mb-3"
            />
            <Textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              placeholder="Περιεχόμενο (προαιρετικό)..."
              className="mb-3"
            />
            <Input
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              placeholder="Tags (διαχωρισμένα με κόμμα)"
              className="mb-3"
            />
            <Input
              value={formData.sources}
              onChange={(e) => setFormData({ ...formData, sources: e.target.value })}
              placeholder="Πηγές (προαιρετικό)"
              className="mb-3"
            />
            <div className="flex gap-2">
              <Button onClick={handleCreate} size="sm">
                <Save className="h-4 w-4 mr-2" />
                Αποθήκευση
              </Button>
              <Button onClick={cancelEdit} variant="outline" size="sm">
                <X className="h-4 w-4 mr-2" />
                Ακύρωση
              </Button>
            </div>
          </div>
        )}

        {knowledgeList.map((knowledge) => (
          <div key={knowledge.id} className="border rounded-lg p-4 bg-white">
            {editingId === knowledge.id ? (
              <>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Τίτλος"
                  className="mb-3"
                />
                <Textarea
                  value={formData.summary}
                  onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                  placeholder="Σύνοψη"
                  className="mb-3"
                />
                <Textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  placeholder="Περιεχόμενο"
                  className="mb-3"
                />
                <Input
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="Tags"
                  className="mb-3"
                />
                <Input
                  value={formData.sources}
                  onChange={(e) => setFormData({ ...formData, sources: e.target.value })}
                  placeholder="Πηγές"
                  className="mb-3"
                />
                <div className="flex gap-2">
                  <Button onClick={() => handleUpdate(knowledge.id)} size="sm">
                    <Save className="h-4 w-4 mr-2" />
                    Αποθήκευση
                  </Button>
                  <Button onClick={cancelEdit} variant="outline" size="sm">
                    <X className="h-4 w-4 mr-2" />
                    Ακύρωση
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-medium mb-1">{knowledge.title}</h3>
                    <p className="text-sm text-gray-700 mb-2">{knowledge.summary}</p>
                    {knowledge.content && (
                      <p className="text-xs text-gray-600 whitespace-pre-wrap mb-2">
                        {knowledge.content}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-1 ml-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => startEdit(knowledge)}
                      className="h-8 w-8"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(knowledge.id)}
                      className="h-8 w-8"
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                  {knowledge.tags && <span>Tags: {knowledge.tags}</span>}
                  {knowledge.sources && <span>Πηγές: {knowledge.sources}</span>}
                  <span>{new Date(knowledge.created_at).toLocaleDateString('el-GR')}</span>
                </div>
              </>
            )}
          </div>
        ))}

        {knowledgeList.length === 0 && !isCreating && (
          <div className="text-center text-gray-500 mt-8">
            <p>Δεν υπάρχει γνώση</p>
            <p className="text-xs mt-1">Δημιούργησε νέες εγγραφές για να αποθηκεύσεις πληροφορίες</p>
          </div>
        )}
      </div>
    </div>
  );
}