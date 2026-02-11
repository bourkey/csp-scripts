#!/bin/bash
#
# Setup script for CSP Compute Node Counter
# This script sets up the Python environment and installs dependencies
#

set -e

echo "=========================================="
echo "CSP Compute Node Counter - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"
echo ""

# Make scripts executable
echo "Making scripts executable..."
chmod +x aws_compute_counter.py
chmod +x azure_compute_counter.py
chmod +x gcp_compute_counter.py
chmod +x all_clouds.py
echo "✓ Scripts are now executable"
echo ""

# Check for cloud CLI tools
echo "Checking for cloud provider CLI tools (optional)..."

if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1)
    echo "✓ AWS CLI found: $AWS_VERSION"
else
    echo "⚠️  AWS CLI not found (optional)"
fi

if command -v az &> /dev/null; then
    AZURE_VERSION=$(az version --output tsv 2>&1 | head -n1)
    echo "✓ Azure CLI found: $AZURE_VERSION"
else
    echo "⚠️  Azure CLI not found (optional)"
fi

if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud version 2>&1 | head -n1 | cut -d' ' -f4)
    echo "✓ Google Cloud SDK found: $GCLOUD_VERSION"
else
    echo "⚠️  Google Cloud SDK not found (optional)"
fi

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Configure cloud provider credentials:"
echo "     - AWS:   aws configure"
echo "     - Azure: az login"
echo "     - GCP:   gcloud auth login"
echo ""
echo "  3. Run a script:"
echo "     python aws_compute_counter.py"
echo "     python azure_compute_counter.py"
echo "     python gcp_compute_counter.py"
echo "     python all_clouds.py"
echo ""
echo "  4. For help on any script:"
echo "     python aws_compute_counter.py --help"
echo ""
