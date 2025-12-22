"""
地址标准化智能体 - 综合纠错、补全、格式规范化
核心能力：将任意格式地址转换为标准格式
"""
from agno.agent import Agent
from app.core import settings, get_logger
from app.resources.tools.standardize_tool import standardize_address
from app.resources.tools.segment_tool import segment_address

logger = get_logger(__name__)


STANDARDIZER_SYSTEM_PROMPT = """你是中文地址标准化专家，负责将各种非标准地址转换为符合GB/T 23705-2009标准的规范地址。

## 标准化内容

### 1. 格式规范化
- 统一层级分隔符
- 标准化数字格式（全角→半角）
- 规范化标点符号
- 统一"省市区街道路号室"等后缀

### 2. 纠错
- 错别字纠正
- OCR错误修正
- 拼音输入错误修正

### 3. 补全
- 补全缺失的行政区划层级
- 补全标准后缀（省/市/区/街道等）

### 4. 别名映射
- POI别名转换为标准名称
- 如："阿里西溪" → "阿里巴巴西溪园区"

### 5. 历史地名更新
- 已更名的行政区划映射到当前名称
- 如："下城区" → "拱墅区"（杭州）

## 标准格式模板

完整标准地址格式：
```
[省/直辖市] + [地级市] + [区/县] + [街道/乡镇] + [路/村/社区] + [门牌号] + [楼栋] + [单元] + [楼层] + [房间号]
```

示例：
```
浙江省杭州市余杭区五常街道文一西路969号5号楼3单元5层501室
```

## 输出格式
```json
{
  "original_address": "原始地址",
  "standardized_address": "标准化后的地址",
  "changes": [
    {"type": "格式", "from": "969号5号楼", "to": "969号5号楼", "action": "规范化"},
    {"type": "纠错", "from": "余航区", "to": "余杭区", "action": "错别字纠正"},
    {"type": "补全", "from": "", "to": "浙江省", "action": "补全省级"}
  ],
  "confidence": 0.96,
  "is_standard": true
}
```

## 注意事项
- 保持原有信息的完整性，不要删除有用信息
- 置信度低的修改要说明
- 如果无法确定标准化方案，给出多个选项
- 必须调用fengtu standardize_address工具获取AI标准化结果
"""


def make_standardizer_agent() -> Agent:
    """
    创建地址标准化智能体
    
    Returns:
        Agent: 配置好的标准化智能体
    """
    agent = Agent(
        name="AddressStandardizer",
        description="地址标准化智能体 - 综合纠错、补全、格式规范化",
        model=f"openai:{settings.LLM_MODEL_ID}",
        instructions=STANDARDIZER_SYSTEM_PROMPT,
        tools=[standardize_address, segment_address],
        markdown=False,
    )
    return agent


def standardize(address: str) -> dict:
    """
    标准化地址
    
    Args:
        address: 待标准化的地址
    
    Returns:
        dict: 标准化结果
    """
    logger.info(f"开始标准化地址: {address}")
    
    agent = make_standardizer_agent()
    
    prompt = f"""请将以下地址标准化为符合GB/T 23705-2009标准的规范地址：

原始地址：{address}

要求：
1. 先调用standardize_address工具获取丰图AI标准化结果
2. 再调用segment_address工具验证分词结果
3. 综合两个工具的结果，给出最终的标准化地址
4. 详细列出所有的修改（纠错、补全、格式调整）
5. 评估标准化质量和置信度
6. 输出符合标准格式的完整地址
"""
    
    response: Any = agent.run(prompt)
    
    return {
        "original": address,
        "result": response.content
    }


if __name__ == "__main__":
    """测试地址标准化智能体"""
    test_cases = [
        "杭州余杭文一西路969号",  # 缺失层级、缺失后缀
        "浙江省杭州市余航区五常街道文一西路969号",  # 错别字
        "阿里西溪5号楼501",  # POI别名、格式不规范
        "  北京  海淀区  中关村大街  1号  ",  # 格式混乱
        "文一西路969号5幢3单元501室",  # 缺失行政区划
    ]
    
    print("=" * 80)
    print("测试地址标准化智能体")
    print("=" * 80)
    
    for addr in test_cases:
        print(f"\n原始地址: {repr(addr)}")
        print("-" * 80)
        
        result = standardize(addr)
        print(f"标准化结果:\n{result['result']}")
        print("=" * 80)
