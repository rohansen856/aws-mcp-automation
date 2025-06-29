# AWS MCP Automation Server

A natural language interface for AWS resource management using the MCP (Model-Context-Protocol) framework. This system allows non-technical users to interact with AWS services through conversational commands.

## 🚀 Features

- **Natural Language AWS Management**: Control AWS resources using plain English
- **Infrastructure as Code**: Terraform integration for reproducible deployments
- **Comprehensive Audit Logging**: PostgreSQL-based tracking of all operations
- **Cost Analysis & Visualization**: Generate cost reports and graphs
- **RAG-Enhanced Responses**: Knowledge base for AWS best practices using ChromaDB
- **Multi-Service Support**: EC2, S3, Cost Explorer, and generic AWS commands
- **Interactive Session Management**: Maintains context across conversations

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Terraform (optional, for IaC features)
- Ollama with Granite 3.3 model
- AWS Account with appropriate permissions

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd aws-mcp-automation
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL Database

```bash
# Create database and tables
psql -U postgres -f init_database.sql
```

### 4. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials and database configuration:

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
```

### 5. Install Ollama and Model

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the Granite 3.3 model
ollama pull granite3.3
```

### 6. (Optional) Install Terraform

For Infrastructure as Code features:

```bash
# macOS
brew install terraform

# Linux
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

## 🚀 Running the Service

### Start the AWS MCP Server

```bash
python aws_mcp_server.py
```

### Connect with the Enhanced Client

In a new terminal:

```bash
python aws_client_enhanced.py aws_mcp_server.py
```

## 💬 Example Interactions

```
🔧 AWS Console> Create a t2.micro EC2 instance with Ubuntu

⏳ Processing...

I'll help you create a t2.micro EC2 instance with Ubuntu. Let me set that up for you using Terraform for better infrastructure management.

---TOOL_START---
TOOL: create_ec2_instance
INPUT: {"instance_type": "t2.micro", "name": "ubuntu-server", "use_terraform": true}
---TOOL_END---

[Tool create_ec2_instance executed]

✅ Great! I've successfully created your EC2 instance with the following details:

- **Instance Type**: t2.micro (1 vCPU, 1 GB RAM - Free tier eligible)
- **Operating System**: Ubuntu Server 22.04 LTS
- **Instance ID**: i-0a1b2c3d4e5f6g7h8
- **Public IP**: 54.123.45.67

The instance is now launching and should be ready in about 1-2 minutes. This t2.micro instance is eligible for the AWS free tier, which includes 750 hours per month for the first 12 months.

Would you like me to:
1. Show you how to connect to this instance via SSH?
2. Set up security group rules for specific access?
3. Create additional instances?
```

```
🔧 AWS Console> What's my AWS cost for the last 3 months?

⏳ Processing...

I'll analyze your AWS costs for the last 3 months and provide you with a detailed breakdown.

---TOOL_START---
TOOL: get_cost_analysis
INPUT: {"start_date": "2025-01-01", "end_date": "2025-03-31", "granularity": "MONTHLY", "generate_graph": true}
---TOOL_END---

[Tool get_cost_analysis executed]

💰 Here's your AWS cost analysis for the last 3 months:

**Total Cost**: $342.56

**Monthly Breakdown**:
- January 2025: $125.43
- February 2025: $112.78
- March 2025: $104.35

**Top Services by Cost**:
1. Amazon EC2: $185.23 (54%)
2. Amazon S3: $67.89 (20%)
3. Amazon RDS: $45.12 (13%)
4. AWS Lambda: $23.45 (7%)
5. Other services: $20.87 (6%)

📊 A visual cost chart has been generated and saved. 

**Cost Optimization Recommendations**:
1. Your EC2 costs are the highest - consider using Reserved Instances for predictable workloads
2. Review and terminate any unused EC2 instances
3. Enable S3 lifecycle policies to move infrequent data to cheaper storage classes
4. Set up AWS Budgets to get alerts before exceeding thresholds

Would you like me to help you implement any of these cost-saving measures?
```

## 🏗️ Architecture

### Technology Stack

- **FastMCP**: Server framework for tool exposure
- **PostgreSQL**: ACID-compliant database for audit logs and state
- **Terraform**: Infrastructure as Code for AWS resources
- **Ollama + Granite 3.3**: LLM for natural language processing
- **ChromaDB**: Vector database for RAG functionality
- **Plotly**: Interactive visualization library
- **Boto3**: AWS SDK for Python

### Why These Technologies?

1. **PostgreSQL over MongoDB**: 
   - ACID compliance for financial and audit data
   - Strong consistency for operation logs
   - Structured queries for reporting
   - Native JSON support for flexible data

2. **Terraform for IaC**:
   - Industry standard for infrastructure management
   - State management and drift detection
   - Declarative configuration
   - Multi-provider support

3. **ChromaDB for RAG**:
   - Persistent client for knowledge base storage
   - Good performance for small-medium knowledge bases
   - Easy integration with Python

4. **Plotly for Visualization**:
   - Interactive charts
   - JSON serialization for storage
   - Wide variety of chart types

## 📊 Database Schema

### aws_operations
- Tracks all AWS operations performed
- Includes parameters, results, and execution metrics
- Used for audit trails and debugging

### terraform_states
- Stores Terraform configurations and state
- Enables infrastructure versioning
- Supports rollback capabilities

### cost_data
- Caches AWS Cost Explorer data
- Enables historical cost analysis
- Supports custom cost reports

## 🔒 Security Considerations

1. **Credentials Management**:
   - Never commit `.env` files
   - Use IAM roles in production
   - Implement least-privilege policies

2. **Database Security**:
   - Use SSL connections
   - Implement row-level security
   - Regular backups

3. **API Security**:
   - Rate limiting on operations
   - Input validation
   - Audit logging

## 🚧 Limitations

- Single-region support per configuration
- Synchronous tool execution
- Limited to configured AWS services
- Requires manual Ollama model setup

## 🔄 Future Enhancements

- [ ] Multi-region support
- [ ] Real-time cost alerts
- [ ] CloudFormation integration
- [ ] AWS Organizations support
- [ ] Web UI interface
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

## 📧 Support

For issues and questions, please open a GitHub issue with:
- Error messages
- Steps to reproduce
- Environment details
- Relevant logs from the database