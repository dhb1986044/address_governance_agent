"""
地址纠错智能体 - AI语义纠错

遵循 Agno SDK v2.3.20 的 Agent 创建规范
"""
from typing import Dict, Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.standardize_tool import standardize_address
from app.resources.knowledge.admin_division import admin_division

logger = get_logger(__name__)


CORRECTION_DESCRIPTION = """\
你是中文地址纠错专家，擅长识别和纠正地址中的错别字、笔误、OCR错误。
"""

CORRECTION_INSTRUCTIONS = [
    "识别地址中的错别字、同音字错误、形近字错误",
    "校验行政区划是否在标准字典中",
    "检查层级关系是否正确",
    "使用编辑距离和拼音相似度匹配标准地名",
    "调用丰图标准化服务辅助纠错",
    "给出纠错后的地址和详细依据",
]


def make_correction_agent() -> Agent:
    """
    创建地址纠错智能体
    
    Returns:
        Agent: 配置好的纠错智能体
    """
    return Agent(
        name="地址纠错专家",
        id="address-correction",
        model=OpenAIChat(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址纠错智能体 - AI语义纠错",
        tools=[standardize_address],
        instructions=CORRECTION_INSTRUCTIONS,
        description=CORRECTION_DESCRIPTION,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
        add_datetime_to_context=True,
        markdown=True,
    )


def correct_address(address: str) -> dict:
    """
    纠正地址错误
    
    Args:
        address: 待纠错的地址
    
    Returns:
        dict: 纠错结果
    """
    logger.info(f"开始纠错地址: {address}")
    
    agent = make_correction_agent()
    
    # 调用丰图标准化服务获取参考
    std_result = standardize_address(address)
    
    prompt = f"请检查并纠正以下地址中的错误：{address}"
    
    response = agent.run(prompt)
    
    return {
        "original": address,
        "result": response.content,
        "standardized_ref": std_result
    }


if __name__ == "__main__":
    """测试地址纠错智能体"""
    test_cases = [
        "杭州市余航区五常街道文一西路969号",  # 余杭→余航
        "北京市海定区中关村大街1号",  # 海淀→海定
        "浙江省抗州市西湖区",  # 杭州→抗州
    ]
    
    print("=" * 80)
    print("测试地址纠错智能体")
    print("=" * 80)
    
    agent = make_correction_agent()
    
    for addr in test_cases:
        print(f"\n原始地址（含错误）: {addr}")
        print("-" * 80)
        agent.print_response(f"请检查并纠正以下地址中的错误：{addr}", stream=True)
