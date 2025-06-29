# AWS MCP Automation Server

A natural language interface for AWS resource management using the MCP (Model-Context-Protocol) framework. This system allows non-technical users to interact with AWS services through conversational commands. The backend is powered by Flask APIs, and the frontend is built with Next.js, featuring authentication and a modern user interface.

## 🚀 Features

- **Natural Language AWS Management**: Control AWS resources using plain English
- **Infrastructure as Code**: Terraform integration for reproducible deployments
- **Comprehensive Audit Logging**: PostgreSQL-based tracking of all operations
- **Cost Analysis & Visualization**: Generate cost reports and graphs
- **RAG-Enhanced Responses**: Knowledge base for AWS best practices using ChromaDB
- **Multi-Service Support**: EC2, S3, Cost Explorer, and generic AWS commands
- **Interactive Session Management**: Maintains context across conversations
- **Secure Authentication**: Next.js frontend with OAuth2-based login

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Terraform (optional, for IaC features)
- Ollama with Granite 3.3 model
- AWS Account with appropriate permissions
- Node.js 16+ and npm/yarn for the frontend

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd aws-mcp-automation
```

### 2. Install Backend Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL Database

```bash
# Create database and tables
psql -U postgres -f init_database.sql
```

### 4. Configure Backend Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials, database configuration, and Flask settings:

```env
# AWS Credentials
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
SECRET_KEY=your_secret_key
```

### 5. Install Ollama and Model

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the Granite 3.3 model
ollama pull granite3.3
```

### 6. Install Terraform (Optional)

For Infrastructure as Code features:

```bash
# macOS
brew install terraform

# Linux
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

### 7. Install Frontend Dependencies

```bash
cd ../website
npm install
```

### 8. Configure Frontend Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.local.example .env.local
```

Edit `.env.local` with your API endpoint and authentication settings:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_nextauth_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

## 🚀 Running the Service

### Start the Backend Server

```bash
cd api
python server.py
```

### Start the Frontend Server
- open up a new terminal and run:

```bash
cd website
npm run dev
```

- Access the application at `http://localhost:3000`.

## 💬 Example Interactions

### Backend API Example

```
POST /api/ec2/instances
{
   "instance_type": "t2.micro",
   "name": "ubuntu-server",
   "use_terraform": true
}
```

Response:
```json
{
   "status": "success",
   "message": "EC2 instance created successfully",
   "data": {
      "instance_id": "i-0a1b2c3d4e5f6g7h8",
      "public_ip": "54.123.45.67"
   }
}
```

### Frontend Example

1. Log in using Google OAuth.
2. Navigate to the EC2 management page.
3. Create a new instance using the interactive form.

## 🏗️ Architecture

### Technology Stack

- **Flask**: Backend API framework
- **Next.js**: Frontend framework with server-side rendering
- **PostgreSQL**: ACID-compliant database for audit logs and state
- **Terraform**: Infrastructure as Code for AWS resources
- **Ollama + Granite 3.3**: LLM for natural language processing
- **ChromaDB**: Vector database for RAG functionality
- **Plotly**: Interactive visualization library
- **Boto3**: AWS SDK for Python

### Why These Technologies?

1. **Flask for Backend**:
    - Lightweight and flexible
    - Easy integration with Python libraries
    - Scalable with extensions

2. **Next.js for Frontend**:
    - Server-side rendering for better SEO
    - Built-in API routes for frontend-backend communication
    - Easy authentication with NextAuth.js

3. **PostgreSQL over MongoDB**:
    - ACID compliance for financial and audit data
    - Strong consistency for operation logs
    - Structured queries for reporting
    - Native JSON support for flexible data

4. **Terraform for IaC**:
    - Industry standard for infrastructure management
    - State management and drift detection
    - Declarative configuration
    - Multi-provider support

5. **ChromaDB for RAG**:
    - Persistent client for knowledge base storage
    - Good performance for small-medium knowledge bases
    - Easy integration with Python

6. **Plotly for Visualization**:
    - Interactive charts
    - JSON serialization for storage
    - Wide variety of chart types

## 🔒 Security Considerations

1. **Authentication**:
    - OAuth2-based login with NextAuth.js
    - Secure session management

2. **Credentials Management**:
    - Never commit `.env` files
    - Use IAM roles in production
    - Implement least-privilege policies

3. **Database Security**:
    - Use SSL connections
    - Implement row-level security
    - Regular backups

4. **API Security**:
    - Rate limiting on operations
    - Input validation
    - Audit logging

## 🔄 Future Enhancements

- [ ] Multi-region support
- [ ] Real-time cost alerts
- [ ] CloudFormation integration
- [ ] AWS Organizations support
- [ ] Web UI interface for advanced operations
- [ ] Scheduled operations
- [ ] Advanced IAM management
- [ ] Backup and disaster recovery automation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Error**:
    ```bash
    # Check PostgreSQL is running
    sudo systemctl status postgresql
    ```

2. **AWS Credentials Error**:
    ```bash
    # Verify credentials
    aws sts get-caller-identity
    ```

3. **Ollama Model Not Found**:
    ```bash
    # List available models
    ollama list
    
    # Pull model if missing
    ollama pull granite3.3
    ```

4. **Terraform Not Found**:
    ```bash
    # Add to PATH or install
    export PATH=$PATH:/usr/local/bin/terraform
    ```

5. **Frontend Build Error**:
    ```bash
    # Ensure Node.js and npm/yarn are installed
    node -v
    npm -v
    ```

## 📧 Support

For issues and questions, please open a GitHub issue with:
- Error messages
- Steps to reproduce
- Environment details
- Relevant logs from the backend or frontend

## Contact
- For any issues or queries regarding the codebase, feel free to contact me! Rohan Sen (rohansen856@gmail.com)