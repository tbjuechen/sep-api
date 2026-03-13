# 国科大教务系统 API 中转站

国科大教务系统（SEP）API 中转站，提供 RESTful API 和 CLI 工具两种访问方式。

## 功能特性

- 登录认证（支持验证码自动识别）
- 获取已选课程列表
- 搜索课程
- 提交选课
- RESTful API 接口
- CLI 命令行工具

## 快速开始

### 1. 创建 Conda 环境

```bash
conda env create -f environment.yml
conda activate sep-api
```

### 2. 安装项目

```bash
pip install -e .
```

### 3. 启动 API 服务

```bash
sep-api serve
# 或
uvicorn sep_api.api:app --reload
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

### 4. 使用 CLI 工具

```bash
# 登录
sep-api login -u your_username -p your_password

# 查看已选课程
sep-api courses

# 搜索课程
sep-api search 课程代码

# 选课
sep-api select 课程ID
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/auth/captcha` | POST | 获取验证码 |
| `/auth/login` | POST | 登录 |
| `/user/info` | GET | 获取用户信息 |
| `/courses` | GET | 获取已选课程 |
| `/courses/search` | POST | 搜索课程 |
| `/courses/select` | POST | 选课 |

## 配置

### 验证码识别方案

默认使用 AntiCAP，可通过环境变量切换：

- `CAPTCHA_METHOD=tesseract` - 使用 Tesseract OCR
- `CAPTCHA_METHOD=anticap` - 使用 AntiCAP（默认）
- `CAPTCHA_METHOD=chaojiying` - 使用超级鹰（需配置账号）

### 超级鹰配置

```bash
export CHAOJIYING_USERNAME=your_username
export CHAOJIYING_PASSWORD=your_password
export CHAOJIYING_SOFT_ID=your_soft_id
```

## 开发

### 运行测试

```bash
pytest
```

### 代码格式

```bash
ruff check src/
ruff format src/
```

## 许可证

MIT License