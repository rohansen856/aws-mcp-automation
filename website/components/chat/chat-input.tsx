'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isStreaming: boolean;
}

export function ChatInput({ onSendMessage, isStreaming }: ChatInputProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isStreaming) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <Card className="glassmorphism border-green-500/20 p-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? "Waiting for response..." : "Type your message here... (Shift+Enter for new line)"}
          disabled={isStreaming}
          className="min-h-[120px] terminal-font bg-black/50 border-green-500/30 focus:border-green-400 focus:ring-green-400/20 resize-none"
        />
        <div className="flex justify-between items-center">
          <span className="text-xs text-muted-foreground terminal-font">
            {isStreaming ? 'Streaming response...' : 'Ready to send'}
          </span>
          <Button
            type="submit"
            disabled={!message.trim() || isStreaming}
            className="cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="ml-2">
              {isStreaming ? 'Sending...' : 'Send'}
            </span>
          </Button>
        </div>
      </form>
    </Card>
  );
}