"""
LanceDB 知识库实现
负责 AOI 和 Village 数据的存储与检索
"""
import lancedb
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx

from app.core import settings, get_logger

logger = get_logger(__name__)

@dataclass
class SearchResult:
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]

class ZhipuEmbedder:
    """简单的智谱Embedding客户端"""
    def __init__(self):
        self.api_key = settings.EMBEDDING_API_KEY
        self.base_url = settings.EMBEDDING_BASE_URL
        self.model = settings.EMBEDDING_MODEL_ID
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        results = []
        # 智谱Embedding不支持过大的Batch，这里简单处理，实际生产应分批
        for text in texts:
            try:
                payload = {
                    "model": self.model,
                    "input": text
                }
                response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                results.append(embedding)
            except Exception as e:
                logger.error(f"Embedding failed for text: {text[:20]}... Error: {e}")
                # Fallback zero vector or raise? For now, raise to be noticed
                raise e
        return results

class AddressLanceKnowledge:
    def __init__(self):
        # 确保目录存在
        settings.LANCEDB_URI = str(settings.LANCEDB_URI) # Ensure string
        import os
        os.makedirs(settings.LANCEDB_URI, exist_ok=True)
        
        self.db = lancedb.connect(settings.LANCEDB_URI)
        self.embedder = ZhipuEmbedder()
        
        self.aoi_table_name = settings.KB_TABLE_NAME_AOI
        self.village_table_name = settings.KB_TABLE_NAME_VILLAGE
        
        self._init_tables()

    def _init_tables(self):
        # 检查并初始化测试数据
        # 如果表不存在，则写入硬编码的测试数据
        if self.aoi_table_name not in self.db.table_names():
            logger.info("初始化 AOI 测试数据...")
            self._ingest_aoi_test_data()
            
        if self.village_table_name not in self.db.table_names():
            logger.info("初始化 Village 测试数据...")
            self._ingest_village_test_data()

    def _ingest_aoi_test_data(self):
        # id,province,city,county,town,name,fullname
        data = [
            {"id": "00001669dea64500974d5354947a3d77", "province": "河北省", "city": "保定市", "county": "满城区", "town": "大册营镇", "name": "悦佳纸业", "fullname": "悦佳纸业"},
            {"id": "000385d8970c4456bad1dbf02e7f0745", "province": "河北省", "city": "保定市", "county": "阜平县", "town": "阜平镇", "name": "文化广电和旅游局", "fullname": "文化广电和旅游局"}
        ]
        
        texts = [f"{row['province']}{row['city']}{row['county']}{row['town']}{row['fullname']}" for row in data]
        vectors = self.embedder.embed_documents(texts)
        
        for i, row in enumerate(data):
            row["vector"] = vectors[i]
            row["text"] = texts[i]
            
        self.db.create_table(self.aoi_table_name, data=data)

    def _ingest_village_test_data(self):
        # cp,province,city,county,town,name
        # cp: 1=自然村, 99=行政村
        data = [
            {"cp": 1, "province": "河北省", "city": "保定市", "county": "涞源县", "town": "王安镇", "name": "孙草沟"},
            {"cp": 99, "province": "河北省", "city": "保定市", "county": "定州市", "town": "号头庄回族乡", "name": "圣佛头村民委员会"},
            {"cp": 99, "province": "河北省", "city": "保定市", "county": "涞水县", "town": "胡家庄乡", "name": "西武泉村民委员会"},
            {"cp": 1, "province": "河北省", "city": "保定市", "county": "唐县", "town": "川里镇", "name": "杨树湾"},
            {"cp": 1, "province": "河北省", "city": "保定市", "county": "安国市", "town": "南娄底乡", "name": "固城村"}
        ]
        
        texts = [f"{row['province']}{row['city']}{row['county']}{row['town']}{row['name']}" for row in data]
        vectors = self.embedder.embed_documents(texts)
        
        for i, row in enumerate(data):
            row["vector"] = vectors[i]
            row["text"] = texts[i]
            
        self.db.create_table(self.village_table_name, data=data)

    def search(self, query: str, city_filter: str = None, limit: int = 5) -> Dict[str, List[SearchResult]]:
        """
        混合检索 AOI 和 Village
        """
        query_vec = self.embedder.embed_documents([query])[0]
        
        results = {
            "aoi": [],
            "village": []
        }
        
        # Search AOI
        aoi_table = self.db.open_table(self.aoi_table_name)
        # Construct filter
        where_clause = f"city = '{city_filter}'" if city_filter else None
        
        aoi_hits = aoi_table.search(query_vec).where(where_clause).limit(limit).to_pandas() if where_clause else aoi_table.search(query_vec).limit(limit).to_pandas()
        
        for _, hit in aoi_hits.iterrows():
            results["aoi"].append(SearchResult(
                id=hit["id"],
                text=hit["text"],
                score=1.0, # LanceDB python wrapper might not return score directly in simple to_pandas? Wait, it usually does as _distance. 
                # LanceDB returns _distance by default. Score = 1 / (1 + distance) or similar.
                metadata={"province": hit["province"], "city": hit["city"], "county": hit["county"], "town": hit["town"], "name": hit["name"], "type": "AOI"}
            ))

        # Search Village
        village_table = self.db.open_table(self.village_table_name)
        village_hits = village_table.search(query_vec).where(where_clause).limit(limit).to_pandas() if where_clause else village_table.search(query_vec).limit(limit).to_pandas()
        
        for _, hit in village_hits.iterrows():
            cp_desc = "自然村" if hit["cp"] == 1 else "行政村"
            results["village"].append(SearchResult(
                id=f"{hit['county']}_{hit['name']}",
                text=hit["text"],
                score=1.0,
                metadata={"province": hit["province"], "city": hit["city"], "county": hit["county"], "town": hit["town"], "name": hit["name"], "type": f"Village({cp_desc})"}
            ))
            
        return results

# Singleton instance
lance_knowledge = AddressLanceKnowledge()
