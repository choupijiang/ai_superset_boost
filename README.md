# 智能商业分析系统

基于 Superset 数据的 AI 驱动业务分析平台，能够自动登录 Superset，捕获看板截图，并使用 AI 分析回答业务问题。

## 功能特性

- 🔐 **自动登录 Superset**：使用 Playwright 自动化登录到 Superset
- 📸 **看板截图捕获**：自动访问所有看板并截图
- 🤖 **AI 智能分析**：使用 DeepSeek API 分析截图并回答业务问题
- 🌐 **友好 Web 界面**：直观的用户界面，支持中文输入
- ⚡ **实时分析**：快速响应的业务分析结果
- 🛡️ **错误处理**：完善的错误处理和降级机制

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd quickstart

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install
```

### 2. 配置环境变量

复制 `.env` 文件并根据需要修改配置：

```bash
# Superset 配置
SUPERSET_URL=http://localhost:8088
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin

# Flask 配置
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production

# AI API 配置
DEEPSEEK_API_KEY=your-deepseek-api-key-here
```

### 3. 启动应用

```bash
# 启动 Flask 应用
python app.py
```

访问 `http://localhost:5000` 即可使用系统。

## 使用说明

1. **输入业务问题**：在文本框中输入您想要分析的业务问题
2. **开始分析**：点击"开始分析"按钮
3. **查看结果**：系统会自动：
   - 登录到 Superset
   - 访问所有可用看板
   - 截图保存
   - 使用 AI 分析数据
   - 返回分析结果

### 支持的问题类型

- 销售趋势分析
- 用户活跃度分析
- 财务状况分析
- 产品性能评估
- 市场趋势预测
- 成本结构分析

## 系统架构

```
智能商业分析系统
├── app.py                    # Flask 主应用
├── superset_automation.py    # Superset 自动化操作
├── ai_analyzer.py           # AI 分析模块
├── templates/
│   └── index.html           # Web 界面
├── screenshots/             # 截图存储目录
├── requirements.txt         # Python 依赖
├── .env                     # 环境配置
└── CLAUDE.md               # Claude Code 配置
```

## 技术栈

- **后端框架**：Flask
- **自动化工具**：Playwright
- **AI 服务**：DeepSeek API
- **前端技术**：HTML5, CSS3, JavaScript
- **图像处理**：Pillow
- **异步处理**：asyncio

## 配置说明

### Superset 连接配置

确保 Superset 实例正在运行并可访问：

```env
SUPERSET_URL=http://localhost:8088
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin
```

### DeepSeek API 配置

获取 DeepSeek API 密钥：

```env
DEEPSEEK_API_KEY=sk-your-api-key-here
```

### 安全配置

生产环境中请修改：

```env
SECRET_KEY=your-secure-secret-key
FLASK_ENV=production
FLASK_DEBUG=False
```

## 故障排除

### 常见问题

1. **Superset 连接失败**
   - 检查 Superset 是否正在运行
   - 验证 URL 和凭据是否正确
   - 确认网络连接

2. **截图失败**
   - 检查 Playwright 浏览器是否正确安装
   - 确认看板 URL 格式正确
   - 检查截图目录权限

3. **AI 分析失败**
   - 验证 DeepSeek API 密钥是否有效
   - 检查网络连接
   - 确认 API 配额充足

### 调试模式

启用调试模式以查看详细日志：

```env
FLASK_DEBUG=True
```

## API 端点

- `GET /` - 主页面
- `POST /analyze` - 分析业务问题
- `GET /screenshots/<filename>` - 获取截图文件
- `GET /health` - 健康检查

## 开发说明

### 添加新的分析模板

在 `ai_analyzer.py` 的 `get_business_insights_template` 方法中添加新的模板：

```python
templates["新类型"] = """
模板内容...
"""
```

### 扩展自动化功能

在 `superset_automation.py` 中添加新的自动化操作：

```python
async def new_automation_function(self):
    # 实现新的自动化功能
    pass
```

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。