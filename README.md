[中文](README-zh.md)

-----

# mcp-server-requests

An MCP server that provides HTTP request capabilities, enabling LLMs to fetch and process web content.

## Features

- **fetch**: Web content fetching tool
  - Supports converting web content to Markdown format
  - Supports filtering web content (non-visual elements like script, style, meta)
  - Feeds into LLM context, reducing token consumption through Markdown conversion or filtering non-visual elements
- **fetch_to_file**: Web content saving tool
  - Disabled by default; enable it with `--enable-fetch-to-file`
  - File writes are limited to the configured writable directories, controlled by `--workspace` and `--writable-dir`
  - Web content is not fed into LLM context, avoiding excessive token consumption
- **http_request**: Generic HTTP request tool
  - Full HTTP method support (GET, POST, PUT, PATCH, DELETE)
  - Supports custom request headers
  - Supports text and JSON request bodies
  - Returns complete HTTP response information (status, headers, body) for LLMs
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
- `--workspace PATH`: Writable directory that also serves as the base for relative paths
- `--writable-dir PATH`: Additional writable directory for `fetch_to_file` (repeatable)

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
  - When `--force-user-agent` is enabled: Force using command-line specified User-Agent (via `--user-agent` or `--random-user-agent`)
  - When `--force-user-agent` is disabled:
    - If LLM provides User-Agent in `headers`, use the LLM-provided one
    - Otherwise use command-line specified User-Agent
  - If none specified, use default User-Agent: `Mozilla/5.0 (compatible; mcp-server-requests/{version})`

- `fetch_to_file` is disabled by default and is not registered as an MCP tool, so the model cannot see it. Enable it with `--enable-fetch-to-file`.
- Writable roots define the scope `fetch_to_file` can write to: the `--workspace` directory plus every `--writable-dir` directory:
  - `--workspace` is the base for relative paths. Relative paths are rejected when no workspace is configured.
  - `--writable-dir` adds extra writable directories on top of `--workspace`.
  - `file_path` may be absolute or relative, but the resolved file must be inside one of the writable roots.
  - Writable roots must be directories. Missing directories are created when the tool is first used.
- System directories such as `/etc` and `C:\Windows` are always denied.

---

### 1. **fetch - Fetch Web Content**

The fetch subcommand is equivalent to the MCP `fetch` tool functionality, used to demonstrate fetch capabilities.

```bash
python -m mcp_server_requests fetch <URL> [--return-content {raw,basic_clean,strict_clean,markdown}]
```

**Options:**
- `--return-content`: Return content type (default: markdown)
  - **raw**: Return raw unprocessed HTML content (includes response headers)
  - **basic_clean**: Basic cleanup, removing non-display tags (script, style, meta, etc.) while preserving structure
  - **strict_clean**: Strict cleanup, removing non-display tags and most HTML attributes, keeping only essential structure
  - **markdown**: Convert HTML to clean Markdown format

---

## Functionality

### MCP Tool Details

#### 1. **fetch** - Fetch Web Content
Fetch content from the specified URL and return it in the specified format.

**Parameters:**
- **url** (required, string): Target URL, supports HTTP/HTTPS protocols
- **return_content** (optional, enum): Content processing format, defaults to "markdown"
  - `"raw"`: Return raw HTML content with complete HTTP response headers
  - `"basic_clean"`: Basic cleanup, removing non-display tags (script, style, meta, etc.) while preserving HTML structure
  - `"strict_clean"`: Strict cleanup, removing non-display tags and most HTML attributes, keeping only essential structure
  - `"markdown"`: Convert HTML content to clean Markdown format

**Returns:** Content processed according to the specified format

---

#### 2. **fetch_to_file** - Fetch Web Content and Save to File
Fetch content from the specified URL and save it to a file.

**Parameters:**
- **url** (required, string): Target URL
- **file_path** (required, string): File save path
  - Absolute paths must be inside one of the writable roots
  - Relative paths are resolved against `--workspace` and must stay inside a writable root
- **return_content** (optional, enum): Content processing format, defaults to "markdown", same options as fetch tool

**Features:**
- Disabled by default; enable with `--enable-fetch-to-file`
- Writes outside the configured writable roots are rejected
- Automatically creates parent directories for nested paths
- All files saved with UTF-8 encoding

**Returns:** Operation result or error message

---

#### 3. **http_request** - Generic HTTP Request Tool
Send HTTP requests using any method and get complete responses.

**Parameters:**
- **url** (required, string): Target URL
- **method** (optional, enum): HTTP method, defaults to "GET"
  - `"GET"`, `"POST"`, `"PUT"`, `"PATCH"`, `"DELETE"`
- **query** (optional, object): URL query parameters as key-value pairs, automatically URL-encoded
- **headers** (optional, object): Custom HTTP request headers
- **data** (optional, string): Text format request body data, mutually exclusive with json parameter
- **json** (optional, any type): JSON format request body data, mutually exclusive with data parameter

**Parameter Constraints:**
- `data` and `json` parameters cannot be used together
- When using `json` parameter, `Content-Type: application/json` is automatically set
- When using `data` parameter, it's recommended to manually set appropriate `Content-Type`

**Returns:** Complete HTTP response (status line, response headers, and response body)

---

**Note**: Individual HTTP method tools (http_get, http_post, http_put, http_patch, http_delete) have been removed and replaced by the unified **http_request** tool.

## License
MIT