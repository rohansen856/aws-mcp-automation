'use client';

import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { 
  MessageSquare, 
  Search, 
  Cloud, 
  HelpCircle,
  Zap,
  Shield,
  Globe
} from 'lucide-react';
import { motion } from 'framer-motion';

const features = [
  {
    icon: MessageSquare,
    title: 'Interactive Chat',
    description: 'Stream real-time conversations with AWS AI services',
    href: '/chat',
    color: 'text-green-400'
  },
  {
    icon: Search,
    title: 'Quick Query',
    description: 'Get instant answers to your AWS questions',
    href: '/query',
    color: 'text-blue-400'
  },
  {
    icon: Cloud,
    title: 'AWS Tools',
    description: 'Manage EC2 instances and S3 buckets directly',
    href: '/aws',
    color: 'text-yellow-400'
  },
  {
    icon: HelpCircle,
    title: 'Help & Examples',
    description: 'Explore example queries and use cases',
    href: '/help',
    color: 'text-purple-400'
  },
];

const stats = [
  { label: 'AI Models', value: '10+', icon: Zap },
  { label: 'AWS Services', value: '50+', icon: Cloud },
  { label: 'Secure', value: '100%', icon: Shield },
  { label: 'Global', value: '24/7', icon: Globe },
];

export default function Home() {
  const { data: session } = useSession();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden px-6 py-24 sm:py-32 lg:px-8">
        <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 via-transparent to-blue-500/10" />
        <div className="relative mx-auto max-w-4xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl font-bold tracking-tight sm:text-7xl">
              <span className="neon-text-green">AWS</span>
              <span className="text-white">.</span>
              <span className="neon-text-blue">AI</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300 max-w-2xl mx-auto">
              Harness the power of AI to interact with AWS services through natural language. 
              Stream real-time responses, manage cloud resources, and get instant insights.
            </p>
            
            <div className="mt-10 flex items-center justify-center gap-x-6">
              {session ? (
                <Link href="/chat">
                  <Button size="lg" className="cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400 px-8 py-3">
                    Start Chatting
                    <MessageSquare className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              ) : (
                <Link href="/auth/signin">
                  <Button size="lg" className="cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400 px-8 py-3">
                    Get Started
                    <Zap className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              )}
              <Link href="/help">
                <Button variant="outline" size="lg" className="border-white/20 text-white hover:bg-white/10 px-8 py-3">
                  View Examples
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 bg-black/20">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            {stats.map((stat, index) => {
              const Icon = stat.icon;
              return (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  className="text-center"
                >
                  <div className="flex justify-center mb-2">
                    <Icon className="h-8 w-8 text-green-400" />
                  </div>
                  <p className="text-3xl font-bold neon-text-green terminal-font">
                    {stat.value}
                  </p>
                  <p className="text-sm text-gray-400">
                    {stat.label}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl font-bold neon-text-green mb-4">
              Powerful Features
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Everything you need to interact with AWS services through AI-powered conversations
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                >
                  <Link href={session ? feature.href : '/auth/signin'}>
                    <Card className="glassmorphism hover:cyber-glow transition-all duration-300 p-6 h-full cursor-pointer group">
                      <div className="text-center">
                        <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-black/50 mb-4 group-hover:scale-110 transition-transform duration-300">
                          <Icon className={`h-6 w-6 ${feature.color}`} />
                        </div>
                        <h3 className="text-lg font-semibold text-white mb-2">
                          {feature.title}
                        </h3>
                        <p className="text-sm text-gray-400 leading-relaxed">
                          {feature.description}
                        </p>
                      </div>
                    </Card>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 lg:px-8 bg-gradient-to-r from-green-500/10 via-blue-500/10 to-purple-500/10">
        <div className="mx-auto max-w-4xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-3xl font-bold text-white mb-6">
              Ready to Experience the Future?
            </h2>
            <p className="text-gray-300 mb-8 max-w-2xl mx-auto">
              Join thousands of developers who are already using AWS.AI to streamline their cloud operations
            </p>
            {!session && (
              <Link href="/auth/signin">
                <Button size="lg" className="cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400 px-8 py-3">
                  Sign Up Now
                  <Zap className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            )}
          </motion.div>
        </div>
      </section>
    </div>
  );
}