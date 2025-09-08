## Docker Compose, Benchmarking, and API Testing Guide

This guide explains how to run Langflow with Docker Compose, benchmark common endpoints, and test streaming and OpenAI‑compatible endpoints.

### Prerequisites

- Docker and Docker Compose installed
- Optional: API key if authentication is enabled

### Run with Docker Compose

- Compose file: `docker/docker-compose.yml`
- Services overview:
  - `main`: Full Langflow app (API + UI) on port `7860`
  - `runner1`: Backend worker (internal port `7861`)
  - `nginx`: Load balancer for forwarding flow runs on port `8080`
  - `postgres`: PostgreSQL database on port `5432`

Key environment variables in `main` and `runner1`:

- `FORWARD_FLOW=true`: Enables forwarding flow execution to the load balancer
- `FORWARD_FLOW_URL=http://localhost:8080`: Nginx endpoint used for forwarding
- `LANGFLOW_LOCAL_MODE=true`: Enables local/development mode
- `LANGFLOW_AUTO_LOGIN=true`: Auto-login for UI in development
- `LANGFLOW_LOG_LEVEL=info`: Logging level
- `LANGFLOW_DATABASE_URL=postgresql+psycopg://langflow:langflow@postgres:5432/langflow`: Database connection

Runner connection tuning (on `runner1`):

- `SQLALCHEMY_POOL_SIZE=50`, `SQLALCHEMY_MAX_OVERFLOW=100`, `SQLALCHEMY_POOL_TIMEOUT=60`

Optional metrics:

- Set `LANGFLOW_PROMETHEUS_PORT=9095` in `main` to expose Prometheus metrics

Start the stack (from repo root):

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Stop and remove containers and volumes:

```bash
docker compose -f docker/docker-compose.yml down -v
```

Access points:

- UI: `http://localhost:7860`
- API health: `http://localhost:7860/health`
- Nginx health: `http://localhost:8080/health`

Data persistence:

- App data: `../data:/app/data`
- Postgres data: named volume `postgres-data`

Auth notes:

- With `LANGFLOW_AUTO_LOGIN=true`, the UI auto‑logs in for local development. API endpoints may still require an API key. If auth is enabled, pass `x-api-key` (or `Authorization: Bearer`) headers; otherwise omit them.

Troubleshooting:

```bash
docker compose -f docker/docker-compose.yml logs -f main
docker compose -f docker/docker-compose.yml logs -f runner1
docker compose -f docker/docker-compose.yml logs -f nginx
```

### Benchmarking

Benchmarks are best done against non‑streaming endpoints. Use your `FLOW_ID` and set `stream=false`.

Sample JSON body for flow runs:

```json
{
  "input_value": "Hello",
  "input_type": "text",
  "output_type": "chat"
}
```

- hey (simple load):

```bash
FLOW_ID="<your-flow-id>"
BASE="http://localhost:7860"
API="/api/v1/run/${FLOW_ID}?stream=false"

hey -m POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -d '{"input_value":"Hello","input_type":"text","output_type":"chat"}' \
  -n 200 -c 20 "$BASE$API"
```

- wrk (advanced): create `post.lua`:

```lua
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
if os.getenv("LANGFLOW_API_KEY") then
  wrk.headers["x-api-key"] = os.getenv("LANGFLOW_API_KEY")
end
wrk.body   = '{"input_value":"Hello","input_type":"text","output_type":"chat"}'
```

Run wrk:

```bash
FLOW_ID="<your-flow-id>"
wrk -t4 -c32 -d30s -s post.lua "http://localhost:7860/api/v1/run/${FLOW_ID}?stream=false"
```

Notes for streaming:

- Many load tools don’t support SSE well. Prefer measuring end‑to‑end latency and correctness with curl or the Python script below for streaming scenarios.

### Test Streaming

- Python script: `test_streaming.py`

```bash
export LANGFLOW_URL="http://localhost:7860"
export LANGFLOW_API_KEY="<optional-api-key>"

python3 test_streaming.py            # interactive: lists flows and asks for FLOW_ID
python3 test_streaming.py <FLOW_ID>  # non-interactive with given FLOW_ID
```

The script connects to `POST /api/v1/run/{flow_id}?stream=true` and prints SSE events: `token`, `add_message`, and `end`.

- curl (SSE):

```bash
FLOW_ID="<your-flow-id>"
curl -N \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -X POST "http://localhost:7860/api/v1/run/${FLOW_ID}?stream=true" \
  -d '{"input_value":"Hello","input_type":"text","output_type":"chat"}'
```

You should see newline‑separated JSON entries with `event` and `data` fields. The stream ends when an `end` event is received.

Forwarding note:

- With `FORWARD_FLOW=true`, streaming is proxied through Nginx (`docker/nginx.conf`), and the app forwards requests to the runner. This supports chunked/SSE streaming end‑to‑end.

### Test Endpoints (OpenAI‑Compatible and Direct)

- Python script: `test_openai_endpoint.py`

```bash
export LANGFLOW_BASE_URL="http://localhost:7860"
export LANGFLOW_API_KEY="<optional-api-key>"
export LANGFLOW_FLOW_ID="<your-flow-id>"

python3 test_openai_endpoint.py
```

The script exercises:

- `POST /api/v1/openai_run_flow` (model set to your `FLOW_ID`)
- `POST /api/v1/openai_run_flow/{flow_id}`
- `POST /api/v1/run/{flow_id}` (direct Langflow format)
- `GET /api/v1/models`

curl examples:

- OpenAI‑compatible generic endpoint:

```bash
FLOW_ID="<your-flow-id>"
curl -sS -X POST "http://localhost:7860/api/v1/openai_run_flow" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -d '{
        "messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"Hello"}],
        "model":"'"$FLOW_ID"'",
        "temperature":0.7,
        "max_tokens":150
      }'
```

- Direct Langflow endpoint (non‑streaming):

```bash
FLOW_ID="<your-flow-id>"
curl -sS -X POST "http://localhost:7860/api/v1/run/${FLOW_ID}" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGFLOW_API_KEY" \
  -d '{
        "input_type":"chat",
        "output_type":"chat",
        "tweaks":{
          "Prompt":{"template":"You are helpful.\n\nUser: Hello\nAssistant:"},
          "OpenAIModel":{"temperature":0.7,"max_tokens":150}
        }
      }'
```

### Health and Logs

```bash
curl -f http://localhost:7860/health
curl -f http://localhost:8080/health
```

If flows aren’t executing, check forwarding is enabled in `main` and that `runner1` is healthy.


