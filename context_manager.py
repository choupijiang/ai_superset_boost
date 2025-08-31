import os
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import threading
from dataclasses import dataclass, asdict
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ChartInfo:
    """Data class for chart information"""
    chart_title: str
    chart_type: str
    chart_summary: str
    screenshot_path: Optional[str] = None

@dataclass
class DashboardContext:
    """Data class for dashboard context information"""
    dashboard_id: str
    dashboard_name: str
    last_update_time: str
    dashboard_summary: str
    charts: List[ChartInfo]
    file_path: str
    screenshot_path: Optional[str] = None
    
    def is_expired(self, days: int = 7) -> bool:
        """Check if context is expired based on update frequency"""
        try:
            update_time = datetime.strptime(self.last_update_time, '%Y-%m-%d %H:%M:%S')
            return datetime.now() - update_time > timedelta(days=days)
        except ValueError:
            return True  # If date format is invalid, consider it expired
    
    def to_file_format(self) -> str:
        """Convert to markdown file format"""
        charts_section = ""
        for i, chart in enumerate(self.charts, 1):
            charts_section += f"""
### 图表 {i}: {chart.chart_title}

**图表类型:** {chart.chart_type}

**图表说明:** {chart.chart_summary}
"""
        
        return f"""# {self.dashboard_name}

## 基本信息

- **Dashboard ID:** {self.dashboard_id}
- **Dashboard 名称:** {self.dashboard_name}
- **最后更新时间:** {self.last_update_time}

## 看板概述

{self.dashboard_summary}

## 图表详情

{charts_section}
"""

class ContextManager:
    """Manages dashboard context files and caching"""
    
    def __init__(self, context_dir: str = "context", update_frequency_days: int = 7):
        self.context_dir = Path(context_dir)
        self.update_frequency_days = update_frequency_days
        self.context_cache: Dict[str, DashboardContext] = {}
        self.cache_lock = threading.RLock()
        
        # Create context directory if not exists
        self.context_dir.mkdir(exist_ok=True)
        
        logger.info(f"✅ ContextManager initialized with directory: {self.context_dir}")
        self._load_existing_contexts()
    
    def _load_existing_contexts(self):
        """Load all existing context files into memory cache"""
        try:
            for file_path in self.context_dir.glob("*.md"):
                context = self._parse_context_file(file_path)
                if context:
                    with self.cache_lock:
                        self.context_cache[context.dashboard_id] = context
            logger.info(f"📁 Loaded {len(self.context_cache)} existing contexts")
        except Exception as e:
            logger.error(f"❌ Failed to load existing contexts: {e}")
    
    def _parse_context_file(self, file_path: Path) -> Optional[DashboardContext]:
        """Parse markdown context file into DashboardContext object"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract dashboard title from H1
            title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
            dashboard_name = title_match.group(1).strip() if title_match else 'Unknown'
            
            # Extract information from basic info section
            dashboard_id_match = re.search(r'\*\*Dashboard ID:\*\*\s*(.+)', content)
            dashboard_name_match = re.search(r'\*\*Dashboard 名称:\*\*\s*(.+)', content)
            update_time_match = re.search(r'\*\*最后更新时间:\*\*\s*(.+)', content)
            
            # Extract summary from 看板概述 section
            summary_match = re.search(r'## 看板概述\s*\n\s*(.+?)\s*\n\s*## 图表详情', content, re.DOTALL)
            
            if not all([dashboard_id_match, update_time_match, summary_match]):
                logger.warning(f"⚠️ Invalid context file format: {file_path}")
                return None
            
            # Extract charts information
            charts = []
            chart_sections = re.findall(r'### 图表 \d+:\s*(.+?)\s*\n\*\*图表类型:\*\*\s*(.+?)\s*\n\*\*图表说明:\*\*\s*(.+?)(?=\s*\n### 图表|\s*\n\s*$)', content, re.DOTALL)
            
            for chart_title, chart_type, chart_summary in chart_sections:
                chart = ChartInfo(
                    chart_title=chart_title.strip(),
                    chart_type=chart_type.strip(),
                    chart_summary=chart_summary.strip()
                )
                charts.append(chart)
            
            return DashboardContext(
                dashboard_id=dashboard_id_match.group(1).strip(),
                dashboard_name=dashboard_name_match.group(1).strip() if dashboard_name_match else dashboard_name,
                last_update_time=update_time_match.group(1).strip(),
                dashboard_summary=summary_match.group(1).strip(),
                charts=charts,
                file_path=str(file_path)
            )
        except Exception as e:
            logger.error(f"❌ Failed to parse context file {file_path}: {e}")
            return None
    
    def get_dashboard_context(self, dashboard_id: str) -> Optional[DashboardContext]:
        """Get dashboard context from cache"""
        with self.cache_lock:
            return self.context_cache.get(dashboard_id)
    
    def get_all_contexts(self) -> List[DashboardContext]:
        """Get all cached contexts"""
        with self.cache_lock:
            return list(self.context_cache.values())
    
    def save_context(self, context: DashboardContext) -> bool:
        """Save context to file and cache"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(context.file_path), exist_ok=True)
            
            logger.info(f"💾 Saving context for dashboard: {context.dashboard_name} (ID: {context.dashboard_id})")
            logger.info(f"📁 Target file path: {context.file_path}")
            
            # Save to file
            with open(context.file_path, 'w', encoding='utf-8') as f:
                f.write(context.to_file_format())
            
            logger.info(f"📄 Context file written successfully")
            
            # Update cache
            with self.cache_lock:
                old_context = self.context_cache.get(context.dashboard_id)
                self.context_cache[context.dashboard_id] = context
                
                if old_context:
                    logger.info(f"🔄 Updated cached context for: {context.dashboard_id}")
                else:
                    logger.info(f"🆕 Added new context to cache: {context.dashboard_id}")
            
            logger.info(f"✅ Context saved successfully for dashboard: {context.dashboard_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save context for {context.dashboard_id}: {e}")
            return False
    
    def create_context_file_path(self, dashboard_id: str) -> str:
        """Create file path for new context"""
        safe_id = re.sub(r'[^\w\-_\.]', '_', dashboard_id)
        return str(self.context_dir / f"{safe_id}.md")
    
    def delete_context(self, dashboard_id: str) -> bool:
        """Delete context file and remove from cache"""
        try:
            context = self.context_cache.get(dashboard_id)
            file_path = None
            
            if context:
                file_path = context.file_path
                logger.info(f"🗑️ Deleting context for dashboard: {dashboard_id} (file: {file_path})")
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"📁 Context file deleted: {file_path}")
                else:
                    logger.warning(f"⚠️ Context file not found: {file_path}")
            else:
                logger.info(f"🗑️ Deleting cached context for dashboard: {dashboard_id} (no file reference)")
            
            with self.cache_lock:
                if dashboard_id in self.context_cache:
                    self.context_cache.pop(dashboard_id)
                    logger.info(f"🧹 Removed from cache: {dashboard_id}")
                else:
                    logger.info(f"ℹ️ Dashboard not in cache: {dashboard_id}")
            
            logger.info(f"✅ Context deletion completed for dashboard: {dashboard_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete context for {dashboard_id}: {e}")
            return False
    
    def get_expired_dashboards(self, available_dashboard_ids: List[str]) -> List[str]:
        """Get list of dashboard IDs that need updating (not in context or expired)"""
        expired_dashboards = []
        
        for dashboard_id in available_dashboard_ids:
            context = self.get_dashboard_context(dashboard_id)
            
            # If context doesn't exist or is expired
            if not context or context.is_expired(self.update_frequency_days):
                expired_dashboards.append(dashboard_id)
        
        logger.info(f"⏰ Found {len(expired_dashboards)} dashboards needing updates")
        return expired_dashboards
    
    def cleanup_old_contexts(self, available_dashboard_ids: List[str]) -> int:
        """Remove contexts for dashboards that no longer exist"""
        removed_count = 0
        
        with self.cache_lock:
            existing_ids = list(self.context_cache.keys())
            for dashboard_id in existing_ids:
                if dashboard_id not in available_dashboard_ids:
                    if self.delete_context(dashboard_id):
                        removed_count += 1
        
        logger.info(f"🧹 Cleaned up {removed_count} old contexts")
        return removed_count

class DashboardAnalyzer:
    """Analyzes dashboard content using AI"""
    
    def __init__(self, ai_analyzer):
        self.ai_analyzer = ai_analyzer
        logger.info("🤖 DashboardAnalyzer initialized")
    
    def analyze_dashboard_content(self, dashboard_data: Dict[str, Any]) -> Optional[DashboardContext]:
        """Analyze dashboard and create context"""
        try:
            dashboard_id = dashboard_data.get('dashboard_id')
            dashboard_title = dashboard_data.get('dashboard_title', 'Unknown')
            screenshot_path = dashboard_data.get('dashboard_screenshot')
            charts = dashboard_data.get('charts', [])
            
            if not dashboard_id:
                logger.error(f"❌ Missing dashboard_id for dashboard analysis")
                return None
            
            # For initial context generation, screenshot might not be available yet
            # In this case, we'll create a basic context without screenshot analysis
            if not screenshot_path or not os.path.exists(screenshot_path):
                logger.info(f"📝 Creating basic context for dashboard: {dashboard_title} (no screenshot available)")
                
                # Create basic context without screenshot analysis
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Generate basic summary based on dashboard title and metadata
                basic_summary = f"{dashboard_title} 是一个数据看板，包含 {len(charts)} 个图表。"
                
                # Create basic chart info list
                chart_info_list = []
                for i, chart in enumerate(charts):
                    chart_title = chart.get('title', f'图表 {i+1}')
                    chart_type = chart.get('type', '未知类型')
                    chart_info = ChartInfo(
                        title=chart_title,
                        chart_type=chart_type,
                        description=f"{chart_title} - {chart_type}"
                    )
                    chart_info_list.append(chart_info)
                
                return DashboardContext(
                    dashboard_id=dashboard_id,
                    dashboard_name=dashboard_title,
                    last_update_time=current_time,
                    dashboard_summary=basic_summary,
                    charts=chart_info_list,
                    file_path="",  # Will be set by caller
                    screenshot_path=screenshot_path
                )
            
            logger.info(f"🔍 Analyzing dashboard content with screenshot: {dashboard_title}")
            
            # Step 1: Analyze overall dashboard content
            dashboard_analysis_prompt = """请详细分析这个看板的内容，包括：

1. 看板的主要功能和目的
2. 包含的关键指标和数据维度
3. 数据可视化类型和布局
4. 业务价值和使用场景
5. 数据源和时间范围（如果能看出）

请提供全面但简洁的看板内容描述，便于后续理解这个看板的作用和价值。"""
            
            # Use existing AI analyzer for dashboard analysis
            if hasattr(self.ai_analyzer, 'analyze_dashboard_progressively'):
                dashboard_summary = self.ai_analyzer.analyze_dashboard_progressively(
                    question="请详细分析这个看板的内容和功能",
                    dashboard_data=dashboard_data
                )
            else:
                # Fallback to multimodal analysis
                screenshots = [{"path": screenshot_path}]
                dashboard_summary = self.ai_analyzer.analyze_multimodal(
                    question=dashboard_analysis_prompt,
                    screenshots=screenshots
                )
            
            # Step 2: Analyze individual charts if available
            chart_infos = []
            
            if charts:
                logger.info(f"📊 Analyzing {len(charts)} charts for dashboard: {dashboard_title}")
                
                for i, chart in enumerate(charts):
                    chart_title = chart.get('chart_title', f'Chart {i+1}')
                    chart_screenshot = chart.get('chart_screenshot')
                    chart_type = chart.get('chart_data', {}).get('type', 'Unknown')
                    
                    if chart_screenshot:
                        try:
                            # Analyze individual chart
                            chart_analysis_prompt = f"""请分析这个图表，提供以下信息：

1. 图表的主要功能和展示的数据
2. 图表类型和数据维度
3. 关键指标和趋势
4. 业务价值和洞察

请简洁明了地描述这个图表的作用和价值。"""
                            
                            # Create chart data for analysis
                            chart_data = {
                                'dashboard_id': dashboard_id,
                                'dashboard_title': dashboard_title,
                                'dashboard_screenshot': chart_screenshot
                            }
                            
                            chart_summary = self.ai_analyzer.analyze_dashboard_progressively(
                                question=chart_analysis_prompt,
                                dashboard_data=chart_data
                            )
                            
                            # Create chart info object
                            chart_info = ChartInfo(
                                chart_title=chart_title,
                                chart_type=chart_type,
                                chart_summary=chart_summary,
                                screenshot_path=chart_screenshot
                            )
                            chart_infos.append(chart_info)
                            
                            logger.info(f"✅ Analyzed chart {i+1}/{len(charts)}: {chart_title}")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to analyze chart {chart_title}: {e}")
                            # Create basic chart info anyway
                            chart_info = ChartInfo(
                                chart_title=chart_title,
                                chart_type=chart_type,
                                chart_summary=f"图表分析失败: {str(e)}",
                                screenshot_path=chart_screenshot
                            )
                            chart_infos.append(chart_info)
            
            # Create context object
            context = DashboardContext(
                dashboard_id=dashboard_id,
                dashboard_name=dashboard_title,
                last_update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                dashboard_summary=dashboard_summary,
                charts=chart_infos,
                file_path="",  # Will be set by ContextManager
                screenshot_path=screenshot_path
            )
            
            logger.info(f"✅ Dashboard analysis completed: {dashboard_title} with {len(chart_infos)} charts")
            return context
            
        except Exception as e:
            logger.error(f"❌ Dashboard analysis failed: {e}")
            return None

class DashboardSelector:
    """AI-powered dashboard selection based on user questions"""
    
    def __init__(self, ai_analyzer):
        self.ai_analyzer = ai_analyzer
        logger.info("🎯 DashboardSelector initialized")
    
    def select_relevant_dashboards(self, question: str, contexts: List[DashboardContext], top_k: int = 3) -> List[Tuple[DashboardContext, float]]:
        """Select top K most relevant dashboards for the user's question"""
        try:
            if not contexts:
                return []
            
            logger.info(f"🔍 Selecting top {top_k} dashboards for question: {question[:100]}...")
            
            # Prepare context summaries for AI analysis with detailed chart information
            context_summaries = []
            for i, context in enumerate(contexts):
                summary = f"""
看板 {i+1}:
ID: {context.dashboard_id}
名称: {context.dashboard_name}
摘要: {context.dashboard_summary[:800]}...
图表数量: {len(context.charts)}
最后更新: {context.last_update_time}
"""
                
                # Add chart information for better matching
                if context.charts:
                    summary += "\n包含图表:\n"
                    for j, chart in enumerate(context.charts[:5]):  # Limit to first 5 charts
                        summary += f"- {chart.chart_title} ({chart.chart_type}): {chart.chart_summary[:200]}...\n"
                
                context_summaries.append(summary)
            
            all_contexts = "\n---\n".join(context_summaries)
            
            # Create selection prompt
            selection_prompt = f"""用户问题：{question}

可用的看板信息：
{all_contexts}

请分析用户问题，选择最相关的{top_k}个看板来回答这个问题。

选择标准：
1. 数据相关性：看板包含的问题相关的数据类型和指标
2. 业务匹配度：看板的业务领域与用户问题的匹配程度
3. 数据完整性：看板数据是否能全面回答问题
4. 时效性：看板数据的更新频率和时间范围是否合适

请返回JSON格式的结果，包含选中的看板索引和相关度分数（0-1）：
{{
    "selections": [
        {{"index": 0, "relevance_score": 0.9, "reason": "相关原因说明"}},
        {{"index": 1, "relevance_score": 0.8, "reason": "相关原因说明"}},
        {{"index": 2, "relevance_score": 0.7, "reason": "相关原因说明"}}
    ]
}}

要求：
1. 严格按照JSON格式返回
2. relevance_score必须是0-1之间的数值
3. 必须选择正好{top_k}个最相关的看板
4. reason字段要说明选择的具体原因
"""
            
            # Call AI for selection
            messages = [
                {"role": "system", "content": "你是一位专业的数据分析师，擅长根据用户问题选择最合适的数据看板。请严格按照JSON格式返回结果。"},
                {"role": "user", "content": selection_prompt}
            ]
            
            # Try AI API call with retry logic
            max_retries = 2
            result = None
            
            for attempt in range(max_retries):
                try:
                    result = self.ai_analyzer._call_ai_api(messages, max_tokens=1500, timeout=60.0)
                    if result and not result.startswith("AI API调用失败") and not result.startswith("AI API返回空内容"):
                        break
                    elif attempt < max_retries - 1:
                        logger.warning(f"⚠️ AI API call attempt {attempt + 1} failed, retrying...")
                        import time
                        time.sleep(1)  # Wait 1 second before retry
                except Exception as e:
                    logger.warning(f"⚠️ AI API call attempt {attempt + 1} failed with exception: {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)  # Wait 1 second before retry
            
            # If all attempts failed, use fallback
            if not result or result.startswith("AI API调用失败") or result.startswith("AI API返回空内容"):
                logger.warning(f"⚠️ All AI API call attempts failed, using fallback selection")
                # Fallback: return first K dashboards with default scores
                fallback_dashboards = contexts[:top_k]
                logger.warning(f"⚠️ Using fallback selection: first {top_k} dashboards:")
                for i, context in enumerate(fallback_dashboards):
                    logger.warning(f"   {i+1}. ID: {context.dashboard_id}, 名称: {context.dashboard_name}")
                return [(ctx, 0.5) for ctx in fallback_dashboards]
            
            # Log the AI response for debugging
            logger.debug(f"🤖 AI selection response: {result}")
            
            # Parse JSON result with better error handling
            try:
                # Clean the result - remove markdown formatting and other artifacts
                cleaned_result = result.strip()
                if cleaned_result.startswith('```json'):
                    cleaned_result = cleaned_result[7:]
                if cleaned_result.endswith('```'):
                    cleaned_result = cleaned_result[:-3]
                cleaned_result = cleaned_result.strip()
                
                # Remove any leading/trailing non-JSON characters
                cleaned_result = cleaned_result.strip()
                if not cleaned_result.startswith('{'):
                    # Find the start of JSON
                    start_idx = cleaned_result.find('{')
                    if start_idx != -1:
                        cleaned_result = cleaned_result[start_idx:]
                
                # Try to parse JSON
                result_data = json.loads(cleaned_result)
                selections = result_data.get("selections", [])
                
                # Convert to (context, score) tuples
                selected_dashboards = []
                for selection in selections:
                    index = selection.get("index")
                    score = selection.get("relevance_score", 0.0)
                    
                    if 0 <= index < len(contexts):
                        selected_dashboards.append((contexts[index], score))
                
                # Sort by relevance score
                selected_dashboards.sort(key=lambda x: x[1], reverse=True)
                
                # Log selected dashboards with IDs and names
                final_selection = selected_dashboards[:top_k]
                logger.info(f"✅ Selected {len(final_selection)} relevant dashboards:")
                for i, (context, score) in enumerate(final_selection):
                    logger.info(f"   {i+1}. ID: {context.dashboard_id}, 名称: {context.dashboard_name}, 相关度: {score:.2f}")
                
                return final_selection
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse AI selection result: {e}")
                logger.error(f"❌ Raw AI response: {result}")
                
                # Try to extract JSON from the response using regex
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    try:
                        extracted_json = json_match.group()
                        result_data = json.loads(extracted_json)
                        selections = result_data.get("selections", [])
                        
                        selected_dashboards = []
                        for selection in selections:
                            index = selection.get("index")
                            score = selection.get("relevance_score", 0.0)
                            
                            if 0 <= index < len(contexts):
                                selected_dashboards.append((contexts[index], score))
                        
                        selected_dashboards.sort(key=lambda x: x[1], reverse=True)
                        final_selection = selected_dashboards[:top_k]
                        logger.info(f"✅ Selected {len(final_selection)} relevant dashboards (after JSON extraction):")
                        for i, (context, score) in enumerate(final_selection):
                            logger.info(f"   {i+1}. ID: {context.dashboard_id}, 名称: {context.dashboard_name}, 相关度: {score:.2f}")
                        return final_selection
                    except json.JSONDecodeError:
                        logger.error("❌ Failed to parse extracted JSON")
                
                # Fallback: return first K dashboards
                fallback_dashboards = contexts[:top_k]
                logger.warning(f"⚠️ Using fallback selection: first {top_k} dashboards:")
                for i, context in enumerate(fallback_dashboards):
                    logger.warning(f"   {i+1}. ID: {context.dashboard_id}, 名称: {context.dashboard_name}")
                return [(ctx, 0.5) for ctx in fallback_dashboards]
                
        except Exception as e:
            logger.error(f"❌ Dashboard selection failed: {e}")
            return []

class SmartContextSystem:
    """Main system that integrates all components"""
    
    def __init__(self, ai_analyzer, context_dir: str = "context", update_frequency_days: int = 7, use_faiss: bool = True):
        self.context_manager = ContextManager(context_dir, update_frequency_days)
        self.dashboard_analyzer = DashboardAnalyzer(ai_analyzer)
        self.dashboard_selector = DashboardSelector(ai_analyzer)
        
        # Initialize FAISS index manager if enabled
        self.use_faiss = use_faiss
        self.faiss_index_manager = None
        if use_faiss:
            try:
                from faiss_index_manager import FAISSIndexManager
                self.faiss_index_manager = FAISSIndexManager(self.context_manager)
                logger.info("🔍 FAISS index manager initialized")
            except ImportError as e:
                logger.warning(f"⚠️ FAISS not available: {e}, falling back to AI selection")
                self.use_faiss = False
        
        logger.info("🚀 SmartContextSystem initialized")
    
    def update_dashboard_contexts(self, available_dashboards: List[Dict[str, Any]], force_update: bool = False) -> Dict[str, Any]:
        """Update contexts for dashboards that need it"""
        
        # If force_update is True, update all dashboards regardless of expiration status
        if force_update:
            logger.info("🔄 Force updating dashboard contexts...")
            # Delete existing context files only for the dashboards being processed
            for dashboard in available_dashboards:
                dashboard_id = dashboard.get('dashboard_id')
                if dashboard_id:
                    self.context_manager.delete_context(dashboard_id)
        try:
            # Get dashboard IDs
            dashboard_ids = [d.get('dashboard_id') for d in available_dashboards if d.get('dashboard_id')]
            
            # Only clean up old contexts if processing multiple dashboards
            # Skip cleanup for single dashboard processing to avoid deleting other contexts
            removed_count = 0
            if len(dashboard_ids) > 1:
                logger.info("🧹 Processing multiple dashboards, cleaning up old contexts...")
                removed_count = self.context_manager.cleanup_old_contexts(dashboard_ids)
            else:
                logger.info("📋 Processing single dashboard, skipping context cleanup to preserve other contexts")
            
            # Get dashboards that need updates
            expired_dashboards = self.context_manager.get_expired_dashboards(dashboard_ids)
            
            update_results = {
                "total_dashboards": len(dashboard_ids),
                "expired_dashboards": len(expired_dashboards),
                "removed_old_contexts": removed_count,
                "updated_contexts": [],
                "failed_updates": []
            }
            
            # Update expired dashboards
            for dashboard_id in expired_dashboards:
                # Find dashboard data
                dashboard_data = next((d for d in available_dashboards if d.get('dashboard_id') == dashboard_id), None)
                
                if dashboard_data:
                    # Analyze dashboard
                    context = self.dashboard_analyzer.analyze_dashboard_content(dashboard_data)
                    
                    if context:
                        # Set file path and save
                        context.file_path = self.context_manager.create_context_file_path(dashboard_id)
                        if self.context_manager.save_context(context):
                            update_results["updated_contexts"].append({
                                "dashboard_id": dashboard_id,
                                "dashboard_name": context.dashboard_name,
                                "update_time": context.last_update_time
                            })
                        else:
                            update_results["failed_updates"].append({
                                "dashboard_id": dashboard_id,
                                "error": "Failed to save context"
                            })
                    else:
                        update_results["failed_updates"].append({
                            "dashboard_id": dashboard_id,
                            "error": "Analysis failed"
                        })
                else:
                    update_results["failed_updates"].append({
                        "dashboard_id": dashboard_id,
                        "error": "Dashboard data not found"
                    })
            
            logger.info(f"📊 Context update completed: {update_results}")
            
            # Update FAISS index if enabled and contexts were updated
            if self.use_faiss and self.faiss_index_manager and update_results["updated_contexts"]:
                logger.info("🔄 Updating FAISS index after context updates...")
                try:
                    if self.faiss_index_manager.build_index_from_contexts():
                        logger.info("✅ FAISS index updated successfully")
                    else:
                        logger.warning("⚠️ FAISS index update failed")
                except Exception as e:
                    logger.error(f"❌ FAISS index update error: {e}")
            
            return update_results
            
        except Exception as e:
            logger.error(f"❌ Context update failed: {e}")
            return {"error": str(e)}
    
    def select_dashboards_for_question(self, question: str, top_k: int = 3) -> List[Tuple[DashboardContext, float]]:
        """Select most relevant dashboards for user question"""
        try:
            # Get all available contexts
            all_contexts = self.context_manager.get_all_contexts()
            
            if not all_contexts:
                logger.warning("⚠️ No contexts available for selection")
                return []
            
            # Use FAISS if available and enabled
            if self.use_faiss and self.faiss_index_manager:
                logger.info(f"🔍 Using FAISS for dashboard selection: {question[:50]}...")
                selected_dashboards = self.faiss_index_manager.search_dashboards(question, top_k)
                
                if selected_dashboards:
                    logger.info(f"✅ FAISS found {len(selected_dashboards)} relevant dashboards")
                    return selected_dashboards
                else:
                    logger.warning("⚠️ FAISS search returned no results, falling back to AI selection")
            
            # Fallback to AI selection
            logger.info(f"🤖 Using AI for dashboard selection: {question[:50]}...")
            selected_dashboards = self.dashboard_selector.select_relevant_dashboards(
                question, all_contexts, top_k
            )
            
            return selected_dashboards
            
        except Exception as e:
            logger.error(f"❌ Dashboard selection failed: {e}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        try:
            all_contexts = self.context_manager.get_all_contexts()
            
            # Calculate statistics
            total_contexts = len(all_contexts)
            expired_contexts = sum(1 for ctx in all_contexts if ctx.is_expired())
            recent_contexts = sum(1 for ctx in all_contexts if not ctx.is_expired())
            
            status = {
                "total_contexts": total_contexts,
                "recent_contexts": recent_contexts,
                "expired_contexts": expired_contexts,
                "update_frequency_days": self.context_manager.update_frequency_days,
                "context_directory": str(self.context_manager.context_dir),
                "cache_size": len(self.context_manager.context_cache),
                "faiss_enabled": self.use_faiss,
                "selection_method": "FAISS" if self.use_faiss else "AI"
            }
            
            # Add FAISS-specific status if enabled
            if self.use_faiss and self.faiss_index_manager:
                try:
                    faiss_status = self.faiss_index_manager.get_index_status()
                    status["faiss_status"] = faiss_status
                except Exception as e:
                    status["faiss_error"] = str(e)
            
            return status
        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    # This would be integrated with the existing AI analyzer
    print("Smart Context System - Example Usage")
    print("This system would be integrated with the existing AI analyzer in app.py")