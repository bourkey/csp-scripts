#!/usr/bin/env python3
"""
Google Cloud Platform Compute Node Counter

Counts all compute resources across GCP including Compute Engine VMs, GKE nodes,
Cloud Run services, Cloud Functions, App Engine instances, and Dataflow workers.
"""

import json
import csv
import sys
from collections import defaultdict
from datetime import datetime

import click
from google.cloud import compute_v1
from google.cloud import container_v1
from google.cloud import run_v2
from google.cloud import functions_v1
from google.cloud import appengine_v1
from google.cloud import resourcemanager_v3
from google.auth import default as google_auth_default
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import GoogleAPIError, PermissionDenied
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)


class GCPComputeCounter:
    """Count compute resources across GCP services."""

    def __init__(self, project_id=None, verbose=False):
        """
        Initialize GCP compute counter.

        Args:
            project_id: GCP project ID (None for default project)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.project_id = project_id
        self.projects = []
        self.results = defaultdict(lambda: defaultdict(int))
        self.project_details = defaultdict(lambda: defaultdict(list))

        # Initialize credentials
        try:
            self.credentials, default_project = google_auth_default()
            if not self.project_id:
                self.project_id = default_project

            self._get_projects()
        except DefaultCredentialsError as e:
            raise Exception("GCP credentials not found. Please run 'gcloud auth login'") from e

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

    def _get_projects(self):
        """Get list of GCP projects."""
        if self.project_id:
            # Use specific project
            self.projects = [{"id": self.project_id, "name": self.project_id}]
            self._log(f"Using project: {self.project_id}", "info")
        else:
            # Try to get all projects (requires resourcemanager.projects.list permission)
            try:
                client = resourcemanager_v3.ProjectsClient(credentials=self.credentials)
                request = resourcemanager_v3.SearchProjectsRequest()

                self.projects = []
                for project in client.search_projects(request=request):
                    if project.state == resourcemanager_v3.Project.State.ACTIVE:
                        self.projects.append({
                            "id": project.project_id,
                            "name": project.display_name or project.project_id,
                        })

                self._log(f"Found {len(self.projects)} active projects", "success")
            except Exception as e:
                self._log(f"Could not list all projects: {e}", "warning")
                if self.project_id:
                    self.projects = [{"id": self.project_id, "name": self.project_id}]
                else:
                    raise Exception("No project specified and unable to list projects")

    def count_compute_engine_vms(self):
        """Count Compute Engine VM instances across all projects."""
        self._log("Counting Compute Engine VMs...", "info")

        for project in self.projects:
            project_id = project["id"]
            project_name = project["name"]

            try:
                client = compute_v1.InstancesClient(credentials=self.credentials)

                count = 0
                # List instances across all zones
                aggregated_list = client.aggregated_list(project=project_id)

                for zone, response in aggregated_list:
                    if response.instances:
                        for instance in response.instances:
                            count += 1
                            zone_name = zone.split("/")[-1]

                            self.project_details["gce"][project_name].append({
                                "name": instance.name,
                                "zone": zone_name,
                                "machine_type": instance.machine_type.split("/")[-1],
                                "status": instance.status,
                            })

                if count > 0:
                    self.results["gce"][project_name] = count
                    self._log(f"  {project_name}: {count} Compute Engine VMs", "success")

            except PermissionDenied:
                self._log(f"  {project_name}: Permission denied", "error")
            except GoogleAPIError as e:
                self._log(f"  {project_name}: API error - {e.message}", "error")
            except Exception as e:
                self._log(f"  {project_name}: Unexpected error - {e}", "error")

    def count_gke_nodes(self):
        """Count GKE cluster nodes across all projects."""
        self._log("Counting GKE nodes...", "info")

        for project in self.projects:
            project_id = project["id"]
            project_name = project["name"]

            try:
                client = container_v1.ClusterManagerClient(credentials=self.credentials)

                total_nodes = 0
                # List clusters across all locations (zones and regions)
                parent = f"projects/{project_id}/locations/-"

                try:
                    response = client.list_clusters(parent=parent)

                    for cluster in response.clusters:
                        # Count nodes from node pools
                        for node_pool in cluster.node_pools:
                            node_count = node_pool.initial_node_count or 0
                            # Use current size if available
                            if hasattr(node_pool, 'status') and node_pool.status:
                                node_count = getattr(node_pool, 'current_node_count', node_count)

                            total_nodes += node_count

                            self.project_details["gke"][project_name].append({
                                "cluster": cluster.name,
                                "location": cluster.location,
                                "node_pool": node_pool.name,
                                "nodes": node_count,
                            })
                except GoogleAPIError:
                    pass  # GKE API might not be enabled

                if total_nodes > 0:
                    self.results["gke"][project_name] = total_nodes
                    self._log(f"  {project_name}: {total_nodes} GKE nodes", "success")

            except PermissionDenied:
                self._log(f"  {project_name}: Permission denied", "error")
            except Exception as e:
                self._log(f"  {project_name}: Unexpected error - {e}", "error")

    def count_cloud_run_services(self):
        """Count Cloud Run service instances across all projects."""
        self._log("Counting Cloud Run services...", "info")

        for project in self.projects:
            project_id = project["id"]
            project_name = project["name"]

            try:
                client = run_v2.ServicesClient(credentials=self.credentials)

                count = 0
                # List services across all locations
                parent = f"projects/{project_id}/locations/-"

                try:
                    for service in client.list_services(parent=parent):
                        # Each service counts as a compute resource
                        count += 1

                        # Get max instances if configured
                        max_instances = 1
                        if service.template and service.template.scaling:
                            max_instances = service.template.scaling.max_instance_count or 1

                        self.project_details["cloud_run"][project_name].append({
                            "name": service.name.split("/")[-1],
                            "location": service.name.split("/")[3],
                            "max_instances": max_instances,
                        })
                except GoogleAPIError:
                    pass  # Cloud Run API might not be enabled

                if count > 0:
                    self.results["cloud_run"][project_name] = count
                    self._log(f"  {project_name}: {count} Cloud Run services", "success")

            except PermissionDenied:
                self._log(f"  {project_name}: Permission denied", "error")
            except Exception as e:
                self._log(f"  {project_name}: Unexpected error - {e}", "error")

    def count_cloud_functions(self):
        """Count Cloud Functions across all projects."""
        self._log("Counting Cloud Functions...", "info")

        for project in self.projects:
            project_id = project["id"]
            project_name = project["name"]

            try:
                client = functions_v1.CloudFunctionsServiceClient(credentials=self.credentials)

                count = 0
                # List functions across all locations
                parent = f"projects/{project_id}/locations/-"

                try:
                    for function in client.list_functions(parent=parent):
                        count += 1

                        self.project_details["cloud_functions"][project_name].append({
                            "name": function.name.split("/")[-1],
                            "location": function.name.split("/")[3],
                            "runtime": function.runtime,
                            "status": function.status.name if hasattr(function, 'status') else "ACTIVE",
                        })
                except GoogleAPIError:
                    pass  # Cloud Functions API might not be enabled

                if count > 0:
                    self.results["cloud_functions"][project_name] = count
                    self._log(f"  {project_name}: {count} Cloud Functions", "success")

            except PermissionDenied:
                self._log(f"  {project_name}: Permission denied", "error")
            except Exception as e:
                self._log(f"  {project_name}: Unexpected error - {e}", "error")

    def count_app_engine_instances(self):
        """Count App Engine instances across all projects."""
        self._log("Counting App Engine instances...", "info")

        for project in self.projects:
            project_id = project["id"]
            project_name = project["name"]

            try:
                client = appengine_v1.InstancesClient(credentials=self.credentials)

                count = 0
                parent = f"apps/{project_id}/services/-/versions/-"

                try:
                    for instance in client.list_instances(parent=parent):
                        count += 1

                        self.project_details["app_engine"][project_name].append({
                            "id": instance.name.split("/")[-1],
                            "service": instance.name.split("/")[3],
                            "version": instance.name.split("/")[5],
                        })
                except GoogleAPIError:
                    pass  # App Engine might not be enabled or have no instances

                if count > 0:
                    self.results["app_engine"][project_name] = count
                    self._log(f"  {project_name}: {count} App Engine instances", "success")

            except PermissionDenied:
                self._log(f"  {project_name}: Permission denied", "error")
            except Exception as e:
                self._log(f"  {project_name}: Unexpected error - {e}", "error")

    def count_all(self):
        """Count all compute resources."""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Starting GCP Compute Node Count{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Scanning {len(self.projects)} project(s)...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

        self.count_compute_engine_vms()
        self.count_gke_nodes()
        self.count_cloud_run_services()
        self.count_cloud_functions()
        self.count_app_engine_instances()

    def get_summary(self):
        """Generate summary statistics."""
        summary = []
        resource_types = {
            "gce": "Compute Engine VMs",
            "gke": "GKE Nodes",
            "cloud_run": "Cloud Run Services",
            "cloud_functions": "Cloud Functions",
            "app_engine": "App Engine Instances",
        }

        for resource_key, resource_name in resource_types.items():
            if resource_key in self.results:
                total = sum(self.results[resource_key].values())
                projects = self.results[resource_key]

                # Format project details
                proj_str = ", ".join([f"{p[:30]}... ({c})" if len(p) > 30 else f"{p} ({c})"
                                     for p, c in sorted(projects.items())])

                summary.append([resource_name, total, proj_str])

        return summary

    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.get_summary()

        if not summary:
            print(f"\n{Fore.YELLOW}No compute resources found.{Style.RESET_ALL}")
            return

        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}GCP Compute Node Summary{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")

        headers = ["Resource Type", "Count", "Projects"]
        print(tabulate(summary, headers=headers, tablefmt="simple"))

        total = sum(row[1] for row in summary)
        print(f"{Fore.GREEN}{'-'*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Total Compute Nodes: {total:,}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")

    def export_json(self, output_file):
        """Export results to JSON format."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": "gcp",
            "summary": {
                resource: sum(projects.values())
                for resource, projects in self.results.items()
            },
            "details": dict(self.results),
            "project_details": dict(self.project_details),
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"{Fore.GREEN}Results exported to {output_file}{Style.RESET_ALL}")

    def export_csv(self, output_file):
        """Export results to CSV format."""
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Resource Type", "Project", "Count"])

            for resource, projects in self.results.items():
                for project, count in projects.items():
                    writer.writerow([resource, project, count])

        print(f"{Fore.GREEN}Results exported to {output_file}{Style.RESET_ALL}")


@click.command()
@click.option(
    "--project",
    "project_id",
    help="GCP project ID (default: default project from gcloud config)",
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
    help="Comma-separated list of resources to count (gce,gke,cloud_run,cloud_functions,app_engine)",
    default="gce,gke,cloud_run,cloud_functions,app_engine",
)
def main(project_id, output, output_format, verbose, resources):
    """
    Count all compute nodes across GCP services.

    Supports Compute Engine VMs, GKE nodes, Cloud Run services, Cloud Functions,
    and App Engine instances.
    """
    try:
        # Parse resources
        resource_list = [r.strip() for r in resources.split(",")]

        # Initialize counter
        counter = GCPComputeCounter(project_id=project_id, verbose=verbose)

        # Count resources based on filter
        if "gce" in resource_list:
            counter.count_compute_engine_vms()
        if "gke" in resource_list:
            counter.count_gke_nodes()
        if "cloud_run" in resource_list:
            counter.count_cloud_run_services()
        if "cloud_functions" in resource_list:
            counter.count_cloud_functions()
        if "app_engine" in resource_list:
            counter.count_app_engine_instances()

        # If no filters, count all
        if resources == "gce,gke,cloud_run,cloud_functions,app_engine":
            counter.count_all()

        # Print summary
        counter.print_summary()

        # Export if requested
        if output:
            if output_format == "json":
                counter.export_json(output)
            elif output_format == "csv":
                counter.export_csv(output)

    except DefaultCredentialsError:
        print(f"\n{Fore.RED}Error: GCP credentials not found.{Style.RESET_ALL}")
        print("Please authenticate using one of these methods:")
        print("  1. Run 'gcloud auth login' to authenticate with gcloud CLI")
        print("  2. Run 'gcloud auth application-default login' for application credentials")
        print("  3. Set GOOGLE_APPLICATION_CREDENTIALS environment variable:")
        print("     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
