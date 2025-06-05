# app/agent/tools/solana/__init__.py

from app.agent.tools.solana.solana_tools import solana_tools

# Solana 工具分类
SOLANA_TOOL_CATEGORIES = {
    "账户查询": [
        "GetSolanaBalance",      # SOL 余额
        "GetSolanaAccountInfo",  # 账户详细信息
    ],
    "SPL Token": [
        "GetSolanaTokens",       # 所有 SPL 代币
        "GetTokenSupply",        # 代币总供应量
        "GetTokenAccountInfo",   # 代币账户信息
    ],
    "交易查询": [
        "GetSolanaTransaction",        # 交易详情
        "GetSolanaRecentTransactions", # 最近交易
    ],
    "系统信息": [
        "GetSlotInfo",          # Slot 信息
        "GetRentExemption",     # 租金计算
    ]
}

__all__ = [
    'solana_tools',
    'SOLANA_TOOL_CATEGORIES'
]