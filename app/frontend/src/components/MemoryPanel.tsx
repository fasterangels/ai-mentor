import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Slider } from '@/components/ui/slider';
import { Plus, Trash2, Edit2, Save, X } from 'lucide-react';
import { apiClient } from '@/services/api';
import { Memory } from '@/types';
import { toast } from 'sonner';

export function MemoryPanel() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    content: '',
    importance: 0.5,
    tags: '',
  });

  useEffect(() => {
    loadMemories();
  }, []);

  const loadMemories = async () => {
    try {
      const data = await apiClient.getMemories();
      setMemories(data);
    } catch (error) {
      toast.error('Σφάλμα φόρτωσης μνημών');
      console.error(error);
    }
  };

  const handleCreate = async () => {
    if (!formData.content.trim()) {
      toast.error('Η μνήμη δεν μπορεί να είναι κενή');
      return;
    }

    try {
      await apiClient.createMemory(formData.content, formData.importance, formData.tags);
      await loadMemories();
      setFormData({ content: '', importance: 0.5, tags: '' });
      setIsCreating(false);
      toast.success('Η μνήμη αποθηκεύτηκε');
    } catch (error) {
      toast.error('Σφάλμα αποθήκευσης μνήμης');
      console.error(error);
    }
  };

  const handleUpdate = async (id: number) => {
    try {
      await apiClient.updateMemory(id, formData.content, formData.importance, formData.tags);
      await loadMemories();
      setEditingId(null);
      setFormData({ content: '', importance: 0.5, tags: '' });
      toast.success('Η μνήμη ενημερώθηκε');
    } catch (error) {
      toast.error('Σφάλμα ενημέρωσης μνήμης');
      console.error(error);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Είσαι σίγουρος ότι θέλεις να διαγράψεις αυτή τη μνήμη;')) {
      return;
    }

    try {
      await apiClient.deleteMemory(id);
      await loadMemories();
      toast.success('Η μνήμη διαγράφηκε');
    } catch (error) {
      toast.error('Σφάλμα διαγραφής μνήμης');
      console.error(error);
    }
  };

  const startEdit = (memory: Memory) => {
    setEditingId(memory.id);
    setFormData({
      content: memory.content,
      importance: memory.importance,
      tags: memory.tags,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setIsCreating(false);
    setFormData({ content: '', importance: 0.5, tags: '' });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Μνήμη Χρήστη</h2>
          <Button
            onClick={() => setIsCreating(true)}
            size="sm"
            disabled={isCreating}
          >
            <Plus className="h-4 w-4 mr-2" />
            Νέα Μνήμη
          </Button>
        </div>
        <p className="text-xs text-gray-500">
          Αποθηκεύει σημαντικές πληροφορίες για εσένα
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isCreating && (
          <div className="border rounded-lg p-4 bg-blue-50">
            <h3 className="font-medium mb-3">Νέα Μνήμη</h3>
            <Textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              placeholder="Περιγραφή μνήμης..."
              className="mb-3"
            />
            <div className="mb-3">
              <label className="text-sm font-medium mb-2 block">
                Σημαντικότητα: {formData.importance.toFixed(1)}
              </label>
              <Slider
                value={[formData.importance]}
                onValueChange={([value]) => setFormData({ ...formData, importance: value })}
                min={0}
                max={1}
                step={0.1}
              />
            </div>
            <Input
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              placeholder="Tags (διαχωρισμένα με κόμμα)"
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

        {memories.map((memory) => (
          <div key={memory.id} className="border rounded-lg p-4 bg-white">
            {editingId === memory.id ? (
              <>
                <Textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  className="mb-3"
                />
                <div className="mb-3">
                  <label className="text-sm font-medium mb-2 block">
                    Σημαντικότητα: {formData.importance.toFixed(1)}
                  </label>
                  <Slider
                    value={[formData.importance]}
                    onValueChange={([value]) => setFormData({ ...formData, importance: value })}
                    min={0}
                    max={1}
                    step={0.1}
                  />
                </div>
                <Input
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="Tags"
                  className="mb-3"
                />
                <div className="flex gap-2">
                  <Button onClick={() => handleUpdate(memory.id)} size="sm">
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
                    <p className="text-sm whitespace-pre-wrap">{memory.content}</p>
                  </div>
                  <div className="flex gap-1 ml-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => startEdit(memory)}
                      className="h-8 w-8"
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(memory.id)}
                      className="h-8 w-8"
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span>Σημαντικότητα: {memory.importance.toFixed(1)}</span>
                  {memory.tags && <span>Tags: {memory.tags}</span>}
                  <span>{new Date(memory.created_at).toLocaleDateString('el-GR')}</span>
                </div>
              </>
            )}
          </div>
        ))}

        {memories.length === 0 && !isCreating && (
          <div className="text-center text-gray-500 mt-8">
            <p>Δεν υπάρχουν μνήμες</p>
            <p className="text-xs mt-1">Δημιούργησε νέες για να αποθηκεύσεις σημαντικές πληροφορίες</p>
          </div>
        )}
      </div>
    </div>
  );
}