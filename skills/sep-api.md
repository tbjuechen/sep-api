---
name: sep-api
description: |
  操作国科大 (UCAS) 教务系统 (SEP)：登录、选课、成绩查询、讲座管理、课程评估。
  TRIGGER when: 用户提到国科大/UCAS/SEP/选课/退课/成绩/讲座/教务系统/课程评估。
  DO NOT TRIGGER when: 与教务系统无关的通用编程任务。
---

# sep-api — 国科大教务系统 CLI Skill

你可以通过 `sep-api` CLI 工具帮助用户操作国科大教务系统。所有子命令都支持 `--json` 输出，适合程序化处理。

## 前置检查

在执行任何操作前，确认 `sep-api` 已安装：

```bash
sep-api --help
```

如未安装，指导用户运行：

```bash
pip install sep-api
```

## 工作流

### 1. 登录

用户必须先登录才能执行任何操作。向用户询问用户名和密码，然后执行：

```bash
sep-api login -u USERNAME -p PASSWORD
```

**输出格式（JSON）：**
- 成功: `{"success": true, "user": {"name": "...", "student_id": "...", "unit": "..."}}`
- 需要二次验证: exit code 2, stderr 输出 `{"success": false, "error": "two_factor_required", "email": "...", "phone": "..."}`
- 登录失败: exit code 1

**二次验证处理：** 如果返回 `two_factor_required`，告知用户需要二次验证，建议使用交互模式 `sep-api`（不带子命令）完成登录。

**登录状态持久化：** 登录成功后会话保存在 `.sep_session.json`，后续命令自动使用。

### 2. 查看已选课程

```bash
sep-api --json courses
```

返回课程列表 JSON 数组，每个对象包含中文字段如 `课程编码`、`课程名称`、`学分` 等。

### 3. 搜索课程

```bash
sep-api --json search COURSE_CODE
```

按课程编码搜索，返回匹配的课程列表。

### 4. 选课

```bash
sep-api --json select COURSE_ID
```

返回 `{"status": "SUCCESS"|"FAIL", "message": "..."}`。

**重要：** 选课前始终向用户确认课程信息，这是不可轻易撤销的操作。

### 5. 查看成绩

```bash
sep-api --json grades
```

返回所有已出成绩的课程列表。

### 6. 讲座信息

```bash
# 人文讲座听课记录
sep-api --json lectures -t hum-rec

# 科学前沿讲座记录
sep-api --json lectures -t sci-rec

# 人文讲座报名列表
sep-api --json lectures -t hum-list
```

### 7. API 服务器（如需要）

```bash
sep-api serve --port 8000
```

需要安装 `pip install sep-api[api]`。启动后可通过 `http://localhost:8000/docs` 查看接口文档。

## 错误处理

- **`未找到会话文件`** — 会话过期或未登录，需要重新执行 `sep-api login`。
- **验证码识别失败** — CLI 会自动重试最多 5 次。如果仍然失败，建议用户稍后再试。
- **网络错误** — SEP 系统可能不稳定，建议重试。

## 安全注意事项

- 密码通过 RSA 加密传输，不会明文存储。
- 会话文件 `.sep_session.json` 包含认证 cookie，不要泄露。
- **绝不要**将用户的密码记录到日志、输出或存储到任何文件中。
