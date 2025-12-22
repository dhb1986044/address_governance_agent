"""
地址补全智能体 - 基于RAG的缺失层级补全

遵循 Agno SDK v2.3.20 的 Agent 创建规范
"""
from typing import Dict, Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.segment_tool import segment_address
from app.resources.knowledge.address_knowledge import address_knowledge
from app.resources.knowledge.admin_division import admin_division

logger = get_logger(__name__)


COMPLETION_DESCRIPTION = """\
你是中文地址补全专家，擅长基于RAG检索和上下文推理来补全缺失的地址层级。
"""

COMPLETION_INSTRUCTIONS = [
    "对于缺失部分层级的地址，通过RAG知识库检索相似地址",
    "基于已知的低层级信息推断高层级行政区划",
    "识别地址中的POI实体，从POI知识库获取标准地址",
    "补全缺失的关键层级（L1-L6优先）",
    "给出补全后的完整地址和推理依据",
    "如果有多个合理方案，都应该列出",
]


def make_completion_agent() -> Agent:
    """
    创建地址补全智能体
    
    Returns:
        Agent: 配置好的补全智能体
    """
    return Agent(
        name="地址补全专家",
        id="address-completion",
        model=OpenAIChat(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址补全智能体 - 基于RAG补全缺失层级",
        tools=[segment_address],
        instructions=COMPLETION_INSTRUCTIONS,
        description=COMPLETION_DESCRIPTION,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
        add_datetime_to_context=True,
        markdown=True,
    )


def complete_address(address: str, context: Dict[str, Any] = None) -> dict:
    """
    补全地址
    
    Args:
        address: 待补全的地址
        context: 补充上下文信息（可选）
    
    Returns:
        dict: 补全结果
    """
    logger.info(f"开始补全地址: {address}")
    
    # 1. 先进行18级分词，识别缺失层级
    segment_result = segment_address(address)
    
    # 2. RAG检索相似地址
    candidates = address_knowledge.hybrid_search(address, top_k=5)
    
    # 3. 构建提示词
    agent = make_completion_agent()
    
    context_info = f"\n上下文信息: {context}" if context else ""
    
    prompt = f"请补全以下地址的缺失层级：{address}{context_info}"
    
    response = agent.run(prompt)
    
    return {
        "original": address,
        "result": response.content,
        "candidates": candidates,
        "segment_info": segment_result
    }


if __name__ == "__main__":
    """测试地址补全智能体"""
    test_cases = [
        ("文一西路969号5号楼", None),
        ("阿里西溪园区", None),
        ("五常街道文一西路969号", None),
    ]
    
    print("=" * 80)
    print("测试地址补全智能体")
    print("=" * 80)
    
    agent = make_completion_agent()
    
    for addr, ctx in test_cases:
        print(f"\n原始地址: {addr}")
        if ctx:
            print(f"上下文: {ctx}")
        print("-" * 80)
        agent.print_response(f"请补全以下地址的缺失层级：{addr}", stream=True)
