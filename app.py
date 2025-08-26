from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import asyncio
import json
import logging
from datetime import datetime
from superset_automation import SupersetAutomation
from ai_analyzer import AIAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    logger.info("📱 用户访问首页")
    return render_template('index.html')

def run_async_analysis(question):
    """Run async analysis in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(analyze_question_async(question))
    finally:
        loop.close()

async def analyze_question_async(question):
    """Async analysis function with detailed dashboard exploration"""
    async with SupersetAutomation() as superset_automation:
        ai_analyzer = AIAnalyzer()
        
        try:
            # Step 1: Capture detailed dashboard information with charts
            print("🚀 Starting detailed dashboard analysis...")
            dashboards_data = await superset_automation.capture_all_dashboards_with_details()
            
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
                    'chart_summary': [],
                    'screenshots': []
                }
            
            # Step 2: Prepare comprehensive analysis data
            print("📊 Preparing comprehensive analysis data...")
            
            # Extract all screenshots for AI analysis
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
            
            # Step 3: Analyze with AI
            print("🤖 Starting AI analysis...")
            dashboard_titles = [d['dashboard_title'] for d in dashboards_data]
            
            try:
                if all_screenshots and any(os.path.exists(s['path']) for s in all_screenshots):
                    # Use vision model if screenshots are available
                    answer = ai_analyzer.analyze_with_screenshots(question, all_screenshots)
                else:
                    # Fallback to text-only analysis with enhanced data
                    enhanced_context = _create_enhanced_context(question, dashboards_data, chart_data_summary)
                    answer = ai_analyzer.analyze_text_only(enhanced_context, dashboard_titles)
            except Exception as ai_error:
                print(f"AI analysis failed: {ai_error}")
                # Provide helpful error message instead of template fallback
                return {
                    'question': question,
                    'answer': f'抱歉，AI分析服务暂时不可用。我们已经成功获取了看板数据，但无法进行分析。\n\n技术详情：{str(ai_error)}\n\n可能的解决方案：\n- 检查AI API密钥配置（OPENAI_API_KEY）\n- 确认网络连接正常\n- 验证API服务状态\n- 稍后重试\n\n已获取的数据：\n- 分析了 {len(dashboards_data)} 个看板\n- 包含 {sum(len(d.get("charts", [])) for d in dashboards_data)} 个图表',
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'ai_error',
                    'dashboards_analyzed': len(dashboards_data),
                    'total_charts': sum(len(d.get('charts', [])) for d in dashboards_data),
                    'dashboards_data': dashboards_data,
                    'chart_summary': chart_data_summary,
                    'screenshots': all_screenshots
                }
            
            return {
                'question': question,
                'answer': answer,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'detailed',
                'dashboards_analyzed': len(dashboards_data),
                'total_charts': sum(len(d.get('charts', [])) for d in dashboards_data),
                'dashboards_data': dashboards_data,
                'chart_summary': chart_data_summary,
                'screenshots': all_screenshots
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
                'screenshots': []
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

@app.route('/health')
def health_check():
    """Health check endpoint"""
    logger.info("💓 健康检查请求")
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    logger.info("🚀 启动 Flask 应用服务器")
    app.run(debug=True, host='0.0.0.0', port=5002)