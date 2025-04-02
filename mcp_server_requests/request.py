from dataclasses import dataclass
from typing import Any, Optional, Literal, Union
import random
import json

import urllib
import urllib.error
import urllib.parse
import urllib.request
import http.client

from .utils import html_to_markdown, remove_tag


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

    @property
    def content_type(self) -> str:
        for k, v in self.headers:
            if k.lower() == "content-type":
                return v
        return "application/octet-stream"


class McpError(Exception):
    def __init__(self, message: str, reason: str | None = None, *args):
        super().__init__(message, reason, *args)
        self.message = message
        self.reason = reason


class ArgumentError(McpError):
    pass


class RequestError(McpError):
    pass


class ResponseError(McpError):
    def __init__(self, response: Response, message: str, reason: str | None = None, *args):
        super().__init__(message, reason, response, *args)
        self.response = response


from urllib.parse import parse_qsl, urlparse, parse_qs, urlencode, urlunparse


def merge_query_to_url(url: str, query_dict: dict[str, str | int | float]) -> str:
    parsed_url = urlparse(url)

    original_query = parse_qsl(parsed_url.query)

    query_single = set(original_query)

    for k, v in query_dict.items():
        if not isinstance(v, (str, int, float)):
            raise ArgumentError(f"invalid value for query parameter {k}: {v}. value must be a string, int, or float.")
    query_single.update(query_dict.items())

    new_query = urlencode(list(query_single))

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


def format_response_result(
    response: Response,
    *,
    format_headers: bool | None = None,
    return_content: Literal["full", "content", "markdown"] = "full",
) -> str:
    """将HTTP响应格式化为字符串"""
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
            if not isinstance(content, str):
                content = content.decode('utf-8')
        except Exception as e:
            err_message = f"response content type is \"{content_type}\", cannot be converted to a string"
            raise ResponseError(response, err_message) from e
    else:
        err_message = f'response content type is "{content_type}", cannot be converted to a string'
        raise ResponseError(response, err_message)

    if content_type.startswith("text/html"):
        if return_content == "full":
            pass
        elif return_content == "content":
            content = remove_tag(content)
        elif return_content == "markdown":
            content = html_to_markdown(content)

    strs = []

    strs.append(f"{http_version} {status} {reason}\r\n")
    if format_headers:
        response_header_str = "\r\n".join(f"{k}: {v}" for k, v in headers)
        strs.append(response_header_str)
    strs.append("\r\n\r\n")
    strs.append(content + "\r\n")

    return "\r\n".join(strs)


def format_error_result(error: Exception):
    if isinstance(error, ArgumentError):
        return "HTTP/1.1 500 MCP Service Internal Error, invalid argument\r\n" \
            "Content-Type: text/plain\r\n\r\n" \
            f"MCP service found an error while checking parameters:\r\n" \
            f"{error.message}\r\n"
    elif isinstance(error, RequestError):
        return "HTTP/1.1 500 MCP Service Internal Error\r\n" \
            "Content-Type: text/plain\r\n\r\n" \
            "the MCP service encountered an internal error when making a request, with the following error message:\r\n" \
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
        return "HTTP/1.1 500 MCP Service Internal Error\r\n" \
            "Content-Type: text/plain\r\n\r\n" \
            "An unexpected error occurred in the MCP service." \



def mcp_http_request(
    method: str,
    url: str,
    *,
    query: Optional[dict] = None,
    data: Optional[dict] = None,
    json: Optional[dict] = None,
    headers: Optional[dict] = None,
    user_agent: Optional[str] = None,
    force_user_agnet: Optional[bool] = None,
    format_headers: bool = True,
    return_content: Literal["full", "content", "markdown"] = "full",
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

        return format_response_result(response, format_headers=format_headers, return_content=return_content)
    except Exception as e:
        return format_error_result(e)
