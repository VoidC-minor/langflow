import os
import httpx
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from loguru import logger
from urllib.parse import urlparse


class FlowForwardingMiddleware(BaseHTTPMiddleware):
    """Middleware to forward flow execution requests to Nginx load balancer."""
    
    def __init__(self, app):
        super().__init__(app)
        self.forward_flow = os.getenv("FORWARD_FLOW", "false").lower() == "true"
        self.forward_url = os.getenv("FORWARD_FLOW_URL", "")
        # Normalize to origin (scheme://netloc) to avoid duplicated path joins
        parsed = urlparse(self.forward_url)
        if parsed.scheme and parsed.netloc:
            self.forward_origin = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self.forward_origin = self.forward_url.rstrip("/")
        self.flow_execution_paths = [
            "/api/v1/run/",
            "/api/v1/webhook/",
            "/api/v1/build/",
            "/api/v1/flow/run"
        ]
        
        if self.forward_flow and not self.forward_url:
            logger.warning("FORWARD_FLOW is enabled but FORWARD_FLOW_URL is not set")
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check if forwarding is enabled and this is a flow execution request
        if not self.forward_flow or not self.forward_url:
            return await call_next(request)
        
        # Check if the request path matches flow execution patterns
        path = request.url.path
        if not any(path.startswith(exec_path) for exec_path in self.flow_execution_paths):
            return await call_next(request)
        
        # Forward the request to Nginx
        try:
            # Prepare the request body
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
            
            # Prepare headers (exclude some headers that shouldn't be forwarded)
            headers_to_remove = {"host", "content-length", "transfer-encoding"}
            headers = {k: v for k, v in request.headers.items() if k.lower() not in headers_to_remove}
            
            # Build the target URL robustly, avoiding duplicated path segments
            base = (self.forward_origin or "").rstrip("/")
            target_url = f"{base}{request.url.path}"
            if request.url.query:
                target_url += f"?{request.url.query}"
            
            logger.info(f"Forwarding request to: {target_url}")
            
            # Make the request to Nginx
            async with httpx.AsyncClient(timeout=None) as client:
                # Detect if this should be streamed (SSE or chunked)
                wants_stream = "text/event-stream" in request.headers.get("accept", "")
                if wants_stream:
                    async with client.stream(
                        method=request.method,
                        url=target_url,
                        headers=headers,
                        content=body,
                        params=request.query_params,
                    ) as upstream:
                        async def iter_upstream_bytes():
                            async for chunk in upstream.aiter_bytes():
                                yield chunk

                        hop_by_hop = {
                            "connection",
                            "keep-alive",
                            "proxy-authenticate",
                            "proxy-authorization",
                            "te",
                            "trailers",
                            "transfer-encoding",
                            "upgrade",
                            "content-length",
                        }
                        forward_headers = {
                            k: v for k, v in upstream.headers.items() if k.lower() not in hop_by_hop
                        }
                        media_type = upstream.headers.get("content-type", "text/event-stream")

                        return StreamingResponse(
                            iter_upstream_bytes(),
                            status_code=upstream.status_code,
                            headers=forward_headers,
                            media_type=media_type,
                        )

                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    params=request.query_params,
                )

                hop_by_hop = {
                    "connection",
                    "keep-alive",
                    "proxy-authenticate",
                    "proxy-authorization",
                    "te",
                    "trailers",
                    "transfer-encoding",
                    "upgrade",
                    "content-length",
                }
                forward_headers = {k: v for k, v in response.headers.items() if k.lower() not in hop_by_hop}
                
                # Return the response from Nginx
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=forward_headers,
                    media_type=response.headers.get("content-type"),
                )
                
        except Exception as e:
            logger.error(f"Error forwarding request to {self.forward_url}: {e}")
            # Fall back to local execution
            return await call_next(request) 