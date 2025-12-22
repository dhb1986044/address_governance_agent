"""
地址标准化智能体 - 综合纠错、补全、格式规范化

遵循 Agno SDK v2.3.20 的 Agent 创建规范
"""
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.standardize_tool import standardize_address
from app.resources.tools.segment_tool import segment_address

logger = get_logger(__name__)


STANDARDIZER_DESCRIPTION = """\
你是中文地址标准化专家，负责将各种非标准地址转换为符合GB/T 23705-2009标准的规范地址。
"""

STANDARDIZER_INSTRUCTIONS = [
    "调用standardize_address工具获取丰图AI标准化结果",
    "调用segment_address工具验证分词结果",
    "综合纠错、补全、格式规范化",
    "将地址转换为标准格式",
    "详细列出所有修改步骤",
    "评估标准化质量和置信度",
]


def make_standardizer_agent() -> Agent:
    """
    创建地址标准化智能体
    
    Returns:
        Agent: 配置好的标准化智能体
    """
    return Agent(
        name="地址标准化专家",
        id="address-standardizer",
        model=OpenAIChat(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址标准化智能体 - 综合纠错、补全、格式规范化",
        tools=[standardize_address, segment_address],
        instructions=STANDARDIZER_INSTRUCTIONS,
        description=STANDARDIZER_DESCRIPTION,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
        add_datetime_to_context=True,
        markdown=True,
    )


def standardize(address: str) -> dict:
    """
    标准化地址
    
    Args:
        address: 待标准化的地址
    
    Returns:
        dict: 标准化结果
    """
    logger.info(f"开始标准化地址: {address}")
    
    agent = make_standardizer_agent()
    
    prompt = f"请将以下地址标准化为符合GB/T 23705-2009标准的规范地址：{address}"
    
    response = agent.run(prompt)
    
    return {
        "original": address,
        "result": response.content
    }


if __name__ == "__main__":
    """测试地址标准化智能体"""
    test_cases = [
        "杭州余杭文一西路969号",  # 缺失层级、缺失后缀
        "浙江省杭州市余航区五常街道文一西路969号",  # 错别字
        "阿里西溪5号楼501",  # POI别名、格式不规范
    ]
    
    print("=" * 80)
    print("测试地址标准化智能体")
    print("=" * 80)
    
    agent = make_standardizer_agent()
    
    for addr in test_cases:
        print(f"\n原始地址: {repr(addr)}")
        print("-" * 80)
        agent.print_response(f"请将以下地址标准化：{addr}", stream=True)
