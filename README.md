# mcp-server-requests

用于 HTTP 请求的 MCP 服务，可以令 LLM 拥有读取网页的能力。   

特性：
- 支持网页转换为 Markdown
- 支持修改 User-Agent
- 支持 headers
- 支持多种 HTTP 请求方法（GET, POST, PUT, DELETE, PATCH）


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

### 选项

- `--user-agent TEXT`: 指定自定义 User-Agent
- `--random-user-agent [browser=xxx;os=xxx]`: 使用随机 User-Agent
- `--force-user-agent`: 强制使用指定或随机生成的 UA，忽略模型提供的 UA
- `--list-os-and-browser`: 列出可用的浏览器和操作系统用于 UA 选择

### 选项说明
- `--user-agent` 和 `--random-user-agent` 不能同时使用。   
- 可以用以下方式设置 User-Agent:
  - 自定义 User-Agent (`--user-agent "Mozilla/5.0 (...)"`)
  - 随机生成 (`--random-user-agent`)
  - 指定浏览器和操作系统
    - 随机生成 chrome 的 User-Agent (`--random-user-agent browser=chrome`)
    - 随机生成 windows 的 User-Agent (`--random-user-agent os=windows`)
    - 随机生成 chrome 和 windows 的 User-Agent (`--random-user-agent browser=chrome;os=windows`)
    - `--random-user-agent` 在指定 os 和 browser 时不区分大小写

- 使用 `--list-os-and-browser` 查看可用于 `--random-user-agent` 的浏览器和操作系统列表。

- 当使用 `--force-user-agent` 后：
  - 当 LLM 调用工具时在 header 参数里指定的 `User-Agent`，替换为 `--user-agent` 提供的或 `--random-user-agnet` 随机产生的或默认的 `User-Agent`
  - 否则，使用 `--user-agent` 提供的或 `--random-user-agnet` 随机产生的或默认的 `User-Agent`
- 当未使用 `--force-user-agent`：
  - 当 LLM 调用工具时在 header 参数里指定了 `User-Agent`，使用该 `User-Agent`
  - 否则，使用 `--user-agent` 提供的或 `--random-user-agnet` 随机产生的或默认的 `User-Agent`

## 功能

### 可用工具

1. **fetch** - 获取网页内容
   - 参数:
     - `url` (必填): 目标 URL
     - `return_content` (可选): 返回内容类型 ("full", "content", "markdown")
       - `"full"`: 返回整个 HTML 页面内容
       - `"content"`: 过滤后的 HTML 内容（移除 script, style 等标签）
       - `"markdown"`: 网页转换为 Markdown 后返回

2. **http_get** - 执行 HTTP GET 请求
   - 参数:
     - `url` (必填): 目标 URL
     - `query` (可选): 查询参数键值对
     - `headers` (可选): 自定义请求头
       - LLM 可能在 headers 里指定 User-Agent，是否采用由 `--force-user-agent` 控制，后续的工具同理

3. **http_post** - 执行 HTTP POST 请求
   - 参数:
     - `url` (必填): 目标 URL
     - `query` (可选): 查询参数键值对
     - `headers` (可选): 自定义请求头
     - `data` (可选): 请求体数据 (文本)
     - `json` (可选): 请求体数据 (JSON)
     - `data` 和 `json` 不能同时使用

4. **http_put** - 执行 HTTP PUT 请求
   - 参数: 同 http_post

5. **http_patch** - 执行 HTTP PATCH 请求
   - 参数: 同 http_post

6. **http_delete** - 执行 HTTP DELETE 请求
   - 参数: 同 http_post


## 其它

### 子命令
子命令仅用于测试，与 MCP 无关，在配置 MCP 的过程中无需考虑。   
子命令可以用于演示工具的使用效果。   
子命令的实现尚不完整。   

#### fetch - 获取网页内容

```bash
python -m mcp_server_requests fetch <URL> [--return-content {full,content,markdown}]
```

选项:
- `--return-content`: 返回内容类型 (默认: markdown)
  - `full`: 完整 HTML 内容
  - `content`: 过滤后的 HTML 内容（移除 script, style 等标签）
  - `markdown`: 转换为 Markdown 格式

示例:
```
python -m mcp_server_requests fetch https://example.com
```

#### get - 执行 HTTP GET 请求

```bash
python -m mcp_server_requests get <URL> [--headers HEADERS]
```

选项:
- `--headers`: 自定义请求头 (格式: "key1=value1;key2=value2")

#### post - 执行 HTTP POST 请求

```bash
python -m mcp_server_requests post <URL> [--headers HEADERS] [--data TEXT]
```

选项:
- `--headers`: 自定义请求头
- `--data`: 请求体数据

#### put - 执行 HTTP PUT 请求

```bash
python -m mcp_server_requests put <URL> [--headers HEADERS] [--data TEXT]
```

选项: 同 POST



#### delete - 执行 HTTP DELETE 请求

```bash
python -m mcp_server_requests delete <URL> [--headers HEADERS] [--data TEXT]
```

选项: 同 POST

## License
MIT
