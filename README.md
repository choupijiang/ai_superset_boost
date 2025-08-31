# 智能商业分析系统

基于 Superset 数据的 AI 驱动业务分析平台，能够自动登录 Superset，通过 Menu Download 机制捕获看板截图，并使用 BigModel.cn GLM-4.5 进行智能分析回答业务问题。

## 功能特性

- 🔐 **自动登录 Superset**：使用 Playwright 自动化登录到 Superset
- 📸 **智能截图捕获**：优先通过 Menu Download 机制获取看板截图，失败时降级到截图方式
- 🤖 **AI 智能分析**：使用 BigModel.cn GLM-4.5 分析截图并回答业务问题
- 📈 **渐进式实时分析**：逐个图表实时分析，提供即时反馈和综合洞察
- 🌐 **友好 Web 界面**：直观的用户界面，支持中文输入和实时进度显示
- ⚡ **高效处理**：异步处理多个看板，快速响应业务分析需求
- 🛡️ **错误处理**：完善的错误处理和降级机制，确保系统稳定性

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

# AI API 配置 - BigModel.cn GLM-4.5
OPENAI_API_KEY=your-bigmodel-api-key-here
OPENAI_API_BASE=https://api.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4v-plus
```

### 3. 启动应用

```bash
# 启动 Flask 应用
python app.py
```

访问 `http://localhost:5002` 即可使用系统。

## 使用说明

### 工作流程

系统采用**渐进式实时分析**模式，完整的工作流程如下：

1. **📝 用户提问**：在 Web 界面输入业务分析问题
2. **🔐 自动登录**：系统使用 Playwright 自动登录 Superset
3. **📸 智能截图**：通过 Menu Download 机制获取每个看板的高质量截图
4. **🤖 AI 分析**：将截图转换为 base64 格式，调用 BigModel.cn GLM-4.5 进行分析
5. **📊 综合回答**：整合所有看板的分析结果，提供全面的业务洞察

### 渐进式分析特性

- **实时反馈**：逐个图表分析，实时显示分析进度
- **错误容错**：Menu Download 失败时自动降级到截图方式
- **并发处理**：异步处理多个看板，提高分析效率
- **进度可视化**：通过 Server-Sent Events 实时更新分析状态

### 支持的问题类型

- 销售趋势分析
- 用户活跃度分析
- 财务状况分析
- 产品性能评估
- 市场趋势预测
- 成本结构分析
- 运营效率分析
- 用户行为分析

### Menu Download 机制

系统优先使用 **Menu Download** 功能获取看板截图：

1. **优先尝试**：通过 Superset 的菜单下载功能获取高质量截图
2. **自动降级**：如果 Menu Download 失败，自动使用页面截图方式
3. **质量保证**：确保获取的截图清晰度满足 AI 分析需求
4. **批量处理**：支持多个看板的批量截图和分析

## 系统架构

```
智能商业分析系统
├── app.py                    # Flask 主应用 (渐进式分析 API)
├── superset_automation.py    # Superset 自动化操作 (Menu Download)
├── ai_analyzer.py           # AI 分析模块 (BigModel.cn GLM-4.5)
├── templates/
│   └── index.html           # Web 界面 (实时进度显示)
├── screenshots/             # 截图存储目录
├── requirements.txt         # Python 依赖
├── .env                     # 环境配置
├── start.sh                 # 启动脚本
└── CLAUDE.md               # Claude Code 配置
```

## 技术栈

- **后端框架**：Flask
- **自动化工具**：Playwright
- **AI 服务**：BigModel.cn GLM-4.5 (通过 OpenAI 客户端)
- **前端技术**：HTML5, CSS3, JavaScript
- **图像处理**：Pillow, base64 编码
- **异步处理**：asyncio
- **实时通信**：Server-Sent Events (SSE)
- **进程管理**：多线程处理

## 配置说明

### Superset 连接配置

确保 Superset 实例正在运行并可访问：

```env
SUPERSET_URL=http://localhost:8088
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=admin
```

### BigModel.cn API 配置

获取 BigModel.cn API 密钥：

```env
OPENAI_API_KEY=your-bigmodel-api-key-here
OPENAI_API_BASE=https://api.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4v-plus
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
   - 检查 Superset 是否正在运行 (http://localhost:8088)
   - 验证 SUPERSET_URL、SUPERSET_USERNAME、SUPERSET_PASSWORD 是否正确
   - 确认网络连接和防火墙设置

2. **截图失败**
   - 检查 Playwright 浏览器是否正确安装 (`playwright install`)
   - 确认看板 URL 格式正确
   - 检查 screenshots/ 目录权限
   - 验证 Menu Download 功能是否正常工作

3. **AI 分析失败**
   - 验证 OPENAI_API_KEY (BigModel.cn) 是否有效
   - 检查 OPENAI_API_BASE 配置是否正确
   - 确认网络连接可以访问 BigModel.cn API
   - 检查 API 配额是否充足

4. **渐进式分析中断**
   - 检查浏览器是否正常运行
   - 确认系统资源充足 (内存、CPU)
   - 查看日志文件了解详细错误信息

### 调试模式

启用调试模式以查看详细日志：

```env
FLASK_DEBUG=True
```

## API 端点

- `GET /` - 主页面
- `POST /analyze_progressive` - 渐进式分析业务问题 (主要接口)
- `GET /screenshots/<filename>` - 获取截图文件
- `GET /health` - 健康检查

## 开发说明

### 项目结构

```
智能商业分析系统/
├── app.py                    # Flask 主应用
│   ├── 渐进式分析 API 端点
│   ├── Server-Sent Events 实现
│   └── 多线程异步处理
├── superset_automation.py    # Superset 自动化
│   ├── Playwright 浏览器自动化
│   ├── Menu Download 机制
│   ├── 截图降级策略
│   └── 看板数据提取
├── ai_analyzer.py           # AI 分析模块
│   ├── BigModel.cn GLM-4.5 集成
│   ├── 多模态分析 (图像+文本)
│   ├── 渐进式分析回调
│   └── 综合结果整合
├── templates/
│   └── index.html           # Web 界面
│   ├── 实时进度显示
│   ├── 渐进式分析动画
│   └── Server-Sent Events 客户端
├── screenshots/             # 截图存储
├── requirements.txt         # Python 依赖
├── .env                     # 环境配置
├── start.sh                 # 启动脚本
└── CLAUDE.md               # Claude Code 配置
```

### 核心功能扩展

#### 1. 添加新的 AI 分析模板

在 `ai_analyzer.py` 的 `get_business_insights_template` 方法中添加新的模板：

```python
templates["新业务类型"] = """
基于 {dashboard_count} 个看板的分析，关于"{question}"的分析结果：

📊 **主要发现：**
- [具体发现内容]

💡 **建议：**
1. [建议1]
2. [建议2]
3. [建议3]

⚠️ **注意：** 具体分析需要基于实际看板数据。
"""
```

#### 2. 扩展自动化功能

在 `superset_automation.py` 中添加新的自动化操作：

```python
async def new_automation_function(self):
    """实现新的自动化功能"""
    try:
        # 1. 登录 Superset
        await self.login()
        
        # 2. 执行新的自动化任务
        # ...
        
        # 3. 清理资源
        await self.close()
        
    except Exception as e:
        logger.error(f"自动化功能失败: {e}")
        raise
```

#### 3. 添加新的渐进式分析事件

在 `app.py` 中添加新的事件类型：

```python
# 添加到 progress_callback 函数中
elif event['type'] == 'new_event_type':
    event_queue.put({
        'type': 'new_event_type',
        'data': event_data
    })
```

### 测试

系统包含多种测试类型：

- **单元测试**：`pytest -m unit`
- **集成测试**：`pytest -m integration`  
- **浏览器测试**：`pytest -m browser`
- **API 测试**：`pytest -m api`

运行所有测试：
```bash
pytest --cov=superset_automation --cov=app --cov=ai_analyzer --cov-report=term-missing
```

## 版本信息

**当前版本**: v2.0.0 - 渐进式分析版

**更新日志**:
- v2.0.0: 添加渐进式实时分析功能，集成 BigModel.cn GLM-4.5，实现 Menu Download 机制
- v1.0.0: 基础版本，支持简单的看板截图和 AI 分析

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

### 贡献指南

1. **Fork** 项目
2. **创建** 功能分支 (`git checkout -b feature/AmazingFeature`)
3. **提交** 更改 (`git commit -m 'Add some AmazingFeature'`)
4. **推送** 分支 (`git push origin feature/AmazingFeature`)
5. **创建** Pull Request

### 开发规范

- 遵循 PEP 8 代码规范
- 添加适当的注释和文档
- 编写对应的测试用例
- 确保所有测试通过

## 联系方式

如有问题或建议，请通过以下方式联系：

- **GitHub Issues**: 提交问题和功能请求
- **Email**: [your-email@example.com]

## 致谢

- **Superset**: 开源的商业智能平台
- **BigModel.cn**: 提供 AI 分析能力
- **Playwright**: 浏览器自动化工具
- **Flask**: 轻量级 Web 框架