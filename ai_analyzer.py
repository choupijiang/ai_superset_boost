import os
import json
import base64
import requests
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

class AIAnalyzer:
    def __init__(self):
        # Initialize AI provider using OpenAI client with BigModel.cn
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.openai_api_base = os.environ.get('OPENAI_API_BASE')
        self.openai_model = os.environ.get('OPENAI_MODEL', 'glm-4v-plus')  # Use vision model by default
        
        if self.openai_api_key and OPENAI_AVAILABLE:
            self.ai_provider = 'openai'
            self.client = OpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_api_base
            )
            logger.info(f"✅ Using OpenAI client with BigModel.cn - Model: {self.openai_model}")
        else:
            # Fallback to mock mode
            self.ai_provider = 'mock'
            logger.warning("⚠️  No AI API keys available, using mock mode")
        
        logger.info(f"🤖 AI Analyzer initialized with provider: {self.ai_provider}")
    
    def encode_image(self, image_path: str) -> Optional[str]:
        """Encode image to base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            return None
    
    def analyze_multimodal(self, 
                         question: str, 
                         screenshots: Optional[List[Dict[str, Any]]] = None,
                         json_data: Optional[Union[Dict, List]] = None) -> str:
        """
        Multimodal analysis supporting images, JSON data, or both
        
        Args:
            question: Business question to analyze
            screenshots: List of screenshot dictionaries with 'path' and 'title' keys
            json_data: JSON data for analysis
        """
        try:
            logger.info(f"🤖 Starting multimodal analysis: {question}")
            
            if self.ai_provider == 'openai':
                return self._analyze_with_glm45_multimodal(question, screenshots, json_data)
            else:
                return self._analyze_with_mock(question, screenshots, json_data)
                
        except Exception as e:
            logger.error(f"❌ Multimodal analysis failed: {e}")
            return self._get_fallback_response(question)
    
    def _analyze_with_glm45_multimodal(self, 
                                     question: str, 
                                     screenshots: Optional[List[Dict[str, Any]]] = None,
                                     json_data: Optional[Union[Dict, List]] = None) -> str:
        """Analyze using GLM-4.5 multimodal capabilities"""
        try:
            # Prepare multimodal content
            content = [{"type": "text", "text": question}]
            
            # Add screenshots if available
            if screenshots:
                screenshot_count = 0
                for screenshot in screenshots[:5]:  # Limit to 5 screenshots
                    if os.path.exists(screenshot['path']):
                        image_base64 = self.encode_image(screenshot['path'])
                        if image_base64:
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            })
                            screenshot_count += 1
                logger.info(f"📸 Added {screenshot_count} screenshots for analysis")
            
            # Add JSON data if available
            if json_data:
                json_text = f"\n\nJSON Data:\n```json\n{json.dumps(json_data, ensure_ascii=False, indent=2)}\n```"
                content.append({"type": "text", "text": json_text})
                logger.info("📊 Added JSON data for analysis")
            
            # Build system message based on available data types
            system_parts = ["你是一位专业的商业数据分析师，专注于数据可视化和仪表板分析。"]
            
            if screenshots and json_data:
                system_parts.append("""
你的任务是：
1. 仔细分析提供的仪表板截图和JSON数据
2. 识别关键指标、趋势和模式
3. 结合可视化数据和结构化数据进行分析
4. 回答用户的具体业务问题
5. 提供可行的见解和建议
6. 在分析中保持具体和数据驱动

请用中文回答，专注于业务价值和实用洞察。""")
            elif screenshots:
                system_parts.append("""
你的任务是：
1. 仔细分析提供的仪表板截图
2. 识别关键指标、趋势和模式
3. 回答用户的具体业务问题
4. 提供可行的见解和建议
5. 在分析中保持具体和数据驱动

请用中文回答，专注于业务价值和实用洞察。""")
            elif json_data:
                system_parts.append("""
你的任务是：
1. 仔细分析提供的JSON数据
2. 识别关键指标、趋势和模式
3. 回答用户的具体业务问题
4. 提供可行的见解和建议
5. 在分析中保持具体和数据驱动

请用中文回答，专注于业务价值和实用洞察。""")
            
            system_message = "\n".join(system_parts)
            
            # Call GLM-4.5 API
            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=3000,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            logger.info(f"✅ GLM-4.5 multimodal analysis completed successfully")
            return answer
            
        except Exception as e:
            logger.error(f"❌ GLM-4.5 multimodal analysis failed: {e}")
            return self._get_fallback_response(question)
    
    def analyze_with_screenshots(self, question: str, screenshots: List[Dict[str, Any]]) -> str:
        """Legacy method for backward compatibility"""
        return self.analyze_multimodal(question, screenshots=screenshots)
    
    def analyze_with_json(self, question: str, json_data: Union[Dict, List]) -> str:
        """Analyze business question using JSON data"""
        return self.analyze_multimodal(question, json_data=json_data)
    
    def _analyze_with_mock(self, 
                          question: str, 
                          screenshots: Optional[List[Dict[str, Any]]] = None,
                          json_data: Optional[Union[Dict, List]] = None) -> str:
        """Mock analysis for testing purposes"""
        logger.info("🤖 Using mock analysis mode")
        
        # Determine what type of analysis to simulate
        has_screenshots = screenshots and len(screenshots) > 0
        has_json = json_data is not None
        
        if has_screenshots and has_json:
            analysis_type = "仪表板截图和JSON数据"
        elif has_screenshots:
            analysis_type = "仪表板截图"
        elif has_json:
            analysis_type = "JSON数据"
        else:
            analysis_type = "业务问题"
        
        mock_response = f"""
基于提供的{analysis_type}，我对您的业务问题"{question}"进行分析：

## 关键发现：
1. **数据质量**: {analysis_type}显示了完整的数据信息
2. **业务指标**: 包含了关键的性能指标
3. **趋势分析**: 可以识别出明显的业务趋势
4. **数据关联**: 不同数据源之间显示出一致性

## 建议行动：
1. **深入分析**: 建议进一步分析具体数据点
2. **监控指标**: 持续监控关键业务指标
3. **数据驱动决策**: 基于数据制定业务策略
4. **定期回顾**: 建立定期的数据分析机制

## 注意事项：
- 这是基于{analysis_type}的初步分析
- 建议结合具体业务上下文进行解读
- 定期更新数据分析以反映最新情况

*注：这是模拟分析结果，实际使用时请配置真实的 AI API 密钥。*
"""
        return mock_response
    
    def _get_fallback_response(self, question: str) -> str:
        """Get fallback response when AI analysis fails"""
        provider_map = {
            'openai': 'GLM-4.5 (BigModel.cn)',
            'mock': 'Mock Mode'
        }
        
        return f"""
抱歉，AI 分析暂时无法完成。对于您的业务问题"{question}"，建议您：

1. 直接查看 Superset 仪表板获取详细数据
2. 联系技术支持检查 AI 服务配置
3. 稍后重试分析

当前使用的 AI 提供商: {provider_map.get(self.ai_provider, self.ai_provider)}
请检查 API 密钥配置和网络连接。
"""
    
    def analyze_text_only(self, question: str, dashboard_titles: List[str]) -> str:
        """Analyze business question using text-only AI"""
        
        try:
            # Format dashboard titles
            formatted_titles = chr(10).join([f"- {title}" for title in dashboard_titles])
            
            # Create the prompt
            prompt = f"""你是一个专业的商业数据分析师。虽然无法直接看到数据，但基于看板标题和常见的业务分析模式，请提供有价值的业务建议。

请用中文回答，保持专业但易懂的语气。

业务问题：{question}

可用的看板（但无法直接看到数据）：
{formatted_titles}

虽然无法直接看到数据，但请基于这些看板标题和你的专业知识：
1. 分析这个问题可能需要哪些类型的数据
2. 提供一般性的业务分析框架
3. 建议应该关注哪些关键指标
4. 给出基于常见业务模式的建议"""
            
            if self.ai_provider == 'openai':
                return self._analyze_text_with_glm45(prompt)
            else:
                return self._fallback_text_analysis(question, dashboard_titles)
            
        except Exception as e:
            logger.error(f"Text analysis error: {str(e)}")
            return self._fallback_text_analysis(question, dashboard_titles)
    
    def _analyze_text_with_glm45(self, prompt: str) -> str:
        """Analyze text using GLM-4.5 via OpenAI client"""
        try:
            response = self.client.chat.completions.create(
                model='glm-4-plus',  # Use text model for text-only analysis
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的商业数据分析师。请用中文回答，保持专业但易懂的语气。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"❌ GLM-4.5 text analysis failed: {e}")
            return f"GLM-4.5分析过程中出现错误：{str(e)}"
    
    def _fallback_text_analysis(self, question: str, dashboard_titles: List[str]) -> str:
        """Fallback method using direct API calls"""
        # For mock mode, return a simple template response
        return f"""
对于业务问题"{question}"，基于 {len(dashboard_titles)} 个可用看板的分析：

## 分析框架：
1. **数据需求分析**: 需要查看相关的业务指标数据
2. **趋势识别**: 分析时间序列数据和变化模式
3. **关联分析**: 找出不同指标间的相关关系
4. **建议制定**: 基于数据洞察提供行动建议

## 建议关注的关键指标：
- 核心业务指标（KPI）
- 趋势变化率
- 同环比分析
- 异常数据点

## 下一步行动：
- 查看具体看板数据
- 结合业务背景解读
- 制定数据驱动策略

*注：这是基于看板标题的通用分析建议，具体分析需要查看实际数据。*
"""
    
    def get_business_insights_template(self, question: str, dashboard_count: int) -> str:
        """Get a template response when AI is not available"""
        
        templates = {
            "销售": f"""
基于 {dashboard_count} 个看板的分析，关于销售趋势的分析结果：

📊 **主要发现：**
- 需要查看销售看板中的具体数据趋势
- 建议关注月度/季度销售增长率
- 分析不同产品线的表现差异

💡 **建议：**
1. 深入分析销售数据的时间序列趋势
2. 识别销售高峰和低谷的原因
3. 对比不同渠道的销售效果

⚠️ **注意：** 具体数值需要查看实际看板数据
""",
            
            "用户": f"""
基于 {dashboard_count} 个看板的分析，关于用户活跃度的分析结果：

👥 **用户行为分析：**
- 建议查看用户活跃度看板中的DAU/MAU指标
- 分析用户留存率和流失率趋势
- 关注用户参与度的变化

📈 **关键指标：**
- 日活跃用户数(DAU)
- 月活跃用户数(MAU) 
- 用户留存率
- 平均使用时长

🔍 **建议：** 需要结合具体数据制定用户增长策略
""",
            
            "财务": f"""
基于 {dashboard_count} 个看板的分析，关于财务分析的结果：

💰 **财务状况分析：**
- 建议查看财务看板中的收入、成本、利润数据
- 分析各项财务指标的趋势变化
- 关注预算执行情况和成本控制

📊 **重点关注：**
- 收入增长率
- 成本结构变化
- 利润率趋势
- 现金流状况

💡 **建议：** 需要基于具体财务数据制定优化策略
""",
            
            "default": f"""
基于 {dashboard_count} 个看板的分析，关于"{question}"的分析结果：

🔍 **分析框架：**
1. **数据收集：** 从相关看板中提取关键指标
2. **趋势分析：** 识别数据中的模式和变化
3. **关联分析：** 找出不同指标间的关联关系
4. **建议制定：** 基于数据洞察提出行动建议

📋 **下一步：**
- 需要查看具体看板数据以获得准确分析
- 建议关注与问题最相关的关键指标
- 结合业务背景进行深度解读

⚠️ **说明：** 具体分析结果需要基于实际看板数据
"""
        }
        
        # Determine which template to use based on question keywords
        question_lower = question.lower()
        
        if any(keyword in question_lower for keyword in ['销售', '收入', 'revenue', 'sales']):
            return templates["销售"]
        elif any(keyword in question_lower for keyword in ['用户', '活跃', 'user', 'active']):
            return templates["用户"]
        elif any(keyword in question_lower for keyword in ['财务', '成本', '利润', 'financial', 'cost']):
            return templates["财务"]
        else:
            return templates["default"]