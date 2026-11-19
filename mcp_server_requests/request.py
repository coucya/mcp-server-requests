from dataclasses import dataclass
from typing import Mapping, Optional, Literal, Union
import json

import urllib.error
import urllib.request
import http.client
from urllib.parse import parse_qsl, quote, urlparse, urlencode, urlunparse


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


def merge_query_to_url(url: str, query_dict: Mapping[str, str | int | float]) -> str:
    parsed_url = urlparse(url)

    original_query = parse_qsl(parsed_url.query)

    query_single: set[tuple[str, str | int | float]] = set(original_query)

    for k, v in query_dict.items():
        if not isinstance(v, (str, int, float)):
            raise ArgumentError(f"invalid value for query parameter {k}: {v}. value must be a string, int, or float.")
    query_single.update(query_dict.items())

    new_query = urlencode(list(query_single), encoding='utf-8')

    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))

    return new_url


def http_request(
    method: str,
    url: str,
    *,
    query: Optional[dict] = None,
    data: Optional[Union[str, bytes, bytearray]] = None,
    json_: Optional[dict] = None,
    headers: Optional[dict] = None
) -> Response:
    if headers is None:
        headers = {}

    if not isinstance(method, str):
        raise ArgumentError(f"http method must be a string, and must be one of {str(HTTP_METHODS)}")

    m, method = method, method.upper()
    if method not in HTTP_METHODS:
        raise ArgumentError(f"Invalid HTTP method: {m}, must be one of {str(HTTP_METHODS)}")

    if not isinstance(url, str):
        raise ArgumentError("URL must be a string")

    if data is not None and json_ is not None:
        raise ArgumentError("Both data and json cannot be provided at the same time")

    try:
        if query is not None:
            url = merge_query_to_url(url, query)
    except ArgumentError as e:
        raise e from e
    except Exception as e:
        raise ArgumentError("Failed to splicing URL and query") from e

    data_bytes = None
    if data is not None:
        if not isinstance(data, (str, bytes, bytearray)):
            raise ArgumentError("Data must be a string, bytes, or bytearray")
        elif isinstance(data, str):
            data_bytes = data.encode(encoding="utf-8")
        elif isinstance(data, bytearray):
            data_bytes = bytes(data)
        else:
            data_bytes = data
    elif json_ is not None:
        try:
            data_bytes = json.dumps(json_).encode(encoding="utf-8")
        except Exception as e:
            raise ArgumentError("Failed to serialize JSON data") from e

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        url = quote(url, safe=";/?:@&=+$,", encoding="utf-8")
        request = urllib.request.Request(url, method=method, headers=headers, data=data_bytes)
        response: http.client.HTTPResponse = urllib.request.urlopen(request)

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
