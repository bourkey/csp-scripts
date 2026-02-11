"""
Unit tests for GCP Compute Counter
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGCPComputeCounter:
    """Test GCP compute counter functionality."""

    @patch('google.auth.default')
    def test_initialization(self, mock_auth):
        """Test GCP counter initialization."""
        mock_auth.return_value = (Mock(), 'test-project')

        from gcp_compute_counter import GCPComputeCounter

        counter = GCPComputeCounter(project_id='test-project', verbose=False)
        assert counter.project_id == 'test-project'
        assert len(counter.projects) == 1

    @patch('google.auth.default')
    @patch('google.cloud.compute_v1.InstancesClient')
    def test_count_compute_engine_vms(self, mock_instances_client, mock_auth):
        """Test counting Compute Engine VMs."""
        mock_auth.return_value = (Mock(), 'test-project')

        # Mock instance
        mock_instance = Mock()
        mock_instance.name = 'test-vm-1'
        mock_instance.machine_type = 'zones/us-central1-a/machineTypes/n1-standard-1'
        mock_instance.status = 'RUNNING'

        # Mock aggregated list response
        mock_response = Mock()
        mock_response.instances = [mock_instance]

        mock_client = Mock()
        mock_client.aggregated_list.return_value = [('zones/us-central1-a', mock_response)]
        mock_instances_client.return_value = mock_client

        from gcp_compute_counter import GCPComputeCounter

        counter = GCPComputeCounter(project_id='test-project', verbose=False)
        counter.count_compute_engine_vms()

        assert counter.results['gce']['test-project'] == 1

    @patch('google.auth.default')
    @patch('google.cloud.container_v1.ClusterManagerClient')
    def test_count_gke_nodes(self, mock_cluster_client, mock_auth):
        """Test counting GKE nodes."""
        mock_auth.return_value = (Mock(), 'test-project')

        # Mock node pool
        mock_node_pool = Mock()
        mock_node_pool.name = 'default-pool'
        mock_node_pool.initial_node_count = 3

        # Mock cluster
        mock_cluster = Mock()
        mock_cluster.name = 'test-cluster'
        mock_cluster.location = 'us-central1'
        mock_cluster.node_pools = [mock_node_pool]

        # Mock response
        mock_response = Mock()
        mock_response.clusters = [mock_cluster]

        mock_client = Mock()
        mock_client.list_clusters.return_value = mock_response
        mock_cluster_client.return_value = mock_client

        from gcp_compute_counter import GCPComputeCounter

        counter = GCPComputeCounter(project_id='test-project', verbose=False)
        counter.count_gke_nodes()

        assert counter.results['gke']['test-project'] == 3

    @patch('google.auth.default')
    @patch('google.cloud.functions_v1.CloudFunctionsServiceClient')
    def test_count_cloud_functions(self, mock_functions_client, mock_auth):
        """Test counting Cloud Functions."""
        mock_auth.return_value = (Mock(), 'test-project')

        # Mock function
        mock_function = Mock()
        mock_function.name = 'projects/test-project/locations/us-central1/functions/test-function'
        mock_function.runtime = 'python39'

        mock_client = Mock()
        mock_client.list_functions.return_value = [mock_function]
        mock_functions_client.return_value = mock_client

        from gcp_compute_counter import GCPComputeCounter

        counter = GCPComputeCounter(project_id='test-project', verbose=False)
        counter.count_cloud_functions()

        assert counter.results['cloud_functions']['test-project'] == 1

    def test_get_summary_empty(self):
        """Test getting summary with no resources."""
        with patch('google.auth.default') as mock_auth:
            mock_auth.return_value = (Mock(), 'test-project')

            from gcp_compute_counter import GCPComputeCounter

            counter = GCPComputeCounter(project_id='test-project', verbose=False)
            summary = counter.get_summary()

            assert len(summary) == 0

    @patch('google.auth.default')
    def test_credentials_error(self, mock_auth):
        """Test handling of missing credentials."""
        from google.auth.exceptions import DefaultCredentialsError

        mock_auth.side_effect = DefaultCredentialsError()

        from gcp_compute_counter import GCPComputeCounter

        with pytest.raises(Exception, match="GCP credentials not found"):
            GCPComputeCounter(project_id='test-project', verbose=False)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
