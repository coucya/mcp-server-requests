from typing import Dict, Any, Optional, Literal

from mcp.server.fastmcp import FastMCP

from .request import mcp_http_request


def create_mcp_server() -> FastMCP:
    mcp = FastMCP("Fatch", description="HTTP 请求服务，用于获取 web 内容。", log_level="ERROR")

    @mcp.tool()
    def fatch(url: str, *, return_content: Literal["full", "content", "markdown"] = "markdown") -> str:
        """获取网页内容。
        - 如果是 HTML, 则根据 returm 返回合适的内容，
        - 如果不是 HTML，但是是 Text 类型的内容，则直接返回其内容。
        - 如果是其它类型的内容，则返回错误信息。

        Args:
            url (str): 要获取的网页 URL。
            return_content ("full" | "content" | "markdown", optional): 默认为 "markdown"，用于控制返回 html 内容的方式，
                - 如果为 full，返回完整 HTML 内容。
                - 如果为 content，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等。
                - 如果为 markdown，HTML 转换为 Markdown 后返回。

        Returns:
            - 如果参数 return_content 为 full，返回完整 HTML 内容。
            - 如果参数 return_content 为 content，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等。
            - 如果参数 return_content 为 markdown，HTML 转换为 Markdown 后返回。
        """
        return mcp_http_request("GET", url, return_content=return_content, format_headers=False)

    @mcp.tool()
    def http_get(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """执行 HTTP GET 请求。

        Args:
            url (str): 请求的目标 URL。
            query (Dict[str, str | int | float], optional): 可选参数，查询参数键值对。参数值会自动转换为字符串，并且会拼接到 url 里。
                例如: {'key1': 'value1', 'key2': 2}会被转换为key1=value1&key2=2，并拼接到 url。
            headers (Dict[str, str], optional): 可选参数，自定义的 http 请求头。

        Returns:
            str: 标准HTTP响应格式的字符串，包含状态行、响应头和响应体。
        """
        return mcp_http_request("GET", url, query=query, headers=headers)

    @mcp.tool()
    def http_post(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """执行 HTTP POST 请求。

        Args:
            url (str): 请求的目标 URL。
            query (Dict[str, str | int | float], optional): 可选参数，查询参数键值对。参数值会自动转换为字符串，并且会拼接到 url 里。
                例如: {'key1': 'value1', 'key2': 2}会被转换为key1=value1&key2=2，并拼接到 url。
            headers (Dict[str, str], optional): 可选参数，自定义的 http 请求头。
            data (str, optional): 可选参数，要发送的 http 请求体数据，必须是文本，data 和 json 参数不能同时使用。
            json (Any, optional): 可选参数，要发送的 http 请求体数据，以 JSON 数据，会自动序列化为JSON字符串，data 和 json 参数不能同时使用。

        Returns:
            str: 标准HTTP响应格式的字符串，包含状态行、响应头和响应体。
        """
        return mcp_http_request("POST", url, query=query, data=data, json=json, headers=headers)

    @mcp.tool()
    def http_put(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """执行 HTTP PUT 请求。

        Args:
            url (str): 请求的目标 URL。
            query (Dict[str, str | int | float], optional): 查询参数键值对。参数值会自动转换为字符串，并且会拼接到 url 里。
                例如: {'key1': 'value1', 'key2': 2}会被转换为key1=value1&key2=2，并拼接到 url。
            headers (Dict[str, str], optional): 可选参数，自定义的 http 请求头。
            data (str, optional): 可选参数，要发送的 http 请求体数据，必须是文本，data 和 json 参数不能同时使用。
            json (Any, optional): 可选参数，要发送的 http 请求体数据，以 JSON 数据，会自动序列化为JSON字符串，data 和 json 参数不能同时使用。

        Returns:
            str: 标准HTTP响应格式的字符串，包含状态行、响应头和响应体。
        """
        return mcp_http_request("PUT", url, query=query, data=data, json=json, headers=headers)

    @mcp.tool()
    def http_patch(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """执行H TTP PATCH 请求。

        Args:
            url (str): 请求的目标 URL。
            query (Dict[str, str | int | float], optional): 查询参数键值对。参数值会自动转换为字符串，并且会拼接到 url 里。
                例如: {'key1': 'value1', 'key2': 2}会被转换为key1=value1&key2=2，并拼接到 url。
            headers (Dict[str, str], optional): 可选参数，自定义的 http 请求头。
            data (str, optional): 可选参数，要发送的 http 请求体数据，必须是文本，data 和 json 参数不能同时使用。
            json (Any, optional): 可选参数，要发送的 http 请求体数据，以 JSON 数据，会自动序列化为JSON字符串，data 和 json 参数不能同时使用。

        Returns:
            str: 标准HTTP响应格式的字符串，包含状态行、响应头和响应体。
        """
        return mcp_http_request("PATCH", url, query=query, data=data, json=json, headers=headers)

    @mcp.tool()
    def http_delete(
        url: str,
        *,
        query: Optional[Dict[str, str | int | float]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        json: Optional[Any] = None,
    ) -> str:
        """执行 HTTP DELETE 请求。

        Args:
            url (str): 请求的目标 URL。
            query (Dict[str, str | int | float], optional): 查询参数键值对。参数值会自动转换为字符串，并且会拼接到 url 里。
                例如: {'key1': 'value1', 'key2': 2}会被转换为key1=value1&key2=2，并拼接到 url。
            headers (Dict[str, str], optional): 可选参数，自定义的 http 请求头。
            data (str, optional): 可选参数，要发送的 http 请求体数据，必须是文本，data 和 json 参数不能同时使用。
            json (Any, optional): 可选参数，要发送的 http 请求体数据，以 JSON 数据，会自动序列化为JSON字符串，data 和 json 参数不能同时使用。

        Returns:
            str: 标准HTTP响应格式的字符串，包含状态行、响应头和响应体。
        """
        return mcp_http_request("DELETE", url, query=query, data=data, json=json, headers=headers)

    return mcp


def main():
    mcp = create_mcp_server()
    mcp.run()


if __name__ == "__main__":
    main()
