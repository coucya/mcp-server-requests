from dataclasses import dataclass
from typing import Optional, Union
import json

import urllib.error
import urllib.request
import http.client
from urllib.parse import quote


HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

VERSION_MAP = {
    10: "HTTP/1.0",
    11: "HTTP/1.1",
    20: "HTTP/2"
}


@dataclass
class Response:
    url: str
    version: str
    status_code: int
    reason: str
    headers: list[tuple[str, str]]
    content: str | bytes | bytearray

    _content_type: str | None = None

    @property
    def content_type(self) -> str:
        if self._content_type is None:
            for k, v in self.headers:
                if k.lower() == "content-type":
                    self._content_type = v

            if self._content_type is None:
                self._content_type = "application/octet-stream"

        return self._content_type


class RequestError(Exception):
    def __init__(self, message: str, reason: str | None = None, *args):
        super().__init__(message, reason, *args)
        self.message = message
        self.reason = reason


class ArgumentError(RequestError):
    pass


def http_request(
    method: str,
    url: str,
    *,
    body: Optional[Union[str, bytes, bytearray]] = None,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: float | None = 30.0,
) -> Response:
    if headers is None:
        headers = {}

    if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
        raise ArgumentError("timeout must be a positive number or None")

    if not isinstance(method, str):
        raise ArgumentError(f"http method must be a string, and must be one of {str(HTTP_METHODS)}")

    m, method = method, method.upper()
    if method not in HTTP_METHODS:
        raise ArgumentError(f"Invalid HTTP method: {m}, must be one of {str(HTTP_METHODS)}")

    if not isinstance(url, str):
        raise ArgumentError("URL must be a string")

    if body is not None and json_body is not None:
        raise ArgumentError("Both body and json_body cannot be provided at the same time")

    body_bytes = None
    if body is not None:
        if not isinstance(body, (str, bytes, bytearray)):
            raise ArgumentError("Body must be a string, bytes, or bytearray")
        elif isinstance(body, str):
            body_bytes = body.encode(encoding="utf-8")
        elif isinstance(body, bytearray):
            body_bytes = bytes(body)
        else:
            body_bytes = body
    elif json_body is not None:
        try:
            body_bytes = json.dumps(json_body).encode(encoding="utf-8")
        except Exception as e:
            raise ArgumentError("Failed to serialize JSON body") from e

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        url = quote(url, safe=";/?:@&=+$,", encoding="utf-8")
        request = urllib.request.Request(url, method=method, headers=headers, data=body_bytes)
        response: http.client.HTTPResponse = urllib.request.urlopen(request, timeout=timeout)

        version = VERSION_MAP.get(response.version, "HTTP/1.1")
        status_code = response.status
        reason = response.reason
        response_headers = response.getheaders()
        content = response.read()

        result = Response(url, version, status_code, reason, response_headers, content)
    except urllib.error.HTTPError as e:
        if e.status is None:
            raise RequestError(f"Failed to send request, unknown error") from e

        version = "HTTP/1.1"
        status_code = e.status
        reason = e.reason
        response_headers = e.headers.items()
        content = e.read()

        result = Response(url, version, status_code, reason, response_headers, content)
    except urllib.error.URLError as e:
        raise RequestError(f"Failed to send request, {e.reason}") from e
    except Exception as e:
        raise RequestError(f"Failed to send request, {e}") from e

    return result
