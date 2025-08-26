#!/usr/bin/env python3
"""
测试 fallback 方法的日志输出格式
"""

import asyncio
import sys
import os
import logging

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from superset_automation import SupersetAutomation
from unittest.mock import patch

async def test_fallback_log_format():
    """测试 fallback 方法的日志输出格式"""
    try:
        print("🚀 测试 fallback 方法的日志输出格式...")
        
        # 创建 SupersetAutomation 实例
        automation = SupersetAutomation()
        
        # 模拟 API 失败，强制使用 fallback 方法
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("API connection failed")
            
            # 获取 dashboard 列表（将使用 fallback 方法）
            dashboards = await automation.get_dashboard_list()
        
        print(f"\n✅ Fallback 测试完成！获取到 {len(dashboards)} 个 dashboard")
        
    except Exception as e:
        print(f"❌ Fallback 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fallback_log_format())