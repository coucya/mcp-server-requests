import unittest
from unittest import mock

from click.testing import CliRunner

from .__main__ import main
from .request import RequestError, Response


def _response(content=b"<p>hello</p>", content_type="text/html"):
    return Response(
        "https://example.com", "HTTP/1.1", 200, "OK",
        [("Content-Type", content_type)],
        content,
    )


class TestFetchCommand(unittest.TestCase):
    """Test the CLI fetch subcommand"""

    def setUp(self):
        self.runner = CliRunner()

    def _invoke(self, args):
        return self.runner.invoke(main, ["fetch", *args])

    def test_default_get(self):
        with mock.patch(
            "mcp_server_requests.__main__.http_request",
            return_value=_response(),
        ) as mocked:
            result = self._invoke(["https://example.com"])

        self.assertEqual(result.exit_code, 0, result.output)
        args, kwargs = mocked.call_args
        self.assertEqual(args, ("GET", "https://example.com"))
        self.assertIsNone(kwargs["query"])
        self.assertIsNone(kwargs["body"])
        self.assertIsNone(kwargs["json_body"])
        self.assertEqual(kwargs["timeout"], 30.0)
        self.assertIn("User-Agent", kwargs["headers"])
        self.assertIn("hello", result.output)

    def test_method_headers_query_json(self):
        with mock.patch(
            "mcp_server_requests.__main__.http_request",
            return_value=_response(b'{"ok": true}', "application/json"),
        ) as mocked:
            result = self._invoke([
                "https://api.example.com/users",
                "-X", "POST",
                "-H", "Authorization: Bearer token",
                "-q", "q=test",
                "-q", "limit=10",
                "--json-body", '{"name": "John"}',
                "--timeout", "5",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        args, kwargs = mocked.call_args
        self.assertEqual(args, ("POST", "https://api.example.com/users"))
        self.assertEqual(kwargs["query"], {"q": "test", "limit": "10"})
        self.assertEqual(kwargs["json_body"], {"name": "John"})
        self.assertIsNone(kwargs["body"])
        self.assertEqual(kwargs["timeout"], 5.0)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer token")
        self.assertIn("User-Agent", kwargs["headers"])

    def test_lowercase_method(self):
        with mock.patch(
            "mcp_server_requests.__main__.http_request",
            return_value=_response(),
        ) as mocked:
            result = self._invoke(["https://example.com", "-X", "get"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(mocked.call_args.args[0], "GET")

    def test_body_forwarded(self):
        with mock.patch(
            "mcp_server_requests.__main__.http_request",
            return_value=_response("ok", "text/plain"),
        ) as mocked:
            result = self._invoke([
                "https://example.com/log",
                "-d", "raw payload",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(mocked.call_args.kwargs["body"], "raw payload")
        self.assertIsNone(mocked.call_args.kwargs["json_body"])

    def test_body_and_json_body_mutually_exclusive(self):
        result = self._invoke([
            "https://example.com",
            "--body", "x",
            "--json-body", "{}",
        ])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("cannot be used together", result.output)

    def test_invalid_json(self):
        result = self._invoke(["https://example.com", "--json-body", "{bad"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("invalid JSON", result.output)

    def test_invalid_header(self):
        result = self._invoke(["https://example.com", "-H", "no-colon"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("invalid header", result.output)

    def test_invalid_query(self):
        result = self._invoke(["https://example.com", "-q", "no-equals"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("invalid query parameter", result.output)

    def test_caller_user_agent_kept_when_not_forced(self):
        with mock.patch(
            "mcp_server_requests.__main__.http_request",
            return_value=_response(),
        ) as mocked:
            result = self._invoke([
                "https://example.com",
                "-H", "user-agent: Caller-Agent",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(
            mocked.call_args.kwargs["headers"],
            {"user-agent": "Caller-Agent"},
        )

    def test_forced_user_agent_replaces_caller_ua(self):
        with mock.patch(
            "mcp_server_requests.__main__.http_request",
            return_value=_response(),
        ) as mocked:
            result = self.runner.invoke(main, [
                "--force-user-agent",
                "fetch",
                "https://example.com",
                "-H", "user-agent: Caller-Agent",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        headers = mocked.call_args.kwargs["headers"]
        self.assertEqual(list(headers.keys()), ["User-Agent"])

    def test_request_error_returns_text(self):
        with mock.patch(
            "mcp_server_requests.__main__.http_request",
            side_effect=RequestError("connection failed"),
        ):
            result = self._invoke(["https://example.com"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("connection failed", result.output)


if __name__ == '__main__':
    unittest.main()
