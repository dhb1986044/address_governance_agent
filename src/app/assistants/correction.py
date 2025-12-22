"""
地址纠错智能体 - AI语义纠错
核心能力：识别并纠正地址中的错别字、笔误、OCR错误
"""
from agno.agent import Agent
from typing import List, Dict, Any
from app.core import settings, get_logger
from app.resources.tools.standardize_tool import standardize_address
from app.resources.knowledge.admin_division import admin_division

logger = get_logger(__name__)


CORRECTION_SYSTEM_PROMPT = """你是中文地址纠错专家，擅长识别和纠正地址中的各类错误。

## 错误类型

### 1. 错别字
- 同音字错误：余杭区 → 余航区、鱼巷区
- 形近字错误：文一西路 → 文―西路
- 笔误：杭州市 → 抗州市

### 2. OCR识别错误
- 数字误识：0/O、1/I、5/S、8/B
- 标点符号：号/弓、室/宝
- 中英混淆：区/Area、号/No

### 3. 拼音输入错误
- 余杭 → yuhang → 鱼航
- 文一 → wenyi → 文艺

### 4. 行政区划历史名称
- 已更名的区县（如杭州下城区→拱墅区）
- 历史地名需要映射到当前标准名称

## 纠错策略

### 1. 行政区划校验
- 检查省市区街道是否在标准字典中
- 校验层级关系是否正确
- 识别已废弃的历史地名

### 2. 语义相似度匹配
- 计算与标准地名的编辑距离
- 使用拼音相似度
- 考虑常见误写模式

### 3. 上下文一致性
- 检查地址各层级是否匹配
- 例如："北京市杭州市"明显矛盾

### 4. 调用标准化API
- 使用丰图标准化服务
- AI语义纠错精度99.8%+

## 输出格式
```json
{
  "original_address": "原始地址（含错误）",
  "corrected_address": "纠错后的地址",
  "errors": [
    {
      "position": "L3",
      "error_text": "余航区",
      "correct_text": "余杭区",
      "error_type": "同音字错误",
      "confidence": 0.98
    }
  ],
  "confidence": 0.96,
  "need_manual_review": false
}
```

## 注意事项
- 不要过度纠错，置信度<0.85的疑似错误不要修改
- 保留用户输入的门牌号、房间号（即使看起来奇怪）
- POI别名不算错误（如"阿里西溪"vs"阿里巴巴西溪园区"）
- 必须说明每个纠错的依据
"""


def make_correction_agent() -> Agent:
    """
    创建地址纠错智能体
    
    Returns:
        Agent: 配置好的纠错智能体
    """
    agent = Agent(
        name="AddressCorrection",
        description="地址纠错智能体 - AI语义纠错",
        model=f"openai:{settings.LLM_MODEL_ID}",
        instructions=CORRECTION_SYSTEM_PROMPT,
        tools=[standardize_address],
        markdown=False,
    )
    return agent


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
    
    prompt = f"""请检查并纠正以下地址中的错误：

原始地址：{address}

丰图标准化服务结果：
- 标准化地址：{std_result['standardized']}
- 置信度：{std_result['confidence']:.2f}
- 纠错列表：{std_result['corrections']}

要求：
1. 识别地址中的错别字、笔误、OCR错误
2. 校验行政区划是否正确（省市区街道）
3. 检查层级关系是否一致
4. 给出纠错后的标准地址
5. 详细说明每个错误的类型和纠正依据
6. 评估纠错的置信度
"""
    
    response: Any = agent.run(prompt)
    
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
        "上海市浦东新区张杨路5O1号",  # 50→5O
    ]
    
    print("=" * 80)
    print("测试地址纠错智能体")
    print("=" * 80)
    
    for addr in test_cases:
        print(f"\n原始地址（含错误）: {addr}")
        print("-" * 80)
        
        result = correct_address(addr)
        print(f"纠错结果:\n{result['result']}")
        print(f"\n标准化服务参考:")
        print(f"  标准化: {result['standardized_ref']['standardized']}")
        print(f"  置信度: {result['standardized_ref']['confidence']:.2f}")
        print("=" * 80)
