"""
地址相似度计算工具
同时考虑文本相似度和空间相似度
"""
from typing import Dict, Any
from agno.tools import tool
from app.core import FengtuClient, get_logger

logger = get_logger(__name__)


@tool(
    name="calculate_address_similarity",
    description="""计算两个地址之间的相似度。
    
    采用空间-语义协同方法，综合考虑：
    1. 文本相似度：基于编辑距离和语义向量
    2. 空间相似度：基于地理坐标距离
    
    返回综合相似度得分(0-1)，以及文本和空间两个维度的分项得分。
    用于地址去重、合并和匹配。
    """
)
def calculate_address_similarity(address1: str, address2: str) -> Dict[str, Any]:
    """
    计算两个地址的相似度
    
    Args:
        address1: 第一个地址
        address2: 第二个地址
    
    Returns:
        Dict: 包含总体相似度、文本相似度、空间相似度
    """
    logger.info(f"计算地址相似度: {address1} <-> {address2}")
    
    try:
        client = FengtuClient()
        result = client.calculate_similarity(address1, address2)
        
        return {
            "address1": result.address1,
            "address2": result.address2,
            "similarity": result.similarity,
            "text_similarity": result.text_similarity,
            "spatial_similarity": result.spatial_similarity,
            "is_similar": result.similarity >= 0.85  # 阈值可配置
        }
    except Exception as e:
        logger.error(f"相似度计算失败: {e}")
        return {
            "address1": address1,
            "address2": address2,
            "similarity": 0.0,
            "text_similarity": 0.0,
            "spatial_similarity": 0.0,
            "is_similar": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """测试地址相似度工具"""
    test_pairs = [
        ("浙江省杭州市余杭区文一西路969号", "杭州市余杭区文一西路969号", "省级省略"),
        ("文一西路969号", "文二西路969号", "近似地址"),
        ("阿里巴巴西溪园区", "阿里西溪园区", "别名"),
        ("文一西路969号5号楼", "文一西路969号6号楼", "楼栋不同"),
    ]
    
    print("=" * 80)
    print("测试地址相似度工具")
    print("=" * 80)
    
    for addr1, addr2, case_type in test_pairs:
        print(f"\n测试类型: {case_type}")
        print(f"地址1: {addr1}")
        print(f"地址2: {addr2}")
        result = calculate_address_similarity(addr1, addr2)
        print(f"综合相似度: {result['similarity']:.2f}")
        print(f"文本相似度: {result['text_similarity']:.2f}")
        print(f"空间相似度: {result['spatial_similarity']:.2f}")
        print(f"判定为相似: {result['is_similar']}")
        print("-" * 80)
