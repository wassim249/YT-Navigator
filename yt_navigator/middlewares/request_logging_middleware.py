"""Middleware for request logging using structlog."""

import time
import uuid

import structlog

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware:
    """Middleware for logging request information using structlog."""

    def __init__(self, get_response):
        """Initialize the middleware."""
        self.get_response = get_response

    def __call__(self, request):
        """Process the request and log information about it.

        This method logs the start and end of each request with a unique ID,
        tracks request duration, and captures relevant request metadata.

        Args:
            request: The Django HTTP request object.

        Returns:
            The HTTP response from the view.
        """
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Bind the request ID to the logger
        request_logger = logger.bind(request_id=request_id)

        # Log the request
        request_logger.info(
            "Request started",
            method=request.method,
            path=request.path,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip=self._get_client_ip(request),
        )

        # Record the start time
        start_time = time.time()

        # Process the request
        response = self.get_response(request)

        # Calculate request duration
        duration = time.time() - start_time

        # Log the response
        request_logger.info(
            "Request finished",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration=f"{duration:.2f}s",
        )

        return response

    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
