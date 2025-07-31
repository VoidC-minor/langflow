import os
from langflow.main import create_app
from langflow.logging.logger import configure


def setup_worker_environment():
    """Setup environment for worker backend."""
    # Set backend-only mode
    os.environ["LANGFLOW_BACKEND_ONLY"] = "true"
    
    # Set worker port if specified
    worker_port = os.getenv("LANGFLOW_WORKER_PORT", "7861")
    os.environ["LANGFLOW_WORKER_PORT"] = worker_port


def create_worker_app():
    """Create the worker FastAPI app."""
    setup_worker_environment()
    
    # Configure logging
    log_level = os.environ.get("LANGFLOW_LOG_LEVEL", "info")
    configure(log_level=log_level)
    
    # Create the app using the main app creation logic
    app = create_app()
    
    # Add health check endpoint for worker
    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "ok", "type": "worker"}
    
    return app
