# Docker Load Balancing Setup for Langflow

This setup provides a production-ready load balancing solution for Langflow using Docker, Nginx, and multiple worker backends.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main Backend  │    │   Nginx Load    │    │   Runner 1      │
│   (UI + API)    │───▶│   Balancer      │───▶│   (Worker)      │
│   Port: 7860    │    │   Port: 8080    │    │   Port: 7861    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                └─────────────▶┌─────────────────┐
                                               │   Runner 2      │
                                               │   (Worker)      │
                                               │   Port: 7862    │
                                               └─────────────────┘
```

## Components

### 1. Main Backend (`main` service)
- **Purpose**: Serves the Langflow UI and handles general API requests
- **Port**: 7860 (accessible from host)
- **Features**: 
  - Frontend UI
  - API endpoints
  - Flow forwarding middleware (when enabled)
  - Health check endpoint

### 2. Nginx Load Balancer (`nginx` service)
- **Purpose**: Distributes flow execution requests across multiple runners
- **Port**: 8080 (accessible from host)
- **Features**:
  - Round-robin load balancing
  - Health checks
  - Request forwarding
  - Timeout handling

### 3. Runner Backends (`runner1`, `runner2` services)
- **Purpose**: Execute flows without frontend interaction
- **Ports**: 7861, 7862 (internal only)
- **Features**:
  - Backend-only mode
  - Flow execution
  - Health check endpoints
  - Resource monitoring

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 7860, 8080 available

### 1. Start the Services

```bash
# Navigate to docker directory
cd docker

# Start all services
make start

# Or manually:
python start_docker.py
```

### 2. Verify Services

```bash
# Check service status
make status

# View logs
make logs

# Test health endpoints
make health
```

### 3. Access the Application

- **Main UI**: http://localhost:7860
- **Nginx Load Balancer**: http://localhost:8080

## Configuration

### Environment Variables

#### Main Backend
```yaml
FORWARD_FLOW: "true"                    # Enable flow forwarding
FORWARD_FLOW_URL: "http://nginx:8080/api/v1/flow/run"  # Nginx URL
LANGFLOW_LOCAL_MODE: "true"             # Run without API keys
LANGFLOW_AUTO_LOGIN: "true"             # Auto-login for development
```

#### Runner Backends
```yaml
LANGFLOW_BACKEND_ONLY: "true"           # Backend-only mode
LANGFLOW_LOCAL_MODE: "true"             # Run without API keys
LANGFLOW_WORKER_PORT: "7861"            # Port for each runner
```

### Scaling Runners

To add more runners:

1. **Update `docker-compose.yml`**:
```yaml
runner3:
  build:
    context: ..
    dockerfile: docker/Dockerfile.runner
  environment:
    - LANGFLOW_BACKEND_ONLY=true
    - LANGFLOW_LOCAL_MODE=true
    - LANGFLOW_WORKER_PORT=7863
  # ... other settings
```

2. **Update `nginx.conf`**:
```nginx
upstream runners {
    server runner1:7861;
    server runner2:7862;
    server runner3:7863;  # Add new runner
}
```

3. **Restart services**:
```bash
make restart
```

## Testing and Benchmarking

### Run Benchmark

```bash
# Install benchmark dependencies
pip install httpx rich psutil

# Run benchmark
make benchmark
```

The benchmark will test:
- Idle state
- 1 parallel flow
- 10 parallel flows
- 20 parallel flows

### Manual Testing

```bash
# Test flow forwarding through main backend
curl -X POST http://localhost:7860/api/v1/run/test-flow \
  -H "Content-Type: application/json" \
  -d '{"input_value": "test", "input_type": "chat"}'

# Test direct access to Nginx
curl -X POST http://localhost:8080/api/v1/flow/run \
  -H "Content-Type: application/json" \
  -d '{"input_value": "test", "input_type": "chat"}'
```

## Monitoring

### Health Checks

All services include health check endpoints:
- Main Backend: `GET /api/v1/health`
- Runners: `GET /api/v1/health`
- Nginx: `GET /health`

### Resource Monitoring

```bash
# View container stats
make stats

# View logs for specific service
make main-logs
make runner-logs
make nginx-logs
```

### Load Balancer Status

```bash
# Check Nginx configuration
docker exec langflow-nginx nginx -t

# Reload Nginx config
make reload-nginx
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check Docker logs
   make logs
   
   # Check if ports are available
   netstat -tlnp | grep :7860
   netstat -tlnp | grep :8080
   ```

2. **Flow forwarding not working**
   ```bash
   # Check if FORWARD_FLOW is enabled
   docker exec langflow-main env | grep FORWARD_FLOW
   
   # Check Nginx connectivity
   docker exec langflow-main curl -f http://nginx:8080/health
   ```

3. **High resource usage**
   ```bash
   # Scale down workers
   docker-compose up -d --scale runner1=1 --scale runner2=1
   
   # Monitor resource usage
   make stats
   ```

### Performance Tuning

1. **Adjust worker processes**:
   ```dockerfile
   # In Dockerfile.runner, change --workers value
   CMD ["sh", "-c", "uvicorn --factory langflow.worker:create_worker_app --host 0.0.0.0 --port ${LANGFLOW_WORKER_PORT:-7861} --loop asyncio --workers 4"]
   ```

2. **Adjust Nginx timeouts**:
   ```nginx
   # In nginx.conf
   proxy_connect_timeout 120s;
   proxy_send_timeout 120s;
   proxy_read_timeout 120s;
   ```

3. **Add more memory to containers**:
   ```yaml
   # In docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 2G
   ```

## Development

### Local Development

For development without Docker:

```bash
# Start main backend
uv run uvicorn --factory langflow.main:create_app --host 0.0.0.0 --port 7860 --reload

# Start worker backend
uv run uvicorn --factory langflow.worker:create_worker_app --host 0.0.0.0 --port 7861
```

### Adding Custom Flows

1. **Mount flow directory**:
   ```yaml
   # In docker-compose.yml
   volumes:
     - ../flows:/app/flows
   ```

2. **Set environment variable**:
   ```yaml
   environment:
     - LANGFLOW_LOAD_FLOWS_PATH=/app/flows
   ```

## Security Considerations

1. **Network isolation**: All services run in a dedicated Docker network
2. **Health checks**: All services include health check endpoints
3. **Resource limits**: Consider adding memory and CPU limits
4. **Logging**: All services log to stdout/stderr for Docker logging

## Production Deployment

For production deployment:

1. **Use proper secrets management**
2. **Add SSL/TLS termination**
3. **Configure proper logging**
4. **Set up monitoring and alerting**
5. **Use persistent volumes for data**
6. **Configure backup strategies**

## Files Overview

- `docker-compose.yml`: Service orchestration
- `Dockerfile.main`: Main backend container
- `Dockerfile.runner`: Worker backend container
- `nginx.conf`: Nginx load balancer configuration
- `start_docker.py`: Startup script
- `benchmark_docker.py`: Performance testing
- `Makefile`: Easy management commands
- `README.md`: This documentation

## Makefile Commands

```bash
make help          # Show all available commands
make start         # Start all services
make stop          # Stop all services
make restart       # Restart all services
make build         # Build Docker images
make logs          # View logs
make status        # Show service status
make clean         # Clean up containers and images
make benchmark     # Run performance benchmark
make test          # Test service health
make health        # Check all health endpoints
make stats         # Show container statistics
make scale RUNNERS=4  # Scale to 4 runners
``` 