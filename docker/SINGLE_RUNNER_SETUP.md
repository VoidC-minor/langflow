# Single Runner Setup

## Overview

The Langflow load balancing setup has been simplified to use only one runner backend for easier testing and development.

## Architecture

### Components

1. **Main Backend** (`langflow-main`): 
   - Serves the UI and general API endpoints
   - Acts as a forwarder for flow execution requests
   - Runs on port 7860

2. **Single Runner Backend** (`langflow-runner1`):
   - Dedicated to flow execution only
   - No UI, backend-only mode
   - Runs on port 7861 (internal)

3. **Nginx Load Balancer** (`langflow-nginx`):
   - Routes flow execution requests to the single runner
   - Runs on port 8080
   - Routes `/api/v1/flow/run` to runner1
   - Routes other `/api/` requests to main backend

## Configuration Changes

### Docker Compose (`docker-compose.yml`)

```yaml
services:
  main:
    # Main backend configuration
    depends_on:
      - runner1  # Only depends on runner1 now
    
  runner1:
    # Single runner configuration
    environment:
      - LANGFLOW_WORKER_PORT=7861
    
  # runner2 service removed
  
  nginx:
    depends_on:
      - runner1  # Only depends on runner1 now
```

### Nginx Configuration (`nginx.conf`)

```nginx
upstream runners {
    server runner1:7861;
    # runner2 removed
    # Add more runners as needed in the future
    # server runner2:7862;
    # server runner3:7863;
}
```

## Benefits of Single Runner Setup

1. **Simplified Testing**: Easier to test and debug with fewer components
2. **Reduced Resource Usage**: Lower CPU and memory consumption
3. **Faster Startup**: Fewer containers to start and initialize
4. **Easier Troubleshooting**: Less complexity in network and service interactions
5. **Development Friendly**: Perfect for development and testing scenarios

## Current Status

- ✅ **Main Backend**: Running on port 7860
- ✅ **Single Runner**: Running on port 7861 (internal)
- ✅ **Nginx Load Balancer**: Running on port 8080
- ✅ **Network Connectivity**: All services can communicate
- ✅ **Forwarding**: Enabled and functional

## Testing Results

```
=== Docker Network Configuration ===
✅ Main backend can reach Nginx
  Response: healthy
✅ Runner1 can reach Nginx
  Response: healthy
✅ Nginx can reach Runner1
  Response: {"status":"ok","type":"worker"}
```

## Scaling Up

When you're ready to scale up to multiple runners:

1. **Add runner2 service** to `docker-compose.yml`
2. **Uncomment runner2** in `nginx.conf`
3. **Update dependencies** to include runner2
4. **Restart services** with `docker-compose up -d`

## Usage

### Starting Services

```bash
cd docker
docker-compose up -d
```

### Testing Forwarding

```bash
python demonstrate_forwarding.py
```

### Monitoring

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Test health endpoints
curl http://localhost:7860/health
curl http://localhost:8080/health
```

## Summary

The single runner setup provides a simplified, resource-efficient configuration that's perfect for:

- **Development and testing**
- **Proof of concept demonstrations**
- **Resource-constrained environments**
- **Learning and understanding the forwarding architecture**

The system maintains all the core functionality of the load balancing setup while being easier to manage and troubleshoot. 