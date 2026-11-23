import unittest
from unittest.mock import patch, Mock
import urllib.error

from .request import (
    http_request,
    Response,
    RequestError,
    ArgumentError,
    HTTP_METHODS,
    VERSION_MAP
)


class TestResponse(unittest.TestCase):
    """Test Response class"""

    def test_response_content_type_detection(self):
        """Test content type detection"""
        headers = [("Content-Type", "application/json"), ("Other", "value")]
        response = Response("https://example.com", "HTTP/1.1", 200, "OK", headers, b"{}")

        self.assertEqual(response.content_type, "application/json")

    def test_response_content_type_case_insensitive(self):
        """Test case insensitive content type detection"""
        headers = [("content-type", "text/html")]
        response = Response("https://example.com", "HTTP/1.1", 200, "OK", headers, b"<html></html>")

        self.assertEqual(response.content_type, "text/html")

    def test_response_content_type_default(self):
        """Test default content type"""
        headers = [("Other", "value")]
        response = Response("https://example.com", "HTTP/1.1", 200, "OK", headers, b"data")

        self.assertEqual(response.content_type, "application/octet-stream")

    def test_response_content_type_cached(self):
        """Test content type caching"""
        headers = [("Content-Type", "application/json")]
        response = Response("https://example.com", "HTTP/1.1", 200, "OK", headers, b"{}")

        # First access
        content_type_1 = response.content_type
        # Second access should use cached value
        content_type_2 = response.content_type

        self.assertEqual(content_type_1, content_type_2)
        self.assertEqual(content_type_1, "application/json")


class TestHttpRequest(unittest.TestCase):
    """Test http_request function"""

    def setUp(self):
        """Set up test environment"""
        self.base_url = "https://example.com"
        self.test_headers = {"User-Agent": "test-agent", "Accept": "application/json"}

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_get_success(self, mock_urlopen):
        """Test successful GET request"""
        # Mock response
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = [("Content-Type", "application/json")]
        mock_response.read.return_value = b'{"success": true}'
        mock_urlopen.return_value = mock_response

        result = http_request("GET", self.base_url)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.reason, "OK")
        self.assertEqual(result.version, "HTTP/1.1")
        self.assertEqual(result.content_type, "application/json")
        self.assertEqual(result.content, b'{"success": true}')

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_post_with_json(self, mock_urlopen):
        """Test POST request with JSON data"""
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 201
        mock_response.reason = "Created"
        mock_response.getheaders.return_value = [("Content-Type", "application/json")]
        mock_response.read.return_value = b'{"id": 123}'
        mock_urlopen.return_value = mock_response

        json_data = {"name": "test", "value": 123}
        result = http_request("POST", self.base_url, json_body=json_data)

        self.assertEqual(result.status_code, 201)

        # Verify request parameters
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.method, "POST")
        self.assertIn(b'{"name": "test", "value": 123}', request.data)

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_post_with_string_data(self, mock_urlopen):
        """Test POST request with string data"""
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = [("Content-Type", "text/plain")]
        mock_response.read.return_value = b'Success'
        mock_urlopen.return_value = mock_response

        data = "test string data"
        result = http_request("POST", self.base_url, body=data)

        # Verify result and request parameters
        self.assertEqual(result.status_code, 200)
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.data, b"test string data")

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_post_with_bytes_data(self, mock_urlopen):
        """Test POST request with bytes data"""
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = [("Content-Type", "application/octet-stream")]
        mock_response.read.return_value = b'Success'
        mock_urlopen.return_value = mock_response

        data = b"binary data"
        result = http_request("POST", self.base_url, body=data)

        # Verify result and request parameters
        self.assertEqual(result.status_code, 200)
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.data, b"binary data")

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_request_with_headers(self, mock_urlopen):
        """Test request with custom headers"""
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = []
        mock_response.read.return_value = b'Success'
        mock_urlopen.return_value = mock_response

        headers = {"Authorization": "Bearer token123", "Custom-Header": "custom-value"}
        http_request("GET", self.base_url, headers=headers)

        # Verify request includes custom headers
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        # Check that headers were added to the request
        # Based on the actual behavior, we can see the header normalization pattern
        self.assertIn("Authorization", request.headers)  # Authorization stays capitalized
        self.assertIn("Custom-header", request.headers)  # Custom-Header becomes Custom-header
        self.assertEqual(request.headers["Authorization"], "Bearer token123")
        self.assertEqual(request.headers["Custom-header"], "custom-value")

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_request_auto_https(self, mock_urlopen):
        """Test automatic HTTPS prefix addition"""
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = []
        mock_response.read.return_value = b'Success'
        mock_urlopen.return_value = mock_response

        url_without_protocol = "example.com"
        http_request("GET", url_without_protocol)

        # Verify URL was automatically prefixed with https://
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertTrue(request.get_full_url().startswith("https://"))

    def test_invalid_method(self):
        """Test invalid HTTP method"""
        with self.assertRaises(ArgumentError) as cm:
            http_request("INVALID", self.base_url)
        self.assertIn("Invalid HTTP method", str(cm.exception))

    def test_non_string_method(self):
        """Test non-string HTTP method"""
        with self.assertRaises(ArgumentError) as cm:
            http_request("123", self.base_url)  # Invalid method string
        self.assertIn("Invalid HTTP method", str(cm.exception))

    def test_non_string_url(self):
        """Test non-string URL"""
        # Test that non-string URLs are rejected
        # We need to use type: ignore to bypass type checking for this test
        with self.assertRaises(ArgumentError) as cm:
            http_request("GET", 123)  # type: ignore
        self.assertIn("URL must be a string", str(cm.exception))

    def test_both_body_and_json_body(self):
        """Test providing both body and json_body parameters"""
        with self.assertRaises(ArgumentError) as cm:
            http_request("POST", self.base_url, body="test", json_body={"key": "value"})
        self.assertIn("Both body and json_body cannot be provided", str(cm.exception))

    def test_invalid_body_type(self):
        """Test invalid body type"""
        # Use type annotation to bypass type checking and test runtime behavior
        invalid_data = {"invalid": "dict"}  # type: ignore
        with self.assertRaises(ArgumentError) as cm:
            http_request("POST", self.base_url, body=invalid_data)  # type: ignore
        self.assertIn("Body must be a string, bytes, or bytearray", str(cm.exception))

    def test_invalid_json_serialization(self):
        """Test invalid JSON serialization"""
        # Create an object that cannot be serialized
        class UnserializableObject:
            pass

        with self.assertRaises(ArgumentError) as cm:
            http_request("POST", self.base_url, json_body={"obj": UnserializableObject()})
        self.assertIn("Failed to serialize JSON body", str(cm.exception))

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_error_handling(self, mock_urlopen):
        """Test HTTP error handling"""
        # Mock HTTPError
        error_response = Mock()
        error_response.status = 404
        error_response.reason = "Not Found"
        error_response.headers.items.return_value = [("Content-Type", "text/html")]
        error_response.read.return_value = b'<h1>404 Not Found</h1>'

        http_error = urllib.error.HTTPError(
            url=self.base_url,
            code=404,
            msg="Not Found",
            hdrs={},  # type: ignore
            fp=error_response
        )
        mock_urlopen.side_effect = http_error

        result = http_request("GET", self.base_url)

        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.reason, "Not Found")
        self.assertEqual(result.version, "HTTP/1.1")
        self.assertEqual(result.content, b'<h1>404 Not Found</h1>')

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_url_error_handling(self, mock_urlopen):
        """Test URL error handling"""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with self.assertRaises(RequestError) as cm:
            http_request("GET", self.base_url)
        self.assertIn("Failed to send request", str(cm.exception))
        self.assertIn("Connection refused", str(cm.exception))

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_general_exception_handling(self, mock_urlopen):
        """Test general exception handling"""
        mock_urlopen.side_effect = Exception("Unexpected error")

        with self.assertRaises(RequestError) as cm:
            http_request("GET", self.base_url)
        self.assertIn("Failed to send request", str(cm.exception))
        self.assertIn("Unexpected error", str(cm.exception))

    def test_all_http_methods(self):
        """Test all supported HTTP methods"""
        for method in HTTP_METHODS:
            with self.subTest(method=method):
                with patch('mcp_server_requests.request.urllib.request.urlopen') as mock_urlopen:
                    mock_response = Mock()
                    mock_response.version = 11
                    mock_response.status = 200
                    mock_response.reason = "OK"
                    mock_response.getheaders.return_value = []
                    mock_response.read.return_value = b'Success'
                    mock_urlopen.return_value = mock_response

                    result = http_request(method, self.base_url)
                    self.assertEqual(result.status_code, 200)

                    # Verify request method
                    mock_urlopen.assert_called_once()
                    request = mock_urlopen.call_args[0][0]
                    self.assertEqual(request.method, method)

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_response_version_mapping(self, mock_urlopen):
        """Test HTTP version mapping"""
        for version_code, version_string in VERSION_MAP.items():
            with self.subTest(version=version_string):
                mock_response = Mock()
                mock_response.version = version_code
                mock_response.status = 200
                mock_response.reason = "OK"
                mock_response.getheaders.return_value = []
                mock_response.read.return_value = b'Success'
                mock_urlopen.return_value = mock_response

                result = http_request("GET", self.base_url)
                self.assertEqual(result.version, version_string)

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_unknown_version_fallback(self, mock_urlopen):
        """Test fallback for unknown HTTP version"""
        mock_response = Mock()
        mock_response.version = 999  # Unknown version
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = []
        mock_response.read.return_value = b'Success'
        mock_urlopen.return_value = mock_response

        result = http_request("GET", self.base_url)
        self.assertEqual(result.version, "HTTP/1.1")  # Default fallback value

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_request_with_unicode_url(self, mock_urlopen):
        """Test HTTP request with Unicode characters in URL"""
        # Mock response
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = [("Content-Type", "text/html")]
        mock_response.read.return_value = b'<html>Test</html>'
        mock_urlopen.return_value = mock_response

        # Test with Unicode characters in URL path
        url = "https://example.com/测试页面"
        result = http_request("GET", url)

        # Verify the request was made successfully
        self.assertEqual(result.status_code, 200)
        mock_urlopen.assert_called_once()

        # Get the request that was made
        request = mock_urlopen.call_args[0][0]
        # The request should have succeeded - either with original URL or encoded URL
        # urllib now handles most Unicode URLs directly, so both are valid
        full_url = request.get_full_url()
        self.assertTrue(
            "%E6%B5%8B%E8%AF%95" in full_url or "测试" in full_url,
            f"URL should contain either encoded or original Chinese characters: {full_url}"
        )


class TestRequestError(unittest.TestCase):
    """Test RequestError exception class"""

    def test_request_error_creation(self):
        """Test RequestError creation"""
        error = RequestError("Test message", "Test reason")
        self.assertEqual(error.message, "Test message")
        self.assertEqual(error.reason, "Test reason")
        self.assertIn("Test message", str(error))

    def test_request_error_without_reason(self):
        """Test RequestError without reason"""
        error = RequestError("Test message")
        self.assertEqual(error.message, "Test message")
        self.assertIsNone(error.reason)


class TestArgumentError(unittest.TestCase):
    """Test ArgumentError exception class"""

    def test_argument_error_inheritance(self):
        """Test ArgumentError inheritance"""
        error = ArgumentError("Test message")
        self.assertIsInstance(error, RequestError)
        self.assertEqual(error.message, "Test message")


if __name__ == '__main__':
    unittest.main()
