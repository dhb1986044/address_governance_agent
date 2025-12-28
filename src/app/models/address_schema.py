"""
地址数据模型定义
基于丰图科技13级地址模型 (Fengtu Address Model)
"""
from typing import Optional, List, Type
from pydantic import BaseModel, Field

class BaseAddressSchema(BaseModel):
    """
    地址模型基类
    提供动态提取字段描述的方法，用于生成 Prompt
    """
    
    @classmethod
    def get_field_descriptions(cls) -> str:
        """
        获取字段描述列表，格式：
        - field_name: description
        """
        descriptions = []
        for name, field in cls.model_fields.items():
            desc = field.description or name
            descriptions.append(f"- {name}: {desc}")
        return "\n".join(descriptions)

class FengtuAddress(BaseAddressSchema):
    """
    丰图13级地址模型
    """
    province: Optional[str] = Field(None, description="省/直辖市/特别行政区 (L1)")
    city: Optional[str] = Field(None, description="地级市 (L2)")
    county: Optional[str] = Field(None, description="区县/县级市 (L3)")
    town: Optional[str] = Field(None, description="乡/镇/街道 (L4)")
    community: Optional[str] = Field(None, description="行政村/社区/居委会 (L5)")
    road: Optional[str] = Field(None, description="道路 (L6)")
    road_no: Optional[str] = Field(None, description="门牌号 (L7)")
    aoi: Optional[str] = Field(None, description="院落/小区/POI (L8)")
    sub_aoi: Optional[str] = Field(None, description="子院落/组团 (L9)")
    building: Optional[str] = Field(None, description="楼栋 (L10)")
    unit: Optional[str] = Field(None, description="单元 (L11)")
    floor: Optional[str] = Field(None, description="楼层 (L12)")
    room: Optional[str] = Field(None, description="房间号 (L13)")

    class Config:
        json_schema_extra = {
            "example": {
                "province": "浙江省",
                "city": "杭州市",
                "county": "余杭区",
                "town": "五常街道",
                "community": "文一社区",
                "road": "文一西路",
                "road_no": "969号",
                "aoi": "阿里巴巴西溪园区",
                "sub_aoi": "A区",
                "building": "5号楼",
                "unit": None,
                "floor": "5层",
                "room": "501室"
            }
        }

class OutputContainer(BaseModel):
    """
    智能体输出容器
    """
    standard_address: FengtuAddress = Field(..., description="标准化的地址结构")
    confidence: float = Field(..., description="解析置信度 (0.0 - 1.0)")
    missing_levels: List[str] = Field(default_factory=list, description="缺失的层级列表")
    reasoning: str = Field(..., description="简短的推理/补全过程说明")
