"""
18级地址分词工具 - 调用丰图科技分词API

层级定义（遵循GB/T 23705-2009扩展）：
L1: 省/直辖市    L7: 户室/层      L13: 方位词
L2: 地级市       L8: 辅助路       L14: 距离描述
L3: 区/县        L9: 标志物       L15: 附加描述
L4: 乡镇/街道    L10: 子POI       L16: 备注信息
L5: 路/村/社区   L11: 出入口      L17: 联系信息
L6: 门牌/楼栋    L12: 内部位置    L18: 其他
AOI: 兴趣面（跨层级实体）
"""
from typing import Dict, Any
from agno.tools import tool
from app.core import FengtuClient, get_logger, settings

logger = get_logger(__name__)


def segment_address_logic(raw_address: str) -> Dict[str, Any]:
    """
    18级分词逻辑 (Internal)
    """
    logger.info(f"18级分词工具: {raw_address}")
    
    # Mock logic if API Key is missing
    if not settings.FENGTU_API_KEY:
        logger.warning("未配置 FENGTU_API_KEY, 使用模拟(Mock)数据")
        return {
            "raw_address": raw_address,
            "segments": [
                 {"level": "L1", "name": "省/直辖市", "value": "河北省", "confidence": 1.0},
                 {"level": "L2", "name": "地级市", "value": "保定市", "confidence": 1.0},
                 {"level": "L3", "name": "区/县", "value": "满城区", "confidence": 0.9}
                 # Simple partial mock for testing
            ],
            "missing_levels": ["L4", "L6"],
            "confidence": 0.8,
            "need_completion": True,
            "note": "MOCKED USER DATA"
        }

    try:
        client = FengtuClient()
        result = client.segment_address(raw_address)
        
        # 转换为字典格式
        return {
            "raw_address": result.raw_address,
            "segments": [
                {
                    "level": seg.level,
                    "name": seg.name,
                    "value": seg.value,
                    "confidence": seg.confidence
                }
                for seg in result.segments
            ],
            "missing_levels": result.missing_levels,
            "aoi_detected": result.aoi_detected,
            "confidence": result.confidence,
            "need_completion": result.need_completion
        }
    except Exception as e:
        logger.error(f"18级分词失败: {e}")
        return {
            "raw_address": raw_address,
            "segments": [],
            "missing_levels": [],
            "confidence": 0.0,
            "need_completion": False,
            "error": str(e)
        }

@tool(
    name="fengtu_segment_address",
    description="""使用丰图18级分词服务解析中文地址。
    
    该工具将任意格式的中文地址解析为遵循GB/T 23705-2009标准的18级结构：
    - L1-L4: 行政区划（省/市/区/街道）
    - L5-L7: 基础定位（路/门牌/房间）
    - L8-L12: 精细定位（辅助路/标志物/子POI/出入口/内部位置）
    - L13-L18: 补充信息（方位/距离/附加描述/备注/联系信息/其他）
    - AOI: 兴趣面实体（如小区、园区）
    
    返回结构化的分词结果，包括各层级值、置信度、缺失层级等信息。
    """
)
def segment_address(raw_address: str) -> Dict[str, Any]:
    """
    调用丰图18级分词API解析地址
    """
    return segment_address_logic(raw_address)


if __name__ == "__main__":
    """测试18级分词工具"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "杭州市余航区五常街道",
        "阿里西溪园区B区",
    ]
    
    print("=" * 80)
    print("测试18级地址分词工具")
    print("=" * 80)
    
    for addr in test_cases:
        print(f"\n原始地址: {addr}")
        result = segment_address(addr)
        print(f"置信度: {result['confidence']:.2f}")
        print(f"分词结果({len(result['segments'])}个层级):")
        for seg in result['segments']:
            print(f"  [{seg['level']}] {seg['name']}: {seg['value']}")
        if result['missing_levels']:
            print(f"缺失层级: {', '.join(result['missing_levels'])}")
        print("-" * 80)
