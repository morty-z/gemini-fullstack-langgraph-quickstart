# app/agent/tools/evm/__init__.py

from app.agent.tools.evm.evm_tools import evm_tools

# EVM 工具分类
EVM_TOOL_CATEGORIES = {
    "账户查询": [
        "GetNativeBalance",      # 原生代币余额
        "GetAccountInfo",        # 账户详细信息
        "CheckIsContract",       # 检查是否合约
    ],
    "ERC20代币": [
        "GetTokenBalance",       # 代币余额
        "GetTokenMetadata",      # 代币元数据
        "GetTokenAllowance",     # 授权额度
    ],
    "交易查询": [
        "GetTransaction",        # 交易详情
        "GetTransactionReceipt", # 交易收据
    ],
    "区块链信息": [
        "GetGasPrice",          # Gas 价格
        "GetBlockInfo",         # 区块信息
    ]
}

__all__ = [
    'evm_tools',
    'EVM_TOOL_CATEGORIES'
]