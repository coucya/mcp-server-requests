from typing import Dict, Any, Optional, Literal
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
    allow_outside_of_workspace: bool = False
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

        if allow_outside_of_workspace:
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
    use_workspace_root: bool | None = None,
    allow_outside_of_workspace: bool | None = None
) -> FastMCP:

    mcp = FastMCP("Requests", log_level="ERROR")

    ua = get_user_agent(ua=ua, ua_random=ua_random, ua_os=ua_os, ua_browser=ua_browser)

    @mcp.tool()
    def fetch(url: str, *, return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'] = "markdown") -> str:
        """Fetch and process web page content.

        This tool retrieves web content and processes it according to the specified format:
        - HTML content is processed based on the return_content parameter
        - Text or JSON content is returned directly
        - Other content types return an error message

        Args:
            url (str): The URL to fetch content from.
            return_content (Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], optional):
                Processing format for HTML content. Defaults to "markdown".
                - "raw": Returns unmodified HTML content
                - "basic_clean": Returns HTML with non-displaying tags removed (script, style, etc.)
                - "strict_clean": Returns HTML with non-displaying tags and most attributes removed
                - "markdown": Converts HTML content to Markdown format

        Returns:
            str: Processed content based on the specified return_content format.
        """
        return mcp_http_request("GET", url, return_content=return_content, user_agent=ua, force_user_agnet=ua_force, format_headers=False)

    if use_workspace_root:
        @mcp.tool()
        async def fetch_to_file(
            url: str,
            file_path: str,
            *,
            return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'] = "markdown",
            ctx: Context,
        ) -> str:
            """Fetch web content and save it to a file in the workspace.

            This tool retrieves web content, processes it according to the specified format,
            and saves it to the provided file path relative to the workspace root.

            Args:
                url (str): The URL to fetch content from.
                file_path (str): File path where the content will be saved. Can be relative
                               to workspace root or absolute. If relative, it will be resolved
                               against the workspace root.
                return_content (Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], optional):
                    Processing format for HTML content. Defaults to "markdown".
                    - "raw": Saves unmodified HTML content
                    - "basic_clean": Saves HTML with non-displaying tags removed (script, style, etc.)
                    - "strict_clean": Saves HTML with non-displaying tags and most attributes removed
                    - "markdown": Converts HTML to Markdown format before saving

            Returns:
                str: Success message with file path, or error message if path validation fails.
            """
            try:
                # Validate file path with workspace context
                status, validated_path = await _validate_file_path(
                    file_path, ctx,
                    use_workspace_root=True,
                    allow_outside_of_workspace=not bool(allow_outside_of_workspace)
                )
                if status != "success":
                    return status

                # Fetch content
                content = mcp_http_request(
                    "GET", url,
                    return_content=return_content,
                    user_agent=ua,
                    force_user_agnet=ua_force,
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
            url: str,
            file_path: str,
            *,
            return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'] = "markdown",
            ctx: Context,
        ) -> str:
            """Fetch web content and save it to a file.

            This tool retrieves web content, processes it according to the specified format,
            and saves it to the provided absolute file path.

            Args:
                url (str): The URL to fetch content from.
                file_path (str): Absolute file path where the content will be saved.
                               The path must be absolute and will be validated for security.
                return_content (Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], optional):
                    Processing format for HTML content. Defaults to "markdown".
                    - "raw": Saves unmodified HTML content
                    - "basic_clean": Saves HTML with non-displaying tags removed (script, style, etc.)
                    - "strict_clean": Saves HTML with non-displaying tags and most attributes removed
                    - "markdown": Converts HTML to Markdown format before saving

            Returns:
                str: Success message with file path, or error message if path validation fails.
            """
            try:
                # Validate file path without workspace context
                status, validated_path = await _validate_file_path(
                    file_path, ctx,
                    use_workspace_root=False,
                    allow_outside_of_workspace=False
                )
                if status != "success":
                    return status

                content = mcp_http_request(
                    "GET", url,
                    return_content=return_content,
                    user_agent=ua,
                    force_user_agnet=ua_force,
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
    def http_get(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """Execute an HTTP GET request.

        Sends a GET request to the specified URL with optional query parameters and headers.

        Args:
            url (str): Target URL for the GET request.
            query (Optional[Dict[str, str | int | float]], optional): Query parameters to append to the URL.
                Values are automatically converted to strings. Example: {'key1': 'value1', 'key2': 2}
                becomes "key1=value1&key2=2" appended to the URL.
            headers (Optional[Dict[str, str]], optional): Custom HTTP request headers.

        Returns:
            str: Complete HTTP response including status line, headers, and body.
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

        Sends a POST request to the specified URL with optional parameters and request body.

        Args:
            url (str): Target URL for the POST request.
            query (Optional[Dict[str, str | int | float]], optional): Query parameters to append to the URL.
                Values are automatically converted to strings. Example: {'key1': 'value1', 'key2': 2}
                becomes "key1=value1&key2=2" appended to the URL.
            headers (Optional[Dict[str, str]], optional): Custom HTTP request headers.
            data (Optional[str], optional): Text data to send in the request body. Cannot be used with 'json'.
            json (Optional[Any], optional): Data to serialize as JSON and send in the request body. Cannot be used with 'data'.

        Returns:
            str: Complete HTTP response including status line, headers, and body.
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

        Sends a PUT request to the specified URL with optional parameters and request body.

        Args:
            url (str): Target URL for the PUT request.
            query (Optional[Dict[str, str | int | float]], optional): Query parameters to append to the URL.
                Values are automatically converted to strings. Example: {'key1': 'value1', 'key2': 2}
                becomes "key1=value1&key2=2" appended to the URL.
            headers (Optional[Dict[str, str]], optional): Custom HTTP request headers.
            data (Optional[str], optional): Text data to send in the request body. Cannot be used with 'json'.
            json (Optional[Any], optional): Data to serialize as JSON and send in the request body. Cannot be used with 'data'.

        Returns:
            str: Complete HTTP response including status line, headers, and body.
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

        Sends a PATCH request to the specified URL with optional parameters and request body.

        Args:
            url (str): Target URL for the PATCH request.
            query (Optional[Dict[str, str | int | float]], optional): Query parameters to append to the URL.
                Values are automatically converted to strings. Example: {'key1': 'value1', 'key2': 2}
                becomes "key1=value1&key2=2" appended to the URL.
            headers (Optional[Dict[str, str]], optional): Custom HTTP request headers.
            data (Optional[str], optional): Text data to send in the request body. Cannot be used with 'json'.
            json (Optional[Any], optional): Data to serialize as JSON and send in the request body. Cannot be used with 'data'.

        Returns:
            str: Complete HTTP response including status line, headers, and body.
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

        Sends a DELETE request to the specified URL with optional parameters and request body.

        Args:
            url (str): Target URL for the DELETE request.
            query (Optional[Dict[str, str | int | float]], optional): Query parameters to append to the URL.
                Values are automatically converted to strings. Example: {'key1': 'value1', 'key2': 2}
                becomes "key1=value1&key2=2" appended to the URL.
            headers (Optional[Dict[str, str]], optional): Custom HTTP request headers.
            data (Optional[str], optional): Text data to send in the request body. Cannot be used with 'json'.
            json (Optional[Any], optional): Data to serialize as JSON and send in the request body. Cannot be used with 'data'.

        Returns:
            str: Complete HTTP response including status line, headers, and body.
        """
        return mcp_http_request("DELETE", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    return mcp
