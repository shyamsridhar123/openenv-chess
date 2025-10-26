"""Base HTTP client for external API calls.

Provides unified HTTP client with timeout handling, retry logic, and error handling
for Lichess APIs (Opening Book, Tablebase) and other external services.
"""

import requests
from typing import Optional, Dict, Any
import structlog
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = structlog.get_logger()


class APIClient:
    """Base HTTP client for external API calls with retry logic."""
    
    def __init__(
        self,
        timeout: float = 1.0,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
    ):
        """Initialize API client.
        
        Args:
            timeout: Request timeout in seconds (default 1.0s)
            max_retries: Maximum number of retry attempts (default 3)
            backoff_factor: Backoff factor for retries (default 0.3)
        """
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(
            "api_client_initialized",
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
        )
    
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Make GET request with error handling.
        
        Args:
            url: URL to request
            params: Query parameters
            headers: Request headers
            
        Returns:
            JSON response as dictionary, or None on failure
        """
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            logger.debug(
                "api_request_success",
                url=url,
                status_code=response.status_code,
            )
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.warning("api_request_timeout", url=url, timeout=self.timeout)
            return None
            
        except requests.exceptions.HTTPError as e:
            logger.warning(
                "api_request_http_error",
                url=url,
                status_code=e.response.status_code,
                error=str(e),
            )
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error("api_request_failed", url=url, error=str(e))
            return None
            
        except ValueError as e:
            logger.error("api_response_json_parse_error", url=url, error=str(e))
            return None
    
    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()
            logger.info("api_client_closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
