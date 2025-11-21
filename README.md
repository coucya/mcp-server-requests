[中文](README-zh.md)

-----

# mcp-server-requests

An MCP server that provides HTTP request capabilities, enabling LLMs to fetch and process web content.

## Features
- Supports converting web content to Markdown format
- Supports filtering out content useless for LLMs
- Supports custom User-Agent headers
- Supports random User-Agent headers
- Supports custom request headers in HTTP requests
- Supports full HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Supports writing web page content to files
- LLMs can access complete HTTP response header information

## Installation

```bash
git clone https://github.com/coucya/mcp-server-requests.git
cd mcp-server-requests
pip install .
```

## Usage

### MCP Server Configuration

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
- `--use-root`: Enable workspace root support for file operations (requires MCP Client with `root` capability support)
- `--allow-external-file-access`: Allow file operations outside workspace (only with --use-root)

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

- `--use-root` enables file operations relative to workspace root:
  - **Prerequisite**: Requires MCP Client with `root` capability support
  - When enabled: `fetch_to_file` allows absolute paths or relative paths, relative paths are relative to workspace root
  - When disabled: `fetch_to_file` must use absolute paths, files are saved to specified absolute path locations
- `--allow-external-file-access`: Controls whether file operations outside workspace are allowed (only usable with --use-root)
  - **Prerequisite**: Requires `--use-root` to be enabled, this option has no effect if `--use-root` is not enabled
  - When enabled: `fetch_to_file` can operate on files outside the workspace directory
  - When disabled: `fetch_to_file` can only operate on files within the workspace directory, even if absolute paths are provided, files outside the workspace cannot be operated on

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

**Returns:** String - Content processed according to the specified format

---

#### 2. **fetch_to_file** - Fetch Web Content and Save to File
Fetch content from the specified URL and save it to a file.

**Parameters:**
- **url** (required, string): Target URL
- **file_path** (required, string): File save path
  - When `--use-root` is enabled: Must be a **relative path** (relative to workspace root)
  - When `--use-root` is disabled: Must be an **absolute path**
- **return_content** (optional, enum): Content processing format, defaults to "markdown", same options as fetch tool

**Features:**
- Automatically creates parent directories for nested paths
- All files saved with UTF-8 encoding
- When `--use-root` is enabled, can work with `--allow-external-file-access` to control file access scope

**Returns:** String - Operation result or error message

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

**Returns:** String - Complete HTTP response (status line, response headers, and response body)

---

**Note**: Individual HTTP method tools (http_get, http_post, http_put, http_patch, http_delete) have been removed and replaced by the unified **http_request** tool.

## License
MIT