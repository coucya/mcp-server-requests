from typing import Dict, Any, Optional, Literal
import os

from mcp.server.fastmcp import FastMCP

from .version import __version__
from .request import mcp_http_request
from .ua import random_ua


def get_user_agent(
    *,
    ua: str | None = None,
    ua_random: bool = False,
    ua_os: str | None = None,
    ua_browser: str | None = None,
) -> str:
    if not ua and ua_random:
        ua = random_ua(browser=ua_browser, os=ua_os)
        if not ua:
            raise RuntimeError(f"can't find suitable user-agent, os or browser: {ua_os}, {ua_browser}, try a different combination.")

    if not ua:
        ua = f"Mozilla/5.0 (compatible; mcp-server-requests/{__version__})"

    return ua


def create_mcp_server(
    *,
    ua: str | None = None,
    ua_random: bool = False,
    ua_os: str | None = None,
    ua_browser: str | None = None,
    ua_force: bool | None = None,
) -> FastMCP:

    mcp = FastMCP("Requests", log_level="ERROR")

    ua = get_user_agent(ua=ua, ua_random=ua_random, ua_os=ua_os, ua_browser=ua_browser)

    @mcp.tool()
    def fetch(url: str, *, return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'] = "markdown") -> str:
        """Fetch web page content.
        - If it's HTML, return appropriate content based on the return_content parameter.
        - If it's not HTML but is Text or JSON content, return its content directly.
        - If it's other types of content, return an error message.

        Args:
            url (str): The URL of the web page to fetch.
            return_content ("raw" | "basic_clean" | "strict_clean" | "markdown", optional): Defaults to "markdown". Controls how HTML content is returned:
                - If "raw", return original HTML content.
                - If "basic_clean", return filtered HTML content, removing all non-displaying tags like script, style, etc.
                - If "strict_clean", return filtered HTML content, removing all non-displaying tags like script, style, etc., and delete most useless HTML attributes.
                - If "markdown", HTML is converted to Markdown before returning.

        Returns:
            - If return_content is "raw", returns original HTML content.
            - If return_content is "basic_clean", returns filtered HTML content with non-displaying tags removed.
            - If return_content is "strict_clean", returns filtered HTML content with non-displaying tags and most attributes removed.
            - If return_content is "markdown", returns content converted to Markdown.
        """
        return mcp_http_request("GET", url, return_content=return_content, user_agent=ua, force_user_agnet=ua_force, format_headers=False)

    @mcp.tool()
    def fetch_to_file(
        url: str,
        file_path: str,
        *,
        return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'] = "markdown"
    ) -> str:
        """Fetch web page content and save it to a file.
        - If it's HTML, save appropriate content based on the return_content parameter.
        - If it's not HTML but is Text or JSON content, save its content directly.
        - If it's other types of content, return an error message.

        Args:
            url (str): The URL of the web page to fetch.
            file_path (str): The absolute file path where the content should be saved.
            return_content ("raw" | "basic_clean" | "strict_clean" | "markdown", optional): Defaults to "markdown". Controls how HTML content is processed:
                - If "raw", save original HTML content.
                - If "basic_clean", save filtered HTML content, removing all non-displaying tags like script, style, etc.
                - If "strict_clean", save filtered HTML content, removing all non-displaying tags like script, style, etc., and delete most useless HTML attributes.
                - If "markdown", HTML is converted to Markdown before saving.

        Returns:
            - File save path on success
            - Error message if the path is unsafe
        """
        # Set protected paths based on operating system
        protected_paths = []
        if os.name == 'nt':  # Windows
            protected_paths.extend([
                os.path.join('C:', 'Windows'),
                os.path.join('C:', 'Program Files'),
                os.path.join('C:', 'Program Files (x86)'),
            ])
        else:  # Linux/Mac
            protected_paths.extend([
                '/etc',
                '/usr',
                '/bin',
                '/sbin',
                '/lib',
                '/root',
            ])

        if not os.path.isabs(file_path):
            return f"Error: Path must be absolute: {file_path}"

        # Check path security
        file_path = os.path.abspath(file_path)
        for protected in protected_paths:
            if file_path.startswith(protected):
                return f"Error: Do not allow writing to protected paths: {protected}"

        # Get content
        content = mcp_http_request("GET", url, return_content=return_content,
                                   user_agent=ua, force_user_agnet=ua_force,
                                   format_headers=False)

        # Write to file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"File written successfully to: {file_path}"

    @mcp.tool()
    def http_get(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """Execute an HTTP GET request.

        Args:
            url (str): The target URL for the request.
            query (Dict[str, str | int | float], optional): Optional query parameter key-value pairs. Parameter values are automatically converted to strings and appended to the URL.
                For example: {'key1': 'value1', 'key2': 2} is converted to key1=value1&key2=2 and appended to the URL.
            headers (Dict[str, str], optional): Optional custom HTTP request headers.

        Returns:
            str: Standard HTTP response format string containing status line, response headers, and response body.
        """
        return mcp_http_request("GET", url, query=query, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    @mcp.tool()
    def http_post(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """Execute an HTTP POST request.

        Args:
            url (str): The target URL for the request.
            query (Dict[str, str | int | float], optional): Optional query parameter key-value pairs. Parameter values are automatically converted to strings and appended to the URL.
                For example: {'key1': 'value1', 'key2': 2} is converted to key1=value1&key2=2 and appended to the URL.
            headers (Dict[str, str], optional): Optional custom HTTP request headers.
            data (str, optional): Optional HTTP request body data, must be text. The data and json parameters cannot be used simultaneously.
            json (Any, optional): Optional HTTP request body data as JSON, which will be automatically serialized to a JSON string. The data and json parameters cannot be used simultaneously.

        Returns:
            str: Standard HTTP response format string containing status line, response headers, and response body.
        """
        return mcp_http_request("POST", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    @mcp.tool()
    def http_put(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """Execute an HTTP PUT request.

        Args:
            url (str): The target URL for the request.
            query (Dict[str, str | int | float], optional): Query parameter key-value pairs. Parameter values are automatically converted to strings and appended to the URL.
                For example: {'key1': 'value1', 'key2': 2} is converted to key1=value1&key2=2 and appended to the URL.
            headers (Dict[str, str], optional): Optional custom HTTP request headers.
            data (str, optional): Optional HTTP request body data, must be text. The data and json parameters cannot be used simultaneously.
            json (Any, optional): Optional HTTP request body data as JSON, which will be automatically serialized to a JSON string. The data and json parameters cannot be used simultaneously.

        Returns:
            str: Standard HTTP response format string containing status line, response headers, and response body.
        """
        return mcp_http_request("PUT", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    @mcp.tool()
    def http_patch(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """Execute an HTTP PATCH request.

        Args:
            url (str): The target URL for the request.
            query (Dict[str, str | int | float], optional): Query parameter key-value pairs. Parameter values are automatically converted to strings and appended to the URL.
                For example: {'key1': 'value1', 'key2': 2} is converted to key1=value1&key2=2 and appended to the URL.
            headers (Dict[str, str], optional): Optional custom HTTP request headers.
            data (str, optional): Optional HTTP request body data, must be text. The data and json parameters cannot be used simultaneously.
            json (Any, optional): Optional HTTP request body data as JSON, which will be automatically serialized to a JSON string. The data and json parameters cannot be used simultaneously.

        Returns:
            str: Standard HTTP response format string containing status line, response headers, and response body.
        """
        return mcp_http_request("PATCH", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    @mcp.tool()
    def http_delete(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """Execute an HTTP DELETE request.

        Args:
            url (str): The target URL for the request.
            query (Dict[str, str | int | float], optional): Query parameter key-value pairs. Parameter values are automatically converted to strings and appended to the URL.
                For example: {'key1': 'value1', 'key2': 2} is converted to key1=value1&key2=2 and appended to the URL.
            headers (Dict[str, str], optional): Optional custom HTTP request headers.
            data (str, optional): Optional HTTP request body data, must be text. The data and json parameters cannot be used simultaneously.
            json (Any, optional): Optional HTTP request body data as JSON, which will be automatically serialized to a JSON string. The data and json parameters cannot be used simultaneously.

        Returns:
            str: Standard HTTP response format string containing status line, response headers, and response body.
        """
        return mcp_http_request("DELETE", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    return mcp