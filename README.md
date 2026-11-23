[中文](README-zh.md)

-----

# mcp-server-requests

An MCP server that provides HTTP request capabilities, enabling LLMs to fetch and process web content.

## Features

- **fetch**: Generic HTTP request tool
  - Fetches web content with GET by default, and sends POST/PUT/PATCH/DELETE requests
  - Supports custom request headers, text and JSON request bodies
  - Returns complete HTTP response information (status, headers, body) for LLMs
  - Supports converting web content to Markdown format
  - Supports filtering web content (non-visual elements like script, style, meta)
  - Feeds into LLM context, reducing token consumption through Markdown conversion or filtering non-visual elements
- **fetch_to_file**: Web content saving tool
  - Disabled by default; enable it with `--enable-fetch-to-file`
  - Supports the same request capabilities as fetch (method, headers, body, json_body)
  - File writes are limited to the configured writable directories, controlled by `--workspace` and `--writable-dir`
  - Web content is not fed into LLM context, avoiding excessive token consumption
- Supports custom User-Agent
- Supports random User-Agent generation

## Installation

```bash
git clone https://github.com/coucya/mcp-server-requests.git
cd mcp-server-requests
pip install .
```

Requires Python 3.11 or newer.

## Usage

### MCP Server Configuration

Basic usage:
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

Advanced usage (enable `fetch_to_file`; add writable directories with `--workspace` or `--writable-dir`):
```json
{
    "mcpServers": {
        "mcp-server-requests": {
            "command": "python",
            "args": [
                "-m",
                "mcp_server_requests",
                "--enable-fetch-to-file",
                "--workspace",
                "/home/user/project",
                "--writable-dir",
                "/home/user/downloads",
                "--writable-dir",
                "/home/user/notes"
            ]
        }
    }
}
```

### Command Line

### 0. **Start MCP Server**

Start the MCP server directly:

```bash
python -m mcp_server_requests
```

#### Options
- `--user-agent TEXT`: Specify custom User-Agent string
- `--random-user-agent [browser=xxx;os=xxx]`: Use randomly generated User-Agent
- `--force-user-agent`: Force using command line specified User-Agent, ignoring LLM provided UA
- `--list-os-and-browser`: List available browsers and OS for random User-Agent generation
- `--enable-fetch-to-file`: Enable the `fetch_to_file` tool (disabled by default)
- `--workspace PATH`: Writable directory that also serves as the base for relative paths. Only absolute paths are used; relative paths are ignored.
- `--writable-dir PATH`: Additional writable directory for `fetch_to_file` (repeatable). Only absolute paths are used; relative paths are ignored.

#### Option Details
- `--user-agent` and `--random-user-agent` are mutually exclusive and cannot be used together
- User-Agent setup methods:
  - Custom string: `--user-agent "Mozilla/5.0 (...)"`
  - Fully random: `--random-user-agent`
  - Conditional random generation:
    - Specify browser type: `--random-user-agent browser=chrome`
    - Specify OS: `--random-user-agent os=windows`
    - Both browser and OS: `--random-user-agent browser=chrome;os=windows`
    - Note: Browser and OS parameters are case insensitive

- Use `--list-os-and-browser` to view available browsers and OS for `--random-user-agent`.

- `--force-user-agent` option controls User-Agent priority:
  - When `--force-user-agent` is enabled: Force using command-line specified User-Agent (via `--user-agent` or `--random-user-agent`); existing User-Agent keys in `headers` (case-insensitive) are replaced
  - When `--force-user-agent` is disabled:
    - If LLM provides User-Agent in `headers` (key matching is case-insensitive), use the LLM-provided one
    - Otherwise use command-line specified User-Agent
  - If none specified, use default User-Agent: `Mozilla/5.0 (compatible; mcp-server-requests/{version})`
- `--force-user-agent` only affects the `fetch` tool; `fetch_to_file` always uses the server User-Agent

- `fetch_to_file` is disabled by default and is not registered as an MCP tool, so the model cannot see it. Enable it with `--enable-fetch-to-file`.
- Writable roots define the scope `fetch_to_file` can write to: the `--workspace` directory plus every `--writable-dir` directory:
  - `--workspace` is the base for relative paths. Relative paths are rejected when no workspace is configured.
  - `--writable-dir` adds extra writable directories on top of `--workspace`.
  - `file_path` may be absolute or relative, but the resolved file must be inside one of the writable roots.
  - Writable roots must be directories. Missing directories are created when the tool is first used.
  - Only absolute `--workspace` and `--writable-dir` paths are used. Relative paths are ignored.
- Existing files are never overwritten. If the target already exists, the tool returns an error and writes nothing.
- Symlinks are resolved before the containment check. The final target must be inside a writable root.
- HTTP 4xx/5xx response bodies are saved like any other response body.
- System directories such as `/etc` and `C:\Windows` are always denied. User-level sensitive paths are denied as well: `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.config/autostart`, shell startup files such as `~/.bashrc` and `~/.zshrc`, and the Windows Startup folder.
- The `.git` and `.husky` directories inside every writable root are denied, so fetched content cannot install git hooks.
- `fetch_to_file` only writes text content. Non-text responses return an error and no file is created.

---

### 1. **fetch - Generic HTTP Request**

The fetch subcommand is equivalent to the MCP `fetch` tool functionality, used to demonstrate request capabilities in the terminal.

```bash
python -m mcp_server_requests fetch <URL> \
  [-X {GET,POST,PUT,PATCH,DELETE}] \
  [-H "Name: value"]... \
  [-d TEXT] \
  [--json-body JSON] \
  [--return-format {raw,basic_clean,strict_clean,markdown}] \
  [--timeout SECONDS]
```

**Options:**
- `-X, --method`: HTTP method (default: GET)
- `-H, --header`: Custom request header in `"Name: value"` format (repeatable)
- `-d, --body`: Text request body; cannot be used with `--json-body`
- `--json-body`: JSON request body; cannot be used with `--body`
- `--return-format`: Return content format (default: markdown)
  - **raw**: Return raw unprocessed HTML content
  - **basic_clean**: Basic cleanup, removing non-display tags (script, style, meta, etc.) while preserving structure
  - **strict_clean**: Strict cleanup, removing non-display tags and most HTML attributes, keeping only essential structure
  - **markdown**: Convert HTML to clean Markdown format
- `--timeout`: Request timeout in seconds (default: 30)

**Examples:**

```bash
# Fetch a web page as markdown
python -m mcp_server_requests fetch https://example.com

# Query parameters directly in the URL
python -m mcp_server_requests fetch "https://api.example.com/search?q=test&limit=10"

# POST JSON
python -m mcp_server_requests fetch https://api.example.com/users \
  -X POST -H "Authorization: Bearer token" --json-body '{"name": "John"}'

# Custom User-Agent
python -m mcp_server_requests fetch https://example.com -H "user-agent: My-Agent"
```

---

## Functionality

### MCP Tool Details

#### 1. **fetch** - Generic HTTP Request
Fetch web content, or send a request with any HTTP method and get the complete response.

**Parameters:**
- **url** (required, string): Target URL, supports HTTP/HTTPS protocols
- **method** (optional, enum): HTTP method, defaults to "GET"
  - `"GET"`, `"POST"`, `"PUT"`, `"PATCH"`, `"DELETE"`
- **headers** (optional, object): Custom HTTP request headers
- **body** (optional, string): Text format request body data, mutually exclusive with json_body parameter
- **json_body** (optional, any type): JSON format request body data, mutually exclusive with body parameter
- **return_format** (optional, enum): HTML content processing format, defaults to "markdown"
  - `"raw"`: Return raw HTML content
  - `"basic_clean"`: Basic cleanup, removing non-display tags (script, style, meta, etc.) while preserving HTML structure
  - `"strict_clean"`: Strict cleanup, removing non-display tags and most HTML attributes, keeping only essential structure
  - `"markdown"`: Convert HTML content to clean Markdown format
- **timeout** (optional, number): Request timeout in seconds, defaults to 30. Use `null` for no timeout.

**Parameter Constraints:**
- `body` and `json_body` parameters cannot be used together
- When using `json_body` parameter, `Content-Type: application/json` is automatically set
- When using `body` parameter, it's recommended to manually set appropriate `Content-Type`
- `return_format` only affects `text/html` responses; JSON and other text responses are returned as-is
- Write query parameters directly in the URL, for example `https://api.example.com/search?q=test&limit=10`. Do not pre-encode; Chinese characters and spaces are encoded by the server

**Returns:** Complete HTTP response (status line, response headers, and response body)

---

#### 2. **fetch_to_file** - Fetch Web Content or Send a Request and Save to a File
Fetch content from the specified URL, or send any HTTP request, and save the response body to a file.

**Parameters:**
- **url** (required, string): Target URL
- **file_path** (required, string): File save path
  - Absolute paths must be inside one of the writable roots
  - Relative paths are resolved against `--workspace` and must stay inside a writable root
- **method** (optional, enum): HTTP method, defaults to "GET"
  - `"GET"`, `"POST"`, `"PUT"`, `"PATCH"`, `"DELETE"`
- **headers** (optional, object): Custom HTTP request headers
- **body** (optional, string): Text format request body data, mutually exclusive with json_body parameter
- **json_body** (optional, any type): JSON format request body data, mutually exclusive with body parameter
- **return_format** (optional, enum): HTML content processing format, defaults to "markdown", same options as fetch tool
- **timeout** (optional, number): Request timeout in seconds, defaults to 30. Use `null` for no timeout.

**Parameter Constraints:**
- `body` and `json_body` parameters cannot be used together
- When using `json_body` parameter, `Content-Type: application/json` is automatically set
- When using `body` parameter, it's recommended to manually set appropriate `Content-Type`
- `return_format` only affects `text/html` responses; JSON and other text responses are saved as-is
- Write query parameters directly in the URL; do not pre-encode values
- Request behavior is the same as the `fetch` tool, including User-Agent rules

**Features:**
- Disabled by default; enable with `--enable-fetch-to-file`
- Writes outside the configured writable roots are rejected
- Path validation happens before the request; invalid paths never trigger a request
- Existing files are never overwritten
- Automatically creates parent directories for nested paths
- All files saved with UTF-8 encoding
- HTTP 4xx/5xx response bodies are written to the file like normal responses
- Symlinks are resolved before the containment check
- Only the response body is written; status line and headers are omitted

**Returns:** Operation result or error message

---

**Note**: The `http_request` tool and the individual HTTP method tools (http_get, http_post, http_put, http_patch, http_delete) from earlier versions have been merged into the **fetch** tool.

## License
MIT