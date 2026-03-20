# sep-api

国科大教务系统 (SEP) 非官方 API 客户端。提供 CLI 工具和 RESTful API 两种方式操作教务系统。

## 功能

- 登录认证（验证码自动识别 + 二次验证）
- 选课管理（查看已选、搜索、选课）
- 成绩查询
- 讲座管理（人文 / 科学前沿讲座记录与报名）
- 课程评估（一键全优）
- RESTful API 服务器（可选）

## 安装

```bash
# 最小安装（CLI + Python SDK）
pip install sep-api

# 完整安装（含 API 服务器 + Tesseract OCR）
pip install sep-api[all]

# 仅 API 服务器
pip install sep-api[api]

# 仅 Tesseract OCR 支持
pip install sep-api[tesseract]
```

## 快速开始

### CLI 使用

```bash
# 交互模式（TUI）
sep-api

# 登录
sep-api login -u 用户名 -p 密码

# 查看已选课程
sep-api courses
sep-api --json courses          # JSON 输出

# 搜索课程
sep-api search 课程编码

# 选课
sep-api select 课程ID

# 查看成绩
sep-api grades
sep-api --json grades

# 讲座
sep-api lectures -t hum-rec     # 人文讲座记录
sep-api lectures -t sci-rec     # 科学前沿讲座记录
sep-api lectures -t hum-list    # 人文讲座报名列表

# 启动 API 服务器（需要 sep-api[api]）
sep-api serve
```

### Python SDK

```python
import asyncio
from sep_api.client import SEPClient

async def main():
    client = SEPClient()
    await client.initialize()

    # 获取并识别验证码
    image = await client.get_captcha()
    captcha = await client.recognize_captcha(image)

    # 登录
    await client.login("用户名", "密码", captcha)

    # 使用服务
    from sep_api.services.xkgo import XkgoService
    xkgo = client.get_service(XkgoService)
    courses = await xkgo.get_selected_courses()
    print(courses)

    await client.close()

asyncio.run(main())
```

## CLI 命令参考

| 命令 | 说明 | 主要选项 |
|------|------|----------|
| `sep-api` | 交互模式 (TUI) | |
| `sep-api login` | 登录 | `-u` 用户名, `-p` 密码 |
| `sep-api courses` | 已选课程 | `--json` |
| `sep-api search <编码>` | 搜索课程 | `--json` |
| `sep-api select <ID>` | 选课 | `--json` |
| `sep-api grades` | 查看成绩 | `--json` |
| `sep-api lectures` | 讲座信息 | `-t hum-rec/sci-rec/hum-list`, `--json` |
| `sep-api serve` | API 服务器 | `--host`, `--port`, `--reload` |

## API 端点参考

需安装 `sep-api[api]`，运行 `sep-api serve` 后访问 `http://localhost:8000/docs` 查看交互式文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/captcha` | 获取验证码 |
| POST | `/auth/login` | 登录 |
| POST | `/auth/logout` | 登出 |
| GET | `/user/info` | 用户信息 |
| GET | `/courses` | 已选课程 |
| POST | `/courses/search` | 搜索课程 |
| POST | `/courses/select` | 选课 |
| GET | `/xkcts/grades` | 成绩查询 |
| GET | `/xkcts/lectures/humanity/record` | 人文讲座记录 |
| GET | `/xkcts/lectures/science/record` | 科学前沿讲座记录 |
| GET | `/xkcts/lectures/humanity/list` | 人文讲座报名列表 |
| GET | `/xkcts/evaluations` | 评估列表 |
| POST | `/xkcts/evaluations/auto` | 自动评估 |

## 验证码配置

默认使用 [AntiCAP](https://github.com/81NewArk/AntiCAP)（本地 ONNX 模型推理，无需联网或配置 API key），失败时自动降级到 Tesseract。

通过环境变量切换：

```bash
export CAPTCHA_METHOD=anticap     # AntiCAP 本地模型（默认）
export CAPTCHA_METHOD=tesseract   # Tesseract OCR（需要 sep-api[tesseract]）
export CAPTCHA_METHOD=chaojiying  # 超级鹰
```

超级鹰需额外配置：

```bash
export CHAOJIYING_USERNAME=...
export CHAOJIYING_PASSWORD=...
export CHAOJIYING_SOFT_ID=...
```

## Claude Code Skill

本项目包含 Claude Code Skill（`skills/sep-api.md`），让 AI agent 能通过 CLI 操作教务系统。

安装后在 Claude Code 中使用 `/skill` 加载即可。

## 开发

```bash
git clone https://github.com/tbjuechen/sep-api.git
cd sep-api
pip install -e ".[all]"

# 测试
pytest

# 代码检查
ruff check src/
ruff format src/
```

## License

[MIT](LICENSE)
