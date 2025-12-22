"""
地址治理流水线 - 确定性端到端流程

使用 Agno SDK v2.3.20 的 Workflow API
"""
from textwrap import dedent
from agno.workflow import Workflow, Step
from agno.workflow.step import StepInput, StepOutput
from agno.db.sqlite import SqliteDb

from app.core import settings, get_logger
from app.assistants.parser import make_parser_agent
from app.assistants.normalizer import make_normalizer_agent
from app.assistants.standardizer import make_standardizer_agent
from app.assistants.spatializer import make_spatializer_agent
from app.assistants.verifier import make_verifier_agent

logger = get_logger(__name__)


def route_by_complexity(step_input: StepInput) -> StepOutput:
    """
    根据地址复杂度进行路由分流
    
    实现漏斗式分级路由：
    - L0 (40%): 标准格式，直接返回
    - L1 (30%): 轻度非标，简单处理
    - L2 (15%): 中度复杂，需要补全纠错
    - L3 (15%): 高度复杂，需要LLM+RAG
    """
    address = step_input.input
    
    # 简单的复杂度判断逻辑
    complexity = "simple"
    
    # 检查是否缺少行政区划
    if not any(kw in address for kw in ["省", "市", "区", "县"]):
        complexity = "medium"
    
    # 检查是否包含口语化表达
    if any(kw in address for kw in ["那个", "旁边", "附近", "对面", "亲"]):
        complexity = "complex"
    
    logger.info(f"地址复杂度评估: {complexity}")
    
    return StepOutput(
        content=address,
        step_name="complexity_router",
        additional_data={"complexity": complexity}
    )


def make_address_pipeline() -> Workflow:
    """
    创建地址治理流水线
    
    流程：预处理 → 分级路由 → 解析 → 标准化 → 空间化 → 校验
    
    Returns:
        配置好的地址治理Workflow实例
    """
    normalizer = make_normalizer_agent()
    parser = make_parser_agent()
    standardizer = make_standardizer_agent()
    spatializer = make_spatializer_agent()
    verifier = make_verifier_agent()
    
    return Workflow(
        name="地址治理流水线",
        id="address-governance-pipeline",
        description="端到端的中文地址治理处理流程",
        steps=[
            Step(name="预处理", agent=normalizer, description="清洗和规范化原始地址"),
            route_by_complexity,  # 路由函数
            Step(name="结构化解析", agent=parser, description="18级地址分词"),
            Step(name="标准化", agent=standardizer, description="匹配标准库、纠错补全"),
            Step(name="空间化", agent=spatializer, description="地理编码"),
            Step(name="校验", agent=verifier, description="三重幻觉抑制校验"),
        ],
        db=SqliteDb(db_file=settings.SQLITE_DB_FILE),
    )


if __name__ == "__main__":
    # 独立测试
    pipeline = make_address_pipeline()
    
    test_addresses = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "亲，帮我送到紫金港那个全家，就是东区那个",
    ]
    
    for addr in test_addresses:
        print(f"\n{'='*60}")
        print(f"处理地址: {addr}")
        pipeline.print_response(addr, stream=True)
