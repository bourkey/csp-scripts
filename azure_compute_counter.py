#!/usr/bin/env python3
"""
Azure Compute Node Counter

Counts all compute resources across Azure including Virtual Machines, AKS nodes,
Container Instances, Azure Functions, VM Scale Sets, and Batch pools.
"""

import json
import csv
import sys
from collections import defaultdict
from datetime import datetime

import click
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.batch import BatchManagementClient
from azure.mgmt.resource import SubscriptionClient
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)


class AzureComputeCounter:
    """Count compute resources across Azure services."""

    def __init__(self, subscription_id=None, verbose=False):
        """
        Initialize Azure compute counter.

        Args:
            subscription_id: Azure subscription ID (None for all subscriptions)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.subscription_id = subscription_id
        self.subscriptions = []
        self.results = defaultdict(lambda: defaultdict(int))
        self.subscription_details = defaultdict(lambda: defaultdict(list))

        # Initialize credentials
        try:
            self.credential = DefaultAzureCredential()
            # Test credential
            subscription_client = SubscriptionClient(self.credential)
            list(subscription_client.subscriptions.list())
        except Exception:
            # Fall back to Azure CLI credential
            self._log("Falling back to Azure CLI credentials", "warning")
            self.credential = AzureCliCredential()

        self._get_subscriptions()

    def _log(self, message, level="info"):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            colors = {
                "info": Fore.CYAN,
                "success": Fore.GREEN,
                "warning": Fore.YELLOW,
                "error": Fore.RED,
            }
            print(f"{colors.get(level, '')}{message}{Style.RESET_ALL}")

    def _get_subscriptions(self):
        """Get list of Azure subscriptions."""
        try:
            subscription_client = SubscriptionClient(self.credential)

            if self.subscription_id:
                # Use specific subscription
                self.subscriptions = [{"id": self.subscription_id, "name": "Specified Subscription"}]
                self._log(f"Using subscription: {self.subscription_id}", "info")
            else:
                # Get all subscriptions
                self.subscriptions = []
                for sub in subscription_client.subscriptions.list():
                    if sub.state == "Enabled":
                        self.subscriptions.append({
                            "id": sub.subscription_id,
                            "name": sub.display_name,
                        })

                self._log(f"Found {len(self.subscriptions)} enabled subscriptions", "success")

        except Exception as e:
            self._log(f"Error getting subscriptions: {e}", "error")
            if self.subscription_id:
                self.subscriptions = [{"id": self.subscription_id, "name": "Specified Subscription"}]
            else:
                raise

    def count_virtual_machines(self):
        """Count Virtual Machines across all subscriptions."""
        self._log("Counting Virtual Machines...", "info")

        for subscription in self.subscriptions:
            sub_id = subscription["id"]
            sub_name = subscription["name"]

            try:
                compute_client = ComputeManagementClient(self.credential, sub_id)

                count = 0
                for vm in compute_client.virtual_machines.list_all():
                    count += 1
                    self.subscription_details["vms"][sub_name].append({
                        "name": vm.name,
                        "location": vm.location,
                        "size": vm.hardware_profile.vm_size,
                        "status": "running",  # Would need instance view for actual status
                    })

                if count > 0:
                    self.results["vms"][sub_name] = count
                    self._log(f"  {sub_name}: {count} VMs", "success")

            except HttpResponseError as e:
                self._log(f"  {sub_name}: Error - {e.message}", "error")
            except Exception as e:
                self._log(f"  {sub_name}: Unexpected error - {e}", "error")

    def count_aks_nodes(self):
        """Count AKS cluster nodes across all subscriptions."""
        self._log("Counting AKS nodes...", "info")

        for subscription in self.subscriptions:
            sub_id = subscription["id"]
            sub_name = subscription["name"]

            try:
                container_client = ContainerServiceClient(self.credential, sub_id)

                total_nodes = 0
                for cluster in container_client.managed_clusters.list():
                    if cluster.agent_pool_profiles:
                        for pool in cluster.agent_pool_profiles:
                            node_count = pool.count or 0
                            total_nodes += node_count

                            self.subscription_details["aks"][sub_name].append({
                                "cluster": cluster.name,
                                "pool": pool.name,
                                "nodes": node_count,
                                "vm_size": pool.vm_size,
                            })

                if total_nodes > 0:
                    self.results["aks"][sub_name] = total_nodes
                    self._log(f"  {sub_name}: {total_nodes} AKS nodes", "success")

            except HttpResponseError as e:
                if "NotFound" not in str(e):
                    self._log(f"  {sub_name}: Error - {e.message}", "error")
            except Exception as e:
                self._log(f"  {sub_name}: Unexpected error - {e}", "error")

    def count_container_instances(self):
        """Count Azure Container Instances across all subscriptions."""
        self._log("Counting Container Instances...", "info")

        for subscription in self.subscriptions:
            sub_id = subscription["id"]
            sub_name = subscription["name"]

            try:
                aci_client = ContainerInstanceManagementClient(self.credential, sub_id)

                count = 0
                for container_group in aci_client.container_groups.list():
                    # Each container group can have multiple containers
                    num_containers = len(container_group.containers) if container_group.containers else 1
                    count += num_containers

                    self.subscription_details["aci"][sub_name].append({
                        "name": container_group.name,
                        "location": container_group.location,
                        "containers": num_containers,
                        "state": container_group.provisioning_state,
                    })

                if count > 0:
                    self.results["aci"][sub_name] = count
                    self._log(f"  {sub_name}: {count} Container Instances", "success")

            except HttpResponseError as e:
                if "NotFound" not in str(e):
                    self._log(f"  {sub_name}: Error - {e.message}", "error")
            except Exception as e:
                self._log(f"  {sub_name}: Unexpected error - {e}", "error")

    def count_azure_functions(self):
        """Count Azure Functions across all subscriptions."""
        self._log("Counting Azure Functions...", "info")

        for subscription in self.subscriptions:
            sub_id = subscription["id"]
            sub_name = subscription["name"]

            try:
                web_client = WebSiteManagementClient(self.credential, sub_id)

                count = 0
                for app in web_client.web_apps.list():
                    # Check if it's a function app
                    if app.kind and "functionapp" in app.kind.lower():
                        count += 1

                        self.subscription_details["functions"][sub_name].append({
                            "name": app.name,
                            "location": app.location,
                            "state": app.state,
                            "kind": app.kind,
                        })

                if count > 0:
                    self.results["functions"][sub_name] = count
                    self._log(f"  {sub_name}: {count} Function Apps", "success")

            except HttpResponseError as e:
                if "NotFound" not in str(e):
                    self._log(f"  {sub_name}: Error - {e.message}", "error")
            except Exception as e:
                self._log(f"  {sub_name}: Unexpected error - {e}", "error")

    def count_vmss_instances(self):
        """Count VM Scale Set instances across all subscriptions."""
        self._log("Counting VM Scale Set instances...", "info")

        for subscription in self.subscriptions:
            sub_id = subscription["id"]
            sub_name = subscription["name"]

            try:
                compute_client = ComputeManagementClient(self.credential, sub_id)

                total_instances = 0
                for vmss in compute_client.virtual_machine_scale_sets.list_all():
                    instance_count = vmss.sku.capacity or 0
                    total_instances += instance_count

                    self.subscription_details["vmss"][sub_name].append({
                        "name": vmss.name,
                        "location": vmss.location,
                        "instances": instance_count,
                        "vm_size": vmss.sku.name,
                    })

                if total_instances > 0:
                    self.results["vmss"][sub_name] = total_instances
                    self._log(f"  {sub_name}: {total_instances} VMSS instances", "success")

            except HttpResponseError as e:
                if "NotFound" not in str(e):
                    self._log(f"  {sub_name}: Error - {e.message}", "error")
            except Exception as e:
                self._log(f"  {sub_name}: Unexpected error - {e}", "error")

    def count_batch_pools(self):
        """Count Azure Batch pool nodes across all subscriptions."""
        self._log("Counting Batch pool nodes...", "info")

        for subscription in self.subscriptions:
            sub_id = subscription["id"]
            sub_name = subscription["name"]

            try:
                batch_client = BatchManagementClient(self.credential, sub_id)

                total_nodes = 0
                for account in batch_client.batch_account.list():
                    try:
                        resource_group = account.id.split("/")[4]  # Extract RG from resource ID

                        for pool in batch_client.pool.list_by_batch_account(resource_group, account.name):
                            # Get current dedicated and low-priority node counts
                            dedicated = pool.current_dedicated_nodes or 0
                            low_priority = pool.current_low_priority_nodes or 0
                            pool_total = dedicated + low_priority
                            total_nodes += pool_total

                            if pool_total > 0:
                                self.subscription_details["batch"][sub_name].append({
                                    "account": account.name,
                                    "pool": pool.name,
                                    "dedicated_nodes": dedicated,
                                    "low_priority_nodes": low_priority,
                                })
                    except Exception as e:
                        self._log(f"  Error processing batch account {account.name}: {e}", "error")

                if total_nodes > 0:
                    self.results["batch"][sub_name] = total_nodes
                    self._log(f"  {sub_name}: {total_nodes} Batch nodes", "success")

            except HttpResponseError as e:
                if "NotFound" not in str(e):
                    self._log(f"  {sub_name}: Error - {e.message}", "error")
            except Exception as e:
                self._log(f"  {sub_name}: Unexpected error - {e}", "error")

    def count_all(self):
        """Count all compute resources."""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Starting Azure Compute Node Count{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Scanning {len(self.subscriptions)} subscriptions...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

        self.count_virtual_machines()
        self.count_aks_nodes()
        self.count_container_instances()
        self.count_azure_functions()
        self.count_vmss_instances()
        self.count_batch_pools()

    def get_summary(self):
        """Generate summary statistics."""
        summary = []
        resource_types = {
            "vms": "Virtual Machines",
            "aks": "AKS Nodes",
            "aci": "Container Instances",
            "functions": "Azure Functions",
            "vmss": "VM Scale Set Instances",
            "batch": "Batch Pool Nodes",
        }

        for resource_key, resource_name in resource_types.items():
            if resource_key in self.results:
                total = sum(self.results[resource_key].values())
                subscriptions = self.results[resource_key]

                # Format subscription details
                sub_str = ", ".join([f"{s[:30]}... ({c})" if len(s) > 30 else f"{s} ({c})"
                                    for s, c in sorted(subscriptions.items())])

                summary.append([resource_name, total, sub_str])

        return summary

    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.get_summary()

        if not summary:
            print(f"\n{Fore.YELLOW}No compute resources found.{Style.RESET_ALL}")
            return

        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Azure Compute Node Summary{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")

        headers = ["Resource Type", "Count", "Subscriptions"]
        print(tabulate(summary, headers=headers, tablefmt="simple"))

        total = sum(row[1] for row in summary)
        print(f"{Fore.GREEN}{'-'*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Total Compute Nodes: {total:,}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")

    def export_json(self, output_file):
        """Export results to JSON format."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": "azure",
            "summary": {
                resource: sum(subs.values())
                for resource, subs in self.results.items()
            },
            "details": dict(self.results),
            "subscription_details": dict(self.subscription_details),
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"{Fore.GREEN}Results exported to {output_file}{Style.RESET_ALL}")

    def export_csv(self, output_file):
        """Export results to CSV format."""
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Resource Type", "Subscription", "Count"])

            for resource, subscriptions in self.results.items():
                for subscription, count in subscriptions.items():
                    writer.writerow([resource, subscription, count])

        print(f"{Fore.GREEN}Results exported to {output_file}{Style.RESET_ALL}")


@click.command()
@click.option(
    "--subscription-id",
    help="Azure subscription ID (default: all enabled subscriptions)",
    default=None,
)
@click.option(
    "--output",
    help="Output file path for results",
    default=None,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "csv"], case_sensitive=False),
    help="Output format (json or csv)",
    default="json",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose output with detailed logging",
)
@click.option(
    "--resources",
    help="Comma-separated list of resources to count (vms,aks,aci,functions,vmss,batch)",
    default="vms,aks,aci,functions,vmss,batch",
)
def main(subscription_id, output, output_format, verbose, resources):
    """
    Count all compute nodes across Azure services.

    Supports Virtual Machines, AKS nodes, Container Instances, Azure Functions,
    VM Scale Sets, and Batch pool nodes.
    """
    try:
        # Parse resources
        resource_list = [r.strip() for r in resources.split(",")]

        # Initialize counter
        counter = AzureComputeCounter(subscription_id=subscription_id, verbose=verbose)

        # Count resources based on filter
        if "vms" in resource_list:
            counter.count_virtual_machines()
        if "aks" in resource_list:
            counter.count_aks_nodes()
        if "aci" in resource_list:
            counter.count_container_instances()
        if "functions" in resource_list:
            counter.count_azure_functions()
        if "vmss" in resource_list:
            counter.count_vmss_instances()
        if "batch" in resource_list:
            counter.count_batch_pools()

        # If no filters, count all
        if resources == "vms,aks,aci,functions,vmss,batch":
            counter.count_all()

        # Print summary
        counter.print_summary()

        # Export if requested
        if output:
            if output_format == "json":
                counter.export_json(output)
            elif output_format == "csv":
                counter.export_csv(output)

    except ClientAuthenticationError:
        print(f"\n{Fore.RED}Error: Azure authentication failed.{Style.RESET_ALL}")
        print("Please authenticate using one of these methods:")
        print("  1. Run 'az login' to authenticate with Azure CLI")
        print("  2. Set environment variables for service principal:")
        print("     - AZURE_CLIENT_ID")
        print("     - AZURE_CLIENT_SECRET")
        print("     - AZURE_TENANT_ID")
        print("  3. Use managed identity (if running on Azure VM/Container)")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
