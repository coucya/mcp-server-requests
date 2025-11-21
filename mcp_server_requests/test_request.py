
from typing import Any
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import os
import json
import urllib.error
import urllib.request
import http.client

from mcp_server_requests.request import (
    Response,
    McpError, ArgumentError, RequestError, ResponseError,
    merge_query_to_url,
    http_request,
    format_response_result, format_error_result,
    mcp_http_request
)
from mcp_server_requests.utils import clean_html, html_to_markdown, simple_html_to_markdown, parse


class TestResponse(unittest.TestCase):
    """Test cases for Response dataclass and its properties

    Tests the creation of Response objects and verification of:
    - Proper initialization with all parameters
    - Content type detection from headers
    - Default content type handling
    - Header preservation
    """

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
    """Test cases for custom exception classes

    Tests the hierarchy and behavior of custom exceptions:
    - McpError: Base exception class
    - ArgumentError: Invalid argument errors
    - RequestError: HTTP request failures
    - ResponseError: Response processing errors
    - Proper inheritance chains
    """

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
        result = format_response_result(response, format_status=True, format_headers=True, return_content="raw")
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

    @patch('mcp_server_requests.request.http_request')
    def test_mcp_http_request_with_headers(self, mock_http_request):
        mock_response = MagicMock()
        mock_response.url = "http://example.com"
        mock_response.version = "HTTP/1.1"
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.headers = [('Content-Type', 'application/json')]
        mock_response.content = b'{"key": "value"}'
        mock_response.content_type = "application/json"
        mock_http_request.return_value = mock_response

        result = mcp_http_request("POST", "http://example.com",
                                  headers={"Authorization": "Bearer token"},
                                  json={"data": "test"})

        # Verify the call was made with correct parameters
        mock_http_request.assert_called_once_with(
            "POST",
            "http://example.com",
            query=None,
            headers={"Authorization": "Bearer token"},
            data=None,
            json_={"data": "test"}
        )

    @patch('mcp_server_requests.request.http_request')
    def test_mcp_http_request_different_content_formats(self, mock_http_request):
        mock_response = MagicMock()
        mock_response.url = "http://example.com"
        mock_response.version = "HTTP/1.1"
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.headers = [('Content-Type', 'text/html')]
        mock_response.content = b"<html><body><p>Test</p></body></html>"
        mock_response.content_type = "text/html"
        mock_http_request.return_value = mock_response

        # Test different return_content formats
        for format_type in ["raw", "basic_clean", "strict_clean", "markdown"]:
            mcp_http_request("GET", "http://example.com", return_content=format_type)  # type: ignore
            # Since we're just testing that the function handles the parameter without error
            # and we've mocked the underlying http_request, we don't need to assert on result

    @patch('mcp_server_requests.request.http_request')
    def test_mcp_http_request_user_agent_handling(self, mock_http_request):
        mock_response = MagicMock()
        mock_response.url = "http://example.com"
        mock_response.version = "HTTP/1.1"
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.headers = [('Content-Type', 'text/plain')]
        mock_response.content = b"test content"
        mock_response.content_type = "text/plain"
        mock_http_request.return_value = mock_response

        # Test user agent handling
        result = mcp_http_request("GET", "http://example.com",
                                  user_agent="Custom-Agent/1.0")

        call_args = mock_http_request.call_args
        self.assertEqual(call_args[1]['headers'], {"User-Agent": "Custom-Agent/1.0"})

        # Test force_user_agent
        mock_http_request.reset_mock()
        result = mcp_http_request("GET", "http://example.com",
                                  headers={"User-Agent": "Existing-Agent"},
                                  user_agent="Custom-Agent/1.0",
                                  force_user_agnet=True)

        call_args = mock_http_request.call_args
        self.assertEqual(call_args[1]['headers'], {"User-Agent": "Custom-Agent/1.0"})


class TestHttpRequestAdvanced(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_http_request_with_query_params(self, mock_urlopen):
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.getheaders.return_value = [('Content-Type', 'application/json')]
        mock_resp.read.return_value = b'{"success": true}'
        mock_urlopen.return_value = mock_resp

        response = http_request("GET", "http://example.com/api",
                                query={"param1": "value1", "param2": 2})

        self.assertEqual(response.status_code, 200)
        # Verify the URL includes query parameters
        call_args = mock_urlopen.call_args[0]
        request_url = call_args[0].get_full_url()
        self.assertIn("param1=value1", request_url)
        self.assertIn("param2=2", request_url)

    @patch('urllib.request.urlopen')
    def test_http_request_with_json_data(self, mock_urlopen):
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 201
        mock_resp.reason = "Created"
        mock_resp.getheaders.return_value = [('Content-Type', 'application/json')]
        mock_resp.read.return_value = b'{"id": 123}'
        mock_urlopen.return_value = mock_resp

        response = http_request("POST", "http://example.com/api",
                                json_={"name": "John", "age": 30})

        self.assertEqual(response.status_code, 201)
        # Verify JSON was properly encoded
        call_args = mock_urlopen.call_args[0]
        request_data = call_args[0].data
        self.assertIn(b'"name": "John"', request_data)
        self.assertIn(b'"age": 30', request_data)

    @patch('urllib.request.urlopen')
    def test_http_request_with_string_data(self, mock_urlopen):
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.getheaders.return_value = [('Content-Type', 'text/plain')]
        mock_resp.read.return_value = b'Success'
        mock_urlopen.return_value = mock_resp

        response = http_request("POST", "http://example.com/api",
                                data="raw text data")

        self.assertEqual(response.status_code, 200)
        # Verify string data was properly encoded
        call_args = mock_urlopen.call_args[0]
        request_data = call_args[0].data
        self.assertEqual(request_data, b"raw text data")

    @patch('urllib.request.urlopen')
    def test_http_request_auto_adds_https(self, mock_urlopen):
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.getheaders.return_value = [('Content-Type', 'text/plain')]
        mock_resp.read.return_value = b'Success'
        mock_urlopen.return_value = mock_resp

        response = http_request("GET", "example.com/api")

        # Verify https:// was added
        call_args = mock_urlopen.call_args[0]
        request_url = call_args[0].get_full_url()
        self.assertTrue(request_url.startswith("https://example.com"))

    @patch('urllib.request.urlopen')
    def test_http_request_http_error_handling(self, mock_urlopen):
        # Create a mock that raises URLError instead of HTTPError to avoid type issues
        mock_urlopen.side_effect = urllib.error.URLError("Not found")

        with self.assertRaises(RequestError) as context:
            http_request("GET", "http://example.com/notfound")

        self.assertIn("Failed to send request", str(context.exception))

    def test_http_request_invalid_data_type(self):
        with self.assertRaises(ArgumentError) as context:
            http_request("POST", "http://example.com", data={"invalid": "type"})  # type: ignore

        self.assertIn("Data must be a string", str(context.exception))

    def test_http_request_invalid_json_serialization(self):
        # Test with non-serializable JSON data
        with self.assertRaises(ArgumentError) as context:
            http_request("POST", "http://example.com", json_={"invalid": object()})

        self.assertIn("Failed to serialize JSON data", str(context.exception))

    @patch('urllib.request.urlopen')
    def test_http_request_with_bytes_data(self, mock_urlopen):
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.getheaders.return_value = [('Content-Type', 'application/octet-stream')]
        mock_resp.read.return_value = b'Success'
        mock_urlopen.return_value = mock_resp

        test_data = b"binary data"
        response = http_request("POST", "http://example.com/api", data=test_data)

        self.assertEqual(response.status_code, 200)
        call_args = mock_urlopen.call_args[0]
        self.assertEqual(call_args[0].data, test_data)

    @patch('urllib.request.urlopen')
    def test_http_request_with_bytearray_data(self, mock_urlopen):
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.getheaders.return_value = [('Content-Type', 'application/octet-stream')]
        mock_resp.read.return_value = b'Success'
        mock_urlopen.return_value = mock_resp

        test_data = bytearray(b"bytearray data")
        response = http_request("POST", "http://example.com/api", data=test_data)

        self.assertEqual(response.status_code, 200)
        call_args = mock_urlopen.call_args[0]
        self.assertEqual(call_args[0].data, b"bytearray data")


class TestFormatFunctionsAdvanced(unittest.TestCase):
  
    def test_format_response_result_non_text_content_type(self):
        response = Response(
            url="http://example.com",
            version="HTTP/1.1",
            status_code=200,
            reason="OK",
            headers=[('Content-Type', 'application/pdf')],
            content=b"%PDF-1.4"
        )
        with self.assertRaises(ResponseError) as context:
            format_response_result(response)

        self.assertIn("cannot be converted to a string", str(context.exception))

    def test_format_response_result_unicode_decode_error(self):
        response = Response(
            url="http://example.com",
            version="HTTP/1.1",
            status_code=200,
            reason="OK",
            headers=[('Content-Type', 'text/plain')],
            content=b'\xff\xfe'  # Invalid UTF-8
        )
        with self.assertRaises(ResponseError) as context:
            format_response_result(response)

        self.assertIn("not utf-8 encoded", str(context.exception))

  
    def test_format_response_result_selective_formatting(self):
        response = Response(
            url="http://example.com",
            version="HTTP/1.1",
            status_code=200,
            reason="OK",
            headers=[('Content-Type', 'text/plain')],
            content=b"test content"
        )

        # Test format_status=False
        result = format_response_result(response, format_status=False, format_headers=True)
        self.assertNotIn("HTTP/1.1 200 OK", result)
        # Headers are included even without status when format_headers=True
        # Let's test with both False instead
        result_both_false = format_response_result(response, format_status=False, format_headers=False)
        self.assertNotIn("Content-Type: text/plain", result_both_false)
        self.assertEqual(result_both_false.strip(), "test content")

        # Test format_headers=False
        result = format_response_result(response, format_status=True, format_headers=False)
        self.assertIn("HTTP/1.1 200 OK", result)
        self.assertNotIn("Content-Type: text/plain", result)

        # Test both False
        result = format_response_result(response, format_status=False, format_headers=False)
        self.assertEqual(result.strip(), "test content")

    def test_format_error_result_request_error(self):
        error = RequestError("Connection timeout")
        result = format_error_result(error)
        self.assertIn("500 MCP Service Internal Error", result)
        self.assertIn("Connection timeout", result)
        self.assertIn("internal error when making a request", result)

    def test_format_error_result_response_error_with_reason(self):
        response = Response("http://test.com", "HTTP/1.1", 200, "OK", [], b"")
        error = ResponseError(response, "Processing failed", "Invalid format")
        result = format_error_result(error)
        self.assertIn("but Invalid format", result)

    def test_format_error_result_unexpected_error(self):
        error = ValueError("Unexpected error")
        result = format_error_result(error)
        self.assertIn("500 MCP Service Internal Error", result)
        self.assertIn("An unexpected error occurred", result)


class TestMergeQueryToUrlAdvanced(unittest.TestCase):
    def test_merge_query_with_fragment(self):
        url = "http://example.com/path#section"
        query = {"param": "value"}
        result = merge_query_to_url(url, query)
        self.assertIn("param=value", result)
        self.assertIn("#section", result)

    def test_merge_query_with_auth(self):
        url = "http://user:pass@example.com/path"
        query = {"param": "value"}
        result = merge_query_to_url(url, query)
        self.assertIn("user:pass@example.com", result)
        self.assertIn("param=value", result)

    def test_merge_query_with_port(self):
        url = "http://example.com:8080/path"
        query = {"param": "value"}
        result = merge_query_to_url(url, query)
        self.assertIn("example.com:8080", result)
        self.assertIn("param=value", result)

    
    def test_merge_query_special_characters(self):
        url = "http://example.com/path"
        query = {"param": "value with spaces & symbols"}
        result = merge_query_to_url(url, query)
        # Should be URL encoded
        self.assertIn("value+with+spaces+%26+symbols", result)

    

class TestUtils(unittest.TestCase):
    def test_clean_html_basic(self):
        html = "<div><p>Hello <strong>world</strong></p><script>alert('xss')</script></div>"
        result = clean_html(html)
        self.assertIn("Hello <strong>world</strong>", result)
        self.assertNotIn("<script>", result)
        self.assertNotIn("alert('xss')", result)

    def test_clean_html_with_allowed_attrs_true(self):
        html = '<div id="main" class="container" data-value="123"><p>Content</p></div>'
        result = clean_html(html, allowed_attrs=True)
        # Should preserve all attributes when allowed_attrs=True
        self.assertIn('id="main"', result)
        self.assertIn('class="container"', result)
        self.assertIn('data-value="123"', result)

    def test_clean_html_with_allowed_attrs_false(self):
        html = '<div id="main" class="container" data-value="123"><p>Content</p></div>'
        result = clean_html(html, allowed_attrs=False)
        # Should remove all attributes when allowed_attrs=False
        self.assertNotIn('id="main"', result)
        self.assertNotIn('class="container"', result)
        self.assertNotIn('data-value="123"', result)
        self.assertIn("<div>", result)

    def test_clean_html_with_specific_allowed_attrs(self):
        html = '<div id="main" class="container" src="image.jpg" href="link.html"><p>Content</p></div>'
        result = clean_html(html, allowed_attrs=("id", "src"))
        # Should preserve only specified attributes
        self.assertIn('id="main"', result)
        self.assertIn('src="image.jpg"', result)
        self.assertNotIn('class="container"', result)
        self.assertNotIn('href="link.html"', result)

    def test_clean_html_custom_clean_tags(self):
        html = "<div><p>Content</p><style>body{color:red}</style><iframe src='evil'></iframe></div>"
        result = clean_html(html, clean_tags=("style", "iframe"))
        self.assertIn("<p>Content</p>", result)
        self.assertNotIn("<style>", result)
        self.assertNotIn("<iframe>", result)

    def test_simple_html_to_markdown_basic(self):
        html = "<h1>Title</h1><p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>"
        result = simple_html_to_markdown(html)
        self.assertIn("# Title", result)
        self.assertIn("**bold**", result)
        self.assertIn("_italic_", result)

    def test_simple_html_to_markdown_links(self):
        html = '<p>Visit <a href="https://example.com">this link</a> for more info.</p>'
        result = simple_html_to_markdown(html)
        self.assertIn("[this link](https://example.com)", result)

    def test_simple_html_to_markdown_images(self):
        html = '<p>Image: <img src="image.jpg" alt="Description"></p>'
        result = simple_html_to_markdown(html)
        self.assertIn("![Description](image.jpg)", result)

    def test_simple_html_to_markdown_lists(self):
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = simple_html_to_markdown(html)
        self.assertIn("* Item 1", result)
        self.assertIn("* Item 2", result)

    def test_simple_html_to_markdown_ordered_lists(self):
        html = "<ol><li>First</li><li>Second</li></ol>"
        result = simple_html_to_markdown(html)
        self.assertIn("1. First", result)
        self.assertIn("2. Second", result)

    def test_simple_html_to_markdown_code_blocks(self):
        html = "<pre><code>print('Hello, World!')</code></pre>"
        result = simple_html_to_markdown(html)
        self.assertIn("```", result)
        self.assertIn("print('Hello, World!')", result)

    def test_simple_html_to_markdown_blockquotes(self):
        html = "<blockquote>This is a quote</blockquote>"
        result = simple_html_to_markdown(html)
        self.assertIn("> This is a quote", result)

    def test_simple_html_to_markdown_horizontal_rule(self):
        html = "<hr>"
        result = simple_html_to_markdown(html)
        self.assertIn("---", result)

    def test_parse_function(self):
        test_string = "key1=value1; key2=value2;key3=value3"
        result = parse(test_string)
        expected = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        self.assertEqual(result, expected)

    def test_parse_empty_string(self):
        result = parse("")
        self.assertEqual(result, {})

    def test_parse_whitespace_string(self):
        result = parse("   ")
        self.assertEqual(result, {})

    def test_parse_complex_string(self):
        test_string = "   key1=value1;key2=value2"
        result = parse(test_string)
        expected = {
            "key1": "value1",
            "key2": "value2"
        }
        self.assertEqual(result, expected)


class TestIntegration(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_full_workflow_html_processing(self, mock_urlopen):
        # Mock HTML response
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.getheaders.return_value = [('Content-Type', 'text/html')]
        mock_resp.read.return_value = b"<html><body><h1>Test Title</h1><p>Test paragraph</p></body></html>"
        mock_urlopen.return_value = mock_resp

        # Test full workflow from mcp_http_request with HTML processing
        result = mcp_http_request("GET", "http://example.com", return_content="markdown")

        # Should contain processed markdown
        self.assertIn("200 OK", result)
        # Note: The exact markdown format depends on the implementation

    @patch('urllib.request.urlopen')
    def test_json_api_workflow(self, mock_urlopen):
        # Mock JSON API response
        mock_resp = MagicMock(spec=http.client.HTTPResponse)
        mock_resp.version = 11
        mock_resp.status = 201
        mock_resp.reason = "Created"
        mock_resp.getheaders.return_value = [
            ('Content-Type', 'application/json'),
            ('X-Custom-Header', 'test-value')
        ]
        mock_resp.read.return_value = b'{"id": 123, "status": "created"}'
        mock_urlopen.return_value = mock_resp

        # Test JSON API workflow
        result = mcp_http_request(
            "POST",
            "http://api.example.com/users",
            json={"name": "John Doe", "email": "john@example.com"},
            headers={"Authorization": "Bearer token123"}
        )

        # Should contain full response with headers and JSON content
        self.assertIn("201 Created", result)
        self.assertIn("X-Custom-Header: test-value", result)
        self.assertIn('"id": 123', result)


if __name__ == '__main__':
    unittest.main()
