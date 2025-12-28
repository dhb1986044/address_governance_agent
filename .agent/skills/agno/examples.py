# -*- coding: utf-8 -*-
"""
Agno 智能体框架 v2.0 代码示例

本文件包含 Agno 框架的常用代码模式和示例，供编程智能体参考使用。
官方文档: https://docs.agno.com/

作者: AI Assistant
版本: 2.0
"""

import os
from typing import List, Optional
from pydantic import BaseModel

# =============================================================================
# 示例1: 基础Agent创建
# =============================================================================

def example_basic_agent():
    """最简单的Agent创建示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions="你是一个有帮助的助手",
        markdown=True,
    )
    
    # 同步运行
    agent.print_response("你好，请介绍一下自己", stream=True)
    
    # 获取响应对象
    response = agent.run("今天天气怎么样？")
    print(response.content)


# =============================================================================
# 示例2: 带Tools的Agent
# =============================================================================

def get_current_time() -> str:
    """获取当前时间。
    
    Returns:
        当前时间字符串
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def search_database(query: str, table: str = "users") -> str:
    """搜索数据库。
    
    Args:
        query: 搜索关键词
        table: 表名，默认为users
    
    Returns:
        JSON格式的搜索结果
    """
    # 模拟数据库查询
    return f'{{"status": "success", "results": [], "query": "{query}", "table": "{table}"}}'


def example_agent_with_tools():
    """带工具的Agent示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[get_current_time, search_database],  # 直接传入函数
        instructions="你是一个数据助手，可以查询时间和搜索数据库",
        markdown=True,
    )
    
    agent.print_response("现在几点了？", stream=True)
    agent.print_response("在users表中搜索张三", stream=True)


# =============================================================================
# 示例3: 使用Toolkit类
# =============================================================================

def example_toolkit_class():
    """使用Toolkit类的示例"""
    from agno.tools import Toolkit
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    
    class CalculatorTools(Toolkit):
        """计算器工具集"""
        
        def __init__(self):
            super().__init__(name="calculator")
            self.register(self.add)
            self.register(self.multiply)
        
        def add(self, a: float, b: float) -> float:
            """将两个数字相加。
            
            Args:
                a: 第一个数字
                b: 第二个数字
            
            Returns:
                两数之和
            """
            return a + b
        
        def multiply(self, a: float, b: float) -> float:
            """将两个数字相乘。
            
            Args:
                a: 第一个数字
                b: 第二个数字
            
            Returns:
                两数之积
            """
            return a * b
    
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[CalculatorTools()],
        instructions="你是一个计算助手",
    )
    
    agent.print_response("请计算 123 + 456")


# =============================================================================
# 示例4: 结构化输出
# =============================================================================

class AnalysisResult(BaseModel):
    """分析结果模型"""
    summary: str
    key_points: List[str]
    sentiment: str
    confidence: float


def example_structured_output():
    """结构化输出示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        output_schema=AnalysisResult,
        instructions="分析用户输入的文本，提取关键信息",
    )
    
    response = agent.run("今天股市大涨，投资者信心增强")
    result: AnalysisResult = response.content
    
    print(f"摘要: {result.summary}")
    print(f"关键点: {result.key_points}")
    print(f"情感: {result.sentiment}")
    print(f"置信度: {result.confidence}")


# =============================================================================
# 示例5: Knowledge/RAG集成
# =============================================================================

def example_knowledge_rag():
    """Knowledge/RAG集成示例"""
    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.chroma import ChromaDb
    from agno.knowledge.embedder.openai import OpenAIEmbedder
    from agno.knowledge.document import Document
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    
    # 1. 创建向量数据库
    vector_db = ChromaDb(
        collection="example_kb",
        path="./chroma_db",
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        persistent_client=True,
    )
    
    # 2. 创建Knowledge实例
    knowledge = Knowledge(
        vector_db=vector_db,
        max_results=5,
    )
    
    # 3. 添加文档 (使用Document对象)
    documents = [
        Document(
            content="公司年假政策：员工入职满一年后，每年享有10天带薪年假。",
            meta_data={"category": "hr", "type": "policy"}
        ),
        Document(
            content="报销流程：员工需在费用发生后30天内提交报销申请。",
            meta_data={"category": "finance", "type": "policy"}
        ),
    ]
    
    # 批量插入文档
    vector_db.insert(content_hash="example_docs", documents=documents)
    
    # 4. 创建带Knowledge的Agent
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        knowledge=knowledge,
        search_knowledge=True,  # 关键：启用Agentic RAG
        instructions="使用知识库回答问题，如果知识库中没有相关信息，请明确告知",
    )
    
    agent.print_response("公司的年假政策是什么？")


# =============================================================================
# 示例6: 本地Embedder (无需API)
# =============================================================================

def example_local_embedder():
    """使用本地Embedder的示例（无需外部API）"""
    from agno.knowledge.knowledge import Knowledge
    from agno.vectordb.chroma import ChromaDb
    from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
    
    # 使用本地中文模型
    embedder = SentenceTransformerEmbedder(
        id="BAAI/bge-small-zh-v1.5",  # 中文向量模型
        normalize_embeddings=True,
    )
    
    vector_db = ChromaDb(
        collection="local_kb",
        path="./local_chroma",
        embedder=embedder,
        persistent_client=True,
    )
    
    knowledge = Knowledge(vector_db=vector_db)
    
    print("本地Knowledge已创建，无需外部API")


# =============================================================================
# 示例7: Team多智能体协作
# =============================================================================

def example_team():
    """Team多智能体协作示例"""
    from agno.team.team import Team
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.tools.duckduckgo import DuckDuckGoTools
    
    # 创建专业Agent
    researcher = Agent(
        name="研究员",
        model=OpenAIChat(id="gpt-4o"),
        tools=[DuckDuckGoTools()],
        instructions="你是一个研究员，负责搜索和整理信息",
    )
    
    writer = Agent(
        name="作家",
        model=OpenAIChat(id="gpt-4o"),
        instructions="你是一个作家，负责将信息整理成优美的文章",
    )
    
    # 创建Team
    team = Team(
        members=[researcher, writer],  # 注意：使用members参数
        model=OpenAIChat(id="gpt-4o"),
        instructions="协调研究员和作家，完成高质量的内容创作",
    )
    
    team.print_response("写一篇关于人工智能发展的短文")


# =============================================================================
# 示例8: 会话持久化
# =============================================================================

def example_session_persistence():
    """会话持久化示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.db.sqlite import SqliteDb
    
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        db=SqliteDb(db_file="./sessions.db"),
        user_id="user-123",
        session_id="session-abc",
        add_history_to_context=True,  # 添加历史到上下文
        num_history_runs=5,           # 保留最近5次对话
        instructions="你是一个记忆力很强的助手",
    )
    
    # 第一次对话
    agent.print_response("我叫张三")
    
    # 第二次对话（Agent会记住之前的内容）
    agent.print_response("我叫什么名字？")


# =============================================================================
# 示例9: 智谱GLM模型配置
# =============================================================================

def example_zhipu_model():
    """使用智谱GLM模型的示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    
    # 通过OpenAI兼容接口使用智谱模型
    zhipu_model = OpenAIChat(
        id="glm-4",
        api_key=os.getenv("ZHIPU_API_KEY"),
        base_url="https://open.bigmodel.cn/api/paas/v4/",
    )
    
    agent = Agent(
        model=zhipu_model,
        instructions="你是一个有帮助的中文助手",
        markdown=True,
    )
    
    agent.print_response("请用中文介绍一下自己")


def example_zhipu_embedder():
    """使用智谱Embedding的示例"""
    from agno.knowledge.embedder.openai import OpenAIEmbedder
    
    zhipu_embedder = OpenAIEmbedder(
        id="embedding-3-pro",
        api_key=os.getenv("ZHIPU_API_KEY"),
        base_url="https://open.bigmodel.cn/api/paas/v4/",
    )
    
    print("智谱Embedder已配置")


# =============================================================================
# 示例10: AgentOS生产部署
# =============================================================================

def example_agentos_production():
    """AgentOS生产部署示例"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.os import AgentOS
    from agno.db.sqlite import SqliteDb  # 开发用SQLite
    # from agno.db.postgres import PostgresDb  # 生产环境用PostgreSQL
    
    # 创建Agent
    agent = Agent(
        name="ProductionAgent",
        model=OpenAIChat(id="gpt-4o"),
        db=SqliteDb(db_file="./agent.db"),
        add_history_to_context=True,
        markdown=True,
        debug_mode=False,  # 生产环境关闭调试
    )
    
    # 创建AgentOS
    agent_os = AgentOS(agents=[agent])
    
    # 获取FastAPI应用
    app = agent_os.get_app()
    
    # 运行方式:
    # fastapi dev your_script.py
    # 或
    # agent_os.serve(app="your_script:app", reload=True)
    
    return app


# =============================================================================
# 性能最佳实践
# =============================================================================

def best_practice_agent_reuse():
    """Agent复用最佳实践"""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    
    # ✅ 正确：创建一次，多次使用
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions="你是一个有帮助的助手",
    )
    
    queries = ["问题1", "问题2", "问题3"]
    
    for query in queries:
        response = agent.run(query)
        print(f"Q: {query}")
        print(f"A: {response.content}")
        print()
    
    # ❌ 错误：不要在循环中创建Agent
    # for query in queries:
    #     agent = Agent(...)  # 严重性能问题！
    #     agent.run(query)


# =============================================================================
# 主函数
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Agno v2.0 示例代码")
    print("=" * 60)
    print()
    print("可用示例:")
    print("  1. example_basic_agent()       - 基础Agent")
    print("  2. example_agent_with_tools()  - 带工具的Agent")
    print("  3. example_toolkit_class()     - Toolkit类")
    print("  4. example_structured_output() - 结构化输出")
    print("  5. example_knowledge_rag()     - Knowledge/RAG")
    print("  6. example_local_embedder()    - 本地Embedder")
    print("  7. example_team()              - Team协作")
    print("  8. example_session_persistence() - 会话持久化")
    print("  9. example_zhipu_model()       - 智谱模型")
    print(" 10. example_agentos_production() - AgentOS部署")
    print()
    print("请根据需要调用相应的示例函数")
