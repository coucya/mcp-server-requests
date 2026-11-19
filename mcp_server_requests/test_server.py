import unittest
import os
import tempfile
import shutil
import asyncio

from .server import (
    create_mcp_server,
    resolve_write_path,
    WritePathError,
    _normalize_path,
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


class TestWritePathHelpers(unittest.TestCase):
    """Test write path validation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_resolve_requires_workspace_for_relative_path(self):
        with self.assertRaises(WritePathError):
            resolve_write_path("relative.txt", None, ())

    def test_resolve_relative_with_workspace(self):
        workspace = _normalize_path(self.temp_dir)
        result = resolve_write_path("sub/x.txt", workspace, [workspace])
        self.assertEqual(result, _normalize_path(os.path.join(workspace, "sub", "x.txt")))

    def test_resolve_relative_escape_rejected(self):
        workspace = _normalize_path(self.temp_dir)
        with self.assertRaises(WritePathError):
            resolve_write_path("../x.txt", workspace, [workspace])

    def test_resolve_absolute_inside_workspace(self):
        workspace = _normalize_path(self.temp_dir)
        target = os.path.join(self.temp_dir, "x.txt")
        self.assertEqual(resolve_write_path(target, workspace, [workspace]), _normalize_path(target))

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
            _normalize_path(target)
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


class TestCreateMcpServer(unittest.TestCase):
    """Test fetch_to_file registration behavior"""

    @async_test
    async def test_fetch_to_file_not_registered_by_default(self):
        mcp = create_mcp_server(ua="Test-Agent")
        tools = await mcp.list_tools()
        names = {tool.name for tool in tools}
        self.assertNotIn("fetch_to_file", names)
        self.assertIn("fetch", names)
        self.assertIn("http_request", names)

    @async_test
    async def test_fetch_to_file_registered_when_enabled(self):
        temp_dir = tempfile.mkdtemp()
        try:
            mcp = create_mcp_server(
                ua="Test-Agent",
                enable_fetch_to_file=True,
                workspace=temp_dir,
            )
            tools = await mcp.list_tools()
            names = {tool.name for tool in tools}
            self.assertIn("fetch_to_file", names)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_startup_does_not_create_workspace(self):
        temp_dir = tempfile.mkdtemp()
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


if __name__ == '__main__':
    unittest.main()
