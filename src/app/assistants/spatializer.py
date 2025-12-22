"""
地址空间化智能体 - 地址到坐标的转换
核心能力：将标准化地址转换为精确的地理坐标（经纬度）
"""
from agno.agent import Agent
from app.core import settings, get_logger
from app.resources.tools.geocode_tool import geocode_address, reverse_geocode

logger = get_logger(__name__)


SPATIALIZER_SYSTEM_PROMPT = """你是地址空间化专家，负责将文本地址转换为精确的地理坐标。

## 核心任务
将标准化后的地址转换为WGS84坐标系的经纬度坐标。

## 空间化策略

### 1. 地理编码
- 调用geocode_address工具获取经纬度
- 评估编码精度等级（省级/市级/区级/街道/门牌）
- 检查置信度

### 2. 坐标验证
- 坐标范围检查（中国境内：73°E-135°E, 3°N-53°N）
- 使用reverse_geocode反向验证
- 对比反向编码结果与原地址

### 3. 精度评估
- **L6级（门牌）**: 精度10米内，置信度>0.90
- **L5级（路）**: 精度100米内，置信度>0.80
- **L4级（街道）**: 精度1公里内，置信度>0.70
- **L3级（区县）**: 精度10公里内，置信度>0.60
- **L2级（市）**: 精度100公里内，置信度>0.50

### 4. 异常处理
- 编码失败：尝试逐级降级（去掉门牌、楼栋等）
- 坐标异常：标记需要人工复核
- 多义性地址：返回多个候选坐标

## 输出格式
```json
{
  "address": "标准化地址",
  "coordinates": {
    "longitude": 120.023456,
    "latitude": 30.275678,
    "coordinate_system": "WGS84"
  },
  "precision_level": "L6",
  "precision_meters": 10,
  "confidence": 0.92,
  "reverse_check": {
    "address": "逆向编码得到的地址",
    "match": true
  },
  "is_valid": true,
  "issues": []
}
```

## 注意事项
- 务必进行逆向验证，确保坐标正确
- 精度不足时应降级重试
- 坐标超出合理范围要标记
- 记录编码精度等级和置信度
"""


def make_spatializer_agent() -> Agent:
    """
    创建地址空间化智能体
    
    Returns:
        Agent: 配置好的空间化智能体
    """
    agent = Agent(
        name="AddressSpatializer",
        description="地址空间化智能体 - 地址到坐标转换",
        model=f"openai:{settings.LLM_MODEL_ID}",
        instructions=SPATIALIZER_SYSTEM_PROMPT,
        tools=[geocode_address, reverse_geocode],
        markdown=False,
    )
    return agent


def spatialize_address(address: str) -> dict:
    """
    将地址空间化（转换为坐标）
    
    Args:
        address: 标准化的地址
    
    Returns:
        dict: 空间化结果
    """
    logger.info(f"开始空间化地址: {address}")
    
    agent = make_spatializer_agent()
    
    prompt = f"""请将以下地址转换为地理坐标：

地址：{address}

要求：
1. 调用geocode_address工具获取经纬度坐标
2. 检查坐标的合理性（中国境内范围）
3. 使用reverse_geocode进行逆向验证
4. 评估编码精度等级（L2-L6）
5. 计算精度范围（米）
6. 给出置信度评分
7. 如果有问题，说明具体是什么问题
"""
    
    response: Any = agent.run(prompt)
    
    return {
        "address": address,
        "result": response.content
    }


if __name__ == "__main__":
    """测试地址空间化智能体"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号",
        "北京市海淀区中关村大街1号",
        "上海市浦东新区张杨路501号",
        "广东省深圳市南山区科技园",
    ]
    
    print("=" * 80)
    print("测试地址空间化智能体")
    print("=" * 80)
    
    for addr in test_cases:
        print(f"\n地址: {addr}")
        print("-" * 80)
        
        result = spatialize_address(addr)
        print(f"空间化结果:\n{result['result']}")
        print("=" * 80)
