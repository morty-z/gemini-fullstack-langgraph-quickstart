# app/agent/tools/graph/__init__.py
"""
The Graph Protocol 工具集
智能查询区块链数据
"""

from app.agent.tools.graph.graph_tools import (
    smart_graph_query,
    graph_multi_query,
    graph_explain_query
)
from langchain.tools import Tool

# 创建 LangChain 工具
graph_tools = [
    Tool(
        name="SmartGraphQuery",
        description="""
智能查询区块链链上实时数据。专门用于查询需要精确数值的数据。

特别适合查询：
- 借贷池利用率（Utilization Rate = 总借款/总流动性）
- 实时利率（借款利率、存款利率）
- 池子的具体指标（TVL、交易量、流动性、手续费）
- 用户仓位详情
- 清算事件
- 具体交易数据

支持的协议：
- DEX: Uniswap, Sushiswap, Curve, Balancer
- 借贷: Aave（利用率、利率）, Compound
- 其他 DeFi 协议

注意：如需查询利用率、利率等具体数值，请使用此工具而非 GetProtocolInfo。
""",
        func=smart_graph_query
    ),
    
    Tool(
        name="GraphMultiQuery",
        description="批量查询多个问题。输入用分号分隔的问题列表，最多5个。示例：'Uniswap TVL; Aave 借贷量; Curve 稳定币池'",
        func=graph_multi_query
    ),
    
    Tool(
        name="GraphExplainQuery",
        description="解释查询的执行过程，显示使用的子图、GraphQL查询等详细信息。用于调试和学习。",
        func=graph_explain_query
    ),
]

__all__ = ['graph_tools']