import unittest
from unittest.mock import patch, Mock, AsyncMock, mock_open
import os
import tempfile
import asyncio

from .server import mcp_http_request, fetch_content_and_write_to_file
from .request import Response, RequestError, ArgumentError


def async_test(test_func):
    """Decorator to make async test functions work with unittest"""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(test_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


class TestMcpHttpRequest(unittest.TestCase):
    """Test mcp_http_request function"""

    @patch('mcp_server_requests.server.http_request')
    def test_successful_request(self, mock_http_request):
        """Test successful HTTP request"""
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "application/json")], '{"success": true}'
        )
        mock_http_request.return_value = mock_response

        result = mcp_http_request("GET", "https://example.com")

        self.assertIn('{"success": true}', result)
        mock_http_request.assert_called_once_with("GET", "https://example.com", query=None, headers={}, data=None, json_=None)

    @patch('mcp_server_requests.server.http_request')
    def test_request_with_custom_headers(self, mock_http_request):
        """Test request with custom headers"""
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")], "content"
        )
        mock_http_request.return_value = mock_response

        custom_headers = {"Authorization": "Bearer token", "Custom": "value"}
        result = mcp_http_request("GET", "https://example.com", headers=custom_headers)

        mock_http_request.assert_called_once()
        call_headers = mock_http_request.call_args[1]['headers']
        self.assertEqual(call_headers["Authorization"], "Bearer token")
        self.assertEqual(call_headers["Custom"], "value")

    @patch('mcp_server_requests.server.http_request')
    def test_request_with_user_agent(self, mock_http_request):
        """Test request with custom user agent"""
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")], "content"
        )
        mock_http_request.return_value = mock_response

        result = mcp_http_request(
            "GET", "https://example.com",
            user_agent="Test-Agent/1.0",
            force_user_agnet=True
        )

        mock_http_request.assert_called_once()
        call_headers = mock_http_request.call_args[1]['headers']
        self.assertEqual(call_headers["User-Agent"], "Test-Agent/1.0")

    @patch('mcp_server_requests.server.http_request')
    def test_request_with_existing_user_agent_header(self, mock_http_request):
        """Test request with existing User-Agent header"""
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")], "content"
        )
        mock_http_request.return_value = mock_response

        headers = {"User-Agent": "Existing-Agent/1.0"}
        result = mcp_http_request("GET", "https://example.com", headers=headers)

        mock_http_request.assert_called_once()
        call_headers = mock_http_request.call_args[1]['headers']
        self.assertEqual(call_headers["User-Agent"], "Existing-Agent/1.0")

    @patch('mcp_server_requests.server.http_request')
    def test_request_with_query_and_data(self, mock_http_request):
        """Test request with query parameters and data"""
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")], "success"
        )
        mock_http_request.return_value = mock_response

        query_params = {"param1": "value1", "param2": 42}
        data = "test data"

        result = mcp_http_request(
            "POST", "https://example.com",
            query=query_params,
            data=data
        )

        mock_http_request.assert_called_once_with(
            "POST", "https://example.com",
            query=query_params,
            headers={},
            data=data,
            json_=None
        )

    @patch('mcp_server_requests.server.http_request')
    def test_request_with_json(self, mock_http_request):
        """Test request with JSON data"""
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 201, "Created",
            [("Content-Type", "application/json")], '{"id": 123}'
        )
        mock_http_request.return_value = mock_response

        json_data = {"name": "test", "value": 123}

        result = mcp_http_request(
            "POST", "https://example.com",
            json=json_data
        )

        mock_http_request.assert_called_once_with(
            "POST", "https://example.com",
            query=None,
            headers={},
            data=None,
            json_=json_data
        )

    @patch('mcp_server_requests.server.http_request')
    def test_request_error_handling(self, mock_http_request):
        """Test request error handling"""
        mock_http_request.side_effect = RequestError("Connection failed", "Network timeout")

        result = mcp_http_request("GET", "https://example.com")

        self.assertIn("encountered an internal error when making a request", result)
        self.assertIn("Connection failed", result)

    @patch('mcp_server_requests.server.http_request')
    def test_argument_error_handling(self, mock_http_request):
        """Test argument error handling"""
        mock_http_request.side_effect = ArgumentError("Invalid URL", "URL is required")

        result = mcp_http_request("GET", "")

        self.assertIn("found an error while checking parameters", result)
        self.assertIn("Invalid URL", result)

    @patch('mcp_server_requests.server.http_request')
    def test_general_exception_handling(self, mock_http_request):
        """Test general exception handling"""
        mock_http_request.side_effect = Exception("Unexpected error")

        result = mcp_http_request("GET", "https://example.com")

        self.assertIn("An unexpected error occurred", result)

    @patch('mcp_server_requests.server.http_request')
    def test_format_status_and_headers_options(self, mock_http_request):
        """Test format_status and format_headers options"""
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain"), ("Cache-Control", "no-cache")], "content"
        )
        mock_http_request.return_value = mock_response

        # Test with format_status=False, format_headers=False
        result = mcp_http_request(
            "GET", "https://example.com",
            format_status=False,
            format_headers=False
        )
        self.assertEqual(result, "content")

        # Test with format_status=True, format_headers=True
        result = mcp_http_request(
            "GET", "https://example.com",
            format_status=True,
            format_headers=True
        )
        self.assertIn("HTTP/1.1 200 OK", result)
        self.assertIn("Content-Type: text/plain", result)
        self.assertIn("Cache-Control: no-cache", result)
        self.assertIn("content", result)

    @patch('mcp_server_requests.server.http_request')
    def test_return_content_options(self, mock_http_request):
        """Test return_content options"""
        html_content = "<html><body><h1>Test</h1></body></html>"
        mock_response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/html")], html_content
        )
        mock_http_request.return_value = mock_response

        # Test raw format
        result = mcp_http_request("GET", "https://example.com", return_content="raw", format_status=False, format_headers=False)
        self.assertEqual(result, html_content)

        # Test markdown format
        result = mcp_http_request("GET", "https://example.com", return_content="markdown", format_status=False, format_headers=False)
        self.assertNotIn("<html>", result)
        self.assertIn("Test", result)


class TestFetchContentAndWriteToFile(unittest.TestCase):
    """Test fetch_content_and_write_to_file function"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "test_file.txt")
        self.test_url = "https://example.com/content"
        self.test_content = "Test content for file"

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_successful_fetch_and_write(self, mock_mcp_request):
        """Test successful content fetch and file write"""
        mock_mcp_request.return_value = self.test_content

        # Mock Context with minimal implementation
        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[])

        result = await fetch_content_and_write_to_file(
            self.test_url,
            self.test_file_path,
            "raw",
            mock_ctx
        )

        self.assertIn("successfully written to", result)
        self.assertIn(str(len(self.test_content)), result)
        self.assertIn(self.test_file_path, result)

        # Verify file was created with correct content
        with open(self.test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, self.test_content)

        mock_mcp_request.assert_called_once_with(
            "GET", self.test_url,
            return_content="raw",
            user_agent="mcp-server-requests",
            force_user_agnet=False,
            format_status=False,
            format_headers=False
        )

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_fetch_and_write_with_workspace_root(self, mock_mcp_request):
        """Test fetch and write with workspace root"""
        mock_mcp_request.return_value = self.test_content

        # Mock Context with workspace root
        mock_root = Mock()
        mock_root.uri.scheme = "file"
        mock_root.uri.path = self.temp_dir

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[mock_root])

        relative_path = "subdir/test_file.txt"
        expected_full_path = os.path.join(self.temp_dir, relative_path.replace('/', os.sep))

        result = await fetch_content_and_write_to_file(
            self.test_url,
            relative_path,
            "markdown",
            mock_ctx,
            use_workspace_root=True
        )

        self.assertIn("successfully written to", result)
        self.assertIn(expected_full_path, result)

        # Verify file was created
        with open(expected_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, self.test_content)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_no_workspace_root_error(self, mock_mcp_request):
        """Test error when no workspace root is available"""
        mock_mcp_request.return_value = self.test_content

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[])

        result = await fetch_content_and_write_to_file(
            self.test_url,
            "relative/path.txt",
            "raw",
            mock_ctx,
            use_workspace_root=True
        )

        self.assertIn("Error: No workspace root available", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_multiple_workspace_roots_error(self, mock_mcp_request):
        """Test error when multiple workspace roots are found"""
        mock_mcp_request.return_value = self.test_content

        mock_root1 = Mock()
        mock_root1.uri.scheme = "file"
        mock_root2 = Mock()
        mock_root2.uri.scheme = "file"

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[mock_root1, mock_root2])

        result = await fetch_content_and_write_to_file(
            self.test_url,
            "relative/path.txt",
            "raw",
            mock_ctx,
            use_workspace_root=True
        )

        self.assertIn("Error: Multiple workspace roots found", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_non_file_uri_scheme_error(self, mock_mcp_request):
        """Test error when workspace root is not file:// URI"""
        mock_mcp_request.return_value = self.test_content

        mock_root = Mock()
        mock_root.uri.scheme = "http"

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[mock_root])

        result = await fetch_content_and_write_to_file(
            self.test_url,
            "relative/path.txt",
            "raw",
            mock_ctx,
            use_workspace_root=True
        )

        self.assertIn("Error: Workspace root is not a file:// URI", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_external_file_access_denied(self, mock_mcp_request):
        """Test error when external file access is denied"""
        mock_mcp_request.return_value = self.test_content

        mock_root = Mock()
        mock_root.uri.scheme = "file"
        mock_root.uri.path = self.temp_dir

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[mock_root])

        # Try to access a path outside the workspace root
        external_path = os.path.join(os.path.dirname(self.temp_dir), "external.txt")

        result = await fetch_content_and_write_to_file(
            self.test_url,
            external_path,
            "raw",
            mock_ctx,
            use_workspace_root=True,
            allow_external_file_access=True
        )

        self.assertIn("Error: Access denied", result)
        self.assertIn("outside workspace root", result)

    @async_test
    async def test_absolute_path_required_error(self):
        """Test error when absolute path is required but not provided"""
        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[])

        result = await fetch_content_and_write_to_file(
            self.test_url,
            "relative/path.txt",  # Not absolute
            "raw",
            mock_ctx,
            use_workspace_root=False
        )

        self.assertIn("Error: Path must be absolute", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_protected_paths_windows(self, mock_mcp_request):
        """Test protection of Windows system paths"""
        mock_mcp_request.return_value = self.test_content

        # Mock both os.name and os.path.join for Windows behavior
        with patch('mcp_server_requests.server.os.name', 'nt'), \
             patch('os.path.join', side_effect=lambda *args: '\\'.join(args)):
            mock_ctx = Mock()
            mock_ctx.list_roots = AsyncMock(return_value=[])

            protected_path = r"C:\Windows\test.txt"

            result = await fetch_content_and_write_to_file(
                self.test_url,
                protected_path,
                "raw",
                mock_ctx,
                use_workspace_root=False
            )

            self.assertIn("Error: Do not allow writing to protected paths", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_protected_paths_unix(self, mock_mcp_request):
        """Test protection of Unix/Linux system paths"""
        mock_mcp_request.return_value = self.test_content

        # Mock os.name for Unix behavior
        with patch('mcp_server_requests.server.os.name', 'posix'):
            mock_ctx = Mock()
            mock_ctx.list_roots = AsyncMock(return_value=[])

            protected_path = "/etc/test.txt"

            result = await fetch_content_and_write_to_file(
                self.test_url,
                protected_path,
                "raw",
                mock_ctx,
                use_workspace_root=False
            )

            self.assertIn("Error: Do not allow writing to protected paths", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @patch('os.makedirs')
    @async_test
    async def test_directory_creation_error(self, mock_makedirs, mock_mcp_request):
        """Test error when directory creation fails"""
        mock_mcp_request.return_value = self.test_content
        mock_makedirs.side_effect = OSError("Permission denied")

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[])

        nested_path = os.path.join(self.temp_dir, "nested", "subdir", "file.txt")

        result = await fetch_content_and_write_to_file(
            self.test_url,
            nested_path,
            "raw",
            mock_ctx,
            use_workspace_root=False
        )

        self.assertIn("Error: Unable to create directory", result)
        self.assertIn("Permission denied", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @patch('builtins.open', new_callable=mock_open)
    @async_test
    async def test_file_write_error(self, mock_file, mock_mcp_request):
        """Test error when file write fails"""
        mock_mcp_request.return_value = self.test_content
        mock_file.side_effect = OSError("Disk full")

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[])

        result = await fetch_content_and_write_to_file(
            self.test_url,
            self.test_file_path,
            "raw",
            mock_ctx,
            use_workspace_root=False
        )

        self.assertIn("Error: Unable to write to file", result)
        self.assertIn("Disk full", result)

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_custom_user_agent(self, mock_mcp_request):
        """Test custom user agent parameter"""
        mock_mcp_request.return_value = self.test_content

        mock_ctx = Mock()
        mock_ctx.list_roots = AsyncMock(return_value=[])

        await fetch_content_and_write_to_file(
            self.test_url,
            self.test_file_path,
            "raw",
            mock_ctx,
            user_agent="Custom-Agent/1.0",
            force_user_agent=True
        )

        mock_mcp_request.assert_called_once_with(
            "GET", self.test_url,
            return_content="raw",
            user_agent="Custom-Agent/1.0",
            force_user_agnet=True,
            format_status=False,
            format_headers=False
        )

    @patch('mcp_server_requests.server.mcp_http_request')
    @async_test
    async def test_different_content_formats(self, mock_mcp_request):
        """Test different content processing formats"""
        test_html = "<html><body><h1>Test</h1></body></html>"

        for content_format in ["raw", "basic_clean", "strict_clean", "markdown"]:
            with self.subTest(format=content_format):
                mock_mcp_request.return_value = f"Processed as {content_format}: {test_html}"

                mock_ctx = Mock()
                mock_ctx.list_roots = AsyncMock(return_value=[])

                file_path = os.path.join(self.temp_dir, f"test_{content_format}.txt")

                result = await fetch_content_and_write_to_file(
                    self.test_url,
                    file_path,
                    content_format,
                    mock_ctx,
                    use_workspace_root=False
                )

                self.assertIn("successfully written to", result)

                # Verify the call parameters
                mock_mcp_request.assert_called_with(
                    "GET", self.test_url,
                    return_content=content_format,
                    user_agent="mcp-server-requests",
                    force_user_agnet=False,
                    format_status=False,
                    format_headers=False
                )


if __name__ == '__main__':
    unittest.main()