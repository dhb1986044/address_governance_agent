---
name: Agno智能体框架编程指南
description: Agno是一个高性能的多智能体框架，用于构建、运行和管理AI智能体系统。本指南提供最新v2.0版本的API使用方式、最佳实践和代码示例。
version: 2.0
tags: [agno, agent, llm, rag, knowledge, tools, multi-agent]
docs_url: https://docs.agno.com/
---

# Agno 智能体框架编程指南

> **官方文档**: https://docs.agno.com/
> **GitHub**: https://github.com/agno-agi/agno
> **版本**: 2.0

## 目录

1. [核心概念](#核心概念)
2. [快速开始](#快速开始)
3. [Agent创建与配置](#agent创建与配置)
4. [Knowledge/RAG集成](#knowledgerag集成)
5. [Tools开发](#tools开发)
6. [Team多智能体协作](#team多智能体协作)
7. [Workflow工作流](#workflow工作流)
8. [Model提供商配置](#model提供商配置)
9. [常见错误与解决方案](#常见错误与解决方案)
10. [v1到v2迁移指南](#v1到v2迁移指南)

---

## 核心概念

### Agno架构组成

```
┌─────────────────────────────────────────────────────────────┐
│                        AgentOS                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │   Agent     │ │   Team      │ │     Workflow            ││
│  │  单智能体   │ │  多智能体    │ │    确定性工作流         ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
│         ↓              ↓                    ↓                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            Model (LLM) / Tools / Knowledge              ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 关键组件

| 组件 | 描述 | 使用场景 |
|------|------|----------|
| **Agent** | 单一智能体，包含模型、工具、知识库 | 90%的使用场景 |
| **Team** | 多智能体协作，LLM决定任务分配 | 需要多专家协作 |
| **Workflow** | 确定性工作流，程序化控制执行顺序 | ETL流程、多步骤任务 |
| **Knowledge** | RAG知识库，支持向量检索 | 需要外部知识增强 |
| **Tools** | 工具函数，扩展Agent能力 | 与外部系统交互 |

---

## 快速开始

### 安装

```bash
# 安装最新版本
pip install -U agno

# 安装额外依赖（根据需要）
pip install agno[openai]       # OpenAI支持
pip install agno[anthropic]    # Claude支持
pip install agno[postgres]     # PostgreSQL存储
```

### 最简示例

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# 创建Agent
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions="你是一个有帮助的助手",
    markdown=True,
)

# 运行Agent
agent.print_response("你好，请介绍一下自己", stream=True)
```

---

## Agent创建与配置

### 基础Agent参数

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

agent = Agent(
    # === 必需参数 ===
    model=OpenAIChat(id="gpt-4o"),  # LLM模型
    
    # === 标识参数 ===
    name="MyAgent",                  # Agent名称
    id="agent-001",                  # Agent ID
    user_id="user-123",              # 用户ID（用于会话隔离）
    session_id="session-abc",        # 会话ID
    
    # === 指令参数 ===
    instructions="你是一个专业的数据分析师",  # 系统指令
    description="数据分析专家",               # Agent描述
    
    # === 存储参数 ===
    db=SqliteDb(db_file="agents.db"),  # 会话存储
    add_history_to_context=True,        # 添加历史到上下文
    num_history_runs=3,                 # 历史运行次数
    
    # === 输出参数 ===
    markdown=True,                      # Markdown格式输出
    debug_mode=False,                   # 调试模式
)
```

### 结构化输出

```python
from pydantic import BaseModel
from typing import List

class AnalysisResult(BaseModel):
    summary: str
    findings: List[str]
    confidence: float

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    output_schema=AnalysisResult,  # 强制结构化输出
)

# 运行后获取结构化结果
result = agent.run("分析这段数据...")
analysis: AnalysisResult = result.content
print(analysis.summary)
```

### ⚠️ 关键性能规则

```python
# ❌ 错误：在循环中创建Agent（严重性能问题）
for query in queries:
    agent = Agent(...)  # 每次都重建Agent
    agent.run(query)

# ✅ 正确：创建一次，重复使用
agent = Agent(...)
for query in queries:
    agent.run(query)
```

---

## Knowledge/RAG集成

### Knowledge基础配置

```python
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.agent import Agent

# 1. 配置向量数据库
vector_db = ChromaDb(
    collection="my_knowledge",
    path="./chroma_db",
    embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    persistent_client=True,
)

# 2. 创建Knowledge实例
knowledge = Knowledge(
    vector_db=vector_db,
    max_results=10,  # 检索结果数量
)

# 3. 添加内容
knowledge.add_content(
    path="docs/handbook.pdf",
    metadata={"type": "policy", "department": "hr"}
)

# 4. 创建带Knowledge的Agent
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    knowledge=knowledge,
    search_knowledge=True,  # 关键：启用Agentic RAG
    instructions="使用知识库回答问题，并引用来源",
)
```

### Embedder选择

```python
# OpenAI Embedder
from agno.knowledge.embedder.openai import OpenAIEmbedder
embedder = OpenAIEmbedder(id="text-embedding-3-small", api_key="...")

# 本地 SentenceTransformer
from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
embedder = SentenceTransformerEmbedder(
    id="BAAI/bge-small-zh-v1.5",
    normalize_embeddings=True
)

# Google Gemini Embedder
from agno.knowledge.embedder.google import GeminiEmbedder
embedder = GeminiEmbedder(id="models/embedding-001", api_key="...")

# 智谱 (通过OpenAI接口)
embedder = OpenAIEmbedder(
    id="embedding-3-pro",
    api_key="your-zhipu-key",
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)
```

### VectorDB选择

```python
# ChromaDb (开发/小规模)
from agno.vectordb.chroma import ChromaDb
vector_db = ChromaDb(collection="kb", path="./chroma_db")

# LanceDb (开发/中规模)
from agno.vectordb.lancedb import LanceDb, SearchType
vector_db = LanceDb(
    uri="tmp/lancedb",
    table_name="knowledge",
    search_type=SearchType.hybrid,
)

# PgVector (生产环境推荐)
from agno.vectordb.pgvector import PgVector
vector_db = PgVector(
    table_name="knowledge",
    db_url="postgresql+psycopg://user:pass@localhost:5432/db",
)
```

### 手动搜索Knowledge

```python
# 手动搜索
results = knowledge.search(
    query="请假政策是什么？",
    max_results=5,
    filters={"department": "hr"}
)

for doc in results:
    print(doc.content)
    print(doc.meta_data)
```

---

## Tools开发

### 函数作为Tool

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat

def get_weather(city: str) -> str:
    """获取指定城市的天气。
    
    Args:
        city: 城市名称
    
    Returns:
        天气描述
    """
    # 实际实现应调用天气API
    return f"{city}今天晴天，气温25°C"

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[get_weather],  # 直接传入函数
)

agent.print_response("北京今天天气怎么样？")
```

### Toolkit类

```python
from agno.tools import Toolkit

class DatabaseTools(Toolkit):
    """数据库工具集"""
    
    def __init__(self, connection_string: str):
        super().__init__(name="database_tools")
        self.conn_str = connection_string
        
        # 注册工具方法
        self.register(self.execute_query)
        self.register(self.get_schema)
    
    def execute_query(self, sql: str) -> str:
        """执行SQL查询并返回结果。
        
        Args:
            sql: SQL查询语句
        
        Returns:
            JSON格式的查询结果
        """
        # 实际实现
        return '{"status": "success", "data": [...]}'
    
    def get_schema(self, table_name: str) -> str:
        """获取表结构信息。
        
        Args:
            table_name: 表名
        
        Returns:
            表结构描述
        """
        return f"表 {table_name} 的结构: ..."

# 使用
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DatabaseTools("postgresql://...")],
)
```

### 内置Toolkit

```python
# DuckDuckGo搜索
from agno.tools.duckduckgo import DuckDuckGoTools

# MCP工具
from agno.tools.mcp import MCPTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        DuckDuckGoTools(),
        MCPTools(transport="streamable-http", url="https://example.com/mcp"),
    ],
)
```

---

## Team多智能体协作

### 使用场景

- 需要多个专业领域的协作
- 复杂任务需要分工
- 需要LLM动态决定任务分配

```python
from agno.team.team import Team
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# 创建专业Agent
researcher = Agent(
    name="研究员",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
    instructions="负责搜索和研究信息",
)

writer = Agent(
    name="作家",
    model=OpenAIChat(id="gpt-4o"),
    instructions="负责撰写内容",
)

# 创建Team
team = Team(
    members=[researcher, writer],
    model=OpenAIChat(id="gpt-4o"),  # Team协调模型
    instructions="研究并撰写高质量的文章",
)

team.print_response("写一篇关于AI发展的文章")
```

### Team配置选项

```python
team = Team(
    members=[...],
    model=OpenAIChat(id="gpt-4o"),
    
    # 响应模式
    respond_directly=True,  # 直接返回成员响应，不经过Team处理
    
    # 任务分配
    delegate_to_all_members=True,  # 同时分配给所有成员
    determine_input_for_members=True,  # Team决定每个成员的输入
)
```

---

## Workflow工作流

### 使用场景

- 需要确定性的执行顺序
- 包含条件分支逻辑
- ETL或多步骤处理流程

```python
from agno.workflow.workflow import Workflow
from agno.db.sqlite import SqliteDb

# 定义工作流步骤
async def content_workflow(session_state, topic: str):
    # 步骤1：研究
    research = await researcher.arun(f"研究主题: {topic}")
    
    # 步骤2：写初稿
    draft = await writer.arun(f"基于以下研究写草稿: {research.content}")
    
    # 步骤3：编辑
    final = await editor.arun(f"编辑以下草稿: {draft.content}")
    
    return final

# 创建Workflow
workflow = Workflow(
    name="ContentGenerator",
    steps=content_workflow,
    db=SqliteDb(db_file="workflow.db"),
)

# 运行
result = workflow.run("人工智能的未来")
```

---

## Model提供商配置

### OpenAI

```python
from agno.models.openai import OpenAIChat

model = OpenAIChat(
    id="gpt-4o",                    # 模型ID
    api_key="sk-...",               # API密钥（可选，默认从环境变量）
    base_url="https://...",         # 自定义端点（可选）
    temperature=0.7,                # 温度
    max_tokens=1000,                # 最大token
)
```

### Anthropic (Claude)

```python
from agno.models.anthropic import Claude

model = Claude(id="claude-sonnet-4-5")
```

### 智谱GLM (通过OpenAI兼容接口)

```python
from agno.models.openai import OpenAIChat

model = OpenAIChat(
    id="glm-4",
    api_key="your-zhipu-api-key",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
```

### Google Gemini

```python
from agno.models.google import Gemini

model = Gemini(id="gemini-1.5-pro", api_key="...")
```

---

## 常见错误与解决方案

### 1. 在循环中创建Agent

```python
# ❌ 问题代码
for q in queries:
    agent = Agent(model=OpenAIChat(id="gpt-4o"))
    agent.run(q)

# ✅ 解决方案
agent = Agent(model=OpenAIChat(id="gpt-4o"))
for q in queries:
    agent.run(q)
```

### 2. Knowledge未启用搜索

```python
# ❌ 问题：添加了knowledge但未启用搜索
agent = Agent(
    knowledge=knowledge,
    # 缺少 search_knowledge=True
)

# ✅ 解决方案
agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,  # 启用Agentic RAG
)
```

### 3. 生产环境使用SQLite

```python
# ❌ 问题：生产环境使用SQLite
db = SqliteDb(db_file="prod.db")

# ✅ 解决方案：使用PostgreSQL
from agno.db.postgres import PostgresDb
db = PostgresDb(db_url=os.getenv("DATABASE_URL"))
```

### 4. Team参数混淆

```python
# ❌ 错误：使用 agents= 参数
team = Team(agents=[...])  # 错误！

# ✅ 正确：使用 members= 参数
team = Team(members=[...])
```

---

## v1到v2迁移指南

### API变更对照表

| v1 API | v2 API | 说明 |
|--------|--------|------|
| `AgentKnowledge` | `Knowledge` | 类名简化 |
| `knowledge.load()` | `knowledge.add_content()` | 方法改名 |
| `retriever` | `knowledge_retriever` | Agent参数 |
| `add_references` | `add_knowledge_to_context` | Agent参数 |
| `context` (Agent) | `dependencies` | Agent参数 |
| `add_state_in_messages` | 自动处理 | 不再需要 |
| `RunResponse` | `RunOutput` | 返回类型 |
| `Team(mode=...)` | `Team(respond_directly=..., delegate_to_all_members=...)` | Team模式 |

### 迁移步骤

1. **升级包**
   ```bash
   pip install -U agno
   ```

2. **更新导入**
   ```python
   # v1
   from agno.knowledge import AgentKnowledge
   
   # v2
   from agno.knowledge.knowledge import Knowledge
   ```

3. **更新Knowledge用法**
   ```python
   # v1
   knowledge.load()
   
   # v2
   knowledge.add_content(path="...", reader=PDFReader())
   ```

4. **更新Agent参数**
   ```python
   # v1
   agent = Agent(
       retriever=custom_retriever,
       add_references=True,
   )
   
   # v2
   agent = Agent(
       knowledge_retriever=custom_retriever,
       add_knowledge_to_context=True,
   )
   ```

---

## 参考资源

- **官方文档**: https://docs.agno.com/
- **GitHub仓库**: https://github.com/agno-agi/agno
- **迁移指南**: https://docs.agno.com/how-to/v2-migration
- **示例库**: https://docs.agno.com/examples/use-cases/agents/overview
- **Discord社区**: https://agno.link/discord
