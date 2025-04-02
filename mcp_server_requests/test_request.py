import unittest
from unittest.mock import patch, MagicMock
from mcp_server_requests.request import (
    Response,
    McpError, ArgumentError, RequestError, ResponseError,
    merge_query_to_url,
    http_request,
    format_response_result, format_error_result,
    mcp_http_request
)
import urllib.error
import http.client

class TestResponse(unittest.TestCase):
    def test_response_initialization(self):
        headers = [('Content-Type', 'text/plain'), ('X-Test', '123')]
        response = Response(
            url="http://example.com",
            version="HTTP/1.1",
            status_code=200,
            reason="OK",
            headers=headers,
            content=b"test content"
        )
        
        self.assertEqual(response.url, "http://example.com")
        self.assertEqual(response.version, "HTTP/1.1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, "OK")
        self.assertEqual(response.headers, headers)
        self.assertEqual(response.content, b"test content")
        self.assertEqual(response.content_type, "text/plain")

class TestExceptions(unittest.TestCase):
    def test_mcp_error(self):
        error = McpError("test message", "test reason")
        self.assertEqual(error.message, "test message")
        self.assertEqual(error.reason, "test reason")
    
    def test_argument_error(self):
        error = ArgumentError("invalid argument")
        self.assertIsInstance(error, McpError)
    
    def test_request_error(self):
        error = RequestError("request failed")
        self.assertIsInstance(error, McpError)
    
    def test_response_error(self):
        response = Response("http://test.com", "HTTP/1.1", 200, "OK", [], b"")
        error = ResponseError(response, "response error")
        self.assertIsInstance(error, McpError)
        self.assertEqual(error.response, response)

class TestMergeQueryToUrl(unittest.TestCase):
    def test_merge_query_simple(self):
        url = "http://example.com/path"
        query = {"param1": "value1", "param2": 2}
        result = merge_query_to_url(url, query)
        self.assertIn("param1=value1", result)
        self.assertIn("param2=2", result)
        self.assertTrue(result.startswith("http://example.com/path?"))
    
    def test_merge_query_existing(self):
        url = "http://example.com/path?existing=1"
        query = {"new": "value"}
        result = merge_query_to_url(url, query)
        self.assertIn("existing=1", result)
        self.assertIn("new=value", result)
    
    def test_merge_query_invalid_value(self):
        url = "http://example.com"
        query = {"invalid": None}
        with self.assertRaises(ArgumentError):
            merge_query_to_url(url, query)

class TestHttpRequest(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_http_request_success(self, mock_urlopen):
        # Setup mock response
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.getheaders.return_value = [('Content-Type', 'text/plain')]
        mock_resp.read.return_value = b"response content"
        mock_urlopen.return_value = mock_resp
        
        # Test request
        response = http_request("GET", "http://example.com")
        
        # Assertions
        self.assertEqual(response.url, "http://example.com")
        self.assertEqual(response.version, "HTTP/1.1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.reason, "OK")
        self.assertEqual(response.headers, [('Content-Type', 'text/plain')])
        self.assertEqual(response.content, b"response content")
    
    @patch('urllib.request.urlopen')
    def test_http_request_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("test error")
        
        with self.assertRaises(RequestError):
            http_request("GET", "invalid_url")
    
    def test_http_request_invalid_method(self):
        with self.assertRaises(ArgumentError):
            http_request("INVALID", "http://example.com")
    
    def test_http_request_conflict_data_json(self):
        with self.assertRaises(ArgumentError):
            http_request("POST", "http://example.com", data="data", json_={"key": "value"})

class TestFormatFunctions(unittest.TestCase):
    def test_format_response_result_full(self):
        response = Response(
            url="http://example.com",
            version="HTTP/1.1",
            status_code=200,
            reason="OK",
            headers=[('Content-Type', 'text/plain')],
            content=b"test content"
        )
        result = format_response_result(response, format_headers=True, return_content="full")
        self.assertIn("HTTP/1.1 200 OK", result)
        self.assertIn("Content-Type: text/plain", result)
        self.assertIn("test content", result)
    
    def test_format_error_result_argument_error(self):
        error = ArgumentError("invalid argument")
        result = format_error_result(error)
        self.assertIn("500 MCP Service Internal Error", result)
        self.assertIn("invalid argument", result)

class TestMcpHttpRequest(unittest.TestCase):
    @patch('mcp_server_requests.request.http_request')
    def test_mcp_http_request_success(self, mock_http_request):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.url = "http://example.com"
        mock_response.version = "HTTP/1.1"
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.headers = [('Content-Type', 'text/plain')]
        mock_response.content = b"test content"
        mock_response.content_type = "text/plain"
        mock_http_request.return_value = mock_response
        
        # Test request
        result = mcp_http_request("GET", "http://example.com")
        
        # Assertions
        self.assertIn("HTTP/1.1 200 OK", result)
        self.assertIn("test content", result)
    
    @patch('mcp_server_requests.request.http_request')
    def test_mcp_http_request_error(self, mock_http_request):
        mock_http_request.side_effect = ArgumentError("test error")
        
        result = mcp_http_request("GET", "invalid_url")
        self.assertIn("500 MCP Service Internal Error", result)
        self.assertIn("test error", result)

if __name__ == '__main__':
    unittest.main()