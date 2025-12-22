"""
地理编码工具 - 地址与坐标的双向转换
"""
from typing import Dict, Any, Optional
from agno.tools import tool
from app.core import FengtuClient, get_logger

logger = get_logger(__name__)


@tool(
    name="geocode_address",
    description="""正向地理编码：将中文地址转换为地理坐标（经纬度）。
    
    返回WGS84坐标系的经纬度坐标、匹配精度等级和置信度。
    用于地址的空间化处理和地理位置验证。
    """
)
def geocode_address(address: str) -> Dict[str, Any]:
    """
    正向地理编码（地址 → 坐标）
    
    Args:
        address: 地址字符串
    
    Returns:
        Dict: 包含经纬度、置信度等信息
    """
    logger.info(f"正向地理编码: {address}")
    
    try:
        client = FengtuClient()
        result = client.geocode(address)
        
        return {
            "address": result.address,
            "longitude": result.location.longitude if result.location else None,
            "latitude": result.location.latitude if result.location else None,
            "coordinate_system": result.location.coordinate_system if result.location else "WGS84",
            "confidence": result.confidence,
            "level": result.level
        }
    except Exception as e:
        logger.error(f"正向地理编码失败: {e}")
        return {
            "address": address,
            "longitude": None,
            "latitude": None,
            "confidence": 0.0,
            "error": str(e)
        }


@tool(
    name="reverse_geocode",
    description="""逆向地理编码：将地理坐标（经纬度）转换为中文地址。
    
    根据经纬度坐标返回最接近的标准地址描述。
    用于坐标校验和地址反查。
    """
)
def reverse_geocode(longitude: float, latitude: float) -> Dict[str, Any]:
    """
    逆向地理编码（坐标 → 地址）
    
    Args:
        longitude: 经度
        latitude: 纬度
    
    Returns:
        Dict: 包含地址字符串等信息
    """
    logger.info(f"逆向地理编码: ({longitude}, {latitude})")
    
    try:
        client = FengtuClient()
        address = client.regeocode(longitude, latitude)
        
        return {
            "longitude": longitude,
            "latitude": latitude,
            "address": address,
            "success": bool(address)
        }
    except Exception as e:
        logger.error(f"逆向地理编码失败: {e}")
        return {
            "longitude": longitude,
            "latitude": latitude,
            "address": "",
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """测试地理编码工具"""
    print("=" * 80)
    print("测试地理编码工具")
    print("=" * 80)
    
    # 测试正向编码
    test_address = "浙江省杭州市余杭区五常街道文一西路969号"
    print(f"\n1. 正向地理编码: {test_address}")
    result = geocode_address(test_address)
    print(f"   经度: {result.get('longitude')}")
    print(f"   纬度: {result.get('latitude')}")
    print(f"   置信度: {result.get('confidence', 0):.2f}")
    print(f"   精度等级: {result.get('level')}")
    
    # 测试逆向编码
    if result.get('longitude') and result.get('latitude'):
        print(f"\n2. 逆向地理编码: ({result['longitude']}, {result['latitude']})")
        reverse_result = reverse_geocode(result['longitude'], result['latitude'])
        print(f"   地址: {reverse_result.get('address')}")
        print(f"   成功: {reverse_result.get('success')}")
    
    print("\n" + "=" * 80)
