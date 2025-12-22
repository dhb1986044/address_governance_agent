#!/usr/bin/env python3
"""
命令行接口 - 地址治理CLI工具
支持单个地址处理、批量处理、文件处理等功能
"""
import sys
import json
import click
from pathlib import Path
from typing import Optional
from app.core import settings, get_logger
from app.workflows.address_pipeline import AddressPipeline
from app.workflows.batch_processor import BatchProcessor, BatchConfig
from app.teams.address_governance_team import IntentType

logger = get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    中文地址治理智能体系统 - 命令行工具
    
    基于LLM+RAG的分层多智能体架构(HMAS)
    """
    pass


@cli.command()
@click.argument('address')
@click.option('--intent', type=click.Choice(['parse', 'complete', 'correct', 'standardize', 'spatialize', 'verify', 'full']),
              default='full', help='治理意图')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径（JSON格式）')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
def process(address: str, intent: str, output: Optional[str], verbose: bool):
    """
    处理单个地址
    
    示例:
        cli.py process "浙江省杭州市余杭区五常街道文一西路969号"
        cli.py process "文一西路969号" --intent complete
        cli.py process "杭州市余航区" --intent correct --output result.json
    """
    click.echo(f"开始处理地址: {address}")
    click.echo(f"治理意图: {intent}")
    
    # 映射意图
    intent_map = {
        'parse': IntentType.PARSE,
        'complete': IntentType.COMPLETE,
        'correct': IntentType.CORRECT,
        'standardize': IntentType.STANDARDIZE,
        'spatialize': IntentType.SPATIALIZE,
        'verify': IntentType.VERIFY,
        'full': IntentType.FULL_PIPELINE
    }
    
    # 执行处理
    pipeline = AddressPipeline()
    result = pipeline.process_single(address)
    
    # 输出结果
    if verbose:
        click.echo("\n" + "=" * 60)
        click.echo(f"地址ID: {result.address_id}")
        click.echo(f"原始地址: {result.original_address}")
        click.echo(f"最终地址: {result.final_address}")
        click.echo(f"状态: {result.status}")
        click.echo(f"置信度: {result.confidence:.2f}")
        click.echo(f"执行步骤: {', '.join(result.steps_completed)}")
        
        if result.coordinates:
            click.echo(f"经度: {result.coordinates.get('longitude', 'N/A')}")
            click.echo(f"纬度: {result.coordinates.get('latitude', 'N/A')}")
        
        if result.errors:
            click.echo(f"错误: {', '.join(result.errors)}")
        
        click.echo(f"耗时: {result.duration_seconds:.2f}秒")
        click.echo("=" * 60)
    else:
        click.echo(f"✓ 处理完成: {result.final_address}")
    
    # 保存到文件
    if output:
        output_data = {
            "address_id": result.address_id,
            "original_address": result.original_address,
            "final_address": result.final_address,
            "coordinates": result.coordinates,
            "confidence": result.confidence,
            "status": result.status,
            "steps_completed": result.steps_completed,
            "errors": result.errors,
            "duration_seconds": result.duration_seconds
        }
        
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        click.echo(f"结果已保存到: {output}")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--column', default='address', help='地址列名（默认: address）')
@click.option('--format', type=click.Choice(['csv', 'excel']), default='csv', help='文件格式')
@click.option('--workers', default=10, help='并发数')
@click.option('--batch-size', default=100, help='批次大小')
def batch(input_file: str, output_file: str, column: str, format: str, workers: int, batch_size: int):
    """
    批量处理地址文件
    
    示例:
        cli.py batch input.csv output.csv
        cli.py batch input.xlsx output.xlsx --format excel --workers 20
    """
    click.echo(f"开始批量处理: {input_file}")
    click.echo(f"输出文件: {output_file}")
    click.echo(f"地址列: {column}, 格式: {format}, 并发数: {workers}")
    
    # 配置
    config = BatchConfig(
        batch_size=batch_size,
        max_workers=workers,
        enable_progress=True
    )
    
    # 处理
    processor = BatchProcessor(config)
    
    try:
        stats = processor.process_large_file(
            input_file=input_file,
            output_file=output_file,
            address_column=column,
            file_format=format
        )
        
        click.echo("\n" + "=" * 60)
        click.echo("批量处理完成！")
        click.echo(f"总数: {stats['total_count']}")
        click.echo(f"成功: {stats['success_count']}")
        click.echo(f"失败: {stats['failed_count']}")
        click.echo(f"平均置信度: {stats['avg_confidence']:.2f}")
        click.echo(f"结果已保存到: {stats['output_file']}")
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"❌ 批量处理失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('addresses', nargs=-1, required=True)
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
def multi(addresses: tuple, output: Optional[str]):
    """
    处理多个地址
    
    示例:
        cli.py multi "地址1" "地址2" "地址3"
        cli.py multi "地址1" "地址2" --output results.json
    """
    click.echo(f"开始处理 {len(addresses)} 个地址")
    
    pipeline = AddressPipeline()
    results = pipeline.process_batch(list(addresses))
    
    # 显示结果
    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.status == "success" else "✗"
        click.echo(f"{i}. {status_icon} {result.original_address}")
        click.echo(f"   → {result.final_address} (置信度: {result.confidence:.2f})")
    
    # 保存结果
    if output:
        json_output = pipeline.export_results(results, output)
        click.echo(f"\n结果已保存到: {output}")


@cli.command()
def config():
    """显示当前配置"""
    click.echo("=" * 60)
    click.echo("系统配置信息")
    click.echo("=" * 60)
    click.echo(f"LLM模型: {settings.LLM_MODEL_ID}")
    click.echo(f"LLM Base URL: {settings.LLM_BASE_URL}")
    click.echo(f"丰图API Base URL: {settings.FENGTU_BASE_URL}")
    click.echo(f"Milvus地址: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    click.echo(f"Elasticsearch地址: {settings.ES_HOST}:{settings.ES_PORT}")
    click.echo(f"Embedding模型: {settings.EMBEDDING_MODEL_ID}")
    click.echo(f"项目根目录: {settings.PROJECT_ROOT}")
    click.echo(f"数据目录: {settings.DATA_DIR}")
    click.echo(f"缓存目录: {settings.CACHE_DIR}")
    click.echo(f"日志级别: {settings.LOG_LEVEL}")
    click.echo("=" * 60)


@cli.command()
def test():
    """运行测试用例"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "亲，帮我送到紫金港那个全家，就是东区那个",
        "杭州市余航区五常街道",
        "阿里西溪园区B区",
        "浙一医院余杭院区旁边那个全家",
    ]
    
    click.echo("=" * 60)
    click.echo("运行测试用例")
    click.echo("=" * 60)
    
    pipeline = AddressPipeline()
    
    for i, address in enumerate(test_cases, 1):
        click.echo(f"\n测试 {i}/{len(test_cases)}: {address}")
        click.echo("-" * 60)
        
        result = pipeline.process_single(address)
        
        status_icon = "✓" if result.status == "success" else "✗"
        click.echo(f"{status_icon} 状态: {result.status}")
        click.echo(f"   最终地址: {result.final_address}")
        click.echo(f"   置信度: {result.confidence:.2f}")
        click.echo(f"   耗时: {result.duration_seconds:.2f}秒")
    
    click.echo("\n" + "=" * 60)
    click.echo("测试完成！")


if __name__ == '__main__':
    cli()
