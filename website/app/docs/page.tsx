'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { redirect } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { motion } from 'framer-motion';
import { 
  BookOpen, 
  Rocket, 
  Settings, 
  Shield, 
  Code, 
  Database,
  Cloud,
  Terminal,
  CheckCircle,
  AlertTriangle,
  Info,
  ExternalLink,
  Copy,
  Download,
  Github,
  Mail,
  Zap,
  Server,
  Globe,
  Lock,
  Layers,
  BarChart3,
  FileText,
  Users,
  Wrench,
  Search,
  Archive,
  Link as LinkIcon,
  Hash,
  Filter,
  Target,
  Cpu,
  HardDrive
} from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';

const features = [
  {
    icon: Globe,
    title: "Natural Language AWS Management",
    description: "Control AWS resources using plain English commands"
  },
  {
    icon: Code,
    title: "Infrastructure as Code",
    description: "Terraform integration for reproducible deployments"
  },
  {
    icon: Database,
    title: "Comprehensive Audit Logging",
    description: "PostgreSQL-based tracking of all operations"
  },
  {
    icon: BarChart3,
    title: "Cost Analysis & Visualization",
    description: "Generate cost reports and interactive graphs"
  },
  {
    icon: Zap,
    title: "RAG-Enhanced Responses",
    description: "Knowledge base for AWS best practices using ChromaDB"
  },
  {
    icon: Server,
    title: "Multi-Service Support",
    description: "EC2, S3, Cost Explorer, and generic AWS commands"
  },
  {
    icon: Users,
    title: "Interactive Session Management",
    description: "Maintains context across conversations"
  },
  {
    icon: Lock,
    title: "Secure Authentication",
    description: "Next.js frontend with OAuth2-based login"
  }
];

const techStack = [
  { name: "Flask", description: "Backend API framework", color: "text-green-400" },
  { name: "Next.js", description: "Frontend framework with SSR", color: "text-blue-400" },
  { name: "PostgreSQL", description: "ACID-compliant database", color: "text-purple-400" },
  { name: "Terraform", description: "Infrastructure as Code", color: "text-yellow-400" },
  { name: "Ollama + Granite 3.3", description: "LLM for natural language processing", color: "text-red-400" },
  { name: "ChromaDB", description: "Vector database for RAG", color: "text-cyan-400" },
  { name: "Plotly", description: "Interactive visualization", color: "text-pink-400" },
  { name: "Boto3", description: "AWS SDK for Python", color: "text-orange-400" }
];

const prerequisites = [
  "Python 3.8+",
  "PostgreSQL 12+",
  "Terraform (optional, for IaC features)",
  "Ollama with Granite 3.3 model",
  "AWS Account with appropriate permissions",
  "Node.js 16+ and npm/yarn for the frontend"
];

const troubleshootingItems = [
  {
    issue: "Database Connection Error",
    solution: "Check PostgreSQL is running: sudo systemctl status postgresql"
  },
  {
    issue: "AWS Credentials Error",
    solution: "Verify credentials: aws sts get-caller-identity"
  },
  {
    issue: "Ollama Model Not Found",
    solution: "List available models: ollama list, then pull if missing: ollama pull granite3.3"
  },
  {
    issue: "Terraform Not Found",
    solution: "Add to PATH or install: export PATH=$PATH:/usr/local/bin/terraform"
  },
  {
    issue: "Frontend Build Error",
    solution: "Ensure Node.js and npm/yarn are installed: node -v && npm -v"
  }
];

const futureEnhancements = [
  "Multi-region support",
  "Real-time cost alerts",
  "CloudFormation integration",
  "AWS Organizations support",
  "Web UI interface for advanced operations",
  "Scheduled operations",
  "Advanced IAM management",
  "Backup and disaster recovery automation"
];

const dataOriginFeatures = [
  {
    icon: Search,
    title: "Web Crawling",
    description: "Recursive crawling from seed URLs with configurable depth limits"
  },
  {
    icon: Filter,
    title: "Content Parsing",
    description: "Structured extraction of titles, headings, paragraphs, images, and links"
  },
  {
    icon: Database,
    title: "ChromaDB Integration",
    description: "Vector storage for semantic search and retrieval"
  },
  {
    icon: Hash,
    title: "Data Deduplication",
    description: "MD5 content hashing to prevent duplicate entries"
  },
  {
    icon: Target,
    title: "Search Functionality",
    description: "Semantic similarity search across collected documentation"
  },
  {
    icon: Archive,
    title: "Data Export",
    description: "JSON export capabilities for backup and analysis"
  }
];

const scrapingComponents = [
  {
    component: "WebScraperWithVector",
    description: "Main class encapsulating scraping and ChromaDB integration",
    methods: [
      "crawl_website() - Recursive crawling with depth control",
      "parse_content() - HTML parsing and data extraction",
      "clean_text() - Text normalization and cleaning"
    ]
  },
  {
    component: "ChromaDB Integration",
    description: "Vector database setup and management",
    methods: [
      "setup_chromadb() - Initialize client and collections",
      "prepare_document_for_vector_db() - Document preparation",
      "insert_to_vector_db() - Batch insertion with chunking"
    ]
  },
  {
    component: "Search & Query",
    description: "Semantic search and content retrieval",
    methods: [
      "search_similar_content() - Similarity-based querying",
      "get_collection_stats() - Database statistics",
      "save_structured_data() - Export functionality"
    ]
  }
];

export default function DocsPage() {
  const { data: session, status } = useSession();
  const [activeSection, setActiveSection] = useState('overview');

  useEffect(() => {
    if (status === 'unauthenticated') {
      redirect('/auth/signin');
    }
  }, [status]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Code copied to clipboard');
  };

  const CodeBlock = ({ children, language = 'bash' }: { children: string; language?: string }) => (
    <div className="relative group">
      <pre className="bg-black/50 border border-green-500/20 rounded-lg p-4 overflow-x-auto terminal-font text-sm">
        <code className="text-green-400">{children}</code>
      </pre>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => copyToClipboard(children)}
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0"
      >
        <Copy className="h-3 w-3" />
      </Button>
    </div>
  );

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400 mx-auto mb-4"></div>
          <p className="text-green-400">Loading documentation...</p>
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
            <h1 className="text-4xl font-bold neon-text-green terminal-font mb-4">
              AWS MCP Automation Server
            </h1>
            <p className="text-xl text-gray-300 max-w-4xl mx-auto leading-relaxed">
              A natural language interface for AWS resource management using the MCP (Model-Context-Protocol) framework. 
              This system allows non-technical users to interact with AWS services through conversational commands.
            </p>
            <div className="flex items-center justify-center space-x-4 mt-6">
              <Badge variant="outline" className="text-green-400 border-green-400">
                v1.0.0
              </Badge>
              <Badge variant="outline" className="text-blue-400 border-blue-400">
                Production Ready
              </Badge>
              <Badge variant="outline" className="text-purple-400 border-purple-400">
                MIT License
              </Badge>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Navigation Sidebar */}
            <div className="lg:col-span-1">
              <Card className="glassmorphism sticky top-8">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-green-400">
                    <BookOpen className="h-5 w-5" />
                    <span>Navigation</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <nav className="space-y-2">
                    {[
                      { id: 'overview', label: 'Overview', icon: Info },
                      { id: 'features', label: 'Features', icon: Zap },
                      { id: 'prerequisites', label: 'Prerequisites', icon: CheckCircle },
                      { id: 'installation', label: 'Installation', icon: Download },
                      { id: 'usage', label: 'Usage', icon: Terminal },
                      { id: 'architecture', label: 'Architecture', icon: Layers },
                      { id: 'data-origin', label: 'Data Origin', icon: Search },
                      { id: 'security', label: 'Security', icon: Shield },
                      { id: 'troubleshooting', label: 'Troubleshooting', icon: Wrench },
                      { id: 'contributing', label: 'Contributing', icon: Users },
                      { id: 'support', label: 'Support', icon: Mail }
                    ].map((item) => {
                      const Icon = item.icon;
                      return (
                        <Button
                          key={item.id}
                          variant="ghost"
                          size="sm"
                          onClick={() => setActiveSection(item.id)}
                          className={`w-full justify-start text-left ${
                            activeSection === item.id 
                              ? 'bg-green-500/20 text-green-400' 
                              : 'text-gray-400 hover:text-green-400'
                          }`}
                        >
                          <Icon className="h-4 w-4 mr-2" />
                          {item.label}
                        </Button>
                      );
                    })}
                  </nav>
                </CardContent>
              </Card>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3">
              <Tabs value={activeSection} onValueChange={setActiveSection} className="w-full">
                {/* Overview */}
                <TabsContent value="overview" className="space-y-6">
                  <Card className="glassmorphism cyber-glow">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-green-400">
                        <Rocket className="h-5 w-5" />
                        <span>Project Overview</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-gray-300 leading-relaxed">
                        The AWS MCP Automation Server provides a powerful natural language interface for managing AWS resources. 
                        Built with modern technologies and best practices, it bridges the gap between complex AWS operations and 
                        user-friendly conversational interfaces.
                      </p>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 rounded-lg bg-black/30 border border-green-500/20">
                          <h4 className="font-medium text-green-400 mb-2">Backend</h4>
                          <p className="text-sm text-gray-400">Flask-powered APIs with PostgreSQL persistence</p>
                        </div>
                        <div className="p-4 rounded-lg bg-black/30 border border-blue-500/20">
                          <h4 className="font-medium text-blue-400 mb-2">Frontend</h4>
                          <p className="text-sm text-gray-400">Next.js with modern authentication and UI</p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-4 pt-4">
                        <Link href="/chat">
                          <Button className="cyber-glow bg-green-500/20 hover:bg-green-500/30 text-green-400">
                            Try Chat Interface
                          </Button>
                        </Link>
                        <Link href="/aws">
                          <Button variant="outline" className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10">
                            AWS Tools
                          </Button>
                        </Link>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Features */}
                <TabsContent value="features" className="space-y-6">
                  <Card className="glassmorphism">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-green-400">
                        <Zap className="h-5 w-5" />
                        <span>Key Features</span>
                      </CardTitle>
                      <CardDescription>
                        Comprehensive AWS management capabilities with modern tooling
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {features.map((feature, index) => {
                          const Icon = feature.icon;
                          return (
                            <motion.div
                              key={feature.title}
                              initial={{ opacity: 0, y: 20 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ duration: 0.5, delay: index * 0.1 }}
                              className="p-4 rounded-lg bg-black/30 border border-white/10 hover:border-green-400/30 transition-colors"
                            >
                              <div className="flex items-start space-x-3">
                                <Icon className="h-6 w-6 text-green-400 mt-1 flex-shrink-0" />
                                <div>
                                  <h4 className="font-medium text-white mb-1">{feature.title}</h4>
                                  <p className="text-sm text-gray-400">{feature.description}</p>
                                </div>
                              </div>
                            </motion.div>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Prerequisites */}
                <TabsContent value="prerequisites" className="space-y-6">
                  <Card className="glassmorphism">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-yellow-400">
                        <CheckCircle className="h-5 w-5" />
                        <span>Prerequisites</span>
                      </CardTitle>
                      <CardDescription>
                        Required software and services before installation
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {prerequisites.map((prereq, index) => (
                          <div key={index} className="flex items-center space-x-3 p-3 rounded-lg bg-black/30 border border-yellow-500/20">
                            <CheckCircle className="h-4 w-4 text-yellow-400 flex-shrink-0" />
                            <span className="text-gray-300">{prereq}</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Installation */}
                <TabsContent value="installation" className="space-y-6">
                  <Card className="glassmorphism">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-blue-400">
                        <Download className="h-5 w-5" />
                        <span>Installation Guide</span>
                      </CardTitle>
                      <CardDescription>
                        Step-by-step setup instructions
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="clone" className="border-white/10">
                          <AccordionTrigger className="text-green-400">1. Clone the Repository</AccordionTrigger>
                          <AccordionContent>
                            <CodeBlock>
{`git clone <repository-url>
cd aws-mcp-automation`}
                            </CodeBlock>
                          </AccordionContent>
                        </AccordionItem>

                        <AccordionItem value="backend" className="border-white/10">
                          <AccordionTrigger className="text-green-400">2. Install Backend Dependencies</AccordionTrigger>
                          <AccordionContent>
                            <CodeBlock>
{`cd api
pip install -r requirements.txt`}
                            </CodeBlock>
                          </AccordionContent>
                        </AccordionItem>

                        <AccordionItem value="database" className="border-white/10">
                          <AccordionTrigger className="text-green-400">3. Set Up PostgreSQL Database</AccordionTrigger>
                          <AccordionContent>
                            <CodeBlock>
{`# Create database and tables
psql -U postgres -f init_database.sql`}
                            </CodeBlock>
                          </AccordionContent>
                        </AccordionItem>

                        <AccordionItem value="env-backend" className="border-white/10">
                          <AccordionTrigger className="text-green-400">4. Configure Backend Environment</AccordionTrigger>
                          <AccordionContent>
                            <div className="space-y-4">
                              <p className="text-gray-300">Copy the example environment file:</p>
                              <CodeBlock>cp .env.example .env</CodeBlock>
                              
                              <p className="text-gray-300">Edit .env with your credentials:</p>
                              <CodeBlock language="env">
{`# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=aws_mcp

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your_secret_key`}
                              </CodeBlock>
                            </div>
                          </AccordionContent>
                        </AccordionItem>

                        <AccordionItem value="ollama" className="border-white/10">
                          <AccordionTrigger className="text-green-400">5. Install Ollama and Model</AccordionTrigger>
                          <AccordionContent>
                            <CodeBlock>
{`# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the Granite 3.3 model
ollama pull granite3.3`}
                            </CodeBlock>
                          </AccordionContent>
                        </AccordionItem>

                        <AccordionItem value="terraform" className="border-white/10">
                          <AccordionTrigger className="text-green-400">6. Install Terraform (Optional)</AccordionTrigger>
                          <AccordionContent>
                            <div className="space-y-4">
                              <p className="text-gray-300">For Infrastructure as Code features:</p>
                              <CodeBlock>
{`# macOS
brew install terraform

# Linux
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform`}
                              </CodeBlock>
                            </div>
                          </AccordionContent>
                        </AccordionItem>

                        <AccordionItem value="frontend" className="border-white/10">
                          <AccordionTrigger className="text-green-400">7. Install Frontend Dependencies</AccordionTrigger>
                          <AccordionContent>
                            <CodeBlock>
{`cd ../website
npm install`}
                            </CodeBlock>
                          </AccordionContent>
                        </AccordionItem>

                        <AccordionItem value="env-frontend" className="border-white/10">
                          <AccordionTrigger className="text-green-400">8. Configure Frontend Environment</AccordionTrigger>
                          <AccordionContent>
                            <div className="space-y-4">
                              <p className="text-gray-300">Copy the example environment file:</p>
                              <CodeBlock>cp .env.local.example .env.local</CodeBlock>
                              
                              <p className="text-gray-300">Edit .env.local with your settings:</p>
                              <CodeBlock language="env">
{`NEXT_PUBLIC_API_URL=http://localhost:5000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret`}
                              </CodeBlock>
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      </Accordion>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Usage */}
                <TabsContent value="usage" className="space-y-6">
                  <Card className="glassmorphism">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-purple-400">
                        <Terminal className="h-5 w-5" />
                        <span>Running the Service</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div>
                        <h4 className="font-medium text-purple-400 mb-3">Start the Backend Server</h4>
                        <CodeBlock>
{`cd api
python server.py`}
                        </CodeBlock>
                      </div>

                      <div>
                        <h4 className="font-medium text-purple-400 mb-3">Start the Frontend Server</h4>
                        <p className="text-gray-300 mb-3">Open up a new terminal and run:</p>
                        <CodeBlock>
{`cd website
npm run dev`}
                        </CodeBlock>
                        <p className="text-gray-300 mt-3">Access the application at <code className="text-green-400">http://localhost:3000</code></p>
                      </div>

                      <Separator className="bg-white/10" />

                      <div>
                        <h4 className="font-medium text-blue-400 mb-3">Example API Interactions</h4>
                        
                        <div className="space-y-4">
                          <div>
                            <p className="text-gray-300 mb-2">Backend API Example:</p>
                            <CodeBlock language="json">
{`POST /api/ec2/instances
{
   "instance_type": "t2.micro",
   "name": "ubuntu-server",
   "use_terraform": true
}`}
                            </CodeBlock>
                            
                            <p className="text-gray-300 mt-3 mb-2">Response:</p>
                            <CodeBlock language="json">
{`{
   "status": "success",
   "message": "EC2 instance created successfully",
   "data": {
      "instance_id": "i-0a1b2c3d4e5f6g7h8",
      "public_ip": "54.123.45.67"
   }
}`}
                            </CodeBlock>
                          </div>

                          <div>
                            <p className="text-gray-300 mb-2">Frontend Example:</p>
                            <ol className="list-decimal list-inside space-y-1 text-gray-300 text-sm">
                              <li>Log in using Google OAuth</li>
                              <li>Navigate to the EC2 management page</li>
                              <li>Create a new instance using the interactive form</li>
                            </ol>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Architecture */}
                <TabsContent value="architecture" className="space-y-6">
                  <Card className="glassmorphism">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-cyan-400">
                        <Layers className="h-5 w-5" />
                        <span>Architecture Overview</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div>
                        <h4 className="font-medium text-cyan-400 mb-4">Technology Stack</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {techStack.map((tech, index) => (
                            <div key={index} className="p-3 rounded-lg bg-black/30 border border-white/10">
                              <div className="flex items-center justify-between">
                                <span className={`font-medium ${tech.color}`}>{tech.name}</span>
                              </div>
                              <p className="text-sm text-gray-400 mt-1">{tech.description}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      <Separator className="bg-white/10" />

                      <div>
                        <h4 className="font-medium text-cyan-400 mb-4">Why These Technologies?</h4>
                        <Accordion type="single" collapsible>
                          <AccordionItem value="flask" className="border-white/10">
                            <AccordionTrigger className="text-green-400">Flask for Backend</AccordionTrigger>
                            <AccordionContent>
                              <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
                                <li>Lightweight and flexible</li>
                                <li>Easy integration with Python libraries</li>
                                <li>Scalable with extensions</li>
                              </ul>
                            </AccordionContent>
                          </AccordionItem>

                          <AccordionItem value="nextjs" className="border-white/10">
                            <AccordionTrigger className="text-blue-400">Next.js for Frontend</AccordionTrigger>
                            <AccordionContent>
                              <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
                                <li>Server-side rendering for better SEO</li>
                                <li>Built-in API routes for frontend-backend communication</li>
                                <li>Easy authentication with NextAuth.js</li>
                              </ul>
                            </AccordionContent>
                          </AccordionItem>

                          <AccordionItem value="postgresql" className="border-white/10">
                            <AccordionTrigger className="text-purple-400">PostgreSQL over MongoDB</AccordionTrigger>
                            <AccordionContent>
                              <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
                                <li>ACID compliance for financial and audit data</li>
                                <li>Strong consistency for operation logs</li>
                                <li>Structured queries for reporting</li>
                                <li>Native JSON support for flexible data</li>
                              </ul>
                            </AccordionContent>
                          </AccordionItem>

                          <AccordionItem value="terraform" className="border-white/10">
                            <AccordionTrigger className="text-yellow-400">Terraform for IaC</AccordionTrigger>
                            <AccordionContent>
                              <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
                                <li>Industry standard for infrastructure management</li>
                                <li>State management and drift detection</li>
                                <li>Declarative configuration</li>
                                <li>Multi-provider support</li>
                              </ul>
                            </AccordionContent>
                          </AccordionItem>
                        </Accordion>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Data Origin */}
                <TabsContent value="data-origin" className="space-y-6">
                  <Card className="glassmorphism cyber-glow-yellow">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-yellow-400">
                        <Search className="h-5 w-5" />
                        <span>Data Origin & Collection</span>
                      </CardTitle>
                      <CardDescription>
                        How we collected and processed data for RAG-enhanced LLM responses
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div>
                        <h4 className="font-medium text-yellow-400 mb-3">Overview</h4>
                        <p className="text-gray-300 leading-relaxed">
                          Our RAG (Retrieval-Augmented Generation) system is powered by a comprehensive web scraper that 
                          extracts structured data from official AWS documentation and integrates it with ChromaDB for 
                          semantic search. This ensures our LLM responses are grounded in accurate, up-to-date AWS information.
                        </p>
                      </div>

                      <div>
                        <h4 className="font-medium text-yellow-400 mb-4">Key Features</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {dataOriginFeatures.map((feature, index) => {
                            const Icon = feature.icon;
                            return (
                              <motion.div
                                key={feature.title}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: index * 0.1 }}
                                className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20"
                              >
                                <div className="flex items-start space-x-3">
                                  <Icon className="h-5 w-5 text-yellow-400 mt-1 flex-shrink-0" />
                                  <div>
                                    <h5 className="font-medium text-yellow-400 mb-1">{feature.title}</h5>
                                    <p className="text-sm text-gray-300">{feature.description}</p>
                                  </div>
                                </div>
                              </motion.div>
                            );
                          })}
                        </div>
                      </div>

                      <Separator className="bg-white/10" />

                      <div>
                        <h4 className="font-medium text-yellow-400 mb-4">Data Sources</h4>
                        <div className="space-y-3">
                          <div className="p-4 rounded-lg bg-black/30 border border-yellow-500/20">
                            <div className="flex items-center space-x-2 mb-2">
                              <Globe className="h-4 w-4 text-yellow-400" />
                              <span className="font-medium text-yellow-400">AWS Official Documentation</span>
                            </div>
                            <p className="text-sm text-gray-300">
                              Primary source for service documentation, best practices, and API references
                            </p>
                          </div>
                          
                          <div className="p-4 rounded-lg bg-black/30 border border-blue-500/20">
                            <div className="flex items-center space-x-2 mb-2">
                              <FileText className="h-4 w-4 text-blue-400" />
                              <span className="font-medium text-blue-400">AWS Whitepapers</span>
                            </div>
                            <p className="text-sm text-gray-300">
                              Technical whitepapers and architectural guidance documents
                            </p>
                          </div>
                          
                          <div className="p-4 rounded-lg bg-black/30 border border-green-500/20">
                            <div className="flex items-center space-x-2 mb-2">
                              <Code className="h-4 w-4 text-green-400" />
                              <span className="font-medium text-green-400">AWS SDK Documentation</span>
                            </div>
                            <p className="text-sm text-gray-300">
                              API references and code examples for various AWS SDKs
                            </p>
                          </div>
                        </div>
                      </div>

                      <Separator className="bg-white/10" />

                      <div>
                        <h4 className="font-medium text-yellow-400 mb-4">Scraper Architecture</h4>
                        <div className="space-y-4">
                          {scrapingComponents.map((component, index) => (
                            <div key={index} className="p-4 rounded-lg bg-black/30 border border-white/10">
                              <h5 className="font-medium text-white mb-2">{component.component}</h5>
                              <p className="text-sm text-gray-400 mb-3">{component.description}</p>
                              <div className="space-y-1">
                                {component.methods.map((method, methodIndex) => (
                                  <div key={methodIndex} className="flex items-center space-x-2">
                                    <Cpu className="h-3 w-3 text-green-400" />
                                    <code className="text-xs text-green-400 terminal-font">{method}</code>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <Separator className="bg-white/10" />

                      <div>
                        <h4 className="font-medium text-yellow-400 mb-3">Usage Example</h4>
                        <p className="text-gray-300 mb-3">Example command to run the data collector:</p>
                        <CodeBlock>
{`# Crawl AWS documentation starting from a specific URL
python scraper.py --url "https://docs.aws.amazon.com/ec2/" \\
                  --depth 3 \\
                  --max-pages 1000 \\
                  --output-dir "./scraped_data" \\
                  --collection-name "aws_docs"

# Search the collected data
python scraper.py --search "EC2 instance types" --n-results 5

# View collection statistics
python scraper.py --stats`}
                        </CodeBlock>
                      </div>

                      <div>
                        <h4 className="font-medium text-yellow-400 mb-3">Data Processing Pipeline</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-center">
                            <LinkIcon className="h-8 w-8 text-blue-400 mx-auto mb-2" />
                            <h5 className="font-medium text-blue-400 mb-1">1. Crawling</h5>
                            <p className="text-xs text-gray-300">Recursive URL discovery and content fetching</p>
                          </div>
                          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
                            <Filter className="h-8 w-8 text-green-400 mx-auto mb-2" />
                            <h5 className="font-medium text-green-400 mb-1">2. Processing</h5>
                            <p className="text-xs text-gray-300">Content parsing, cleaning, and structuring</p>
                          </div>
                          <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20 text-center">
                            <HardDrive className="h-8 w-8 text-purple-400 mx-auto mb-2" />
                            <h5 className="font-medium text-purple-400 mb-1">3. Storage</h5>
                            <p className="text-xs text-gray-300">Vector embedding and ChromaDB insertion</p>
                          </div>
                        </div>
                      </div>

                      <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                        <div className="flex items-start space-x-3">
                          <Info className="h-5 w-5 text-yellow-400 mt-0.5 flex-shrink-0" />
                          <div>
                            <h5 className="font-medium text-yellow-400 mb-1">Data Quality Assurance</h5>
                            <p className="text-sm text-gray-300">
                              All scraped content undergoes deduplication using MD5 hashing, text normalization, 
                              and quality filtering to ensure only relevant, high-quality AWS documentation 
                              is included in our knowledge base.
                            </p>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Security */}
                <TabsContent value="security" className="space-y-6">
                  <Card className="glassmorphism cyber-glow-red">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-red-400">
                        <Shield className="h-5 w-5" />
                        <span>Security Considerations</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                            <h4 className="font-medium text-red-400 mb-2">Authentication</h4>
                            <ul className="text-sm text-gray-300 space-y-1">
                              <li>• OAuth2-based login with NextAuth.js</li>
                              <li>• Secure session management</li>
                            </ul>
                          </div>

                          <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                            <h4 className="font-medium text-yellow-400 mb-2">Credentials Management</h4>
                            <ul className="text-sm text-gray-300 space-y-1">
                              <li>• Never commit .env files</li>
                              <li>• Use IAM roles in production</li>
                              <li>• Implement least-privilege policies</li>
                            </ul>
                          </div>
                        </div>

                        <div className="space-y-4">
                          <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                            <h4 className="font-medium text-blue-400 mb-2">Database Security</h4>
                            <ul className="text-sm text-gray-300 space-y-1">
                              <li>• Use SSL connections</li>
                              <li>• Implement row-level security</li>
                              <li>• Regular backups</li>
                            </ul>
                          </div>

                          <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                            <h4 className="font-medium text-green-400 mb-2">API Security</h4>
                            <ul className="text-sm text-gray-300 space-y-1">
                              <li>• Rate limiting on operations</li>
                              <li>• Input validation</li>
                              <li>• Audit logging</li>
                            </ul>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Troubleshooting */}
                <TabsContent value="troubleshooting" className="space-y-6">
                  <Card className="glassmorphism">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-orange-400">
                        <Wrench className="h-5 w-5" />
                        <span>Troubleshooting</span>
                      </CardTitle>
                      <CardDescription>
                        Common issues and their solutions
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {troubleshootingItems.map((item, index) => (
                          <div key={index} className="p-4 rounded-lg bg-black/30 border border-orange-500/20">
                            <div className="flex items-start space-x-3">
                              <AlertTriangle className="h-5 w-5 text-orange-400 mt-0.5 flex-shrink-0" />
                              <div className="flex-1">
                                <h4 className="font-medium text-orange-400 mb-2">{item.issue}</h4>
                                <CodeBlock>{item.solution}</CodeBlock>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Contributing */}
                <TabsContent value="contributing" className="space-y-6">
                  <Card className="glassmorphism">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-pink-400">
                        <Users className="h-5 w-5" />
                        <span>Contributing</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div>
                        <h4 className="font-medium text-pink-400 mb-3">How to Contribute</h4>
                        <ol className="list-decimal list-inside space-y-2 text-gray-300">
                          <li>Fork the repository</li>
                          <li>Create a feature branch</li>
                          <li>Commit your changes</li>
                          <li>Push to the branch</li>
                          <li>Create a Pull Request</li>
                        </ol>
                      </div>

                      <Separator className="bg-white/10" />

                      <div>
                        <h4 className="font-medium text-pink-400 mb-3">Future Enhancements</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {futureEnhancements.map((enhancement, index) => (
                            <div key={index} className="flex items-center space-x-2 p-2 rounded bg-black/30">
                              <CheckCircle className="h-4 w-4 text-gray-400" />
                              <span className="text-sm text-gray-300">{enhancement}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center space-x-4">
                        <Button variant="outline" className="border-pink-500/30 text-pink-400 hover:bg-pink-500/10">
                          <Github className="h-4 w-4 mr-2" />
                          View on GitHub
                        </Button>
                        <Button variant="outline" className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10">
                          <FileText className="h-4 w-4 mr-2" />
                          License (MIT)
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Support */}
                <TabsContent value="support" className="space-y-6">
                  <Card className="glassmorphism cyber-glow-blue">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2 text-blue-400">
                        <Mail className="h-5 w-5" />
                        <span>Support & Contact</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div>
                        <h4 className="font-medium text-blue-400 mb-3">Getting Help</h4>
                        <p className="text-gray-300 mb-4">
                          For issues and questions, please open a GitHub issue with:
                        </p>
                        <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
                          <li>Error messages</li>
                          <li>Steps to reproduce</li>
                          <li>Environment details</li>
                          <li>Relevant logs from the backend or frontend</li>
                        </ul>
                      </div>

                      <Separator className="bg-white/10" />

                      <div>
                        <h4 className="font-medium text-blue-400 mb-3">Contact Information</h4>
                        <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                          <p className="text-gray-300 mb-2">
                            For any issues or queries regarding the codebase, feel free to contact:
                          </p>
                          <div className="flex items-center space-x-2">
                            <Mail className="h-4 w-4 text-blue-400" />
                            <span className="text-blue-400 font-medium">Rohan Sen</span>
                            <span className="text-gray-400">-</span>
                            <a 
                              href="mailto:rohansen856@gmail.com" 
                              className="text-blue-400 hover:text-blue-300 transition-colors"
                            >
                              rohansen856@gmail.com
                            </a>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-4">
                        <Button className="cyber-glow-blue bg-blue-500/20 hover:bg-blue-500/30 text-blue-400">
                          <Github className="h-4 w-4 mr-2" />
                          Open Issue
                        </Button>
                        <Button 
                          variant="outline" 
                          className="border-green-500/30 text-green-400 hover:bg-green-500/10"
                          onClick={() => window.location.href = 'mailto:rohansen856@gmail.com'}
                        >
                          <Mail className="h-4 w-4 mr-2" />
                          Send Email
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}