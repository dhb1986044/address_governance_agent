"""
地址知识库 - RAG检索
基于Milvus向量数据库和Elasticsearch倒排索引
提供百亿级地址底座的快速检索能力
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterable

import httpx

from app.core import settings, get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """标准化的检索结果对象，用于三路检索与融合"""

    address: str
    score: float
    source: str
    location: Optional[Dict[str, float]] = None
    admin: Optional[Dict[str, str]] = None
    debug: Dict[str, Any] = field(default_factory=dict)


class ZhipuEmbeddingClient:
    """智谱向量模型客户端，用于生成真实向量或降级为伪向量"""

    def __init__(
        self,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.model_id = model_id or settings.EMBEDDING_MODEL_ID
        self.api_key = api_key or settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        self.base_url = base_url or settings.EMBEDDING_BASE_URL
        self.enabled = bool(self.api_key and self.base_url and self.model_id)

    def embed_query(self, text: str) -> List[float]:
        embeddings = self.embed_batch([text])
        return embeddings[0] if embeddings else []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.enabled:
            return []

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"input": texts, "model": self.model_id}

        try:
            response = httpx.post(
                f"{self.base_url}/embeddings",
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            return [item.get("embedding", []) for item in data]
        except Exception as exc:  # noqa: BLE001 - 需要捕获网络异常并降级
            logger.warning("调用智谱向量接口失败，降级为伪向量: %s", exc)
            return []


class LancedbAddressStore:
    """使用 LanceDB 的轻量地址底座，用于本地验证和集成测试"""

    TABLE_NAME = "address_knowledge"

    def __init__(self, uri: str, embedder: ZhipuEmbeddingClient, logger_ref) -> None:
        self.embedder = embedder
        self.logger = logger_ref
        self.available = False
        self.table = None

        try:
            import lancedb

            self.db = lancedb.connect(uri)
            self.available = True
        except Exception as exc:  # noqa: BLE001 - 初始化失败仅记录日志
            self.logger.warning("LanceDB 不可用，回退到模拟检索: %s", exc)
            self.available = False
            self.db = None

        if self.available and settings.LANCEDB_BOOTSTRAP_ENABLED:
            self.bootstrap_seed_data()

    @property
    def ready(self) -> bool:
        return bool(self.available and self.table)

    def bootstrap_seed_data(self) -> None:
        """创建并填充样例库，用于 Milvus/ES 缺席时的功能验证"""

        if not self.available:
            return

        if self.TABLE_NAME in self.db.table_names():
            self.table = self.db.open_table(self.TABLE_NAME)
            if self.table.count_rows() == 0:
                self._seed_table()
            return

        self.table = self.db.create_table(self.TABLE_NAME, data=self._build_seed_records())
        self.logger.info("LanceDB 已初始化样例库 (%s)", self.TABLE_NAME)

    def semantic_search(
        self, query_vector: List[float], top_k: int, filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        if not self.ready or not query_vector:
            return []

        try:
            results = (
                self.table.search(query_vector, query_type="vector", vector_column="embedding")
                .metric("cosine")
                .limit(top_k)
                .to_list()
            )
        except Exception as exc:  # noqa: BLE001 - 搜索失败时降级
            self.logger.warning("LanceDB 语义检索失败，将使用模拟数据: %s", exc)
            return []

        wrapped: List[SearchResult] = []
        for item in results:
            if not AddressKnowledge._match_filters_static(item, filters):  # noqa: SLF001
                continue
            distance = float(item.get("_distance", 0))
            wrapped.append(
                SearchResult(
                    address=item["address"],
                    score=max(0.0, 1.0 - distance),
                    source="lancedb-semantic",
                    location=item.get("location"),
                    admin=item.get("admin"),
                    debug={"table": self.TABLE_NAME},
                )
            )
        return wrapped

    def text_search(
        self, query: str, top_k: int, filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        if not self.ready:
            return []

        tokens = AddressKnowledge._tokenize(query)
        rows = self.table.to_list()
        scored: List[SearchResult] = []
        for item in rows:
            if not AddressKnowledge._match_filters_static(item, filters):  # noqa: SLF001
                continue
            overlap = tokens.intersection(set(item.get("tokens", [])))
            ratio = len(overlap) / (len(tokens) + 1e-5)
            if ratio == 0:
                continue
            scored.append(
                SearchResult(
                    address=item["address"],
                    score=ratio,
                    source="lancedb-text",
                    location=item.get("location"),
                    admin=item.get("admin"),
                    debug={"table": self.TABLE_NAME},
                )
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def _seed_table(self) -> None:
        self.table.add(self._build_seed_records())
        self.logger.info("LanceDB 样例库已写入 %s 条记录", self.table.count_rows())

    def _build_seed_records(self) -> List[Dict[str, Any]]:
        aoi_rows = [
            {
                "id": "00001669dea64500974d5354947a3d77",
                "province": "河北省",
                "city": "保定市",
                "county": "满城区",
                "town": "大册营镇",
                "name": "悦佳纸业",
                "fullname": "悦佳纸业",
            },
            {
                "id": "000385d8970c4456bad1dbf02e7f0745",
                "province": "河北省",
                "city": "保定市",
                "county": "阜平县",
                "town": "阜平镇",
                "name": "文化广电和旅游局",
                "fullname": "文化广电和旅游局",
            },
        ]

        village_rows = [
            {
                "cp": 1,
                "province": "河北省",
                "city": "保定市",
                "county": "涞源县",
                "town": "王安镇",
                "name": "孙草沟",
            },
            {
                "cp": 99,
                "province": "河北省",
                "city": "保定市",
                "county": "定州市",
                "town": "号头庄回族乡",
                "name": "圣佛头村民委员会",
            },
            {
                "cp": 99,
                "province": "河北省",
                "city": "保定市",
                "county": "涞水县",
                "town": "胡家庄乡",
                "name": "西武泉村民委员会",
            },
            {
                "cp": 1,
                "province": "河北省",
                "city": "保定市",
                "county": "唐县",
                "town": "川里镇",
                "name": "杨树湾",
            },
            {
                "cp": 1,
                "province": "河北省",
                "city": "保定市",
                "county": "安国市",
                "town": "南娄底乡",
                "name": "固城村",
            },
        ]

        def to_record(row: Dict[str, Any], source: str) -> Dict[str, Any]:
            admin = {
                "province": row["province"],
                "city": row["city"],
                "county": row["county"],
                "town": row.get("town"),
            }
            address_text = "".join(
                [
                    admin.get("province", ""),
                    admin.get("city", ""),
                    admin.get("county", ""),
                    admin.get("town", ""),
                    row.get("name", ""),
                ]
            )
            embedding = self.embedder.embed_query(address_text) or AddressKnowledge._synthetic_embedding_static(  # noqa: SLF001
                address_text
            )
            tokens = list(AddressKnowledge._tokenize(address_text))  # noqa: SLF001
            return {
                "address": address_text,
                "source": source,
                "embedding": embedding,
                "tokens": tokens,
                "admin": admin,
            }

        records = [to_record(row, "aoi") for row in aoi_rows]
        records.extend(to_record(row, "village") for row in village_rows)
        return records


class AddressKnowledge:
    """地址知识库 - 百亿级地址底座"""

    def __init__(self):
        """初始化地址知识库连接"""
        self.logger = get_logger(self.__class__.__name__)
        self.milvus_collection = settings.MILVUS_COLLECTION_ADDRESS
        self.es_index = settings.ES_INDEX_ADDRESS
        self.embedder = ZhipuEmbeddingClient()
        self.lancedb_store = LancedbAddressStore(settings.LANCEDB_URI, self.embedder, self.logger)
        self.logger.info("地址知识库已初始化")
    
    def search_by_semantic(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        语义向量检索
        
        Args:
            query: 查询地址
            top_k: 返回TopK结果
            filters: 过滤条件（如省市区限制）
        
        Returns:
            List[Dict]: 候选地址列表
        """
        self.logger.info(f"语义检索: {query} (TopK={top_k})")

        embedding = self._encode_query(query)

        if self.lancedb_store.ready:
            lancedb_results = self.lancedb_store.semantic_search(embedding, top_k * 2, filters)
            if lancedb_results:
                return lancedb_results[:top_k]

        candidates = self._mock_candidates()

        scored = []
        for item in candidates:
            if not self._match_filters(item, filters):
                continue
            similarity = self._cosine_similarity(embedding, item["embedding"])
            scored.append(
                SearchResult(
                    address=item["address"],
                    score=similarity,
                    source="semantic",
                    location=item.get("location"),
                    admin=item.get("admin"),
                    debug={"geohash": item.get("geohash"), "h3": item.get("h3")},
                )
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]
    
    def search_by_text(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        倒排索引检索
        
        Args:
            query: 查询地址
            top_k: 返回TopK结果
            filters: 过滤条件
        
        Returns:
            List[Dict]: 候选地址列表
        """
        self.logger.info(f"文本检索: {query} (TopK={top_k})")

        if self.lancedb_store.ready:
            lancedb_results = self.lancedb_store.text_search(query, top_k * 2, filters)
            if lancedb_results:
                return lancedb_results[:top_k]

        tokens = self._tokenize(query)
        candidates = self._mock_candidates()

        scored = []
        for item in candidates:
            if not self._match_filters(item, filters):
                continue
            overlap = tokens.intersection(item.get("tokens", set()))
            ratio = len(overlap) / (len(tokens) + 1e-5)
            scored.append(
                SearchResult(
                    address=item["address"],
                    score=ratio,
                    source="text",
                    location=item.get("location"),
                    admin=item.get("admin"),
                    debug={"geohash": item.get("geohash"), "h3": item.get("h3")},
                )
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.6,
        text_weight: float = 0.4,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        混合检索（语义+文本）
        
        Args:
            query: 查询地址
            top_k: 返回TopK结果
            semantic_weight: 语义检索权重
            text_weight: 文本检索权重
            filters: 过滤条件
        
        Returns:
            List[Dict]: 候选地址列表
        """
        self.logger.info(f"混合检索: {query}")
        
        semantic_results = self.search_by_semantic(query, top_k * 2, filters)
        text_results = self.search_by_text(query, top_k * 2, filters)
        spatial_results = self._spatial_boost(semantic_results + text_results, filters)

        # RRF融合
        fused = self._rrf_fusion(
            [semantic_results, text_results, spatial_results],
            weights=[semantic_weight, text_weight, 1.0],
        )

        # Cross-Encoder重排（使用轻量级字符串相似度代替真实模型）
        if settings.RAG_RERANK_ENABLED:
            fused = self._rerank_with_cross_encoder(fused, query)

        # 返回TopK，附带调试信息
        results = [
            {
                "address": item.address,
                "score": item.score,
                "source": item.source,
                "admin": item.admin,
                "location": item.location,
                "debug": item.debug,
            }
            for item in fused[:top_k]
        ]
        return results
    
    def get_standard_address(self, address_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取标准地址详情
        
        Args:
            address_id: 地址唯一标识
        
        Returns:
            Optional[Dict]: 地址详情
        """
        # TODO: 实现从数据库获取完整地址信息
        return None

    # ==================== 内部工具方法 ====================

    def _encode_query(self, query: str) -> List[float]:
        """向量编码，优先调用智谱embedding，失败则退化为伪向量"""

        embedding = self.embedder.embed_query(query)
        if embedding:
            return embedding
        return self._synthetic_embedding(query)

    def _synthetic_embedding(self, text: str) -> List[float]:
        return self._synthetic_embedding_static(text)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _synthetic_embedding_static(text: str, dim: Optional[int] = None) -> List[float]:
        seed = sum(ord(c) for c in text)
        dimension = dim or min(settings.EMBEDDING_DIMENSION or 0, 128) or 64
        return [((seed + i * 31) % 100) / 100 for i in range(dimension)]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        cleaned = text.replace("号", " ").replace("\n", " ")
        return set(filter(None, cleaned.split()))

    def _match_filters(self, item: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        return self._match_filters_static(item, filters)

    @staticmethod
    def _match_filters_static(item: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        if not filters:
            return True

        admin = item.get("admin", {})
        if province := filters.get("province"):
            if admin.get("province") != province:
                return False
        if city := filters.get("city"):
            if admin.get("city") != city:
                return False
        if geohash := filters.get("geohash"):
            if item.get("geohash") != geohash:
                return False
        if h3 := filters.get("h3"):
            if item.get("h3") != h3:
                return False

        # 简单矩形范围过滤
        if bbox := filters.get("bbox"):
            lon, lat = item.get("location", {}).get("lon"), item.get("location", {}).get("lat")
            if lon is None or lat is None:
                return False
            min_lon, min_lat, max_lon, max_lat = bbox
            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                return False

        return True

    def _spatial_boost(
        self, results: Iterable[SearchResult], filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """基于地理约束的加权，模拟GeoHash/H3空间过滤"""

        if not filters:
            return []

        boosted: List[SearchResult] = []
        for item in results:
            if not item.location:
                continue
            if not self._match_filters(
                {
                    "admin": item.admin,
                    "geohash": item.debug.get("geohash"),
                    "h3": item.debug.get("h3"),
                    "location": item.location,
                },
                filters,
            ):
                continue

            distance_penalty = self._distance_penalty(item.location, filters)
            boosted.append(
                SearchResult(
                    address=item.address,
                    score=item.score * distance_penalty,
                    source="spatial",
                    location=item.location,
                    admin=item.admin,
                    debug=item.debug,
                )
            )

        boosted.sort(key=lambda r: r.score, reverse=True)
        return boosted

    def _distance_penalty(self, location: Dict[str, float], filters: Dict[str, Any]) -> float:
        if not location:
            return 1.0
        target = filters.get("center")
        if not target:
            return 1.0

        # 计算近似球面距离（Haversine 简化版）
        lat1, lon1 = math.radians(location.get("lat", 0)), math.radians(location.get("lon", 0))
        lat2, lon2 = math.radians(target.get("lat", 0)), math.radians(target.get("lon", 0))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        earth_radius_km = 6371
        distance_km = earth_radius_km * c

        # 5km 内全权重，线性衰减到 20km
        if distance_km <= 5:
            return 1.2
        if distance_km >= 20:
            return 0.7
        return 1.2 - (distance_km - 5) * 0.033

    def _rrf_fusion(
        self, result_lists: List[List[SearchResult]], weights: Optional[List[float]] = None, k: int = 60
    ) -> List[SearchResult]:
        """Reciprocal Rank Fusion，实现多路检索结果融合"""

        weights = weights or [1.0] * len(result_lists)
        fused: Dict[str, SearchResult] = {}

        for weight, results in zip(weights, result_lists):
            for rank, item in enumerate(results, start=1):
                rrf_score = weight * (1.0 / (k + rank))
                if item.address not in fused:
                    fused[item.address] = SearchResult(
                        address=item.address,
                        score=rrf_score,
                        source=item.source,
                        location=item.location,
                        admin=item.admin,
                        debug=item.debug.copy(),
                    )
                else:
                    fused[item.address].score += rrf_score
                    fused[item.address].debug[item.source] = rrf_score

        return sorted(fused.values(), key=lambda r: r.score, reverse=True)

    def _rerank_with_cross_encoder(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """基于轻量级相似度的重排序，代替真实Cross-Encoder"""

        def similarity(a: str, b: str) -> float:
            a_tokens = set(a)
            b_tokens = set(b)
            return len(a_tokens.intersection(b_tokens)) / (len(a_tokens) + 1e-5)

        reranked = []
        for idx, item in enumerate(results, start=1):
            rerank_score = similarity(query, item.address)
            # 结合RRF分数，突出上下文匹配且距离近的结果
            combined = 0.7 * rerank_score + 0.3 * item.score
            reranked.append(
                SearchResult(
                    address=item.address,
                    score=combined,
                    source=f"{item.source}+rerank",
                    location=item.location,
                    admin=item.admin,
                    debug={**item.debug, "rrf_score": item.score, "rerank_score": rerank_score},
                )
            )

        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked

    def _mock_candidates(self) -> List[Dict[str, Any]]:
        """模拟底座数据，包含语义/文本/空间编码"""

        return [
            {
                "address": "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
                "embedding": [0.9, 0.85, 0.88, 0.80, 0.76, 0.81, 0.79, 0.75],
                "tokens": self._tokenize("文一西路969 西溪园区 5号楼"),
                "geohash": "wtm6j8",
                "h3": "8a2a1072d59ffff",
                "location": {"lat": 30.2749, "lon": 120.0934},
                "admin": {"province": "浙江省", "city": "杭州市", "district": "余杭区"},
            },
            {
                "address": "浙江省杭州市西湖区文一西路969号中国电信大楼",
                "embedding": [0.82, 0.80, 0.83, 0.78, 0.74, 0.77, 0.75, 0.70],
                "tokens": self._tokenize("文一西路 969 电信"),
                "geohash": "wtm6j7",
                "h3": "8a2a1072d597fff",
                "location": {"lat": 30.2752, "lon": 120.0928},
                "admin": {"province": "浙江省", "city": "杭州市", "district": "西湖区"},
            },
            {
                "address": "北京市海淀区中关村大街27号中关村创业大厦",
                "embedding": [0.40, 0.42, 0.41, 0.39, 0.40, 0.38, 0.41, 0.39],
                "tokens": self._tokenize("中关村 大街27号 创业大厦"),
                "geohash": "wx4g0f",
                "h3": "89c2849058fffff",
                "location": {"lat": 39.9834, "lon": 116.3152},
                "admin": {"province": "北京市", "city": "北京市", "district": "海淀区"},
            },
        ]


# 创建全局实例
address_knowledge = AddressKnowledge()


if __name__ == "__main__":
    """测试地址知识库"""
    print("=" * 80)
    print("测试地址知识库")
    print("=" * 80)
    
    kb = AddressKnowledge()
    
    test_query = "文一西路969号"
    
    print(f"\n查询: {test_query}")
    print("\n1. 语义检索:")
    results = kb.search_by_semantic(test_query, top_k=3)
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['address']} (得分: {result['score']:.2f})")
    
    print("\n2. 文本检索:")
    results = kb.search_by_text(test_query, top_k=3)
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['address']} (得分: {result['score']:.2f})")
    
    print("\n3. 混合检索:")
    results = kb.hybrid_search(test_query, top_k=5)
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['address']} (得分: {result['score']:.2f})")
    
    print("\n" + "=" * 80)
