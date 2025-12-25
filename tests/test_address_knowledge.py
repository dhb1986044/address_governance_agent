"""针对 AddressKnowledge 的 LanceDB 集成回归测试。"""

from pathlib import Path
from typing import Dict, List
import importlib
import importlib.util
import os
import sys

import pytest


lancedb_required = pytest.mark.lancedb


def build_knowledge(tmp_path) -> "AddressKnowledge":
    """构造独立的 AddressKnowledge，使用隔离的 LanceDB 路径。"""

    # 确保 src 目录在导入路径中
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    # 指定单独的 LanceDB 目录，避免污染默认数据
    os.environ["LANCEDB_URI"] = str(tmp_path / "lancedb")
    os.environ["LANCEDB_BOOTSTRAP_ENABLED"] = "1"

    # 重新加载配置和依赖模块，使环境变量生效
    from app import core
    from app.core import config

    importlib.reload(config)
    importlib.reload(core)

    from app.resources.knowledge import address_knowledge as ak

    importlib.reload(ak)
    return ak.AddressKnowledge()


def extract_addresses(results: List[object]) -> List[str]:
    return [getattr(item, "address", item.get("address")) for item in results]


def has_lancedb() -> bool:
    return importlib.util.find_spec("lancedb") is not None


@lancedb_required
def test_lancedb_bootstrap_and_ready(tmp_path):
    pytest.importorskip("lancedb", reason="需要安装 lancedb 才能验证 LanceDB 集成")

    kb = build_knowledge(tmp_path)

    assert kb.lancedb_store.ready, "LanceDB 未就绪，无法进行集成测试"
    assert kb.lancedb_store.table.count_rows() == 7


@lancedb_required
def test_semantic_search_returns_seed_aoi(tmp_path):
    pytest.importorskip("lancedb", reason="需要安装 lancedb 才能验证 LanceDB 语义召回")

    kb = build_knowledge(tmp_path)

    filters: Dict[str, str] = {"province": "河北省", "city": "保定市"}
    results = kb.search_by_semantic("悦佳纸业", top_k=3, filters=filters)

    addresses = extract_addresses(results)
    assert any("悦佳纸业" in addr for addr in addresses)


def test_text_search_respects_filters(tmp_path):
    kb = build_knowledge(tmp_path)

    # 过滤条件不匹配应直接被过滤掉（无论是 LanceDB 还是模拟候选集）
    mismatched_filters: Dict[str, str] = {"province": "新疆维吾尔自治区"}
    results = kb.search_by_text("悦佳", top_k=3, filters=mismatched_filters)

    assert results == []


def test_hybrid_search_triggers_rerank(tmp_path):
    kb = build_knowledge(tmp_path)

    # 在无 LanceDB 环境下回落到模拟候选也能执行混合检索与重排
    results = kb.hybrid_search("文一西路969", top_k=5, filters=None)

    assert results, "混合检索应返回至少一个候选"
    assert all("rerank" in item["source"] for item in results)
    assert any("文一西路" in item["address"] for item in results)
