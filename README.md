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

### 2. **get - Execute HTTP GET Request**

The get subcommand is equivalent to the http_get tool functionality, demonstrating http_get capabilities.

```bash
python -m mcp_server_requests get <URL> [--headers HEADERS]
```

Options:
- `--headers`: Custom request headers (format: "key1=value1;key2=value2")

---

### 3. **post - Execute HTTP POST Request**

The post subcommand is equivalent to the http_post tool functionality, demonstrating http_post capabilities.

```bash
python -m mcp_server_requests post <URL> [--headers HEADERS] [--data TEXT]
```

Options:
- `--headers`: Custom request headers
- `--data`: Request body data

---

### 4. **put - Execute HTTP PUT Request**

The put subcommand is equivalent to the http_put tool functionality, demonstrating http_put capabilities.

```bash
python -m mcp_server_requests put <URL> [--headers HEADERS] [--data TEXT]
```

Options: Same as POST method

---

### 5. **delete - Execute HTTP DELETE Request**

The delete subcommand is equivalent to the http_delete tool functionality, demonstrating http_delete capabilities.

```bash
python -m mcp_server_requests delete <URL> [--headers HEADERS] [--data TEXT]
```

Options: Same as POST method

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

2. **http_get** - Execute HTTP GET request
   - Parameters:
     - **url** (required): Target URL
     - **query** (optional): Query parameter key-value pairs
     - **headers** (optional): Custom request headers
       - LLM may specify User-Agent in headers, whether to use it is controlled by `--force-user-agent` (same applies to other tools)

3. **http_post** - Execute HTTP POST request
   - Parameters:
     - **url** (required): Target URL
     - **query** (optional): Query parameter key-value pairs
     - **headers** (optional): Custom request headers
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