
[中文](README-zh.md)

---

# mcp-server-requests

MCP service for HTTP requests, enabling LLMs to read web content.

Features:
- Supports converting web pages to Markdown
- Filters out irrelevant content (for LLMs)
- Supports custom User-Agent
- Supports random User-Agent
- Supports setting request headers in HTTP requests
- Supports multiple HTTP methods (GET, POST, PUT, DELETE, PATCH)
- LLMs can read response headers

## Installation

```bash
git clone github.com/coucya/mcp-server-requests.git
cd mcp-server-requests
pip install .
```

## Usage

### mcp server

```json
{
    "mcpServers": {
        "mcp-server-requests": {
            "command": "python",
            "args": [
                "-m",
                "mcp_server_requests"
            ]
        }
    }
}
```

### Command Line

- Command line implementation is not yet complete

---

### 0. **Start MCP Service**

starts the MCP service directly

```bash
python -m mcp_server_requests
```

Options:
- `--user-agent TEXT`: Specify custom **User-Agent**
- `--random-user-agent [browser=xxx;os=xxx]`: Use random **User-Agent**
- `--force-user-agent`: Force using specified or randomly generated UA, ignoring UA provided by model
- `--list-os-and-browser`: List available browsers and operating systems for UA selection

Option notes:
- `--user-agent` and `--random-user-agent` cannot be used together
- User-Agent can be set in following ways:
  - Custom User-Agent (`--user-agent "Mozilla/5.0 (...)"`)
  - Random generation (`--random-user-agent`)
  - Specify browser and OS
    - Random chrome **User-Agent** (`--random-user-agent browser=chrome`)
    - Random windows **User-Agent** (`--random-user-agent os=windows`)
    - Random chrome + windows **User-Agent** (`--random-user-agent browser=chrome;os=windows`)
    - `--random-user-agent` is case-insensitive when specifying os and browser

- Use `--list-os-and-browser` to see available browsers and OS for `--random-user-agent`

- `--force-user-agent` controls whether to use User-Agent specified in **header** parameter when LLM calls tools:
  - When using `--force-user-agent` and LLM specifies User-Agent in **header**, 
    the LLM-specified User-Agent will be ignored, replaced by command line specified one (`--user-agent`, `--random-user-agent` or default)
  - When not using `--force-user-agent` and LLM specifies User-Agent in **header**,
    use LLM-specified User-Agent
  - Otherwise, use command line specified one (`--user-agent`, `--random-user-agent` or default)

---

#### 1. **fetch - Fetch web content**
fetch subcommand has same functionality as fetch tool, can demonstrate fetch features.

```bash
python -m mcp_server_requests fetch <URL> [--return-content {raw,basic_clean,strict_clean,markdown}]
```

Options:
- `--return-content`: Return content type (default: markdown)
  - **raw**, returns raw HTML content
  - **basic_clean**, returns filtered HTML content, removing non-display tags like script, style etc.
  - **strict_clean**, returns filtered HTML content, removing non-display tags and most useless HTML attributes
  - **markdown**, converts HTML to Markdown then returns

Example:
```
python -m mcp_server_requests fetch https://example.com
```

---

#### 2. **get - Execute HTTP GET request**
get subcommand has same functionality as http_get tool, can demonstrate http_get features.

```bash
python -m mcp_server_requests get <URL> [--headers HEADERS]
```

Options:
- `--headers`: Custom headers (format: "key1=value1;key2=value2")

---

#### 3. **post - Execute HTTP POST request**
post subcommand has same functionality as http_post tool, can demonstrate http_post features.

```bash
python -m mcp_server_requests post <URL> [--headers HEADERS] [--data TEXT]
```

Options:
- `--headers`: Custom headers
- `--data`: Request body data

---

#### 4. **put - Execute HTTP PUT request**
put subcommand has same functionality as http_put tool, can demonstrate http_put features.

```bash
python -m mcp_server_requests put <URL> [--headers HEADERS] [--data TEXT]
```

Options: Same as POST

---

#### 5. **delete - Execute HTTP DELETE request**
delete subcommand has same functionality as http_delete tool, can demonstrate http_delete features.

```bash
python -m mcp_server_requests delete <URL> [--headers HEADERS] [--data TEXT]
```

Options: Same as POST

## Features

### Available Tools

1. **fetch** - Fetch web content
  - Parameters:
    - **url** (required): Target URL
    - **return_content** (optional): Return content type ('raw', 'basic_clean', 'strict_clean', 'markdown')
      - **raw**, returns raw HTML content
      - **basic_clean**, returns filtered HTML content, removing non-display tags like script, style etc.
      - **strict_clean**, returns filtered HTML content, removing non-display tags and most useless HTML attributes
      - **markdown**, converts HTML to Markdown then returns

2. **http_get** - Execute HTTP GET request
  - Parameters:
    - **url** (required): Target URL
    - **query** (optional): Query parameter key-value pairs
    - **headers** (optional): Custom headers
      - LLM may specify User-Agent in headers, whether to use it is controlled by `--force-user-agent` (same for other tools)

3. **http_post** - Execute HTTP POST request
  - Parameters:
    - **url** (required): Target URL
    - **query** (optional): Query parameter key-value pairs
    - **headers** (optional): Custom headers
    - **data** (optional): Request body data (text)
    - **json** (optional): Request body data (JSON)
    - **data** and **json** cannot be used together

4. **http_put** - Execute HTTP PUT request
  - Parameters: Same as http_post

5. **http_patch** - Execute HTTP PATCH request
  - Parameters: Same as http_post

6. **http_delete** - Execute HTTP DELETE request
  - Parameters: Same as http_post

## License
MIT