# mcp-server-requests

用于 HTTP 请求的 MCP 服务，可以令 LLM 拥有读取网页的能力。   

特性：
- 支持网页转换为 Markdown
- 过滤网页无用内容（对于 LLM 来说）
- 支持自定义 User-Agent
- 支持随机 User-Agent
- 支持在 HTTP 请求时设置请求头
- 支持多种 HTTP 请求方法（GET, POST, PUT, DELETE, PATCH）
- LLM 可以读取响应头

## 安装

```bash
git clone github.com/coucya/mcp-server-requests.git
cd mcp-server-requests
pip install .
```

## 使用

### mcp server

``` json
{
    "mcpServers": {
        "mcp-server-requests": {
            "command": "python",
            "args": [
                "-m",
                "mcp_server_requests"
            ],
        }
    }
}
```

### 命令行

- 命令行可以用于演示工具的使用效果。   
- 命令行功能的实现尚不完整。   

---

### 0. **启动 MCP 服务**

当未使用子命令时，直接启动 MCP 服务   

```bash
python -m mcp_server_requests
```

选项：
- `--user-agent TEXT`: 指定自定义 **User-Agent**
- `--random-user-agent [browser=xxx;os=xxx]`: 使用随机 **User-Agent**
- `--force-user-agent`: 强制使用指定或随机生成的 UA，忽略模型提供的 UA
- `--list-os-and-browser`: 列出可用的浏览器和操作系统用于 UA 选择

选项说明：
- `--user-agent` 和 `--random-user-agent` 不能同时使用。   
- 可以用以下方式设置 User-Agent:
  - 自定义 User-Agent (`--user-agent "Mozilla/5.0 (...)"`)
  - 随机生成 (`--random-user-agent`)
  - 指定浏览器和操作系统
    - 随机生成 chrome 的 **User-Agent** (`--random-user-agent browser=chrome`)
    - 随机生成 windows 的 **User-Agent** (`--random-user-agent os=windows`)
    - 随机生成 chrome 和 windows 的 **User-Agent** (`--random-user-agent browser=chrome;os=windows`)
    - `--random-user-agent` 在指定 os 和 browser 时不区分大小写

- 使用 `--list-os-and-browser` 查看可用于 `--random-user-agent` 的浏览器和操作系统列表。

- `--force-user-agent` 用于控制是否使用 LLM 调用工具时在 **header** 参数里指定的 **User-Agent**，如下：
  - 当使用 `--force-user-agent`，且 LLM 调用工具时在 **header** 参数里指定了 **User-Agent**，
    LLM 指定的 **User-Agent** 将被忽略，替换为命令行参数指定的（`--user-agent`、`--random-user-agnet` 或默认的）
  - 当未使用 `--force-user-agent`，且 LLM 调用工具时在 **header** 参数里指定了 **User-Agent**，
    使用 LLM 指定的 **User-Agent**
  - 否则，使用命令行参数指定的（`--user-agent`、`--random-user-agnet` 或默认的）



---

#### 1. **fetch - 获取网页内容**
fetch 子命令与 fetch 工具的功能等价，可以演示 fetch 的功能。

```bash
python -m mcp_server_requests fetch <URL> [--return-content {full,content,markdown}]
```

选项:
- `--return-content`: 返回内容类型 (默认: markdown)
  - **raw**，返回原始 HTML 内容。
  - **basic_clean**，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等。
  - **strict_clean**，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等，并且会删除大部分无用的 HTML 属性。
  - **markdown**，HTML 转换为 Markdown 后返回。

示例:
```
python -m mcp_server_requests fetch https://example.com
```

---

#### 2. **get - 执行 HTTP GET 请求**
get 子命令与 http_get 工具的功能等价，可以演示 http_get 的功能。

```bash
python -m mcp_server_requests get <URL> [--headers HEADERS]
```

选项:
- `--headers`: 自定义请求头 (格式: "key1=value1;key2=value2")

---

#### 3. **post - 执行 HTTP POST 请求**
post 子命令与 http_get 工具的功能等价，可以演示 http_get 的功能。

```bash
python -m mcp_server_requests post <URL> [--headers HEADERS] [--data TEXT]
```

选项:
- `--headers`: 自定义请求头
- `--data`: 请求体数据

---

#### 4. **put - 执行 HTTP PUT 请求**
put 子命令与 http_put 工具的功能等价，可以演示 http_put 的功能。

```bash
python -m mcp_server_requests put <URL> [--headers HEADERS] [--data TEXT]
```

选项: 同 POST

---

#### 5. **delete - 执行 HTTP DELETE 请求**
delete 子命令与 http_delete 工具的功能等价，可以演示 http_delete 的功能。

```bash
python -m mcp_server_requests delete <URL> [--headers HEADERS] [--data TEXT]
```

选项: 同 POST




## 功能

### 可用工具

1. **fetch** - 获取网页内容
  - 参数:
    - **url** (必填): 目标 URL
    - **return_content** (可选): 返回内容类型 ('raw', 'basic_clean', 'strict_clean', 'markdown')
      - **raw**，返回原始 HTML 内容。
      - **basic_clean**，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等。
      - **strict_clean**，返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script, style 等，并且会删除大部分无用的 HTML 属性。
      - **markdown**，HTML 转换为 Markdown 后返回。

2. **http_get** - 执行 HTTP GET 请求
  - 参数:
    - **url** (必填): 目标 URL
    - **query** (可选): 查询参数键值对
    - **headers** (可选): 自定义请求头
      - LLM 可能在 headers 里指定 User-Agent，是否采用由 `--force-user-agent` 控制，后续的工具同理

3. **http_post** - 执行 HTTP POST 请求
  - 参数:
    - **url** (必填): 目标 URL
    - **query** (可选): 查询参数键值对
    - **headers** (可选): 自定义请求头
    - **data** (可选): 请求体数据 (文本)
    - **json** (可选): 请求体数据 (JSON)
    - **data** 和 **json** 不能同时使用

4. **http_put** - 执行 HTTP PUT 请求
  - 参数: 同 http_post

5. **http_patch** - 执行 HTTP PATCH 请求
  - 参数: 同 http_post

6. **http_delete** - 执行 HTTP DELETE 请求
  - 参数: 同 http_post


## License
MIT
