from typing import Dict, Any, Optional, Literal, Annotated
import os

from fastmcp import FastMCP


from .version import __version__
from .request import ArgumentError, RequestError, Response, http_request
from .ua import random_ua
from .utils import clean_html, html_to_markdown


class FormatResponseError(Exception):
    def __init__(self, response: Response, message: str, *args):
        super().__init__(message, response, *args)
        self.response = response
        self.message = message


class WritePathError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _protected_paths() -> tuple[str, ...]:
    """Return system directories that must never be written to."""
    if os.name == 'nt':
        candidates = []
        for env_name in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
            value = os.environ.get(env_name)
            if value:
                candidates.append(value)
        if not candidates:
            candidates = [r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)"]
    else:
        candidates = [
            "/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64",
            "/boot", "/proc", "/sys", "/dev",
        ]
    return tuple(_normalize_path(path) for path in candidates)


def _normalize_path(path: str) -> str:
    """Expand ~ and make the path absolute."""
    return os.path.normpath(os.path.expanduser(path))


# def is_protected_path(path: str) -> bool:
#     """Check whether a path points into a protected system directory."""
#     key = _normalize_path(path)
#     for protected in _protected_paths():
#         protected_key = _path_key(protected)
#         if key == protected_key or key.startswith(protected_key + os.sep):
#             return True
#     return False


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
    format_content: bool | None = None,
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

    if format_content:
        if content_type.startswith("text/") or content_type.startswith("application/json"):
            try:
                if isinstance(content, (bytes, bytearray)):
                    content = content.decode('utf-8')
                else:
                    content = str(content)
            except UnicodeDecodeError as e:
                err_message = f"response content type is \"{content_type}\", but not utf-8 encoded'"
                raise FormatResponseError(response, err_message) from e
            except Exception as e:
                err_message = f"response content type is \"{content_type}\", but cannot be converted to a string"
                raise FormatResponseError(response, err_message) from e
        else:
            err_message = f'response content type is "{content_type}", cannot be converted to a string'
            raise FormatResponseError(response, err_message)

        if content_type.startswith("text/html"):
            if return_content == "raw":
                pass
            elif return_content == "basic_clean":
                content = clean_html(content, allowed_attrs=True)
            elif return_content == "strict_clean":
                content = clean_html(content, allowed_attrs=("id", "src", "href"))
            elif return_content == "markdown":
                content = html_to_markdown(content)
    else:
        content = ""

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


def resolve_write_path(
    file_path: str,
    workspace: str | None,
    allowed_paths: list[str] | None = None,
    denied_paths: list[str] | None = None,
) -> str:
    """Resolve file_path and ensure it stays inside a writable root.

    Returns the normalized absolute path. Raises WritePathError otherwise.
    """
    if not file_path or not file_path.strip():
        raise WritePathError("file_path must not be empty")

    file_path = _normalize_path(file_path)

    if os.path.isabs(file_path):
        candidate = file_path
    else:
        if not workspace:
            raise WritePathError(
                "relative paths require a workspace; configure --workspace or use an absolute path"
            )
        candidate = _normalize_path(os.path.join(workspace, file_path))

    allowed_keys = [os.path.normcase(path) for path in (allowed_paths or ())]
    denied_keys = [os.path.normcase(path) for path in (denied_paths or ())]
    candidate_key = os.path.normcase(candidate)

    if any(candidate_key.startswith(root_key + os.sep) for root_key in denied_keys):
        raise WritePathError(f"path '{file_path}' is inside a denied write root.")

    if len(allowed_keys) == 0:
        raise WritePathError("fetch_to_file is enabled but no writable directory is configured.")

    if not any(candidate_key.startswith(root_key + os.sep) for root_key in allowed_keys):
        raise WritePathError(
            f"path '{file_path}' is not inside any allowed write root: {', '.join(allowed_keys)}"
        )

    if os.path.isdir(candidate):
        raise WritePathError(f"path '{file_path}' is a directory, not a file")

    return candidate


def create_mcp_server(
    *,
    ua: str | None = None,
    ua_random: bool = False,
    ua_os: str | None = None,
    ua_browser: str | None = None,
    ua_force: bool | None = None,
    enable_fetch_to_file: bool = False,
    workspace: str | None = None,
    allow_write_paths: tuple[str, ...] = ()
) -> FastMCP:

    mcp = FastMCP("Requests")

    ua = get_user_agent(ua=ua, ua_random=ua_random, ua_os=ua_os, ua_browser=ua_browser)

    workspace_path = _normalize_path(workspace) if workspace else None
    allowed_paths: list[str] = [workspace, *allow_write_paths] if workspace else [*allow_write_paths]
    allowed_paths = list(set(_normalize_path(p) for p in allowed_paths))
    allowed_paths = list(filter(os.path.isabs, allowed_paths))
    denied_paths = list(_protected_paths())

    @mcp.tool(name="fetch")
    def fetch_tool(
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
        if len(url) == 0:
            return "Error: url must not be empty"

        try:
            response = http_request(
                "GET", url,
                query=None,
                headers={"User-Agent": ua},
                data=None,
                json_=None
            )
        except RequestError as e:
            return "encountered an internal error when making a request, with the following error message:\n" \
                f"{e.message}"
        except Exception as e:
            return f"An unexpected error occurred while fetching \"{url}\"."

        try:
            return format_response_result(
                response,
                format_status=True,
                format_headers=True,
                format_content=True,
                return_content=return_content,
            )
        except FormatResponseError as e:
            res = format_response_result(
                response,
                format_status=True,
                format_headers=True,
                format_content=False,
                return_content=return_content,
            )

            return f"An error occurred while processing the response from \"{url}\":\r\n"\
                f"{e.message}\r\n"\
                "\r\n"\
                "The following is the response result:\r\n"\
                f"{res}"
        except Exception as e:
            return f"An unexpected error occurred while processing the response from \"{url}\"."

    if enable_fetch_to_file:
        @mcp.tool(name="fetch_to_file")
        def fetch_to_file_tool(
            url: Annotated[str, "(require) The URL to fetch content from"],
            file_path: Annotated[str, "(require) File path where the content will be saved"],
            *,
            return_content: Annotated[Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], "(optional, Defaults to \"markdown\") processing format for HTML content"] = "markdown",
        ) -> str:
            """Fetch web content and save it to a file

            Function/Features:
            - Retrieves web content from any HTTP/HTTPS URL and saves it to a file
            - Automatic directory creation for nested file paths

            Notes:
            - Automatically creates parent directories if they don't exist
            - Uses UTF-8 encoding for all saved files

            Args:
                url (str): The URL to fetch content from.
                file_path (str): File path where the content will be saved.
                return_content ('raw' | 'basic_clean' | 'strict_clean' | 'markdown', optional): Processing format for HTML content. Defaults to "markdown".
                  - "raw": Saves unmodified HTML content
                  - "basic_clean": Saves HTML with non-displaying tags removed (script, style, etc.) while preserving structure
                  - "strict_clean": Saves HTML with non-displaying tags and most HTML attributes removed, keeping only essential structure
                  - "markdown": Converts HTML content to clean, readable Markdown format before saving

            Examples:
                // Save web page as markdown
                fetch_to_file({url: "https://example.com", file_path: "content/example.md"})

                // Save raw HTML content
                fetch_to_file({url: "https://api.example.com/data", file_path: "data/response.html", return_content: "raw"})

                // Save cleaned content
                fetch_to_file({url: "https://example.com/docs", file_path: "docs/cleaned.html", return_content: "strict_clean"})
            """
            try:
                validated_path = resolve_write_path(file_path, workspace_path, allowed_paths, denied_paths)
            except WritePathError as e:
                return f"Error: {e.message}"
            except Exception as e:
                return f"An unexpected error occurred while fetching {url}."

            try:
                response = http_request(
                    "GET", url,
                    query=None,
                    headers={"User-Agent": ua},
                    data=None,
                    json_=None
                )
            except RequestError as e:
                return "encountered an internal error when making a request, with the following error message:\n" \
                    f"{e.message}"
            except Exception as e:
                return f"An unexpected error occurred while fetching \"{url}\"."

            try:
                content = format_response_result(
                    response,
                    format_status=False,
                    format_headers=False,
                    format_content=True,
                    return_content=return_content,
                )
            except FormatResponseError as e:
                res = format_response_result(
                    response,
                    format_status=True,
                    format_headers=True,
                    format_content=False,
                    return_content=return_content,
                )

                return f"An error occurred while processing the response from \"{url}\":\r\n"\
                    f"{e.message}\r\n"\
                    "\r\n"\
                    "The following is the response result:\r\n"\
                    f"{res}"
            except Exception as e:
                return f"An unexpected error occurred while processing the response from \"{url}\"."

            try:
                dir_path = os.path.dirname(validated_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)

                with open(validated_path, 'w', encoding='utf-8', newline='') as f:
                    f.write(content)

            except OSError as e:
                return f"Error: Unable to write to file '{validated_path}': {e}"
            except Exception as e:
                return f"An unexpected error occurred while writing the response from \"{url}\" to file \"{validated_path}\"."

            return f"Content from '{url}' ({len(content)} bytes) successfully written to: {validated_path}"

    @mcp.tool(name="http_request")
    def http_request_tool(
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

        if len(url) == 0:
            return "Error: url must not be empty"

        try:
            hs = dict(headers or {})

            if ua:
                if ua_force or "User-Agent" not in hs:
                    hs["User-Agent"] = ua

            response = http_request(
                method, url,
                query=query,
                headers=hs,
                data=data,
                json_=json
            )
        except RequestError as e:
            return "encountered an internal error when making a request, with the following error message:\n" \
                f"{e.message}"
        except Exception as e:
            return f"An unexpected error occurred while fetching \"{url}\"."

        try:
            return format_response_result(
                response,
                format_status=True,
                format_headers=True,
                format_content=True,
            )
        except FormatResponseError as e:
            res = format_response_result(
                response,
                format_status=True,
                format_headers=True,
                format_content=False,
            )

            return f"An error occurred while processing the response from \"{url}\":\r\n"\
                f"{e.message}\r\n"\
                "\r\n"\
                "The following is the response result:\r\n"\
                f"{res}"
        except Exception as e:
            return f"An unexpected error occurred while processing the response from \"{url}\"."

    return mcp
