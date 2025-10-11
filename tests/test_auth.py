"""Tests for authentication module."""

import pytest
from datetime import timedelta
from core.security.auth import AuthService


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password_123"
    hashed = AuthService.get_password_hash(password)
    
    assert hashed != password
    assert AuthService.verify_password(password, hashed)
    assert not AuthService.verify_password("wrong_password", hashed)


def test_create_access_token():
    """Test JWT access token creation."""
    data = {"sub": "user123", "email": "test@example.com"}
    token = AuthService.create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_refresh_token():
    """Test JWT refresh token creation."""
    data = {"sub": "user123"}
    token = AuthService.create_refresh_token(data)
    
    assert token is not None
    assert isinstance(token, str)


def test_decode_token():
    """Test JWT token decoding."""
    data = {"sub": "user123", "email": "test@example.com"}
    token = AuthService.create_access_token(data)
    
    decoded = AuthService.decode_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "user123"
    assert decoded.get("email") == "test@example.com"


def test_decode_invalid_token():
    """Test decoding invalid token."""
    invalid_token = "invalid.token.here"
    decoded = AuthService.decode_token(invalid_token)
    
    assert decoded is None


def test_token_expiration():
    """Test token with custom expiration."""
    data = {"sub": "user123"}
    expires_delta = timedelta(minutes=1)
    token = AuthService.create_access_token(data, expires_delta=expires_delta)
    
    decoded = AuthService.decode_token(token)
    assert decoded is not None
    assert "exp" in decoded
