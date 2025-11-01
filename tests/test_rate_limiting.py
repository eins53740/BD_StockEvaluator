"""
Tests for API rate limiting and authentication (Epic 9 F9.3).
"""

import os
import time
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.bd_stockevaluator.api.middleware import (
    APIKeyAuthenticator,
    RateLimiter,
    RateLimitMiddleware,
    generate_api_key,
    get_client_identifier,
)


# ============================================================================
# RateLimiter Tests
# ============================================================================

class TestRateLimiter:
    """Test the in-memory rate limiter."""

    def test_rate_limiter_allows_within_limit(self):
        """Test that requests within limit are allowed."""
        limiter = RateLimiter(requests_per_minute=10)
        client_id = "test_client"

        # Should allow first 10 requests
        for i in range(10):
            is_allowed, metadata = limiter.check_rate_limit(client_id)
            assert is_allowed, f"Request {i+1} should be allowed"
            assert metadata["limit"] == 10
            assert metadata["remaining"] == 9 - i

    def test_rate_limiter_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(requests_per_minute=5)
        client_id = "test_client"

        # Use up the limit
        for _ in range(5):
            is_allowed, _ = limiter.check_rate_limit(client_id)
            assert is_allowed

        # Next request should be blocked
        is_allowed, metadata = limiter.check_rate_limit(client_id)
        assert not is_allowed
        assert metadata["remaining"] == 0

    def test_rate_limiter_resets_after_window(self):
        """Test that rate limit resets after time window."""
        limiter = RateLimiter(requests_per_minute=2)
        limiter.window_size = 1  # 1 second window for testing
        client_id = "test_client"

        # Use up the limit
        limiter.check_rate_limit(client_id)
        limiter.check_rate_limit(client_id)

        # Should be blocked
        is_allowed, _ = limiter.check_rate_limit(client_id)
        assert not is_allowed

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        is_allowed, metadata = limiter.check_rate_limit(client_id)
        assert is_allowed
        assert metadata["remaining"] == 1

    def test_rate_limiter_separate_clients(self):
        """Test that different clients have separate limits."""
        limiter = RateLimiter(requests_per_minute=2)

        client1 = "client_1"
        client2 = "client_2"

        # Client 1 uses limit
        limiter.check_rate_limit(client1)
        limiter.check_rate_limit(client1)

        # Client 1 blocked
        is_allowed, _ = limiter.check_rate_limit(client1)
        assert not is_allowed

        # Client 2 still allowed
        is_allowed, _ = limiter.check_rate_limit(client2)
        assert is_allowed

    def test_rate_limiter_metadata(self):
        """Test that metadata contains correct information."""
        limiter = RateLimiter(requests_per_minute=5)
        client_id = "test_client"

        is_allowed, metadata = limiter.check_rate_limit(client_id)

        assert "limit" in metadata
        assert "remaining" in metadata
        assert "reset" in metadata
        assert metadata["limit"] == 5
        assert metadata["remaining"] == 4
        assert isinstance(metadata["reset"], int)


# ============================================================================
# APIKeyAuthenticator Tests
# ============================================================================

class TestAPIKeyAuthenticator:
    """Test API key authentication."""

    def test_authenticator_with_auth_disabled(self):
        """Test that all requests are allowed when auth is disabled."""
        with patch.dict(os.environ, {"REQUIRE_API_KEY": "false"}):
            auth = APIKeyAuthenticator()

            is_authenticated, client_id = auth.authenticate(None)
            assert is_authenticated
            assert client_id == "anonymous"

            is_authenticated, client_id = auth.authenticate("any_key")
            assert is_authenticated
            assert client_id == "anonymous"

    def test_authenticator_with_auth_enabled_valid_key(self):
        """Test authentication with valid API key."""
        test_key = "sk_test_key_123"
        with patch.dict(
            os.environ, {"REQUIRE_API_KEY": "true", "VALID_API_KEYS": test_key}
        ):
            auth = APIKeyAuthenticator()

            is_authenticated, client_id = auth.authenticate(test_key)
            assert is_authenticated
            assert client_id == test_key

    def test_authenticator_with_auth_enabled_invalid_key(self):
        """Test authentication with invalid API key."""
        with patch.dict(
            os.environ,
            {"REQUIRE_API_KEY": "true", "VALID_API_KEYS": "sk_valid_key"},
        ):
            auth = APIKeyAuthenticator()

            is_authenticated, error_msg = auth.authenticate("sk_invalid_key")
            assert not is_authenticated
            assert error_msg == "Invalid API key"

    def test_authenticator_with_auth_enabled_missing_key(self):
        """Test authentication with missing API key."""
        with patch.dict(
            os.environ,
            {"REQUIRE_API_KEY": "true", "VALID_API_KEYS": "sk_valid_key"},
        ):
            auth = APIKeyAuthenticator()

            is_authenticated, error_msg = auth.authenticate(None)
            assert not is_authenticated
            assert error_msg == "Missing API key"

    def test_authenticator_multiple_keys(self):
        """Test authentication with multiple valid keys."""
        keys = "sk_key_1,sk_key_2,sk_key_3"
        with patch.dict(os.environ, {"REQUIRE_API_KEY": "true", "VALID_API_KEYS": keys}):
            auth = APIKeyAuthenticator()

            for key in ["sk_key_1", "sk_key_2", "sk_key_3"]:
                is_authenticated, client_id = auth.authenticate(key)
                assert is_authenticated
                assert client_id == key


# ============================================================================
# Middleware Integration Tests
# ============================================================================

class TestRateLimitMiddleware:
    """Test the rate limit middleware integration."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        @app.get("/health")
        def health_endpoint():
            return {"status": "ok"}

        # Add rate limiting (low limit for testing)
        app.add_middleware(RateLimitMiddleware, requests_per_minute=3)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_middleware_allows_within_limit(self, client):
        """Test that requests within limit are allowed."""
        with patch.dict(os.environ, {"REQUIRE_API_KEY": "false"}):
            # First 3 requests should succeed
            for i in range(3):
                response = client.get("/test")
                assert response.status_code == 200
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers

    def test_middleware_blocks_over_limit(self, client):
        """Test that requests over limit are blocked."""
        with patch.dict(os.environ, {"REQUIRE_API_KEY": "false"}):
            # Use up the limit
            for _ in range(3):
                client.get("/test")

            # Next request should be rate limited
            response = client.get("/test")
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]
            assert "Retry-After" in response.headers

    def test_middleware_exempts_health_check(self, client):
        """Test that health check is exempt from rate limiting."""
        with patch.dict(os.environ, {"REQUIRE_API_KEY": "false"}):
            # Health check should work even after rate limit
            for _ in range(3):
                client.get("/test")

            # Should still work
            response = client.get("/health")
            assert response.status_code == 200

    def test_middleware_with_api_key_auth(self, client):
        """Test middleware with API key authentication enabled."""
        test_key = "sk_test_key"
        with patch.dict(
            os.environ, {"REQUIRE_API_KEY": "true", "VALID_API_KEYS": test_key}
        ):
            # Without API key - should fail
            response = client.get("/test")
            assert response.status_code == 401

            # With valid API key - should succeed
            response = client.get("/test", headers={"X-API-Key": test_key})
            assert response.status_code == 200

            # With invalid API key - should fail
            response = client.get("/test", headers={"X-API-Key": "wrong_key"})
            assert response.status_code == 401


# ============================================================================
# Helper Functions Tests
# ============================================================================

class TestHelperFunctions:
    """Test helper functions."""

    def test_get_client_identifier_from_api_key(self):
        """Test client identification from API key."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "sk_test_key"}
        request.client = Mock(host="192.168.1.1")

        identifier = get_client_identifier(request)
        assert identifier == "key:sk_test_key"

    def test_get_client_identifier_from_forwarded_header(self):
        """Test client identification from X-Forwarded-For."""
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.1, 198.51.100.1"}
        request.client = Mock(host="192.168.1.1")

        identifier = get_client_identifier(request)
        assert identifier == "203.0.113.1"

    def test_get_client_identifier_from_client_ip(self):
        """Test client identification from client IP."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="192.168.1.1")

        identifier = get_client_identifier(request)
        assert identifier == "192.168.1.1"

    def test_get_client_identifier_unknown(self):
        """Test client identification when no info available."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        identifier = get_client_identifier(request)
        assert identifier == "unknown"

    def test_generate_api_key(self):
        """Test API key generation."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        # Keys should start with sk_
        assert key1.startswith("sk_")
        assert key2.startswith("sk_")

        # Keys should be unique
        assert key1 != key2

        # Keys should be reasonably long
        assert len(key1) > 20


# ============================================================================
# Performance Tests
# ============================================================================

class TestRateLimiterPerformance:
    """Test rate limiter performance."""

    def test_rate_limiter_handles_many_clients(self):
        """Test that rate limiter scales with many clients."""
        limiter = RateLimiter(requests_per_minute=10)

        # Simulate 1000 different clients
        for i in range(1000):
            client_id = f"client_{i}"
            is_allowed, _ = limiter.check_rate_limit(client_id)
            assert is_allowed

    def test_rate_limiter_cleanup_works(self):
        """Test that old requests are cleaned up."""
        limiter = RateLimiter(requests_per_minute=5)
        limiter.window_size = 1  # 1 second window
        client_id = "test_client"

        # Generate some requests
        for _ in range(3):
            limiter.check_rate_limit(client_id)

        # Wait for cleanup
        time.sleep(1.1)

        # Check that old requests were cleaned
        limiter._clean_old_requests(client_id, time.time())
        assert len(limiter.requests[client_id]) == 0
