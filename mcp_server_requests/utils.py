
from typing import Iterable
import re

from bs4 import BeautifulSoup


def remove_tag(html: str, tags: Iterable[str] = ("script", "style", "meta", "link", "noscript")) -> str:
    tags = set(tags)
    soup = BeautifulSoup(html, "html.parser")
    for tag in tags:
        for element in soup.find_all(tag):
            element.decompose()
    return str(soup)


def simple_html_to_markdown(html: str, *, remove_tags: Iterable[str] = ("script", "style", "meta", "link", "noscript")) -> str:
    """Convert simple HTML to Markdown format.

    Supports:
    - Headings: h1-h6 -> # to ######
    - Paragraphs: p -> text with newlines
    - Links: a -> [text](url)
    - Images: img -> ![alt](src)
    - Lists: ul/ol/li -> */1. items
    - Code blocks: pre/code -> ```code```
    - Formatting: strong/b -> **bold**, em/i -> _italic_
    - Blockquotes: blockquote -> > quote
    - Horizontal rules: hr -> ---
    - Nested tags handling
    """
    soup = BeautifulSoup(html, "html.parser")
    markdown = []

    remove_tag_set = set(remove_tags)

    def process_element(element):
        if element.name is None:  # Text node
            return str(element).strip()
        if element.name in remove_tag_set:
            return ""

        children = "".join(process_element(child) for child in element.children)

        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(element.name[1])
            return f"{'#' * level} {children}\n\n"
        elif element.name == "p":
            return f"{children}\n\n"
        elif element.name == "a":
            href = element.get("href", "")
            return f"[{children}]({href})"
        elif element.name == "img":
            src = element.get("src", "")
            alt = element.get("alt", "")
            return f"![{alt}]({src})"
        elif element.name == "ul":
            items = []
            for li in element.find_all("li", recursive=False):
                items.append(f"* {process_element(li)}")
            return "\n".join(items) + "\n\n"
        elif element.name == "ol":
            items = []
            for i, li in enumerate(element.find_all("li", recursive=False), 1):
                items.append(f"{i}. {process_element(li)}")
            return "\n".join(items) + "\n\n"
        elif element.name == "pre":
            code = element.find("code")
            if code:
                return f"```\n{code.get_text()}\n```\n\n"
            return children
        elif element.name in ["strong", "b"]:
            return f" **{children}** "
        elif element.name in ["em", "i"]:
            return f" _{children}_ "
        elif element.name == "blockquote":
            return "> " + children.replace("\n", "\n> ") + "\n\n"
        elif element.name == "hr":
            return "---\n\n"
        elif element.name in ["div", "span"]:
            return children
        else:
            return children

    # Process top-level elements
    for element in soup.find_all(recursive=False):
        markdown.append(process_element(element))

    # Join and clean up extra newlines
    result = "".join(markdown)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


try:
    from markdownify import markdownify

    def html_to_markdown(html: str) -> str:
        return markdownify(html)
except ImportError:
    def html_to_markdown(html: str):
        return simple_html_to_markdown(html)


def parse(s: str) -> dict[str, str]:
    s = s.strip()
    if len(s) == 0:
        return {}
    # key1=val1;key2val2... -> dict
    return dict((k.strip(), v) for k, v in (item.split("=", 1) for item in s.split(";")) if k.strip())


if __name__ == "__main__":
    html1 = """
    <div>
        <script>alert('test')</script>
        <p>Content</p>
        <style>.cls{color:red}</style>
        <link>  </link>
        <noscript>Content</noscript> 
    </div>
    """

    html2 = '<b>Yay</b> <a href="http://github.com">GitHub</a>'

    print("==================================================")
    print("==================================================")
    print(remove_tag(html1))
    print("==================================================")
    print(html_to_markdown(html1))
    print("==================================================")
    print("==================================================")
    print(remove_tag(html2))
    print("==================================================")
    print(html_to_markdown(html2))
