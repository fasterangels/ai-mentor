import { useState, useEffect } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { Button } from '@/components/ui/button';
import { FileText, Loader2 } from 'lucide-react';
import { apiClient } from '@/services/api';
import { Message } from '@/types';
import { toast } from 'sonner';

interface ChatInterfaceProps {
  conversationId: number | null;
}

export function ChatInterface({ conversationId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);

  useEffect(() => {
    if (conversationId) {
      loadMessages();
    } else {
      setMessages([]);
    }
  }, [conversationId]);

  const loadMessages = async () => {
    if (!conversationId) return;
    
    try {
      const msgs = await apiClient.getMessages(conversationId);
      setMessages(msgs);
    } catch (error) {
      toast.error('Σφάλμα φόρτωσης μηνυμάτων');
      console.error(error);
    }
  };

  const handleSendMessage = async (content: string, useOnline: boolean) => {
    if (!conversationId) {
      toast.error('Επίλεξε ή δημιούργησε μια συνομιλία πρώτα');
      return;
    }

    setIsLoading(true);
    try {
      const newMessage = await apiClient.sendMessage(conversationId, content, useOnline);
      await loadMessages();
      
      if (newMessage.used_online) {
        toast.info('Χρησιμοποιήθηκε online βοήθεια για αυτό το μήνυμα');
      }
    } catch (error) {
      toast.error('Σφάλμα αποστολής μηνύματος');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!conversationId || messages.length === 0) {
      toast.error('Δεν υπάρχουν μηνύματα για σύνοψη');
      return;
    }

    setIsSummarizing(true);
    try {
      const result = await apiClient.generateSummary(conversationId);
      
      // Add summary as a system message
      setMessages([...messages, {
        id: Date.now(),
        conversation_id: conversationId,
        role: 'system',
        content: `📋 **Σύνοψη Συνομιλίας**\n\n${result.summary}`,
        thinking_state: 'offline',
        used_online: false,
        created_at: new Date().toISOString(),
      }]);
      
      toast.success('Η σύνοψη δημιουργήθηκε επιτυχώς');
    } catch (error) {
      toast.error('Σφάλμα δημιουργίας σύνοψης');
      console.error(error);
    } finally {
      setIsSummarizing(false);
    }
  };

  if (!conversationId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <MessageSquare className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Καλώς ήρθες στον AI Μέντορα
          </h3>
          <p className="text-gray-500">
            Επίλεξε μια συνομιλία ή δημιούργησε νέα για να ξεκινήσεις
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-50">
      <div className="border-b bg-white px-4 py-3 flex items-center justify-between">
        <h2 className="font-semibold text-gray-900">Συνομιλία</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={handleGenerateSummary}
          disabled={isSummarizing || messages.length === 0}
        >
          {isSummarizing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileText className="mr-2 h-4 w-4" />
          )}
          Σύνοψη μέχρι εδώ
        </Button>
      </div>
      
      <MessageList messages={messages} />
      
      <MessageInput
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
      />
    </div>
  );
}

function MessageSquare({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
      />
    </svg>
  );
}