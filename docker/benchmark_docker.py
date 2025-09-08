#!/usr/bin/env python3
"""
Benchmark script for Docker single runner setup.
Tests performance with one runner behind Nginx.
"""

import asyncio
import time
import httpx
import psutil
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel


console = Console()


class DockerBenchmark:
    def __init__(self, main_url="http://localhost:7860", nginx_url="http://localhost:8080"):
        self.main_url = main_url
        self.nginx_url = nginx_url
        self.results = {}
    
    async def check_services(self):
        """Check if all services are running."""
        console.print("Checking services...", style="bold blue")
        
        services = [
            (f"{self.main_url}/health", "Main Backend"),
            (f"{self.nginx_url}/health", "Nginx Load Balancer"),
        ]
        
        all_healthy = True
        for url, name in services:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        console.print(f"{name}: {url}", style="green")
                    else:
                        console.print(f"❌ {name}: {url} (Status: {response.status_code})", style="red")
                        all_healthy = False
            except Exception as e:
                console.print(f"❌ {name}: {url} (Error: {e})", style="red")
                all_healthy = False
        
        return all_healthy
    
    async def get_container_stats(self):
        """Get resource usage for Docker containers."""
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "json"],
                capture_output=True, text=True, check=True
            )
            stats = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    stats.append(json.loads(line))
            return stats
        except Exception as e:
            console.print(f"⚠️  Could not get container stats: {e}", style="yellow")
            return []
    
    async def run_flow_test(self, flow_id, n_parallel, n_repeat=1):
        """Run flow execution tests."""
        times = []
        
        async def run_one_flow():
            async with httpx.AsyncClient(timeout=60.0) as client:
                start = time.time()
                try:
                    response = await client.post(
                        f"{self.main_url}/api/v1/run/{flow_id}",
                        json={"input_value": "hello", "input_type": "chat"}
                    )
                    elapsed = time.time() - start
                    if response.status_code == 200 or response.status_code == 307:
                        return elapsed
                    else:
                        console.print(f"⚠️  Flow execution failed: {response.status_code}", style="yellow")
                        return None
                except Exception as e:
                    console.print(f"⚠️  Flow execution error: {e}", style="yellow")
                    return None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Running {n_parallel} parallel flows...", total=n_repeat)
            
            for _ in range(n_repeat):
                tasks = [run_one_flow() for _ in range(n_parallel)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out None results (failed requests)
                valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]
                times.extend(valid_results)
                
                progress.advance(task)
        
        return times
    
    async def benchmark(self, flow_id="d3f20939-c3a3-4003-80a6-c6777334a4be"):
        """Run the complete benchmark."""
        console.print(Panel.fit(" Docker Single Runner Benchmark", style="bold blue"))
        
        # Check services
        if not await self.check_services():
            console.print(" Some services are not healthy. Please check your Docker setup.", style="red")
            return
        
        # Get baseline stats
        console.print("\n Getting baseline resource usage...", style="bold blue")
        baseline_stats = await self.get_container_stats()
        
        # Test scenarios
        scenarios = [
            ("Idle", 0),
            ("1 Flow", 1),
            ("50 Flows", 50),
            ("100 Flows", 100),
        ]
        
        for scenario_name, n_parallel in scenarios:
            console.print(f"\n Testing: {scenario_name}", style="bold green")
            
            if n_parallel > 0:
                times = await self.run_flow_test(flow_id, n_parallel, n_repeat=1)
                if times:
                    avg_time = sum(times) / len(times)
                    min_time = min(times)
                    max_time = max(times)
                    
                    self.results[scenario_name] = {
                        "avg_time": avg_time,
                        "min_time": min_time,
                        "max_time": max_time,
                        "total_requests": len(times),
                    }
                else:
                    self.results[scenario_name] = {"error": "No successful requests"}
            else:
                # Idle test - just wait and get stats
                await asyncio.sleep(5)
                self.results[scenario_name] = {"status": "idle"}
        
        # Get final stats
        final_stats = await self.get_container_stats()
        
        # Display results
        self.display_results(baseline_stats, final_stats)
    
    def display_results(self, baseline_stats, final_stats):
        """Display benchmark results."""
        console.print("\n" + "="*60, style="bold")
        console.print("BENCHMARK RESULTS", style="bold blue")
        console.print("="*60, style="bold")
        
        # Performance table
        table = Table(title="Flow Execution Performance")
        table.add_column("Scenario", style="cyan")
        table.add_column("Avg Time (s)", style="magenta")
        table.add_column("Min Time (s)", style="green")
        table.add_column("Max Time (s)", style="red")
        table.add_column("Total Requests", style="blue")
        
        for scenario, data in self.results.items():
            if "error" in data:
                table.add_row(scenario, "ERROR", "", "", "", "")
            elif "status" in data:
                table.add_row(scenario, "IDLE", "", "", "", "")
            else:
                table.add_row(
                    scenario,
                    f"{data['avg_time']:.3f}",
                    f"{data['min_time']:.3f}",
                    f"{data['max_time']:.3f}",
                    str(data['total_requests'])
                )
        
        console.print(table)
        
        # Container stats
        if baseline_stats and final_stats:
            console.print("\nContainer Resource Usage", style="bold blue")
            stats_table = Table()
            stats_table.add_column("Container", style="cyan")
            stats_table.add_column("CPU %", style="magenta")
            stats_table.add_column("Memory (MB)", style="green")
            stats_table.add_column("Network I/O", style="yellow")
            
            for stat in final_stats:
                container_name = stat.get("Name", "Unknown")
                cpu = stat.get("CPUPerc", "N/A")
                memory = stat.get("MemUsage", "N/A")
                network = stat.get("NetIO", "N/A")
                
                stats_table.add_row(container_name, cpu, memory, network)
            
            console.print(stats_table)
        
        # # Save results
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # results_file = Path(f"docker_benchmark_results_{timestamp}.json")
        
        # with open(results_file, 'w') as f:
        #     json.dump({
        #         "timestamp": timestamp,
        #         "results": self.results,
        #         "baseline_stats": baseline_stats,
        #         "final_stats": final_stats
        #     }, f, indent=2)
        
        # console.print(f"\n💾 Results saved to: {results_file}", style="green")


async def main():
    """Main function."""
    benchmark = DockerBenchmark()
    await benchmark.benchmark()


if __name__ == "__main__":
    asyncio.run(main()) 