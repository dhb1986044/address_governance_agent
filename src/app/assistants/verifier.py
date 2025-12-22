"""
地址校验智能体 - 三重幻觉抑制机制
核心能力：验证地址的真实性、一致性、几何约束
"""
from agno.agent import Agent
from typing import Dict, Any
from app.core import settings, get_logger
from app.resources.tools.geocode_tool import geocode_address
from app.resources.knowledge.admin_division import admin_division

logger = get_logger(__name__)


VERIFIER_SYSTEM_PROMPT = """你是地址校验专家，负责验证地址治理结果的真实性和准确性，防止LLM幻觉。

## 核心任务
对地址治理的输出进行三重校验，确保结果真实可靠。

## 三重校验机制

### 1. 存在性验证 (Existence Check)
**目标**: 确保输出的行政区划、道路、POI等实体真实存在

**检查项**:
- 省市区街道是否在标准行政区划字典中
- 道路名称是否存在于地址库
- POI名称是否在POI知识库中
- 门牌号范围是否合理

**判定标准**:
- 所有行政区划必须存在于标准字典
- 道路/POI至少在知识库或候选集中出现过
- 置信度阈值: 0.80

### 2. 一致性验证 (Consistency Check)
**目标**: 确保地址各层级之间关系正确

**检查项**:
- 行政区划层级关系（余杭区必须属于杭州市）
- 道路必须在对应行政区内
- 楼栋号与小区/园区匹配
- 坐标与行政区一致

**判定标准**:
- 层级关系必须符合行政区划树
- 不允许出现跨区域矛盾（如"北京市杭州区"）
- 置信度阈值: 0.85

### 3. 几何约束验证 (Geometry Check)
**目标**: 确保地理坐标在合理范围内

**检查项**:
- 坐标是否在中国境内（73°E-135°E, 3°N-53°N）
- 坐标是否落在对应行政区的多边形内
- 坐标精度是否与层级匹配
- 距离是否合理（如两个相邻楼栋不应相距10公里）

**判定标准**:
- 坐标必须在对应行政区多边形内
- 坐标偏差超过1公里需人工复核
- 置信度阈值: 0.80

## 综合判定

### 通过条件
- 三重校验全部通过
- 综合置信度 >= 0.80

### 需人工复核
- 任一校验置信度 < 0.80
- 检测到矛盾或异常
- 多个备选方案差异较大

### 拒绝
- 存在明显的幻觉（如不存在的省市区）
- 几何约束严重违反
- 综合置信度 < 0.60

## 输出格式
```json
{
  "address": "待校验地址",
  "validation_result": {
    "existence_check": {
      "passed": true,
      "confidence": 0.95,
      "issues": []
    },
    "consistency_check": {
      "passed": true,
      "confidence": 0.92,
      "issues": []
    },
    "geometry_check": {
      "passed": true,
      "confidence": 0.88,
      "issues": []
    }
  },
  "overall_confidence": 0.92,
  "decision": "通过",
  "need_manual_review": false,
  "issues": [],
  "suggestions": []
}
```

## 注意事项
- 宁可标记为需复核，也不要放过可疑结果
- 所有判定必须有明确依据
- 置信度低于阈值必须说明原因
- 发现幻觉要立即标记
"""


def make_verifier_agent() -> Agent:
    """
    创建地址校验智能体
    
    Returns:
        Agent: 配置好的校验智能体
    """
    agent = Agent(
        name="AddressVerifier",
        description="地址校验智能体 - 三重幻觉抑制机制",
        model=f"openai:{settings.LLM_MODEL_ID}",
        instructions=VERIFIER_SYSTEM_PROMPT,
        tools=[geocode_address],
        markdown=False,
    )
    return agent


def verify_address(
    address: str,
    coordinates: Dict[str, float] = None,
    segment_info: Dict[str, Any] = None
) -> dict:
    """
    校验地址
    
    Args:
        address: 待校验的地址
        coordinates: 地理坐标（可选）
        segment_info: 分词信息（可选）
    
    Returns:
        dict: 校验结果
    """
    logger.info(f"开始校验地址: {address}")
    
    agent = make_verifier_agent()
    
    # 如果没有提供坐标，先进行地理编码
    if not coordinates:
        from app.resources.tools.geocode_tool import geocode_address as geocode_func
        geo_result = geocode_func(address)
        if geo_result.get('longitude') and geo_result.get('latitude'):
            coordinates = {
                "longitude": geo_result['longitude'],
                "latitude": geo_result['latitude']
            }
    
    coord_info = f"\n坐标信息: {coordinates}" if coordinates else "\n坐标信息: 未提供"
    segment_str = f"\n分词信息: {segment_info}" if segment_info else ""
    
    prompt = f"""请对以下地址进行三重校验：

地址：{address}{coord_info}{segment_str}

要求进行三重校验：

1. **存在性验证**
   - 检查省市区街道是否在标准字典中
   - 检查道路、POI是否真实存在
   - 使用admin_division和knowledge库验证

2. **一致性验证**
   - 验证行政区划层级关系
   - 检查各层级是否匹配
   - 识别矛盾（如"北京市杭州区"）

3. **几何约束验证**
   - 如果有坐标，检查是否在中国境内
   - 验证坐标是否在对应行政区内
   - 评估坐标精度

给出综合判定：
- 通过：所有校验通过，置信度>=0.80
- 需复核：任一校验置信度<0.80
- 拒绝：存在明显错误或幻觉

详细说明所有发现的问题和置信度评估。
"""
    
    response: Any = agent.run(prompt)
    
    return {
        "address": address,
        "result": response.content,
        "coordinates": coordinates
    }


if __name__ == "__main__":
    """测试地址校验智能体"""
    test_cases = [
        {
            "address": "浙江省杭州市余杭区五常街道文一西路969号",
            "coordinates": {"longitude": 120.023, "latitude": 30.276},
            "desc": "标准地址+正确坐标"
        },
        {
            "address": "浙江省杭州市不存在区文一西路969号",
            "coordinates": None,
            "desc": "存在性错误（虚构区名）"
        },
        {
            "address": "北京市杭州市余杭区",
            "coordinates": None,
            "desc": "一致性错误（层级矛盾）"
        },
        {
            "address": "浙江省杭州市余杭区五常街道文一西路969号",
            "coordinates": {"longitude": 116.4, "latitude": 39.9},  # 北京坐标
            "desc": "几何约束错误（坐标与地址不符）"
        },
    ]
    
    print("=" * 80)
    print("测试地址校验智能体")
    print("=" * 80)
    
    for case in test_cases:
        print(f"\n测试: {case['desc']}")
        print(f"地址: {case['address']}")
        if case['coordinates']:
            print(f"坐标: {case['coordinates']}")
        print("-" * 80)
        
        result = verify_address(
            case['address'],
            case['coordinates']
        )
        print(f"校验结果:\n{result['result']}")
        print("=" * 80)
