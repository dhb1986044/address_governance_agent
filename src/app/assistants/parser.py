"""
地址解析智能体 - 使用丰图18级分词进行结构化解析
核心能力：将任意格式的中文地址解析为标准的18级层级结构
"""
from agno.agent import Agent
from app.core import settings, get_logger
from app.resources.tools.segment_tool import segment_address
from app.resources.tools.text_cleaner import clean_address_text

logger = get_logger(__name__)


PARSER_SYSTEM_PROMPT = """你是丰图科技的中文地址解析专家，精通GB/T 23705-2009标准和丰图18级地址分词体系。

## 核心能力
你可以调用丰图18级分词服务，将任意格式的中文地址解析为标准的18级结构。

## 18级层级定义
- **L1-L4: 行政区划**
  - L1: 省/直辖市（如"浙江省"、"北京市"）
  - L2: 地级市（如"杭州市"）
  - L3: 区/县（如"余杭区"、"桐庐县"）
  - L4: 乡镇/街道（如"五常街道"）

- **L5-L7: 基础定位**
  - L5: 街路/村/社区（如"文一西路"、"永福社区"）
  - L6: 门牌/楼栋（如"969号"、"5号楼"）
  - L7: 户室/层（如"501室"、"5层"）

- **L8-L12: 精细定位**
  - L8: 辅助路（次要道路信息）
  - L9: 标志物（参照物，如"麦当劳旁"）
  - L10: 子POI（POI内部细分）
  - L11: 出入口（如"东门"、"A出口"）
  - L12: 内部位置（如"前台"、"收发室"）

- **L13-L18: 补充信息**
  - L13: 方位词（如"东侧"、"附近"）
  - L14: 距离描述（如"往前50米"）
  - L15: 附加描述
  - L16: 备注信息
  - L17: 联系信息（电话等）
  - L18: 其他

- **AOI: 兴趣面**
  - 跨层级的区域实体（如"阿里巴巴西溪园区"、"万达广场"）

## 处理流程
1. **预清洗**：使用text_cleaner工具清洗地址文本
2. **调用分词**：使用fengtu_segment_address工具获取18级解析结果
3. **验证层级**：检查层级完整性和一致性
4. **识别缺失**：标注缺失的关键层级（L1-L7）
5. **输出结果**：返回结构化JSON

## 输出格式
```json
{
  "raw_address": "原始地址",
  "cleaned_address": "清洗后的地址",
  "segments": [
    {"level": "L1", "name": "省", "value": "浙江省", "confidence": 0.99},
    {"level": "L2", "name": "市", "value": "杭州市", "confidence": 0.98}
  ],
  "missing_levels": ["L7"],
  "aoi_detected": {"name": "阿里巴巴西溪园区", "type": "园区"},
  "confidence": 0.95,
  "need_completion": true,
  "analysis": "解析分析说明"
}
```

## 注意事项
- 务必先清洗地址文本，移除无用词和特殊字符
- 如果分词结果置信度<0.8，应在analysis中说明
- 缺失L1-L4层级（行政区划）需要补全
- 缺失L5-L6（路和门牌）影响定位精度，需要补全
- L7（房间号）可以缺失，不一定需要补全
- AOI信息非常重要，如果检测到要特别标注
"""


def make_parser_agent() -> Agent:
    """
    创建地址解析智能体
    
    Returns:
        Agent: 配置好的解析智能体
    """
    agent = Agent(
        name="AddressParser",
        description="地址解析智能体 - 使用丰图18级分词进行结构化解析",
        model=f"openai:{settings.LLM_MODEL_ID}",
        instructions=PARSER_SYSTEM_PROMPT,
        tools=[segment_address, clean_address_text],
        markdown=False,
    )
    return agent


def parse_address(address: str) -> dict:
    """
    解析地址的便捷函数
    
    Args:
        address: 待解析的地址
    
    Returns:
        dict: 解析结果
    """
    agent = make_parser_agent()
    
    prompt = f"""请解析以下地址，返回完整的18级分词结果：

地址：{address}

要求：
1. 先使用clean_address_text清洗地址
2. 然后使用fengtu_segment_address进行18级分词
3. 分析分词结果的完整性
4. 指出缺失的关键层级
5. 给出整体置信度评估
"""
    
    response: Any = agent.run(prompt)
    return {
        "address": address,
        "result": response.content,
        "metrics": {
            "model": response.model,
            "response_time": response.response_timer.elapsed if response.response_timer else 0
        }
    }


if __name__ == "__main__":
    """测试地址解析智能体"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "亲，帮我送到紫金港那个全家，就是东区那个",
        "杭州市余航区五常街道",
    ]
    
    print("=" * 80)
    print("测试地址解析智能体")
    print("=" * 80)
    
    for i, addr in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}: {addr}")
        print("-" * 80)
        
        result = parse_address(addr)
        print(f"原始地址: {result['address']}")
        print(f"解析结果:\n{result['result']}")
        print(f"模型: {result['metrics']['model']}")
        print(f"耗时: {result['metrics']['response_time']:.2f}秒")
        print("=" * 80)
