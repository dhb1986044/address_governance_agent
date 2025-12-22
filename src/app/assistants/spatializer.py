"""
地址空间化智能体 - 地址到坐标的转换

遵循 Agno SDK v2.3.20 的 Agent 创建规范
"""
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.geocode_tool import geocode_address, reverse_geocode

logger = get_logger(__name__)


SPATIALIZER_DESCRIPTION = """\
你是地址空间化专家，负责将文本地址转换为精确的地理坐标（经纬度）。
"""

SPATIALIZER_INSTRUCTIONS = [
    "调用geocode_address工具获取经纬度坐标",
    "评估编码精度等级（省级/市级/区级/街道/门牌）",
    "检查坐标范围是否在中国境内",
    "使用reverse_geocode进行逆向验证",
    "对比反向编码结果与原地址",
    "给出置信度和精度评估",
]


def make_spatializer_agent() -> Agent:
    """
    创建地址空间化智能体
    
    Returns:
        Agent: 配置好的空间化智能体
    """
    return Agent(
        name="地址空间化专家",
        id="address-spatializer",
        model=OpenAIChat(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址空间化智能体 - 地址到坐标转换",
        tools=[geocode_address, reverse_geocode],
        instructions=SPATIALIZER_INSTRUCTIONS,
        description=SPATIALIZER_DESCRIPTION,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
        add_datetime_to_context=True,
        markdown=True,
    )


def spatialize_address(address: str) -> dict:
    """
    将地址空间化（转换为坐标）
    
    Args:
        address: 标准化的地址
    
    Returns:
        dict: 空间化结果
    """
    logger.info(f"开始空间化地址: {address}")
    
    agent = make_spatializer_agent()
    
    prompt = f"请将以下地址转换为地理坐标：{address}"
    
    response = agent.run(prompt)
    
    return {
        "address": address,
        "result": response.content
    }


if __name__ == "__main__":
    """测试地址空间化智能体"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号",
        "北京市海淀区中关村大街1号",
        "上海市浦东新区张杨路501号",
    ]
    
    print("=" * 80)
    print("测试地址空间化智能体")
    print("=" * 80)
    
    agent = make_spatializer_agent()
    
    for addr in test_cases:
        print(f"\n地址: {addr}")
        print("-" * 80)
        agent.print_response(f"请将以下地址转换为地理坐标：{addr}", stream=True)
