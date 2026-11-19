from typing import Optional, Literal

import click

from .server import create_mcp_server, format_response_result, get_user_agent
from .ua import list_ua_browsers, list_ua_oses
from .utils import parse
from .request import http_request, RequestError


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--user-agent", default=None, help='Specify user agent string directly')
@click.option(
    "--random-user-agent",
    is_flag=False,
    flag_value="",
    default=None,
    metavar="[browser=xxx;os=xxx]",
    help="Use a random user agent, optionally filtered by browser and os",
)
@click.option("--force-user-agent", is_flag=True, help="Force the use of specified or randomly generated UA, ignoring UA provided by the model")
@click.option('--list-os-and-browser', is_flag=True, help='List available browsers and operating systems for UA selection')
@click.option('--enable-fetch-to-file', is_flag=True, help='Enable the fetch_to_file tool (disabled by default)')
@click.option('--workspace', default=None, type=click.Path(), help='Writable directory that also serves as the base for relative paths in fetch_to_file')
@click.option('--writable-dir', 'allow_write_paths', multiple=True, type=click.Path(), help='Additional writable directory for fetch_to_file (repeatable)')
def main(
    context: click.Context,
    user_agent: Optional[str],
    random_user_agent: Optional[str],
    force_user_agent: Optional[bool],
    list_os_and_browser: bool,
    enable_fetch_to_file: bool,
    workspace: Optional[str],
    allow_write_paths: tuple[str, ...]
):
    if list_os_and_browser and context.invoked_subcommand:
        raise click.UsageError("Cannot use --list-os-and-browser with subcommand.")
    if user_agent is not None and random_user_agent is not None:
        raise click.UsageError("Cannot use both --user-agent and --random-user-agent.")

    if list_os_and_browser:
        click.echo("Available browsers:")
        for b in sorted(list_ua_browsers()):
            click.echo(f"- {b}")
        click.echo("Available operating systems:")
        for o in sorted(list_ua_oses()):
            click.echo(f"- {o}")
        return

    ua_random = False
    ua_os = None
    ua_browser = None
    if random_user_agent is not None:
        ua_random = True
        if random_user_agent:
            limit = parse(random_user_agent)
            ua_os = limit.get("os", None)
            ua_browser = limit.get("browser", None)

    try:
        effective_ua = get_user_agent(
            ua=user_agent,
            ua_random=ua_random,
            ua_os=ua_os,
            ua_browser=ua_browser,
        )
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e

    context.obj = {"ua": effective_ua}

    if context.invoked_subcommand:
        return

    mcp = create_mcp_server(
        ua=effective_ua,
        ua_random=False,
        ua_force=force_user_agent,
        enable_fetch_to_file=enable_fetch_to_file,
        workspace=workspace,
        allow_write_paths=allow_write_paths,
    )
    mcp.run(log_level="ERROR")


@main.command()
@click.pass_context
@click.argument("url", type=str, required=True)
@click.option("--return-content", type=click.Choice(['raw', 'basic_clean', 'strict_clean', 'markdown']), default="markdown", help="return content type")
@click.option("--timeout", type=float, default=30.0, show_default=True, help="request timeout in seconds")
def fetch(
    context: click.Context,
    url: str,
    return_content: Literal['raw'] | Literal['basic_clean'] | Literal['strict_clean'] | Literal['markdown'],
    timeout: float,
):
    ua = None
    if context.obj:
        ua = context.obj.get("ua")
    if not ua:
        ua = get_user_agent()

    try:
        response = http_request(
            "GET", url,
            query=None,
            headers={"User-Agent": ua},
            data=None,
            json_=None,
            timeout=timeout,
        )
        res = format_response_result(
            response,
            format_status=True,
            format_headers=False,
            format_content=True,
            return_content=return_content,
        )
    except RequestError as e:
        res = f"Error: {e.message}"
    except Exception as e:
        res = f"Error: {e}"
    click.echo(res)


@main.command(help="not implemented yet")
@click.argument("query", type=str, required=True)
def search(query):
    raise NotImplementedError("Search functionality is not implemented yet")


if __name__ == "__main__":
    main()
