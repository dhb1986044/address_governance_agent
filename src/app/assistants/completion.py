"""
地址补全智能体 - 基于RAG的缺失层级补全
核心能力：推断并补全缺失的行政区划和地址层级
"""
from agno.agent import Agent
from typing import Dict, Any
from app.core import settings, get_logger
from app.resources.tools.segment_tool import segment_address
from app.resources.knowledge.address_knowledge import address_knowledge
from app.resources.knowledge.admin_division import admin_division

logger = get_logger(__name__)


COMPLETION_SYSTEM_PROMPT = """你是中文地址补全专家，擅长基于RAG检索和上下文推理来补全缺失的地址层级。

## 核心任务
对于缺失部分层级的地址（如只有"文一西路969号"），通过以下方式补全：

### 补全策略

1. **RAG知识库检索**
   - 在百亿级地址库中检索相似地址
   - 提取候选地址的完整层级信息
   - 计算匹配度和置信度

2. **行政区划推断**
   - 基于已知的低层级信息推断高层级
   - 例如："文一西路" → "五常街道" → "余杭区" → "杭州市" → "浙江省"
   - 利用行政区划字典验证层级关系

3. **POI实体识别**
   - 识别地址中的POI（如"阿里巴巴西溪园区"）
   - 从POI知识库获取标准地址
   - 补全缺失的行政区划层级

4. **语义上下文分析**
   - 分析地址的语义特征
   - 排除不合理的补全结果
   - 优先选择高置信度的补全方案

### 补全优先级
- **高优先级**: L1-L4（行政区划） - 必须补全
- **中优先级**: L5-L6（路和门牌） - 影响定位精度
- **低优先级**: L7-L18（房间及补充信息） - 可选补全

### 输出格式
```json
{
  "original_address": "原始地址",
  "completed_address": "补全后的完整地址",
  "completions": [
    {
      "level": "L1",
      "name": "省",
      "value": "浙江省",
      "confidence": 0.95,
      "source": "RAG检索",
      "reasoning": "基于'文一西路'检索到大量杭州地址，推断为浙江省"
    }
  ],
  "alternatives": [
    {"address": "备选方案1", "confidence": 0.85},
    {"address": "备选方案2", "confidence": 0.75}
  ],
  "confidence": 0.93,
  "need_manual_review": false
}
```

## 注意事项
- 补全结果必须符合行政区划层级关系
- 置信度<0.8的补全结果需要人工复核
- 如果有多个合理的补全方案，都应该列出
- 必须说明每个补全层级的推理依据
"""


def make_completion_agent() -> Agent:
    """
    创建地址补全智能体
    
    Returns:
        Agent: 配置好的补全智能体
    """
    agent = Agent(
        name="AddressCompletion",
        description="地址补全智能体 - 基于RAG补全缺失层级",
        model=f"openai:{settings.LLM_MODEL_ID}",
        instructions=COMPLETION_SYSTEM_PROMPT,
        tools=[segment_address],
        markdown=False,
    )
    return agent


def complete_address(address: str, context: Dict[str, Any] = None) -> dict:
    """
    补全地址
    
    Args:
        address: 待补全的地址
        context: 补充上下文信息（可选）
    
    Returns:
        dict: 补全结果
    """
    logger.info(f"开始补全地址: {address}")
    
    # 1. 先进行18级分词，识别缺失层级
    segment_result = segment_address(address)
    
    # 2. RAG检索相似地址
    candidates = address_knowledge.hybrid_search(address, top_k=5)
    
    # 3. 构建提示词
    agent = make_completion_agent()
    
    context_info = f"\n上下文信息: {context}" if context else ""
    
    prompt = f"""请补全以下地址的缺失层级：

原始地址：{address}

18级分词结果：
{segment_result}

RAG检索到的相似地址（Top5）：
"""
    for i, candidate in enumerate(candidates, 1):
        prompt += f"\n{i}. {candidate['address']} (得分: {candidate['score']:.2f})"
    
    prompt += f"""{context_info}

要求：
1. 分析缺失的层级（特别是L1-L6）
2. 基于RAG候选集和行政区划知识推断缺失层级
3. 给出补全后的完整地址
4. 说明每个补全层级的推理依据
5. 提供置信度评估和备选方案
"""
    
    response: Any = agent.run(prompt)
    
    return {
        "original": address,
        "result": response.content,
        "candidates": candidates,
        "segment_info": segment_result
    }


if __name__ == "__main__":
    """测试地址补全智能体"""
    test_cases = [
        ("文一西路969号5号楼", None),
        ("阿里西溪园区", None),
        ("五常街道文一西路969号", None),
        ("紫金港校区", {"hint": "杭州地区"}),
    ]
    
    print("=" * 80)
    print("测试地址补全智能体")
    print("=" * 80)
    
    for addr, ctx in test_cases:
        print(f"\n原始地址: {addr}")
        if ctx:
            print(f"上下文: {ctx}")
        print("-" * 80)
        
        result = complete_address(addr, ctx)
        print(f"补全结果:\n{result['result']}")
        print("\n相似地址参考:")
        for i, candidate in enumerate(result['candidates'][:3], 1):
            print(f"  {i}. {candidate['address']} (得分: {candidate['score']:.2f})")
        print("=" * 80)
