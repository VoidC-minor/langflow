#!/usr/bin/env python3
"""
Docker startup script for Langflow load balancing setup.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def wait_for_service(url, timeout=60, interval=2):
    """Wait for a service to be ready."""
    print(f"Waiting for {url} to be ready...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {url} is ready!")
                return True
        except requests.RequestException:
            pass
        
        time.sleep(interval)
    
    print(f"❌ {url} failed to start within {timeout} seconds")
    return False


def main():
    """Main function."""
    print("🚀 Starting Langflow Docker Load Balancing Setup")
    
    # Check if Docker is running
    try:
        run_command(["docker", "version"])
    except subprocess.CalledProcessError:
        print("❌ Docker is not running. Please start Docker first.")
        sys.exit(1)
    
    # Check if docker-compose is available
    try:
        run_command(["docker-compose", "--version"])
    except subprocess.CalledProcessError:
        print("❌ docker-compose is not available. Please install it first.")
        sys.exit(1)
    
    # Build and start services
    print("\n📦 Building Docker images...")
    try:
        run_command(["docker-compose", "build"])
    except subprocess.CalledProcessError:
        print("❌ Failed to build Docker images")
        sys.exit(1)
    
    print("\n🚀 Starting services...")
    try:
        run_command(["docker-compose", "up", "-d"])
    except subprocess.CalledProcessError:
        print("❌ Failed to start services")
        sys.exit(1)
    
    # Wait for services to be ready
    print("\n⏳ Waiting for services to be ready...")
    
    services = [
        ("http://localhost:7860/api/v1/health", "Main Backend"),
        ("http://localhost:7861/api/v1/health", "Runner 1"),
        ("http://localhost:7862/api/v1/health", "Runner 2"),
        ("http://localhost:8080/health", "Nginx Load Balancer"),
    ]
    
    all_ready = True
    for url, name in services:
        if not wait_for_service(url):
            all_ready = False
    
    if all_ready:
        print("\n🎉 All services are ready!")
        print("\n📋 Service URLs:")
        print("   • Main Backend (UI): http://localhost:7860")
        print("   • Runner 1: http://localhost:7861")
        print("   • Runner 2: http://localhost:7862")
        print("   • Nginx Load Balancer: http://localhost:8080")
        print("\n🔧 Useful commands:")
        print("   • View logs: docker-compose logs -f")
        print("   • Stop services: docker-compose down")
        print("   • Restart services: docker-compose restart")
    else:
        print("\n❌ Some services failed to start")
        print("Check logs with: docker-compose logs")
        sys.exit(1)


if __name__ == "__main__":
    main() 