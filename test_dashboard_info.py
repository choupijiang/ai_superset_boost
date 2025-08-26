#!/usr/bin/env python3
"""
测试脚本：获取 Superset 中所有 dashboard 的 ID、名称和发布状态
"""

import asyncio
import sys
import os
import logging

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 SupersetAutomation 类
from superset_automation import SupersetAutomation

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_dashboard_list():
    """测试获取 dashboard 列表并打印信息"""
    try:
        logger.info("🚀 开始测试获取 Superset dashboard 列表...")
        
        # 创建 SupersetAutomation 实例
        automation = SupersetAutomation()
        
        # 获取 dashboard 列表
        dashboards = await automation.get_dashboard_list()
        
        if not dashboards:
            logger.warning("⚠️ 没有找到任何 dashboard")
            return
        
        logger.info(f"✅ 成功获取到 {len(dashboards)} 个 dashboard")
        logger.info("=" * 80)
        logger.info("Dashboard 列表:")
        logger.info("=" * 80)
        
        # 打印每个 dashboard 的信息
        for i, dashboard in enumerate(dashboards, 1):
            dashboard_id = dashboard.get('id', 'N/A')
            title = dashboard.get('title', 'N/A')
            published = dashboard.get('published', False)
            url = dashboard.get('url', 'N/A')
            
            # 格式化发布状态
            status = "🟢 Public" if published else "🔴 Private"
            
            logger.info(f"{i:2d}. ID: {dashboard_id:4d} | {title:40s} | {status:10s} | URL: {url}")
        
        logger.info("=" * 80)
        
        # 统计信息
        public_count = sum(1 for d in dashboards if d.get('published', False))
        private_count = len(dashboards) - public_count
        
        logger.info(f"📊 统计信息:")
        logger.info(f"   总计: {len(dashboards)} 个 dashboard")
        logger.info(f"   公开: {public_count} 个")
        logger.info(f"   私有: {private_count} 个")
        
        # 测试 API vs Web Scraping 的使用情况
        logger.info("\n🔧 测试方法信息:")
        logger.info("✅ 测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主函数"""
    try:
        await test_dashboard_list()
    except KeyboardInterrupt:
        logger.info("⚠️ 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 主程序错误: {e}")

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())