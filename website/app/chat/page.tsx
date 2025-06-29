"use client"

import { useState, useEffect, useRef } from "react"
import { useSession } from "next-auth/react"
import { redirect } from "next/navigation"
import { ChatMessage } from "@/components/chat/chat-message"
import { ChatInput } from "@/components/chat/chat-input"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  streamChat,
  generateId,
  type ChatMessage as ChatMessageType,
} from "@/lib/api"
import { motion } from "framer-motion"
import {
  MessageSquare,
  Activity,
  Clock,
  User,
  Server,
  Wifi,
  Database,
  Trash2,
  Download,
  Settings,
} from "lucide-react"
import { toast } from "sonner"

export default function ChatPage() {
  const { data: session, status } = useSession()
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<
    "connected" | "disconnected" | "connecting"
  >("connected")
  const [totalMessages, setTotalMessages] = useState(0)
  const [sessionStartTime] = useState(new Date())
  const [lastActivity, setLastActivity] = useState(new Date())
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const sessionId = useRef(generateId())

  useEffect(() => {
    if (status === "unauthenticated") {
      redirect("/auth/signin")
    }
  }, [status])

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    setTotalMessages(messages.length)
    if (messages.length > 0) {
      setLastActivity(new Date())
    }
  }, [messages])

  const handleSendMessage = async (message: string) => {
    setConnectionStatus("connecting")

    // Add user message
    const userMessage: ChatMessageType = {
      id: generateId(),
      message,
      timestamp: new Date(),
      status: "info",
    }

    setMessages((prev) => [...prev, userMessage])
    setIsStreaming(true)

    try {
      setConnectionStatus("connected")
      const responseStream = streamChat(message, sessionId.current)

      for await (const response of responseStream) {
        const streamMessage: ChatMessageType = {
          id: generateId(),
          message: response.message,
          timestamp: new Date(),
          status: response.status,
          isStreaming: true,
        }

        setMessages((prev) => [...prev, streamMessage])
      }
    } catch (error) {
      setConnectionStatus("disconnected")
      const errorMessage: ChatMessageType = {
        id: generateId(),
        message: `Error: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
        timestamp: new Date(),
        status: "error",
      }

      setMessages((prev) => [...prev, errorMessage])
      toast.error("Failed to send message")
    } finally {
      setIsStreaming(false)
      setConnectionStatus("connected")
    }
  }

  const clearMessages = () => {
    setMessages([])
    toast.success("Chat history cleared")
  }

  const exportChat = () => {
    const chatData = {
      sessionId: sessionId.current,
      messages: messages.map((msg) => ({
        timestamp: msg.timestamp.toISOString(),
        status: msg.status,
        message: msg.message,
      })),
      exportedAt: new Date().toISOString(),
    }

    const blob = new Blob([JSON.stringify(chatData, null, 2)], {
      type: "application/json",
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `chat-export-${sessionId.current.slice(0, 8)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast.success("Chat exported successfully")
  }

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "text-green-400 border-green-400"
      case "connecting":
        return "text-yellow-400 border-yellow-400"
      case "disconnected":
        return "text-red-400 border-red-400"
      default:
        return "text-gray-400 border-gray-400"
    }
  }

  const getSessionDuration = () => {
    const now = new Date()
    const diff = now.getTime() - sessionStartTime.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`
    }
    return `${minutes}m`
  }

  const getLastActivityTime = () => {
    const now = new Date()
    const diff = now.getTime() - lastActivity.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)

    if (minutes > 0) {
      return `${minutes}m ago`
    }
    return `${seconds}s ago`
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400 mx-auto mb-4"></div>
          <p className="text-green-400">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Status Panel */}
        <div className="w-80 border-r border-white/10 bg-black/20 backdrop-blur-md flex flex-col">
          <div className="p-4 border-b border-white/10">
            <h2 className="text-lg font-bold neon-text-green terminal-font mb-2">
              System Status
            </h2>
            <p className="text-xs text-gray-400">Real-time chat monitoring</p>
          </div>

          <div className="flex-1 p-4 space-y-4 overflow-y-auto">
            {/* Connection Status */}
            <Card className="glassmorphism">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-sm">
                  <Wifi className="h-4 w-4" />
                  <span>Connection</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center justify-between">
                  <Badge
                    variant="outline"
                    className={`terminal-font text-xs ${getConnectionStatusColor()}`}
                  >
                    {connectionStatus}
                  </Badge>
                  <div
                    className={`w-2 h-2 rounded-full ${
                      connectionStatus === "connected"
                        ? "bg-green-400"
                        : connectionStatus === "connecting"
                        ? "bg-yellow-400"
                        : "bg-red-400"
                    } ${
                      connectionStatus === "connecting" ? "animate-pulse" : ""
                    }`}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Session Info */}
            <Card className="glassmorphism">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-sm">
                  <User className="h-4 w-4" />
                  <span>Session</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-3">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">User:</span>
                  <span className="text-green-400 terminal-font">
                    {session?.user?.name || session?.user?.email || "Anonymous"}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Session ID:</span>
                  <span className="text-blue-400 terminal-font">
                    {sessionId.current.slice(0, 8)}...
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Duration:</span>
                  <span className="text-purple-400 terminal-font">
                    {getSessionDuration()}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Activity Stats */}
            <Card className="glassmorphism">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-sm">
                  <Activity className="h-4 w-4" />
                  <span>Activity</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-3">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Messages:</span>
                  <span className="text-green-400 terminal-font">
                    {totalMessages}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Status:</span>
                  <span
                    className={`terminal-font ${
                      isStreaming ? "text-yellow-400" : "text-green-400"
                    }`}
                  >
                    {isStreaming ? "Streaming" : "Ready"}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Last Activity:</span>
                  <span className="text-blue-400 terminal-font">
                    {getLastActivityTime()}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Server Info */}
            <Card className="glassmorphism">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-sm">
                  <Server className="h-4 w-4" />
                  <span>Server</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-3">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Client API:</span>
                  <span className="text-green-400 terminal-font">:5001</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">AWS API:</span>
                  <span className="text-blue-400 terminal-font">:5000</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Protocol:</span>
                  <span className="text-purple-400 terminal-font">
                    HTTP/SSE
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="glassmorphism">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-sm">
                  <Settings className="h-4 w-4" />
                  <span>Actions</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={clearMessages}
                  className="w-full justify-start text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10"
                >
                  <Trash2 className="h-3 w-3 mr-2" />
                  Clear Chat
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={exportChat}
                  disabled={messages.length === 0}
                  className="w-full justify-start text-xs text-blue-400 hover:text-blue-300 hover:bg-blue-500/10"
                >
                  <Download className="h-3 w-3 mr-2" />
                  Export Chat
                </Button>
              </CardContent>
            </Card>

            {/* System Resources */}
            <Card className="glassmorphism">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center space-x-2 text-sm">
                  <Database className="h-4 w-4" />
                  <span>Resources</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0 space-y-3">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Memory:</span>
                  <span className="text-green-400 terminal-font">
                    {Math.round(messages.length * 0.1)}KB
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Cache:</span>
                  <span className="text-yellow-400 terminal-font">Active</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Latency:</span>
                  <span className="text-blue-400 terminal-font">
                    ~{Math.floor(Math.random() * 50 + 20)}ms
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-white/10 bg-black/20 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="text-center"
            >
              <h1 className="text-3xl font-bold neon-text-green terminal-font mb-2">
                AI Chat Interface
              </h1>
              <p className="text-gray-400">
                Stream real-time conversations with AWS AI services
              </p>
            </motion.div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-hidden">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center text-center p-8">
                <div>
                  <MessageSquare className="h-16 w-16 text-green-400/50 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-green-400 mb-2">
                    Start a Conversation
                  </h3>
                  <p className="text-gray-400 mb-4">
                    Ask me anything about AWS services, costs, or resources
                  </p>
                  <div className="text-sm text-gray-500 space-y-1">
                    <p>• &quot;Show me all my EC2 instances&quot;</p>
                    <p>
                      • &quot;What&apos;s my AWS cost for the last month?&quot;
                    </p>
                    <p>
                      • &quot;Create an S3 bucket named my-demo-bucket&quot;
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <ScrollArea className="h-full p-6" ref={scrollAreaRef}>
                <div className="space-y-4 pb-4">
                  {messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      status={message.status}
                      message={message.message}
                      timestamp={message.timestamp}
                      isStreaming={message.isStreaming}
                    />
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </div>
      </div>

      {/* Docked Input Area */}
      <div className="border-t border-white/10 bg-black/30 backdrop-blur-md p-4">
        <div className="max-w-4xl mx-auto">
          <ChatInput
            onSendMessage={handleSendMessage}
            isStreaming={isStreaming}
          />
        </div>
      </div>
    </div>
  )
}
