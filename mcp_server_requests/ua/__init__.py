
from typing import Dict, List, Optional

import os
import json
import random

import click


FALLBACK_UA_LIST = [
    {"useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0",
     "type": "desktop", "browser": "Opera", "browser_version": "116.0.0", "os": "Windows", "os_version": "10", "platform": "Win32"},
    {"useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36", "type": "desktop",
     "browser": "Chrome", "browser_version": "134.0.0.0", "os": "Windows", "os_version": "10", "platform": "Win32"},
    {"useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
     "type": "desktop", "browser": "Edge", "browser_version": "133.0.0.0", "os": "Windows", "os_version": "10", "platform": "Win32"},
    {"useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0", "type": "desktop", "browser": "Firefox", "browser_version": "136.0", "os": "Windows", "os_version": "10", "platform": "Win32"},
    {"useragent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36", "type": "desktop", "browser": "Chrome", "browser_version": "133.0.0.0", "os": "Linux", "os_version": "", "platform": "Linux x86_64"},
    {"useragent": "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0", "type": "desktop", "browser": "Firefox", "browser_version": "125.0", "os": "Linux", "os_version": "", "platform": "Linux x86_64"},
]

REQUIRED_FIELDS = {
    'useragent',
    'type',
    'browser',
    'browser_version',
    'os',
    'os_version',
    'platform'
}


class UALoader:
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._data: Optional[List[Dict]] = None
        self._os_list: Optional[set[str]] = None
        self._browser_list: Optional[set[str]] = None

    @staticmethod
    def _valid(data: any) -> bool:
        return isinstance(data, dict) and all(isinstance(data.get(key, None), str) for key in REQUIRED_FIELDS)

    def _load_data(self) -> List[Dict]:
        items = []
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    try:
                        data = json.loads(line.strip())
                        if not UALoader._valid(data):
                            continue
                        items.append(data)
                    except json.JSONDecodeError:
                        continue
                return items
        except:
            return FALLBACK_UA_LIST

    @property
    def data(self) -> List[Dict]:
        if self._data is None:
            self._data = self._load_data()
        return self._data

    def oses(self) -> list[str]:
        if not self._os_list:
            self._os_list = {d["os"] for d in self.data}
        return list(self._os_list)

    def browsers(self) -> list[str]:
        if not self._browser_list:
            self._browser_list = {d["browser"] for d in self.data}
        return list(self._browser_list)

    def filter(self, *, browser: Optional[str] = None, os: Optional[str] = None) -> List[Dict]:
        browser = browser.lower() if browser else None
        os = os.lower() if os else None

        def cond(data: dict):
            return (not browser or data["browser"].lower() == browser) and (not os or data["browser"].lower() == os)

        filtered = [d for d in self.data if cond(d)]

        return filtered

    def random(self, *, browser: Optional[str] = None, os: Optional[str] = None) -> Dict | None:
        filtered = self.filter(browser=browser, os=os)
        if not filtered:
            return None
        return random.choice(filtered)

    def __len__(self) -> int:
        return len(self.data)


UA_FILE = os.path.join(os.path.dirname(__file__), 'ua.jsonl')
loader = UALoader(UA_FILE)


def random_ua(*, browser: Optional[str] = None, os: Optional[str] = None) -> str | None:
    item = loader.random(browser=browser, os=os)
    if item is None:
        return None
    return item["useragent"]


def list_ua_oses() -> list[str]:
    return loader.oses()


def list_ua_browsers() -> list[str]:
    return loader.browsers()


@click.command()
@click.option('--browser', "-b", help='Filter by browser type (e.g. Chrome, Edge, Firefox, Opera)')
@click.option('--os', help='Filter by operating system (e.g. Windows, Linux)')
@click.option('--list', "-l", is_flag=True, help='List all available browser types and operating systems')
def cli(browser: Optional[str], os: Optional[str], list: bool):
    if list:
        click.echo(f"User agents count: {len(loader)}")
        click.echo("Available browsers:")
        for b in sorted(list_ua_browsers()):
            click.echo(f"- {b}")
        click.echo("Available operating systems:")
        for o in sorted(list_ua_oses()):
            click.echo(f"- {o}")
        return

    try:
        ua = random_ua(browser=browser, os=os)
        if not ua:
            click.echo(f"No user agent found for browser={browser}, os={os}")
        click.echo(ua)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
