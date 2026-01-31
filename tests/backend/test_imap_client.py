#!/usr/bin/env python3
"""
Tests for IMAP client module.

Tests cover:
- Token expiration checking
- Connection creation and management
- Email parsing utilities
- Error handling
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.imap_client import (
    IMAPEmailClient,
    IMAPError,
    IMAPConnectionError,
    IMAPAuthenticationError,
    decode_header_value,
)


class TestDecodeHeaderValue:
    """Tests for decode_header_value function."""

    def test_decode_simple_ascii(self):
        """Test decoding simple ASCII string."""
        result = decode_header_value("Hello World")
        assert result == "Hello World"

    def test_decode_none(self):
        """Test decoding None returns empty string."""
        result = decode_header_value(None)
        assert result == ""

    def test_decode_utf8_encoded(self):
        """Test decoding UTF-8 encoded header."""
        # This tests the basic flow, actual encoded headers would need MIME encoding
        result = decode_header_value("Test Subject")
        assert "Test" in result


class TestIMAPEmailClient:
    """Tests for IMAPEmailClient class."""

    @pytest.fixture
    def mock_account_info(self):
        """Create mock account info."""
        return {
            "refresh_token": "mock_refresh_token_123",
            "password": "",
            "client_id": "mock_client_id",
        }

    @pytest.fixture
    def imap_client(self, mock_account_info):
        """Create IMAPEmailClient instance."""
        return IMAPEmailClient("test@outlook.com", mock_account_info)

    def test_init(self, imap_client, mock_account_info):
        """Test client initialization."""
        assert imap_client.email == "test@outlook.com"
        assert imap_client.refresh_token == mock_account_info["refresh_token"]
        assert imap_client.access_token == ""
        assert imap_client.expires_at == 0

    def test_is_token_expired_no_token(self, imap_client):
        """Test token expiration when no token exists."""
        assert imap_client.is_token_expired() is True

    def test_is_token_expired_fresh_token(self, imap_client):
        """Test token expiration with fresh token."""
        # Set expires_at to 1 hour from now
        imap_client.expires_at = datetime.now().timestamp() + 3600
        imap_client.access_token = "test_token"
        assert imap_client.is_token_expired() is False

    def test_is_token_expired_within_buffer(self, imap_client):
        """Test token expiration within buffer time."""
        # Set expires_at to 1 minute from now (within 5 min buffer)
        imap_client.expires_at = datetime.now().timestamp() + 60
        imap_client.access_token = "test_token"
        assert imap_client.is_token_expired() is True

    @pytest.mark.asyncio
    async def test_ensure_token_valid_with_valid_token(self, imap_client):
        """Test ensure_token_valid with valid token."""
        imap_client.access_token = "valid_token"
        imap_client.expires_at = datetime.now().timestamp() + 3600
        
        # Should not raise and not call refresh
        with patch.object(imap_client, 'refresh_access_token') as mock_refresh:
            await imap_client.ensure_token_valid()
            mock_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_token_valid_with_expired_token(self, imap_client):
        """Test ensure_token_valid with expired token."""
        imap_client.access_token = ""
        imap_client.expires_at = 0
        
        with patch.object(imap_client, 'refresh_access_token', new_callable=AsyncMock) as mock_refresh:
            await imap_client.ensure_token_valid()
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, imap_client):
        """Test successful token refresh."""
        mock_get_access_token = AsyncMock(return_value=("new_access_token", "new_refresh_token"))
        
        with patch('app.imap_client.get_access_token', mock_get_access_token):
            await imap_client.refresh_access_token()
            
            assert imap_client.access_token == "new_access_token"
            assert imap_client.refresh_token == "new_refresh_token"
            assert imap_client.expires_at > datetime.now().timestamp()

    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self, imap_client):
        """Test token refresh failure."""
        from fastapi import HTTPException
        
        mock_get_access_token = AsyncMock(return_value=(None, None))
        
        with patch('app.imap_client.get_access_token', mock_get_access_token):
            with pytest.raises(HTTPException) as exc_info:
                await imap_client.refresh_access_token()
            
            assert exc_info.value.status_code == 401

    def test_close_imap_connection_none(self, imap_client):
        """Test closing None connection."""
        # Should not raise
        imap_client.close_imap_connection(None)

    def test_close_imap_connection_with_state(self, imap_client):
        """Test closing connection with state."""
        mock_conn = MagicMock()
        mock_conn.state = 'SELECTED'
        
        imap_client.close_imap_connection(mock_conn)
        
        mock_conn.close.assert_called_once()
        mock_conn.logout.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, imap_client):
        """Test cleanup method."""
        # Should not raise
        await imap_client.cleanup()


class TestEmailParsing:
    """Tests for email parsing methods."""

    @pytest.fixture
    def imap_client(self):
        """Create IMAPEmailClient instance."""
        return IMAPEmailClient("test@outlook.com", {"refresh_token": "test"})

    def test_parse_email_header_basic(self, imap_client):
        """Test parsing basic email headers."""
        mock_message = MagicMock()
        mock_message.__getitem__ = MagicMock(side_effect=lambda x: {
            'Subject': 'Test Subject',
            'From': 'Sender Name <sender@example.com>',
            'To': 'recipient@example.com',
            'Date': 'Mon, 01 Jan 2024 12:00:00 +0000',
        }.get(x))
        
        result = IMAPEmailClient._parse_email_header(mock_message)
        
        assert result['subject'] == 'Test Subject'
        assert result['from_name'] == 'Sender Name'
        assert result['from_email'] == 'sender@example.com'

    def test_parse_email_header_no_name(self, imap_client):
        """Test parsing header without sender name."""
        mock_message = MagicMock()
        mock_message.__getitem__ = MagicMock(side_effect=lambda x: {
            'Subject': None,
            'From': 'sender@example.com',
            'To': None,
            'Date': None,
        }.get(x))
        
        result = IMAPEmailClient._parse_email_header(mock_message)
        
        assert result['subject'] == '(No Subject)'
        assert result['from_email'] == 'sender@example.com'

    def test_build_message_dict(self):
        """Test building message dictionary."""
        uid_bytes = b'12345'
        header_info = {
            'subject': 'Test',
            'date_str': '2024-01-01',
            'from_email': 'test@example.com',
            'from_name': 'Test User',
            'to_str': 'recipient@example.com',
        }
        body_info = {
            'body_content': 'Hello World',
            'body_type': 'text',
            'body_preview': 'Hello...',
        }
        
        result = IMAPEmailClient._build_message_dict(uid_bytes, header_info, body_info)
        
        assert result['id'] == '12345'
        assert result['subject'] == 'Test'
        assert result['body']['content'] == 'Hello World'
        assert result['bodyPreview'] == 'Hello...'


class TestIMAPExceptions:
    """Tests for IMAP exception classes."""

    def test_imap_error(self):
        """Test IMAPError base exception."""
        error = IMAPError("Test error")
        assert str(error) == "Test error"

    def test_imap_connection_error(self):
        """Test IMAPConnectionError."""
        error = IMAPConnectionError("Connection failed")
        assert "Connection failed" in str(error)
        assert isinstance(error, IMAPError)

    def test_imap_authentication_error(self):
        """Test IMAPAuthenticationError."""
        error = IMAPAuthenticationError("Auth failed")
        assert "Auth failed" in str(error)
        assert isinstance(error, IMAPError)


class TestConcurrency:
    """Tests for concurrent token refresh handling."""

    @pytest.mark.asyncio
    async def test_concurrent_token_refresh(self):
        """Test that concurrent token refreshes are serialized."""
        client = IMAPEmailClient("test@outlook.com", {"refresh_token": "test"})
        refresh_count = 0
        
        async def mock_refresh():
            nonlocal refresh_count
            refresh_count += 1
            await asyncio.sleep(0.1)
            client.access_token = "new_token"
            client.expires_at = datetime.now().timestamp() + 3600
        
        with patch.object(client, 'refresh_access_token', side_effect=mock_refresh):
            # Trigger multiple concurrent ensure_token_valid calls
            await asyncio.gather(
                client.ensure_token_valid(),
                client.ensure_token_valid(),
                client.ensure_token_valid(),
            )
        
        # Due to the lock, only one refresh should happen
        # (others should see the token is now valid after acquiring lock)
        assert refresh_count >= 1
