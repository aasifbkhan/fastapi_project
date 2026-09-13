"""
Unit tests for API v1 router registration.
"""

from api.v1.router import v1_router
from api.v1.auth.router import router as auth_router


class TestV1Router:
    """
    Unit tests for API v1 router.
    """

    def test_auth_router_is_included(self):
        """
        Test that the authentication router is included in v1.
        """
        included_routers = [
            route.original_router
            for route in v1_router.routes
            if hasattr(route, "original_router")
        ]

        assert auth_router in included_routers
