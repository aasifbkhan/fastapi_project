"""
Unit tests for the FastAPI application.
"""

from fastapi import FastAPI

from main import app


class TestMain:
    """
    Unit tests for main application initialization.
    """

    def test_app_is_fastapi_instance(self):
        """
        Test that the application is a FastAPI instance.
        """

        assert isinstance(app, FastAPI)

    def test_app_metadata(self):
        """
        Test FastAPI application metadata.
        """

        assert app.title == "DevFlow"
        assert app.version == "1.0.0"

    def test_api_router_is_included(self):
        """
        Test that the API router is included in the application.
        """

        assert len(app.routes) > 4