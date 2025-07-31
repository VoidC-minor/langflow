# Docker Load Balancing Makefile for Langflow

.PHONY: help start stop restart build logs status clean benchmark test health

# Default target
help:
	@echo "Docker Load Balancing Commands:"
	@echo ""
	@echo "  start      - Start all services"
	@echo "  stop       - Stop all services"
	@echo "  restart    - Restart all services"
	@echo "  build      - Build Docker images"
	@echo "  logs       - View logs for all services"
	@echo "  status     - Show service status"
	@echo "  clean      - Stop and remove all containers"
	@echo "  benchmark  - Run performance benchmark"
	@echo "  test       - Test service health"
	@echo "  health     - Check all health endpoints"
	@echo "  scale      - Scale runners (usage: make scale RUNNERS=3)"

# Start all services
start:
	@echo "🚀 Starting Langflow Docker Load Balancing..."
	python start_docker.py

# Stop all services
stop:
	@echo "🛑 Stopping services..."
	docker-compose down

# Restart all services
restart: stop start

# Build Docker images
build:
	@echo "📦 Building Docker images..."
	docker-compose build

# View logs
logs:
	@echo "📋 Viewing logs..."
	docker-compose logs -f

# Show service status
status:
	@echo "📊 Service Status:"
	docker-compose ps

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Run benchmark
benchmark:
	@echo "🧪 Running benchmark..."
	python benchmark_docker.py

# Test services
test:
	@echo "🔍 Testing services..."
	@echo "Testing Main Backend..."
	@curl -s http://localhost:7860/api/v1/health || echo "❌ Main Backend not responding"
	@echo "Testing Nginx..."
	@curl -s http://localhost:8080/health || echo "❌ Nginx not responding"
	@echo "Testing Runner 1..."
	@curl -s http://localhost:7861/api/v1/health || echo "❌ Runner 1 not responding"
	@echo "Testing Runner 2..."
	@curl -s http://localhost:7862/api/v1/health || echo "❌ Runner 2 not responding"

# Check health endpoints
health:
	@echo "🏥 Health Check Results:"
	@echo "Main Backend:"
	@curl -s http://localhost:7860/api/v1/health | jq . 2>/dev/null || curl -s http://localhost:7860/api/v1/health
	@echo ""
	@echo "Nginx:"
	@curl -s http://localhost:8080/health
	@echo ""
	@echo "Runner 1:"
	@curl -s http://localhost:7861/api/v1/health | jq . 2>/dev/null || curl -s http://localhost:7861/api/v1/health
	@echo ""
	@echo "Runner 2:"
	@curl -s http://localhost:7862/api/v1/health | jq . 2>/dev/null || curl -s http://localhost:7862/api/v1/health

# Scale runners
scale:
	@if [ -z "$(RUNNERS)" ]; then \
		echo "Usage: make scale RUNNERS=3"; \
		exit 1; \
	fi
	@echo "📈 Scaling to $(RUNNERS) runners..."
	@for i in $$(seq 1 $(RUNNERS)); do \
		if [ $$i -gt 2 ]; then \
			echo "Adding runner$$i..."; \
			docker-compose up -d --scale runner1=1 --scale runner2=1; \
		fi; \
	done

# Show container stats
stats:
	@echo "📊 Container Statistics:"
	docker stats --no-stream

# Show network info
network:
	@echo "🌐 Network Information:"
	docker network ls | grep langflow
	docker network inspect langflow-network 2>/dev/null || echo "Network not found"

# Update nginx config
reload-nginx:
	@echo "🔄 Reloading Nginx configuration..."
	docker exec langflow-nginx nginx -s reload

# Show nginx logs
nginx-logs:
	@echo "📋 Nginx logs:"
	docker logs langflow-nginx

# Show main backend logs
main-logs:
	@echo "📋 Main backend logs:"
	docker logs langflow-main

# Show runner logs
runner-logs:
	@echo "📋 Runner logs:"
	docker logs langflow-runner1
	docker logs langflow-runner2

# Quick setup (build + start)
setup: build start

# Development mode (with volume mounts)
dev:
	@echo "🔧 Starting in development mode..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production mode
prod:
	@echo "🚀 Starting in production mode..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d 