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
- `--use-workspace-root`：启用工作区根目录支持的文件操作（需要支持 root 能力的 MCP Client）
- `--allow-outside-of-workspace`：允许在工作区外进行文件操作（仅与 --use-workspace-root 一起使用）

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

- `--use-workspace-root` 启用相对于工作区根目录的文件操作：
  - **前提条件**：需要支持 root 能力的 MCP Client
  - 启用时：文件路径相对于工作区根目录
  - 禁用时：文件路径必须为绝对路径
  - `--allow-outside-of-workspace`：控制是否允许在工作区外操作文件（仅能与 --use-workspace-root 一起使用）

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

2. **fetch_to_file** - 获取网页内容并保存到文件
   - 参数：
     - **url**（必填）：目标 URL
     - **file_path**（必填）：保存内容的文件路径
       - 当启用 `--use-workspace-root` 时：相对于工作区根目录的路径
       - 禁用时：必须为绝对文件路径
     - **return_content**（可选）：处理格式（与 fetch 工具相同）
   - 功能特性：
     - 自动为嵌套路径创建目录
     - 文件路径安全验证
     - 所有保存的文件使用 UTF-8 编码

3. **http_request** - 使用任意方法执行 HTTP 请求
   - 参数：
     - **url**（必填）：目标 URL
     - **method**（可选）：HTTP 方法（'GET'、'POST'、'PUT'、'PATCH'、'DELETE'）
     - **query**（可选）：查询参数键值对
     - **headers**（可选）：自定义请求头
     - **data**（可选）：请求体数据（文本）
     - **json**（可选）：请求体数据（JSON）
       - **data** 和 **json** 不能同时使用
   - 功能特性：
     - 完整的 HTTP 响应，包括状态、头部和正文
     - 查询参数自动 URL 编码
     - JSON 数据自动设置 Content-Type 头
   - 注意：LLM 可能在 headers 中指定 User-Agent，是否采用由 `--force-user-agent` 控制

**注意**：单独的 HTTP 方法工具（http_get、http_post、http_put、http_patch、http_delete）已被移除，并替换为统一的 **http_request** 工具。

## License
MIT
