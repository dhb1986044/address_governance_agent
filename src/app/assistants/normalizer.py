"""
地址规范化智能体 - 文本预处理和格式规范
核心能力：清洗和规范化地址文本格式
"""
from agno import Agent, RunResponse
from app.core import settings, get_logger
from app.resources.tools.text_cleaner import clean_address_text

logger = get_logger(__name__)


NORMALIZER_SYSTEM_PROMPT = """你是地址规范化专家，负责清洗和规范化地址文本格式。

## 核心任务
对原始地址文本进行预处理，为后续的解析、纠错、补全做准备。

## 规范化处理

### 1. 文本清洗
- 移除多余空白字符
- 统一全角/半角（数字、字母、标点）
- 移除无用词（亲、您好、麻烦、谢谢等）
- 移除特殊符号

### 2. 格式规范
- 标准化数字格式
- 统一标点符号
- 规范化空格使用
- 移除重复词

### 3. 结构识别
- 识别地址的基本结构
- 区分行政区划、道路、门牌、楼栋等
- 识别POI和关键词

## 输出格式
```json
{
  "original": "原始地址",
  "normalized": "规范化后的地址",
  "changes": [
    {"type": "清洗", "description": "移除无用词"},
    {"type": "格式", "description": "统一全角数字"}
  ],
  "structure": {
    "has_province": true,
    "has_city": true,
    "has_district": true,
    "has_road": true,
    "has_number": true,
    "has_poi": false
  }
}
```

## 注意事项
- 不要删除有用信息（即使格式奇怪）
- 保留数字和关键词
- POI名称不要拆分
- 地址层级不要合并
"""


def make_normalizer_agent() -> Agent:
    """
    创建地址规范化智能体
    
    Returns:
        Agent: 配置好的规范化智能体
    """
    agent = Agent(
        name="AddressNormalizer",
        description="地址规范化智能体 - 文本预处理",
        model=f"openai/{settings.LLM_MODEL_ID}",
        instructions=NORMALIZER_SYSTEM_PROMPT,
        tools=[clean_address_text],
        markdown=False,
        show_tool_calls=True,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )
    return agent


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
    
    prompt = f"""请规范化以下地址的格式：

原始地址：{address}

要求：
1. 调用clean_address_text工具进行文本清洗
2. 分析地址的基本结构
3. 识别包含的层级（省市区街道路号楼室）
4. 识别POI和关键词
5. 给出规范化后的地址
6. 列出所有的处理步骤
"""
    
    response: RunResponse = agent.run(prompt)
    
    return {
        "original": address,
        "result": response.content
    }


if __name__ == "__main__":
    """测试地址规范化智能体"""
    test_cases = [
        "  亲，帮我送到  浙江省杭州市  余杭区  文一西路９６９号  谢谢！！",
        "您好，请送到：北京市，海淀区，中关村大街1号（科技大厦）",
        "杭州市余杭区文一西路969号阿里巴巴西溪园区5号楼501室",
        "麻烦送到紫金港校区东区那个全家便利店",
    ]
    
    print("=" * 80)
    print("测试地址规范化智能体")
    print("=" * 80)
    
    for addr in test_cases:
        print(f"\n原始地址: {repr(addr)}")
        print("-" * 80)
        
        result = normalize_address(addr)
        print(f"规范化结果:\n{result['result']}")
        print("=" * 80)
