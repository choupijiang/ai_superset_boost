#!/bin/bash

# 智能商业分析系统启动脚本 - 真实 Superset 连接版本

echo "🚀 启动智能商业分析系统 (真实连接版)..."
echo "=================================================="

# 检查 Python 环境
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ 未找到 Python 环境，请先安装 Python"
    exit 1
fi

echo "✅ 使用 Python: $PYTHON_CMD"

# 检查环境变量
if [ ! -f .env ]; then
    echo "⚠️  警告：未找到 .env 文件"
    echo "请确保已配置 Superset 和 DeepSeek API 凭据"
    echo ""
    echo "需要的环境变量："
    echo "  SUPERSET_URL=http://localhost:8088"
    echo "  SUPERSET_USERNAME=admin"
    echo "  SUPERSET_PASSWORD=admin"
    echo "  OPENAI_API_KEY=your-api-key"
    echo ""
    read -p "是否继续启动？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查 Playwright 依赖
echo "🔍 检查依赖..."
$PYTHON_CMD -c "import playwright; print('✅ Playwright 已安装')" 2>/dev/null || {
    echo "❌ Playwright 未安装，正在安装..."
    pip install playwright
    playwright install chromium
}

# 检查 Superset 连接
echo "🔍 测试 Superset 连接..."
$PYTHON_CMD -c "
import asyncio
import sys
sys.path.append('.')
from superset_automation import SupersetAutomation

async def test_connection():
    try:
        async with SupersetAutomation() as automation:
            if await automation.login_to_superset():
                dashboards = await automation.get_dashboard_list()
                print(f'✅ Superset 连接成功，发现 {len(dashboards)} 个仪表板')
                return True
            else:
                print('❌ Superset 登录失败')
                return False
    except Exception as e:
        print(f'❌ 连接测试失败: {e}')
        return False

asyncio.run(test_connection())
"

if [ $? -ne 0 ]; then
    echo "⚠️  Superset 连接测试失败，但仍然可以启动系统"
    echo "系统将使用模拟数据作为备选方案"
fi

# 创建必要的目录
mkdir -p screenshots
mkdir -p dashboard_data

echo "🌐 启动 Web 服务器..."
echo "=================================================="
echo "📱 访问地址: http://localhost:5002"
echo "🔗 健康检查: http://localhost:5002/health"
echo "📊 系统功能:"
echo "   ✅ 真实 Superset 连接"
echo "   ✅ 动态仪表板发现"
echo "   ✅ 智能截图捕获"
echo "   ✅ AI 商业分析 (BigModel.cn)"
echo "   ✅ 中文支持"
echo "   ✅ 实时分析"
echo "   ✅ 完善的错误处理"
echo ""
echo "⚠️  按 Ctrl+C 停止服务器"
echo "=================================================="

# 启动 Flask 应用
$PYTHON_CMD app.py