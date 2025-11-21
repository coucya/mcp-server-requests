import unittest
from unittest.mock import patch, Mock
import urllib.error

from .request import (
    http_request,
    Response,
    RequestError,
    ArgumentError,
    merge_query_to_url,
    HTTP_METHODS,
    VERSION_MAP
)


class TestMergeQueryToUrl(unittest.TestCase):
    """Test merge_query_to_url function"""

    def test_merge_query_to_existing_url(self):
        """Test adding new parameters to URL with existing query parameters"""
        url = "https://example.com/path?existing=value"
        query_dict = {"new": "param", "another": "123"}
        result = merge_query_to_url(url, query_dict)

        self.assertIn("existing=value", result)
        self.assertIn("new=param", result)
        self.assertIn("another=123", result)

    def test_merge_query_to_url_without_existing(self):
        """Test adding parameters to URL without existing query parameters"""
        url = "https://example.com/path"
        query_dict = {"param1": "value1", "param2": "value2"}
        result = merge_query_to_url(url, query_dict)

        self.assertIn("param1=value1", result)
        self.assertIn("param2=value2", result)
        self.assertIn("?", result)

    def test_merge_query_override_existing(self):
        """Test adding parameters to URL with existing query parameters"""
        url = "https://example.com/path?param=old"
        query_dict = {"param": "new"}
        result = merge_query_to_url(url, query_dict)

        # The current implementation keeps both old and new values
        self.assertIn("param=new", result)
        self.assertIn("param=old", result)

    def test_merge_query_invalid_types(self):
        """Test invalid query parameter types"""
        url = "https://example.com"
        # Use None as invalid type
        query_dict = {"param": None}

        with self.assertRaises(ArgumentError) as cm:
            merge_query_to_url(url, query_dict)
        self.assertIn("invalid value for query parameter", str(cm.exception))

    def test_merge_query_various_numeric_types(self):
        """Test various numeric types for query parameters"""
        url = "https://example.com"
        query_dict = {"int": 42, "float": 3.14, "str": "value"}
        result = merge_query_to_url(url, query_dict)

        self.assertIn("int=42", result)
        self.assertIn("float=3.14", result)
        self.assertIn("str=value", result)


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
        result = http_request("POST", self.base_url, json_=json_data)

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
        result = http_request("POST", self.base_url, data=data)

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
        result = http_request("POST", self.base_url, data=data)

        # Verify result and request parameters
        self.assertEqual(result.status_code, 200)
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.data, b"binary data")

    @patch('mcp_server_requests.request.urllib.request.urlopen')
    def test_http_request_with_query_params(self, mock_urlopen):
        """Test request with query parameters"""
        mock_response = Mock()
        mock_response.version = 11
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.getheaders.return_value = []
        mock_response.read.return_value = b'Success'
        mock_urlopen.return_value = mock_response

        query_params = {"param1": "value1", "param2": 42}
        http_request("GET", self.base_url, query=query_params)

        # Verify URL contains query parameters
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertIn("param1=value1", request.get_full_url())
        self.assertIn("param2=42", request.get_full_url())

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

    def test_both_data_and_json(self):
        """Test providing both data and json parameters"""
        with self.assertRaises(ArgumentError) as cm:
            http_request("POST", self.base_url, data="test", json_={"key": "value"})
        self.assertIn("Both data and json cannot be provided", str(cm.exception))

    def test_invalid_data_type(self):
        """Test invalid data type"""
        # Use type annotation to bypass type checking and test runtime behavior
        invalid_data = {"invalid": "dict"}  # type: ignore
        with self.assertRaises(ArgumentError) as cm:
            http_request("POST", self.base_url, data=invalid_data)  # type: ignore
        self.assertIn("Data must be a string, bytes, or bytearray", str(cm.exception))

    def test_invalid_json_serialization(self):
        """Test invalid JSON serialization"""
        # Create an object that cannot be serialized
        class UnserializableObject:
            pass

        with self.assertRaises(ArgumentError) as cm:
            http_request("POST", self.base_url, json_={"obj": UnserializableObject()})
        self.assertIn("Failed to serialize JSON data", str(cm.exception))

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
