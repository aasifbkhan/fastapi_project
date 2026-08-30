"""
Unit tests for API router.
"""

from api.router import api_router
from api.auth.router import router as auth_router


class TestAPIRouter:
    """
    Unit tests for API router registration.
    """

    def test_auth_router_is_included(self):
        """
        Test that the authentication router is included.
        """

        included_routers = [
            route
            for route in api_router.routes
            if hasattr(route, "original_router")
        ]

        assert included_routers

        original_routers = [
            route.original_router
            for route in included_routers
        ]

        assert auth_router in original_routers