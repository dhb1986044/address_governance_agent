# Agno v1 到 v2 迁移指南

本文档提供从 Agno v1 升级到 v2 的完整迁移指南。

## 快速升级

```bash
pip install -U agno
```

---

## API 变更对照表

### Agent 参数变更

| v1 参数 | v2 参数 | 说明 |
|---------|---------|------|
| `retriever` | `knowledge_retriever` | 自定义知识检索函数 |
| `add_references` | `add_knowledge_to_context` | 自动添加知识到上下文 |
| `context` | `dependencies` | 上下文依赖注入 |
| `add_state_in_messages` | *(自动处理)* | 不再需要手动设置 |

### Knowledge 变更

| v1 API | v2 API | 说明 |
|--------|--------|------|
| `AgentKnowledge` | `Knowledge` | 类名简化 |
| `knowledge.load()` | `knowledge.add_content()` | 加载内容方法 |
| *(无)* | `knowledge.get_content()` | 新增：获取内容列表 |
| *(无)* | `knowledge.get_content_status()` | 新增：获取处理状态 |

### 返回类型变更

| v1 类型 | v2 类型 |
|---------|---------|
| `RunResponse` | `RunOutput` |
| `RunOutputStartedEvent` | `RunStartedEvent` |
| `RunOutputCompletedEvent` | `RunCompletedEvent` |
| `RunOutputErrorEvent` | `RunErrorEvent` |
| `RunOutputCancelledEvent` | `RunCancelledEvent` |
| `RunOutputContinuedEvent` | `RunContinuedEvent` |
| `RunOutputPausedEvent` | `RunPausedEvent` |
| `RunOutputContentEvent` | `RunContentEvent` |

### Team 参数变更

| v1 参数 | v2 参数 | 说明 |
|---------|---------|------|
| `mode="coordinate"` | *(默认行为)* | 协调模式现为默认 |
| `mode="route"` | `respond_directly=True, determine_input_for_members=False` | 路由模式 |
| `mode="collaborate"` | `delegate_to_all_members=True` | 协作模式 |

### Metrics 字段变更

| v1 字段 | v2 字段 |
|---------|---------|
| `time` | `duration` |
| `audio_tokens` | `audio_total_tokens` |
| `input_audio_tokens` | `audio_input_tokens` |
| `output_audio_tokens` | `audio_output_tokens` |
| `cached_tokens` | `cache_read_tokens` |
| `prompt_tokens` | `input_tokens` |
| `completion_tokens` | `output_tokens` |

---

## 详细迁移步骤

### 1. 更新导入语句

```python
# ❌ v1
from agno.knowledge import AgentKnowledge

# ✅ v2
from agno.knowledge.knowledge import Knowledge
```

### 2. 更新 Knowledge 用法

```python
# ❌ v1 方式
from agno.knowledge import AgentKnowledge
from agno.document.pdf import PDFKnowledgeBase

knowledge = AgentKnowledge(
    sources=[
        PDFKnowledgeBase(path="docs/"),
    ],
    vector_db=vector_db,
)
knowledge.load()

# ✅ v2 方式
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.pdf_reader import PDFReader

knowledge = Knowledge(
    vector_db=vector_db,
    max_results=10,
)

# 使用 add_content 添加内容
knowledge.add_content(
    path="docs/handbook.pdf",
    reader=PDFReader(),
    metadata={"type": "policy"}
)
```

### 3. 更新 Agent 参数

```python
# ❌ v1 方式
agent = Agent(
    model=model,
    retriever=my_custom_retriever,
    add_references=True,
    context={"data": get_data},
    add_state_in_messages=True,
)

# ✅ v2 方式
agent = Agent(
    model=model,
    knowledge_retriever=my_custom_retriever,
    add_knowledge_to_context=True,
    dependencies={"data": get_data},
    # add_state_in_messages 不再需要，自动处理
)
```

### 4. 更新 Team 用法

```python
# ❌ v1 方式
team = Team(
    agents=[agent1, agent2],  # 错误参数名
    mode="route",
)

# ✅ v2 方式
team = Team(
    members=[agent1, agent2],  # 正确参数名
    respond_directly=True,
    determine_input_for_members=False,
)
```

### 5. 更新返回类型处理

```python
# ❌ v1 方式
from agno.run import RunResponse
response: RunResponse = agent.run(query)

# ✅ v2 方式
from agno.run.agent import RunOutput
response: RunOutput = agent.run(query)
```

### 6. 更新异步迭代

```python
# ❌ v1 方式 (返回 AsyncIterator)
async for chunk in agent.arun(query):
    print(chunk)

# ✅ v2 方式 (事件驱动)
async for event in agent.arun(query):
    if hasattr(event, 'content'):
        print(event.content)
```

---

## 数据库迁移

如果您有现有的 Agno 数据库需要迁移，可以使用官方迁移脚本：

```python
# 下载并运行迁移脚本
# https://github.com/agno-agi/agno/blob/main/libs/agno/migrations/v1_to_v2/migrate_to_v2.py
```

**注意事项:**
- 脚本不会清理旧表，以防需要回滚
- 脚本是幂等的，可以安全地多次运行
- Metrics 会自动转换为 v2 格式

---

## 兼容性检查清单

### 必须更新

- [ ] `AgentKnowledge` → `Knowledge`
- [ ] `knowledge.load()` → `knowledge.add_content()`
- [ ] `retriever` → `knowledge_retriever`
- [ ] `add_references` → `add_knowledge_to_context`
- [ ] `Team(agents=...)` → `Team(members=...)`

### 建议更新

- [ ] 移除 `add_state_in_messages`（不再需要）
- [ ] `context` → `dependencies`
- [ ] 更新事件处理代码以使用新的事件类型
- [ ] 更新 Metrics 字段名称

### 可选更新

- [ ] 使用新的 `contents_db` 跟踪内容处理状态
- [ ] 使用新的 `knowledge.get_content_status()` 检查处理进度
- [ ] 利用新的 `knowledge.validate_filters()` 验证过滤器

---

## 常见问题

### Q: 升级后 Knowledge 搜索不工作？

A: 确保设置了 `search_knowledge=True`：

```python
agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,  # 必须设置！
)
```

### Q: Team 行为变化了？

A: `mode` 参数已被移除，使用新参数：

- 原 `mode="coordinate"` → 默认行为
- 原 `mode="route"` → `respond_directly=True`
- 原 `mode="collaborate"` → `delegate_to_all_members=True`

### Q: 找不到 RunResponse？

A: 已重命名为 `RunOutput`：

```python
from agno.run.agent import RunOutput
```

---

## 参考资源

- [官方迁移指南](https://docs.agno.com/how-to/v2-migration)
- [v2 变更日志](https://docs.agno.com/how-to/v2-changelog)
- [Discord 支持](https://agno.link/discord)
- [GitHub Issues](https://github.com/agno-agi/agno/issues)
