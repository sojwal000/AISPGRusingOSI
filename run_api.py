"""
FastAPI server runner.
Starts the REST API for querying risk scores and data.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import uvicorn
from app.core.logging import setup_logger

logger = setup_logger("api_server", "INFO")


def main():
    """Start the API server"""
    logger.info("Starting Geopolitical Risk Analysis API Server...")
    logger.info("API will be available at: http://localhost:8000")
    logger.info("API documentation at: http://localhost:8000/docs")
    logger.info("Press CTRL+C to stop the server")
    
    try:
        uvicorn.run(
            "app.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
