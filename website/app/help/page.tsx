'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { redirect } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { getHelp, type HelpResponse } from '@/lib/api';
import { motion } from 'framer-motion';
import { HelpCircle, Search, Copy, ExternalLink, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';

export default function HelpPage() {
  const { data: session, status } = useSession();
  const [helpData, setHelpData] = useState<HelpResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredData, setFilteredData] = useState<HelpResponse | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') {
      redirect('/auth/signin');
    }
  }, [status]);

  useEffect(() => {
    const fetchHelp = async () => {
      try {
        const data = await getHelp();
        setHelpData(data);
        setFilteredData(data);
      } catch (error) {
        toast.error('Failed to load help data');
        // Fallback data if API is not available
        const fallbackData: HelpResponse = {
          examples: [
            {
              category: "EC2 Management",
              queries: [
                "Show me all my EC2 instances",
                "List running EC2 instances",
                "What are my largest EC2 instances?",
                "Show EC2 instances by region",
                "Which EC2 instances are stopped?"
              ]
            },
            {
              category: "Cost Analysis",
              queries: [
                "What's my AWS cost for the last month?",
                "Show me my highest cost services",
                "Analyze my S3 storage costs",
                "What are my EC2 costs by instance type?",
                "Compare costs between regions"
              ]
            },
            {
              category: "S3 Management",
              queries: [
                "List all my S3 buckets",
                "Create an S3 bucket named my-demo-bucket",
                "Show S3 bucket sizes",
                "Which S3 buckets have public access?",
                "Analyze S3 storage classes"
              ]
            },
            {
              category: "Security & Compliance",
              queries: [
                "Show me security groups with open ports",
                "List IAM users without MFA",
                "Check for unused security groups",
                "Show resources without encryption",
                "Audit public resources"
              ]
            },
            {
              category: "Performance & Monitoring",
              queries: [
                "Show CloudWatch alarms",
                "What are my highest CPU instances?",
                "Check database performance metrics",
                "Show load balancer health",
                "Monitor application performance"
              ]
            },
            {
              category: "Resource Management",
              queries: [
                "List untagged resources",
                "Show unused EBS volumes",
                "Find idle resources",
                "List snapshots older than 30 days",
                "Show duplicate resources"
              ]
            }
          ]
        };
        setHelpData(fallbackData);
        setFilteredData(fallbackData);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHelp();
  }, []);

  useEffect(() => {
    if (!helpData || !searchTerm.trim()) {
      setFilteredData(helpData);
      return;
    }

    const filtered: HelpResponse = {
      examples: helpData.examples
        .map(category => ({
          ...category,
          queries: category.queries.filter(query =>
            query.toLowerCase().includes(searchTerm.toLowerCase()) ||
            category.category.toLowerCase().includes(searchTerm.toLowerCase())
          )
        }))
        .filter(category => category.queries.length > 0)
    };

    setFilteredData(filtered);
  }, [searchTerm, helpData]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Query copied to clipboard');
  };

  const getCategoryColor = (category: string) => {
    const colors = {
      'EC2 Management': 'text-green-400 border-green-400',
      'Cost Analysis': 'text-blue-400 border-blue-400',
      'S3 Management': 'text-yellow-400 border-yellow-400',
      'Security & Compliance': 'text-red-400 border-red-400',
      'Performance & Monitoring': 'text-purple-400 border-purple-400',
      'Resource Management': 'text-cyan-400 border-cyan-400',
    };
    return colors[category as keyof typeof colors] || 'text-gray-400 border-gray-400';
  };

  if (status === 'loading' || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-green-400 mx-auto mb-4" />
          <p className="text-green-400">Loading help information...</p>
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
              Help & Examples
            </h1>
            <p className="text-gray-400">
              Explore example queries and learn how to interact with AWS services
            </p>
          </div>

          {/* Search */}
          <Card className="glassmorphism cyber-glow">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-green-400">
                <Search className="h-5 w-5" />
                <span>Search Examples</span>
              </CardTitle>
              <CardDescription>
                Find specific queries or browse by category
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search queries or categories..."
                  className="pl-10 terminal-font bg-black/50 border-green-500/30 focus:border-green-400"
                />
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/chat">
              <Card className="glassmorphism hover:cyber-glow transition-all duration-300 cursor-pointer">
                <CardContent className="p-6 text-center">
                  <div className="text-green-400 mb-2">💬</div>
                  <h3 className="font-medium text-green-400 mb-1">Try Chat</h3>
                  <p className="text-xs text-gray-400">Start a conversation</p>
                </CardContent>
              </Card>
            </Link>
            <Link href="/query">
              <Card className="glassmorphism hover:cyber-glow-blue transition-all duration-300 cursor-pointer">
                <CardContent className="p-6 text-center">
                  <div className="text-blue-400 mb-2">❓</div>
                  <h3 className="font-medium text-blue-400 mb-1">Quick Query</h3>
                  <p className="text-xs text-gray-400">Get instant answers</p>
                </CardContent>
              </Card>
            </Link>
            <Link href="/aws">
              <Card className="glassmorphism hover:cyber-glow-yellow transition-all duration-300 cursor-pointer">
                <CardContent className="p-6 text-center">
                  <div className="text-yellow-400 mb-2">☁️</div>
                  <h3 className="font-medium text-yellow-400 mb-1">AWS Tools</h3>
                  <p className="text-xs text-gray-400">Manage resources</p>
                </CardContent>
              </Card>
            </Link>
          </div>

          {/* Examples */}
          {filteredData && (
            <Card className="glassmorphism">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-green-400">
                  <HelpCircle className="h-5 w-5" />
                  <span>Example Queries by Category</span>
                </CardTitle>
                <CardDescription>
                  {searchTerm ? `Found ${filteredData.examples.length} matching categories` : `${filteredData.examples.length} categories available`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {filteredData.examples.length === 0 ? (
                  <div className="text-center py-12">
                    <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-400">No matching queries found</p>
                    <Button
                      variant="ghost"
                      onClick={() => setSearchTerm('')}
                      className="mt-2 text-green-400 hover:text-green-300"
                    >
                      Clear search
                    </Button>
                  </div>
                ) : (
                  <Accordion type="multiple" className="w-full">
                    {filteredData.examples.map((category, categoryIndex) => (
                      <AccordionItem
                        key={categoryIndex}
                        value={`category-${categoryIndex}`}
                        className="border-white/10"
                      >
                        <AccordionTrigger className="hover:no-underline">
                          <div className="flex items-center space-x-3">
                            <Badge variant="outline" className={`${getCategoryColor(category.category)} terminal-font`}>
                              {category.category}
                            </Badge>
                            <span className="text-gray-300">{category.queries.length} queries</span>
                          </div>
                        </AccordionTrigger>
                        <AccordionContent>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-4">
                            {category.queries.map((query, queryIndex) => (
                              <motion.div
                                key={queryIndex}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.3, delay: queryIndex * 0.05 }}
                                className="group relative"
                              >
                                <div className="p-4 rounded-lg bg-black/30 border border-white/10 hover:border-green-400/30 transition-colors">
                                  <p className="text-sm text-gray-300 terminal-font mb-3 leading-relaxed">
                                    "{query}"
                                  </p>
                                  <div className="flex items-center space-x-2">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => copyToClipboard(query)}
                                      className="h-7 px-2 text-xs text-green-400 hover:text-green-300 hover:bg-green-500/10"
                                    >
                                      <Copy className="h-3 w-3 mr-1" />
                                      Copy
                                    </Button>
                                    <Link href={`/chat?query=${encodeURIComponent(query)}`}>
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-7 px-2 text-xs text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                                      >
                                        <ExternalLink className="h-3 w-3 mr-1" />
                                        Try
                                      </Button>
                                    </Link>
                                  </div>
                                </div>
                              </motion.div>
                            ))}
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                )}
              </CardContent>
            </Card>
          )}

          {/* Tips Section */}
          <Card className="glassmorphism">
            <CardHeader>
              <CardTitle className="text-yellow-400">
                💡 Tips for Better Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-yellow-400 mb-2">Chat Interface</h4>
                  <ul className="text-sm text-gray-300 space-y-1">
                    <li>• Use natural language</li>
                    <li>• Be specific about resources</li>
                    <li>• Ask follow-up questions</li>
                    <li>• Request different formats</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-yellow-400 mb-2">Query Interface</h4>
                  <ul className="text-sm text-gray-300 space-y-1">
                    <li>• Ask direct questions</li>
                    <li>• Include timeframes</li>
                    <li>• Specify regions if needed</li>
                    <li>• Use technical terms</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}