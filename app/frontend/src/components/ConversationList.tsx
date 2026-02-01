import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, Trash2, MessageSquare } from 'lucide-react';
import { apiClient } from '@/services/api';
import { Conversation } from '@/types';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface ConversationListProps {
  selectedId: number | null;
  onSelectConversation: (id: number | null) => void;
}

export function ConversationList({ selectedId, onSelectConversation }: ConversationListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const data = await apiClient.getConversations();
      setConversations(data);
    } catch (error) {
      toast.error('Σφάλμα φόρτωσης συνομιλιών');
      console.error(error);
    }
  };

  const handleCreateConversation = async () => {
    if (!newTitle.trim()) {
      toast.error('Δώσε τίτλο στη συνομιλία');
      return;
    }

    setIsCreating(true);
    try {
      const conversation = await apiClient.createConversation(newTitle);
      setConversations([conversation, ...conversations]);
      setNewTitle('');
      onSelectConversation(conversation.id);
      toast.success('Νέα συνομιλία δημιουργήθηκε');
    } catch (error) {
      toast.error('Σφάλμα δημιουργίας συνομιλίας');
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!confirm('Είσαι σίγουρος ότι θέλεις να διαγράψεις αυτή τη συνομιλία;')) {
      return;
    }

    try {
      await apiClient.deleteConversation(id);
      setConversations(conversations.filter((c) => c.id !== id));
      if (selectedId === id) {
        onSelectConversation(null);
      }
      toast.success('Η συνομιλία διαγράφηκε');
    } catch (error) {
      toast.error('Σφάλμα διαγραφής συνομιλίας');
      console.error(error);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <h2 className="font-semibold mb-3">Συνομιλίες</h2>
        <div className="flex gap-2">
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Τίτλος νέας συνομιλίας"
            onKeyDown={(e) => e.key === 'Enter' && handleCreateConversation()}
            disabled={isCreating}
          />
          <Button
            onClick={handleCreateConversation}
            disabled={isCreating}
            size="icon"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 ? (
          <div className="text-center text-gray-500 mt-8 px-4">
            <MessageSquare className="mx-auto h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">Δεν υπάρχουν συνομιλίες</p>
            <p className="text-xs mt-1">Δημιούργησε μια νέα για να ξεκινήσεις</p>
          </div>
        ) : (
          conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={cn(
                'p-3 rounded-lg mb-2 cursor-pointer group hover:bg-gray-100 transition-colors',
                selectedId === conversation.id && 'bg-blue-50 hover:bg-blue-100'
              )}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm truncate">
                    {conversation.title}
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(conversation.updated_at).toLocaleDateString('el-GR')}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8"
                  onClick={(e) => handleDeleteConversation(conversation.id, e)}
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}