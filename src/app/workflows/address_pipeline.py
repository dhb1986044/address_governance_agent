"""
地址治理流水线 - 确定性端到端流程
预处理 → 分级路由 → 18级解析 → 补全/纠错 → 标准化 → 空间化 → 校验 → 输出
"""
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from app.core import get_logger
from app.teams.address_governance_team import AddressGovernanceTeam, IntentType

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """流水线执行结果"""
    address_id: str
    original_address: str
    final_address: str
    coordinates: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    status: str = "pending"  # pending/success/failed/manual_review
    steps_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = None
    duration_seconds: float = 0.0


class AddressPipeline:
    """
    地址治理流水线
    
    特点：
    - 确定性流程，每个地址都经过相同的处理步骤
    - 自动路由和容错机制
    - 完整的日志和追踪
    - 支持批量处理
    """
    
    def __init__(self):
        """初始化流水线"""
        self.logger = get_logger(self.__class__.__name__)
        self.team = AddressGovernanceTeam()
        self.logger.info("地址治理流水线已初始化")
    
    def process_single(
        self,
        address: str,
        address_id: str = None,
        context: Dict[str, Any] = None
    ) -> PipelineResult:
        """
        处理单个地址
        
        Args:
            address: 待处理的地址
            address_id: 地址唯一标识（可选）
            context: 上下文信息（可选）
        
        Returns:
            PipelineResult: 处理结果
        """
        start_time = datetime.now()
        
        if address_id is None:
            import uuid
            address_id = f"addr_{uuid.uuid4().hex[:8]}"
        
        self.logger.info(f"开始处理地址 [{address_id}]: {address}")
        
        result = PipelineResult(
            address_id=address_id,
            original_address=address,
            final_address=address,
            start_time=start_time
        )
        
        try:
            # 执行完整治理流程
            governance_result = self.team.govern_address(
                address,
                intent=IntentType.FULL_PIPELINE,
                context=context
            )
            
            # 提取结果
            if governance_result.get("status") == "success":
                result.status = "success"
                result.final_address = governance_result.get("final_address", address)
                result.steps_completed = governance_result.get("pipeline_steps", [])
                
                # 提取坐标
                spatialized = governance_result.get("intermediate_results", {}).get("spatialized", {})
                if spatialized:
                    # 简化实现，实际需要解析spatialized结果
                    result.coordinates = {"longitude": 0.0, "latitude": 0.0}
                
                # 提取置信度
                verified = governance_result.get("intermediate_results", {}).get("verified", {})
                if verified:
                    # 简化实现
                    result.confidence = 0.90
                
                result.metadata = governance_result.get("intermediate_results", {})
                
            else:
                result.status = "failed"
                result.errors.append(governance_result.get("error", "未知错误"))
            
        except Exception as e:
            self.logger.error(f"处理地址失败 [{address_id}]: {e}")
            result.status = "failed"
            result.errors.append(str(e))
        
        # 计算耗时
        result.end_time = datetime.now()
        result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        self.logger.info(
            f"地址处理完成 [{address_id}]: "
            f"状态={result.status}, 耗时={result.duration_seconds:.2f}秒"
        )
        
        return result
    
    def process_batch(
        self,
        addresses: List[str],
        context: Dict[str, Any] = None
    ) -> List[PipelineResult]:
        """
        批量处理地址
        
        Args:
            addresses: 地址列表
            context: 上下文信息（可选）
        
        Returns:
            List[PipelineResult]: 处理结果列表
        """
        self.logger.info(f"开始批量处理 {len(addresses)} 个地址")
        
        results = []
        for i, address in enumerate(addresses, 1):
            self.logger.info(f"处理进度: {i}/{len(addresses)}")
            result = self.process_single(address, f"batch_{i}", context)
            results.append(result)
        
        # 统计
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        
        self.logger.info(
            f"批量处理完成: 成功={success_count}, 失败={failed_count}, "
            f"总数={len(addresses)}"
        )
        
        return results
    
    def export_results(
        self,
        results: List[PipelineResult],
        output_file: str = None
    ) -> str:
        """
        导出处理结果
        
        Args:
            results: 处理结果列表
            output_file: 输出文件路径（可选）
        
        Returns:
            str: 导出的JSON字符串
        """
        import json
        from pathlib import Path
        
        # 转换为可序列化的字典
        export_data = []
        for result in results:
            export_data.append({
                "address_id": result.address_id,
                "original_address": result.original_address,
                "final_address": result.final_address,
                "coordinates": result.coordinates,
                "confidence": result.confidence,
                "status": result.status,
                "steps_completed": result.steps_completed,
                "errors": result.errors,
                "warnings": result.warnings,
                "duration_seconds": result.duration_seconds,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat() if result.end_time else None
            })
        
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        # 如果指定了输出文件，写入文件
        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            self.logger.info(f"结果已导出到: {output_file}")
        
        return json_str


if __name__ == "__main__":
    """测试地址治理流水线"""
    test_addresses = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "亲，帮我送到紫金港那个全家，就是东区那个",
        "杭州市余航区五常街道",
        "阿里西溪园区B区",
        "浙一医院余杭院区旁边那个全家",
    ]
    
    print("=" * 80)
    print("测试地址治理流水线")
    print("=" * 80)
    
    pipeline = AddressPipeline()
    
    # 测试单个处理
    print("\n=== 单个地址处理 ===")
    result = pipeline.process_single(test_addresses[0])
    print(f"地址ID: {result.address_id}")
    print(f"原始地址: {result.original_address}")
    print(f"最终地址: {result.final_address}")
    print(f"状态: {result.status}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"执行步骤: {result.steps_completed}")
    print(f"耗时: {result.duration_seconds:.2f}秒")
    
    # 测试批量处理
    print("\n=== 批量地址处理 ===")
    batch_results = pipeline.process_batch(test_addresses[:3])
    
    print(f"\n批量处理结果统计:")
    for r in batch_results:
        print(f"  [{r.address_id}] {r.status} - {r.original_address[:30]}...")
    
    # 导出结果
    print("\n=== 导出结果 ===")
    json_output = pipeline.export_results(batch_results[:2])
    print(f"导出JSON长度: {len(json_output)} 字符")
    
    print("\n" + "=" * 80)
