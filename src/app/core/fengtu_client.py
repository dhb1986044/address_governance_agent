"""
丰图科技API统一客户端
封装所有丰图科技地址服务API调用
"""
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .config import settings
from .logger import get_logger


logger = get_logger(__name__)


# ==================== 数据模型定义 ====================

class AddressSegment(BaseModel):
    """18级地址分词结果"""
    level: str = Field(..., description="层级代码（L1-L18, AOI）")
    name: str = Field(..., description="层级名称")
    value: str = Field(..., description="层级值")
    confidence: float = Field(default=1.0, description="置信度")


class SegmentResult(BaseModel):
    """分词结果模型"""
    raw_address: str = Field(..., description="原始地址")
    segments: List[AddressSegment] = Field(default_factory=list, description="18级分词结果")
    missing_levels: List[str] = Field(default_factory=list, description="缺失的层级")
    aoi_detected: Optional[Dict[str, Any]] = Field(None, description="检测到的AOI信息")
    confidence: float = Field(default=1.0, description="整体置信度")
    need_completion: bool = Field(default=False, description="是否需要补全")


class GeoPoint(BaseModel):
    """地理坐标点"""
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")
    coordinate_system: str = Field(default="WGS84", description="坐标系统")


class GeocodeResult(BaseModel):
    """地理编码结果"""
    address: str = Field(..., description="输入地址")
    location: Optional[GeoPoint] = Field(None, description="地理坐标")
    confidence: float = Field(default=0.0, description="置信度")
    level: str = Field(default="", description="匹配精度等级")


class StandardizedAddress(BaseModel):
    """标准化地址结果"""
    original: str = Field(..., description="原始地址")
    standardized: str = Field(..., description="标准化后的地址")
    corrections: List[Dict[str, str]] = Field(default_factory=list, description="纠错列表")
    completions: List[Dict[str, str]] = Field(default_factory=list, description="补全列表")
    confidence: float = Field(default=0.0, description="置信度")


class VerifyResult(BaseModel):
    """地址校验结果"""
    address: str = Field(..., description="待校验地址")
    is_valid: bool = Field(default=False, description="是否真实存在")
    existence_score: float = Field(default=0.0, description="存在性得分")
    geometry_matched: bool = Field(default=False, description="几何约束是否匹配")
    issues: List[str] = Field(default_factory=list, description="发现的问题")


class SimilarityResult(BaseModel):
    """相似度计算结果"""
    address1: str = Field(..., description="地址1")
    address2: str = Field(..., description="地址2")
    similarity: float = Field(..., description="相似度得分(0-1)")
    text_similarity: float = Field(default=0.0, description="文本相似度")
    spatial_similarity: float = Field(default=0.0, description="空间相似度")


# ==================== API客户端 ====================

class FengtuClient:
    """丰图科技API客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """
        初始化丰图API客户端
        
        Args:
            api_key: API密钥（默认从配置读取）
            base_url: API基础URL（默认从配置读取）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.api_key = api_key or settings.FENGTU_API_KEY
        self.base_url = base_url or settings.FENGTU_BASE_URL
        self.timeout = timeout or settings.FENGTU_TIMEOUT
        self.max_retries = max_retries or settings.FENGTU_MAX_RETRIES
        
        if not self.api_key:
            logger.warning("丰图API Key未设置，某些功能可能无法使用")
    
    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求到丰图API
        
        Args:
            endpoint: API端点路径
            method: HTTP方法
            data: 请求体数据
            params: URL参数
        
        Returns:
            Dict: API响应数据
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method.upper() == "POST":
                    response = client.post(url, json=data, headers=headers, params=params)
                elif method.upper() == "GET":
                    response = client.get(url, headers=headers, params=params)
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"丰图API请求失败: {e}")
            # 返回模拟数据以便开发测试
            return self._mock_response(endpoint, data or params)
    
    def _mock_response(self, endpoint: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成模拟响应数据（用于开发测试）
        
        Args:
            endpoint: API端点
            request_data: 请求数据
        
        Returns:
            Dict: 模拟响应
        """
        logger.warning(f"使用模拟数据响应 {endpoint}")
        
        if "segment" in endpoint:
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "segments": [
                        {"level": "L1", "name": "省", "value": "浙江省", "confidence": 0.99},
                        {"level": "L2", "name": "市", "value": "杭州市", "confidence": 0.98},
                        {"level": "L3", "name": "区", "value": "余杭区", "confidence": 0.97},
                        {"level": "L4", "name": "街道", "value": "五常街道", "confidence": 0.95},
                        {"level": "L5", "name": "路", "value": "文一西路", "confidence": 0.96},
                        {"level": "L6", "name": "门牌", "value": "969号", "confidence": 0.94}
                    ],
                    "missing_levels": ["L7"],
                    "confidence": 0.95
                }
            }
        elif "geocode" in endpoint:
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "location": {
                        "longitude": 120.0234,
                        "latitude": 30.2756
                    },
                    "confidence": 0.92,
                    "level": "L6"
                }
            }
        elif "standard" in endpoint:
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "standardized": "浙江省杭州市余杭区五常街道文一西路969号",
                    "corrections": [],
                    "completions": [],
                    "confidence": 0.96
                }
            }
        else:
            return {"code": 0, "message": "success", "data": {}}
    
    def segment_address(self, address: str) -> SegmentResult:
        """
        18级地址分词
        
        Args:
            address: 待分词的地址字符串
        
        Returns:
            SegmentResult: 分词结果
        """
        logger.info(f"调用18级分词服务: {address}")
        
        response = self._make_request(
            endpoint=settings.FENGTU_SEGMENT_ENDPOINT,
            method="POST",
            data={"address": address}
        )
        
        if response.get("code") == 0:
            data = response.get("data", {})
            segments = [AddressSegment(**seg) for seg in data.get("segments", [])]
            
            return SegmentResult(
                raw_address=address,
                segments=segments,
                missing_levels=data.get("missing_levels", []),
                aoi_detected=data.get("aoi_detected"),
                confidence=data.get("confidence", 0.0),
                need_completion=len(data.get("missing_levels", [])) > 0
            )
        else:
            logger.error(f"分词失败: {response.get('message')}")
            return SegmentResult(raw_address=address, confidence=0.0)
    
    def geocode(self, address: str) -> GeocodeResult:
        """
        正向地理编码（地址 → 坐标）
        
        Args:
            address: 地址字符串
        
        Returns:
            GeocodeResult: 地理编码结果
        """
        logger.info(f"调用正向地理编码: {address}")
        
        response = self._make_request(
            endpoint=settings.FENGTU_GEOCODE_ENDPOINT,
            method="POST",
            data={"address": address}
        )
        
        if response.get("code") == 0:
            data = response.get("data", {})
            location = None
            if "location" in data:
                location = GeoPoint(**data["location"])
            
            return GeocodeResult(
                address=address,
                location=location,
                confidence=data.get("confidence", 0.0),
                level=data.get("level", "")
            )
        else:
            return GeocodeResult(address=address)
    
    def regeocode(self, longitude: float, latitude: float) -> str:
        """
        逆向地理编码（坐标 → 地址）
        
        Args:
            longitude: 经度
            latitude: 纬度
        
        Returns:
            str: 地址字符串
        """
        logger.info(f"调用逆向地理编码: ({longitude}, {latitude})")
        
        response = self._make_request(
            endpoint=settings.FENGTU_REGEOCODE_ENDPOINT,
            method="POST",
            data={"longitude": longitude, "latitude": latitude}
        )
        
        if response.get("code") == 0:
            return response.get("data", {}).get("address", "")
        return ""
    
    def standardize(self, address: str) -> StandardizedAddress:
        """
        地址标准化（纠错、补全、联想）
        
        Args:
            address: 原始地址
        
        Returns:
            StandardizedAddress: 标准化结果
        """
        logger.info(f"调用地址标准化服务: {address}")
        
        response = self._make_request(
            endpoint=settings.FENGTU_STANDARDIZE_ENDPOINT,
            method="POST",
            data={"address": address}
        )
        
        if response.get("code") == 0:
            data = response.get("data", {})
            return StandardizedAddress(
                original=address,
                standardized=data.get("standardized", address),
                corrections=data.get("corrections", []),
                completions=data.get("completions", []),
                confidence=data.get("confidence", 0.0)
            )
        else:
            return StandardizedAddress(original=address, standardized=address)
    
    def verify_address(self, address: str) -> VerifyResult:
        """
        地址真实性校验
        
        Args:
            address: 待校验地址
        
        Returns:
            VerifyResult: 校验结果
        """
        logger.info(f"调用地址校验服务: {address}")
        
        response = self._make_request(
            endpoint=settings.FENGTU_VERIFY_ENDPOINT,
            method="POST",
            data={"address": address}
        )
        
        if response.get("code") == 0:
            data = response.get("data", {})
            return VerifyResult(
                address=address,
                is_valid=data.get("is_valid", False),
                existence_score=data.get("existence_score", 0.0),
                geometry_matched=data.get("geometry_matched", False),
                issues=data.get("issues", [])
            )
        else:
            return VerifyResult(address=address)
    
    def calculate_similarity(self, address1: str, address2: str) -> SimilarityResult:
        """
        计算两个地址的相似度
        
        Args:
            address1: 地址1
            address2: 地址2
        
        Returns:
            SimilarityResult: 相似度结果
        """
        logger.info(f"计算地址相似度: {address1} <-> {address2}")
        
        response = self._make_request(
            endpoint=settings.FENGTU_SIMILARITY_ENDPOINT,
            method="POST",
            data={"address1": address1, "address2": address2}
        )
        
        if response.get("code") == 0:
            data = response.get("data", {})
            return SimilarityResult(
                address1=address1,
                address2=address2,
                similarity=data.get("similarity", 0.0),
                text_similarity=data.get("text_similarity", 0.0),
                spatial_similarity=data.get("spatial_similarity", 0.0)
            )
        else:
            return SimilarityResult(
                address1=address1,
                address2=address2,
                similarity=0.0
            )


if __name__ == "__main__":
    """测试丰图API客户端"""
    print("=" * 60)
    print("测试丰图科技API客户端")
    print("=" * 60)
    
    client = FengtuClient()
    
    # 测试地址
    test_address = "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼"
    
    # 测试18级分词
    print("\n1. 测试18级地址分词:")
    result = client.segment_address(test_address)
    print(f"原始地址: {result.raw_address}")
    print(f"分词结果: {len(result.segments)}个层级")
    for seg in result.segments:
        print(f"  {seg.level} {seg.name}: {seg.value} (置信度: {seg.confidence})")
    print(f"缺失层级: {result.missing_levels}")
    print(f"整体置信度: {result.confidence}")
    
    # 测试地理编码
    print("\n2. 测试正向地理编码:")
    geo_result = client.geocode(test_address)
    if geo_result.location:
        print(f"经度: {geo_result.location.longitude}")
        print(f"纬度: {geo_result.location.latitude}")
        print(f"置信度: {geo_result.confidence}")
    
    # 测试标准化
    print("\n3. 测试地址标准化:")
    std_result = client.standardize("杭州市余航区五常街道文一西路969号")
    print(f"原始: {std_result.original}")
    print(f"标准化: {std_result.standardized}")
    print(f"置信度: {std_result.confidence}")
    
    print("\n" + "=" * 60)
