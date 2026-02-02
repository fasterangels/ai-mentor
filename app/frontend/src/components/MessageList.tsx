import { useEffect, useRef } from 'react';
import { t } from '@/i18n';
import { Message } from '@/types';
import { Brain, Globe, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getThinkingStateIcon = (state?: string) => {
    switch (state) {
      case 'online':
        return <Globe className="h-3 w-3 text-blue-500" />;
      case 'memory_knowledge':
        return <BookOpen className="h-3 w-3 text-purple-500" />;
      case 'offline':
      default:
        return <Brain className="h-3 w-3 text-green-500" />;
    }
  };

  const getThinkingStateLabel = (state?: string) => {
    switch (state) {
      case 'online':
        return '🌐 ' + t("message.online_research");
      case 'memory_knowledge':
        return '📚 ' + t("message.memory_knowledge");
      case 'offline':
      default:
        return '🧠 ' + t("message.offline_thought");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 ? (
        <div className="text-center text-gray-500 mt-8">
          <p>{t("message.start_conversation")}</p>
        </div>
      ) : (
        messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'flex',
              message.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'max-w-[80%] rounded-lg px-4 py-2',
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : message.role === 'system'
                  ? 'bg-yellow-50 text-gray-900 border border-yellow-200'
                  : 'bg-white text-gray-900 shadow-sm border border-gray-200'
              )}
            >
              {message.role === 'assistant' && message.thinking_state && (
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                  {getThinkingStateIcon(message.thinking_state)}
                  <span>{getThinkingStateLabel(message.thinking_state)}</span>
                  {message.used_online && (
                    <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                      Online
                    </span>
                  )}
                </div>
              )}
              
              <div className="whitespace-pre-wrap break-words">
                {message.content}
              </div>
              
              <div className="text-xs opacity-70 mt-2">
                {new Date(message.created_at).toLocaleTimeString('el-GR', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  );
}