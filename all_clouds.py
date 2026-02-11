#!/usr/bin/env python3
"""
Multi-Cloud Compute Node Counter

Aggregates compute node counts across AWS, Azure, and Google Cloud Platform.
Runs all provider scripts and combines results into a unified view.
"""

import json
import sys
import subprocess
import tempfile
import os
from datetime import datetime
from collections import defaultdict

import click
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)


class MultiCloudCounter:
    """Aggregate compute node counts across multiple cloud providers."""

    def __init__(self, verbose=False):
        """
        Initialize multi-cloud counter.

        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.results = {}
        self.errors = []
        self.temp_dir = tempfile.gettempdir()

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

    def count_aws(self, regions=None):
        """Count AWS compute resources."""
        self._log("Counting AWS resources...", "info")

        try:
            # Create temp file for results
            aws_results_file = os.path.join(self.temp_dir, "aws_results.json")

            # Build command using current Python interpreter
            cmd = [sys.executable, "aws_compute_counter.py", "--format", "json", "--output", aws_results_file]

            if regions:
                cmd.extend(["--regions", regions])

            if self.verbose:
                cmd.append("--verbose")

            # Run AWS counter
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                # Load results
                with open(aws_results_file, "r") as f:
                    self.results["aws"] = json.load(f)
                # Clean up temp file
                os.remove(aws_results_file)
                self._log("AWS counting completed successfully", "success")
            else:
                error_msg = result.stderr or result.stdout
                self._log(f"AWS counting failed: {error_msg}", "error")
                self.errors.append(f"AWS: {error_msg}")

        except FileNotFoundError:
            error_msg = "aws_compute_counter.py not found"
            self._log(error_msg, "error")
            self.errors.append(f"AWS: {error_msg}")
        except Exception as e:
            self._log(f"AWS error: {e}", "error")
            self.errors.append(f"AWS: {str(e)}")

    def count_azure(self, subscription_id=None):
        """Count Azure compute resources."""
        self._log("Counting Azure resources...", "info")

        try:
            # Create temp file for results
            azure_results_file = os.path.join(self.temp_dir, "azure_results.json")

            # Build command using current Python interpreter
            cmd = [sys.executable, "azure_compute_counter.py", "--format", "json", "--output", azure_results_file]

            if subscription_id:
                cmd.extend(["--subscription-id", subscription_id])

            if self.verbose:
                cmd.append("--verbose")

            # Run Azure counter
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                # Load results
                with open(azure_results_file, "r") as f:
                    self.results["azure"] = json.load(f)
                # Clean up temp file
                os.remove(azure_results_file)
                self._log("Azure counting completed successfully", "success")
            else:
                error_msg = result.stderr or result.stdout
                self._log(f"Azure counting failed: {error_msg}", "error")
                self.errors.append(f"Azure: {error_msg}")

        except FileNotFoundError:
            error_msg = "azure_compute_counter.py not found"
            self._log(error_msg, "error")
            self.errors.append(f"Azure: {error_msg}")
        except Exception as e:
            self._log(f"Azure error: {e}", "error")
            self.errors.append(f"Azure: {str(e)}")

    def count_gcp(self, project_id=None):
        """Count GCP compute resources."""
        self._log("Counting GCP resources...", "info")

        try:
            # Create temp file for results
            gcp_results_file = os.path.join(self.temp_dir, "gcp_results.json")

            # Build command using current Python interpreter
            cmd = [sys.executable, "gcp_compute_counter.py", "--format", "json", "--output", gcp_results_file]

            if project_id:
                cmd.extend(["--project", project_id])

            if self.verbose:
                cmd.append("--verbose")

            # Run GCP counter
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                # Load results
                with open(gcp_results_file, "r") as f:
                    self.results["gcp"] = json.load(f)
                # Clean up temp file
                os.remove(gcp_results_file)
                self._log("GCP counting completed successfully", "success")
            else:
                error_msg = result.stderr or result.stdout
                self._log(f"GCP counting failed: {error_msg}", "error")
                self.errors.append(f"GCP: {error_msg}")

        except FileNotFoundError:
            error_msg = "gcp_compute_counter.py not found"
            self._log(error_msg, "error")
            self.errors.append(f"GCP: {error_msg}")
        except Exception as e:
            self._log(f"GCP error: {e}", "error")
            self.errors.append(f"GCP: {str(e)}")

    def get_summary(self):
        """Generate aggregated summary across all providers."""
        summary = []

        # Map resource types to friendly names
        resource_names = {
            "ec2": "EC2 Instances",
            "eks": "EKS Nodes",
            "ecs": "ECS Tasks",
            "lambda": "Lambda Functions",
            "lightsail": "Lightsail Instances",
            "batch": "Batch Nodes",
            "vms": "Virtual Machines",
            "aks": "AKS Nodes",
            "aci": "Container Instances",
            "functions": "Azure Functions",
            "vmss": "VM Scale Sets",
            "gce": "Compute Engine VMs",
            "gke": "GKE Nodes",
            "cloud_run": "Cloud Run Services",
            "cloud_functions": "Cloud Functions",
            "app_engine": "App Engine Instances",
        }

        # Aggregate by provider
        for provider, data in self.results.items():
            if "summary" in data:
                for resource_type, count in data["summary"].items():
                    resource_name = resource_names.get(resource_type, resource_type)
                    summary.append([
                        provider.upper(),
                        resource_name,
                        count,
                    ])

        return summary

    def print_summary(self):
        """Print aggregated summary to console."""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Multi-Cloud Compute Node Summary{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

        if self.errors:
            print(f"{Fore.YELLOW}Errors encountered:{Style.RESET_ALL}")
            for error in self.errors:
                print(f"  {Fore.RED}• {error}{Style.RESET_ALL}")
            print()

        summary = self.get_summary()

        if not summary:
            print(f"{Fore.YELLOW}No compute resources found across any provider.{Style.RESET_ALL}\n")
            return

        # Sort by provider, then resource type
        summary.sort(key=lambda x: (x[0], x[1]))

        # Print detailed breakdown
        print(f"{Fore.GREEN}Detailed Breakdown:{Style.RESET_ALL}")
        headers = ["Provider", "Resource Type", "Count"]
        print(tabulate(summary, headers=headers, tablefmt="simple"))

        # Calculate totals by provider
        print(f"\n{Fore.GREEN}Provider Totals:{Style.RESET_ALL}")
        provider_totals = defaultdict(int)
        for row in summary:
            provider_totals[row[0]] += row[2]

        provider_summary = [[provider, total] for provider, total in sorted(provider_totals.items())]
        print(tabulate(provider_summary, headers=["Provider", "Total Nodes"], tablefmt="simple"))

        # Grand total
        grand_total = sum(provider_totals.values())
        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Grand Total Across All Clouds: {grand_total:,} compute nodes{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")

    def export_json(self, output_file):
        """Export aggregated results to JSON."""
        # Calculate summary
        summary = self.get_summary()

        provider_totals = defaultdict(int)
        for row in summary:
            provider_totals[row[0]] += row[2]

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "multi_cloud_summary": {
                "providers": dict(provider_totals),
                "grand_total": sum(provider_totals.values()),
            },
            "detailed_results": self.results,
            "errors": self.errors,
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"{Fore.GREEN}Aggregated results exported to {output_file}{Style.RESET_ALL}")

    def export_csv(self, output_file):
        """Export aggregated results to CSV."""
        import csv

        summary = self.get_summary()

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Provider", "Resource Type", "Count"])

            for row in summary:
                writer.writerow(row)

        print(f"{Fore.GREEN}Aggregated results exported to {output_file}{Style.RESET_ALL}")


@click.command()
@click.option(
    "--providers",
    help="Comma-separated list of providers to query (aws,azure,gcp). Default: all",
    default="aws,azure,gcp",
)
@click.option(
    "--aws-regions",
    help="Comma-separated list of AWS regions",
    default=None,
)
@click.option(
    "--azure-subscription",
    help="Azure subscription ID",
    default=None,
)
@click.option(
    "--gcp-project",
    help="GCP project ID",
    default=None,
)
@click.option(
    "--output",
    help="Output file path for aggregated results",
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
def main(providers, aws_regions, azure_subscription, gcp_project, output, output_format, verbose):
    """
    Count compute nodes across multiple cloud providers.

    Aggregates results from AWS, Azure, and GCP into a unified view.
    """
    try:
        # Parse providers
        provider_list = [p.strip().lower() for p in providers.split(",")]

        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Starting Multi-Cloud Compute Node Count{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Providers: {', '.join([p.upper() for p in provider_list])}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

        # Initialize counter
        counter = MultiCloudCounter(verbose=verbose)

        # Count resources for each provider
        if "aws" in provider_list:
            counter.count_aws(regions=aws_regions)

        if "azure" in provider_list:
            counter.count_azure(subscription_id=azure_subscription)

        if "gcp" in provider_list:
            counter.count_gcp(project_id=gcp_project)

        # Print summary
        counter.print_summary()

        # Export if requested
        if output:
            if output_format == "json":
                counter.export_json(output)
            elif output_format == "csv":
                counter.export_csv(output)

        # Exit with error code if all providers failed
        if len(counter.errors) == len(provider_list):
            print(f"\n{Fore.RED}All providers failed. Please check credentials and try again.{Style.RESET_ALL}")
            sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
