'use client';

import { useState, useRef } from 'react';
import { useSession } from 'next-auth/react';
import { redirect } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatMessage } from '@/components/chat/chat-message';
import { listEC2Instances, createS3Bucket, generateId, type ChatMessage as ChatMessageType, type ApiResponse } from '@/lib/api';
import { motion } from 'framer-motion';
import { Cloud, Database, Loader2, Server, Play } from 'lucide-react';
import { toast } from 'sonner';
import { useEffect } from 'react';

export default function AWSPage() {
  const { data: session, status } = useSession();
  const [ec2Messages, setEc2Messages] = useState<ChatMessageType[]>([]);
  const [isListingEC2, setIsListingEC2] = useState(false);
  const [bucketName, setBucketName] = useState('');
  const [encryption, setEncryption] = useState(true);
  const [versioning, setVersioning] = useState(false);
  const [isCreatingBucket, setIsCreatingBucket] = useState(false);
  const [bucketResult, setBucketResult] = useState<ApiResponse | null>(null);
  const ec2ScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      redirect('/auth/signin');
    }
  }, [status]);

  useEffect(() => {
    // Auto-scroll EC2 messages area
    if (ec2ScrollRef.current) {
      ec2ScrollRef.current.scrollTop = ec2ScrollRef.current.scrollHeight;
    }
  }, [ec2Messages]);

  const handleListEC2 = async () => {
    setIsListingEC2(true);
    setEc2Messages([]);

    try {
      const responseStream = listEC2Instances();
      
      for await (const response of responseStream) {
        const message: ChatMessageType = {
          id: generateId(),
          message: response.message,
          timestamp: new Date(),
          status: response.status,
          isStreaming: true,
        };
        
        setEc2Messages(prev => [...prev, message]);
      }
      
      toast.success('EC2 instances listed successfully');
    } catch (error) {
      const errorMessage: ChatMessageType = {
        id: generateId(),
        message: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
        status: 'error',
      };
      
      setEc2Messages(prev => [...prev, errorMessage]);
      toast.error('Failed to list EC2 instances');
    } finally {
      setIsListingEC2(false);
    }
  };

  const handleCreateS3Bucket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bucketName.trim() || isCreatingBucket) return;

    setIsCreatingBucket(true);
    setBucketResult(null);

    try {
      const result = await createS3Bucket(bucketName.trim(), encryption, versioning);
      setBucketResult(result);
      
      if (result.status === 'success') {
        setBucketName('');
        toast.success('S3 bucket created successfully');
      } else {
        toast.error('Failed to create S3 bucket');
      }
    } catch (error) {
      const errorResult: ApiResponse = {
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to create S3 bucket'
      };
      setBucketResult(errorResult);
      toast.error('Failed to create S3 bucket');
    } finally {
      setIsCreatingBucket(false);
    }
  };

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
      <div className="max-w-7xl mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="space-y-8"
        >
          {/* Header */}
          <div className="text-center">
            <h1 className="text-3xl font-bold neon-text-green terminal-font mb-2">
              AWS Management Tools
            </h1>
            <p className="text-gray-400">
              Manage your AWS resources directly through our interface
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* EC2 Management */}
            <Card className="glassmorphism cyber-glow">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-green-400">
                  <Server className="h-5 w-5" />
                  <span>EC2 Instances</span>
                </CardTitle>
                <CardDescription>
                  List and manage your EC2 instances with streaming updates
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button
                  onClick={handleListEC2}
                  disabled={isListingEC2}
                  className="w-full cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400"
                >
                  {isListingEC2 ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Play className="h-4 w-4 mr-2" />
                  )}
                  {isListingEC2 ? 'Listing Instances...' : 'List EC2 Instances'}
                </Button>

                {/* EC2 Messages Area */}
                <div className="h-80 border border-green-500/20 rounded-lg bg-black/30">
                  {ec2Messages.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-center p-4">
                      <div>
                        <Server className="h-12 w-12 text-green-400/50 mx-auto mb-3" />
                        <p className="text-gray-400 text-sm">
                          Click "List EC2 Instances" to see your running instances
                        </p>
                      </div>
                    </div>
                  ) : (
                    <ScrollArea className="h-full p-4" ref={ec2ScrollRef}>
                      <div className="space-y-3">
                        {ec2Messages.map((message) => (
                          <div key={message.id} className="text-sm">
                            <ChatMessage
                              status={message.status}
                              message={message.message}
                              timestamp={message.timestamp}
                              isStreaming={message.isStreaming}
                            />
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>Messages: {ec2Messages.length}</span>
                  <Badge variant="outline" className={`terminal-font ${isListingEC2 ? 'border-yellow-400 text-yellow-400' : 'border-green-400 text-green-400'}`}>
                    {isListingEC2 ? 'Streaming' : 'Ready'}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* S3 Management */}
            <Card className="glassmorphism cyber-glow-blue">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-blue-400">
                  <Database className="h-5 w-5" />
                  <span>S3 Bucket Creation</span>
                </CardTitle>
                <CardDescription>
                  Create new S3 buckets with custom configurations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateS3Bucket} className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="bucketName" className="text-blue-400">
                      Bucket Name
                    </Label>
                    <Input
                      id="bucketName"
                      value={bucketName}
                      onChange={(e) => setBucketName(e.target.value)}
                      placeholder="my-unique-bucket-name"
                      className="terminal-font bg-black/50 border-blue-500/30 focus:border-blue-400"
                      disabled={isCreatingBucket}
                      required
                    />
                    <p className="text-xs text-gray-400">
                      Must be globally unique and follow S3 naming conventions
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label htmlFor="encryption" className="text-blue-400">
                          Enable Encryption
                        </Label>
                        <p className="text-xs text-gray-400">
                          Encrypt objects at rest
                        </p>
                      </div>
                      <Switch
                        id="encryption"
                        checked={encryption}
                        onCheckedChange={setEncryption}
                        disabled={isCreatingBucket}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <Label htmlFor="versioning" className="text-blue-400">
                          Enable Versioning
                        </Label>
                        <p className="text-xs text-gray-400">
                          Keep multiple versions of objects
                        </p>
                      </div>
                      <Switch
                        id="versioning"
                        checked={versioning}
                        onCheckedChange={setVersioning}
                        disabled={isCreatingBucket}
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={!bucketName.trim() || isCreatingBucket}
                    className="w-full cyber-glow-blue bg-blue-500/20 hover:bg-blue-500/30 text-blue-400"
                  >
                    {isCreatingBucket ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Database className="h-4 w-4 mr-2" />
                    )}
                    {isCreatingBucket ? 'Creating Bucket...' : 'Create S3 Bucket'}
                  </Button>
                </form>

                {/* S3 Result */}
                {bucketResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className="mt-6"
                  >
                    <div className={`p-4 rounded-lg border ${
                      bucketResult.status === 'success' 
                        ? 'bg-green-500/10 border-green-500/30' 
                        : 'bg-red-500/10 border-red-500/30'
                    }`}>
                      <div className="flex items-start space-x-2">
                        <span className="text-lg">
                          {bucketResult.status === 'success' ? '✅' : '❌'}
                        </span>
                        <div>
                          <p className={`font-medium ${
                            bucketResult.status === 'success' ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {bucketResult.status === 'success' ? 'Success' : 'Error'}
                          </p>
                          <p className="text-sm text-gray-300 terminal-font">
                            {bucketResult.message}
                          </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Additional Tools Section */}
          <Card className="glassmorphism">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-purple-400">
                <Cloud className="h-5 w-5" />
                <span>Additional AWS Tools</span>
              </CardTitle>
              <CardDescription>
                More AWS management tools coming soon
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-black/30 border border-purple-500/20 text-center">
                  <div className="text-purple-400 mb-2">🚧</div>
                  <h4 className="font-medium text-purple-400 mb-1">RDS Management</h4>
                  <p className="text-xs text-gray-400">Coming Soon</p>
                </div>
                <div className="p-4 rounded-lg bg-black/30 border border-purple-500/20 text-center">
                  <div className="text-purple-400 mb-2">🚧</div>
                  <h4 className="font-medium text-purple-400 mb-1">Lambda Functions</h4>
                  <p className="text-xs text-gray-400">Coming Soon</p>
                </div>
                <div className="p-4 rounded-lg bg-black/30 border border-purple-500/20 text-center">
                  <div className="text-purple-400 mb-2">🚧</div>
                  <h4 className="font-medium text-purple-400 mb-1">CloudWatch</h4>
                  <p className="text-xs text-gray-400">Coming Soon</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}