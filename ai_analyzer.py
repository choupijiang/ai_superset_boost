import os
import json
import base64
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clean_ai_response(text: str) -> str:
    """Clean AI response by removing HTML tags, CSS styles, and other unwanted formatting"""
    if not text:
        return text
    
    import re
    
    # Step 1: Remove CSS style blocks and attributes completely
    # Remove style="..." attributes
    text = re.sub(r'style\s*=\s*"[^"]*"', '', text, flags=re.IGNORECASE)
    text = re.sub(r'style\s*=\s*\'[^\']*\'', '', text, flags=re.IGNORECASE)
    
    # Step 2: Remove CSS properties patterns that appear without style attributes
    css_patterns = [
        r'color\s*:\s*[^;]+;?',
        r'margin\s*:\s*[^;]+;?',
        r'padding\s*:\s*[^;]+;?',
        r'font-size\s*:\s*[^;]+;?',
        r'font-weight\s*:\s*[^;]+;?',
        r'background\s*:\s*[^;]+;?',
        r'border\s*:\s*[^;]+;?',
        r'text-align\s*:\s*[^;]+;?',
        r'line-height\s*:\s*[^;]+;?',
        r'font-family\s*:\s*[^;]+;?',
        r'display\s*:\s*[^;]+;?',
        r'width\s*:\s*[^;]+;?',
        r'height\s*:\s*[^;]+;?',
        r'list-style-type\s*:\s*[^;]+;?',
    ]
    
    for pattern in css_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Step 3: Remove HTML tags completely
    text = re.sub(r'<[^>]*>', '', text)
    
    # Step 4: Remove any remaining HTML attributes
    text = re.sub(r'\w+\s*=\s*"[^"]*"', '', text)
    text = re.sub(r'\w+\s*=\s*\'[^\']*\'', '', text)
    
    # Step 5: Remove orphaned CSS values that might be left
    text = re.sub(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}', '', text)  # Remove hex colors
    text = re.sub(r'\b\d+px\b', '', text)  # Remove pixel values
    text = re.sub(r'\b\d+em\b', '', text)  # Remove em values
    text = re.sub(r'\b\d+%\b', '', text)   # Remove percentage values
    
    # Step 6: Remove orphaned quotes and special characters
    text = re.sub(r'^["\'>\s]+', '', text, flags=re.MULTILINE)
    text = re.sub(r'["\'>\s]+$', '', text, flags=re.MULTILINE)
    
    # Step 7: Clean up multiple quotes and special characters
    text = re.sub(r'["\']{2,}', '', text)
    text = re.sub(r'["\'>]', '', text)
    
    # Step 8: Split by lines and clean each line
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Remove any remaining CSS-like patterns more aggressively
        line = re.sub(r'\b\w+\s*:\s*[^;]*;?', '', line, flags=re.IGNORECASE)
        
        # Remove orphaned CSS property names and values
        line = re.sub(r'\b(border|padding|margin|color|font|background|width|height|display|text-align|line-height|font-weight|font-size)\s*[-\w]*', '', line, flags=re.IGNORECASE)
        
        # Clean up spacing
        line = re.sub(r'\s+', ' ', line)
        line = line.replace(' .', '.').replace(' ,', ',').replace(' ;', ';')
        
        if line.strip():
            cleaned_lines.append(line.strip())
    
    # Step 9: Join cleaned lines and ensure proper markdown formatting
    text = '\n\n'.join(cleaned_lines)
    
    # Step 10: Final cleanup - remove any lines that are just CSS properties or orphaned CSS parts
    lines = text.split('\n')
    final_lines = []
    for line in lines:
        line = line.strip()
        # Skip lines that look like CSS properties or contain only CSS-related words
        if not re.match(r'^[a-zA-Z-]+\s*:\s*.*;?$', line) and not re.match(r'^\s*(border|padding|margin|color|font|background)\s*[-\w]*\s*$', line, flags=re.IGNORECASE):
            final_lines.append(line)
    
    text = '\n'.join(final_lines)
    
    return text.strip()

class AIAnalyzer:
    def __init__(self):
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.openai_api_base = os.environ.get('OPENAI_API_BASE')
        self.openai_model = os.environ.get('OPENAI_MODEL', 'glm-4v-plus')
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library is required but not available")
        
        self.client = OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_base
        )
        logger.info(f"✅ Using GLM-4.5 with BigModel.cn - Model: {self.openai_model}")
    
    def encode_image(self, image_path: str) -> Optional[str]:
        """Encode image to base64 with proper data URL format for BigModel.cn"""
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # Determine image type from file extension
                import mimetypes
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type:
                    mime_type = 'image/png'
                
                # Format as data URL: data:image/png;base64,<base64_data>
                data_url = f"data:{mime_type};base64,{base64_data}"
                return data_url
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            return None
    
    def _call_ai_api(self, messages: List[Dict], model: str = None, max_tokens: int = 2000, timeout: float = 30.0) -> str:
        """Generic AI API call method"""
        try:
            # Configure timeout and retry settings
            response = self.client.chat.completions.create(
                model=model or self.openai_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
                timeout=timeout  # Configurable timeout
            )
            content = response.choices[0].message.content
            if not content or content.strip() == "":
                logger.warning("⚠️ AI API returned empty content")
                logger.warning(f"⚠️ Response details: {response}")
                logger.warning(f"⚠️ Model used: {model or self.openai_model}")
                logger.warning(f"⚠️ Max tokens: {max_tokens}")
                return "AI API返回空内容，可能是网络问题或API限制"
            return content
        except Exception as e:
            error_msg = f"AI API调用失败: {str(e)}"
            logger.error(error_msg)
            # Check if it's a connection error and provide more helpful message
            if "Connection error" in str(e) or "timeout" in str(e).lower():
                logger.warning("⚠️ 网络连接问题，请检查网络连接或稍后重试")
            return error_msg
    
    def analyze_dashboard_progressively(self, question: str, dashboard_data: Dict[str, Any], progress_callback=None) -> str:
        """
        Analyze a single dashboard progressively with simplified approach
        
        Args:
            question: Business question to analyze
            dashboard_data: Dictionary containing dashboard information and screenshots
            progress_callback: Optional callback function to send progress updates
        """
        try:
            dashboard_title = dashboard_data.get('dashboard_title', 'Unknown')
            logger.info(f"🤖 Analyzing dashboard: {dashboard_title}")
            
            # Send start event if callback provided
            if progress_callback:
                progress_callback({
                    'type': 'analysis_started',
                    'dashboard_title': dashboard_title,
                    'message': '开始分析看板数据'
                })
            
            # Get dashboard screenshot
            dashboard_screenshot = dashboard_data.get('dashboard_screenshot')
            if not dashboard_screenshot:
                return f"看板 {dashboard_title} 没有可用的截图"
            
            # Construct full path if needed
            if not os.path.isabs(dashboard_screenshot):
                # Convert from relative URL path to filesystem path
                if dashboard_screenshot.startswith('screenshots/'):
                    dashboard_screenshot = os.path.join(os.path.dirname(__file__), dashboard_screenshot)
                else:
                    dashboard_screenshot = os.path.join('screenshots', dashboard_screenshot)
            
            if not os.path.exists(dashboard_screenshot):
                return f"看板截图文件不存在: {dashboard_screenshot}"
            
            # Encode image
            image_base64 = self.encode_image(dashboard_screenshot)
            if not image_base64:
                return f"图片编码失败: {dashboard_screenshot}"
            
            # Prepare content with just question and image
            content = [
                {"type": "text", "text": f"请分析这个看板截图，回答业务问题：{question}"},
                {"type": "image_url", "image_url": {"url": image_base64}}
            ]
            
            # Simple system message
            system_message = """你是一位专业的商业数据分析师。请仔细分析看板截图，识别关键指标和趋势，回答用户的业务问题。

极其严格的要求（必须严格遵守）：
1. 请用中文回答，提供具体的洞察和建议
2. 绝对禁止使用任何HTML标签、CSS样式、Markdown格式或其他格式化代码
3. 只返回纯文本内容，严禁任何格式化
4. 严禁返回任何包含以下内容的内容：
   - 任何HTML标签（如 <div>, <span>, <p>, <h1> 等）
   - 任何CSS样式（如 style="color: #2c3e50; margin: 20px 0 10px 0;"）
   - 任何CSS属性（如 color: #2c3e50; margin: 20px 0 10px 0;）
   - 任何颜色代码（如 #2c3e50, #667eea 等）
   - 任何字体大小（如 1.3em, 14px 等）
   - 任何边框或布局属性（如 border-left: 3px solid #667eea;）
   - 任何JavaScript代码
   - 任何编程代码或格式化标记
   - 任何引号包含的样式信息
   - 任何列表样式（如 list-style-type: disc;）

5. 请严格按照以下纯文本格式回答，不要添加任何格式化：

主要发现：
[在这里描述从看板中观察到的主要数据和趋势，使用纯文本]

关键洞察：
[在这里提供2-3个最重要的业务洞察，使用纯文本]

建议：
[在这里基于数据提供具体的业务建议，使用纯文本]

6. 如果违反以上任何要求，将会严重影响用户体验，请务必只返回纯文本内容。
7. 不要添加任何颜色、字体、边框、间距等CSS相关的描述。
8. 内容应该像纯文本文档一样简洁明了。"""
            
            # Call AI API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": content}
            ]
            
            result = self._call_ai_api(messages)
            if result.startswith("AI API调用失败") or result.startswith("AI API返回空内容"):
                return result
            
            # Log the original AI response for debugging
            logger.info(f"🔍 Original AI response for {dashboard_title}:")
            logger.info(f"--- BEGIN RAW AI RESPONSE ---")
            logger.info(result)
            logger.info(f"--- END RAW AI RESPONSE ---")
            
            # Clean the result to remove any HTML tags or unwanted formatting
            cleaned_result = clean_ai_response(result)
            
            # Log the cleaned result for comparison
            logger.info(f"🧹 Cleaned AI response for {dashboard_title}:")
            logger.info(f"--- BEGIN CLEANED AI RESPONSE ---")
            logger.info(cleaned_result)
            logger.info(f"--- END CLEANED AI RESPONSE ---")
            
            result = cleaned_result
            
            logger.info(f"✅ Dashboard analysis completed: {dashboard_title}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Dashboard analysis failed: {e}")
            return f"分析看板 {dashboard_data.get('dashboard_title', 'Unknown')} 时出现错误：{str(e)}"
    
    def combine_multiple_analyses(self, question: str, individual_analyses: List[Dict[str, Any]]) -> str:
        """
        Combine multiple individual dashboard analyses into a comprehensive answer
        
        Args:
            question: Original business question
            individual_analyses: List of dictionaries containing dashboard analysis results
        """
        try:
            logger.info(f"🤖 Combining {len(individual_analyses)} analyses")
            
            # Prepare analysis summaries
            analysis_summaries = []
            for i, analysis in enumerate(individual_analyses):
                dashboard_title = analysis.get('dashboard_title', f'看板{i+1}')
                analysis_result = analysis.get('analysis', '无分析结果')
                analysis_summaries.append(f"看板 {i+1}: {dashboard_title}\n分析结果: {analysis_result}")
            
            combined_text = "\n\n".join(analysis_summaries)
            
            # Simple prompt for combining analyses
            prompt = f"""原始业务问题：{question}

各看板的独立分析结果：
{combined_text}

请综合以上所有看板的分析结果，提供一个全面的回答。

极其严格的格式要求（必须严格遵守）：

整体洞察：
综合所有看板数据的关键发现

关键趋势：
识别最重要的趋势和模式

跨看板关联：
分析不同看板数据之间的关系

综合建议：
提供整体性的业务建议

绝对严格禁止：
- 严禁使用任何HTML标签（如 <div>, <span>, <p>, <h1> 等）
- 严禁使用CSS样式（如 style="color: #2c3e50; margin: 20px 0 10px 0;"）
- 严禁使用CSS属性（如 color: #2c3e50; margin: 20px 0 10px 0;）
- 严禁使用颜色代码（如 #2c3e50, #667eea 等）
- 严禁使用字体大小（如 1.3em, 14px 等）
- 严禁使用边框或布局属性（如 border-left: 3px solid #667eea;）
- 严禁使用列表样式（如 list-style-type: disc;）
- 严禁使用Markdown格式
- 严禁使用任何格式化代码或标记
- 严禁使用任何引号包含的样式信息

请只返回纯文本内容，使用清晰的段落和简单的标题。如果返回任何格式化代码将严重影响用户体验。
内容应该像纯文本文档一样简洁明了，不要添加任何视觉样式的描述。"""
            
            # Call AI API for summary
            messages = [
                {"role": "system", "content": "你是一位专业的商业数据分析师，擅长综合多源数据进行全面分析。请用中文回答，严禁使用任何HTML标签、CSS样式或格式化代码。"},
                {"role": "user", "content": prompt}
            ]
            
            result = self._call_ai_api(messages, model='glm-4-plus', max_tokens=3000)
            if result.startswith("AI API调用失败") or result.startswith("AI API返回空内容"):
                return result
            
            # Log the original AI response for debugging
            logger.info(f"🔍 Original combined AI response:")
            logger.info(f"--- BEGIN RAW COMBINED AI RESPONSE ---")
            logger.info(result)
            logger.info(f"--- END RAW COMBINED AI RESPONSE ---")
            
            # Clean the result to remove any HTML tags or unwanted formatting
            cleaned_result = clean_ai_response(result)
            
            # Log the cleaned result for comparison
            logger.info(f"🧹 Cleaned combined AI response:")
            logger.info(f"--- BEGIN CLEANED COMBINED AI RESPONSE ---")
            logger.info(cleaned_result)
            logger.info(f"--- END CLEANED COMBINED AI RESPONSE ---")
            
            result = cleaned_result
            
            logger.info(f"✅ Successfully combined {len(individual_analyses)} analyses")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to combine analyses: {e}")
            return f"综合分析时出现错误：{str(e)}"
    
    # Legacy methods for backward compatibility
    def analyze_multimodal(self, question: str, screenshots: Optional[List[Dict[str, Any]]] = None, json_data: Optional[Union[Dict, List]] = None) -> str:
        """Legacy method - use simplified dashboard analysis instead"""
        if screenshots:
            # Convert to dashboard format and use new method
            dashboard_data = {
                'dashboard_title': 'Legacy Analysis',
                'dashboard_screenshot': screenshots[0]['path']
            }
            return self.analyze_dashboard_progressively(question, dashboard_data)
        return self._get_fallback_response(question)
    
    def analyze_with_screenshots(self, question: str, screenshots: List[Dict[str, Any]]) -> str:
        """Legacy method"""
        return self.analyze_multimodal(question, screenshots=screenshots)
    
    def analyze_with_json(self, question: str, json_data: Union[Dict, List]) -> str:
        """Legacy method"""
        return self._get_fallback_response(question)
    
    def analyze_text_only(self, question: str, dashboard_titles: List[str]) -> str:
        """Legacy method"""
        return self._get_fallback_response(question)
    
    def _get_fallback_response(self, question: str) -> str:
        """Get fallback response when AI analysis fails"""
        return f"""
抱歉，AI 分析暂时无法完成。对于您的业务问题"{question}"，建议您：

1. 直接查看 Superset 仪表板获取详细数据
2. 联系技术支持检查 AI 服务配置
3. 稍后重试分析

当前使用的 AI 提供商: GLM-4.5 (BigModel.cn)
请检查 API 密钥配置和网络连接。
"""