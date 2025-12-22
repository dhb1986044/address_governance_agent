#!/usr/bin/env python3
"""
命令行接口 - 地址治理CLI工具

使用 Typer 构建CLI应用 (Agno SDK v2.3.20 规范)
"""
import typer
from typing import Optional
from rich.console import Console
from pathlib import Path

from app.core import settings
from app.teams.address_governance_team import make_address_governance_team
from app.workflows.address_pipeline import make_address_pipeline


app = typer.Typer(
    name="address-governance",
    help="中文地址治理智能体 CLI 工具 (基于 Agno SDK v2.3.20)",
)
console = Console()


@app.command("chat")
def chat_mode():
    """
    交互式对话模式 - 使用地址治理团队
    """
    console.print("[bold green]启动地址治理对话模式...[/bold green]")
    team = make_address_governance_team()
    
    while True:
        try:
            user_input = console.input("[bold blue]请输入地址（输入 'quit' 退出）: [/bold blue]")
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            team.print_response(user_input, stream=True, markdown=True)
            
        except KeyboardInterrupt:
            break
    
    console.print("[bold yellow]再见！[/bold yellow]")


@app.command("process")
def process_address(
    address: str = typer.Argument(..., help="待处理的地址"),
    geocode: bool = typer.Option(True, "--geocode/--no-geocode", help="是否获取经纬度"),
):
    """
    单地址处理模式 - 使用确定性流水线
    """
    console.print(f"[bold]处理地址: {address}[/bold]")
    
    pipeline = make_address_pipeline()
    pipeline.print_response(address, stream=True, markdown=True)


@app.command("batch")
def batch_process(
    file_path: str = typer.Argument(..., help="包含地址列表的文件路径"),
    output_path: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """
    批量地址处理模式
    """
    import json
    
    # 读取地址文件
    with open(file_path, "r", encoding="utf-8") as f:
        addresses = [line.strip() for line in f if line.strip()]
    
    console.print(f"[bold]共读取 {len(addresses)} 个地址[/bold]")
    
    pipeline = make_address_pipeline()
    results = []
    
    for i, addr in enumerate(addresses, 1):
        console.print(f"[{i}/{len(addresses)}] 处理: {addr}")
        response = pipeline.run(input=addr)
        results.append({
            "input": addr,
            "output": response.content if hasattr(response, 'content') else str(response),
            "status": "success" if response else "failed"
        })
    
    # 输出结果
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        console.print(f"[bold green]结果已保存至: {output_path}[/bold green]")
    else:
        console.print_json(data=results)


@app.command("config")
def show_config():
    """显示当前配置"""
    console.print("=" * 60)
    console.print("系统配置信息")
    console.print("=" * 60)
    console.print(f"LLM模型: {settings.LLM_MODEL_ID}")
    console.print(f"LLM Base URL: {settings.LLM_BASE_URL}")
    console.print(f"丰图API Base URL: {settings.FENGTU_BASE_URL}")
    console.print(f"SQLite DB: {settings.SQLITE_DB_FILE}")
    console.print(f"LanceDB URI: {settings.LANCEDB_URI}")
    console.print(f"项目根目录: {settings.PROJECT_ROOT}")
    console.print(f"数据目录: {settings.DATA_DIR}")
    console.print(f"缓存目录: {settings.CACHE_DIR}")
    console.print(f"日志级别: {settings.LOG_LEVEL}")
    console.print("=" * 60)


@app.command("test")
def run_tests():
    """运行测试用例"""
    test_cases = [
        "浙江省杭州市余杭区五常街道文一西路969号阿里巴巴西溪园区5号楼",
        "文一西路969号5号楼",
        "亲，帮我送到紫金港那个全家，就是东区那个",
        "杭州市余航区五常街道",
        "阿里西溪园区B区",
        "浙一医院余杭院区旁边那个全家",
    ]
    
    console.print("=" * 60)
    console.print("运行测试用例")
    console.print("=" * 60)
    
    team = make_address_governance_team()
    
    for i, address in enumerate(test_cases, 1):
        console.print(f"\n测试 {i}/{len(test_cases)}: {address}")
        console.print("-" * 60)
        team.print_response(f"请完成地址治理：{address}", stream=True, markdown=True)
    
    console.print("\n" + "=" * 60)
    console.print("测试完成！")


if __name__ == '__main__':
    app()
