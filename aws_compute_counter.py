#!/usr/bin/env python3
"""
AWS Compute Node Counter

Counts all compute resources across AWS including EC2 instances, EKS nodes,
ECS tasks, Lambda functions, Lightsail instances, and Batch compute environments.
"""

import json
import csv
import sys
from collections import defaultdict
from datetime import datetime

import boto3
import click
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class AWSComputeCounter:
    """Count compute resources across AWS services."""

    def __init__(self, regions=None, verbose=False):
        """
        Initialize AWS compute counter.

        Args:
            regions: List of AWS regions to query (None for all regions)
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.regions = regions or self._get_all_regions()
        self.results = defaultdict(lambda: defaultdict(int))
        self.region_details = defaultdict(lambda: defaultdict(list))

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

    def _get_all_regions(self):
        """Get all available AWS regions."""
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            response = ec2.describe_regions()
            regions = [region["RegionName"] for region in response["Regions"]]
            self._log(f"Found {len(regions)} AWS regions", "success")
            return regions
        except Exception as e:
            self._log(f"Error getting regions, using default: {e}", "warning")
            return ["us-east-1"]

    def count_ec2_instances(self):
        """Count EC2 instances across all regions."""
        self._log("Counting EC2 instances...", "info")

        for region in self.regions:
            try:
                ec2 = boto3.client("ec2", region_name=region)
                paginator = ec2.get_paginator("describe_instances")

                count = 0
                for page in paginator.paginate():
                    for reservation in page["Reservations"]:
                        for instance in reservation["Instances"]:
                            count += 1
                            self.region_details["ec2"][region].append({
                                "id": instance["InstanceId"],
                                "type": instance["InstanceType"],
                                "state": instance["State"]["Name"],
                            })

                if count > 0:
                    self.results["ec2"][region] = count
                    self._log(f"  {region}: {count} EC2 instances", "success")

            except ClientError as e:
                self._log(f"  {region}: Error - {e}", "error")
            except Exception as e:
                self._log(f"  {region}: Unexpected error - {e}", "error")

    def count_eks_nodes(self):
        """Count EKS cluster nodes across all regions."""
        self._log("Counting EKS nodes...", "info")

        for region in self.regions:
            try:
                eks = boto3.client("eks", region_name=region)
                ec2 = boto3.client("ec2", region_name=region)

                clusters = eks.list_clusters()["clusters"]
                total_nodes = 0

                for cluster_name in clusters:
                    try:
                        # Get node groups
                        nodegroups = eks.list_nodegroups(clusterName=cluster_name)["nodegroups"]

                        for ng_name in nodegroups:
                            ng_info = eks.describe_nodegroup(
                                clusterName=cluster_name,
                                nodegroupName=ng_name
                            )["nodegroup"]

                            current_size = ng_info.get("scalingConfig", {}).get("desiredSize", 0)
                            total_nodes += current_size

                            self.region_details["eks"][region].append({
                                "cluster": cluster_name,
                                "nodegroup": ng_name,
                                "nodes": current_size,
                            })
                    except Exception as e:
                        self._log(f"  Error processing cluster {cluster_name}: {e}", "error")

                if total_nodes > 0:
                    self.results["eks"][region] = total_nodes
                    self._log(f"  {region}: {total_nodes} EKS nodes in {len(clusters)} clusters", "success")

            except ClientError as e:
                if e.response["Error"]["Code"] != "AccessDeniedException":
                    self._log(f"  {region}: Error - {e}", "error")
            except Exception as e:
                self._log(f"  {region}: Unexpected error - {e}", "error")

    def count_ecs_tasks(self):
        """Count running ECS tasks across all regions."""
        self._log("Counting ECS tasks...", "info")

        for region in self.regions:
            try:
                ecs = boto3.client("ecs", region_name=region)

                clusters = ecs.list_clusters()["clusterArns"]
                total_tasks = 0

                for cluster_arn in clusters:
                    try:
                        tasks = ecs.list_tasks(cluster=cluster_arn, desiredStatus="RUNNING")
                        task_count = len(tasks.get("taskArns", []))
                        total_tasks += task_count

                        if task_count > 0:
                            cluster_name = cluster_arn.split("/")[-1]
                            self.region_details["ecs"][region].append({
                                "cluster": cluster_name,
                                "running_tasks": task_count,
                            })
                    except Exception as e:
                        self._log(f"  Error processing cluster: {e}", "error")

                if total_tasks > 0:
                    self.results["ecs"][region] = total_tasks
                    self._log(f"  {region}: {total_tasks} running ECS tasks", "success")

            except ClientError as e:
                if e.response["Error"]["Code"] != "AccessDeniedException":
                    self._log(f"  {region}: Error - {e}", "error")
            except Exception as e:
                self._log(f"  {region}: Unexpected error - {e}", "error")

    def count_lambda_functions(self):
        """Count Lambda functions across all regions."""
        self._log("Counting Lambda functions...", "info")

        for region in self.regions:
            try:
                lambda_client = boto3.client("lambda", region_name=region)
                paginator = lambda_client.get_paginator("list_functions")

                count = 0
                for page in paginator.paginate():
                    functions = page.get("Functions", [])
                    count += len(functions)

                    for func in functions:
                        self.region_details["lambda"][region].append({
                            "name": func["FunctionName"],
                            "runtime": func.get("Runtime", "N/A"),
                            "memory": func.get("MemorySize", 0),
                        })

                if count > 0:
                    self.results["lambda"][region] = count
                    self._log(f"  {region}: {count} Lambda functions", "success")

            except ClientError as e:
                if e.response["Error"]["Code"] != "AccessDeniedException":
                    self._log(f"  {region}: Error - {e}", "error")
            except Exception as e:
                self._log(f"  {region}: Unexpected error - {e}", "error")

    def count_lightsail_instances(self):
        """Count Lightsail instances across all regions."""
        self._log("Counting Lightsail instances...", "info")

        for region in self.regions:
            try:
                lightsail = boto3.client("lightsail", region_name=region)
                response = lightsail.get_instances()

                instances = response.get("instances", [])
                count = len(instances)

                if count > 0:
                    for instance in instances:
                        self.region_details["lightsail"][region].append({
                            "name": instance["name"],
                            "blueprint": instance.get("blueprintName", "N/A"),
                            "state": instance["state"]["name"],
                        })

                    self.results["lightsail"][region] = count
                    self._log(f"  {region}: {count} Lightsail instances", "success")

            except ClientError as e:
                if e.response["Error"]["Code"] not in ["AccessDeniedException", "InvalidInputException"]:
                    self._log(f"  {region}: Error - {e}", "error")
            except Exception as e:
                self._log(f"  {region}: Unexpected error - {e}", "error")

    def count_batch_compute(self):
        """Count AWS Batch compute environments across all regions."""
        self._log("Counting Batch compute environments...", "info")

        for region in self.regions:
            try:
                batch = boto3.client("batch", region_name=region)
                response = batch.describe_compute_environments()

                environments = response.get("computeEnvironments", [])
                total_instances = 0

                for env in environments:
                    if env["state"] == "ENABLED":
                        # Get desired vCPUs as a proxy for compute nodes
                        compute_resources = env.get("computeResources", {})
                        desired = compute_resources.get("desiredvCpus", 0)

                        if desired > 0:
                            # Rough estimate: divide by 2 for node count
                            nodes = max(1, desired // 2)
                            total_instances += nodes

                            self.region_details["batch"][region].append({
                                "name": env["computeEnvironmentName"],
                                "vcpus": desired,
                                "estimated_nodes": nodes,
                            })

                if total_instances > 0:
                    self.results["batch"][region] = total_instances
                    self._log(f"  {region}: ~{total_instances} Batch compute nodes", "success")

            except ClientError as e:
                if e.response["Error"]["Code"] != "AccessDeniedException":
                    self._log(f"  {region}: Error - {e}", "error")
            except Exception as e:
                self._log(f"  {region}: Unexpected error - {e}", "error")

    def count_all(self):
        """Count all compute resources."""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Starting AWS Compute Node Count{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Scanning {len(self.regions)} regions...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

        self.count_ec2_instances()
        self.count_eks_nodes()
        self.count_ecs_tasks()
        self.count_lambda_functions()
        self.count_lightsail_instances()
        self.count_batch_compute()

    def get_summary(self):
        """Generate summary statistics."""
        summary = []
        resource_types = {
            "ec2": "EC2 Instances",
            "eks": "EKS Nodes",
            "ecs": "ECS Tasks (Running)",
            "lambda": "Lambda Functions",
            "lightsail": "Lightsail Instances",
            "batch": "Batch Compute Nodes",
        }

        for resource_key, resource_name in resource_types.items():
            if resource_key in self.results:
                total = sum(self.results[resource_key].values())
                regions = self.results[resource_key]

                # Format region details
                region_str = ", ".join([f"{r} ({c})" for r, c in sorted(regions.items())])

                summary.append([resource_name, total, region_str])

        return summary

    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.get_summary()

        if not summary:
            print(f"\n{Fore.YELLOW}No compute resources found.{Style.RESET_ALL}")
            return

        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}AWS Compute Node Summary{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")

        headers = ["Resource Type", "Count", "Regions"]
        print(tabulate(summary, headers=headers, tablefmt="simple"))

        total = sum(row[1] for row in summary)
        print(f"{Fore.GREEN}{'-'*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Total Compute Nodes: {total:,}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")

    def export_json(self, output_file):
        """Export results to JSON format."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": "aws",
            "summary": {
                resource: sum(regions.values())
                for resource, regions in self.results.items()
            },
            "details": dict(self.results),
            "region_details": dict(self.region_details),
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"{Fore.GREEN}Results exported to {output_file}{Style.RESET_ALL}")

    def export_csv(self, output_file):
        """Export results to CSV format."""
        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Resource Type", "Region", "Count"])

            for resource, regions in self.results.items():
                for region, count in regions.items():
                    writer.writerow([resource, region, count])

        print(f"{Fore.GREEN}Results exported to {output_file}{Style.RESET_ALL}")


@click.command()
@click.option(
    "--regions",
    help="Comma-separated list of AWS regions (default: all regions)",
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
    help="Comma-separated list of resources to count (ec2,eks,ecs,lambda,lightsail,batch)",
    default="ec2,eks,ecs,lambda,lightsail,batch",
)
def main(regions, output, output_format, verbose, resources):
    """
    Count all compute nodes across AWS services.

    Supports EC2 instances, EKS nodes, ECS tasks, Lambda functions,
    Lightsail instances, and Batch compute environments.
    """
    try:
        # Parse regions
        region_list = None
        if regions:
            region_list = [r.strip() for r in regions.split(",")]

        # Parse resources
        resource_list = [r.strip() for r in resources.split(",")]

        # Initialize counter
        counter = AWSComputeCounter(regions=region_list, verbose=verbose)

        # Count resources based on filter
        if "ec2" in resource_list:
            counter.count_ec2_instances()
        if "eks" in resource_list:
            counter.count_eks_nodes()
        if "ecs" in resource_list:
            counter.count_ecs_tasks()
        if "lambda" in resource_list:
            counter.count_lambda_functions()
        if "lightsail" in resource_list:
            counter.count_lightsail_instances()
        if "batch" in resource_list:
            counter.count_batch_compute()

        # If no filters, count all
        if resources == "ec2,eks,ecs,lambda,lightsail,batch":
            counter.count_all()

        # Print summary
        counter.print_summary()

        # Export if requested
        if output:
            if output_format == "json":
                counter.export_json(output)
            elif output_format == "csv":
                counter.export_csv(output)

    except (NoCredentialsError, PartialCredentialsError):
        print(f"\n{Fore.RED}Error: AWS credentials not found.{Style.RESET_ALL}")
        print("Please configure credentials using one of these methods:")
        print("  1. Run 'aws configure' to set up AWS CLI credentials")
        print("  2. Set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        print("  3. Use IAM role (if running on EC2/ECS/Lambda)")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
