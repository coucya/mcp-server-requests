from typing import Dict, Any, Optional, Literal, Annotated
import os

from fastmcp import FastMCP


from .version import __version__
from .request import RequestError, Response, http_request
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


def _protected_paths(allowed_paths: list[str] | None = None) -> list[str]:
    """Return files and directories that must never be written to."""
    home = os.path.expanduser("~")
    if os.name == 'nt':
        candidates = []
        for env_name in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
            value = os.environ.get(env_name)
            if value:
                candidates.append(value)
        if not candidates:
            candidates = [r"C:\Windows", r"C:\Program Files", r"C:\Program Files (x86)"]
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(
                os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            )
    else:
        candidates = [
            "/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64",
            "/boot", "/proc", "/sys", "/dev",
        ]

    candidates.extend([
        os.path.join(home, ".config", "autostart"),
        os.path.join(home, ".aws"),
        os.path.join(home, ".gnupg"),
        os.path.join(home, ".ssh"),
        os.path.join(home, ".bashrc"),
        os.path.join(home, ".bash_profile"),
        os.path.join(home, ".bash_login"),
        os.path.join(home, ".profile"),
        os.path.join(home, ".zshrc"),
        os.path.join(home, ".zprofile"),
    ])

    for root in (allowed_paths or ()):
        candidates.append(os.path.join(root, ".git"))
        candidates.append(os.path.join(root, ".husky"))

    result = []
    seen = set()
    for path in candidates:
        normalized = _normalize_path(path)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _normalize_path(path: str) -> str:
    """Expand ~ and normalize the path without changing relative vs absolute."""
    return os.path.normpath(os.path.expanduser(path))


def _realpath(path: str) -> str:
    """Return the canonical path, stripping the Windows extended-length prefix."""
    resolved = os.path.realpath(path)
    if os.name == 'nt':
        if resolved.startswith('\\\\?\\UNC\\'):
            resolved = '\\\\' + resolved[8:]
        elif resolved.startswith('\\\\?\\'):
            resolved = resolved[4:]
    return resolved


def _path_key(path: str) -> str:
    """Return a canonical comparison key for a path."""
    return os.path.normcase(_realpath(os.path.abspath(os.path.expanduser(path))))


def _is_inside(path_key: str, root_key: str) -> bool:
    """Return True when path_key is strictly inside root_key."""
    prefix = root_key.rstrip(os.sep) + os.sep
    return path_key.startswith(prefix)


def _configured_dir(path: str | None) -> str | None:
    """Return a normalized absolute directory, or None when it is relative/empty."""
    if not path:
        return None
    normalized = _normalize_path(path)
    if not os.path.isabs(normalized):
        return None
    return normalized


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


def merge_user_agent(
    headers: Dict[str, str] | None,
    ua: str,
    force: bool | None = None,
) -> Dict[str, str]:
    """Merge the server User-Agent into caller-provided headers.

    Matching is case-insensitive. When force is true, every existing
    User-Agent variant is removed and replaced with the server UA.
    """
    merged = dict(headers or {})
    if not ua:
        return merged

    ua_keys = [key for key in merged if key.lower() == "user-agent"]
    if force or not ua_keys:
        for key in ua_keys:
            del merged[key]
        merged["User-Agent"] = ua
    return merged


def format_response_result(
    response: Response,
    *,
    format_status: bool | None = None,
    format_headers: bool | None = None,
    format_content: bool | None = None,
    return_format: Literal["raw", "basic_clean", "strict_clean", "markdown"] = "raw",
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
            if return_format == "raw":
                pass
            elif return_format == "basic_clean":
                content = clean_html(content, allowed_attrs=True)
            elif return_format == "strict_clean":
                content = clean_html(content, allowed_attrs=("id", "src", "href"))
            elif return_format == "markdown":
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

    Relative paths are resolved against workspace. Symlinks are resolved
    before the containment checks. Existing files are never overwritten.
    Returns the canonical absolute path. Raises WritePathError otherwise.
    """
    if not file_path or not file_path.strip():
        raise WritePathError("file_path must not be empty. Provide a file path.")
    file_path = file_path.strip()

    if workspace:
        workspace = _normalize_path(workspace)
        if not os.path.isabs(workspace):
            workspace = None

    normalized = _normalize_path(file_path)

    if os.path.isabs(normalized):
        candidate = os.path.abspath(normalized)
    else:
        if not workspace:
            raise WritePathError(
                "relative paths are not available: the server was started without a workspace. "
                "This is a server-side setting and cannot be changed by tool calls. "
                "Use an absolute path, or tell the user that the server needs --workspace "
                "to accept relative paths."
            )
        candidate = os.path.normpath(os.path.join(workspace, normalized))

    if not os.path.isabs(candidate):
        raise WritePathError(f"path '{file_path}' must resolve to an absolute path. Use an absolute path.")

    resolved = _realpath(candidate)
    resolved_key = os.path.normcase(resolved)
    denied_keys = [_path_key(path) for path in (denied_paths or ())]
    allowed_keys = [_path_key(path) for path in (allowed_paths or ())]

    # Denied paths include whole directories and individual files.
    is_denied = any(
        resolved_key == root_key or _is_inside(resolved_key, root_key)
        for root_key in denied_keys
    )
    if is_denied:
        raise WritePathError(f"path '{file_path}' is inside a denied write root. Choose a different path.")

    if len(allowed_keys) == 0:
        raise WritePathError(
            "no writable directory is configured on the server. "
            "This is a server-side setting and cannot be changed by tool calls. "
            "Ask the user to restart the server with --workspace or --writable-dir."
        )

    if not any(_is_inside(resolved_key, root_key) for root_key in allowed_keys):
        raise WritePathError(
            f"path '{file_path}' is not inside any writable directory configured on the server. "
            "Choose a different path."
        )

    # isdir() runs first so directories get a clearer error message.
    # lexists() covers regular files, directories, symlinks, and broken symlinks.
    if os.path.isdir(candidate):
        raise WritePathError(f"path '{file_path}' is a directory, not a file. Provide a file path.")
    if os.path.lexists(candidate):
        raise WritePathError(
            f"path '{file_path}' already exists; refusing to overwrite. Choose a different file name."
        )

    return resolved


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

    workspace_path = _configured_dir(workspace)
    allowed_paths: list[str] = []
    for path in ([workspace] if workspace else []) + list(allow_write_paths):
        configured = _configured_dir(path)
        if configured is not None and configured not in allowed_paths:
            allowed_paths.append(configured)

    denied_paths = _protected_paths(allowed_paths)

    @mcp.tool(name="fetch")
    def fetch_tool(
        url: Annotated[str, "(require) The URL to fetch content from or send the request to"],
        *,
        method: Annotated[Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], "(optional, Defaults to \"GET\") HTTP method to use for the request"] = "GET",
        query: Annotated[Optional[Dict[str, str | int | float]], "(optional) Query parameters to append to the URL"] = None,
        headers: Annotated[Optional[Dict[str, str]], "(optional) Custom HTTP request headers"] = None,
        body: Annotated[Optional[str], "(optional) Text data to send in the request body. Cannot be used with 'json_body'"] = None,
        json_body: Annotated[Optional[Any], "(optional) JSON to send in the request body. Cannot be used with 'body'"] = None,
        return_format: Annotated[Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], "(optional, Defaults to \"markdown\") processing format for HTML content"] = "markdown",
        timeout: Annotated[float | None, "(optional, Defaults to 30) request timeout in seconds; use null for no timeout"] = 30.0,
    ) -> str:
        """Fetch web content or send an HTTP request

        Function/Features:
        - Retrieves web content from any HTTP/HTTPS URL (default method is GET)
        - Sends requests using any standard method (GET, POST, PUT, PATCH, DELETE)
        - Allows custom query parameters and HTTP headers
        - Supports text and JSON request bodies
        - Returns the complete HTTP response including status line, headers, and body
        - Converts or cleans HTML content to reduce token usage

        Notes:
        - 'body' and 'json_body' parameters are mutually exclusive - use only one
        - When using 'json_body', the Content-Type header is automatically set to 'application/json'
        - When using 'body', you may need to set an appropriate Content-Type header manually
        - Query parameters are URL-encoded automatically and appended to the URL
        - 'return_format' only affects text/html responses:
          - "raw": Returns unmodified HTML
          - "basic_clean": Removes non-displaying tags (script, style, meta, etc.) while preserving structure
          - "strict_clean": Removes non-displaying tags and most HTML attributes, keeping only essential structure
          - "markdown": Converts HTML content to clean, readable Markdown format
        - JSON and other text responses are returned as-is, without HTML processing

        Args:
            url (str): The URL to fetch content from or send the request to.
            method ('GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE', optional): HTTP method to use. Defaults to "GET".
            query ({ [string]: string | number }, optional): Query parameters to append to the URL. Values are automatically converted to strings.
            headers ({ [string]: string }, optional): Custom HTTP request headers.
            body (str, optional): Text data to send in the request body. Cannot be used with 'json_body'.
            json_body (Any JSON, optional): Data to serialize as JSON and send in the request body. Cannot be used with 'body'.
            return_format ('raw' | 'basic_clean' | 'strict_clean' | 'markdown', optional): Processing format for HTML content. Defaults to "markdown".
            timeout (float, optional): Request timeout in seconds. Defaults to 30. Use null for no timeout.

        Examples:
            // Fetch a web page as markdown (default)
            fetch({url: "https://example.com"})

            // Fetch raw HTML content
            fetch({url: "https://example.com", return_format: "raw"})

            // GET request with query parameters
            fetch({url: "https://api.example.com/search", query: {"q": "test", "limit": 10}})

            // POST request with JSON data
            fetch({url: "https://api.example.com/users", method: "POST", json_body: {"name": "John", "age": 30}})

            // POST request with raw text data
            fetch({url: "https://api.example.com/log", method: "POST", body: "This is a log message"})

            // PUT request
            fetch({url: "https://api.example.com/users/123", method: "PUT", json_body: {"name": "John Updated"}})

            // PATCH request
            fetch({url: "https://api.example.com/users/123", method: "PATCH", json_body: {"age": 31}})

            // DELETE request
            fetch({url: "https://api.example.com/users/123", method: "DELETE"})

            // Request with custom headers
            fetch({url: "https://api.example.com/secure", method: "POST", headers: {"Authorization": "Bearer token"}, json_body: {"key": "value"}})
        """
        if len(url) == 0:
            return "Error: url must not be empty"

        try:
            response = http_request(
                method, url,
                query=query,
                headers=merge_user_agent(headers, ua, ua_force),
                body=body,
                json_body=json_body,
                timeout=timeout,
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
                return_format=return_format,
            )
        except FormatResponseError as e:
            res = format_response_result(
                response,
                format_status=True,
                format_headers=True,
                format_content=False,
                return_format=return_format,
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
            url: Annotated[str, "(require) The URL to fetch content from or send the request to"],
            file_path: Annotated[str, "(require) File path where the content will be saved. Must be inside a writable directory configured on the server."],
            *,
            method: Annotated[Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], "(optional, Defaults to \"GET\") HTTP method to use for the request"] = "GET",
            query: Annotated[Optional[Dict[str, str | int | float]], "(optional) Query parameters to append to the URL"] = None,
            headers: Annotated[Optional[Dict[str, str]], "(optional) Custom HTTP request headers"] = None,
            body: Annotated[Optional[str], "(optional) Text data to send in the request body. Cannot be used with 'json_body'"] = None,
            json_body: Annotated[Optional[Any], "(optional) JSON to send in the request body. Cannot be used with 'body'"] = None,
            return_format: Annotated[Literal['raw', 'basic_clean', 'strict_clean', 'markdown'], "(optional, Defaults to \"markdown\") processing format for HTML content"] = "markdown",
            timeout: Annotated[float | None, "(optional, Defaults to 30) request timeout in seconds; use null for no timeout"] = 30.0,
        ) -> str:
            """Fetch web content or send an HTTP request, then save the response body to a file

            Function/Features:
            - Retrieves web content from any HTTP/HTTPS URL (default method is GET) and saves it to a file
            - Sends requests using any standard method (GET, POST, PUT, PATCH, DELETE)
            - Allows custom query parameters and HTTP headers
            - Supports text and JSON request bodies
            - Automatic directory creation for nested file paths

            Notes:
            - 'body' and 'json_body' parameters are mutually exclusive - use only one
            - When using 'json_body', the Content-Type header is automatically set to 'application/json'
            - When using 'body', you may need to set an appropriate Content-Type header manually
            - Query parameters are URL-encoded automatically and appended to the URL
            - The target path must be inside a writable directory configured on the server
            - Path validation happens before the request; invalid paths never trigger a request
            - Automatically creates parent directories if they don't exist
            - Existing files are never overwritten
            - Uses UTF-8 encoding for all saved files
            - Only the response body is written; status line and headers are omitted
            - 'return_format' only affects text/html responses

            Args:
                url (str): The URL to fetch content from or send the request to.
                file_path (str): File path where the content will be saved. Must be inside a writable directory configured on the server.
                method ('GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE', optional): HTTP method to use. Defaults to "GET".
                query ({ [string]: string | number }, optional): Query parameters to append to the URL.
                headers ({ [string]: string }, optional): Custom HTTP request headers.
                body (str, optional): Text data to send in the request body. Cannot be used with 'json_body'.
                json_body (Any JSON, optional): Data to serialize as JSON and send in the request body. Cannot be used with 'body'.
                return_format ('raw' | 'basic_clean' | 'strict_clean' | 'markdown', optional): Processing format for HTML content. Defaults to "markdown".
                  - "raw": Saves unmodified HTML content
                  - "basic_clean": Saves HTML with non-displaying tags removed (script, style, etc.) while preserving structure
                  - "strict_clean": Saves HTML with non-displaying tags and most HTML attributes removed, keeping only essential structure
                  - "markdown": Converts HTML content to clean, readable Markdown format before saving
                timeout (float, optional): Request timeout in seconds. Defaults to 30. Use null for no timeout.

            Examples:
                // Save web page as markdown
                fetch_to_file({url: "https://example.com", file_path: "content/example.md"})

                // Save raw HTML content
                fetch_to_file({url: "https://api.example.com/data", file_path: "data/response.html", return_format: "raw"})

                // Save cleaned content
                fetch_to_file({url: "https://example.com/docs", file_path: "docs/cleaned.html", return_format: "strict_clean"})

                // POST JSON and save the response body
                fetch_to_file({url: "https://api.example.com/users", file_path: "data/created.json", method: "POST", json_body: {"name": "John"}})
            """
            if len(url) == 0:
                return "Error: url must not be empty"

            try:
                validated_path = resolve_write_path(file_path, workspace_path, allowed_paths, denied_paths)
            except WritePathError as e:
                return f"Error: {e.message}"
            except Exception:
                return f"An unexpected error occurred while resolving the target path for \"{url}\"."

            try:
                response = http_request(
                    method, url,
                    query=query,
                    headers=merge_user_agent(headers, ua, ua_force),
                    body=body,
                    json_body=json_body,
                    timeout=timeout,
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
                    return_format=return_format,
                )
            except FormatResponseError as e:
                res = format_response_result(
                    response,
                    format_status=True,
                    format_headers=True,
                    format_content=False,
                    return_format=return_format,
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

                with open(validated_path, 'x', encoding='utf-8', newline='') as f:
                    f.write(content)

            except FileExistsError:
                return f"Error: file '{validated_path}' already exists; refusing to overwrite"
            except OSError as e:
                return f"Error: Unable to write to file '{validated_path}': {e}"
            except Exception as e:
                return f"An unexpected error occurred while writing the response from \"{url}\" to file \"{validated_path}\"."

            return f"Content from '{url}' ({len(content)} bytes) successfully written to: {validated_path}"

    return mcp
