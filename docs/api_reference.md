# API参考文档

## REST API

### 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

### 端点列表

#### 1. 健康检查

**GET** `/health`

检查服务健康状态。

**响应示例**：
```json
{
  "status": "healthy",
  "timestamp": "2024-12-22T10:30:00",
  "services": {
    "llm": "qwen-plus",
    "fengtu_api": "https://api.fengtu.com",
    "milvus": "localhost:19530",
    "elasticsearch": "localhost:9200"
  }
}
```

#### 2. 处理单个地址

**POST** `/api/v1/address/process`

处理单个地址，返回治理结果。

**请求体**：
```json
{
  "address": "浙江省杭州市余杭区五常街道文一西路969号",
  "intent": "full",
  "context": {}
}
```

**参数说明**：
- `address` (string, required): 待处理的地址
- `intent` (string, optional): 治理意图，可选值：
  - `parse`: 仅解析
  - `complete`: 仅补全
  - `correct`: 仅纠错
  - `standardize`: 仅标准化
  - `spatialize`: 仅空间化
  - `verify`: 仅校验
  - `full`: 完整流程（默认）
- `context` (object, optional): 上下文信息

**响应示例**：
```json
{
  "address_id": "addr_a1b2c3d4",
  "original_address": "浙江省杭州市余杭区五常街道文一西路969号",
  "final_address": "浙江省杭州市余杭区五常街道文一西路969号",
  "coordinates": {
    "longitude": 120.023456,
    "latitude": 30.275678
  },
  "confidence": 0.95,
  "status": "success",
  "steps_completed": ["规范化", "解析", "纠错", "补全", "标准化", "空间化", "校验"],
  "errors": [],
  "warnings": [],
  "duration_seconds": 2.34
}
```

#### 3. 批量处理地址

**POST** `/api/v1/address/batch`

批量处理多个地址。

**请求体**：
```json
{
  "addresses": [
    "地址1",
    "地址2",
    "地址3"
  ],
  "intent": "full",
  "context": {},
  "async_mode": false
}
```

**参数说明**：
- `addresses` (array, required): 地址列表，最多1000个
- `intent` (string, optional): 治理意图，同上
- `context` (object, optional): 上下文信息
- `async_mode` (boolean, optional): 是否异步处理，默认false

**同步响应示例** (async_mode=false):
```json
{
  "task_id": null,
  "results": [
    {
      "address_id": "batch_1",
      "original_address": "地址1",
      "final_address": "标准化地址1",
      "confidence": 0.92,
      "status": "success",
      ...
    }
  ],
  "total_count": 3,
  "success_count": 2,
  "failed_count": 1,
  "status": "completed"
}
```

**异步响应示例** (async_mode=true):
```json
{
  "task_id": "task_xyz123abc456",
  "total_count": 3,
  "status": "pending"
}
```

#### 4. 查询异步任务状态

**GET** `/api/v1/task/{task_id}`

查询异步批量处理任务的状态。

**响应示例**：
```json
{
  "task_id": "task_xyz123abc456",
  "status": "processing",
  "progress": 0.67,
  "total_count": 100,
  "completed_count": 67,
  "start_time": "2024-12-22T10:00:00",
  "end_time": null
}
```

**状态值**：
- `pending`: 等待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败

#### 5. 获取异步任务结果

**GET** `/api/v1/task/{task_id}/results`

获取已完成的异步任务结果。

**响应示例**：
```json
{
  "task_id": "task_xyz123abc456",
  "results": [...],
  "total_count": 100,
  "success_count": 95,
  "failed_count": 5
}
```

#### 6. 获取系统配置

**GET** `/api/v1/config`

获取系统配置信息。

**响应示例**：
```json
{
  "llm": {
    "model": "qwen-plus",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
  },
  "fengtu": {
    "base_url": "https://api.fengtu.com"
  },
  "vector_db": {
    "host": "localhost",
    "port": 19530,
    "collection_address": "fengtu_address_standard"
  },
  "search_engine": {
    "host": "localhost",
    "port": 9200,
    "index_address": "address_inverted"
  }
}
```

### 错误响应

所有错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

**常见错误码**：
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

---

## CLI命令行接口

### 安装

```bash
pip install -e .
```

安装后，`address-cli`命令全局可用。

### 命令列表

#### 1. process - 处理单个地址

```bash
address-cli process <address> [OPTIONS]
```

**选项**：
- `--intent`: 治理意图（parse/complete/correct/standardize/spatialize/verify/full）
- `-o, --output`: 输出文件路径（JSON格式）
- `-v, --verbose`: 详细输出

**示例**：
```bash
# 基本用法
address-cli process "浙江省杭州市余杭区五常街道文一西路969号"

# 仅纠错
address-cli process "杭州市余航区" --intent correct

# 保存结果到文件
address-cli process "文一西路969号" --intent complete -o result.json

# 详细输出
address-cli process "阿里西溪" -v
```

#### 2. batch - 批量处理文件

```bash
address-cli batch <input_file> <output_file> [OPTIONS]
```

**选项**：
- `--column`: 地址列名（默认: address）
- `--format`: 文件格式（csv/excel，默认: csv）
- `--workers`: 并发数（默认: 10）
- `--batch-size`: 批次大小（默认: 100）

**示例**：
```bash
# 处理CSV文件
address-cli batch input.csv output.csv

# 处理Excel文件
address-cli batch input.xlsx output.xlsx --format excel

# 自定义并发数
address-cli batch data.csv result.csv --workers 20 --batch-size 50
```

#### 3. multi - 处理多个地址

```bash
address-cli multi <address1> <address2> ... [OPTIONS]
```

**选项**：
- `-o, --output`: 输出文件路径

**示例**：
```bash
address-cli multi "地址1" "地址2" "地址3"

address-cli multi "地址1" "地址2" -o results.json
```

#### 4. config - 显示配置

```bash
address-cli config
```

显示当前系统配置信息。

#### 5. test - 运行测试

```bash
address-cli test
```

运行内置测试用例。

---

## Python SDK

### 基础用法

#### 1. 单个地址处理

```python
from app.workflows.address_pipeline import AddressPipeline

# 创建流水线
pipeline = AddressPipeline()

# 处理地址
result = pipeline.process_single("浙江省杭州市余杭区五常街道文一西路969号")

# 访问结果
print(f"原始地址: {result.original_address}")
print(f"最终地址: {result.final_address}")
print(f"置信度: {result.confidence:.2f}")
print(f"坐标: {result.coordinates}")
print(f"状态: {result.status}")
```

#### 2. 批量处理

```python
from app.workflows.address_pipeline import AddressPipeline

pipeline = AddressPipeline()

addresses = [
    "文一西路969号",
    "杭州市余航区",
    "阿里西溪园区"
]

results = pipeline.process_batch(addresses)

for r in results:
    print(f"{r.original_address} → {r.final_address} ({r.confidence:.2f})")
```

#### 3. 高级并发处理

```python
from app.workflows.batch_processor import BatchProcessor, BatchConfig

# 配置
config = BatchConfig(
    batch_size=100,
    max_workers=20,
    use_process=False,  # 使用多线程
    timeout=300,
    retry_count=3
)

# 创建处理器
processor = BatchProcessor(config)

# 并发处理
results = processor.process_concurrent(addresses)
```

#### 4. 文件处理

```python
from app.workflows.batch_processor import BatchProcessor

processor = BatchProcessor()

# 处理CSV/Excel文件
stats = processor.process_large_file(
    input_file="input.csv",
    output_file="output.csv",
    address_column="address",
    file_format="csv"
)

print(f"成功: {stats['success_count']}")
print(f"失败: {stats['failed_count']}")
print(f"平均置信度: {stats['avg_confidence']:.2f}")
```

#### 5. 使用智能体团队

```python
from app.teams.address_governance_team import AddressGovernanceTeam, IntentType

# 创建团队
team = AddressGovernanceTeam()

# 指定意图治理
result = team.govern_address(
    address="杭州市余航区",
    intent=IntentType.CORRECT  # 仅纠错
)

# 完整流程
result = team.govern_address(
    address="文一西路969号",
    intent=IntentType.FULL_PIPELINE,
    context={"hint": "杭州地区"}
)
```

#### 6. 单独使用智能体

```python
from app.assistants.parser import parse_address
from app.assistants.correction import correct_address
from app.assistants.completion import complete_address

# 地址解析
parse_result = parse_address("浙江省杭州市余杭区文一西路969号")

# 地址纠错
correct_result = correct_address("杭州市余航区")

# 地址补全
complete_result = complete_address("文一西路969号")
```

---

## 数据模型

### PipelineResult

地址处理结果对象。

**属性**：
- `address_id` (str): 地址唯一标识
- `original_address` (str): 原始地址
- `final_address` (str): 最终标准化地址
- `coordinates` (dict): 经纬度坐标
- `confidence` (float): 置信度 (0-1)
- `status` (str): 状态（success/failed/manual_review）
- `steps_completed` (list): 已完成的处理步骤
- `errors` (list): 错误列表
- `warnings` (list): 警告列表
- `metadata` (dict): 元数据
- `duration_seconds` (float): 处理耗时（秒）

### BatchConfig

批量处理配置对象。

**属性**：
- `batch_size` (int): 每批次大小，默认100
- `max_workers` (int): 最大并发数，默认10
- `use_process` (bool): 是否使用多进程，默认False
- `timeout` (int): 超时时间（秒），默认300
- `retry_count` (int): 重试次数，默认3
- `enable_progress` (bool): 是否显示进度，默认True

---

**文档版本**: 1.0.0  
**更新日期**: 2024-12-22
