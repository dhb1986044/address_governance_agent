"""
地址治理团队 - 基于HMAS架构的多智能体协作

使用 Agno SDK v2.3.20 的 Team API
"""
from textwrap import dedent
from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.assistants.parser import make_parser_agent
from app.assistants.normalizer import make_normalizer_agent
from app.assistants.completion import make_completion_agent
from app.assistants.correction import make_correction_agent
from app.assistants.standardizer import make_standardizer_agent
from app.assistants.spatializer import make_spatializer_agent
from app.assistants.verifier import make_verifier_agent

logger = get_logger(__name__)


TEAM_DESCRIPTION = dedent("""\
    你是地址治理团队的协调者（Orchestrator）。你的职责是：
    1. 分析用户输入的地址，识别其复杂度和治理需求
    2. 根据地址情况，智能分派任务给合适的团队成员
    3. 聚合各成员的处理结果，输出最终的标准化地址
""")

TEAM_INSTRUCTIONS = [
    "首先判断地址的复杂度：简单(标准格式)/中等(有缺失或错别字)/复杂(口语化或非标描述)",
    "简单地址：直接调用Parser解析",
    "中等地址：Parser解析 → Completion补全 → Correction纠错",
    "复杂地址：Parser解析 → Completion补全 → Correction纠错 → Standardizer标准化",
    "所有结果最后都需要经过Verifier进行三重校验",
    "如果需要空间坐标，调用Spatializer进行地理编码",
    "输出完整的治理结果JSON，包含各阶段处理信息",
]


def make_address_governance_team() -> Team:
    """
    创建地址治理团队
    
    实现HMAS分层多智能体架构，协调各专家智能体完成地址治理任务
    
    Returns:
        配置好的地址治理Team实例
    """
    # 创建团队成员
    parser = make_parser_agent()
    normalizer = make_normalizer_agent()
    completion = make_completion_agent()
    correction = make_correction_agent()
    standardizer = make_standardizer_agent()
    spatializer = make_spatializer_agent()
    verifier = make_verifier_agent()
    
    return Team(
        name="地址治理团队",
        id="address-governance-team",
        model=OpenAIChat(
            id=settings.LLM_MODEL_ID,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ),
        members=[parser, normalizer, completion, correction, standardizer, spatializer, verifier],
        description=TEAM_DESCRIPTION,
        instructions=TEAM_INSTRUCTIONS,
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
        show_members_responses=True,
        add_history_to_context=True,
        num_history_runs=3,
        markdown=True,
        retries=3,
        delay_between_retries=1,
        exponential_backoff=True,
    )


if __name__ == "__main__":
    # 独立测试
    team = make_address_governance_team()
    
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "亲，帮我送到紫金港那个全家，就是东区那个",
    ]
    
    for addr in test_cases:
        print(f"\n{'='*60}")
        print(f"治理地址: {addr}")
        team.print_response(f"请完成以下地址的全流程治理：{addr}", stream=True)
