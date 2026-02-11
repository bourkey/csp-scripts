# CSP Compute Node Counter

Python scripts to count and inventory all compute nodes across AWS, Azure, and Google Cloud Platform. Get comprehensive visibility into virtual machines, Kubernetes nodes, serverless compute, and container services across your multi-cloud infrastructure.

## Features

- **Multi-Cloud Support**: AWS, Azure, and Google Cloud Platform
- **Comprehensive Coverage**: VMs, Kubernetes, serverless, and containers
- **Easy to Run**: Simple Python scripts with minimal dependencies
- **Multiple Output Formats**: Human-readable tables, JSON, and CSV
- **Flexible Filtering**: Query specific regions, projects, or resource types
- **Secure**: Read-only operations using existing cloud credentials

## Supported Compute Resources

### Amazon Web Services (AWS)
- EC2 Instances (all regions)
- EKS Kubernetes Nodes
- ECS Container Tasks (Fargate & EC2)
- Lambda Functions
- Lightsail Instances
- AWS Batch Compute Environments

### Microsoft Azure
- Virtual Machines
- AKS Kubernetes Nodes
- Azure Container Instances (ACI)
- Azure Functions
- Virtual Machine Scale Sets
- Azure Batch Pools

### Google Cloud Platform (GCP)
- Compute Engine VMs
- GKE Kubernetes Nodes
- Cloud Run Services
- Cloud Functions
- App Engine Instances
- Dataflow Workers

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Cloud provider CLI tools (optional but recommended):
  - AWS CLI (`aws`)
  - Azure CLI (`az`)
  - Google Cloud SDK (`gcloud`)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd csp-scripts
```

2. **Create a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Authentication Setup

#### AWS
```bash
# Option 1: Configure AWS CLI
aws configure

# Option 2: Set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

#### Azure
```bash
# Option 1: Azure CLI login
az login

# Option 2: Service Principal
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

#### Google Cloud Platform
```bash
# Option 1: gcloud CLI login
gcloud auth login
gcloud config set project your-project-id

# Option 2: Service Account Key
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

## Usage

### Basic Commands

**Count AWS compute nodes:**
```bash
python aws_compute_counter.py
```

**Count Azure compute nodes:**
```bash
python azure_compute_counter.py
```

**Count GCP compute nodes:**
```bash
python gcp_compute_counter.py
```

**Run all providers at once:**
```bash
python all_clouds.py
```

### Advanced Options

**Filter by region/project:**
```bash
# AWS specific regions
python aws_compute_counter.py --regions us-east-1,us-west-2

# Azure specific subscription
python azure_compute_counter.py --subscription-id <subscription-id>

# GCP specific project
python gcp_compute_counter.py --project my-project-id
```

**Export results:**
```bash
# JSON format
python aws_compute_counter.py --output results.json --format json

# CSV format
python aws_compute_counter.py --output results.csv --format csv
```

**Verbose output:**
```bash
python aws_compute_counter.py --verbose
```

**Count specific resource types:**
```bash
python aws_compute_counter.py --resources ec2,eks,lambda
```

## Example Output

```
AWS Compute Node Summary
================================================================================
Resource Type                Count    Regions
--------------------------------------------------------------------------------
EC2 Instances                 42      us-east-1 (25), us-west-2 (17)
EKS Nodes                     18      us-east-1 (12), eu-west-1 (6)
ECS Tasks (Running)           8       us-east-1 (8)
Lambda Functions              156     us-east-1 (100), us-west-2 (56)
Lightsail Instances           2       us-east-1 (2)
--------------------------------------------------------------------------------
Total Compute Nodes:          226
================================================================================
```

## Required Permissions

### AWS
Attach this IAM policy to your user or role:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeRegions",
        "ec2:DescribeInstances",
        "eks:ListClusters",
        "eks:DescribeCluster",
        "ecs:ListClusters",
        "ecs:ListTasks",
        "lambda:ListFunctions",
        "lightsail:GetInstances",
        "batch:DescribeComputeEnvironments"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: `ec2:DescribeRegions` is required for automatic region detection. If you don't have this permission, specify regions explicitly with `--regions`.

### Azure
Minimum required role: **Reader** at the subscription level

### Google Cloud Platform
Required IAM roles:
- `roles/compute.viewer` (Compute Engine Viewer)
- `roles/container.viewer` (Kubernetes Engine Viewer)
- `roles/cloudfunctions.viewer` (Cloud Functions Viewer)
- `roles/run.viewer` (Cloud Run Viewer)

## Troubleshooting

### Missing Credentials
```
Error: Unable to locate credentials
```
**Solution**: Configure cloud provider authentication (see Authentication Setup above)

### Insufficient Permissions
```
Error: Access denied to list EC2 instances
```
**Solution**: Ensure your credentials have the required read permissions (see Required Permissions above)

### Rate Limiting
```
Error: Rate limit exceeded
```
**Solution**: Scripts automatically implement retry logic with exponential backoff

### Network Timeouts
```
Error: Connection timeout
```
**Solution**: Check internet connectivity and cloud provider API status pages

### AWS Region Detection Failure
```
Error: Failed to retrieve AWS regions
```
**Solution**: The script cannot auto-detect available AWS regions. Specify regions explicitly:
```bash
python aws_compute_counter.py --regions us-east-1,us-west-2,eu-west-1
```
This typically happens when:
- AWS credentials are missing or invalid
- Network connectivity issues prevent API calls
- Insufficient permissions to call `ec2:DescribeRegions`

## Project Structure

```
csp-scripts/
├── README.md                    # This file
├── CLAUDE.MD                    # Claude Code project guidance
├── requirements.txt             # Python dependencies
├── aws_compute_counter.py       # AWS compute counter
├── azure_compute_counter.py     # Azure compute counter
├── gcp_compute_counter.py       # GCP compute counter
├── all_clouds.py                # Run all providers
└── tests/                       # Unit tests
    ├── test_aws.py
    ├── test_azure.py
    └── test_gcp.py
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
flake8 *.py
pylint *.py
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Security

- **Read-Only**: Scripts only perform read operations
- **No Credential Storage**: Uses existing cloud provider authentication
- **Audit Trail**: All API calls are logged for compliance
- **Least Privilege**: Only requires viewer/reader permissions

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Submit a pull request
- Contact the maintainers

## Changelog

### Version 1.0.0 (Initial Release)
- AWS compute node counting
- Azure compute node counting
- GCP compute node counting
- Multi-cloud aggregation
- JSON/CSV export functionality
- Comprehensive error handling
