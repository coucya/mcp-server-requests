from typing import Dict, Any, Optional, Literal, Annotated
import os

from fastmcp import FastMCP, Context

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


async def _validate_file_path(
    file_path: str,
    ctx: Context | None = None,
    use_workspace_root: bool = False,
    allow_external_file_access: bool = False
) -> tuple[str, str]:
    """Validate file path and return (status, normalized_path).

    Returns:
        tuple: (status, normalized_path) where status is "success" or an error message
    """
    if use_workspace_root and ctx:
        roots = await ctx.list_roots()
        if len(roots) == 0:
            return "Error: No workspace root available", ""
        if len(roots) > 1:
            return "Error: Multiple workspace roots found, which is not supported", ""

        if roots[0].uri.scheme != "file":
            return "Error: Workspace root is not a file:// URI", ""
        root = roots[0].uri.path or "/"

        if not os.path.isabs(file_path):
            file_path = os.path.normpath(os.path.join(root, file_path))

        if allow_external_file_access:
            rel = os.path.relpath(file_path, root)
            if rel.startswith(".."):
                return f"Error: Access denied - path '{file_path}' is outside workspace root '{root}'", ""

    if not os.path.isabs(file_path):
        return f"Error: Path must be absolute: {file_path}", ""

    file_path = os.path.abspath(file_path)

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
            '/etc', '/usr', '/bin', '/sbin', '/lib', '/root',
        ])

    for protected in protected_paths:
        if file_path.startswith(protected):
            return f"Error: Do not allow writing to protected paths: {protected}", ""

    return "success", file_path


def create_mcp_server(
    *,
    ua: str | None = None,
    ua_random: bool = False,
    ua_os: str | None = None,
    ua_browser: str | None = None,
    ua_force: bool | None = None,
    use_root: bool | None = None,
    allow_external_file_access: bool | None = None
) -> FastMCP:

    mcp = FastMCP("Requests", log_level="ERROR")

    ua = get_user_agent(ua=ua, ua_random=ua_random, ua_os=ua_os, ua_browser=ua_browser)

    @mcp.tool()
    def fetch(
        url: Annotated[str, "(require) The URL to fetch content from"],
        return_content: Annotated[Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], "(optional, Defaults to \"markdown\") processing format for HTML content"] = "markdown",
    ) -> str:
        """Fetch web page content

        Function/Features:
        - Retrieves web page content from any HTTP/HTTPS URL

        Args:
            url (str): The URL to fetch content from.
            return_content ('raw' | 'basic_clean' | 'strict_clean' | 'markdown', optional):
                Processing format for HTML content. Defaults to "markdown".
                - "raw": Returns unmodified HTML content with full response headers
                - "basic_clean": Removes non-displaying tags (script, style, meta, etc.) while preserving structure
                - "strict_clean": Removes non-displaying tags and most HTML attributes, keeping only essential structure
                - "markdown": Converts HTML content to clean, readable Markdown format

        Examples:
            // Returns content as markdown
            fetch({url: "https://example.com"})

            // Returns raw HTML content
            fetch({url: "https://api.example.com/data", return_content: "raw"})  
        """
        return mcp_http_request("GET", url, return_content=return_content, user_agent=ua, force_user_agnet=ua_force, format_headers=False)

    if use_root:
        @mcp.tool()
        async def fetch_to_file(
            url: Annotated[str, "(require) The URL to fetch content from"],
            file_path: Annotated[str, "(require) File path where the content will be saved"],
            *,
            return_content: Annotated[Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], "(optional, Defaults to \"markdown\") processing format for HTML content"] = "markdown",
            ctx: Context,
        ) -> str:
            """Fetch web content and save it to a file in the workspace

            Function/Features:
            - Retrieves web content from any HTTP/HTTPS URL and saves it to a file
            - Automatic directory creation for nested file paths

            Notes:
            - Automatically creates parent directories if they don't exist
            - Uses UTF-8 encoding for all saved files
            - parameter `file_path` **must** be a relative path (relative to the workspace root)

            Args:
                url (str): The URL to fetch content from.
                file_path (str): File path where the content will be saved.
                return_content ('raw' | 'basic_clean' | 'strict_clean' | 'markdown'], optional): Processing format for HTML content. Defaults to "markdown".
                  - "raw": Saves unmodified HTML content
                  - "basic_clean": Saves HTML with non-displaying tags removed (script, style, etc.) while preserving structure
                  - "strict_clean": Saves HTML with non-displaying tags and most HTML attributes removed, keeping only essential structure
                  - "markdown": Converts HTML content to clean, readable Markdown format before saving

            Examples:
                // Save web page as markdown in workspace
                fetch_to_file({url: "https://example.com", file_path: "content/example.md"})

                // Save raw HTML content
                fetch_to_file({url: "https://api.example.com/data", file_path: "data/response.html", return_content: "raw"})

                // Save cleaned content
                fetch_to_file({url: "https://example.com/docs", file_path: "docs/cleaned.html", return_content: "strict_clean"})
            """
            try:
                # Validate file path with workspace context
                status, validated_path = await _validate_file_path(
                    file_path, ctx,
                    use_workspace_root=True,
                    allow_external_file_access=bool(allow_external_file_access)
                )
                if status != "success":
                    return status

                # Fetch content
                content = mcp_http_request(
                    "GET", url,
                    return_content=return_content,
                    user_agent=ua,
                    force_user_agnet=ua_force,
                    format_status=False,
                    format_headers=False
                )

                try:
                    dir_path = os.path.dirname(validated_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                except OSError as e:
                    return f"Error: Unable to create directory '{os.path.dirname(validated_path)}': {e}"

                try:
                    with open(validated_path, 'w', encoding='utf-8', newline='') as f:
                        f.write(content)
                except OSError as e:
                    return f"Error: Unable to write to file '{validated_path}': {e}"

                return f"File written successfully to: {validated_path}"

            except Exception as e:
                return f"Error: Failed to fetch content or write file: {e}"
    else:
        @mcp.tool()
        async def fetch_to_file(
            url: Annotated[str, "(require) The URL to fetch content from"],
            file_path: Annotated[str, "(require) Absolute file path where the content will be saved. The path must be absolute and will be validated for security"],
            *,
            return_content: Annotated[Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], "(optional, Defaults to \"markdown\") processing format for HTML content"] = "markdown",
            ctx: Context,
        ) -> str:
            """Fetch web content and save it to a file in the workspace

            Function/Features:
            - Retrieves web content from any HTTP/HTTPS URL and saves it to a file
            - Automatic directory creation for nested file paths

            Notes:
            - Automatically creates parent directories if they don't exist
            - Uses UTF-8 encoding for all saved files
            - parameter `file_path` **must** be a absolute path

            Args:
                url (str): The URL to fetch content from.
                file_path (str): File path where the content will be saved.
                return_content ('raw' | 'basic_clean' | 'strict_clean' | 'markdown'], optional): Processing format for HTML content. Defaults to "markdown".
                  - "raw": Saves unmodified HTML content
                  - "basic_clean": Saves HTML with non-displaying tags removed (script, style, etc.) while preserving structure
                  - "strict_clean": Saves HTML with non-displaying tags and most HTML attributes removed, keeping only essential structure
                  - "markdown": Converts HTML content to clean, readable Markdown format before saving

            Examples:
                // Save web page as markdown
                fetch_to_file({url: "https://example.com", file_path: "/home/user/content/example.md"})

                // Save raw HTML content
                fetch_to_file({url: "https://api.example.com/data", file_path: "C:\\data\\response.html", return_content: "raw"})

                // Save cleaned content
                fetch_to_file({url: "https://example.com/docs", file_path: "/tmp/docs/cleaned.html", return_content: "strict_clean"})
            """
            try:
                # Validate file path without workspace context
                status, validated_path = await _validate_file_path(
                    file_path, ctx,
                    use_workspace_root=False,
                    allow_external_file_access=False
                )
                if status != "success":
                    return status

                content = mcp_http_request(
                    "GET", url,
                    return_content=return_content,
                    user_agent=ua,
                    force_user_agnet=ua_force,
                    format_status=False,
                    format_headers=False
                )

                try:
                    dir_path = os.path.dirname(validated_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                except OSError as e:
                    return f"Error: Unable to create directory '{os.path.dirname(validated_path)}': {e}"

                try:
                    with open(validated_path, 'w', encoding='utf-8', newline='') as f:
                        f.write(content)
                except OSError as e:
                    return f"Error: Unable to write to file '{validated_path}': {e}"

                return f"File written successfully to: {validated_path}"
            except Exception as e:
                return f"Error: Failed to fetch content or write file: {e}"

    @mcp.tool()
    def http_request(
        url: Annotated[str, "(require) Target URL for the HTTP request"],
        *,
        method: Annotated[Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], "(optional, Defaults to \"GET\") HTTP method to use for the request"] = "GET",
        query: Annotated[Optional[Dict[str, str | int | float]], "(optional) Query parameters to append to the URL"] = None,
        headers: Annotated[Optional[Dict[str, str]], "(optional) Custom HTTP request headers"] = None,
        data: Annotated[Optional[str], "(optional) Text data to send in the request body. Cannot be used with 'json'"] = None,
        json: Annotated[Optional[Any], "(optional) JSON to send in the request body. Cannot be used with 'data'"] = None,
    ) -> str:
        """Execute an HTTP request with the specified method

        Function/Features:
        - Sends HTTP requests using any standard method (GET, POST, PUT, PATCH, DELETE)
        - Allows custom HTTP headers
        - Returns **complete** HTTP response including status, headers, and body

        Notes:
        - 'data' and 'json' parameters are mutually exclusive - use only one
        - When using 'json', the Content-Type header is automatically set to 'application/json'
        - When using 'data', you may need to set appropriate Content-Type header manually
        - Query parameters are URL-encoded automatically and appended to the URL
        - The response includes the full HTTP response with status line, all headers, and body

        Args:
            url (str): Target URL for the HTTP request.
            method ('GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'], optional): HTTP method to use. Defaults to "GET".
            query ({ [string]: string | number }, optional): Query parameters to append to the URL. Values are automatically converted to strings. Example: {'key1': 'value1', 'key2': 2}, becomes "key1=value1&key2=2" appended to the URL.
            headers ({ [string]: string }, optional): Custom HTTP request headers.
            data (str, optional): Text data to send in the request body. Cannot be used with 'json'.
            json (Any JSON, optional): Data to serialize as JSON and send in the request body. Cannot be used with 'data'.

        Examples:
            // GET request (default method)
            http_request({url: "https://api.example.com/data"})

            // GET request with query parameters
            http_request({url: "https://api.example.com/search", query: {"q": "test", "limit": 10}})

            // POST request with JSON data
            http_request({url: "https://api.example.com/users", method: "POST", json: {"name": "John", "age": 30}})

            // POST request with raw text data
            http_request({url: "https://api.example.com/log", method: "POST", data: "This is a log message"})

            // PUT request
            http_request({url: "https://api.example.com/users/123", method: "PUT", json: {"name": "John Updated", "age": 31}})

            // PATCH request
            http_request({url: "https://api.example.com/users/123", method: "PATCH", json: {"age": 31, "email": "new@example.com"}})

            // DELETE request
            http_request({url: "https://api.example.com/users/123", method: "DELETE"})

            // Request with custom headers
            http_request({url: "https://api.example.com/secure", method: "POST", headers: {"Authorization": "Bearer token"}, json: {"key": "value"}})
        """
        return mcp_http_request(method, url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    return mcp
