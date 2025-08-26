#!/usr/bin/env python3
"""
智能商业分析系统测试脚本
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append('.')

def test_imports():
    """测试所有模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        from superset_automation import SupersetAutomation
        print("✅ SupersetAutomation 导入成功")
    except Exception as e:
        print(f"❌ SupersetAutomation 导入失败: {e}")
        return False
    
    try:
        from ai_analyzer import AIAnalyzer
        print("✅ AIAnalyzer 导入成功")
    except Exception as e:
        print(f"❌ AIAnalyzer 导入失败: {e}")
        return False
    
    try:
        from app import app
        print("✅ Flask 应用导入成功")
    except Exception as e:
        print(f"❌ Flask 应用导入失败: {e}")
        return False
    
    return True

def test_ai_analyzer():
    """测试AI分析器"""
    print("\n🤖 测试AI分析器...")
    
    try:
        from ai_analyzer import AIAnalyzer
        ai = AIAnalyzer()
        print(f"✅ AI分析器初始化成功")
        print(f"   - 提供商: {ai.ai_provider}")
        print(f"   - 模型: {ai.openai_model}")
        print(f"   - API密钥: {'已配置' if ai.openai_api_key else '未配置'}")
        return True
    except Exception as e:
        print(f"❌ AI分析器测试失败: {e}")
        return False

def test_superset_automation():
    """测试Superset自动化"""
    print("\n🔐 测试Superset自动化...")
    
    try:
        from superset_automation import SupersetAutomation
        
        async def test_automation():
            async with SupersetAutomation() as automation:
                print(f"✅ Superset自动化初始化成功")
                print(f"   - URL: {automation.superset_url}")
                print(f"   - 用户名: {automation.username}")
                print(f"   - 截图目录: {automation.screenshots_dir}")
                return True
        
        return asyncio.run(test_automation())
    except Exception as e:
        print(f"❌ Superset自动化测试失败: {e}")
        return False

def test_flask_app():
    """测试Flask应用"""
    print("\n🌐 测试Flask应用...")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # 测试健康检查
            response = client.get('/health')
            if response.status_code == 200:
                print("✅ 健康检查端点正常")
                data = response.get_json()
                print(f"   - 状态: {data['status']}")
                print(f"   - 时间: {data['timestamp']}")
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
            
            # 测试首页
            response = client.get('/')
            if response.status_code == 200:
                print("✅ 首页正常")
            else:
                print(f"❌ 首页访问失败: {response.status_code}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Flask应用测试失败: {e}")
        return False

def test_directories():
    """测试必要目录"""
    print("\n📁 测试必要目录...")
    
    directories = ['screenshots', 'dashboard_data', 'logs']
    all_good = True
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"✅ {directory} 目录存在")
        else:
            print(f"⚠️  {directory} 目录不存在")
            all_good = False
    
    return all_good

def test_environment():
    """测试环境变量"""
    print("\n🔧 测试环境变量...")
    
    env_vars = [
        'SUPERSET_URL',
        'SUPERSET_USERNAME', 
        'SUPERSET_PASSWORD',
        'OPENAI_API_KEY',
        'SECRET_KEY'
    ]
    
    all_good = True
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: 已配置")
        else:
            print(f"⚠️  {var}: 未配置")
            all_good = False
    
    return all_good

def main():
    """主测试函数"""
    print("🚀 智能商业分析系统测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("AI分析器", test_ai_analyzer),
        ("Superset自动化", test_superset_automation),
        ("Flask应用", test_flask_app),
        ("必要目录", test_directories),
        ("环境变量", test_environment)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统已准备就绪。")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)