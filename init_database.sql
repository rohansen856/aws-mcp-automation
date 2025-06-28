-- Create the AWS MCP database
CREATE DATABASE aws_mcp;

-- Connect to the database
\c aws_mcp;

-- Create tables
CREATE TABLE IF NOT EXISTS aws_operations (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(100) NOT NULL,
    parameters JSONB,
    result JSONB,
    status VARCHAR(50),
    error_message TEXT,
    user_query TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER
);

CREATE TABLE IF NOT EXISTS terraform_states (
    id SERIAL PRIMARY KEY,
    resource_type VARCHAR(100),
    resource_name VARCHAR(255),
    state JSONB,
    terraform_config TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cost_data (
    id SERIAL PRIMARY KEY,
    service VARCHAR(100),
    cost DECIMAL(10, 2),
    usage_type VARCHAR(255),
    date DATE,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_operations_type ON aws_operations(operation_type);
CREATE INDEX idx_operations_status ON aws_operations(status);
CREATE INDEX idx_operations_created ON aws_operations(created_at);

CREATE INDEX idx_terraform_resource ON terraform_states(resource_type, resource_name);
CREATE INDEX idx_terraform_created ON terraform_states(created_at);

CREATE INDEX idx_cost_service ON cost_data(service);
CREATE INDEX idx_cost_date ON cost_data(date);

-- Create views for common queries
CREATE VIEW recent_operations AS
SELECT 
    id,
    operation_type,
    parameters,
    status,
    error_message,
    created_at,
    execution_time_ms
FROM aws_operations
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

CREATE VIEW monthly_costs AS
SELECT 
    DATE_TRUNC('month', date) as month,
    service,
    SUM(cost) as total_cost
FROM cost_data
GROUP BY DATE_TRUNC('month', date), service
ORDER BY month DESC, total_cost DESC;

-- Grant permissions (adjust user as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;