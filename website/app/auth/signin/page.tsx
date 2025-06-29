'use client';

import { useState } from 'react';
import { signIn, getSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Github, Mail, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

export default function SignIn() {
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();

  const handleCredentialsSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      });

      if (result?.error) {
        toast.error('Invalid credentials. Try demo@example.com / demo123');
      } else {
        toast.success('Signed in successfully!');
        router.push('/chat');
      }
    } catch (error) {
      toast.error('Something went wrong');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGithubSignIn = async () => {
    setIsLoading(true);
    try {
      await signIn('github', { callbackUrl: '/chat' });
    } catch (error) {
      toast.error('Failed to sign in with GitHub');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="w-full max-w-md"
      >
        <Card className="glassmorphism cyber-glow">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl neon-text-green terminal-font">
              Welcome to AWS.AI
            </CardTitle>
            <CardDescription className="text-gray-400">
              Sign in to start managing your AWS resources with AI
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="credentials" className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-black/50">
                <TabsTrigger value="credentials" className="data-[state=active]:bg-green-500/20">
                  Email
                </TabsTrigger>
                <TabsTrigger value="github" className="data-[state=active]:bg-green-500/20">
                  GitHub
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="credentials" className="space-y-4 mt-6">
                <form onSubmit={handleCredentialsSignIn} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-green-400">
                      Email
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="demo@example.com"
                      className="bg-black/50 border-green-500/30 focus:border-green-400"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-green-400">
                      Password
                    </Label>
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="demo123"
                      className="bg-black/50 border-green-500/30 focus:border-green-400"
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400"
                  >
                    {isLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Mail className="mr-2 h-4 w-4" />
                    )}
                    Sign In with Email
                  </Button>
                </form>
                
                <div className="text-center text-sm text-gray-400 mt-4">
                  Demo credentials: demo@example.com / demo123
                </div>
              </TabsContent>
              
              <TabsContent value="github" className="space-y-4 mt-6">
                <Button
                  onClick={handleGithubSignIn}
                  disabled={isLoading}
                  className="w-full cyber-glow-blue bg-blue-500/20 hover:bg-blue-500/30 text-blue-400"
                >
                  {isLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Github className="mr-2 h-4 w-4" />
                  )}
                  Sign In with GitHub
                </Button>
                
                <div className="text-center text-sm text-gray-400">
                  Connect with your GitHub account for instant access
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}