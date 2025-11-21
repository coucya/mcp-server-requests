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
- `--use-workspace-root`: Enable workspace root support for file operations (requires MCP Client with root capability support)
- `--allow-outside-of-workspace`: Allow file operations outside workspace (only with --use-workspace-root)

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

- `--force-user-agent` controls User-Agent priority:
  - When enabled: Prioritize command line specified User-Agent (via `--user-agent` or `--random-user-agent`), ignoring LLM provided UA
  - When disabled:
    - If LLM provides User-Agent, use that
    - Otherwise use command line specified User-Agent

- `--use-workspace-root` enables file operations relative to workspace root:
  - **Prerequisite**: Requires MCP Client with root capability support
  - When enabled: File paths are relative to workspace root
  - When disabled: File paths must be absolute paths
  - `--allow-outside-of-workspace`: Controls whether files outside workspace are allowed (only usable with --use-workspace-root)

---

### 1. **fetch - Fetch Web Content**

The fetch subcommand is equivalent to the fetch tool functionality, demonstrating fetch capabilities.

```bash
python -m mcp_server_requests fetch <URL> [--return-content {raw,basic_clean,strict_clean,markdown}]
```

Options:
- `--return-content`: Return content type (default: markdown)
  - **raw**: Return raw unprocessed HTML content
  - **basic_clean**: Basic cleanup, removing non-display tags like script, style
  - **strict_clean**: Strict cleanup, removing non-display tags and most HTML attributes
  - **markdown**: Convert HTML to clean Markdown format

Example:
```
python -m mcp_server_requests fetch https://example.com
```

---

---

## Functionality

### Available Tools

1. **fetch** - Fetch web content
   - Parameters:
     - **url** (required): Target URL
     - **return_content** (optional): Return content type ('raw', 'basic_clean', 'strict_clean', 'markdown')
       - **raw**: Return raw HTML content
       - **basic_clean**: Return filtered HTML content, removing non-display tags like script, style
       - **strict_clean**: Return filtered HTML content, removing non-display tags and most useless HTML attributes
       - **markdown**: Return HTML converted to Markdown

2. **fetch_to_file** - Fetch web content and save to file
   - Parameters:
     - **url** (required): Target URL
     - **file_path** (required): File path where content will be saved
       - When `--use-workspace-root` is enabled: Relative path to workspace root
       - When disabled: Absolute file path
     - **return_content** (optional): Processing format (same as fetch tool)
   - Features:
     - Automatic directory creation for nested paths
     - UTF-8 encoding for all saved files

3. **http_request** - Execute HTTP request with any method
   - Parameters:
     - **url** (required): Target URL
     - **method** (optional): HTTP method ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'), default to `GET`
     - **query** (optional): Query parameter key-value pairs
     - **headers** (optional): Custom request headers
     - **data** (optional): Request body data (text)
     - **json** (optional): Request body data (JSON)
     - **data** and **json** cannot be used together
   - Features:
     - Complete HTTP response including status, headers, and body
   - Note: LLM may specify User-Agent in headers, whether to use it is controlled by `--force-user-agent`

**Note**: Individual HTTP method tools (http_get, http_post, http_put, http_patch, http_delete) have been removed and replaced by the unified **http_request** tool.

## License
MIT