"""
文本清洗工具 - 地址预处理
"""
import re
from typing import Dict, Any
from agno.tools import tool
from app.core import get_logger

logger = get_logger(__name__)


@tool(
    name="clean_address_text",
    description="""清洗和预处理地址文本。
    
    处理步骤包括：
    1. 移除多余空白字符
    2. 统一全角/半角字符
    3. 移除特殊符号
    4. 标准化数字格式
    5. 移除重复词
    
    返回清洗后的地址文本，提高后续处理的准确性。
    """
)
def clean_address_text(address: str) -> Dict[str, Any]:
    """
    清洗地址文本
    
    Args:
        address: 原始地址文本
    
    Returns:
        Dict: 包含清洗后的地址和清洗步骤
    """
    logger.info(f"清洗地址文本: {address}")
    
    try:
        original = address
        steps = []
        
        # 1. 移除首尾空白
        address = address.strip()
        if address != original:
            steps.append("移除首尾空白")
        
        # 2. 统一全角到半角（数字和字母）
        address = address.replace('０', '0').replace('１', '1').replace('２', '2')
        address = address.replace('３', '3').replace('４', '4').replace('５', '5')
        address = address.replace('６', '6').replace('７', '7').replace('８', '8')
        address = address.replace('９', '9')
        
        # 3. 移除多余空白（保留单个空格）
        cleaned = re.sub(r'\s+', ' ', address)
        if cleaned != address:
            steps.append("移除多余空白")
            address = cleaned
        
        # 4. 移除常见无用词
        useless_words = ['亲', '您好', '麻烦', '谢谢', '请', '帮忙']
        for word in useless_words:
            if word in address:
                address = address.replace(word, '')
                steps.append(f"移除无用词: {word}")
        
        # 5. 标准化标点符号
        address = address.replace('，', ',').replace('。', '.')
        address = address.replace('（', '(').replace('）', ')')
        
        # 6. 移除首尾标点
        address = address.strip(',.;:!?，。；：！？')
        
        return {
            "original": original,
            "cleaned": address,
            "steps": steps,
            "changed": original != address
        }
    except Exception as e:
        logger.error(f"文本清洗失败: {e}")
        return {
            "original": address,
            "cleaned": address,
            "steps": [],
            "changed": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """测试文本清洗工具"""
    test_cases = [
        "  浙江省杭州市余杭区   文一西路969号  ",
        "亲，帮我送到文一西路９６９号，谢谢",
        "杭州市，，余杭区。。文一西路",
        "您好（请送到）阿里巴巴西溪园区！",
    ]
    
    print("=" * 80)
    print("测试文本清洗工具")
    print("=" * 80)
    
    for addr in test_cases:
        print(f"\n原始: {repr(addr)}")
        result = clean_address_text(addr)
        print(f"清洗: {repr(result['cleaned'])}")
        if result['steps']:
            print(f"步骤: {', '.join(result['steps'])}")
        print("-" * 80)
