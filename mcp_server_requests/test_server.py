import unittest
import os
import inspect
import tempfile
import shutil
import asyncio
import uuid

from .request import Response
from .server import (
    create_mcp_server,
    format_response_result,
    FormatResponseError,
    resolve_write_path,
    WritePathError,
    _configured_dir,
    _normalize_path,
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


class TestCreateMcpServer(unittest.TestCase):
    """Test fetch_to_file registration behavior"""

    @async_test
    async def test_fetch_to_file_not_registered_by_default(self):
        mcp = create_mcp_server(ua="Test-Agent")
        names = await _tool_names(mcp)
        self.assertNotIn("fetch_to_file", names)
        self.assertIn("fetch", names)
        self.assertIn("http_request", names)

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
            return_content="markdown",
        )
        self.assertIn("hello", result)

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
