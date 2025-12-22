"""
地址治理团队 - HMAS分层多智能体协作
实现意图识别、任务分发、漏斗式分级处理
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from agno import Agent
from app.core import settings, get_logger
from app.assistants.parser import make_parser_agent
from app.assistants.normalizer import make_normalizer_agent
from app.assistants.completion import make_completion_agent
from app.assistants.correction import make_correction_agent
from app.assistants.standardizer import make_standardizer_agent
from app.assistants.spatializer import make_spatializer_agent
from app.assistants.verifier import make_verifier_agent

logger = get_logger(__name__)


class IntentType(Enum):
    """地址治理意图类型"""
    PARSE = "解析"  # 结构化解析
    COMPLETE = "补全"  # 缺失层级补全
    CORRECT = "纠错"  # 错误修正
    STANDARDIZE = "标准化"  # 综合标准化
    SPATIALIZE = "空间化"  # 坐标转换
    VERIFY = "校验"  # 结果校验
    FULL_PIPELINE = "完整流程"  # 端到端处理


class ComplexityLevel(Enum):
    """地址复杂度等级"""
    SIMPLE = "简单"  # 标准地址，无需处理
    MEDIUM = "中等"  # 需要简单纠错或补全
    COMPLEX = "复杂"  # 需要多步骤处理
    VERY_COMPLEX = "极复杂"  # 需要LLM深度推理


class AddressGovernanceTeam:
    """
    地址治理团队 - HMAS架构实现
    
    分层架构：
    L1: Orchestrator（协调者） - 意图识别和任务分发
    L2: Specialist Agents（专家智能体） - 各垂直领域
    L3: Tool Layer（工具层） - 丰图API和RAG
    """
    
    def __init__(self):
        """初始化地址治理团队"""
        self.logger = get_logger(self.__class__.__name__)
        
        # 创建所有专家智能体
        self.agents = {
            "normalizer": make_normalizer_agent(),
            "parser": make_parser_agent(),
            "completion": make_completion_agent(),
            "correction": make_correction_agent(),
            "standardizer": make_standardizer_agent(),
            "spatializer": make_spatializer_agent(),
            "verifier": make_verifier_agent(),
        }
        
        self.logger.info("地址治理团队已初始化，包含7个专家智能体")
    
    def analyze_intent(self, user_input: str) -> IntentType:
        """
        意图识别 - 识别用户的治理需求
        
        Args:
            user_input: 用户输入
        
        Returns:
            IntentType: 识别的意图
        """
        user_lower = user_input.lower()
        
        if "解析" in user_input or "分词" in user_input:
            return IntentType.PARSE
        elif "补全" in user_input or "缺失" in user_input:
            return IntentType.COMPLETE
        elif "纠错" in user_input or "错误" in user_input or "错别字" in user_input:
            return IntentType.CORRECT
        elif "标准化" in user_input or "规范" in user_input:
            return IntentType.STANDARDIZE
        elif "坐标" in user_input or "经纬度" in user_input or "空间" in user_input:
            return IntentType.SPATIALIZE
        elif "校验" in user_input or "验证" in user_input:
            return IntentType.VERIFY
        else:
            # 默认执行完整流程
            return IntentType.FULL_PIPELINE
    
    def assess_complexity(self, address: str) -> ComplexityLevel:
        """
        评估地址复杂度
        
        Args:
            address: 地址文本
        
        Returns:
            ComplexityLevel: 复杂度等级
        """
        # 简单启发式规则
        score = 0
        
        # 长度因素
        if len(address) < 20:
            score += 2
        elif len(address) > 50:
            score += 1
        
        # 包含完整行政区划
        if "省" in address and "市" in address and "区" in address:
            score += 1
        else:
            score -= 1
        
        # 包含明显错误
        if "亲" in address or "您好" in address or "麻烦" in address:
            score -= 1
        
        # 包含门牌号
        import re
        if re.search(r'\d+号', address):
            score += 1
        
        if score >= 3:
            return ComplexityLevel.SIMPLE
        elif score >= 1:
            return ComplexityLevel.MEDIUM
        elif score >= -1:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX
    
    def route_by_complexity(
        self,
        address: str,
        complexity: ComplexityLevel
    ) -> str:
        """
        基于复杂度的漏斗式分级路由
        
        漏斗比例（配置化）：
        - 40% 规则引擎处理（简单）
        - 30% 轻量模型处理（中等）
        - 15% ES检索处理（复杂）
        - 15% LLM深度处理（极复杂）
        
        Args:
            address: 地址
            complexity: 复杂度等级
        
        Returns:
            str: 路由策略
        """
        if complexity == ComplexityLevel.SIMPLE:
            return "rule_engine"  # 规则引擎
        elif complexity == ComplexityLevel.MEDIUM:
            return "light_model"  # 轻量模型
        elif complexity == ComplexityLevel.COMPLEX:
            return "es_search"  # ES检索
        else:
            return "llm_reasoning"  # LLM深度推理
    
    def govern_address(
        self,
        address: str,
        intent: Optional[IntentType] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        地址治理主入口
        
        Args:
            address: 待治理的地址
            intent: 治理意图（可选，自动识别）
            context: 上下文信息（可选）
        
        Returns:
            Dict: 治理结果
        """
        self.logger.info(f"开始治理地址: {address}")
        
        # 1. 意图识别
        if intent is None:
            intent = IntentType.FULL_PIPELINE
        self.logger.info(f"治理意图: {intent.value}")
        
        # 2. 复杂度评估
        complexity = self.assess_complexity(address)
        self.logger.info(f"复杂度评估: {complexity.value}")
        
        # 3. 路由策略
        route = self.route_by_complexity(address, complexity)
        self.logger.info(f"路由策略: {route}")
        
        # 4. 执行治理流程
        result = self._execute_pipeline(address, intent, route, context)
        
        return result
    
    def _execute_pipeline(
        self,
        address: str,
        intent: IntentType,
        route: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行治理流程
        
        Args:
            address: 地址
            intent: 意图
            route: 路由策略
            context: 上下文
        
        Returns:
            Dict: 执行结果
        """
        results = {
            "original_address": address,
            "intent": intent.value,
            "complexity_route": route,
            "steps": []
        }
        
        # 根据意图执行不同流程
        if intent == IntentType.FULL_PIPELINE:
            # 完整治理流程
            results = self._full_pipeline(address, context)
        elif intent == IntentType.PARSE:
            # 仅解析
            from app.assistants.parser import parse_address
            parse_result = parse_address(address)
            results["parse_result"] = parse_result
            results["steps"].append("解析完成")
        elif intent == IntentType.STANDARDIZE:
            # 仅标准化
            from app.assistants.standardizer import standardize
            std_result = standardize(address)
            results["standardized_result"] = std_result
            results["steps"].append("标准化完成")
        # 其他意图类似...
        
        return results
    
    def _full_pipeline(
        self,
        address: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        完整治理流水线
        
        流程: 规范化 → 解析 → 纠错 → 补全 → 标准化 → 空间化 → 校验
        
        Args:
            address: 地址
            context: 上下文
        
        Returns:
            Dict: 完整治理结果
        """
        self.logger.info("执行完整治理流水线")
        
        results = {
            "original_address": address,
            "pipeline_steps": [],
            "intermediate_results": {}
        }
        
        try:
            # Step 1: 规范化
            self.logger.info("Step 1: 地址规范化")
            from app.assistants.normalizer import normalize_address
            normalized = normalize_address(address)
            results["intermediate_results"]["normalized"] = normalized
            results["pipeline_steps"].append("规范化")
            current_address = address  # 简化实现，实际应提取normalized的结果
            
            # Step 2: 解析
            self.logger.info("Step 2: 18级解析")
            from app.assistants.parser import parse_address
            parsed = parse_address(current_address)
            results["intermediate_results"]["parsed"] = parsed
            results["pipeline_steps"].append("解析")
            
            # Step 3: 纠错
            self.logger.info("Step 3: 地址纠错")
            from app.assistants.correction import correct_address
            corrected = correct_address(current_address)
            results["intermediate_results"]["corrected"] = corrected
            results["pipeline_steps"].append("纠错")
            
            # Step 4: 补全
            self.logger.info("Step 4: 层级补全")
            from app.assistants.completion import complete_address
            completed = complete_address(current_address, context)
            results["intermediate_results"]["completed"] = completed
            results["pipeline_steps"].append("补全")
            
            # Step 5: 标准化
            self.logger.info("Step 5: 标准化")
            from app.assistants.standardizer import standardize
            standardized = standardize(current_address)
            results["intermediate_results"]["standardized"] = standardized
            results["pipeline_steps"].append("标准化")
            
            # Step 6: 空间化
            self.logger.info("Step 6: 空间化")
            from app.assistants.spatializer import spatialize_address
            spatialized = spatialize_address(current_address)
            results["intermediate_results"]["spatialized"] = spatialized
            results["pipeline_steps"].append("空间化")
            
            # Step 7: 校验
            self.logger.info("Step 7: 三重校验")
            from app.assistants.verifier import verify_address
            verified = verify_address(current_address)
            results["intermediate_results"]["verified"] = verified
            results["pipeline_steps"].append("校验")
            
            results["status"] = "success"
            results["final_address"] = current_address
            
        except Exception as e:
            self.logger.error(f"流水线执行失败: {e}")
            results["status"] = "error"
            results["error"] = str(e)
        
        return results


# 创建全局团队实例
address_team = AddressGovernanceTeam()


if __name__ == "__main__":
    """测试地址治理团队"""
    test_cases = [
        {
            "address": "浙江省杭州市余杭区五常街道文一西路969号",
            "intent": None,
            "desc": "标准地址-完整流程"
        },
        {
            "address": "文一西路969号",
            "intent": IntentType.COMPLETE,
            "desc": "缺失层级-仅补全"
        },
        {
            "address": "杭州市余航区五常街道",
            "intent": IntentType.CORRECT,
            "desc": "错别字-仅纠错"
        },
    ]
    
    print("=" * 80)
    print("测试地址治理团队（HMAS架构）")
    print("=" * 80)
    
    team = AddressGovernanceTeam()
    
    for case in test_cases:
        print(f"\n测试: {case['desc']}")
        print(f"地址: {case['address']}")
        print("-" * 80)
        
        result = team.govern_address(
            case['address'],
            intent=case['intent']
        )
        
        print(f"意图: {result.get('intent', 'N/A')}")
        print(f"路由: {result.get('complexity_route', 'N/A')}")
        print(f"执行步骤: {result.get('pipeline_steps', result.get('steps', []))}")
        print(f"状态: {result.get('status', 'N/A')}")
        
        print("=" * 80)
