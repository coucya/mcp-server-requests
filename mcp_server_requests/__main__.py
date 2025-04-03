from typing import Dict, Any, Optional, Literal

import click
from mcp.server.fastmcp import FastMCP

from .version import __version__
from .request import mcp_http_request
from .ua import list_ua_browsers, list_ua_oses, random_ua
from .utils import parse


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


def create_mcp_server(
    *,
    ua: str | None = None,
    ua_random: bool = False,
    ua_os: str | None = None,
    ua_browser: str | None = None,
    ua_force: bool | None = None,
) -> FastMCP:

    mcp = FastMCP("Requests", description="HTTP 请求服务，用于获取 web 内容。", log_level="ERROR")

    ua = get_user_agent(ua=ua, ua_random=ua_random, ua_os=ua_os, ua_browser=ua_browser)

    @mcp.tool()
    def fetch(url: str, *, return_content: Literal['raw', 'basic_clean', 'strict_clean', 'markdown'] = "markdown") -> str:
        """获取网页内容。
        - 如果是 HTML, 则根据 returm 返回合适的内容，
        - 如果不是 HTML，但是是 Text 或 Json 内容，则直接返回其内容。
        - 如果是其它类型的内容，则返回错误信息。

        Args:
            url (str): 要获取的网页 URL。
            return_content ("raw" | "basic_clean" | "strict_clean" | "markdown", optional): 默认为 "markdown"，用于控制返回 html 内容的方式，
                - 如果为 raw，返回原始 HTML 内容。
                - 如果为 basic_clean，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等。
                - 如果为 strict_clean，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等，并且会删除大部分无用的 HTML 属性。
                - 如果为 markdown，HTML 转换为 Markdown 后返回。

        Returns:
            - 如果 return_content 为 raw，返回原始 HTML 内容。
            - 如果 return_content 为 basic_clean，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等。
            - 如果 return_content 为 strict_clean，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等，并且会删除大部分无用的 HTML 属性。
            - 如果 return_content 为 markdown，HTML 转换为 Markdown 后返回。
        """
        return mcp_http_request("GET", url, return_content=return_content, user_agent=ua, force_user_agnet=ua_force, format_headers=False)

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
        return mcp_http_request("GET", url, query=query, headers=headers, user_agent=ua, force_user_agnet=ua_force)

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
        return mcp_http_request("POST", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

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
        return mcp_http_request("PUT", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

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
        return mcp_http_request("PATCH", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

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
        return mcp_http_request("DELETE", url, query=query, data=data, json=json, headers=headers, user_agent=ua, force_user_agnet=ua_force)

    return mcp


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--user-agent", is_flag=True, flag_value=True, default=None, help='Specify user agent string directly')
@click.option("--random-user-agent", is_flag=True, flag_value=True, default=None, help="Use a random user agent,")
@click.option("--force-user-agent", is_flag=True, help="Force the use of specified or randomly generated UA, ignoring UA provided by the model")
@click.option('--list-os-and-browser', is_flag=True, help='List available browsers and operating systems for UA selection')
def main(
    context: click.Context,
    user_agent: Optional[str | bool],
    random_user_agent: Optional[str],
    force_user_agent: Optional[bool],
    list_os_and_browser: bool
):
    if list_os_and_browser and context.invoked_subcommand:
        raise ValueError("Cannot use --list-os-and-browser with subcommand.")
    if user_agent and random_user_agent:
        raise ValueError("Cannot use both --user-agent and --random-user-agent.")

    if list_os_and_browser:
        click.echo("Available browsers:")
        for b in sorted(list_ua_browsers()):
            click.echo(f"- {b}")
        click.echo("Available operating systems:")
        for o in sorted(list_ua_oses()):
            click.echo(f"- {o}")
        return

    if context.invoked_subcommand:
        pass
    else:
        ua_random = False
        ua_os = None
        ua_browser = None
        if isinstance(random_user_agent, str):
            limit = parse(random_user_agent)
            ua_random = True
            ua_os = limit.get("os", None)
            ua_browser = limit.get("browser", None)

        mcp = create_mcp_server(
            ua=user_agent,
            ua_random=ua_random,
            ua_os=ua_os,
            ua_browser=ua_browser,
            ua_force=force_user_agent,
        )
        mcp.run()


@main.command()
@click.argument("url", type=str, required=True)
@click.option("--return-content", type=click.Choice(['raw', 'basic_clean', 'strict_clean', 'markdown']), default="markdown", help="return content type")
def fetch(url: str, return_content: str):
    res = mcp_http_request("GET", url, format_headers=False, return_content=return_content)
    click.echo(res)


@main.command()
@click.argument("url", type=str, required=True)
@click.option("--headers", type=str, default="", help="custom headers")
def get(url: str, headers: str):
    hs = parse(headers)
    res = mcp_http_request("GET", url, headers=hs)
    click.echo(res)


@main.command()
@click.argument("url", type=str, required=True)
@click.option("--headers", type=str, default="", help="custom headers")
@click.option("--data", type=str)
def post(url: str, headers: str, data: str | None):
    hs = parse(headers)
    res = mcp_http_request("POST", url, headers=hs, data=data)
    click.echo(res)


@main.command()
@click.argument("url", type=str, required=True)
@click.option("--headers", type=str, default="", help="custom headers")
@click.option("--data", type=str)
def put(url: str, headers: str, data: str | None):
    hs = parse(headers)
    res = mcp_http_request("PUT", url, headers=hs, data=data)
    click.echo(res)


@main.command()
@click.argument("url", type=str, required=True)
@click.option("--headers", type=str, default="", help="custom headers")
@click.option("--data", type=str)
def delete(url: str, headers: str, data: str | None):
    hs = parse(headers)
    res = mcp_http_request("DELETE", url, headers=hs, data=data)
    click.echo(res)


@main.command(help="not implemented yet")
@click.argument("query", type=str, required=True)
def search(query):
    raise NotImplementedError("Search functionality is not implemented yet")


if __name__ == "__main__":
    main()
