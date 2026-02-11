"""
Unit tests for AWS Compute Counter
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAWSComputeCounter:
    """Test AWS compute counter functionality."""

    @patch('boto3.client')
    def test_get_all_regions(self, mock_boto_client):
        """Test fetching all AWS regions."""
        # Mock EC2 client response
        mock_ec2 = Mock()
        mock_ec2.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'us-west-2'},
                {'RegionName': 'eu-west-1'},
            ]
        }
        mock_boto_client.return_value = mock_ec2

        from aws_compute_counter import AWSComputeCounter

        counter = AWSComputeCounter(verbose=False)
        assert len(counter.regions) == 3
        assert 'us-east-1' in counter.regions

    @patch('boto3.client')
    def test_count_ec2_instances(self, mock_boto_client):
        """Test counting EC2 instances."""
        # Mock EC2 client with paginator
        mock_ec2 = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                'Reservations': [
                    {
                        'Instances': [
                            {
                                'InstanceId': 'i-1234567890abcdef0',
                                'InstanceType': 't2.micro',
                                'State': {'Name': 'running'}
                            }
                        ]
                    }
                ]
            }
        ]
        mock_ec2.get_paginator.return_value = mock_paginator
        mock_boto_client.return_value = mock_ec2

        from aws_compute_counter import AWSComputeCounter

        counter = AWSComputeCounter(regions=['us-east-1'], verbose=False)
        counter.count_ec2_instances()

        assert counter.results['ec2']['us-east-1'] == 1

    @patch('boto3.client')
    def test_count_lambda_functions(self, mock_boto_client):
        """Test counting Lambda functions."""
        # Mock Lambda client with paginator
        mock_lambda = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                'Functions': [
                    {
                        'FunctionName': 'test-function-1',
                        'Runtime': 'python3.9',
                        'MemorySize': 128
                    },
                    {
                        'FunctionName': 'test-function-2',
                        'Runtime': 'nodejs18.x',
                        'MemorySize': 256
                    }
                ]
            }
        ]
        mock_lambda.get_paginator.return_value = mock_paginator
        mock_boto_client.return_value = mock_lambda

        from aws_compute_counter import AWSComputeCounter

        counter = AWSComputeCounter(regions=['us-east-1'], verbose=False)
        counter.count_lambda_functions()

        assert counter.results['lambda']['us-east-1'] == 2

    def test_get_summary_empty(self):
        """Test getting summary with no resources."""
        from aws_compute_counter import AWSComputeCounter

        counter = AWSComputeCounter(regions=['us-east-1'], verbose=False)
        summary = counter.get_summary()

        assert len(summary) == 0

    @patch('boto3.client')
    def test_error_handling(self, mock_boto_client):
        """Test error handling for API failures."""
        from botocore.exceptions import ClientError

        # Mock EC2 client that raises an error
        mock_ec2 = Mock()
        mock_ec2.get_paginator.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'DescribeInstances'
        )
        mock_boto_client.return_value = mock_ec2

        from aws_compute_counter import AWSComputeCounter

        counter = AWSComputeCounter(regions=['us-east-1'], verbose=False)
        # Should not raise exception, just log error
        counter.count_ec2_instances()

        # No results should be recorded
        assert 'ec2' not in counter.results or 'us-east-1' not in counter.results['ec2']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
