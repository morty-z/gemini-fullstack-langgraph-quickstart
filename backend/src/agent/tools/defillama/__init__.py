# app/agent/tools/defillama/__init__.py

from app.agent.tools.defillama.defillama_tools import defillama_tools

# DeFiLlama 工具分类
DEFILLAMA_TOOL_CATEGORIES = {
    "DeFiLlama - 协议数据": [
        "GetProtocolInfo",
        "GetDeFiRankings", 
        "GetChainTVLRanking"
    ],
    "DeFiLlama - 价格数据": [
        "GetTokenPrices"
    ],
    "DeFiLlama - 交易数据": [
        "GetDEXOverview"
    ],
    "DeFiLlama - 收益数据": [
        "GetYieldOpportunities"
    ],
    "DeFiLlama - 稳定币数据": [
        "GetStablecoinOverview"
    ]
}

__all__ = [
    'defillama_tools',
    'DEFILLAMA_TOOL_CATEGORIES'
]