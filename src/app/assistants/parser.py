"""
地址解析智能体 - 使用丰图13级模型进行结构化解析
Refactored to support Pydantic Structured Outputs (Agno Best Practices)
"""
from typing import Any, Dict
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.segment_tool import segment_address_logic
from app.resources.tools.text_cleaner import clean_address_text_logic
from app.models.address_schema import FengtuAddress, OutputContainer

logger = get_logger(__name__)

# 获取Schema描述用于System Prompt
SCHEMA_DESC = FengtuAddress.get_field_descriptions()

PARSER_DESCRIPTION = f"""\
你是丰图科技的中文地址解析专家，精通GB/T 23705-2009标准和丰图13级楼盘表地址模型。
你的任务是将任意格式的中文地址解析为标准的结构化数据。

你需要填充的标准字段如下：
{SCHEMA_DESC}
"""

PARSER_INSTRUCTIONS = [
    "你通过 Input 接收到了原始地址和预处理的分词结果(Segmentation Info)",
    "请基于分词结果和你的语义理解，提取标准化的13级地址要素",
    "你需要输出 OutputContainer 格式的结构化数据",
    "自信地判断置信度 (confidence)",
    "如果某个层级确实不存在，请设为 null，不要臆造",
    "简要说明解析的推理过程 (reasoning)",
    "IMPORTANT: Output ONLY valid JSON inside a json code block.",
    "Do not hallucinate tool calls."
]

def make_parser_agent() -> Agent:
    """
    创建地址解析智能体 (无Tools, 纯Prompt)
    """
    return Agent(
        name="地址解析专家",
        id="address-parser",
        model=OpenAILike(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址解析智能体 - 结构化解析",
        # tools=[], # No tools, manual orchestration
        instructions=PARSER_INSTRUCTIONS,
        description=PARSER_DESCRIPTION,
        # output_schema=OutputContainer, # Removed to handle raw parsing manually
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
    )

def parse_address(address: str) -> Dict[str, Any]:
    """
    执行地址解析 (Manual Orchestration)
    """
    try:
        # 1. Cleaning
        cleaned_result = clean_address_text_logic(address)
        cleaned_address = cleaned_result.get("cleaned", address)
        
        # 2. Segmentation (Python call)
        seg_result = segment_address_logic(cleaned_address)
        
        # 3. Construct Prompt with context
        prompt = f"""
请解析以下地址：
原始地址: {address}
清洗后地址: {cleaned_address}
分词结果: {seg_result}

请输出 OutputContainer JSON.
"""
        agent = make_parser_agent()
        
        # Run agent
        response = agent.run(prompt)
        
        # Pydantic model to dict
        content = response.content
        if isinstance(content, str):
            logger.warning("Received string content instead of Pydantic model in Parser, attempting manual parse.")
            import json
            import re
            # Match any code block (json, python, or none)
            json_match = re.search(r'```(?:\w+)?\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content_str = json_match.group(1)
            else:
                content_str = content.strip()
                if content_str.startswith("```"):
                     content_str = content_str.replace("```json", "").replace("```", "")
            
            data_dict = json.loads(content_str)
            
            # Handle possible root wrapping (Case Insensitive)
            for k in list(data_dict.keys()):
                if k.lower() == "outputcontainer":
                    data_dict = data_dict[k]
                    break
            
            # Handle flattened structure (model puts address fields at root)
            if "standard_address" not in data_dict and "province" in data_dict:
                # Reconstruct structure
                address_fields = {k: v for k, v in data_dict.items() if k in FengtuAddress.model_fields}
                meta_fields = {k: v for k, v in data_dict.items() if k not in FengtuAddress.model_fields}
                data_dict = {
                    "standard_address": address_fields,
                    "confidence": meta_fields.get("confidence", 0.0),
                    "reasoning": meta_fields.get("reasoning", "")
                }
            
            container = OutputContainer.model_validate(data_dict)
            result_data = container.model_dump()
        else:
            result_data = content.model_dump()

        return {
            "original_address": address,
            "status": "success",
            "data": result_data,
            "metrics": {
                 "model": settings.LLM_MODEL_ID,
            }
        }
    except Exception as e:
        import traceback
        with open("debug_error.log", "w") as f:
            f.write(traceback.format_exc())
            try:
                 if 'response' in locals():
                     f.write(f"\nDEBUG RAW RESPONSE CONTENT: {response.content}")
            except:
                pass
        
        logger.error(f"Failed to parse address '{address}': {e}", exc_info=True)
            
        return {
            "original_address": address,
            "status": "error",
            "error_message": str(e)
        }

if __name__ == "__main__":
    """测试地址解析智能体"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "保定悦佳纸业", # 对应 AOI
    ]
    
    print("=" * 80)
    print("测试地址解析智能体 (Refactored output_schema)")
    print("=" * 80)
    
    for addr in test_cases:
        print(f"\n测试案例: {addr}")
        print("-" * 40)
        res = parse_address(addr)
        import json
        print(json.dumps(res, ensure_ascii=False, indent=2))
