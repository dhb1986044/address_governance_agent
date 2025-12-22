# 中文地址治理智能体系统

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

基于LLM+RAG的分层多智能体架构(HMAS)，面向百亿级规模的中文地址治理解决方案。

## 📋 项目概述

本系统整合丰图科技核心服务能力（18级地址分词、地理编码、地址标准化），结合大语言模型和RAG技术，实现智能化的中文地址治理。遵循GB/T 23705-2009国家标准，提供地址解析、纠错、补全、标准化、空间化、校验等完整功能。

### 核心特性

- **🎯 18级地址解析**：符合GB/T 23705-2009标准，精确解析省/市/区/街道/路/门牌/楼栋/房间等18个层级
- **🤖 分层多智能体**：HMAS架构，7个专家智能体协同工作
- **🔍 RAG增强**：百亿级地址知识库，Milvus向量检索 + Elasticsearch全文检索
- **✅ 三重校验**：存在性验证 + 一致性验证 + 几何约束验证，有效抑制LLM幻觉
- **⚡ 高性能**：支持多线程/多进程并发，漏斗式分级处理（40%规则+30%模型+15%ES+15%LLM）
- **🌐 多接口**：CLI命令行 + RESTful API + Python SDK

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                      L1: Orchestrator Agent                         │
│                     (协调者 - 意图识别/任务分发)                      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Parser Agent  │    │ Completion    │    │ Correction    │
│ (解析)        │    │ Agent(补全)   │    │ Agent(纠错)   │
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
│                      L3: Tool Layer (工具层)                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │丰图18级分词API│ │丰图地理编码API│ │丰图标准化API │ │ RAG检索    │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- 丰图科技API Key（可选，用于真实API调用）
- 阿里云DashScope API Key（用于LLM）

### 安装

```bash
# 克隆仓库
git clone https://github.com/306251708dd-gif/address_governance_agent.git
cd address_governance_agent

# 安装依赖
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

### 使用示例

#### 1. 命令行接口（CLI）

```bash
# 处理单个地址
python -m app.api.cli process "浙江省杭州市余杭区五常街道文一西路969号"

# 处理单个地址（仅纠错）
python -m app.api.cli process "杭州市余航区五常街道" --intent correct

# 批量处理CSV文件
python -m app.api.cli batch input.csv output.csv --workers 20

# 处理多个地址
python -m app.api.cli multi "地址1" "地址2" "地址3" --output results.json

# 查看配置
python -m app.api.cli config

# 运行测试用例
python -m app.api.cli test
```

#### 2. Python API

```python
from app.workflows.address_pipeline import AddressPipeline

# 创建流水线
pipeline = AddressPipeline()

# 处理单个地址
result = pipeline.process_single("浙江省杭州市余杭区五常街道文一西路969号")

print(f"原始地址: {result.original_address}")
print(f"最终地址: {result.final_address}")
print(f"置信度: {result.confidence:.2f}")
print(f"状态: {result.status}")

# 批量处理
addresses = [
    "文一西路969号5号楼",
    "杭州市余航区五常街道",
    "阿里西溪园区B区"
]

results = pipeline.process_batch(addresses)
for r in results:
    print(f"{r.original_address} → {r.final_address}")
```

#### 3. REST API服务

```bash
# 启动API服务
python -m app.api.server

# 或使用uvicorn
uvicorn app.api.server:app --host 0.0.0.0 --port 8000
```

访问API文档：http://localhost:8000/docs

**API示例**：

```bash
# 处理单个地址
curl -X POST "http://localhost:8000/api/v1/address/process" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "浙江省杭州市余杭区五常街道文一西路969号",
    "intent": "full"
  }'

# 批量处理（同步）
curl -X POST "http://localhost:8000/api/v1/address/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "addresses": ["地址1", "地址2", "地址3"],
    "async_mode": false
  }'

# 健康检查
curl "http://localhost:8000/health"
```

## 📁 项目结构

```
src/app/
├── core/                      # 基础设施层
│   ├── config.py              # 配置管理
│   ├── logger.py              # 日志工具
│   └── fengtu_client.py       # 丰图API客户端
├── resources/                 # 共享资源层
│   ├── tools/                 # 工具集
│   │   ├── segment_tool.py    # 18级分词
│   │   ├── geocode_tool.py    # 地理编码
│   │   ├── standardize_tool.py # 标准化
│   │   ├── text_cleaner.py    # 文本清洗
│   │   └── similarity_tool.py # 相似度计算
│   └── knowledge/             # 知识库
│       ├── address_knowledge.py # 地址库（RAG）
│       ├── poi_knowledge.py   # POI库
│       └── admin_division.py  # 行政区划
├── assistants/                # 智能体层
│   ├── parser.py              # 解析智能体
│   ├── normalizer.py          # 规范化智能体
│   ├── completion.py          # 补全智能体
│   ├── correction.py          # 纠错智能体
│   ├── standardizer.py        # 标准化智能体
│   ├── spatializer.py         # 空间化智能体
│   └── verifier.py            # 校验智能体
├── teams/                     # 协作层
│   └── address_governance_team.py # HMAS团队
├── workflows/                 # 工作流层
│   ├── address_pipeline.py    # 治理流水线
│   └── batch_processor.py     # 批量处理器
└── api/                       # 接口层
    ├── cli.py                 # CLI接口
    └── server.py              # FastAPI服务
```

## 🧪 测试用例

系统提供了多种类型的测试地址：

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

## 🔧 高级配置

### 分级处理配置

系统采用漏斗式分级处理策略，可在`.env`中配置比例：

```env
RULE_PROCESS_RATIO=0.40      # 40% 规则引擎
MODEL_PROCESS_RATIO=0.30     # 30% 轻量模型
ES_PROCESS_RATIO=0.15        # 15% ES检索
LLM_PROCESS_RATIO=0.15       # 15% LLM深度推理
```

### 幻觉抑制配置

```env
HALLUCINATION_CHECK_ENABLED=true
CONFIDENCE_THRESHOLD=0.80
GEOMETRY_CHECK_ENABLED=true
```

### RAG配置

```env
RAG_TOP_K=10
RAG_SCORE_THRESHOLD=0.85
RAG_RERANK_ENABLED=true
RAG_RERANK_TOP_K=5
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- 项目主页: https://github.com/306251708dd-gif/address_governance_agent
- 问题反馈: https://github.com/306251708dd-gif/address_governance_agent/issues

---

**基于丰图科技核心能力 | 精度99.8%+ | 百亿级规模**