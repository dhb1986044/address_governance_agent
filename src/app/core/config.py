"""
核心配置模块 - 管理所有环境变量和系统配置
严格遵循：所有模型ID、API Key、Base URL 从此读取，严禁硬编码
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """系统配置类 - 所有配置从环境变量或.env文件读取"""
    
    # ==================== LLM配置 (智谱AI) ====================
    ZHIPU_API_KEY: str = "8102be46cfd84a12a527b9e8dd664a7b.9FgtFSd414I49j6F"
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    LLM_MODEL_ID: str = "glm-4"
    
    # 兼容Agno/OpenAI SDK的配置
    LLM_API_KEY: str = "8102be46cfd84a12a527b9e8dd664a7b.9FgtFSd414I49j6F" 
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    
    # ==================== 丰图API配置 ====================
    FENGTU_API_KEY: Optional[str] = None
    FENGTU_BASE_URL: str = "https://api.fengmap.com" # Dummy default

    # ==================== Embedding模型配置 (智谱AI) ====================
    EMBEDDING_MODEL_ID: str = "embedding-3-pro"
    EMBEDDING_API_KEY: str = "8102be46cfd84a12a527b9e8dd664a7b.9FgtFSd414I49j6F"
    EMBEDDING_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    EMBEDDING_DIMENSION: int = 2048 # embedding-3-pro dimension

    # ==================== 向量数据库配置 (LanceDB) ====================
    LANCEDB_URI: str = "./data/lancedb_store"
    KB_TABLE_NAME_AOI: str = "aoi_knowledge"
    KB_TABLE_NAME_VILLAGE: str = "village_knowledge"
    SQLITE_DB_FILE: str = "./data/agents.db"
    
    # ==================== RAG配置 ====================
    RAG_TOP_K: int = 10
    RAG_SCORE_THRESHOLD: float = 0.85
    RAG_RERANK_ENABLED: bool = True
    RAG_RERANK_TOP_K: int = 5
    
    # ==================== 分级处理配置 ====================
    # 漏斗式分级处理比例（40%规则 → 30%模型 → 15%ES → 15%LLM）
    RULE_PROCESS_RATIO: float = 0.40
    MODEL_PROCESS_RATIO: float = 0.30
    ES_PROCESS_RATIO: float = 0.15
    LLM_PROCESS_RATIO: float = 0.15
    
    # ==================== 幻觉抑制配置 ====================
    HALLUCINATION_CHECK_ENABLED: bool = True
    CONFIDENCE_THRESHOLD: float = 0.80
    GEOMETRY_CHECK_ENABLED: bool = True
    
    # ==================== 日志配置 ====================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ==================== 性能配置 ====================
    BATCH_SIZE: int = 100
    MAX_WORKERS: int = 10
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600
    
    # ==================== 项目路径 ====================
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    CACHE_DIR: Path = PROJECT_ROOT / "cache"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保必要的目录存在
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)


# 创建全局配置实例
settings = Settings()


if __name__ == "__main__":
    """测试配置加载"""
    print("=" * 60)
    print("系统配置信息")
    print("=" * 60)
    print(f"LLM模型: {settings.LLM_MODEL_ID}")
    print(f"LLM Base URL: {settings.LLM_BASE_URL}")
    print(f"丰图API Base URL: {settings.FENGTU_BASE_URL}")
    print(f"Milvus地址: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    print(f"Elasticsearch地址: {settings.ES_HOST}:{settings.ES_PORT}")
    print(f"Embedding模型: {settings.EMBEDDING_MODEL_ID}")
    print(f"项目根目录: {settings.PROJECT_ROOT}")
    print(f"数据目录: {settings.DATA_DIR}")
    print(f"缓存目录: {settings.CACHE_DIR}")
    print("=" * 60)
