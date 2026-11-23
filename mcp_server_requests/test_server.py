import unittest
import os
import inspect
import tempfile
import shutil
import asyncio
import uuid
from unittest import mock

from .request import RequestError, Response
from .server import (
    create_mcp_server,
    format_response_result,
    FormatResponseError,
    resolve_write_path,
    WritePathError,
    _configured_dir,
    _normalize_path,
    _protected_paths,
    _realpath,
)


def async_test(test_func):
    """Decorator to make async test functions work with unittest"""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(test_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


def _make_temp_dir() -> str:
    """Create a writable temporary directory with default permissions."""
    path = os.path.join(
        tempfile.gettempdir(),
        f"mcp-server-requests-test-{uuid.uuid4().hex}",
    )
    os.makedirs(path)
    return path


async def _tool_names(mcp) -> set[str]:
    """Return registered tool names across FastMCP versions."""
    get_tools = getattr(mcp, "get_tools", None)
    if get_tools is not None:
        tools = get_tools()
        if inspect.isawaitable(tools):
            tools = await tools
        if isinstance(tools, dict):
            return set(tools.keys())
        return {tool.name for tool in tools}

    tools = mcp._list_tools()
    if inspect.isawaitable(tools):
        tools = await tools
    return {tool.name for tool in tools}


async def _get_tool(mcp, name: str):
    """Return a registered tool object across FastMCP versions."""
    get_tool = getattr(mcp, "get_tool", None)
    if get_tool is not None:
        tool = get_tool(name)
        if inspect.isawaitable(tool):
            tool = await tool
        return tool

    get_tools = getattr(mcp, "get_tools", None)
    if get_tools is not None:
        tools = get_tools()
        if inspect.isawaitable(tools):
            tools = await tools
        if isinstance(tools, dict):
            return tools[name]
        for tool in tools:
            if tool.name == name:
                return tool

    tools = mcp._list_tools()
    if inspect.isawaitable(tools):
        tools = await tools
    for tool in tools:
        if tool.name == name:
            return tool
    raise KeyError(name)


class TestWritePathHelpers(unittest.TestCase):
    """Test write path validation"""

    def setUp(self):
        self.temp_dir = _make_temp_dir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_resolve_requires_workspace_for_relative_path(self):
        with self.assertRaises(WritePathError):
            resolve_write_path("relative.txt", None, ())

    def test_resolve_relative_with_workspace(self):
        workspace = _normalize_path(self.temp_dir)
        result = resolve_write_path("sub/x.txt", workspace, [workspace])
        self.assertEqual(result, _realpath(os.path.join(workspace, "sub", "x.txt")))

    def test_resolve_relative_escape_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        with self.assertRaises(WritePathError):
            resolve_write_path("../x.txt", workspace, [workspace])

    def test_resolve_absolute_inside_workspace(self):
        workspace = _normalize_path(self.temp_dir)
        target = os.path.join(self.temp_dir, "x.txt")
        self.assertEqual(resolve_write_path(target, workspace, [workspace]), _realpath(target))

    def test_resolve_absolute_outside_roots_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        outside = os.path.join(tempfile.gettempdir(), "outside.txt")
        with self.assertRaises(WritePathError):
            resolve_write_path(outside, workspace, [workspace])

    def test_resolve_absolute_inside_extra_root(self):
        workspace = _normalize_path(os.path.join(self.temp_dir, "ws"))
        extra = _normalize_path(os.path.join(self.temp_dir, "extra"))
        os.makedirs(workspace, exist_ok=True)
        os.makedirs(extra, exist_ok=True)
        target = os.path.join(extra, "x.txt")
        self.assertEqual(
            resolve_write_path(target, workspace, [workspace, extra]),
            _realpath(target)
        )

    def test_resolve_prefix_confusion_rejected(self):
        workspace = _normalize_path(os.path.join(self.temp_dir, "data"))
        os.makedirs(workspace, exist_ok=True)
        evil_dir = os.path.join(self.temp_dir, "data-evil")
        os.makedirs(evil_dir, exist_ok=True)
        evil = os.path.join(evil_dir, "x.txt")
        with self.assertRaises(WritePathError):
            resolve_write_path(evil, workspace, [workspace])

    def test_resolve_directory_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        with self.assertRaises(WritePathError):
            resolve_write_path(self.temp_dir, workspace, [workspace])

    def test_resolve_empty_rejected(self):
        with self.assertRaises(WritePathError):
            resolve_write_path("", None, ())

    def test_resolve_no_roots_rejected(self):
        with self.assertRaises(WritePathError):
            resolve_write_path(os.path.join(self.temp_dir, "x.txt"), None, ())

    def test_resolve_normalization_bypass_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        with self.assertRaises(WritePathError):
            resolve_write_path(os.path.join(self.temp_dir, "..", "x.txt"), workspace, [workspace])

    def test_resolve_relative_workspace_ignored(self):
        with self.assertRaises(WritePathError):
            resolve_write_path("x.txt", "relative-workspace", ["relative-workspace"])

    def test_resolve_denied_directory_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        denied = _normalize_path(os.path.join(self.temp_dir, "protected"))
        os.makedirs(denied, exist_ok=True)
        target = os.path.join(denied, "x.txt")
        with self.assertRaises(WritePathError):
            resolve_write_path(target, workspace, [workspace], [denied])

    def test_resolve_denied_file_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        denied_file = _normalize_path(os.path.join(self.temp_dir, "protected.txt"))
        with self.assertRaises(WritePathError):
            resolve_write_path(denied_file, workspace, [workspace], [denied_file])

    def test_resolve_denied_git_hooks_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        denied = _normalize_path(os.path.join(workspace, ".git"))
        target = os.path.join(denied, "hooks", "pre-commit")
        with self.assertRaises(WritePathError):
            resolve_write_path(target, workspace, [workspace], [denied])

    @unittest.skipIf(os.name == "nt", "POSIX double-slash path semantics")
    def test_resolve_double_slash_denied(self):
        with self.assertRaises(WritePathError):
            resolve_write_path("//etc/passwd", "/", ["/"], ["/etc"])

    def test_resolve_existing_file_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        target = os.path.join(self.temp_dir, "exists.txt")
        with open(target, "w", encoding="utf-8") as f:
            f.write("x")
        with self.assertRaises(WritePathError):
            resolve_write_path(target, workspace, [workspace])

    @unittest.skipIf(os.name == "nt", "symlink creation requires extra privileges on Windows")
    def test_resolve_symlink_escape_rejected(self):
        workspace = _normalize_path(os.path.join(self.temp_dir, "ws"))
        os.makedirs(workspace, exist_ok=True)
        outside = os.path.join(self.temp_dir, "outside")
        os.makedirs(outside, exist_ok=True)
        link = os.path.join(workspace, "link")
        os.symlink(outside, link)
        with self.assertRaises(WritePathError):
            resolve_write_path(os.path.join(link, "x.txt"), workspace, [workspace])

    @unittest.skipIf(os.name == "nt", "symlink creation requires extra privileges on Windows")
    def test_resolve_existing_symlink_rejected(self):
        workspace = _normalize_path(os.path.join(self.temp_dir, "ws"))
        os.makedirs(workspace, exist_ok=True)
        target_file = os.path.join(self.temp_dir, "target.txt")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("x")
        link = os.path.join(workspace, "link.txt")
        os.symlink(target_file, link)
        with self.assertRaises(WritePathError):
            resolve_write_path(link, workspace, [workspace])

    def test_resolve_root_workspace_allows_child(self):
        if os.name == "nt":
            root = os.path.splitdrive(self.temp_dir)[0] + os.sep
        else:
            root = os.sep
        target = os.path.join(self.temp_dir, "root-child.txt")
        self.assertEqual(
            resolve_write_path(target, root, [root]),
            _realpath(target)
        )

    def test_resolve_error_does_not_list_allowed_roots(self):
        workspace = _normalize_path(self.temp_dir)
        outside_dir = _make_temp_dir()
        try:
            outside = os.path.join(outside_dir, "outside-root.txt")
            with self.assertRaises(WritePathError) as ctx:
                resolve_write_path(outside, workspace, [workspace])
            self.assertNotIn(workspace, str(ctx.exception))
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_protected_paths_include_reported_targets(self):
        home = _normalize_path(os.path.expanduser("~"))
        denied = _protected_paths()
        self.assertIn(_normalize_path(os.path.join(home, ".ssh")), denied)
        self.assertIn(_normalize_path(os.path.join(home, ".bashrc")), denied)
        self.assertIn(_normalize_path(os.path.join(home, ".config", "autostart")), denied)
        if os.name == "nt":
            system_root = os.environ.get("SystemRoot")
            if system_root:
                self.assertIn(_normalize_path(system_root), denied)
        else:
            self.assertIn("/etc", denied)

    def test_resolve_reported_ssh_target_rejected(self):
        home = _normalize_path(os.path.expanduser("~"))
        target = os.path.join(home, ".ssh", "authorized_keys")
        with self.assertRaises(WritePathError):
            resolve_write_path(target, home, [home], _protected_paths())

    def test_resolve_reported_bashrc_rejected(self):
        home = _normalize_path(os.path.expanduser("~"))
        target = os.path.join(home, ".bashrc")
        with self.assertRaises(WritePathError):
            resolve_write_path(target, home, [home], _protected_paths())

    def test_resolve_reported_autostart_rejected(self):
        home = _normalize_path(os.path.expanduser("~"))
        target = os.path.join(home, ".config", "autostart", "evil.desktop")
        with self.assertRaises(WritePathError):
            resolve_write_path(target, home, [home], _protected_paths())

    @unittest.skipIf(os.name == "nt", "POSIX protected system directory")
    def test_resolve_posix_etc_rejected(self):
        with self.assertRaises(WritePathError):
            resolve_write_path("/etc/cron.d/evil", "/", ["/"], _protected_paths())

    @unittest.skipUnless(os.name == "nt", "Windows protected system directory")
    def test_resolve_windows_system_directory_rejected(self):
        system_root = os.environ.get("SystemRoot")
        if not system_root:
            self.skipTest("SystemRoot is not set")
        drive_root = os.path.splitdrive(system_root)[0] + os.sep
        target = os.path.join(system_root, "Temp", "evil.txt")
        with self.assertRaises(WritePathError):
            resolve_write_path(target, drive_root, [drive_root], _protected_paths())


class TestCreateMcpServer(unittest.TestCase):
    """Test fetch_to_file registration behavior"""

    @async_test
    async def test_default_tool_set(self):
        mcp = create_mcp_server(ua="Test-Agent")
        names = await _tool_names(mcp)
        self.assertIn("fetch", names)
        self.assertNotIn("http_request", names)
        self.assertNotIn("fetch_to_file", names)

    @async_test
    async def test_fetch_to_file_registered_when_enabled(self):
        temp_dir = _make_temp_dir()
        try:
            mcp = create_mcp_server(
                ua="Test-Agent",
                enable_fetch_to_file=True,
                workspace=temp_dir,
            )
            names = await _tool_names(mcp)
            self.assertIn("fetch_to_file", names)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_startup_does_not_create_workspace(self):
        temp_dir = _make_temp_dir()
        target = os.path.join(temp_dir, "not_yet")
        try:
            create_mcp_server(
                ua="Test-Agent",
                enable_fetch_to_file=True,
                workspace=target,
            )
            self.assertFalse(os.path.exists(target))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_configured_dir_ignores_relative_path(self):
        self.assertIsNone(_configured_dir("relative-dir"))
        self.assertIsNone(_configured_dir(""))
        self.assertIsNone(_configured_dir(None))
        self.assertEqual(
            _configured_dir(tempfile.gettempdir()),
            _normalize_path(tempfile.gettempdir()),
        )

    def test_protected_paths_includes_git_hooks(self):
        workspace = _make_temp_dir()
        try:
            denied = _protected_paths([workspace])
            self.assertIn(_normalize_path(os.path.join(workspace, ".git")), denied)
            self.assertIn(_normalize_path(os.path.join(workspace, ".husky")), denied)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


class TestFetchTool(unittest.TestCase):
    """Test the merged fetch tool"""

    def _make_server(self, *, ua_force: bool | None = None):
        return create_mcp_server(ua="Test-Agent", ua_force=ua_force)

    @staticmethod
    def _response(content=b"<p>hello</p>", content_type="text/html"):
        return Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", content_type)],
            content,
        )

    @async_test
    async def test_default_get_with_server_user_agent(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch")
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=self._response(),
        ) as mocked:
            result = tool.fn(url="https://example.com")

        mocked.assert_called_once_with(
            "GET", "https://example.com",

            headers={"User-Agent": "Test-Agent"},
            body=None,
            json_body=None,
            timeout=30.0,
        )
        self.assertIn("HTTP/1.1 200 OK", result)
        self.assertIn("hello", result)

    @async_test
    async def test_method_body_forwarded(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch")
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=self._response("ok", "text/plain"),
        ) as mocked:
            tool.fn(
                url="https://example.com/log",
                method="PATCH",

                body="payload",
                timeout=5.0,
            )

        mocked.assert_called_once_with(
            "PATCH", "https://example.com/log",

            headers={"User-Agent": "Test-Agent"},
            body="payload",
            json_body=None,
            timeout=5.0,
        )

    @async_test
    async def test_post_json_forwarded(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch")
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=self._response(b'{"ok": true}', "application/json"),
        ) as mocked:
            result = tool.fn(
                url="https://api.example.com/users",
                method="POST",
                json_body={"name": "John"},
                timeout=None,
            )

        mocked.assert_called_once_with(
            "POST", "https://api.example.com/users",

            headers={"User-Agent": "Test-Agent"},
            body=None,
            json_body={"name": "John"},
            timeout=None,
        )
        self.assertIn('{"ok": true}', result)

    @async_test
    async def test_caller_user_agent_kept_when_not_forced(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch")
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=self._response(),
        ) as mocked:
            tool.fn(
                url="https://example.com",
                headers={"user-agent": "Caller-Agent"},
            )

        headers = mocked.call_args.kwargs["headers"]
        self.assertEqual(headers, {"user-agent": "Caller-Agent"})

    @async_test
    async def test_forced_user_agent_replaces_case_variants(self):
        mcp = self._make_server(ua_force=True)
        tool = await _get_tool(mcp, "fetch")
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=self._response(),
        ) as mocked:
            tool.fn(
                url="https://example.com",
                headers={"user-agent": "Caller-Agent", "User-Agent": "Other-Agent"},
            )

        headers = mocked.call_args.kwargs["headers"]
        self.assertEqual(headers, {"User-Agent": "Test-Agent"})

    @async_test
    async def test_empty_url(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch")
        result = tool.fn(url="")
        self.assertIn("url must not be empty", result)

    @async_test
    async def test_request_error_returns_text(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch")
        with mock.patch(
            "mcp_server_requests.server.http_request",
            side_effect=RequestError("connection failed"),
        ):
            result = tool.fn(url="https://example.com")
        self.assertIn("connection failed", result)


class TestFetchToFileTool(unittest.TestCase):
    def setUp(self):
        self.workspace = _make_temp_dir()

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def _make_server(self, *, ua_force: bool | None = None):
        return create_mcp_server(
            ua="Test-Agent",
            ua_force=ua_force,
            enable_fetch_to_file=True,
            workspace=self.workspace,
        )

    @async_test
    async def test_fetch_error_does_not_write_file(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        target = os.path.join(self.workspace, "out.txt")
        with mock.patch(
            "mcp_server_requests.server.http_request",
            side_effect=RequestError("connection failed"),
        ):
            result = tool.fn(
                url="https://example.com",
                file_path="out.txt",
                return_format="raw",
                timeout=30.0,
            )
        self.assertIn("internal error", result)
        self.assertFalse(os.path.exists(target))

    @async_test
    async def test_format_error_does_not_write_file(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        target = os.path.join(self.workspace, "out.bin")
        response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "application/octet-stream")],
            b"\x00",
        )
        with mock.patch("mcp_server_requests.server.http_request", return_value=response):
            result = tool.fn(
                url="https://example.com",
                file_path="out.bin",
                return_format="raw",
                timeout=30.0,
            )
        self.assertIn("cannot be converted", result)
        self.assertFalse(os.path.exists(target))

    @async_test
    async def test_existing_file_not_overwritten(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        target = os.path.join(self.workspace, "out.txt")
        with open(target, "w", encoding="utf-8") as f:
            f.write("original")
        result = tool.fn(
            url="https://example.com",
            file_path="out.txt",
            return_format="raw",
            timeout=30.0,
        )
        self.assertIn("already exists", result)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "original")

    @async_test
    async def test_text_response_writes_file(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        target = os.path.join(self.workspace, "out.txt")
        response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"hello",
        )
        with mock.patch("mcp_server_requests.server.http_request", return_value=response):
            result = tool.fn(
                url="https://example.com",
                file_path="out.txt",
                return_format="raw",
                timeout=30.0,
            )
        self.assertIn("successfully written", result)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "hello")

    @async_test
    async def test_post_json_request_forwarded_and_written(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        target = os.path.join(self.workspace, "out.json")
        response = Response(
            "https://api.example.com/users", "HTTP/1.1", 201, "Created",
            [("Content-Type", "application/json")],
            b'{"id": 1}',
        )
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=response,
        ) as mocked:
            result = tool.fn(
                url="https://api.example.com/users",
                file_path="out.json",
                method="POST",

                json_body={"name": "John"},
                timeout=5.0,
            )

        mocked.assert_called_once_with(
            "POST", "https://api.example.com/users",

            headers={"User-Agent": "Test-Agent"},
            body=None,
            json_body={"name": "John"},
            timeout=5.0,
        )
        self.assertIn("successfully written", result)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"id": 1}')

    @async_test
    async def test_body_request_forwarded_and_written(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        target = os.path.join(self.workspace, "out.txt")
        response = Response(
            "https://example.com/log", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"accepted",
        )
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=response,
        ) as mocked:
            result = tool.fn(
                url="https://example.com/log",
                file_path="out.txt",
                method="PUT",
                body="raw payload",
            )

        mocked.assert_called_once_with(
            "PUT", "https://example.com/log",

            headers={"User-Agent": "Test-Agent"},
            body="raw payload",
            json_body=None,
            timeout=30.0,
        )
        self.assertIn("successfully written", result)
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "accepted")

    @async_test
    async def test_caller_user_agent_kept_when_not_forced(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"ok",
        )
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=response,
        ) as mocked:
            tool.fn(
                url="https://example.com",
                file_path="out.txt",
                headers={"user-agent": "Caller-Agent"},
            )

        headers = mocked.call_args.kwargs["headers"]
        self.assertEqual(headers, {"user-agent": "Caller-Agent"})

    @async_test
    async def test_forced_user_agent_replaces_case_variants(self):
        mcp = self._make_server(ua_force=True)
        tool = await _get_tool(mcp, "fetch_to_file")
        response = Response(
            "https://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"ok",
        )
        with mock.patch(
            "mcp_server_requests.server.http_request",
            return_value=response,
        ) as mocked:
            tool.fn(
                url="https://example.com",
                file_path="out.txt",
                headers={"user-agent": "Caller-Agent", "User-Agent": "Other-Agent"},
            )

        headers = mocked.call_args.kwargs["headers"]
        self.assertEqual(headers, {"User-Agent": "Test-Agent"})

    @async_test
    async def test_invalid_path_does_not_request(self):
        mcp = self._make_server()
        tool = await _get_tool(mcp, "fetch_to_file")
        with mock.patch("mcp_server_requests.server.http_request") as mocked:
            result = tool.fn(
                url="https://example.com",
                file_path="../escape.txt",
            )

        self.assertIn("Error:", result)
        mocked.assert_not_called()


class TestFormatResponseResult(unittest.TestCase):
    def test_format_markdown(self):
        response = Response(
            "http://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/html")],
            b"<p>hello</p>",
        )
        result = format_response_result(
            response,
            format_content=True,
            return_format="markdown",
        )
        self.assertIn("hello", result)

    def test_format_status_headers_and_content(self):
        response = Response(
            "http://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain"), ("X-Test", "1")],
            b"hello",
        )
        result = format_response_result(
            response,
            format_status=True,
            format_headers=True,
            format_content=True,
        )
        self.assertEqual(
            result,
            "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nX-Test: 1\r\n\r\nhello",
        )

    def test_format_status_without_headers(self):
        response = Response(
            "http://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"hello",
        )
        result = format_response_result(
            response,
            format_status=True,
            format_headers=False,
            format_content=True,
        )
        self.assertEqual(result, "HTTP/1.1 200 OK\r\n\r\nhello")

    def test_format_headers_without_status(self):
        response = Response(
            "http://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"hello",
        )
        result = format_response_result(
            response,
            format_status=False,
            format_headers=True,
            format_content=True,
        )
        self.assertEqual(result, "Content-Type: text/plain\r\n\r\nhello")

    def test_format_content_only(self):
        response = Response(
            "http://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"hello",
        )
        result = format_response_result(
            response,
            format_status=False,
            format_headers=False,
            format_content=True,
        )
        self.assertEqual(result, "hello")

    def test_format_non_text_raises(self):
        response = Response(
            "http://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "application/octet-stream")],
            b"\x00",
        )
        with self.assertRaises(FormatResponseError):
            format_response_result(response, format_content=True)

    def test_format_content_false_returns_empty(self):
        response = Response(
            "http://example.com", "HTTP/1.1", 200, "OK",
            [("Content-Type", "text/plain")],
            b"hello",
        )
        result = format_response_result(
            response,
            format_status=False,
            format_headers=False,
            format_content=False,
        )
        self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
