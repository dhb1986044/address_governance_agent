# 中文地址治理智能体系统 - 基于 Agno SDK v2.3.20

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Agno SDK](https://img.shields.io/badge/agno-v2.3.20-green.svg)](https://github.com/agno-sdk/agno)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

基于 **Agno SDK v2.3.20** 最新框架和 LLM+RAG 的分层多智能体架构(HMAS)，面向百亿级规模的中文地址治理解决方案。

## 📋 项目概述

本系统整合丰图科技核心服务能力（18级地址分词、地理编码、地址标准化），结合大语言模型和RAG技术，实现智能化的中文地址治理。遵循GB/T 23705-2009国家标准，提供地址解析、纠错、补全、标准化、空间化、校验等完整功能。

### 核心特性

- **🎯 18级地址解析**：符合GB/T 23705-2009标准，精确解析省/市/区/街道/路/门牌/楼栋/房间等18个层级
- **🤖 分层多智能体**：HMAS架构，7个专家智能体协同工作，基于 Agno SDK v2.3.20 Team API
- **🔍 RAG增强**：百亿级地址知识库，LanceDB 向量检索
- **✅ 三重校验**：存在性验证 + 一致性验证 + 几何约束验证，有效抑制LLM幻觉
- **⚡ 高性能**：Workflow API 实现确定性流水线，支持批量并发处理
- **🌐 多接口**：Typer CLI命令行 + RESTful API + Python SDK

## 🏗️ 架构设计 (基于 Agno v2.3.20)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Team: Orchestrator Agent                        │
│                     (协调者 - 意图识别/任务分发)                      │
│                     使用 Team API (v2.3.20)                          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Parser Agent  │    │ Completion    │    │ Correction    │
│ (解析)        │    │ Agent(补全)   │    │ Agent(纠错)   │
│ OpenAIChat    │    │ + SqliteDb    │    │ + History     │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Standardizer  │    │ Spatializer   │    │ Verifier      │
│ Agent(标准化) │    │ Agent(空间化) │    │ Agent(校验)   │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Tool Layer (工具层)                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │丰图18级分词API│ │丰图地理编码API│ │丰图标准化API │ │ @tool装饰器│  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Agno SDK v2.3.20
- 阿里云DashScope API Key（用于LLM）
- 丰图科技API Key（可选，用于真实API调用）

### 安装

```bash
# 克隆仓库
git clone https://github.com/306251708dd-gif/address_governance_agent.git
cd address_governance_agent

# 安装依赖（使用 Agno v2.3.20）
pip install -r requirements.txt

# 或使用pip安装（开发模式）
pip install -e .
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入必要的API Keys
# - LLM_API_KEY: 阿里云DashScope API Key
# - FENGTU_API_KEY: 丰图科技API Key（可选）
nano .env
```

## 💻 使用示例

### 1. 命令行接口（CLI）- 使用 Typer

```bash
# 交互式对话模式（新功能！）
python -m app.api.cli chat

# 处理单个地址
python -m app.api.cli process "浙江省杭州市余杭区五常街道文一西路969号"

# 批量处理文件
python -m app.api.cli batch input.txt output.json

# 查看配置
python -m app.api.cli config

# 运行测试用例
python -m app.api.cli test
```

### 2. Python API - 使用 Agno v2.3.20

#### 使用 Team API（推荐）

```python
from app.teams.address_governance_team import make_address_governance_team

# 创建地址治理团队
team = make_address_governance_team()

# 流式输出处理结果
team.print_response(
    "请完成以下地址的全流程治理：浙江省杭州市余杭区五常街道文一西路969号",
    stream=True,
    markdown=True
)

# 或获取结果
response = team.run("请完成地址治理：文一西路969号")
print(response.content)
```

#### 使用 Workflow API

```python
from app.workflows.address_pipeline import make_address_pipeline

# 创建流水线
pipeline = make_address_pipeline()

# 流式输出
pipeline.print_response("文一西路969号5号楼", stream=True)

# 或获取结果
response = pipeline.run(input="文一西路969号5号楼")
print(response.content)
```

#### 使用单个 Agent

```python
from app.assistants.parser import make_parser_agent

# 创建解析智能体
parser = make_parser_agent()

# 流式输出
parser.print_response("请解析以下地址：文一西路969号", stream=True)

# 或获取结果
response = parser.run("请解析以下地址：文一西路969号")
print(response.content)
```

### 3. REST API服务

```bash
# 启动API服务
python -m app.api.server

# 或使用uvicorn
uvicorn app.api.server:app --host 0.0.0.0 --port 8000
```

访问API文档：http://localhost:8000/docs

## 📁 项目结构（Agno v2.3.20 规范）

```
src/app/
├── core/                      # 基础设施层
│   ├── config.py              # 配置管理（Settings）
│   ├── logger.py              # 日志工具
│   └── fengtu_client.py       # 丰图API客户端
├── resources/                 # 共享资源层
│   ├── tools/                 # 工具集（使用 @tool 装饰器）
│   │   ├── segment_tool.py    # 18级分词工具
│   │   ├── geocode_tool.py    # 地理编码工具
│   │   ├── standardize_tool.py # 标准化工具
│   │   ├── text_cleaner.py    # 文本清洗工具
│   │   └── similarity_tool.py # 相似度计算工具
│   └── knowledge/             # 知识库（Knowledge + LanceDb）
│       ├── address_knowledge.py # 地址库（RAG）
│       ├── poi_knowledge.py   # POI库
│       └── admin_division.py  # 行政区划
├── assistants/                # 智能体层（使用 Agent API）
│   ├── parser.py              # 解析智能体
│   ├── normalizer.py          # 规范化智能体
│   ├── completion.py          # 补全智能体
│   ├── correction.py          # 纠错智能体
│   ├── standardizer.py        # 标准化智能体
│   ├── spatializer.py         # 空间化智能体
│   └── verifier.py            # 校验智能体
├── teams/                     # 协作层（使用 Team API）
│   └── address_governance_team.py # HMAS团队
├── workflows/                 # 工作流层（使用 Workflow API）
│   ├── address_pipeline.py    # 治理流水线
│   └── batch_processor.py     # 批量处理器
└── api/                       # 接口层
    ├── cli.py                 # Typer CLI接口
    └── server.py              # FastAPI服务
```

## 🔧 Agno SDK v2.3.20 核心特性

### Agent 创建

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.sqlite import SqliteDb

agent = Agent(
    name="Agent Name",
    id="agent-id",
    model=OpenAIChat(id="gpt-4o", api_key="...", base_url="..."),
    tools=[tool1, tool2],
    instructions=["指令1", "指令2"],
    description="Agent 描述",
    db=SqliteDb(db_file="agents.db"),
    add_history_to_context=True,
    add_datetime_to_context=True,
    markdown=True,
)
```

### Team 创建

```python
from agno.team import Team

team = Team(
    name="Team Name",
    model=OpenAIChat(id="gpt-4o"),
    members=[agent1, agent2, agent3],
    instructions=["团队协作指令"],
    db=SqliteDb(db_file="teams.db"),
    show_members_responses=True,
    retries=3,
    exponential_backoff=True,
)
```

### Workflow 创建

```python
from agno.workflow import Workflow, Step
from agno.workflow.step import StepInput, StepOutput

def custom_step(step_input: StepInput) -> StepOutput:
    return StepOutput(content=f"Processed: {step_input.input}")

workflow = Workflow(
    name="Workflow Name",
    steps=[
        Step(name="Step 1", agent=agent1),
        custom_step,  # 自定义函数
        Step(name="Step 3", agent=agent3),
    ],
)
```

### Tool 创建

```python
from agno.tools import tool

@tool(name="tool_name", description="工具描述")
def my_tool(param1: str, param2: int = 0) -> dict:
    """工具的详细说明"""
    return {"result": "处理结果"}
```

## 🧪 测试用例

```python
test_cases = [
    # 标准地址
    "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
    
    # 缺失层级
    "文一西路969号5号楼",
    
    # 口语化描述
    "亲，帮我送到紫金港那个全家，就是东区那个",
    
    # 错别字
    "杭州市余航区五常街道",
    
    # POI别名
    "阿里西溪园区B区",
    
    # 复杂描述
    "浙一医院余杭院区旁边那个全家",
]
```

运行测试：

```bash
python -m app.api.cli test
```

## 📚 文档

- [架构设计文档](docs/architecture.md) - 详细的系统架构设计
- [API参考文档](docs/api_reference.md) - 完整的API接口说明
- [LLM+RAG 地址治理智能体方案](LLM+RAG%20地址治理智能体方案.md) - 研究报告

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- 项目主页: https://github.com/306251708dd-gif/address_governance_agent
- 问题反馈: https://github.com/306251708dd-gif/address_governance_agent/issues

---

**基于 Agno SDK v2.3.20 | 丰图科技核心能力 | 精度99.8%+ | 百亿级规模**