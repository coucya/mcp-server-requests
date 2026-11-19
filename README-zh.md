# mcp-server-requests

一个提供 HTTP 请求能力的 MCP 服务，使 LLM 能够获取和处理网页内容。

## 特性

- **fetch**：获取网页内容工具
  - 支持网页内容转换为 Markdown 格式
  - 支持过滤网页内容（script、style、meta 等非视觉元素）
  - 填充到 LLM 上下文、通过转换为 Markdown 或过滤非视觉元素减少 tokens 消耗
- **fetch_to_file**：保存网页内容到文件工具
  - 默认关闭，需用 `--enable-fetch-to-file` 开启
  - 可写入的文件范围限制在配置的可写目录内，用 `--workspace` 和 `--writable-dir` 控制
  - 网页内容不会填充到 LLM 上下文、不会过多消耗 tokens
- **http_request**：通用 HTTP 请求工具
  - 完整 HTTP 方法支持（GET、POST、PUT、PATCH、DELETE）
  - 支持自定义请求头
  - 支持文本和 JSON 请求体
  - 为 LLM 返回完整 HTTP 响应信息（状态、响应头、响应体）
- 支持自定义 User-Agent
- 支持随机 User-Agent 生成

## 安装

```bash
git clone https://github.com/coucya/mcp-server-requests.git
cd mcp-server-requests
pip install .
```

需要 Python 3.11 或更高版本。

## 使用

### MCP Server 配置

基本使用：
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

高级使用（启用 `fetch_to_file`，需要使用 `--workspace` 或 `--writable-dir` 参数添加可写的目录）：
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
- `--enable-fetch-to-file`：启用 `fetch_to_file` 工具（默认关闭）
- `--workspace PATH`：可写目录，同时作为相对路径的根目录。只使用绝对路径，相对路径会被忽略。
- `--writable-dir PATH`：为 `fetch_to_file` 追加额外的可写目录（可重复）。只使用绝对路径，相对路径会被忽略。

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
- 当 `--force-user-agent` 启用时：强制使用命令行指定的 User-Agent（通过 `--user-agent` 或 `--random-user-agent`）
- 当 `--force-user-agent` 禁用时：
  - 如果 LLM 在 `headers` 中提供 User-Agent，则使用 LLM 提供的
  - 否则使用命令行指定的 User-Agent
- 如果都没有指定，使用默认 User-Agent：`Mozilla/5.0 (compatible; mcp-server-requests/{version})`

- `fetch_to_file` 默认不注册为 MCP 工具，模型看不到它。用 `--enable-fetch-to-file` 开启。
- 可写目录是 `fetch_to_file` 可以写入的范围，是 `--workspace` 目录加上所有 `--writable-dir` 目录：
  - 当 LLM 尝试把网页写入某个相对路径时，以 `--workspace` 为相对路径的根。未配置 workspace 时，相对路径会被拒绝。
  - `--writable-dir` 用于在 `--workspace`之外添加额外的可写目录。
  - `file_path` 可以是绝对路径或相对路径，但解析后的文件必须位于某个可写根内。
  - 可写根必须是目录。目录不存在时，在首次使用工具时自动创建。
  - `--workspace` 和 `--writable-dir` 只使用绝对路径，相对路径会被忽略。
- 不会覆盖已有文件。目标文件已存在时，工具返回错误，不写入任何内容。
- 写入前会解析符号链接。解析后的最终目标必须位于某个可写根内。
- HTTP 4xx/5xx 的响应体会像正常响应一样写入文件。
- `/etc`、`C:\Windows` 等系统目录始终禁止写入。用户级敏感路径也会被拒绝：`~/.ssh`、`~/.aws`、`~/.gnupg`、`~/.config/autostart`、`~/.bashrc`、`~/.zshrc` 等 shell 启动文件，以及 Windows 的启动目录。
- 每个可写根下的 `.git` 和 `.husky` 目录也会被拒绝，防止抓取到的网页内容安装 git hook。
- `fetch_to_file` 只保存文本内容。非文本响应会返回错误，不会创建文件。

---

### 1. **fetch - 获取网页内容**

fetch 子命令与 MCP 工具 `fetch` 的功能等价，用于演示 fetch 功能。

```bash
python -m mcp_server_requests fetch <URL> [--return-content {raw,basic_clean,strict_clean,markdown}] [--timeout SECONDS]
```

**选项说明：**
- `--return-content`：返回内容类型（默认：markdown）
  - **raw**：返回未经处理的原始 HTML 内容（包含响应头信息）
  - **basic_clean**：基础清理，移除 script、style、meta 等非显示性标签，保留结构
  - **strict_clean**：严格清理，移除非显示性标签并清除大部分 HTML 属性，仅保留必要结构
  - **markdown**：将 HTML 转换为简洁的 Markdown 格式
- `--timeout`：请求超时时间，单位秒（默认：30）

---

## 功能

### MCP 工具详细说明

#### 1. **fetch** - 获取网页内容
获取指定 URL 的内容并按指定格式返回。

**参数：**
- **url**（必填，字符串）：目标 URL，支持 HTTP/HTTPS 协议
- **return_content**（可选，枚举）：内容处理格式，默认为 "markdown"
  - `"raw"`：返回原始 HTML 内容，包含完整的 HTTP 响应头
  - `"basic_clean"`：基础清理，移除 script、style、meta 等非显示标签，保留 HTML 结构
  - `"strict_clean"`：严格清理，移除非显示标签和大部分 HTML 属性，仅保留必要结构
  - `"markdown"`：将 HTML 内容转换为清洁的 Markdown 格式
- **timeout**（可选，数字）：请求超时时间，单位秒，默认 30。传 `null` 表示不超时。

**返回值：** 根据指定格式处理后的 web 内容

---

#### 2. **fetch_to_file** - 获取网页内容并保存到文件
获取指定 URL 的内容并保存到文件。

**参数：**
- **url**（必填，字符串）：目标 URL
- **file_path**（必填，字符串）：文件保存路径
  - 绝对路径必须位于某个可写根内
  - 相对路径以 `--workspace` 为基准，且必须落在某个可写根内
- **return_content**（可选，枚举）：内容处理格式，默认为 "markdown"，选项同 fetch 工具
- **timeout**（可选，数字）：请求超时时间，单位秒，默认 30。传 `null` 表示不超时。

**特性：**
- 默认关闭，需用 `--enable-fetch-to-file` 开启
- 写入配置的可写根之外的路径会被拒绝
- 已有文件不会被覆盖
- 自动创建嵌套目录的父目录
- 所有文件使用 UTF-8 编码保存
- HTTP 4xx/5xx 的响应体会像正常响应一样写入文件
- 写入前会解析符号链接

**返回值：** 操作结果或错误信息

---

#### 3. **http_request** - 通用 HTTP 请求工具
使用任意 HTTP 方法发送请求并获取完整响应。

**参数：**
- **url**（必填，字符串）：目标 URL
- **method**（可选，枚举）：HTTP 方法，默认为 "GET"
  - `"GET"`、`"POST"`、`"PUT"`、`"PATCH"`、`"DELETE"`
- **query**（可选，对象）：URL 查询参数，键值对形式，自动 URL 编码
- **headers**（可选，对象）：自定义 HTTP 请求头
- **data**（可选，字符串）：文本格式的请求体数据，与 json 参数互斥
- **json**（可选，任意类型）：JSON 格式的请求体数据，与 data 参数互斥
- **timeout**（可选，数字）：请求超时时间，单位秒，默认 30。传 `null` 表示不超时。

**返回值：** 包含完整的 HTTP 响应（状态行、响应头、响应体）

---

**注意**：之前版本的独立 HTTP 方法工具（http_get、http_post、http_put、http_patch、http_delete）已被移除，统一使用 **http_request** 工具。

## License
MIT
