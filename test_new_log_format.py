#!/usr/bin/env python3
"""
测试新的日志输出格式
"""

import asyncio
import sys
import os
import logging

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from superset_automation import SupersetAutomation

async def test_new_log_format():
    """测试新的日志输出格式"""
    try:
        print("🚀 测试新的日志输出格式...")
        
        # 创建 SupersetAutomation 实例
        automation = SupersetAutomation()
        
        # 获取 dashboard 列表
        dashboards = await automation.get_dashboard_list()
        
        print(f"\n✅ 测试完成！获取到 {len(dashboards)} 个 dashboard")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_log_format())