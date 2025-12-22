"""
FastAPI服务 - RESTful API接口
提供HTTP API服务，支持单个和批量地址治理
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

from app.core import settings, get_logger
from app.workflows.address_pipeline import AddressPipeline, PipelineResult
from app.workflows.batch_processor import BatchProcessor, BatchConfig
from app.teams.address_governance_team import IntentType

logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="中文地址治理智能体系统",
    description="基于LLM+RAG的分层多智能体架构(HMAS)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
pipeline = AddressPipeline()
processor = BatchProcessor()

# 任务存储（简化实现，生产环境应使用Redis等）
tasks_store = {}


# ==================== 数据模型 ====================

class IntentEnum(str, Enum):
    """治理意图枚举"""
    parse = "parse"
    complete = "complete"
    correct = "correct"
    standardize = "standardize"
    spatialize = "spatialize"
    verify = "verify"
    full = "full"


class AddressRequest(BaseModel):
    """单个地址处理请求"""
    address: str = Field(..., description="待处理的地址", example="浙江省杭州市余杭区五常街道文一西路969号")
    intent: IntentEnum = Field(IntentEnum.full, description="治理意图")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class BatchAddressRequest(BaseModel):
    """批量地址处理请求"""
    addresses: List[str] = Field(..., description="地址列表", min_items=1, max_items=1000)
    intent: IntentEnum = Field(IntentEnum.full, description="治理意图")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    async_mode: bool = Field(False, description="是否异步处理")


class AddressResponse(BaseModel):
    """地址处理响应"""
    address_id: str
    original_address: str
    final_address: str
    coordinates: Dict[str, float] = {}
    confidence: float
    status: str
    steps_completed: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    duration_seconds: float


class BatchResponse(BaseModel):
    """批量处理响应"""
    task_id: Optional[str] = None
    results: Optional[List[AddressResponse]] = None
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    status: str = "completed"


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending/processing/completed/failed
    progress: float = 0.0
    total_count: int = 0
    completed_count: int = 0
    start_time: str
    end_time: Optional[str] = None


# ==================== API端点 ====================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "中文地址治理智能体系统",
        "version": "1.0.0",
        "description": "基于LLM+RAG的分层多智能体架构",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "llm": settings.LLM_MODEL_ID,
            "fengtu_api": settings.FENGTU_BASE_URL,
            "milvus": f"{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
            "elasticsearch": f"{settings.ES_HOST}:{settings.ES_PORT}"
        }
    }


@app.post("/api/v1/address/process", response_model=AddressResponse)
async def process_address(request: AddressRequest):
    """
    处理单个地址
    
    - **address**: 待处理的地址
    - **intent**: 治理意图（parse/complete/correct/standardize/spatialize/verify/full）
    - **context**: 可选的上下文信息
    """
    logger.info(f"收到地址处理请求: {request.address}")
    
    try:
        # 映射意图
        intent_map = {
            IntentEnum.parse: IntentType.PARSE,
            IntentEnum.complete: IntentType.COMPLETE,
            IntentEnum.correct: IntentType.CORRECT,
            IntentEnum.standardize: IntentType.STANDARDIZE,
            IntentEnum.spatialize: IntentType.SPATIALIZE,
            IntentEnum.verify: IntentType.VERIFY,
            IntentEnum.full: IntentType.FULL_PIPELINE
        }
        
        # 处理地址
        result = pipeline.process_single(
            request.address,
            context=request.context
        )
        
        # 转换响应
        response = AddressResponse(
            address_id=result.address_id,
            original_address=result.original_address,
            final_address=result.final_address,
            coordinates=result.coordinates,
            confidence=result.confidence,
            status=result.status,
            steps_completed=result.steps_completed,
            errors=result.errors,
            warnings=result.warnings,
            duration_seconds=result.duration_seconds
        )
        
        return response
    
    except Exception as e:
        logger.error(f"处理地址失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/address/batch", response_model=BatchResponse)
async def process_batch_addresses(
    request: BatchAddressRequest,
    background_tasks: BackgroundTasks
):
    """
    批量处理地址
    
    - **addresses**: 地址列表（最多1000个）
    - **intent**: 治理意图
    - **async_mode**: 是否异步处理（大批量建议使用）
    """
    logger.info(f"收到批量处理请求: {len(request.addresses)} 个地址")
    
    if len(request.addresses) > 1000:
        raise HTTPException(status_code=400, detail="单次批量处理最多支持1000个地址")
    
    try:
        if request.async_mode:
            # 异步处理
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            
            # 创建任务记录
            tasks_store[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "progress": 0.0,
                "total_count": len(request.addresses),
                "completed_count": 0,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "results": []
            }
            
            # 添加后台任务
            background_tasks.add_task(
                _process_batch_background,
                task_id,
                request.addresses,
                request.context
            )
            
            return BatchResponse(
                task_id=task_id,
                total_count=len(request.addresses),
                status="pending"
            )
        
        else:
            # 同步处理
            results = pipeline.process_batch(request.addresses, request.context)
            
            # 转换响应
            response_results = [
                AddressResponse(
                    address_id=r.address_id,
                    original_address=r.original_address,
                    final_address=r.final_address,
                    coordinates=r.coordinates,
                    confidence=r.confidence,
                    status=r.status,
                    steps_completed=r.steps_completed,
                    errors=r.errors,
                    warnings=r.warnings,
                    duration_seconds=r.duration_seconds
                )
                for r in results
            ]
            
            success_count = sum(1 for r in results if r.status == "success")
            failed_count = len(results) - success_count
            
            return BatchResponse(
                results=response_results,
                total_count=len(results),
                success_count=success_count,
                failed_count=failed_count,
                status="completed"
            )
    
    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    查询异步任务状态
    
    - **task_id**: 任务ID
    """
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_store[task_id]
    
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        total_count=task["total_count"],
        completed_count=task["completed_count"],
        start_time=task["start_time"],
        end_time=task["end_time"]
    )


@app.get("/api/v1/task/{task_id}/results")
async def get_task_results(task_id: str):
    """
    获取异步任务结果
    
    - **task_id**: 任务ID
    """
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_store[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {task['status']}")
    
    return {
        "task_id": task_id,
        "results": task["results"],
        "total_count": task["total_count"],
        "success_count": sum(1 for r in task["results"] if r["status"] == "success"),
        "failed_count": sum(1 for r in task["results"] if r["status"] == "failed")
    }


@app.get("/api/v1/config")
async def get_config():
    """获取系统配置信息"""
    return {
        "llm": {
            "model": settings.LLM_MODEL_ID,
            "base_url": settings.LLM_BASE_URL
        },
        "fengtu": {
            "base_url": settings.FENGTU_BASE_URL
        },
        "vector_db": {
            "host": settings.MILVUS_HOST,
            "port": settings.MILVUS_PORT,
            "collection_address": settings.MILVUS_COLLECTION_ADDRESS
        },
        "search_engine": {
            "host": settings.ES_HOST,
            "port": settings.ES_PORT,
            "index_address": settings.ES_INDEX_ADDRESS
        }
    }


# ==================== 后台任务函数 ====================

def _process_batch_background(task_id: str, addresses: List[str], context: Dict[str, Any]):
    """后台批量处理任务"""
    try:
        tasks_store[task_id]["status"] = "processing"
        
        results = pipeline.process_batch(addresses, context)
        
        # 转换结果
        result_dicts = [
            {
                "address_id": r.address_id,
                "original_address": r.original_address,
                "final_address": r.final_address,
                "coordinates": r.coordinates,
                "confidence": r.confidence,
                "status": r.status,
                "steps_completed": r.steps_completed,
                "errors": r.errors,
                "warnings": r.warnings,
                "duration_seconds": r.duration_seconds
            }
            for r in results
        ]
        
        # 更新任务状态
        tasks_store[task_id].update({
            "status": "completed",
            "progress": 1.0,
            "completed_count": len(results),
            "end_time": datetime.now().isoformat(),
            "results": result_dicts
        })
        
    except Exception as e:
        logger.error(f"后台任务失败 [{task_id}]: {e}")
        tasks_store[task_id].update({
            "status": "failed",
            "end_time": datetime.now().isoformat(),
            "error": str(e)
        })


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("启动地址治理智能体API服务")
    print("=" * 60)
    print(f"API文档: http://localhost:8000/docs")
    print(f"健康检查: http://localhost:8000/health")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
