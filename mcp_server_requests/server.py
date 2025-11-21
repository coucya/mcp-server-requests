from typing import Dict, Any, Optional, Literal, Annotated
import os

from fastmcp import FastMCP, Context


from .version import __version__
from .request import ArgumentError, RequestError, Response, http_request
from .ua import random_ua
from .utils import clean_html, html_to_markdown


class McpError(Exception):
    def __init__(self, message: str, reason: str | None = None, *args):
        super().__init__(message, reason, *args)
        self.message = message
        self.reason = reason


class ResponseError(McpError):
    def __init__(self, response: Response, message: str, reason: str | None = None, *args):
        super().__init__(message, reason, response, *args)
        self.response = response


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


def format_response_result(
    response: Response,
    *,
    format_status: bool | None = None,
    format_headers: bool | None = None,
    return_content: Literal["raw", "basic_clean", "strict_clean", "markdown"] = "raw",
) -> str:
    http_version = response.version
    status = response.status_code
    reason = response.reason
    headers = response.headers
    content = response.content
    content_type = response.content_type

    if not isinstance(content_type, str):
        content_type = 'application/octet-stream'

    if content_type.startswith("text/") or content_type.startswith("application/json"):
        try:
            if isinstance(content, (bytes, bytearray)):
                content = content.decode('utf-8')
            else:
                content = str(content)
        except UnicodeDecodeError as e:
            err_message = f"response content type is \"{content_type}\", but not utf-8 encoded'"
            raise ResponseError(response, err_message) from e
        except Exception as e:
            err_message = f"response content type is \"{content_type}\", but cannot be converted to a string"
            raise ResponseError(response, err_message) from e
    else:
        err_message = f'response content type is "{content_type}", cannot be converted to a string'
        raise ResponseError(response, err_message)

    if content_type.startswith("text/html"):
        if return_content == "raw":
            pass
        elif return_content == "basic_clean":
            content = clean_html(content, allowed_attrs=True)
        elif return_content == "strict_clean":
            content = clean_html(content, allowed_attrs=("id", "src", "href"))
        elif return_content == "markdown":
            content = html_to_markdown(content)

    strs = []

    if format_status:
        strs.append(f"{http_version} {status} {reason}\r\n")
    if format_headers:
        response_header_str = "\r\n".join(f"{k}: {v}" for k, v in headers)
        strs.append(response_header_str)
    if len(strs) > 0:
        strs.append("\r\n\r\n")
    strs.append(content)

    return "\r\n".join(strs)


def format_error_result(error: Exception):
    if isinstance(error, ArgumentError):
        return f"found an error while checking parameters:\n" \
            f"{error.message}\n"
    elif isinstance(error, RequestError):
        return "encountered an internal error when making a request, with the following error message:\n" \
            f"{error.message}"
    elif isinstance(error, ResponseError):
        resp = error.response
        err_reason = f", but {error.reason}" if error.reason else ", but there was an error when processing the response"
        return f"{resp.version} {resp.status_code} {resp.reason}{err_reason}\r\n" \
            "Content-Type: text/plain\r\n\r\n" \
            "The request sent has successfully received a response, but an error occurred during the processing of the response." \
            " The error message is as follows:\r\n" \
            f"{error.message}"
    else:
        return "An unexpected error occurred" \



def mcp_http_request(
    method: str,
    url: str,
    *,
    query: Optional[dict] = None,
    data: Optional[str | bytes | bytearray] = None,
    json: Optional[dict] = None,
    headers: Optional[dict] = None,
    user_agent: Optional[str] = None,
    force_user_agnet: Optional[bool] = None,
    format_status: bool = True,
    format_headers: bool = True,
    return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'] = "raw",
) -> str:
    hs = {}

    if headers:
        hs.update(headers)

    if force_user_agnet:
        if user_agent:
            hs["User-Agent"] = user_agent
    else:
        if "User-Agent" not in hs and user_agent:
            hs["User-Agent"] = user_agent

    try:
        response = http_request(
            method, url,
            query=query,
            headers=hs,
            data=data,
            json_=json
        )

        return format_response_result(
            response,
            format_status=format_status,
            format_headers=format_headers,
            return_content=return_content
        )
    except Exception as e:
        return format_error_result(e)


async def fetch_content_and_write_to_file(
    url: str,
    file_path: str,
    return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'],
    ctx: Context,
    use_workspace_root: bool = False,
    allow_external_file_access: bool = False,
    user_agent: str = "mcp-server-requests",
    force_user_agent: bool = False
) -> str:
    try:
        # Validate file path
        validated_path = file_path

        if use_workspace_root and ctx:
            roots = await ctx.list_roots()
            if len(roots) == 0:
                return "Error: No workspace root available"
            if len(roots) > 1:
                return "Error: Multiple workspace roots found, which is not supported"

            if roots[0].uri.scheme != "file":
                return "Error: Workspace root is not a file:// URI"
            root = roots[0].uri.path or "/"

            if not os.path.isabs(file_path):
                validated_path = os.path.normpath(os.path.abspath(os.path.join(root, file_path)))

            if allow_external_file_access:
                rel = os.path.relpath(validated_path, root)
                if rel.startswith(".."):
                    return f"Error: Access denied - path '{validated_path}' is outside workspace root '{root}'"

        if not os.path.isabs(validated_path):
            return f"Error: Path must be absolute: {validated_path}"

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
            if validated_path.startswith(protected):
                return f"Error: Do not allow writing to protected paths: {protected}"

        # Fetch content
        content = mcp_http_request(
            "GET", url,
            return_content=return_content,
            user_agent=user_agent,
            force_user_agnet=force_user_agent,
            format_status=False,
            format_headers=False
        )

        # Create parent directories if needed
        try:
            dir_path = os.path.dirname(validated_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            return f"Error: Unable to create directory for path '{validated_path}': {e}"

        # Write content to file
        try:
            with open(validated_path, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
        except OSError as e:
            return f"Error: Unable to write to file '{validated_path}': {e}"

        content_size = len(content)
        return f"Content from '{url}' ({content_size:,} bytes) successfully written to: {validated_path}"

    except Exception as e:
        return f"Error: Failed to fetch content or write file: {e}"


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
            return await fetch_content_and_write_to_file(
                url=url,
                file_path=file_path,
                return_content=return_content,
                ctx=ctx,
                use_workspace_root=True,
                allow_external_file_access=bool(allow_external_file_access),
                user_agent=ua,
                force_user_agent=ua_force if ua_force is not None else False
            )
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
            return await fetch_content_and_write_to_file(
                url=url,
                file_path=file_path,
                return_content=return_content,
                ctx=ctx,
                use_workspace_root=False,
                allow_external_file_access=False,
                user_agent=ua,
                force_user_agent=ua_force if ua_force is not None else False
            )

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
