import os
import httpx
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from loguru import logger


class FlowForwardingMiddleware(BaseHTTPMiddleware):
    """Middleware to forward flow execution requests to Nginx load balancer."""
    
    def __init__(self, app):
        super().__init__(app)
        self.forward_flow = os.getenv("FORWARD_FLOW", "false").lower() == "true"
        self.forward_url = os.getenv("FORWARD_FLOW_URL", "")
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
            headers = dict(request.headers)
            headers_to_remove = ["host", "content-length", "transfer-encoding"]
            for header in headers_to_remove:
                headers.pop(header.lower(), None)
            
            # Build the target URL
            target_url = f"{self.forward_url}{request.url.path}"
            if request.url.query:
                target_url += f"?{request.url.query}"
            
            logger.info(f"Forwarding request to: {target_url}")
            
            # Make the request to Nginx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    params=request.query_params
                )
                
                # Return the response from Nginx
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.headers.get("content-type")
                )
                
        except Exception as e:
            logger.error(f"Error forwarding request to {self.forward_url}: {e}")
            # Fall back to local execution
            return await call_next(request) 