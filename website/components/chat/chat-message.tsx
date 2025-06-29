'use client';

import { cn } from '@/lib/utils';
import { getStatusEmoji } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { motion } from 'framer-motion';

interface ChatMessageProps {
  status: 'info' | 'success' | 'error' | 'warning' | 'assistant';
  message: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export function ChatMessage({ status, message, timestamp, isStreaming }: ChatMessageProps) {
  const emoji = getStatusEmoji(status);
  
  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'error':
        return 'cyber-glow-red border-red-500/30 bg-red-500/5';
      case 'success':
        return 'cyber-glow border-green-500/30 bg-green-500/5';
      case 'warning':
        return 'cyber-glow-yellow border-yellow-500/30 bg-yellow-500/5';
      case 'assistant':
        return 'cyber-glow-blue border-blue-500/30 bg-blue-500/5';
      default:
        return 'glassmorphism border-white/10';
    }
  };

  const getTextStyles = (status: string) => {
    switch (status) {
      case 'error':
        return 'text-red-400';
      case 'success':
        return 'text-green-400';
      case 'warning':
        return 'text-yellow-400';
      case 'assistant':
        return 'text-blue-400';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="message-enter"
    >
      <Card className={cn('p-4 mb-4', getStatusStyles(status))}>
        <div className="flex items-start space-x-3">
          <span className="text-xl flex-shrink-0 mt-0.5">
            {emoji}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <span className={cn('text-sm font-medium capitalize', getTextStyles(status))}>
                {status}
              </span>
              <span className="text-xs text-muted-foreground terminal-font">
                {timestamp.toLocaleTimeString()}
              </span>
            </div>
            <div className={cn(
              'terminal-font text-sm leading-relaxed',
              status === 'assistant' ? 'text-foreground' : getTextStyles(status)
            )}>
              {status === 'assistant' && (
                <div className="mb-2 text-blue-400 font-medium">
                  🤖 Assistant:
                </div>
              )}
              <pre className="whitespace-pre-wrap font-sans">
                {message}
                {isStreaming && (
                  <span className="typing-indicator ml-1">▋</span>
                )}
              </pre>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}