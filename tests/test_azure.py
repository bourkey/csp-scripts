"""
Unit tests for Azure Compute Counter
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAzureComputeCounter:
    """Test Azure compute counter functionality."""

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.mgmt.resource.SubscriptionClient')
    def test_get_subscriptions(self, mock_sub_client, mock_creds):
        """Test fetching Azure subscriptions."""
        # Mock subscription client
        mock_subscription = Mock()
        mock_subscription.subscription_id = 'sub-12345'
        mock_subscription.display_name = 'Test Subscription'
        mock_subscription.state = 'Enabled'

        mock_client = Mock()
        mock_client.subscriptions.list.return_value = [mock_subscription]
        mock_sub_client.return_value = mock_client

        from azure_compute_counter import AzureComputeCounter

        counter = AzureComputeCounter(verbose=False)
        assert len(counter.subscriptions) == 1
        assert counter.subscriptions[0]['id'] == 'sub-12345'

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.mgmt.resource.SubscriptionClient')
    @patch('azure.mgmt.compute.ComputeManagementClient')
    def test_count_virtual_machines(self, mock_compute_client, mock_sub_client, mock_creds):
        """Test counting Azure Virtual Machines."""
        # Setup mocks
        mock_subscription = Mock()
        mock_subscription.subscription_id = 'sub-12345'
        mock_subscription.display_name = 'Test Subscription'
        mock_subscription.state = 'Enabled'

        mock_sub_client_instance = Mock()
        mock_sub_client_instance.subscriptions.list.return_value = [mock_subscription]
        mock_sub_client.return_value = mock_sub_client_instance

        # Mock VMs
        mock_vm = Mock()
        mock_vm.name = 'test-vm-1'
        mock_vm.location = 'eastus'
        mock_vm.hardware_profile.vm_size = 'Standard_B2s'

        mock_compute_instance = Mock()
        mock_compute_instance.virtual_machines.list_all.return_value = [mock_vm]
        mock_compute_client.return_value = mock_compute_instance

        from azure_compute_counter import AzureComputeCounter

        counter = AzureComputeCounter(verbose=False)
        counter.count_virtual_machines()

        assert counter.results['vms']['Test Subscription'] == 1

    @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.mgmt.resource.SubscriptionClient')
    @patch('azure.mgmt.containerservice.ContainerServiceClient')
    def test_count_aks_nodes(self, mock_container_client, mock_sub_client, mock_creds):
        """Test counting AKS nodes."""
        # Setup subscription mock
        mock_subscription = Mock()
        mock_subscription.subscription_id = 'sub-12345'
        mock_subscription.display_name = 'Test Subscription'
        mock_subscription.state = 'Enabled'

        mock_sub_client_instance = Mock()
        mock_sub_client_instance.subscriptions.list.return_value = [mock_subscription]
        mock_sub_client.return_value = mock_sub_client_instance

        # Mock AKS cluster
        mock_pool = Mock()
        mock_pool.name = 'nodepool1'
        mock_pool.count = 3
        mock_pool.vm_size = 'Standard_DS2_v2'

        mock_cluster = Mock()
        mock_cluster.name = 'test-cluster'
        mock_cluster.agent_pool_profiles = [mock_pool]

        mock_container_instance = Mock()
        mock_container_instance.managed_clusters.list.return_value = [mock_cluster]
        mock_container_client.return_value = mock_container_instance

        from azure_compute_counter import AzureComputeCounter

        counter = AzureComputeCounter(verbose=False)
        counter.count_aks_nodes()

        assert counter.results['aks']['Test Subscription'] == 3

    def test_get_summary_empty(self):
        """Test getting summary with no resources."""
        with patch('azure.identity.DefaultAzureCredential'):
            with patch('azure.mgmt.resource.SubscriptionClient'):
                from azure_compute_counter import AzureComputeCounter

                counter = AzureComputeCounter(subscription_id='test-sub', verbose=False)
                summary = counter.get_summary()

                assert len(summary) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
