"""
集成测试 - 验证 LanceDB + Zhipu AI 全流程
"""
import os
import sys
import unittest
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.core import settings
from app.resources.knowledge.lance_knowledge import lance_knowledge
from app.assistants.completion import complete_address
from app.assistants.parser import parse_address

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAddressGovernance(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """初始化测试环境"""
        # 确保 LanceDB 数据已摄入
        # lance_knowledge singleton init matches this
        pass

    def test_parser_structure(self):
        """测试解析器的结构化输出"""
        logger.info("Testing Parser Structure...")
        addr = "浙江省杭州市余杭区文一西路969号"
        result = parse_address(addr)
        
        self.assertEqual(result["status"], "success")
        data = result["data"]
        
        # Check standard_address
        self.assertIn("standard_address", data)
        std = data["standard_address"]
        # Since we are using MOCKED segment tool if key missing, checks depend on mock or real
        # But structure check is valid
        self.assertIn("province", std)
        
    def test_rag_completion_aoi(self):
        """测试 AOI 补全 (RAG)"""
        logger.info("Testing RAG Completion (AOI)...")
        # Query specifically matches ingested data: 00001669... 悦佳纸业
        # Mock Segment will return "保定市" matching logic
        addr = "保定悦佳纸业"
        
        result = complete_address(addr)
        
        if result["status"] != "success":
             msg = result.get('error_message')
             print(f"\n[ERROR] Test Failed (AOI). Error: {msg}")
             print(f"[DEBUG] Raw Response: {result.get('raw_content')}")
        
        self.assertEqual(result["status"], "success")

    def test_rag_completion_village(self):
        """测试村庄补全 (RAG)"""
        logger.info("Testing RAG Completion (Village)...")
        # Query matches "孙草沟"
        addr = "孙草沟"
        
        result = complete_address(addr)
        if result["status"] != "success":
             msg = result.get('error_message')
             print(f"\n[ERROR] Test Failed (Village). Error: {msg}")
             print(f"[DEBUG] Raw Response: {result.get('raw_content')}")

        self.assertEqual(result["status"], "success")
        std = data["standard_address"]
        
        logger.info(f"RAG Result for {addr}: {std}")
        
        self.assertEqual(std["county"], "涞源县")
        self.assertEqual(std["town"], "王安镇")
        self.assertIn("孙草沟", str(std["community"]) + str(std["aoi"])) 

if __name__ == "__main__":
    unittest.main()
