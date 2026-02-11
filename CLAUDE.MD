# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the CSP Compute Node Counter project.

## Project Overview

This repository contains Python scripts for counting compute nodes across major cloud service providers (AWS, Azure, Google Cloud Platform). The scripts provide comprehensive visibility into all compute resources including virtual machines, Kubernetes nodes, serverless compute, and container-as-a-service offerings.

## Project Purpose

Enable users to quickly audit and count all compute resources across their multi-cloud environments with simple, easy-to-run Python scripts.

## Architecture

### Script Structure
Each cloud provider has a dedicated Python script:
- **aws_compute_counter.py**: Amazon Web Services compute inventory
- **azure_compute_counter.py**: Microsoft Azure compute inventory
- **gcp_compute_counter.py**: Google Cloud Platform compute inventory
- **all_clouds.py**: Unified script to run all providers and aggregate results

### Compute Resources Tracked

#### AWS
- **EC2 Instances**: All running and stopped virtual machines across all regions
- **EKS Nodes**: Kubernetes worker nodes in all EKS clusters
- **ECS Tasks**: Running container tasks (Fargate and EC2 launch types)
- **Lambda Functions**: Serverless compute functions (count by configured concurrency)
- **Lightsail Instances**: Simplified VPS instances
- **Batch Compute Environments**: Batch processing compute nodes

#### Azure
- **Virtual Machines**: All VMs across all subscriptions and resource groups
- **AKS Nodes**: Kubernetes worker nodes in all AKS clusters
- **Container Instances**: Azure Container Instances (ACI)
- **Azure Functions**: Serverless compute functions (count by app service plans)
- **VM Scale Sets**: Individual instances in scale sets
- **Batch Pools**: Batch processing compute nodes

#### Google Cloud Platform
- **Compute Engine VMs**: All instances across all zones and projects
- **GKE Nodes**: Kubernetes worker nodes in all GKE clusters
- **Cloud Run Services**: Container-based serverless compute instances
- **Cloud Functions**: Serverless compute functions (count by max instances)
- **App Engine Instances**: App Engine flexible and standard environment instances
- **Dataflow Workers**: Data processing compute workers

## Development Guidelines

### Python Best Practices
- Use Python 3.8+ for compatibility
- Follow PEP 8 style guidelines
- Include comprehensive error handling for API failures
- Implement retry logic for rate-limited API calls
- Use boto3 for AWS, azure-sdk for Azure, google-cloud-sdk for GCP
- Support both credential files and environment variables

### Script Requirements
- Each script must be runnable standalone
- Include `--help` flag with usage instructions
- Support `--region` or `--project` filters for targeted queries
- Provide `--verbose` flag for detailed output
- Export results to JSON/CSV formats with `--output` flag
- Handle missing credentials gracefully with clear error messages

### Authentication
- **AWS**: Use AWS CLI credentials (~/.aws/credentials) or IAM roles
- **Azure**: Use Azure CLI credentials (`az login`) or service principals
- **GCP**: Use gcloud credentials (`gcloud auth login`) or service account keys

### Output Format
Scripts should provide:
1. **Summary**: Total compute nodes by category
2. **Detailed Breakdown**: Resources by region/zone/cluster
3. **Cost Hints**: Indicate which resources are billable vs. free tier
4. **Export Options**: JSON, CSV, and human-readable table formats

## Common Commands

### Setup and Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure cloud provider credentials
aws configure  # For AWS
az login       # For Azure
gcloud auth login  # For GCP
```

### Running Scripts
```bash
# Count AWS compute nodes
python aws_compute_counter.py

# Count Azure compute nodes (specific subscription)
python azure_compute_counter.py --subscription-id <sub-id>

# Count GCP compute nodes (specific project)
python gcp_compute_counter.py --project <project-id>

# Run all providers and aggregate
python all_clouds.py

# Export results to JSON
python aws_compute_counter.py --output results.json --format json

# Verbose mode with detailed logging
python aws_compute_counter.py --verbose
```

### Development and Testing
```bash
# Run with dry-run mode (no actual API calls)
python aws_compute_counter.py --dry-run

# Test specific resource types
python aws_compute_counter.py --resources ec2,eks

# Run linting
flake8 *.py
pylint *.py

# Run tests
pytest tests/
```

## Required Permissions

### AWS IAM Permissions
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

**Important**: `ec2:DescribeRegions` is required for automatic region detection. Without this permission, users must specify regions explicitly using the `--regions` flag.

### Azure RBAC Roles
- **Reader** role at subscription level (minimum)
- Access to query Virtual Machines, AKS, Container Instances, Functions, Scale Sets

### GCP IAM Roles
- **Compute Viewer** (roles/compute.viewer)
- **Kubernetes Engine Viewer** (roles/container.viewer)
- **Cloud Functions Viewer** (roles/cloudfunctions.viewer)
- **Cloud Run Viewer** (roles/run.viewer)

## Error Handling

Scripts should gracefully handle:
- **Missing Credentials**: Clear error message with setup instructions
- **Insufficient Permissions**: List required permissions for each failed API call
- **Rate Limiting**: Implement exponential backoff and retry logic
- **Network Failures**: Timeout handling and connection error recovery
- **Partial Failures**: Continue counting other resources if one API fails

## Testing Strategy

- **Unit Tests**: Mock cloud provider APIs for isolated testing
- **Integration Tests**: Use test accounts with minimal resources
- **Dry-Run Mode**: Validate logic without making actual API calls
- **Sample Data**: Include example JSON responses for development

## Security Considerations

- Never commit credentials or API keys to the repository
- Use `.gitignore` to exclude credential files
- Support read-only operations only (no write/delete permissions)
- Implement least-privilege principle for required permissions
- Log audit trails for compliance requirements

## Documentation Standards

- Keep README.md updated with setup instructions and examples
- Document all command-line arguments and flags
- Include troubleshooting section for common errors
- Provide example outputs for each script
- Maintain CHANGELOG.md for version history
