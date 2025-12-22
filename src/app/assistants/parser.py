"""
地址解析智能体 - 使用丰图18级分词进行结构化解析

遵循 Agno SDK v2.3.20 的 Agent 创建规范
"""
from typing import Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.segment_tool import segment_address
from app.resources.tools.text_cleaner import clean_address_text

logger = get_logger(__name__)


PARSER_DESCRIPTION = """\
你是丰图科技的中文地址解析专家，精通GB/T 23705-2009标准和丰图18级地址分词体系。
你的任务是将任意格式的中文地址解析为标准的18级结构。
"""

PARSER_INSTRUCTIONS = [
    "调用丰图18级分词工具获取地址解析结果",
    "验证分词结果的层级完整性和一致性",
    "识别并标注缺失的层级",
    "输出结构化的JSON格式结果",
    "如果地址存在歧义，列出所有可能的解析方案",
]


def make_parser_agent() -> Agent:
    """
    创建地址解析智能体
    
    使用工厂函数模式，允许在测试时轻松替换配置
    
    Returns:
        Agent: 配置好的解析智能体
    """
    return Agent(
        name="地址解析专家",
        id="address-parser",
        model=OpenAIChat(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址解析智能体 - 使用丰图18级分词进行结构化解析",
        tools=[segment_address, clean_address_text],
        instructions=PARSER_INSTRUCTIONS,
        description=PARSER_DESCRIPTION,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
        add_datetime_to_context=True,
        markdown=True,
    )


def parse_address(address: str) -> dict:
    """
    解析地址的便捷函数
    
    Args:
        address: 待解析的地址
    
    Returns:
        dict: 解析结果
    """
    agent = make_parser_agent()
    
    prompt = f"请解析以下地址：{address}"
    
    response = agent.run(prompt)
    return {
        "address": address,
        "result": response.content,
        "metrics": {
            "model": response.model if hasattr(response, 'model') else settings.LLM_MODEL_ID,
            "response_time": response.response_timer.elapsed if hasattr(response, 'response_timer') and response.response_timer else 0
        }
    }


if __name__ == "__main__":
    """测试地址解析智能体"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "阿里西溪园区B区",
    ]
    
    print("=" * 80)
    print("测试地址解析智能体")
    print("=" * 80)
    
    agent = make_parser_agent()
    
    for i, addr in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}: {addr}")
        print("-" * 80)
        agent.print_response(f"请解析以下地址：{addr}", stream=True)
