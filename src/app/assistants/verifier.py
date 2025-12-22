"""
地址校验智能体 - 三重幻觉抑制机制

遵循 Agno SDK v2.3.20 的 Agent 创建规范
"""
from typing import Dict, Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.geocode_tool import geocode_address
from app.resources.knowledge.admin_division import admin_division

logger = get_logger(__name__)


VERIFIER_DESCRIPTION = """\
你是地址校验专家，负责验证地址治理结果的真实性和准确性，防止LLM幻觉。
"""

VERIFIER_INSTRUCTIONS = [
    "执行三重校验：存在性验证、一致性验证、几何约束验证",
    "检查省市区街道是否在标准字典中",
    "验证行政区划层级关系",
    "检查坐标是否在合理范围内",
    "评估每项校验的置信度",
    "给出综合判定：通过/需复核/拒绝",
]


def make_verifier_agent() -> Agent:
    """
    创建地址校验智能体
    
    Returns:
        Agent: 配置好的校验智能体
    """
    return Agent(
        name="地址校验专家",
        id="address-verifier",
        model=OpenAIChat(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址校验智能体 - 三重幻觉抑制机制",
        tools=[geocode_address],
        instructions=VERIFIER_INSTRUCTIONS,
        description=VERIFIER_DESCRIPTION,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
        add_datetime_to_context=True,
        markdown=True,
    )


def verify_address(
    address: str,
    coordinates: Dict[str, float] = None,
    segment_info: Dict[str, Any] = None
) -> dict:
    """
    校验地址
    
    Args:
        address: 待校验的地址
        coordinates: 地理坐标（可选）
        segment_info: 分词信息（可选）
    
    Returns:
        dict: 校验结果
    """
    logger.info(f"开始校验地址: {address}")
    
    agent = make_verifier_agent()
    
    # 如果没有提供坐标，先进行地理编码
    if not coordinates:
        from app.resources.tools.geocode_tool import geocode_address as geocode_func
        geo_result = geocode_func(address)
        if geo_result.get('longitude') and geo_result.get('latitude'):
            coordinates = {
                "longitude": geo_result['longitude'],
                "latitude": geo_result['latitude']
            }
    
    coord_info = f" 坐标: {coordinates}" if coordinates else ""
    
    prompt = f"请对以下地址进行三重校验：{address}{coord_info}"
    
    response = agent.run(prompt)
    
    return {
        "address": address,
        "result": response.content,
        "coordinates": coordinates
    }


if __name__ == "__main__":
    """测试地址校验智能体"""
    test_cases = [
        {
            "address": "浙江省杭州市余杭区五常街道文一西路969号",
            "coordinates": {"longitude": 120.023, "latitude": 30.276},
            "desc": "标准地址+正确坐标"
        },
        {
            "address": "浙江省杭州市不存在区文一西路969号",
            "coordinates": None,
            "desc": "存在性错误（虚构区名）"
        },
        {
            "address": "北京市杭州市余杭区",
            "coordinates": None,
            "desc": "一致性错误（层级矛盾）"
        },
    ]
    
    print("=" * 80)
    print("测试地址校验智能体")
    print("=" * 80)
    
    agent = make_verifier_agent()
    
    for case in test_cases:
        print(f"\n测试: {case['desc']}")
        print(f"地址: {case['address']}")
        if case['coordinates']:
            print(f"坐标: {case['coordinates']}")
        print("-" * 80)
        
        coord_str = f" 坐标: {case['coordinates']}" if case['coordinates'] else ""
        agent.print_response(f"请对以下地址进行三重校验：{case['address']}{coord_str}", stream=True)
