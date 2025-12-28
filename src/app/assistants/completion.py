"""
地址补全智能体 - 基于LanceDB RAG与智谱LLM
Refactored to integrate LanceDB and Structured Outputs (Agno Best Practices)
"""
from typing import Dict, Any, Optional
from agno.agent import Agent
from agno.models.openai.like import OpenAILike 
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.segment_tool import segment_address_logic
from app.resources.knowledge.lance_knowledge import lance_knowledge
from app.models.address_schema import FengtuAddress, OutputContainer

logger = get_logger(__name__)

SCHEMA_DESC = FengtuAddress.get_field_descriptions()

COMPLETION_DESCRIPTION = f"""\
你是中文地址补全专家。
你的任务是结合RAG检索到的上下文知识，将缺失信息的地址补全为完整的丰图13级标准地址。

目标字段结构：
{SCHEMA_DESC}
"""

COMPLETION_INSTRUCTIONS = [
    "分析输入地址和提供的上下文信息(RAG Search Results)",
    "如果检索结果中包含与输入地址高度匹配的AOI或村庄，直接复用其行政区划信息",
    "特别是省、市、区县、乡镇四级行政区划，必须优先使用检索结果",
    "补全 AOI 名称和详细地址",
    "输出 OutputContainer 格式的 JSON",
    "在 reasoning 字段中说明你参考了哪条检索结果"
]

def make_completion_agent() -> Agent:
    return Agent(
        name="地址补全专家",
        id="address-completion",
        model=OpenAILike(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址补全智能体 - RAG增强",
        instructions=COMPLETION_INSTRUCTIONS,
        description=COMPLETION_DESCRIPTION,
        # Structured Output using v2.0 API (output_schema instead of response_model)
        # output_schema=OutputContainer, # Removed for manual parsing
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
    )

def _extract_city_from_segments(segment_result: Dict) -> Optional[str]:
    """从分词结果中提取地级市"""
    segments = segment_result.get("segments", [])
    if not segments:
        return None
        
    for seg in segments:
        if seg.get("level") in ["L2", "City"] or seg.get("name") == "地级市":
            return seg.get("value")
    return None

def complete_address(address: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    RAG 补全流程
    """
    try:
        logger.info(f"开始补全地址: {address}")
        
        # 1. 预处理：分词获取 City (用于 Filter)
        segment_result = segment_address_logic(address)
        city = _extract_city_from_segments(segment_result)
        logger.info(f"提取到的城市过滤条件: {city}")
        
        # 2. 检索 LanceDB
        search_results = lance_knowledge.search(address, city_filter=city, limit=5)
        
        # 3. 构建 Context 字符串
        rag_context_str = "检索到的参考地址信息:\n"
        if search_results["aoi"]:
            rag_context_str += "--- AOI (兴趣面) ---\n"
            for item in search_results["aoi"]:
                rag_context_str += f"- [{item.metadata['province']}/{item.metadata['city']}/{item.metadata['county']}/{item.metadata['town']}] 名称:{item.metadata['name']} (Score: {item.score})\n"
        
        if search_results["village"]:
            rag_context_str += "--- Village (村庄) ---\n"
            for item in search_results["village"]:
                rag_context_str += f"- [{item.metadata['province']}/{item.metadata['city']}/{item.metadata['county']}/{item.metadata['town']}] 名称:{item.metadata['name']} (Score: {item.score})\n"
        
        # 4. 调用 Agent
        agent = make_completion_agent()
        prompt = f"""
        待补全地址: {address}
        
        {rag_context_str}
        
        辅助上下文: {context if context else '无'}
        """
        
        response = agent.run(prompt)
        
        # In v2.0 with output_schema, response.content SHOULD be the Pydantic object
        # But if model returns text (Zhipu might not support strict structured output via OpenAI adapter fully),
        # output might be a string.
        content = response.content
        if isinstance(content, str):
            logger.warning("Received string content instead of Pydantic model, attempting manual parse.")
            import json
            import re
            # Try to extract JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content_str = json_match.group(1)
            else:
                content_str = content.replace("```json", "").replace("```", "")
            
            data_dict = json.loads(content_str)
            container = OutputContainer.model_validate(data_dict)
            result_data = container.model_dump()
        else:
            result_data = content.model_dump()
        
        return {
            "original_address": address,
            "status": "success",
            "data": result_data,
            "rag_hits": {
                "aoi": len(search_results["aoi"]),
                "village": len(search_results["village"])
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to complete address '{address}': {e}", exc_info=True)
        return {
            "original_address": address,
            "status": "error",
            "error_message": str(e)
        }
