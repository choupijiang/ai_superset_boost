# 智能商业分析系统架构文档

## 系统概述

这是一个基于Superset的智能商业分析系统，集成了自动化数据采集、AI分析和FAISS向量搜索功能。系统通过Web界面为用户提供智能化的业务问题解答服务。

## 核心特性

- 🔗 **真实Superset连接** - 自动连接到Superset实例进行数据采集
- 🤖 **AI驱动分析** - 使用BigModel.cn进行智能业务分析
- 🔍 **FAISS向量搜索** - 基于嵌入的语义相似性搜索
- 📸 **自动化截图** - 智能捕获仪表板和图表截图
- 🎯 **智能仪表板选择** - 根据问题自动选择相关仪表板
- 🌐 **现代化Web界面** - 响应式设计，支持实时分析

## 系统架构图

```mermaid
graph TB
    subgraph "用户界面层"
        UI[Web浏览器]
        UI -->|HTTP请求| FLASK
    end
    
    subgraph "应用服务层"
        FLASK[Flask Web服务器<br/>app.py]
        FLASK -->|路由处理| ROUTES
        
        subgraph "核心路由"
            ROUTES[路由控制器]
            ROUTES -->|首页| INDEX[首页渲染]
            ROUTES -->|分析请求| ANALYZE[智能分析]
            ROUTES -->|状态查询| STATUS[系统状态]
            ROUTES -->|刷新上下文| REFRESH[上下文刷新]
        end
    end
    
    subgraph "业务逻辑层"
        AI[AI分析器<br/>ai_analyzer.py]
        CONTEXT[智能上下文系统<br/>context_manager.py]
        SUPERSET[Superset自动化<br/>superset_automation.py]
        FAISS[FAISS索引管理器<br/>faiss_index_manager.py]
        
        FLASK -->|调用| AI
        FLASK -->|调用| CONTEXT
        FLASK -->|调用| SUPERSET
        CONTEXT -->|使用| FAISS
    end
    
    subgraph "数据存储层"
        SCREENSHOTS[截图存储<br/>screenshots/]
        CONTEXT_FILES[上下文文件<br/>context/]
        FAISS_INDEX[FAISS索引<br/>faiss_index/]
        DASHBOARD_DATA[仪表板数据<br/>dashboard_data/]
        LOGS[日志文件<br/>*.log]
    end
    
    subgraph "外部服务层"
        SUPERSET_SERVICE[Superset服务<br/>http://localhost:8088]
        BIGMODEL[BigModel.cn API<br/>AI服务]
    end
    
    SUPERSET -->|浏览器自动化| SUPERSET_SERVICE
    AI -->|API调用| BIGMODEL
    SUPERSET -->|截图存储| SCREENSHOTS
    CONTEXT -->|上下文存储| CONTEXT_FILES
    FAISS -->|索引存储| FAISS_INDEX
    
    style UI fill:#e1f5fe
    style FLASK fill:#f3e5f5
    style AI fill:#e8f5e8
    style CONTEXT fill:#fff3e0
    style SUPERSET fill:#fce4ec
    style FAISS fill:#f1f8e9
```

## 详细模块架构

### 1. 启动与部署模块

```mermaid
graph LR
    subgraph "系统启动流程"
        START[start.sh] -->|环境检查| ENV_CHECK[环境变量检查]
        ENV_CHECK -->|依赖验证| DEPS_CHECK[依赖检查]
        DEPS_CHECK -->|Superset连接| SUPERSET_TEST[连接测试]
        SUPERSET_TEST -->|创建目录| MKDIR[创建必要目录]
        MKDIR -->|启动应用| FLASK_START[启动Flask应用]
    end
    
    subgraph "环境配置"
        ENV_FILE[.env文件]
        ENV_CHECK -->|读取| ENV_FILE
        ENV_FILE -->|配置信息| CONFIG{配置信息}
        CONFIG -->|Superset凭据| SUPERSET_CREDS
        CONFIG -->|AI API密钥| AI_CREDS
        CONFIG -->|系统设置| SYS_CONFIG
    end
    
    subgraph "启动脚本功能"
        PYTHON_CHECK[Python环境检查]
        PLAYWRIGHT_CHECK[Playwright依赖检查]
        SUPERSET_CONN[Superset连接测试]
        DIRECTORY_SETUP[目录结构创建]
        SERVICE_START[服务启动]
        
        START -->|步骤1| PYTHON_CHECK
        PYTHON_CHECK -->|步骤2| PLAYWRIGHT_CHECK
        PLAYWRIGHT_CHECK -->|步骤3| SUPERSET_CONN
        SUPERSET_CONN -->|步骤4| DIRECTORY_SETUP
        DIRECTORY_SETUP -->|步骤5| SERVICE_START
    end
    
    style START fill:#4caf50
    style ENV_CHECK fill:#2196f3
    style DEPS_CHECK fill:#ff9800
    style SUPERSET_TEST fill:#9c27b0
    style FLASK_START fill:#f44336
```

**启动脚本详细功能 (start.sh):**

1. **环境检查阶段**
   - Python环境检测 (支持 python3 和 python 命令)
   - 环境变量文件 (.env) 检查
   - 必要配置项验证 (Superset和API凭据)

2. **依赖验证阶段**
   - Playwright库安装检查
   - 自动安装缺失依赖
   - Chromium浏览器安装

3. **连接测试阶段**
   - 异步Superset连接测试
   - 登录功能验证
   - 仪表板列表获取测试
   - 连接失败时的降级处理

4. **环境准备阶段**
   - 创建screenshots目录 (截图存储)
   - 创建dashboard_data目录 (仪表板数据)
   - 权限和路径验证

5. **服务启动阶段**
   - Flask应用启动
   - 系统信息展示
   - 访问地址和健康检查端点显示

### 2. 数据采集层架构

```mermaid
graph TB
    subgraph "Superset自动化模块"
        SUPerset_AUTO[SupersetAutomation类]
        SUPerset_AUTO -->|初始化| INIT[初始化配置]
        INIT -->|设置浏览器| PLAYWRIGHT[Playwright浏览器]
        
        SUPerset_AUTO -->|登录流程| LOGIN[登录Superset]
        LOGIN -->|获取仪表板| GET_DASHBOARDS[获取仪表板列表]
        GET_DASHBOARDS -->|捕获截图| CAPTURE_SCREEN[捕获仪表板截图]
        CAPTURE_SCREEN -->|图表处理| PROCESS_CHARTS[处理图表数据]
        
        subgraph "渐进式处理"
            PROGRESSIVE[渐进式捕获]
            PROGRESSIVE -->|回调函数| CALLBACK[分析回调]
            CALLBACK -->|实时分析| REALTIME_ANALYSIS[实时AI分析]
        end
    end
    
    subgraph "数据流"
        DATA_FLOW[数据流向]
        SUPerset_SERVICE[Superset服务] -->|HTML内容| SUPerset_AUTO
        SUPerset_AUTO -->|截图文件| SCREENSHOTS_DIR[screenshots/]
        SUPerset_AUTO -->|元数据| DASHBOARD_META[仪表板元数据]
    end
    
    style SUPerset_AUTO fill:#e91e63
    style PLAYWRIGHT fill:#9c27b0
    style LOGIN fill:#673ab7
    style PROGRESSIVE fill:#3f51b5
```

### 3. AI分析层架构

```mermaid
graph TB
    subgraph "AI分析器模块"
        AI_ANALYZER[AIAnalyzer类]
        AI_ANALYZER -->|初始化| AI_INIT[AI配置初始化]
        AI_INIT -->|API客户端| OPENAI_CLIENT[OpenAI客户端]
        
        subgraph "分析功能"
            SINGLE_DASH[单个仪表板分析]
            MULTI_DASH[多仪表板综合分析]
            VISION_ANALYSIS[视觉分析]
            TEXT_ANALYSIS[文本分析]
        end
        
        AI_ANALYZER -->|主要方法| SINGLE_DASH
        AI_ANALYZER -->|组合分析| MULTI_DASH
        SINGLE_DASH -->|图像处理| VISION_ANALYSIS
        MULTI_DASH -->|文本处理| TEXT_ANALYSIS
        
        subgraph "响应处理"
            CLEAN_RESPONSE[响应清理]
            FORMAT_OUTPUT[格式化输出]
            ERROR_HANDLING[错误处理]
        end
        
        VISION_ANALYSIS -->|原始响应| CLEAN_RESPONSE
        TEXT_ANALYSIS -->|原始响应| CLEAN_RESPONSE
        CLEAN_RESPONSE -->|清理后| FORMAT_OUTPUT
        FORMAT_OUTPUT -->|最终结果| ERROR_HANDLING
    end
    
    subgraph "API集成"
        BIGMODEL_API[BigModel.cn API]
        OPENAI_CLIENT -->|RESTful调用| BIGMODEL_API
        BIGMODEL_API -->|嵌入向量| EMBEDDINGS[文本嵌入]
        BIGMODEL_API -->|视觉分析| VISION_AI[视觉AI]
    end
    
    style AI_ANALYZER fill:#4caf50
    style SINGLE_DASH fill:#8bc34a
    style MULTI_DASH fill:#cddc39
    style CLEAN_RESPONSE fill:#ffeb3b
```

### 4. 上下文管理层架构

```mermaid
graph TB
    subgraph "智能上下文系统"
        SMART_CONTEXT[SmartContextSystem]
        SMART_CONTEXT -->|组合模块| CONTEXT_MGR[ContextManager]
        SMART_CONTEXT -->|仪表板分析| DASH_ANALYZER[DashboardAnalyzer]
        SMART_CONTEXT -->|仪表板选择| DASH_SELECTOR[DashboardSelector]
        
        subgraph "上下文管理"
            CONTEXT_MGR -->|缓存管理| CACHE[上下文缓存]
            CONTEXT_MGR -->|文件存储| FILE_STORAGE[文件存储]
            CONTEXT_MGR -->|过期管理| EXPIRY[过期管理]
        end
        
        subgraph "仪表板分析器"
            DASH_ANALYZER -->|内容分析| CONTENT_ANALYSIS[内容分析]
            DASH_ANALYZER -->|图表分析| CHART_ANALYSIS[图表分析]
            CONTENT_ANALYSIS -->|AI分析| AI_ANALYSIS_CALL
            CHART_ANALYSIS -->|AI分析| AI_ANALYSIS_CALL
        end
        
        subgraph "仪表板选择器"
            DASH_SELECTOR -->|传统方法| AI_SELECTION[AI选择]
            DASH_SELECTOR -->|新方法| FAISS_SELECTION[FAISS选择]
            FAISS_SELECTION -->|向量搜索| VECTOR_SEARCH[向量搜索]
        end
    end
    
    subgraph "FAISS集成"
        FAISS_MGR[FAISSIndexManager]
        FAISS_MGR -->|索引管理| INDEX_MGMT[索引管理]
        FAISS_MGR -->|嵌入服务| EMBEDDING_SVC[嵌入服务]
        EMBEDDING_SVC -->|API调用| BIGMODEL_EMBED[BigModel嵌入]
        INDEX_MGMT -->|相似性搜索| SIMILARITY_SEARCH[相似性搜索]
    end
    
    DASH_SELECTOR -->|使用| FAISS_MGR
    FAISS_SELECTION -->|调用| SIMILARITY_SEARCH
    
    style SMART_CONTEXT fill:#2196f3
    style CONTEXT_MGR fill:#1976d2
    style DASH_ANALYZER fill:#0d47a1
    style DASH_SELECTOR fill:#1565c0
    style FAISS_MGR fill:#00695c
```

### 5. FAISS向量搜索架构

```mermaid
graph TB
    subgraph "FAISS嵌入服务"
        EMBEDDING_SVC[FAISSEmbeddingService]
        EMBEDDING_SVC -->|初始化| INIT_INDEX[创建索引]
        EMBEDDING_SVC -->|嵌入生成| GEN_EMBEDDING[生成嵌入]
        EMBEDDING_SVC -->|批量处理| BATCH_PROCESS[批量处理]
        EMBEDDING_SVC -->|搜索功能| SEARCH[相似性搜索]
        
        subgraph "索引类型"
            FLAT_INDEX[Flat索引]
            IVF_INDEX[IVF索引]
            HNSW_INDEX[HNSW索引]
        end
        
        INIT_INDEX -->|选择| FLAT_INDEX
        GEN_EMBEDDING -->|文本处理| TEXT_PROCESSING[文本处理]
        TEXT_PROCESSING -->|API调用| BIGMODEL_API
        BIGMODEL_API -->|嵌入向量| EMBEDDING_VECTOR[嵌入向量]
        EMBEDDING_VECTOR -->|添加到索引| ADD_TO_INDEX[添加到索引]
    end
    
    subgraph "索引管理器"
        INDEX_MGR[FAISSIndexManager]
        INDEX_MGR -->|上下文集成| CONTEXT_INTEGRATION[上下文集成]
        INDEX_MGR -->|自动更新| AUTO_UPDATE[自动更新]
        INDEX_MGR -->|状态监控| STATUS_MONITOR[状态监控]
        
        CONTEXT_INTEGRATION -->|构建索引| BUILD_INDEX[构建索引]
        BUILD_INDEX -->|从上下文| FROM_CONTEXTS[从上下文数据]
        FROM_CONTEXTS -->|批量嵌入| BATCH_EMBEDDINGS[批量嵌入]
    end
    
    subgraph "数据持久化"
        INDEX_FILE[FAISS索引文件]
        METADATA_FILE[元数据文件]
        CONTEXT_FILES[上下文文件]
        
        EMBEDDING_SVC -->|保存索引| INDEX_FILE
        EMBEDDING_SVC -->|保存元数据| METADATA_FILE
        INDEX_MGR -->|读取上下文| CONTEXT_FILES
    end
    
    style EMBEDDING_SVC fill:#009688
    style INDEX_MGR fill:#004d40
    style BIGMODEL_API fill:#795548
```

### 6. Web界面层架构

```mermaid
graph TB
    subgraph "前端界面"
        HTML[HTML模板<br/>templates/index.html]
        CSS[CSS样式]
        JAVASCRIPT[JavaScript]
        
        HTML -->|结构| LAYOUT[页面布局]
        CSS -->|样式| STYLING[视觉样式]
        JAVASCRIPT -->|交互| INTERACTION[用户交互]
        
        subgraph "主要组件"
            HEADER[页面头部]
            QUESTION_INPUT[问题输入区]
            ANALYSIS_RESULT[分析结果显示]
            STATUS_DISPLAY[状态显示]
            LOADING[加载指示器]
        end
        
        LAYOUT -->|包含| HEADER
        LAYOUT -->|包含| QUESTION_INPUT
        LAYOUT -->|包含| ANALYSIS_RESULT
        LAYOUT -->|包含| STATUS_DISPLAY
        INTERACTION -->|控制| LOADING
    end
    
    subgraph "后端API"
        API_ENDPOINTS[API端点]
        API_ENDPOINTS -->|/| HOME[首页]
        API_ENDPOINTS -->|/analyze| ANALYZE_API[分析接口]
        API_ENDPOINTS -->|/context-status| STATUS_API[状态接口]
        API_ENDPOINTS -->|/context-refresh| REFRESH_API[刷新接口]
        API_ENDPOINTS -->|/screenshots/<file>| SCREENSHOT_API[截图接口]
        
        ANALYZE_API -->|异步处理| ASYNC_ANALYSIS[异步分析]
        ASYNC_ANALYSIS -->|业务逻辑| BUSINESS_LOGIC[业务逻辑]
    end
    
    subgraph "数据流"
        USER_INPUT[用户输入]
        USER_INPUT -->|AJAX| JAVASCRIPT
        JAVASCRIPT -->|API调用| API_ENDPOINTS
        API_ENDPOINTS -->|JSON响应| JAVASCRIPT
        JAVASCRIPT -->|DOM更新| ANALYSIS_RESULT
    end
    
    style HTML fill:#f44336
    style CSS fill:#e91e63
    style JAVASCRIPT fill:#9c27b0
    style API_ENDPOINTS fill:#673ab7
```

## 用户旅程图

```mermaid
journey
    title 用户使用智能商业分析系统的完整旅程
    
    section 系统启动
      系统启动: 5: 用户
      环境检查: 3: 系统
      依赖验证: 3: 系统
      Superset连接测试: 4: 系统
      Web服务器启动: 5: 系统
    
    section 用户交互
      访问Web界面: 5: 用户
      查看系统状态: 3: 用户
      输入业务问题: 5: 用户
      提交分析请求: 4: 用户
    
    section 后端处理
      接收分析请求: 3: 系统
      获取仪表板列表: 4: 系统
      更新上下文信息: 4: 系统
      智能选择相关仪表板: 5: 系统
      捕获仪表板截图: 4: 系统
      AI分析仪表板内容: 5: 系统
      综合分析结果: 4: 系统
    
    section 结果展示
      返回分析结果: 5: 系统
      显示分析内容: 5: 用户
      展示相关截图: 4: 用户
      查看详细数据: 3: 用户
    
    section 系统维护
      刷新上下文: 3: 管理员
      查看系统日志: 2: 管理员
      监控系统状态: 3: 管理员
```

## 数据流图

```mermaid
graph LR
    subgraph "输入数据"
        USER_QUESTION[用户问题]
        SUPERSET_URL[Superset URL]
        DASHBOARD_LIST[仪表板列表]
    end
    
    subgraph "处理流程"
        STEP1[问题理解]
        STEP2[仪表板选择]
        STEP3[数据采集]
        STEP4[AI分析]
        STEP5[结果整合]
    end
    
    subgraph "中间数据"
        SELECTED_DASHBOARDS[选中的仪表板]
        SCREENSHOTS[截图文件]
        CONTEXT_DATA[上下文数据]
        AI_RESPONSES[AI响应]
        CLEANED_RESPONSES[清理后的响应]
    end
    
    subgraph "输出结果"
        FINAL_ANSWER[最终答案]
        RELATED_IMAGES[相关图片]
        ANALYSIS_METADATA[分析元数据]
    end
    
    USER_QUESTION --> STEP1
    SUPERSET_URL --> STEP1
    DASHBOARD_LIST --> STEP2
    
    STEP1 --> STEP2
    STEP2 --> SELECTED_DASHBOARDS
    SELECTED_DASHBOARDS --> STEP3
    
    STEP3 --> SCREENSHOTS
    STEP3 --> CONTEXT_DATA
    SCREENSHOTS --> STEP4
    CONTEXT_DATA --> STEP4
    
    STEP4 --> AI_RESPONSES
    AI_RESPONSES --> CLEANED_RESPONSES
    CLEANED_RESPONSES --> STEP5
    
    STEP5 --> FINAL_ANSWER
    STEP5 --> RELATED_IMAGES
    STEP5 --> ANALYSIS_METADATA
```

## 技术栈详情

### 后端技术栈
- **Python 3.x** - 主要编程语言
- **Flask 2.3.3** - Web框架
- **Playwright** - 浏览器自动化
- **OpenAI** - AI客户端
- **FAISS** - 向量搜索库
- **NumPy** - 数值计算
- **Requests** - HTTP客户端
- **python-dotenv** - 环境变量管理

### 前端技术栈
- **HTML5** - 页面结构
- **CSS3** - 样式设计
- **JavaScript** - 交互逻辑
- **响应式设计** - 移动端适配

### 外部服务
- **Superset** - 数据可视化平台
- **BigModel.cn** - AI服务提供商

### 数据存储
- **文件系统** - 截图和上下文存储
- **FAISS索引** - 向量搜索索引
- **Markdown文件** - 上下文数据

## 部署架构

```mermaid
graph TB
    subgraph "服务器环境"
        WEB_SERVER[Web服务器]
        APP_SERVER[应用服务器]
        DB_SERVER[数据库服务器]
        
        WEB_SERVER -->|反向代理| APP_SERVER
        APP_SERVER -->|数据存储| DB_SERVER
    end
    
    subgraph "应用部署"
        FLASK_APP[Flask应用]
        SUPERSET_SERVICE[Superset服务]
        REDIS_CACHE[Redis缓存]
        
        FLASK_APP -->|依赖| PYTHON_ENV[Python环境]
        SUPERSET_SERVICE -->|依赖| DOCKER[Docker容器]
    end
    
    subgraph "外部依赖"
        BIGMODEL_API[BigModel.cn API]
        CDN_SERVICE[CDN服务]
        MONITORING[监控服务]
        
        FLASK_APP -->|API调用| BIGMODEL_API
        FLASK_APP -->|静态资源| CDN_SERVICE
        FLASK_APP -->|日志| MONITORING
    end
    
    style WEB_SERVER fill:#4caf50
    style APP_SERVER fill:#2196f3
    style DB_SERVER fill:#ff9800
```

## 系统监控与日志

```mermaid
graph TB
    subgraph "日志系统"
        APP_LOG[应用日志<br/>app.log]
        AI_LOG[AI分析日志<br/>ai_analyzer.log]
        SUPERSET_LOG[Superset日志<br/>superset_automation.log]
        CONTEXT_LOG[上下文日志<br/>context_manager.log]
        FAISS_LOG[FAISS日志<br/>faiss_*.log]
    end
    
    subgraph "监控指标"
        PERFORMANCE[性能监控]
        ERROR_TRACKING[错误追踪]
        USAGE_STATS[使用统计]
        HEALTH_CHECK[健康检查]
    end
    
    subgraph "告警系统"
        ALERTING[告警系统]
        NOTIFICATION[通知服务]
        DASHBOARD[监控仪表板]
    end
    
    APP_LOG -->|日志分析| PERFORMANCE
    AI_LOG -->|AI指标| PERFORMANCE
    SUPERSET_LOG -->|自动化指标| PERFORMANCE
    CONTEXT_LOG -->|上下文指标| PERFORMANCE
    FAISS_LOG -->|搜索指标| PERFORMANCE
    
    PERFORMANCE -->|异常检测| ALERTING
    ERROR_TRACKING -->|错误通知| ALERTING
    ALERTING -->|告警推送| NOTIFICATION
    ALERTING -->|可视化| DASHBOARD
```

## 安全考虑

### 数据安全
- 环境变量存储敏感信息
- API密钥加密存储
- 文件访问权限控制
- 请求频率限制

### 系统安全
- 输入验证和清理
- SQL注入防护
- XSS攻击防护
- CSRF保护

### 网络安全
- HTTPS加密传输
- API访问认证
- 防火墙配置
- 安全头部设置

## 性能优化

### 缓存策略
- 上下文数据缓存
- FAISS索引缓存
- 静态资源缓存
- AI响应缓存

### 异步处理
- 异步任务队列
- 非阻塞I/O操作
- 并发处理优化
- 资源池管理

### 数据库优化
- 索引优化
- 查询优化
- 连接池管理
- 读写分离

## 扩展性设计

### 水平扩展
- 微服务架构
- 负载均衡
- 容器化部署
- 自动扩缩容

### 功能扩展
- 插件系统
- API扩展
- 多语言支持
- 第三方集成

## 总结

这个智能商业分析系统采用现代化的架构设计，集成了多种先进技术：

1. **模块化设计** - 各个功能模块独立，便于维护和扩展
2. **异步处理** - 支持长时间运行的分析任务
3. **智能化** - 结合AI和向量搜索提供智能分析
4. **可扩展性** - 支持多种部署方式和扩展需求
5. **用户友好** - 现代化的Web界面和良好的用户体验

系统通过FAISS向量搜索解决了传统AI选择中的token限制问题，提供了更加高效和可扩展的解决方案。