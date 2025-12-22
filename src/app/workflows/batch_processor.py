"""
批量处理工作流 - 高性能并发处理
支持多线程/多进程批量处理大规模地址数据
"""
from typing import List, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import time
from app.core import settings, get_logger
from app.workflows.address_pipeline import AddressPipeline, PipelineResult

logger = get_logger(__name__)


@dataclass
class BatchConfig:
    """批量处理配置"""
    batch_size: int = 100  # 每批次大小
    max_workers: int = 10  # 最大并发数
    use_process: bool = False  # 是否使用多进程（默认多线程）
    timeout: int = 300  # 超时时间（秒）
    retry_count: int = 3  # 重试次数
    enable_progress: bool = True  # 是否显示进度


class BatchProcessor:
    """
    批量处理器
    
    特点：
    - 支持多线程/多进程并发
    - 自动分批和负载均衡
    - 失败重试机制
    - 实时进度跟踪
    - 性能监控
    """
    
    def __init__(self, config: BatchConfig = None):
        """
        初始化批量处理器
        
        Args:
            config: 批量处理配置
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = config or BatchConfig()
        self.pipeline = AddressPipeline()
        self.logger.info(f"批量处理器已初始化: 批次大小={self.config.batch_size}, "
                        f"并发数={self.config.max_workers}")
    
    def process_concurrent(
        self,
        addresses: List[str],
        context: Dict[str, Any] = None
    ) -> List[PipelineResult]:
        """
        并发处理地址列表
        
        Args:
            addresses: 地址列表
            context: 上下文信息
        
        Returns:
            List[PipelineResult]: 处理结果列表
        """
        self.logger.info(f"开始并发处理 {len(addresses)} 个地址")
        start_time = time.time()
        
        results = []
        failed_indices = []
        
        # 选择执行器
        ExecutorClass = ProcessPoolExecutor if self.config.use_process else ThreadPoolExecutor
        
        with ExecutorClass(max_workers=self.config.max_workers) as executor:
            # 提交所有任务
            future_to_idx = {}
            for idx, address in enumerate(addresses):
                future = executor.submit(
                    self._process_with_retry,
                    address,
                    f"addr_{idx}",
                    context
                )
                future_to_idx[future] = idx
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_idx, timeout=self.config.timeout):
                idx = future_to_idx[future]
                try:
                    result = future.result()
                    results.append((idx, result))
                    
                    if result.status == "failed":
                        failed_indices.append(idx)
                    
                    completed += 1
                    if self.config.enable_progress and completed % 10 == 0:
                        progress = completed / len(addresses) * 100
                        self.logger.info(f"处理进度: {completed}/{len(addresses)} ({progress:.1f}%)")
                
                except Exception as e:
                    self.logger.error(f"处理地址 {idx} 时发生异常: {e}")
                    failed_indices.append(idx)
        
        # 按原始顺序排序结果
        results.sort(key=lambda x: x[0])
        sorted_results = [r[1] for r in results]
        
        # 统计
        duration = time.time() - start_time
        success_count = len(sorted_results) - len(failed_indices)
        throughput = len(addresses) / duration if duration > 0 else 0
        
        self.logger.info(
            f"并发处理完成: 成功={success_count}, 失败={len(failed_indices)}, "
            f"总数={len(addresses)}, 耗时={duration:.2f}秒, "
            f"吞吐量={throughput:.2f}个/秒"
        )
        
        return sorted_results
    
    def _process_with_retry(
        self,
        address: str,
        address_id: str,
        context: Dict[str, Any]
    ) -> PipelineResult:
        """
        带重试的处理函数
        
        Args:
            address: 地址
            address_id: 地址ID
            context: 上下文
        
        Returns:
            PipelineResult: 处理结果
        """
        last_error = None
        
        for attempt in range(self.config.retry_count):
            try:
                result = self.pipeline.process_single(address, address_id, context)
                
                if result.status == "success":
                    return result
                
                # 如果失败，记录错误并重试
                last_error = result.errors
                if attempt < self.config.retry_count - 1:
                    self.logger.warning(f"处理失败，重试 {attempt + 1}/{self.config.retry_count}")
                    time.sleep(1)  # 重试延迟
            
            except Exception as e:
                last_error = str(e)
                if attempt < self.config.retry_count - 1:
                    self.logger.warning(f"发生异常，重试 {attempt + 1}/{self.config.retry_count}: {e}")
                    time.sleep(1)
        
        # 所有重试失败
        from datetime import datetime
        result = PipelineResult(
            address_id=address_id,
            original_address=address,
            final_address=address,
            status="failed",
            start_time=datetime.now()
        )
        result.errors.append(f"重试{self.config.retry_count}次后仍失败: {last_error}")
        result.end_time = datetime.now()
        
        return result
    
    def process_large_file(
        self,
        input_file: str,
        output_file: str,
        address_column: str = "address",
        file_format: str = "csv"
    ) -> Dict[str, Any]:
        """
        处理大文件（CSV/Excel）
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            address_column: 地址列名
            file_format: 文件格式（csv/excel）
        
        Returns:
            Dict: 处理统计信息
        """
        import pandas as pd
        
        self.logger.info(f"开始处理大文件: {input_file}")
        
        # 读取文件
        if file_format == "csv":
            df = pd.read_csv(input_file)
        elif file_format == "excel":
            df = pd.read_excel(input_file)
        else:
            raise ValueError(f"不支持的文件格式: {file_format}")
        
        self.logger.info(f"文件包含 {len(df)} 条记录")
        
        # 提取地址列
        addresses = df[address_column].tolist()
        
        # 并发处理
        results = self.process_concurrent(addresses)
        
        # 将结果添加到DataFrame
        df['final_address'] = [r.final_address for r in results]
        df['confidence'] = [r.confidence for r in results]
        df['status'] = [r.status for r in results]
        df['longitude'] = [r.coordinates.get('longitude', None) for r in results]
        df['latitude'] = [r.coordinates.get('latitude', None) for r in results]
        
        # 保存结果
        if file_format == "csv":
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
        elif file_format == "excel":
            df.to_excel(output_file, index=False)
        
        self.logger.info(f"结果已保存到: {output_file}")
        
        # 返回统计信息
        stats = {
            "total_count": len(results),
            "success_count": sum(1 for r in results if r.status == "success"),
            "failed_count": sum(1 for r in results if r.status == "failed"),
            "avg_confidence": sum(r.confidence for r in results) / len(results),
            "input_file": input_file,
            "output_file": output_file
        }
        
        return stats


if __name__ == "__main__":
    """测试批量处理器"""
    test_addresses = [
        "浙江省杭州市余杭区五常街道文一西路969号",
        "文一西路969号5号楼",
        "杭州市余航区五常街道",
        "阿里西溪园区B区",
        "北京市海淀区中关村大街1号",
    ]
    
    print("=" * 80)
    print("测试批量处理器")
    print("=" * 80)
    
    # 配置
    config = BatchConfig(
        batch_size=10,
        max_workers=3,
        use_process=False,
        enable_progress=True
    )
    
    processor = BatchProcessor(config)
    
    # 并发处理
    print("\n=== 并发处理测试 ===")
    results = processor.process_concurrent(test_addresses)
    
    print(f"\n处理结果:")
    for r in results:
        status_icon = "✓" if r.status == "success" else "✗"
        print(f"  {status_icon} [{r.address_id}] {r.original_address[:40]}...")
        print(f"     → {r.final_address[:40]}... (置信度: {r.confidence:.2f})")
    
    print("\n" + "=" * 80)
