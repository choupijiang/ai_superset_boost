#!/usr/bin/env python3
"""
测试 capture_dashboard_screenshot 函数
"""

import asyncio
import os
import sys
import pytest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest_asyncio

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from superset_automation import SupersetAutomation


@pytest_asyncio.fixture
async def temp_screenshots_dir():
    """创建临时截图目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # 清理临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def mock_automation(temp_screenshots_dir):
    """创建模拟的 SupersetAutomation 实例"""
    automation = SupersetAutomation()
    automation.screenshots_dir = temp_screenshots_dir
    automation.superset_url = "http://localhost:8088"
    automation.page = Mock()
    automation.page.goto = AsyncMock()
    automation.page.screenshot = AsyncMock()
    automation.page.content = AsyncMock()
    automation.page.text_content = AsyncMock()
    automation.page.wait_for_selector = AsyncMock()
    automation.page.url = "http://localhost:8088/dashboard/123"
    
    # Mock session cookies
    automation.session_cookies = {"session": "mock_session"}
    
    return automation


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_success(mock_automation):
    """测试成功捕获 dashboard 截图"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock 成功的 dashboard 加载
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=True)
    
    # Mock export 成功并创建实际文件
    export_mock = AsyncMock(return_value=True)
    original_export = mock_automation._export_dashboard_as_image
    
    async def mock_export_dashboard_as_image(filename, dashboard_title=None):
        # 创建实际文件来模拟成功
        filepath = os.path.join(mock_automation.screenshots_dir, filename)
        with open(filepath, 'w') as f:
            f.write("mock screenshot content")
        return True
    
    mock_automation._export_dashboard_as_image = mock_export_dashboard_as_image
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证结果
    assert result is not None
    assert result.endswith(".png")
    assert os.path.exists(result)
    assert "test_dashboard" in result
    
    # 验证调用
    mock_automation.page.goto.assert_called_once()
    mock_automation._wait_for_dashboard_load.assert_called_once()


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_fallback_success(mock_automation):
    """测试 fallback 方法成功"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock dashboard 加载成功，但 export 失败
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=True)
    mock_automation._export_dashboard_as_image = AsyncMock(return_value=False)
    mock_automation._capture_dashboard_screenshot_fallback = AsyncMock(return_value="/path/to/screenshot.png")
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证结果
    assert result == "/path/to/screenshot.png"
    
    # 验证调用
    mock_automation._wait_for_dashboard_load.assert_called_once()
    mock_automation._export_dashboard_as_image.assert_called_once()
    mock_automation._capture_dashboard_screenshot_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_retry_mechanism(mock_automation):
    """测试重试机制"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock 第一次失败，第二次成功
    call_count = 0
    async def mock_wait_for_dashboard_load(title):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return False
        return True
    
    mock_automation._wait_for_dashboard_load = mock_wait_for_dashboard_load
    mock_automation._export_dashboard_as_image = AsyncMock(return_value=True)
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard, max_retries=2)
    
    # 验证结果
    assert result is not None
    assert call_count == 2  # 应该调用了两次
    
    # 验证 goto 调用次数
    assert mock_automation.page.goto.call_count == 2


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_all_attempts_fail(mock_automation):
    """测试所有尝试都失败的情况"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock 所有尝试都失败
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=False)
    mock_automation.page.screenshot = AsyncMock(return_value=True)
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard, max_retries=1)
    
    # 验证结果
    assert result is None
    
    # 验证调用了两次（初始+一次重试）
    assert mock_automation._wait_for_dashboard_load.call_count == 2


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_no_browser_initialized(mock_automation):
    """测试浏览器未初始化的情况"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock page 为 None
    original_page = mock_automation.page
    mock_automation.page = None
    
    # Mock initialize_browser 设置 page
    async def mock_initialize_browser():
        mock_automation.page = original_page
    
    mock_automation.initialize_browser = AsyncMock(side_effect=mock_initialize_browser)
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=True)
    mock_automation._export_dashboard_as_image = AsyncMock(return_value=True)
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证结果
    assert result is not None
    
    # 验证调用了初始化
    mock_automation.initialize_browser.assert_called_once()


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_full_url(mock_automation):
    """测试使用完整 URL 的情况"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "http://localhost:8088/dashboard/123"
    }
    
    # Mock 成功
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=True)
    mock_automation._export_dashboard_as_image = AsyncMock(return_value=True)
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证结果
    assert result is not None
    
    # 验证使用了完整的 URL
    mock_automation.page.goto.assert_called_once_with("http://localhost:8088/dashboard/123")


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_relative_url(mock_automation):
    """测试使用相对 URL 的情况"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock 成功
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=True)
    mock_automation._export_dashboard_as_image = AsyncMock(return_value=True)
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证结果
    assert result is not None
    
    # 验证使用了完整的 URL（拼接了 superset_url）
    mock_automation.page.goto.assert_called_once_with("http://localhost:8088/dashboard/123")




@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_filename_cleaning(mock_automation):
    """测试文件名清理功能"""
    # 准备测试数据（包含特殊字符）
    dashboard = {
        "title": "Test Dashboard @#$% Special & Characters",
        "url": "/dashboard/123"
    }
    
    # Mock 成功
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=True)
    mock_automation._export_dashboard_as_image = AsyncMock(return_value=True)
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证结果
    assert result is not None
    assert "test_dashboard_special_characters" in result
    assert not any(char in result for char in ['@', '#', '$', '%', '&'])


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_exception_handling(mock_automation):
    """测试异常处理"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock 抛出异常
    mock_automation.page.goto = AsyncMock(side_effect=Exception("Navigation failed"))
    
    # 执行测试
    result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证结果
    assert result is None


@pytest.mark.asyncio
async def test_capture_dashboard_screenshot_logging(mock_automation, caplog):
    """测试日志记录"""
    # 准备测试数据
    dashboard = {
        "title": "Test Dashboard",
        "url": "/dashboard/123"
    }
    
    # Mock 成功
    mock_automation._wait_for_dashboard_load = AsyncMock(return_value=True)
    mock_automation._export_dashboard_as_image = AsyncMock(return_value=True)
    
    # 执行测试
    with caplog.at_level('INFO'):
        result = await mock_automation.capture_dashboard_screenshot(dashboard)
    
    # 验证日志记录
    assert "📸 Capturing dashboard: Test Dashboard" in caplog.text
    assert "✅ Dashboard 'Test Dashboard' loaded successfully" in caplog.text
    assert "🔄 Attempting Superset Download as Image..." in caplog.text


def test_clean_filename_function():
    """测试 _clean_filename 函数"""
    # 创建自动化实例
    automation = SupersetAutomation()
    
    # 测试各种文件名清理情况
    test_cases = [
        ("Simple Dashboard", "simple_dashboard"),
        ("Dashboard@#$%", "dashboard"),
        ("Dashboard with Spaces", "dashboard_with_spaces"),
        ("Dashboard-with-dashes", "dashboard_with_dashes"),
        ("Dashboard__underscores", "dashboard__underscores"),
        ("", "unknown"),
        ("   ", "unknown"),
    ]
    
    for input_name, expected in test_cases:
        result = automation._clean_filename(input_name)
        assert result == expected, f"输入 '{input_name}' 应该得到 '{expected}'，但得到 '{result}'"


async def run_integration_test():
    """运行集成测试（需要真实的 Superset 环境）"""
    print("🚀 开始集成测试...")
    
    # 检查环境变量
    required_env_vars = ['SUPERSET_URL', 'SUPERSET_USERNAME', 'SUPERSET_PASSWORD']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        print("跳过集成测试")
        return
    
    try:
        # 创建真实的自动化实例
        async with SupersetAutomation() as automation:
            # 获取 dashboard 列表
            dashboards = await automation.get_dashboard_list()
            
            if not dashboards:
                print("❌ 没有找到可用的 dashboard")
                return
            
            # 选择第一个 dashboard 进行测试
            test_dashboard = dashboards[0]
            print(f"📸 测试 dashboard: {test_dashboard['title']}")
            
            # 测试截图功能
            screenshot_path = await automation.capture_dashboard_screenshot(test_dashboard)
            
            if screenshot_path:
                print(f"✅ 截图成功: {screenshot_path}")
                print(f"📁 文件大小: {os.path.getsize(screenshot_path)} bytes")
            else:
                print("❌ 截图失败")
                
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行单元测试
    print("🧪 运行单元测试...")
    pytest.main([__file__, "-v", "--tb=short"])
    
    # 运行集成测试
    print("\n🔧 运行集成测试...")
    asyncio.run(run_integration_test())