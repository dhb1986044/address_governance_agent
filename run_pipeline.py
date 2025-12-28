"""
地址治理流程演示脚本
Usage: python run_pipeline.py
"""
import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from app.assistants.completion import complete_address
from app.resources.knowledge.lance_knowledge import lance_knowledge

# Silence logs for clean output
logging.getLogger("httpx").setLevel(logging.WARNING)

def main():
    print("=" * 60)
    print("地址治理智能体 - 交互式演示")
    print("包含功能: 13级地址解析 | LanceDB 混合检索 | RAG 补全")
    print("=" * 60)
    
    # 预热 Knowledge Base
    print("[INFO] 初始化 Knowledge Base (LanceDB)...")
    _ = lance_knowledge
    print("[INFO] 初始化完成。")
    
    while True:
        try:
            addr = input("\n请输入测试地址 (输入 'q' 退出): ").strip()
            if not addr:
                continue
            if addr.lower() in ['q', 'quit', 'exit']:
                break
            
            print(f"\n[处理中...] 正在治理地址: {addr}")
            
            result = complete_address(addr)
            
            if result.get("status") == "success":
                data = result["data"]
                std = data.get("standard_address", {})
                
                print("\n✅ 治理成功!")
                print("-" * 40)
                print(f"完整标准地址: {std.get('province')}{std.get('city')}{std.get('county')}{std.get('town')}{std.get('community') or ''}{std.get('road') or ''}{std.get('road_no') or ''}{std.get('aoi') or ''}")
                print("-" * 40)
                print(f"置信度: {data.get('confidence')}")
                print(f"缺失层级: {data.get('missing_levels')}")
                print(f"推理过程: {data.get('reasoning')}")
                print("-" * 40)
                print("13级详情:")
                print(json.dumps(std, indent=2, ensure_ascii=False))
            else:
                print(f"\n❌ 处理失败: {result.get('error_message')}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
