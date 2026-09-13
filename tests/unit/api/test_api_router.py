"""
Unit tests for API router registration.
"""

from api.router import api_router
from api.v1.router import v1_router
from api.v1.auth.router import router as auth_router


class TestAPIRouter:
    """
    Unit tests for API router registration.
    """

    def test_v1_router_is_included(self):
        """
        Test that the v1 router is included under the top-level API router.
        """
        included_routers = [
            route.original_router
            for route in api_router.routes
            if hasattr(route, "original_router")
        ]

        assert v1_router in included_routers

    def test_auth_router_is_included_in_v1(self):
        """
        Test that the authentication router is included under v1.
        """
        included_routers = [
            route.original_router
            for route in v1_router.routes
            if hasattr(route, "original_router")
        ]

        assert auth_router in included_routers
