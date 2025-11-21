from typing import Optional, Literal

import click

from .server import create_mcp_server
from .ua import list_ua_browsers, list_ua_oses
from .utils import parse
from .request import mcp_http_request


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--user-agent", default=None, help='Specify user agent string directly')
@click.option("--random-user-agent", is_flag=True, flag_value=True, default=None, help="Use a random user agent,")
@click.option("--force-user-agent", is_flag=True, help="Force the use of specified or randomly generated UA, ignoring UA provided by the model")
@click.option('--list-os-and-browser', is_flag=True, help='List available browsers and operating systems for UA selection')
def main(
    context: click.Context,
    user_agent: Optional[str],
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
def fetch(
    url: str,
    return_content: Literal['raw'] | Literal['basic_clean'] | Literal['strict_clean'] | Literal['markdown']
):
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
