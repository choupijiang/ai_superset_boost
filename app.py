from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import os
import asyncio
import json
import logging
from datetime import datetime
from superset_automation import SupersetAutomation
from ai_analyzer import AIAnalyzer
from context_manager import SmartContextSystem
from queue import Queue
import threading
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configure logging - Comprehensive logging as described in README.md
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局变量存储智能上下文系统
smart_context_system = None

def initialize_system():
    """初始化系统组件，包括FAISS索引"""
    global smart_context_system
    
    try:
        logger.info("🚀 初始化智能商业分析系统...")
        
        # 初始化AI分析器
        ai_analyzer = AIAnalyzer()
        
        # 初始化智能上下文系统
        smart_context_system = SmartContextSystem(ai_analyzer, use_faiss=True)
        
        # 检查FAISS索引状态
        if smart_context_system.use_faiss and smart_context_system.faiss_index_manager:
            logger.info("🔍 检查FAISS索引状态...")
            
            # 尝试加载现有索引
            if not smart_context_system.faiss_index_manager.load_existing_index():
                logger.info("📝 未找到现有FAISS索引，开始构建新索引...")
                
                # 从context下的markdown文件构建FAISS索引
                if smart_context_system.faiss_index_manager.build_index_from_contexts():
                    logger.info("✅ FAISS索引构建成功")
                else:
                    logger.warning("⚠️ FAISS索引构建失败，将使用AI选择作为备选")
            else:
                logger.info("✅ FAISS索引加载成功")
        
        logger.info("🎉 系统初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {e}")
        return False

def initialize_system_on_first_request():
    """在第一个请求之前初始化系统"""
    if not hasattr(app, '_system_initialized'):
        logger.info("📱 收到第一个请求，初始化系统...")
        initialize_system()
        app._system_initialized = True

# 在主请求处理中调用初始化
@app.before_request
def before_request():
    """在每个请求之前检查系统初始化状态"""
    initialize_system_on_first_request()

def get_screenshot_url(screenshot_path):
    """Convert full file path to relative URL path for web access"""
    if not screenshot_path:
        return None
    
    # If it's already a relative path, return as is
    if screenshot_path.startswith('screenshots/'):
        return screenshot_path
    
    # Extract just the filename from the full path
    filename = os.path.basename(screenshot_path)
    return f'screenshots/{filename}'

def ensure_full_dashboard_url(url):
    """Ensure dashboard URL is a full URL for proper linking"""
    if not url:
        return '#'
    
    # If it's already a full URL, return as is
    if url.startswith('http://') or url.startswith('https://'):
        return url
    
    # Get Superset URL from environment
    superset_url = os.environ.get('SUPERSET_URL', 'http://localhost:8088')
    
    # Remove trailing slash from superset_url if present
    superset_url = superset_url.rstrip('/')
    
    # Handle relative URLs
    if url.startswith('/'):
        return f"{superset_url}{url}"
    else:
        return f"{superset_url}/{url}"

@app.route('/')
def index():
    logger.info("📱 用户访问首页")
    return render_template('index.html')

@app.route('/context-status')
def context_status():
    """Get context system status"""
    try:
        # 使用全局的smart_context_system
        global smart_context_system
        
        if smart_context_system is None:
            logger.warning("⚠️ 智能上下文系统未初始化，正在初始化...")
            initialize_system()
        
        if smart_context_system is None:
            return jsonify({
                "error": "智能上下文系统初始化失败",
                "faiss_enabled": False,
                "selection_method": "未初始化"
            }), 500
        
        status = smart_context_system.get_system_status()
        
        # Add additional helpful information
        contexts = smart_context.context_manager.get_all_contexts()
        context_details = []
        
        for context in contexts:
            context_details.append({
                'dashboard_id': context.dashboard_id,
                'dashboard_name': context.dashboard_name,
                'last_update_time': context.last_update_time,
                'is_expired': context.is_expired(),
                'charts_count': len(context.charts),
                'file_path': context.file_path
            })
        
        enhanced_status = {
            **status,
            'context_details': context_details,
            'server_time': datetime.now().isoformat(),
            'update_frequency_days': smart_context.context_manager.update_frequency_days
        }
        
        return jsonify(enhanced_status)
    except Exception as e:
        logger.error(f"❌ Failed to get context status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/context-refresh', methods=['POST'])
def context_refresh():
    """Manually refresh context system"""
    try:
        logger.info("🔄 手动刷新Context系统...")
        
        # 使用全局的smart_context_system
        global smart_context_system
        
        if smart_context_system is None:
            logger.warning("⚠️ 智能上下文系统未初始化，正在初始化...")
            initialize_system()
        
        if smart_context_system is None:
            return jsonify({
                'success': False,
                'error': '智能上下文系统初始化失败',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        smart_context = smart_context_system
        
        # Get available dashboards and update contexts
        async def refresh_contexts():
            try:
                async with SupersetAutomation() as superset_automation:
                    dashboard_list = await superset_automation.get_dashboard_list()
                    
                    if dashboard_list:
                        # Step 1: Capture screenshots for all dashboards first
                        logger.info("📸 Capturing screenshots for all dashboards...")
                        available_dashboards = []
                        
                        for i, dashboard in enumerate(dashboard_list, 1):
                            logger.info(f"🔄 Processing {i}/{len(dashboard_list)}: {dashboard.get('title')}")
                            
                            try:
                                # Capture dashboard screenshot
                                screenshot_path = await superset_automation.capture_dashboard_screenshot(dashboard)
                                
                                # Create simplified dashboard data
                                simplified_dashboard = {
                                    'dashboard_id': str(dashboard.get('id', '')),
                                    'dashboard_title': dashboard.get('title', ''),
                                    'dashboard_url': dashboard.get('url', ''),
                                    'published': dashboard.get('published', False),
                                    'changed_on': dashboard.get('changed_on', ''),
                                    'dashboard_screenshot': get_screenshot_url(screenshot_path),
                                    'charts': []
                                }
                                available_dashboards.append(simplified_dashboard)
                                
                                if screenshot_path:
                                    logger.info(f"✅ Screenshot captured: {screenshot_path}")
                                else:
                                    logger.warning(f"⚠️ Failed to capture screenshot for: {dashboard.get('title')}")
                                    
                            except Exception as e:
                                logger.error(f"❌ Error processing dashboard {dashboard.get('title')}: {e}")
                                # Still add to available_dashboards but without screenshot
                                simplified_dashboard = {
                                    'dashboard_id': str(dashboard.get('id', '')),
                                    'dashboard_title': dashboard.get('title', ''),
                                    'dashboard_url': dashboard.get('url', ''),
                                    'published': dashboard.get('published', False),
                                    'changed_on': dashboard.get('changed_on', ''),
                                    'dashboard_screenshot': None,
                                    'charts': []
                                }
                                available_dashboards.append(simplified_dashboard)
                            
                            # Add delay between processing to avoid overwhelming the system
                            if i < len(dashboard_list):
                                await asyncio.sleep(1)
                        
                        logger.info(f"✅ Completed processing {len(available_dashboards)} dashboards")
                        
                        # Step 2: Update contexts with screenshots (force update all)
                        logger.info("🤖 Analyzing dashboard content with AI...")
                        update_results = smart_context.update_dashboard_contexts(available_dashboards, force_update=True)
                        return update_results
                    else:
                        return {'error': 'No dashboards found'}
            except Exception as e:
                return {'error': str(e)}
        
        # Run async refresh
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            update_results = loop.run_until_complete(refresh_contexts())
        finally:
            loop.close()
        
        logger.info("✅ Context系统刷新完成")
        
        # 强制重建FAISS索引
        if smart_context.use_faiss and smart_context.faiss_index_manager:
            logger.info("🔄 重建FAISS索引...")
            try:
                if smart_context.faiss_index_manager.force_rebuild():
                    logger.info("✅ FAISS索引重建成功")
                else:
                    logger.warning("⚠️ FAISS索引重建失败")
            except Exception as e:
                logger.error(f"❌ FAISS索引重建错误: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Context system refreshed successfully',
            'update_results': update_results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Context刷新失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def run_async_analysis(question):
    """Run async analysis in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(analyze_question_async(question))
    finally:
        loop.close()

async def analyze_question_async(question):
    """Async analysis function with smart context system - optimized version"""
    # 使用全局的smart_context_system
    global smart_context_system
    
    if smart_context_system is None:
        logger.warning("⚠️ 智能上下文系统未初始化，正在重新初始化...")
        initialize_system()
        if smart_context_system is None:
            logger.error("❌ 智能上下文系统初始化失败")
            return {
                'question': question,
                'answer': '系统初始化失败，请稍后重试。',
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'system_error',
                'dashboards_analyzed': 0,
                'total_charts': 0,
                'dashboards_data': [],
                'individual_analyses': [],
                'screenshots': []
            }
    
    smart_context = smart_context_system
    ai_analyzer = smart_context.dashboard_analyzer.ai_analyzer
    
    async with SupersetAutomation() as superset_automation:
        
        try:
            logger.info(f"🔍 开始智能分析: {question[:100]}...")
            
            # Step 1: Get available dashboards (like test_download_all_dashboards.py)
            logger.info("📋 获取Dashboard列表...")
            dashboard_list = await superset_automation.get_dashboard_list()
            
            if not dashboard_list:
                logger.warning("⚠️ 无法获取看板列表")
                return {
                    'question': question,
                    'answer': '抱歉，目前无法连接到Superset或获取看板列表。\n\n可能的原因：\n1. Superset服务未运行（请检查 http://localhost:8088）\n2. 网络连接问题\n3. 登录凭据错误\n4. Superset配置问题\n\n建议解决方案：\n- 确认Superset服务已启动\n- 检查环境变量配置（.env文件）\n- 验证SUPERSET_URL、SUPERSET_USERNAME、SUPERSET_PASSWORD是否正确\n- 稍后重试',
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'no_data',
                    'dashboards_analyzed': 0,
                    'total_charts': 0,
                    'dashboards_data': [],
                    'individual_analyses': [],
                    'screenshots': []
                }
            
            logger.info(f"✅ 找到 {len(dashboard_list)} 个Dashboards")
            
            # Step 2: Convert to simplified format and update contexts
            available_dashboards = []
            for dashboard in dashboard_list:
                simplified_dashboard = {
                    'dashboard_id': str(dashboard.get('id', '')),
                    'dashboard_title': dashboard.get('title', ''),
                    'dashboard_url': dashboard.get('url', ''),
                    'published': dashboard.get('published', False),
                    'changed_on': dashboard.get('changed_on', ''),
                    'dashboard_screenshot': None,
                    'charts': []
                }
                available_dashboards.append(simplified_dashboard)
            
            # Step 3: Update contexts for expired dashboards
            logger.info("🔄 更新Dashboard Contexts...")
            update_results = smart_context.update_dashboard_contexts(available_dashboards)
            
            # Check if update_results contains an error
            if 'error' in update_results:
                logger.error(f"❌ Context update failed: {update_results['error']}")
                updated_count = 0
                expired_count = 0
            else:
                updated_count = len(update_results.get('updated_contexts', []))
                expired_count = len(update_results.get('expired_dashboards', []))
                logger.info(f"📊 Context更新: 新增{updated_count}个, 过期{expired_count}个")
            
            # Step 4: Select most relevant dashboards using FAISS or AI
            logger.info("🎯 智能选择相关Dashboards...")
            if smart_context.use_faiss and smart_context.faiss_index_manager:
                logger.info("🔍 使用FAISS向量搜索进行Dashboard选择...")
            else:
                logger.info("🤖 使用AI进行Dashboard选择...")
            
            selected_dashboards = smart_context.select_dashboards_for_question(question, top_k=3)
            
            if not selected_dashboards:
                logger.warning("⚠️ 没有找到相关的Dashboards")
                return {
                    'question': question,
                    'answer': '抱歉，没有找到与您问题相关的看板。\n\n可能的原因：\n1. 当前看板内容与您的问题不匹配\n2. 看板数据可能需要更新\n3. 问题表述可能需要调整\n\n建议：\n- 尝试重新表述您的问题\n- 检查是否有相关的看板存在\n- 联系管理员确认看板内容',
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'no_relevant_dashboards',
                    'dashboards_analyzed': 0,
                    'total_charts': 0,
                    'dashboards_data': [],
                    'individual_analyses': [],
                    'screenshots': []
                }
            
            logger.info(f"✅ 选择了 {len(selected_dashboards)} 个相关Dashboards")
            for i, (context, score) in enumerate(selected_dashboards):
                logger.info(f"   {i+1}. {context.dashboard_name} (相关度: {score:.2f})")
            
            # Step 5: Progressive analysis of selected dashboards (like test_download_all_dashboards.py)
            logger.info("🚀 开始渐进式分析...")
            
            individual_analyses = []
            dashboards_data = []
            selected_dashboard_ids = [ctx.dashboard_id for ctx, score in selected_dashboards]
            
            # Define callback function for progressive analysis
            async def analyze_dashboard_callback(dashboard_data, dashboard_index, total_dashboards):
                """Callback function to analyze each dashboard immediately after capture"""
                try:
                    dashboard_id = dashboard_data.get('dashboard_id')
                    dashboard_title = dashboard_data.get('dashboard_title', 'Unknown')
                    
                    # Only analyze selected dashboards
                    if dashboard_id not in selected_dashboard_ids:
                        logger.debug(f"⏭️ 跳过未选中的Dashboard: {dashboard_title}")
                        return
                    
                    logger.info(f"🤖 分析Dashboard {dashboard_index + 1}/{total_dashboards}: {dashboard_title}")
                    
                    # Analyze this dashboard immediately
                    analysis_result = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        ai_analyzer.analyze_dashboard_progressively, 
                        question, 
                        dashboard_data
                    )
                    
                    # Store the analysis result
                    individual_analyses.append({
                        'dashboard_title': dashboard_title,
                        'analysis': analysis_result,
                        'dashboard_index': dashboard_index,
                        'timestamp': datetime.now().isoformat(),
                        'dashboard_url': dashboard_data.get('url', dashboard_data.get('dashboard_url', '')),
                        'dashboard_screenshot': dashboard_data.get('screenshot_path', ''),
                        'chart_analyses': dashboard_data.get('chart_analyses', [])
                    })
                    
                    logger.info(f"✅ 完成Dashboard分析: {dashboard_title}")
                    
                except Exception as e:
                    logger.error(f"❌ Dashboard分析失败: {e}")
                    # Store error result
                    individual_analyses.append({
                        'dashboard_title': dashboard_data.get('dashboard_title', 'Unknown'),
                        'analysis': f"分析此看板时出现错误：{str(e)}",
                        'dashboard_index': dashboard_index,
                        'timestamp': datetime.now().isoformat(),
                        'error': True,
                        'dashboard_url': dashboard_data.get('url', dashboard_data.get('dashboard_url', '')),
                        'dashboard_screenshot': dashboard_data.get('screenshot_path', ''),
                        'chart_analyses': dashboard_data.get('chart_analyses', [])
                    })
            
            # Capture dashboards progressively (like test_download_all_dashboards.py)
            dashboards_data = await superset_automation.capture_dashboards_progressively(analyze_dashboard_callback)
            
            if not dashboards_data:
                # No dashboard data available
                print("⚠️  无法获取看板数据")
                return {
                    'question': question,
                    'answer': '抱歉，目前无法连接到Superset或获取看板数据。\n\n可能的原因：\n1. Superset服务未运行（请检查 http://localhost:8088）\n2. 网络连接问题\n3. 登录凭据错误\n4. Superset配置问题\n\n建议解决方案：\n- 确认Superset服务已启动\n- 检查环境变量配置（.env文件）\n- 验证SUPERSET_URL、SUPERSET_USERNAME、SUPERSET_PASSWORD是否正确\n- 稍后重试',
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'no_data',
                    'dashboards_analyzed': 0,
                    'total_charts': 0,
                    'dashboards_data': [],
                    'individual_analyses': [],
                    'screenshots': []
                }
            
            # Step 2: Prepare comprehensive analysis data
            print("📊 Preparing comprehensive analysis data...")
            
            # Extract all screenshots for final summary
            all_screenshots = []
            chart_data_summary = []
            
            for dashboard in dashboards_data:
                # Add dashboard screenshot
                if dashboard.get('dashboard_screenshot'):
                    all_screenshots.append({
                        'title': f"{dashboard['dashboard_title']} - 完整看板",
                        'path': dashboard['dashboard_screenshot'],
                        'type': 'dashboard'
                    })
                
                # Add chart screenshots and data
                for chart in dashboard.get('charts', []):
                    if chart.get('chart_screenshot'):
                        all_screenshots.append({
                            'title': f"{chart['chart_title']} - 图表",
                            'path': chart['chart_screenshot'],
                            'type': 'chart'
                        })
                    
                    # Add chart data summary
                    chart_data_summary.append({
                        'dashboard': dashboard['dashboard_title'],
                        'chart': chart['chart_title'],
                        'data_type': chart.get('chart_data', {}).get('type', 'unknown'),
                        'key_metrics': _extract_key_metrics(chart.get('chart_data', {}))
                    })
            
            # Step 3: Combine all individual analyses
            print("🤖 Combining all individual analyses...")
            
            try:
                if individual_analyses and len(individual_analyses) > 1:
                    # Combine multiple analyses
                    final_answer = ai_analyzer.combine_multiple_analyses(question, individual_analyses)
                elif individual_analyses and len(individual_analyses) == 1:
                    # Only one dashboard, use the single analysis
                    final_answer = individual_analyses[0]['analysis']
                else:
                    # No individual analyses available, fallback to traditional method
                    dashboard_titles = [d['dashboard_title'] for d in dashboards_data]
                    if all_screenshots and any(os.path.exists(s['path']) for s in all_screenshots):
                        final_answer = ai_analyzer.analyze_with_screenshots(question, all_screenshots)
                    else:
                        enhanced_context = _create_enhanced_context(question, dashboards_data, chart_data_summary)
                        final_answer = ai_analyzer.analyze_text_only(enhanced_context, dashboard_titles)
                        
            except Exception as ai_error:
                print(f"AI analysis failed: {ai_error}")
                # Provide helpful error message with individual analyses if available
                if individual_analyses:
                    individual_analysis_text = "\n\n各看板的独立分析：\n"
                    for analysis in individual_analyses:
                        individual_analysis_text += f"\n--- {analysis['dashboard_title']} ---\n{analysis['analysis']}\n"
                    
                    return {
                        'question': question,
                        'answer': f'抱歉，AI综合分析服务暂时不可用。但以下是各看板的独立分析：{individual_analysis_text}\n\n技术详情：{str(ai_error)}\n\n可能的解决方案：\n- 检查AI API密钥配置（OPENAI_API_KEY）\n- 确认网络连接正常\n- 验证API服务状态\n- 稍后重试',
                        'timestamp': datetime.now().isoformat(),
                        'analysis_type': 'ai_error_but_individual',
                        'dashboards_analyzed': len(dashboards_data),
                        'total_charts': sum(len(d.get('charts', [])) for d in dashboards_data),
                        'dashboards_data': dashboards_data,
                        'chart_summary': chart_data_summary,
                        'screenshots': all_screenshots,
                        'individual_analyses': individual_analyses
                    }
                else:
                    return {
                        'question': question,
                        'answer': f'抱歉，AI分析服务暂时不可用。我们已经成功获取了看板数据，但无法进行分析。\n\n技术详情：{str(ai_error)}\n\n可能的解决方案：\n- 检查AI API密钥配置（OPENAI_API_KEY）\n- 确认网络连接正常\n- 验证API服务状态\n- 稍后重试\n\n已获取的数据：\n- 分析了 {len(dashboards_data)} 个看板\n- 包含 {sum(len(d.get("charts", [])) for d in dashboards_data)} 个图表',
                        'timestamp': datetime.now().isoformat(),
                        'analysis_type': 'ai_error',
                        'dashboards_analyzed': len(dashboards_data),
                        'total_charts': sum(len(d.get('charts', [])) for d in dashboards_data),
                        'dashboards_data': dashboards_data,
                        'chart_summary': chart_data_summary,
                        'screenshots': all_screenshots,
                        'individual_analyses': individual_analyses
                    }
            
            return {
                'question': question,
                'answer': final_answer,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'progressive',
                'dashboards_analyzed': len(dashboards_data),
                'total_charts': sum(len(d.get('charts', [])) for d in dashboards_data),
                'dashboards_data': dashboards_data,
                'chart_summary': chart_data_summary,
                'screenshots': all_screenshots,
                'individual_analyses': individual_analyses
            }
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return {
                'question': question,
                'answer': f'抱歉，分析过程中遇到了技术问题。\n\n错误详情：{str(e)}\n\n建议解决方案：\n- 检查Superset服务是否正常运行\n- 确认网络连接稳定\n- 验证浏览器自动化组件是否正常\n- 稍后重试或联系技术支持\n\n技术支持信息：\n- 请检查日志文件：app.log, superset_automation.log\n- 确认所有依赖项已正确安装',
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'error',
                'dashboards_analyzed': 0,
                'total_charts': 0,
                'dashboards_data': [],
                'chart_summary': [],
                'screenshots': [],
                'individual_analyses': []
            }

def _extract_key_metrics(chart_data):
    """Extract key metrics from chart data"""
    try:
        metrics = []
        data = chart_data.get('data', {})
        
        if 'total_sales' in data:
            metrics.append(f"总销售额: {data['total_sales']:,}")
        if 'growth_rate' in data:
            metrics.append(f"增长率: {data['growth_rate']}%")
        if 'total_users' in data:
            metrics.append(f"总用户数: {data['total_users']:,}")
        if 'active_users' in data:
            metrics.append(f"活跃用户: {data['active_users']:,}")
        if 'retention_rate' in data:
            metrics.append(f"留存率: {data['retention_rate']}%")
        if 'value' in data:
            metrics.append(f"数值: {data['value']:,}")
        
        return metrics if metrics else ["数据不可用"]
    except:
        return ["数据提取失败"]

def _create_enhanced_context(question, dashboards_data, chart_summary):
    """Create enhanced context for AI analysis"""
    context = f"业务问题: {question}\n\n"
    context += "可用的看板和图表数据:\n\n"
    
    for dashboard in dashboards_data:
        context += f"📊 {dashboard['dashboard_title']}:\n"
        for chart in dashboard.get('charts', []):
            context += f"  📈 {chart['chart_title']}\n"
            
            # Add key metrics
            metrics = _extract_key_metrics(chart.get('chart_data', {}))
            for metric in metrics:
                context += f"    • {metric}\n"
        context += "\n"
    
    context += "请基于以上详细的看板和图表数据分析业务问题，提供具体的洞察和建议。"
    
    return context

@app.route('/analyze', methods=['POST'])
def analyze():
    logger.info("🔍 收到分析请求")
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        logger.info(f"📝 用户问题: {question}")
        
        if not question:
            logger.warning("⚠️ 用户问题为空")
            return jsonify({'error': 'Question is required'}), 400
        
        logger.info("🚀 开始异步分析")
        # Run analysis in a separate thread to avoid blocking
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_analysis, question)
            result = future.result(timeout=120)  # 2 minute timeout
        
        logger.info(f"✅ 分析完成，分析了 {result.get('dashboards_analyzed', 0)} 个看板")
        return jsonify(result)
    
    except concurrent.futures.TimeoutError:
        logger.error("⏰ 分析超时")
        return jsonify({
            'error': '分析超时，请稍后重试或简化问题。\n\n可能的原因：\n- 网络连接缓慢\n- Superset响应时间过长\n- 看板数据量过大\n- AI服务响应延迟\n\n建议：\n- 简化分析问题\n- 稍后重试\n- 检查网络连接状态'
        }), 504
    except Exception as e:
        logger.error(f"❌ 分析请求失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/screenshots/<filename>')
def serve_screenshot(filename):
    """Serve screenshot files"""
    logger.info(f"🖼️ 用户请求截图: {filename}")
    try:
        # Check if file exists in screenshots directory
        screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        file_path = os.path.join(screenshots_dir, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"❌ 截图文件不存在: {file_path}")
            return jsonify({'error': 'Screenshot not found', 'path': file_path}), 404
        
        logger.info(f"✅ 找到截图文件: {file_path}")
        return send_from_directory(screenshots_dir, filename)
    except Exception as e:
        logger.error(f"❌ 截图服务失败 {filename}: {e}")
        return jsonify({'error': f'Screenshot service error: {str(e)}'}), 404

@app.route('/analyze_progressive', methods=['POST'])
def analyze_progressive():
    """Progressive analysis endpoint with real-time updates via SSE
    This implements the progressive analysis feature described in README.md:
    - Real-time chart analysis feedback
    - Server-Sent Events for live updates
    - Individual chart analysis with progress callbacks
    """
    logger.info("🔍 收到渐进式分析请求")
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        logger.info(f"📝 用户问题: {question}")
        
        if not question:
            logger.warning("⚠️ 用户问题为空")
            return jsonify({'error': 'Question is required'}), 400
        
        logger.info("🚀 开始渐进式分析")
        
        # Create a queue for this analysis session
        event_queue = Queue()
        
        # Start progressive analysis in a separate thread
        def run_progressive_analysis():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(run_progressive_analysis_async(question, event_queue))
                finally:
                    loop.close()
                    
                # Send completion signal
                event_queue.put({
                    'type': 'complete',
                    'data': {'message': '分析完成'}
                })
                
            except Exception as e:
                logger.error(f"❌ 渐进式分析失败: {e}")
                
                # Check if it's a timeout error
                error_message = str(e)
                if "Timeout" in error_message or "timeout" in error_message:
                    error_message = f"分析过程中出现超时错误。可能的原因：\n- 某些看板加载时间过长\n- 网络连接不稳定\n- Superset服务器响应慢\n\n建议：\n- 稍后重试\n- 检查网络连接\n- 考虑简化分析问题\n- 联系管理员优化看板性能"
                else:
                    error_message = str(e)
                
                event_queue.put({
                    'type': 'error',
                    'data': {'error': error_message}
                })
        
        # Start the analysis thread
        analysis_thread = threading.Thread(target=run_progressive_analysis)
        analysis_thread.daemon = True
        analysis_thread.start()
        
        # Return SSE response
        def generate():
            yield f"data: {json.dumps({'type': 'start', 'message': '开始分析'})}\n\n"
            
            while True:
                try:
                    event = event_queue.get(timeout=300)  # 5 minute timeout for progressive analysis
                    yield f"data: {json.dumps(event)}\n\n"
                    
                    if event['type'] in ['complete', 'error']:
                        break
                        
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"
                    break
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        logger.error(f"❌ 渐进式分析请求失败: {e}")
        return jsonify({'error': str(e)}), 500

async def run_progressive_analysis_async(question, event_queue):
    """Run progressive analysis with real-time updates using smart context system"""
    async with SupersetAutomation() as superset_automation:
        ai_analyzer = AIAnalyzer()
        smart_context = SmartContextSystem(ai_analyzer)
        
        try:
            # Send initial status
            event_queue.put({
                'type': 'status',
                'data': {'message': '正在初始化智能分析系统...', 'step': 'initializing'}
            })
            
            # Store individual analysis results
            individual_analyses = []
            dashboards_data = []
            
            # Step 1: Use smart context system to select top 3 relevant dashboards
            event_queue.put({
                'type': 'status',
                'data': {'message': '正在分析问题并选择最相关的看板...', 'step': 'selecting_dashboards'}
            })
            
            logger.info(f"🧠 Using smart context to select dashboards for question: {question}")
            
            # Select top 3 relevant dashboards based on question
            selected_dashboards_with_scores = smart_context.select_dashboards_for_question(question, top_k=3)
            
            # Convert to dict format for easier processing
            selected_dashboards = []
            for dashboard_context, score in selected_dashboards_with_scores:
                selected_dashboards.append({
                    'dashboard_id': dashboard_context.dashboard_id,
                    'dashboard_title': dashboard_context.dashboard_name,
                    'score': score
                })
            
            if not selected_dashboards:
                logger.warning("⚠️ No relevant dashboards found")
                event_queue.put({
                    'type': 'no_data',
                    'data': {
                        'question': question,
                        'answer': '抱歉，根据您的问题，没有找到相关的看板数据。\n\n建议：\n- 尝试更具体的问题描述\n- 使用其他相关的关键词\n- 检查看板数据是否包含您需要的信息'
                    }
                })
                return
            
            logger.info(f"✅ Selected {len(selected_dashboards)} relevant dashboards")
            
            # Send selected dashboards info
            dashboard_titles = [d.get('dashboard_title', 'Unknown') for d in selected_dashboards]
            event_queue.put({
                'type': 'dashboards_selected',
                'data': {
                    'message': f'已选择 {len(selected_dashboards)} 个最相关的看板进行分析',
                    'dashboards': dashboard_titles
                }
            })
            
            # Get full dashboard list for processing
            full_dashboard_list = await superset_automation.get_dashboard_list()
            if not full_dashboard_list:
                logger.warning("⚠️ No dashboards available")
                event_queue.put({
                    'type': 'no_data',
                    'data': {
                        'question': question,
                        'answer': '抱歉，目前无法获取看板列表。\n\n可能的原因：\n1. Superset服务未运行\n2. 网络连接问题\n3. 登录凭据错误\n\n建议解决方案：\n- 确认Superset服务已启动\n- 检查环境变量配置\n- 稍后重试'
                    }
                })
                return
            
            # Create a mapping of dashboard ID to full dashboard info
            dashboard_map = {str(d.get('id')): d for d in full_dashboard_list}
            
            # Process only the selected dashboards
            total_selected = len(selected_dashboards)
            
            # Define callback function for progressive analysis
            async def analyze_dashboard_callback(dashboard_data, dashboard_index, total_dashboards):
                """Callback function to analyze each dashboard immediately after capture"""
                try:
                    # Send status update
                    event_queue.put({
                        'type': 'dashboard_captured',
                        'data': {
                            'dashboard_title': dashboard_data.get('dashboard_title', 'Unknown'),
                            'dashboard_index': dashboard_index,
                            'total_dashboards': total_dashboards,
                            'dashboard_screenshot': dashboard_data.get('dashboard_screenshot'),
                            'charts': dashboard_data.get('charts', [])
                        }
                    })
                    
                    print(f"🤖 Analyzing dashboard {dashboard_index + 1}/{total_dashboards}: {dashboard_data.get('dashboard_title', 'Unknown')}")
                    
                    # Send analysis status
                    event_queue.put({
                        'type': 'analyzing',
                        'data': {
                            'dashboard_title': dashboard_data.get('dashboard_title', 'Unknown'),
                            'dashboard_index': dashboard_index,
                            'total_dashboards': total_dashboards
                        }
                    })
                    
                    # Send analysis start status
                    event_queue.put({
                        'type': 'analysis_started',
                        'data': {
                            'dashboard_title': dashboard_data.get('dashboard_title', 'Unknown'),
                            'dashboard_index': dashboard_index,
                            'total_dashboards': total_dashboards,
                            'message': f'开始分析看板: {dashboard_data.get("dashboard_title", "Unknown")}',
                            'dashboard_screenshot': dashboard_data.get('dashboard_screenshot'),
                            'charts': dashboard_data.get('charts', [])
                        }
                    })
                    
                    # Define progress callback for chart analysis events
                    def progress_callback(event):
                        """Handle progress events from progressive analysis"""
                        try:
                            # Map the event types to SSE events
                            if event['type'] == 'chart_analysis_started':
                                event_queue.put({
                                    'type': 'chart_analysis_started',
                                    'data': {
                                        'dashboard_title': event['dashboard_title'],
                                        'chart_title': event['chart_title'],
                                        'chart_index': event['chart_index'],
                                        'total_charts': event['total_charts'],
                                        'chart_screenshot': event.get('chart_screenshot'),
                                        'message': event['message']
                                    }
                                })
                            elif event['type'] == 'chart_analysis_complete':
                                event_queue.put({
                                    'type': 'chart_analysis_complete',
                                    'data': {
                                        'dashboard_title': event['dashboard_title'],
                                        'chart_title': event['chart_title'],
                                        'chart_index': event['chart_index'],
                                        'total_charts': event['total_charts'],
                                        'chart_screenshot': event.get('chart_screenshot'),
                                        'analysis': event['analysis'],
                                        'message': event['message']
                                    }
                                })
                            elif event['type'] == 'dashboard_analysis_started':
                                event_queue.put({
                                    'type': 'dashboard_analysis_started',
                                    'data': {
                                        'dashboard_title': event['dashboard_title'],
                                        'message': event['message']
                                    }
                                })
                            elif event['type'] == 'dashboard_analysis_complete':
                                event_queue.put({
                                    'type': 'dashboard_analysis_complete',
                                    'data': {
                                        'dashboard_title': event['dashboard_title'],
                                        'analysis': event['analysis'],
                                        'message': event['message']
                                    }
                                })
                        except Exception as e:
                            print(f"❌ Error in progress callback: {e}")
                    
                    # Analyze this dashboard with progress callback
                    analysis_result = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        ai_analyzer.analyze_dashboard_progressively, 
                        question, 
                        dashboard_data,
                        progress_callback  # Pass the progress callback
                    )
                    
                    # Store the analysis result
                    analysis_entry = {
                        'dashboard_title': dashboard_data.get('dashboard_title', 'Unknown'),
                        'analysis': analysis_result,
                        'dashboard_index': dashboard_index,
                        'timestamp': datetime.now().isoformat(),
                        'dashboard_url': dashboard_data.get('url', dashboard_data.get('dashboard_url', '')),
                        'dashboard_screenshot': dashboard_data.get('dashboard_screenshot', ''),
                        'chart_analyses': dashboard_data.get('chart_analyses', [])
                    }
                    individual_analyses.append(analysis_entry)
                    
                    # Send final analysis result
                    event_queue.put({
                        'type': 'analysis_complete',
                        'data': analysis_entry
                    })
                    
                    print(f"✅ Completed analysis for dashboard {dashboard_index + 1}/{total_dashboards}")
                    
                except Exception as e:
                    print(f"❌ Error in dashboard analysis callback: {e}")
                    
                    # Check if it's a timeout error
                    error_message = str(e)
                    if "Timeout" in error_message or "timeout" in error_message:
                        error_message = f"看板加载超时：{dashboard_data.get('dashboard_title', 'Unknown')}。可能的原因：\n- 看板数据量过大\n- 网络连接缓慢\n- Superset服务器响应慢\n\n建议：\n- 稍后重试\n- 检查网络连接\n- 联系管理员优化看板性能"
                    else:
                        error_message = f"分析此看板时出现错误：{str(e)}"
                    
                    # Store error result
                    error_entry = {
                        'dashboard_title': dashboard_data.get('dashboard_title', 'Unknown'),
                        'analysis': error_message,
                        'dashboard_index': dashboard_index,
                        'timestamp': datetime.now().isoformat(),
                        'error': True,
                        'dashboard_url': dashboard_data.get('url', dashboard_data.get('dashboard_url', '')),
                        'dashboard_screenshot': dashboard_data.get('dashboard_screenshot', ''),
                        'chart_analyses': dashboard_data.get('chart_analyses', [])
                    }
                    individual_analyses.append(error_entry)
                    
                    # Send error result
                    event_queue.put({
                        'type': 'analysis_error',
                        'data': error_entry
                    })
            
            # Send status update
            event_queue.put({
                'type': 'status',
                'data': {'message': '正在获取看板列表...', 'step': 'fetching_dashboards'}
            })
            
            # Process only the selected 3 dashboards
            event_queue.put({
                'type': 'status',
                'data': {'message': f'开始处理选中的 {len(selected_dashboards)} 个看板...', 'step': 'processing_dashboards'}
            })
            
            # Process each selected dashboard individually
            for i, selected_dashboard in enumerate(selected_dashboards, 1):
                dashboard_id = selected_dashboard.get('dashboard_id')
                dashboard_title = selected_dashboard.get('dashboard_title', 'Unknown')
                
                logger.info(f"🔄 Processing selected dashboard {i}/{len(selected_dashboards)}: {dashboard_title}")
                
                # Get full dashboard info from the map
                full_dashboard_info = dashboard_map.get(dashboard_id)
                if not full_dashboard_info:
                    logger.warning(f"⚠️ Full dashboard info not found for {dashboard_id}")
                    continue
                
                # Capture dashboard screenshot using menu download
                event_queue.put({
                    'type': 'status',
                    'data': {'message': f'正在下载看板截图: {dashboard_title}...', 'step': 'capturing_dashboard'}
                })
                
                try:
                    # Capture screenshot for this specific dashboard
                    screenshot_path = await superset_automation.capture_dashboard_screenshot(full_dashboard_info)
                    
                    if screenshot_path:
                        # Create dashboard data for analysis
                        dashboard_data = {
                            'dashboard_id': dashboard_id,
                            'dashboard_title': dashboard_title,
                            'dashboard_url': full_dashboard_info.get('url', ''),
                            'published': full_dashboard_info.get('published', False),
                            'changed_on': full_dashboard_info.get('changed_on', ''),
                            'dashboard_screenshot': get_screenshot_url(screenshot_path),
                            'charts': []  # Will be populated by AI analysis
                        }
                        
                        # Add to dashboards data list
                        dashboards_data.append(dashboard_data)
                        
                        # Call the analysis callback for this dashboard
                        await analyze_dashboard_callback(dashboard_data, i - 1, len(selected_dashboards))
                        
                    else:
                        logger.warning(f"⚠️ Failed to capture screenshot for {dashboard_title}")
                        event_queue.put({
                            'type': 'dashboard_capture_failed',
                            'data': {
                                'dashboard_title': dashboard_title,
                                'message': f'无法下载看板截图: {dashboard_title}'
                            }
                        })
                        
                except Exception as e:
                    logger.error(f"❌ Error processing dashboard {dashboard_title}: {e}")
                    event_queue.put({
                        'type': 'dashboard_capture_failed',
                        'data': {
                            'dashboard_title': dashboard_title,
                            'message': f'处理看板时出错: {dashboard_title} - {str(e)}'
                        }
                    })
            
            if not dashboards_data:
                # No dashboard data available
                event_queue.put({
                    'type': 'no_data',
                    'data': {
                        'question': question,
                        'answer': '抱歉，目前无法连接到Superset或获取看板数据。\n\n可能的原因：\n1. Superset服务未运行（请检查 http://localhost:8088）\n2. 网络连接问题\n3. 登录凭据错误\n4. Superset配置问题\n\n建议解决方案：\n- 确认Superset服务已启动\n- 检查环境变量配置（.env文件）\n- 验证SUPERSET_URL、SUPERSET_USERNAME、SUPERSET_PASSWORD是否正确\n- 稍后重试'
                    }
                })
                return
            
            # Step 2: Prepare comprehensive analysis data
            print("📊 Preparing comprehensive analysis data...")
            
            # Extract all screenshots for final summary
            all_screenshots = []
            chart_data_summary = []
            
            for dashboard in dashboards_data:
                # Add dashboard screenshot
                if dashboard.get('dashboard_screenshot'):
                    all_screenshots.append({
                        'title': f"{dashboard['dashboard_title']} - 完整看板",
                        'path': dashboard['dashboard_screenshot'],
                        'type': 'dashboard'
                    })
                
                # Add chart screenshots and data
                for chart in dashboard.get('charts', []):
                    if chart.get('chart_screenshot'):
                        all_screenshots.append({
                            'title': f"{chart['chart_title']} - 图表",
                            'path': chart['chart_screenshot'],
                            'type': 'chart'
                        })
                    
                    # Add chart data summary
                    chart_data_summary.append({
                        'dashboard': dashboard['dashboard_title'],
                        'chart': chart['chart_title'],
                        'data_type': chart.get('chart_data', {}).get('type', 'unknown'),
                        'key_metrics': _extract_key_metrics(chart.get('chart_data', {}))
                    })
            
            # Step 3: Combine all individual analyses
            print("🤖 Combining all individual analyses...")
            
            # Send combining status
            event_queue.put({
                'type': 'combining',
                'data': {'message': '正在综合分析结果...'}
            })
            
            try:
                if individual_analyses and len(individual_analyses) > 1:
                    # Combine multiple analyses
                    final_answer = ai_analyzer.combine_multiple_analyses(question, individual_analyses)
                elif individual_analyses and len(individual_analyses) == 1:
                    # Only one dashboard, use the single analysis
                    final_answer = individual_analyses[0]['analysis']
                else:
                    # No individual analyses available, fallback to traditional method
                    dashboard_titles = [d['dashboard_title'] for d in dashboards_data]
                    if all_screenshots and any(os.path.exists(s['path']) for s in all_screenshots):
                        final_answer = ai_analyzer.analyze_with_screenshots(question, all_screenshots)
                    else:
                        enhanced_context = _create_enhanced_context(question, dashboards_data, chart_data_summary)
                        final_answer = ai_analyzer.analyze_text_only(enhanced_context, dashboard_titles)
                        
            except Exception as ai_error:
                print(f"AI analysis failed: {ai_error}")
                # Provide helpful error message with individual analyses if available
                if individual_analyses:
                    individual_analysis_text = "\n\n各看板的独立分析：\n"
                    for analysis in individual_analyses:
                        individual_analysis_text += f"\n--- {analysis['dashboard_title']} ---\n{analysis['analysis']}\n"
                    
                    final_answer = f'抱歉，AI综合分析服务暂时不可用。但以下是各看板的独立分析：{individual_analysis_text}\n\n技术详情：{str(ai_error)}'
                else:
                    final_answer = f'抱歉，AI分析服务暂时不可用。我们已经成功获取了看板数据，但无法进行分析。\n\n技术详情：{str(ai_error)}'
            
            # Send final result
            event_queue.put({
                'type': 'final_result',
                'data': {
                    'question': question,
                    'answer': final_answer,
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'progressive',
                    'dashboards_analyzed': len(dashboards_data),
                    'total_charts': sum(len(d.get('charts', [])) for d in dashboards_data),
                    'dashboards_data': dashboards_data,
                    'chart_summary': chart_data_summary,
                    'screenshots': all_screenshots,
                    'individual_analyses': individual_analyses
                }
            })
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            event_queue.put({
                'type': 'error',
                'data': {
                    'question': question,
                    'answer': f'抱歉，分析过程中遇到了技术问题。\n\n错误详情：{str(e)}',
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'error',
                    'dashboards_analyzed': 0,
                    'total_charts': 0,
                    'dashboards_data': [],
                    'chart_summary': [],
                    'screenshots': [],
                    'individual_analyses': []
                }
            })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    logger.info("💓 健康检查请求")
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def initialize_context_system():
    """Initialize and update context system on startup"""
    try:
        logger.info("🔧 初始化智能Context系统...")
        
        # Initialize AI analyzer and context system
        ai_analyzer = AIAnalyzer()
        smart_context = SmartContextSystem(ai_analyzer)
        
        # Get system status
        status = smart_context.get_system_status()
        logger.info(f"📊 Context系统状态: {status}")
        
        # Check and update contexts
        logger.info("🔄 检查并更新Dashboard Contexts...")
        
        # Get available dashboards
        async def update_contexts():
            try:
                async with SupersetAutomation() as superset_automation:
                    # Step 1: Get dashboard list
                    logger.info("📋 Step 1: 获取Dashboard列表...")
                    dashboard_list = await superset_automation.get_dashboard_list()
                    
                    if not dashboard_list:
                        logger.warning("⚠️ 未找到可用的Dashboards")
                        return None
                    
                    logger.info(f"✅ 找到 {len(dashboard_list)} 个Dashboards")
                    
                    # Step 2: Process each dashboard individually
                    logger.info("🔄 Step 2: 循环检查每个Dashboard...")
                    processed_count = 0
                    analysis_count = 0
                    all_update_results = {'updated_contexts': [], 'failed_updates': [], 'total_dashboards': len(dashboard_list)}
                    
                    for i, dashboard in enumerate(dashboard_list, 1):
                        dashboard_id = str(dashboard.get('id', ''))
                        dashboard_title = dashboard.get('title', '')
                        
                        logger.info(f"🔍 Step 2.{i}: 检查Dashboard {dashboard_id}: {dashboard_title}")
                        
                        try:
                            # Step 2.1: Check if current dashboard context needs update
                            logger.info(f"📝 Step 2.{i}.1: 检查Context是否需要更新...")
                            
                            # Get existing context
                            existing_context = smart_context.context_manager.get_dashboard_context(dashboard_id)
                            
                            needs_update = False
                            if not existing_context:
                                logger.info(f"⚠️ Context不存在，需要下载和分析: {dashboard_title}")
                                needs_update = True
                            elif existing_context.is_expired(smart_context.context_manager.update_frequency_days):
                                logger.info(f"⏰ Context已过期，需要更新: {dashboard_title}")
                                needs_update = True
                            else:
                                logger.info(f"✅ Context有效，跳过: {dashboard_title}")
                            
                            # Step 2.2: If needs update, download screenshot and analyze
                            if needs_update:
                                logger.info(f"📸 Step 2.{i}.2: 下载Dashboard Screenshot...")
                                
                                # Capture dashboard screenshot
                                screenshot_path = await superset_automation.capture_dashboard_screenshot(dashboard)
                                
                                if screenshot_path:
                                    logger.info(f"✅ Screenshot captured: {screenshot_path}")
                                    
                                    # Create dashboard data
                                    dashboard_data = {
                                        'dashboard_id': dashboard_id,
                                        'dashboard_title': dashboard_title,
                                        'dashboard_url': dashboard.get('url', ''),
                                        'published': dashboard.get('published', False),
                                        'changed_on': dashboard.get('changed_on', ''),
                                        'dashboard_screenshot': get_screenshot_url(screenshot_path),
                                        'charts': []
                                    }
                                    
                                    # Step 2.2.1: Call AI analysis immediately
                                    logger.info(f"🤖 Step 2.{i}.2.1: 调用AI分析...")
                                    
                                    # Update context for just this dashboard
                                    update_result = smart_context.update_dashboard_contexts([dashboard_data], force_update=True)
                                    
                                    if update_result and update_result.get('updated_contexts'):
                                        analysis_count += 1
                                        updated_context = update_result['updated_contexts'][0]
                                        all_update_results['updated_contexts'].append(updated_context)
                                        logger.info(f"✅ AI分析完成: {dashboard_title} ({analysis_count}/{len(dashboard_list)})")
                                        
                                        # Verify context file was created
                                        context_file = f"context/{dashboard_id}.md"
                                        if os.path.exists(context_file):
                                            file_size = os.path.getsize(context_file)
                                            logger.info(f"📁 Context文件已创建: {context_file} ({file_size} bytes)")
                                        else:
                                            logger.warning(f"⚠️ Context文件未找到: {context_file}")
                                    else:
                                        logger.warning(f"⚠️ AI分析失败: {dashboard_title}")
                                        all_update_results['failed_updates'].append({
                                            'dashboard_id': dashboard_id,
                                            'dashboard_name': dashboard_title,
                                            'error': 'AI analysis failed'
                                        })
                                else:
                                    logger.warning(f"⚠️ Screenshot下载失败: {dashboard_title}")
                                    all_update_results['failed_updates'].append({
                                        'dashboard_id': dashboard_id,
                                        'dashboard_name': dashboard_title,
                                        'error': 'Screenshot capture failed'
                                    })
                            else:
                                logger.info(f"✅ Dashboard无需更新: {dashboard_title}")
                            
                            processed_count += 1
                            
                        except Exception as e:
                            logger.error(f"❌ 处理Dashboard失败 {dashboard_title}: {e}")
                            all_update_results['failed_updates'].append({
                                'dashboard_id': dashboard_id,
                                'dashboard_name': dashboard_title,
                                'error': str(e)
                            })
                        
                        # Add delay between processing to avoid overwhelming the system
                        if i < len(dashboard_list):
                            logger.info(f"⏳ 等待3秒后处理下一个...")
                            await asyncio.sleep(3)
                    
                    # Step 3: Rebuild FAISS index if contexts were updated
                    logger.info("🎉 Step 3: 所有Dashboard处理完成，开始重建FAISS索引...")
                    
                    if analysis_count > 0:
                        logger.info(f"🔍 有 {analysis_count} 个context被更新，重建FAISS索引...")
                        if smart_context.use_faiss and smart_context.faiss_index_manager:
                            # Rebuild FAISS index with updated contexts
                            if smart_context.faiss_index_manager.build_index_from_contexts(force_rebuild=True):
                                logger.info("✅ FAISS索引重建成功")
                            else:
                                logger.warning("⚠️ FAISS索引重建失败")
                        else:
                            logger.warning("⚠️ FAISS未启用，跳过索引重建")
                    else:
                        logger.info("ℹ️ 没有context被更新，跳过FAISS索引重建")
                    
                    # Step 4: Ready
                    logger.info("🎉 Step 4: 系统完全Ready!")
                    logger.info(f"📊 处理统计:")
                    logger.info(f"   - 总共Dashboards: {len(dashboard_list)}")
                    logger.info(f"   - 已处理: {processed_count}")
                    logger.info(f"   - AI分析完成: {analysis_count}")
                    logger.info(f"   - 成功更新: {len(all_update_results.get('updated_contexts', []))}")
                    logger.info(f"   - 失败: {len(all_update_results.get('failed_updates', []))}")
                    
                    # Log FAISS status
                    if smart_context.use_faiss and smart_context.faiss_index_manager:
                        faiss_status = smart_context.faiss_index_manager.get_index_status()
                        logger.info(f"🔍 FAISS状态: {faiss_status['total_dashboards']} 个仪表板已索引")
                    
                    return all_update_results
                        
            except Exception as e:
                logger.error(f"❌ Context更新失败: {e}")
                return None
        
        # Run async update
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            update_results = loop.run_until_complete(update_contexts())
        finally:
            loop.close()
        
        logger.info("✅ 智能Context系统初始化完成")
        logger.info("🚀 系统已就绪，用户可以开始提问!")
        
        return update_results
        
    except Exception as e:
        logger.error(f"❌ Context系统初始化失败: {e}")
        return None

if __name__ == '__main__':
    logger.info("🚀 启动 Flask 应用服务器")
    
    # Initialize context system on startup
    try:
        update_results = initialize_context_system()
        if update_results is not None:
            logger.info("✅ 智能Context系统就绪")
        else:
            logger.warning("⚠️ 智能Context系统初始化失败，将使用传统分析方法")
    except Exception as e:
        logger.error(f"❌ 启动时Context检查失败: {e}")
        logger.warning("⚠️ 将继续启动但不使用智能Context系统")
    
    app.run(debug=True, host='0.0.0.0', port=5002)