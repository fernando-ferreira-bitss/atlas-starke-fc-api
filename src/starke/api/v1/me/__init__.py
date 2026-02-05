"""Client self-service module for API v1.

This module provides endpoints for clients to view their own data.
All endpoints automatically filter data for the logged-in client.
"""

from starke.api.v1.me.routes import router

__all__ = ["router"]
