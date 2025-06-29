'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { redirect } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { simpleQuery, type QueryResponse } from '@/lib/api';
import { motion } from 'framer-motion';
import { Search, Loader2, Clock, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useEffect } from 'react';

export default function QueryPage() {
  const { data: session, status } = useSession();
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryResponse[]>([]);

  useEffect(() => {
    if (status === 'unauthenticated') {
      redirect('/auth/signin');
    }
  }, [status]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    setResponse(null);

    try {
      const result = await simpleQuery(query.trim());
      setResponse(result);
      setQueryHistory(prev => [result, ...prev.slice(0, 4)]);
      toast.success('Query completed successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Query failed');
    } finally {
      setIsLoading(false);
    }
  };

  const exampleQueries = [
    "What are the best practices for EC2 security?",
    "How can I optimize my S3 storage costs?",
    "What's the difference between RDS and DynamoDB?",
    "How do I set up auto-scaling for my application?",
    "What are the compliance standards AWS supports?",
  ];

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400 mx-auto mb-4"></div>
          <p className="text-green-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="space-y-8"
        >
          {/* Header */}
          <div className="text-center">
            <h1 className="text-3xl font-bold neon-text-green terminal-font mb-2">
              Quick Query
            </h1>
            <p className="text-gray-400">
              Get instant answers to your AWS questions
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Query Input */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="glassmorphism cyber-glow">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-green-400">
                    <Search className="h-5 w-5" />
                    <span>Ask Your Question</span>
                  </CardTitle>
                  <CardDescription>
                    Enter your AWS-related question below for an instant response
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <Textarea
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="e.g., What are the best practices for EC2 security?"
                      className="min-h-[120px] terminal-font bg-black/50 border-green-500/30 focus:border-green-400 focus:ring-green-400/20"
                      disabled={isLoading}
                    />
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400">
                        {query.length}/500 characters
                      </span>
                      <Button
                        type="submit"
                        disabled={!query.trim() || isLoading}
                        className="cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400"
                      >
                        {isLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Search className="h-4 w-4 mr-2" />
                        )}
                        {isLoading ? 'Processing...' : 'Submit Query'}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>

              {/* Response */}
              {response && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                >
                  <Card className="glassmorphism cyber-glow-blue">
                    <CardHeader>
                      <CardTitle className="flex items-center justify-between text-blue-400">
                        <div className="flex items-center space-x-2">
                          <CheckCircle className="h-5 w-5" />
                          <span>Response</span>
                        </div>
                        <Badge variant="outline" className="terminal-font text-xs">
                          {response.status}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="terminal-font text-sm leading-relaxed bg-black/30 p-4 rounded-lg border border-blue-500/20">
                          <pre className="whitespace-pre-wrap font-sans">
                            {response.response}
                          </pre>
                        </div>
                        <div className="flex items-center justify-between text-xs text-gray-400">
                          <div className="flex items-center space-x-1">
                            <Clock className="h-3 w-3" />
                            <span>{new Date(response.timestamp).toLocaleString()}</span>
                          </div>
                          <span className="terminal-font">
                            {response.response.length} characters
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              )}
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Example Queries */}
              <Card className="glassmorphism">
                <CardHeader>
                  <CardTitle className="text-yellow-400">
                    Example Queries
                  </CardTitle>
                  <CardDescription>
                    Click to try these sample questions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {exampleQueries.map((example, index) => (
                      <Button
                        key={index}
                        variant="ghost"
                        size="sm"
                        onClick={() => setQuery(example)}
                        className="w-full text-left justify-start h-auto p-3 text-xs text-gray-300 hover:text-green-400 hover:bg-green-500/10"
                        disabled={isLoading}
                      >
                        {example}
                      </Button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Query History */}
              {queryHistory.length > 0 && (
                <Card className="glassmorphism">
                  <CardHeader>
                    <CardTitle className="text-purple-400">
                      Recent Queries
                    </CardTitle>
                    <CardDescription>
                      Your last {queryHistory.length} queries
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {queryHistory.map((item, index) => (
                        <div
                          key={index}
                          className="p-3 rounded-lg bg-black/30 border border-purple-500/20"
                        >
                          <div className="text-xs text-gray-400 mb-1 flex items-center space-x-1">
                            <Clock className="h-3 w-3" />
                            <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-sm text-gray-300 line-clamp-2">
                            {item.response.substring(0, 100)}...
                          </p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}