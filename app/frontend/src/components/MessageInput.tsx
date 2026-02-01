import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Mic, Globe } from 'lucide-react';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface MessageInputProps {
  onSendMessage: (content: string, useOnline: boolean) => void;
  isLoading: boolean;
}

export function MessageInput({ onSendMessage, isLoading }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [useOnline, setUseOnline] = useState(false);
  const {
    isListening,
    transcript,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition();

  useEffect(() => {
    if (transcript) {
      setMessage((prev) => (prev ? `${prev} ${transcript}` : transcript));
      resetTranscript();
    }
  }, [transcript, resetTranscript]);

  const handleSubmit = () => {
    if (!message.trim() || isLoading) return;

    onSendMessage(message, useOnline);
    setMessage('');
    
    // Reset online toggle after sending
    if (useOnline) {
      setUseOnline(false);
      toast.info('Online mode απενεργοποιήθηκε αυτόματα');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleOnline = () => {
    setUseOnline(!useOnline);
    toast.info(
      !useOnline
        ? 'Online mode ενεργοποιήθηκε για το επόμενο μήνυμα'
        : 'Online mode απενεργοποιήθηκε'
    );
  };

  return (
    <div className="border-t bg-white p-4">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Γράψε το μήνυμά σου..."
            className="min-h-[60px] resize-none"
            disabled={isLoading}
          />
        </div>
        
        <div className="flex flex-col gap-2">
          <Button
            variant={useOnline ? 'default' : 'outline'}
            size="icon"
            onClick={toggleOnline}
            title={useOnline ? 'Online ON' : 'Online OFF'}
            className={cn(
              useOnline && 'bg-blue-600 hover:bg-blue-700'
            )}
          >
            <Globe className="h-4 w-4" />
          </Button>
          
          {isSupported && (
            <Button
              variant="outline"
              size="icon"
              onClick={isListening ? stopListening : startListening}
              disabled={isLoading}
              title="Φωνητική εισαγωγή"
              className={cn(
                isListening && 'bg-red-100 border-red-300'
              )}
            >
              <Mic className={cn('h-4 w-4', isListening && 'text-red-600')} />
            </Button>
          )}
          
          <Button
            onClick={handleSubmit}
            disabled={!message.trim() || isLoading}
            size="icon"
            title="Αποστολή"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span>
            Online: {useOnline ? '🟢 ON' : '🔴 OFF'}
          </span>
          {isListening && (
            <span className="text-red-600 animate-pulse">
              🎤 Ακούω...
            </span>
          )}
        </div>
        <span className="text-gray-400">
          Enter για αποστολή, Shift+Enter για νέα γραμμή
        </span>
      </div>
    </div>
  );
}