# app/agent/tools/__init__.py
"""
区块链工具集合
"""

from app.agent.tools.solana import solana_tools
from app.agent.tools.evm import evm_tools
from app.agent.tools.defillama import defillama_tools
from app.agent.tools.graph import graph_tools
from app.agent.tools.coinmarketcap import cmc_tools

# 汇总所有工具
tools = [
    *solana_tools,
    *evm_tools,
    *defillama_tools,
    *graph_tools,
    *cmc_tools,
]

__all__ = ['tools']