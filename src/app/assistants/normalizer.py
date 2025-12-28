"""
地址规范化智能体 - 文本预处理和格式规范

遵循 Agno SDK v2.3.20 的 Agent 创建规范
"""
from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.resources.tools.text_cleaner import clean_address_text

logger = get_logger(__name__)


NORMALIZER_DESCRIPTION = """\
你是地址规范化专家，负责清洗和规范化地址文本格式。
"""

NORMALIZER_INSTRUCTIONS = [
    "调用clean_address_text工具进行文本清洗",
    "移除多余空白、无用词和特殊符号",
    "统一全角/半角字符和标点符号",
    "分析地址的基本结构和层级",
    "识别POI和关键词",
    "给出规范化后的地址",
]


from typing import Optional
from pydantic import BaseModel, Field

class NormalizationResult(BaseModel):
    """地址规范化结果"""
    normalized_text: str = Field(..., description="规范化后的标准地址文本")
    structure_analysis: str = Field(..., description="对地址结构和层级的分析")
    poi_detected: Optional[str] = Field(None, description="识别出的POI（兴趣点）或关键地标")
    corrections_made: list[str] = Field(default_factory=list, description="执行的具体纠错或清洗操作列表")


def make_normalizer_agent() -> Agent:
    """
    创建地址规范化智能体
    
    Returns:
        Agent: 配置好的规范化智能体
    """
    return Agent(
        name="地址规范化专家",
        id="address-normalizer",
        model=OpenAILike(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        role="地址规范化智能体 - 文本预处理",
        tools=[clean_address_text],
        instructions=NORMALIZER_INSTRUCTIONS,
        description=NORMALIZER_DESCRIPTION,
        output_schema=NormalizationResult,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        add_history_to_context=True,
        add_datetime_to_context=True,
        markdown=True,
    )


def normalize_address(address: str) -> dict:
    """
    规范化地址
    
    Args:
        address: 原始地址
    
    Returns:
        dict: 规范化结果
    """
    logger.info(f"开始规范化地址: {address}")
    
    agent = make_normalizer_agent()
    
    prompt = f"请规范化以下地址的格式：{address}"
    
    response = agent.run(prompt)
    
    # response.content 已经是 NormalizationResult 对象
    result: NormalizationResult = response.content
    
    return {
        "original": address,
        "result": result.normalized_text,
        "details": result.model_dump()
    }


if __name__ == "__main__":
    """测试地址规范化智能体"""
    test_cases = [
        "  亲，帮我送到  浙江省杭州市  余杭区  文一西路９６９号  谢谢！！",
        "您好，请送到：北京市，海淀区，中关村大街1号（科技大厦）",
        "杭州市余杭区文一西路969号阿里巴巴西溪园区5号楼501室",
    ]
    
    print("=" * 80)
    print("测试地址规范化智能体 (Structured Output)")
    print("=" * 80)
    
    agent = make_normalizer_agent()
    
    for addr in test_cases:
        print(f"\n原始地址: {repr(addr)}")
        print("-" * 80)
        response = agent.run(f"请规范化以下地址的格式：{addr}")
        result: NormalizationResult = response.content
        
        print(f"规范化文本: {result.normalized_text}")
        print(f"结构分析:   {result.structure_analysis}")
        print(f"识别POI:    {result.poi_detected}")
        print(f"纠错操作:   {result.corrections_made}")
