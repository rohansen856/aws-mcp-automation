/**
 * API Client for AWS Flask APIs
 * Handles both streaming and non-streaming requests
 */

export interface ChatMessage {
  id: string;
  message: string;
  timestamp: Date;
  status: 'info' | 'success' | 'error' | 'warning' | 'assistant';
  isStreaming?: boolean;
}

export interface ApiResponse {
  status: 'info' | 'success' | 'error' | 'warning' | 'assistant';
  message: string;
  data?: any;
}

export interface QueryResponse {
  response: string;
  timestamp: string;
  status: string;
}

export interface HelpResponse {
  examples: Array<{
    category: string;
    queries: string[];
  }>;
}

// API Configuration
const CLIENT_API_URL = process.env.NEXT_PUBLIC_CLIENT_API_URL || "http://localhost:5001";
const AWS_API_URL = process.env.NEXT_PUBLIC_AWS_API_URL || "http://localhost:5000";

/**
 * Stream chat messages from the API
 */
export async function* streamChat(
  message: string,
  sessionId: string = "demo"
): AsyncGenerator<ApiResponse, void, unknown> {
  const url = `${CLIENT_API_URL}/chat`;
  const data = {
    message,
    session_id: sessionId
  };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body reader available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.trim()) {
          try {
            const parsed = JSON.parse(line);
            yield parsed as ApiResponse;
          } catch (error) {
            console.error('Failed to parse line:', line, error);
            yield {
              status: 'error',
              message: `Failed to parse response: ${line}`
            };
          }
        }
      }
    }
  } catch (error) {
    console.error('Streaming error:', error);
    yield {
      status: 'error',
      message: error instanceof Error ? error.message : 'Unknown streaming error'
    };
  }
}

/**
 * Send a simple query (non-streaming)
 */
export async function simpleQuery(query: string): Promise<QueryResponse> {
  const url = `${CLIENT_API_URL}/query`;
  const data = { query };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : 'Query failed');
  }
}

/**
 * List EC2 instances with streaming response
 */
export async function* listEC2Instances(): AsyncGenerator<ApiResponse, void, unknown> {
  const url = `${AWS_API_URL}/ec2/instances`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body reader available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.trim()) {
          try {
            const parsed = JSON.parse(line);
            yield parsed as ApiResponse;
          } catch (error) {
            console.error('Failed to parse line:', line, error);
            yield {
              status: 'error',
              message: `Failed to parse response: ${line}`
            };
          }
        }
      }
    }
  } catch (error) {
    console.error('EC2 listing error:', error);
    yield {
      status: 'error',
      message: error instanceof Error ? error.message : 'Failed to list EC2 instances'
    };
  }
}

/**
 * Create S3 bucket (non-streaming)
 */
export async function createS3Bucket(
  bucketName: string,
  encryption: boolean = true,
  versioning: boolean = false
): Promise<ApiResponse> {
  const url = `${AWS_API_URL}/s3/buckets`;
  const data = {
    bucket_name: bucketName,
    encryption,
    versioning
  };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    return {
      status: 'success',
      message: result.message || 'S3 bucket created successfully',
      data: result
    };
  } catch (error) {
    return {
      status: 'error',
      message: error instanceof Error ? error.message : 'Failed to create S3 bucket'
    };
  }
}

/**
 * Get help information
 */
export async function getHelp(): Promise<HelpResponse> {
  const url = `${CLIENT_API_URL}/help`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : 'Failed to get help');
  }
}

/**
 * Utility function to get status emoji
 */
export function getStatusEmoji(status: string): string {
  switch (status) {
    case 'error':
      return '❌';
    case 'success':
      return '✅';
    case 'warning':
      return '⚠️';
    case 'assistant':
      return '🤖';
    default:
      return 'ℹ️';
  }
}

/**
 * Utility function to generate unique IDs
 */
export function generateId(): string {
  return Math.random().toString(36).substr(2, 9);
}