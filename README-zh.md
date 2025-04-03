# mcp-server-requests

一个提供 HTTP 请求能力的 MCP 服务，使 LLM 能够获取和处理网页内容。

## 特性
- 支持将网页内容转换为 Markdown 格式
- 支持过滤网页中对 LLM 无用的内容
- 支持自定义 User-Agent 头
- 支持随机 User-Agent 头
- 支持在 HTTP 请求中自定义请求头
- 支持完整的 HTTP 方法（GET、POST、PUT、DELETE、PATCH）
- LLM 可获取完整的 HTTP 响应头信息

## 安装

```bash
git clone https://github.com/coucya/mcp-server-requests.git
cd mcp-server-requests
pip install .
```

## 使用

### MCP Server 配置

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

### 命令行

### 0. **启动 MCP 服务**

直接启动 MCP 服务：

```bash
python -m mcp_server_requests
```

#### 选项
- `--user-agent TEXT`：指定自定义 User-Agent 字符串
- `--random-user-agent [browser=xxx;os=xxx]`：使用随机生成的 User-Agent
- `--force-user-agent`：强制使用命令行指定的 User-Agent，忽略 LLM 提供的 UA
- `--list-os-and-browser`：列出可用于生成随机 User-Agent 的浏览器和操作系统

#### 选项说明
- `--user-agent` 和 `--random-user-agent` 选项互斥，不能同时使用
- User-Agent 设置方式：
  - 自定义字符串：`--user-agent "Mozilla/5.0 (...)"`
  - 完全随机生成：`--random-user-agent`
  - 按条件随机生成：
    - 指定浏览器类型：`--random-user-agent browser=chrome`
    - 指定操作系统：`--random-user-agent os=windows`
    - 同时指定浏览器和系统：`--random-user-agent browser=chrome;os=windows`
    - 注意：浏览器和系统参数不区分大小写

- 使用 `--list-os-and-browser` 查看可用于 `--random-user-agent` 的浏览器和操作系统列表。

- `--force-user-agent` 选项控制 User-Agent 的优先级：
  - 启用时：优先使用命令行指定的 User-Agent（通过 `--user-agent` 或 `--random-user-agent`），忽略 LLM 提供的 UA
  - 禁用时：
    - 如果 LLM 提供了 User-Agent，则使用 LLM 提供的
    - 否则使用命令行指定的 User-Agent

---

### 1. **fetch - 获取网页内容**

fetch 子命令与 fetch 工具的功能等价，可以演示 fetch 的功能。

```bash
python -m mcp_server_requests fetch <URL> [--return-content {raw,basic_clean,strict_clean,markdown}]
```

选项：
- `--return-content`：返回内容类型（默认：markdown）
  - **raw**：返回未经处理的原始 HTML 内容
  - **basic_clean**：基础清理，移除 script、style 等非显示性标签
  - **strict_clean**：严格清理，移除非显示性标签并清除大部分 HTML 属性
  - **markdown**：将 HTML 转换为简洁的 Markdown 格式

示例：
```
python -m mcp_server_requests fetch https://example.com
```

---

### 2. **get - 执行 HTTP GET 请求**

get 子命令与 http_get 工具的功能等价，可以演示 http_get 的功能。

```bash
python -m mcp_server_requests get <URL> [--headers HEADERS]
```

选项：
- `--headers`：自定义请求头（格式："key1=value1;key2=value2"）

---

### 3. **post - 执行 HTTP POST 请求**

post 子命令与 http_post 工具的功能等价，可以演示 http_post 的功能。

```bash
python -m mcp_server_requests post <URL> [--headers HEADERS] [--data TEXT]
```

选项：
- `--headers`：自定义请求头
- `--data`：请求体数据

---

### 4. **put - 执行 HTTP PUT 请求**

put 子命令与 http_put 工具的功能等价，可以演示 http_put 的功能。

```bash
python -m mcp_server_requests put <URL> [--headers HEADERS] [--data TEXT]
```

选项：与 POST 方法相同

---

### 5. **delete - 执行 HTTP DELETE 请求**

delete 子命令与 http_delete 工具的功能等价，可以演示 http_delete 的功能。

```bash
python -m mcp_server_requests delete <URL> [--headers HEADERS] [--data TEXT]
```

选项：与 POST 方法相同

---

## 功能

### 可用工具

1. **fetch** - 获取网页内容
   - 参数：
     - **url**（必填）：目标 URL
     - **return_content**（可选）：返回内容类型（'raw'、'basic_clean'、'strict_clean'、'markdown'）
       - **raw**：返回原始 HTML 内容
       - **basic_clean**：返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script、style 等
       - **strict_clean**：返回过滤后的 HTML 内容，过滤掉所有不会显示的标签，如 script、style 等，并且会删除大部分无用的 HTML 属性
       - **markdown**：HTML 转换为 Markdown 后返回

2. **http_get** - 执行 HTTP GET 请求
   - 参数：
     - **url**（必填）：目标 URL
     - **query**（可选）：查询参数键值对
     - **headers**（可选）：自定义请求头
       - LLM 可能在 headers 里指定 User-Agent，是否采用由 `--force-user-agent` 控制，后续的工具同理

3. **http_post** - 执行 HTTP POST 请求
   - 参数：
     - **url**（必填）：目标 URL
     - **query**（可选）：查询参数键值对
     - **headers**（可选）：自定义请求头
     - **data**（可选）：请求体数据（文本）
     - **json**（可选）：请求体数据（JSON）
     - **data** 和 **json** 不能同时使用

4. **http_put** - 执行 HTTP PUT 请求
   - 参数：同 http_post

5. **http_patch** - 执行 HTTP PATCH 请求
   - 参数：与 http_post 相同

6. **http_delete** - 执行 HTTP DELETE 请求
   - 参数：与 http_post 相同

## License
MIT
