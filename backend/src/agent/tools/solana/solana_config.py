# app/agent/tools/solana/solana_config.py
"""
Solana 配置文件 - 纯 RPC 配置
只包含 Solana RPC 相关配置，不包含外部 API
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ===== 基础配置类 =====

@dataclass
class TokenInfo:
    """代币信息"""
    symbol: str
    mint: str
    decimals: int
    name: str

@dataclass
class RPCConfig:
    """RPC 配置"""
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.1
    commitment: str = "confirmed"

# ===== 程序 ID =====

# 系统程序
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"

# Metaplex 程序
METAPLEX_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
METAPLEX_CANDY_MACHINE_V2 = "cndy3Z4yapfJBmL3ShUp5exZKqR3z33thTzeNMm2gRZ"

# DeFi 程序
SERUM_PROGRAM_ID = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
RAYDIUM_AMM_PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
ORCA_WHIRLPOOL_PROGRAM = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
JUPITER_AGGREGATOR_V6 = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

# ===== 主要 DEX 和 AMM 程序 =====

DEX_PROGRAMS = {
    "RAYDIUM": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "ORCA": "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",
    "JUPITER": "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
    "SERUM": "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
    "PHOENIX": "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY",
    "LIFINITY": "EewxydAPCCVuNEyrVN68PuSYdQ7wKn27V9Gjeoi8dy3S",
}

# ===== 常用 SPL 代币列表（仅用于识别，不包含价格） =====

COMMON_TOKENS: Dict[str, TokenInfo] = {
    # 稳定币
    "USDC": TokenInfo(
        symbol="USDC",
        mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        decimals=6,
        name="USD Coin"
    ),
    "USDT": TokenInfo(
        symbol="USDT",
        mint="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        decimals=6,
        name="Tether USD"
    ),
    
    # 主要代币
    "SOL": TokenInfo(
        symbol="SOL",
        mint="So11111111111111111111111111111111111111112",
        decimals=9,
        name="Wrapped SOL"
    ),
    "RAY": TokenInfo(
        symbol="RAY",
        mint="4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
        decimals=6,
        name="Raydium"
    ),
    "SRM": TokenInfo(
        symbol="SRM",
        mint="SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt",
        decimals=6,
        name="Serum"
    ),
    
    # DeFi 代币
    "JUP": TokenInfo(
        symbol="JUP",
        mint="JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        decimals=6,
        name="Jupiter"
    ),
    "ORCA": TokenInfo(
        symbol="ORCA",
        mint="orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
        decimals=6,
        name="Orca"
    ),
    
    # Meme 币
    "BONK": TokenInfo(
        symbol="BONK",
        mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        decimals=5,
        name="Bonk"
    ),
    "WIF": TokenInfo(
        symbol="WIF",
        mint="EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        decimals=6,
        name="dogwifhat"
    ),
    
    # 其他重要代币
    "JTO": TokenInfo(
        symbol="JTO",
        mint="jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
        decimals=9,
        name="Jito"
    ),
    "PYTH": TokenInfo(
        symbol="PYTH",
        mint="HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
        decimals=6,
        name="Pyth Network"
    ),
}

# ===== Solana RPC 提供商配置 =====

# RPC 端点（按优先级排序）
RPC_PROVIDERS = [
    # Helius (如果有 API key)
    f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}" if os.getenv('HELIUS_API_KEY') else None,
    
    # Alchemy (如果有 API key)
    f"https://solana-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_SOLANA_KEY')}" if os.getenv('ALCHEMY_SOLANA_KEY') else None,
    
    # QuickNode (如果有端点)
    os.getenv('QUICKNODE_SOLANA_URL') if os.getenv('QUICKNODE_SOLANA_URL') else None,
    
    # 免费公共 RPC（按可靠性排序）
    os.getenv("SOLANA_RPC_1", "https://api.mainnet-beta.solana.com"),
    os.getenv("SOLANA_RPC_2", "https://solana-api.projectserum.com"),
    os.getenv("SOLANA_RPC_3", "https://rpc.ankr.com/solana"),
    os.getenv("SOLANA_RPC_4", "https://solana.public-rpc.com"),
    
    # 其他免费端点
    "https://solana-mainnet.g.alchemy.com/v2/demo",
    "https://api.metaplex.solana.com",
    "https://solana-mainnet.core.chainstack.com/demo",
    "https://rpc.xnftdata.com",
    "https://ssc-dao.genesysgo.net",
]

# 过滤掉 None 值
RPC_PROVIDERS = [rpc for rpc in RPC_PROVIDERS if rpc]

# ===== Solana 浏览器 =====

EXPLORERS = {
    "solscan": os.getenv("SOLSCAN_URL", "https://solscan.io"),
    "solana_explorer": os.getenv("SOLANA_EXPLORER_URL", "https://explorer.solana.com"),
    "solana_beach": os.getenv("SOLANA_BEACH_URL", "https://solanabeach.io"),
    "solana_fm": os.getenv("SOLANA_FM_URL", "https://solana.fm"),
}

# ===== RPC 配置参数 =====

# 请求配置
REQUEST_CONFIG = RPCConfig(
    timeout=int(os.getenv("SOLANA_TIMEOUT", "30")),
    max_retries=int(os.getenv("SOLANA_MAX_RETRIES", "3")),
    rate_limit_delay=float(os.getenv("SOLANA_RATE_LIMIT", "0.1")),
    commitment=os.getenv("SOLANA_COMMITMENT", "confirmed")
)

# 向后兼容
DEFAULT_TIMEOUT = REQUEST_CONFIG.timeout
MAX_RETRIES = REQUEST_CONFIG.max_retries
RATE_LIMIT_DELAY = REQUEST_CONFIG.rate_limit_delay
DEFAULT_COMMITMENT = REQUEST_CONFIG.commitment

# ===== 显示配置 =====

DISPLAY_CONFIG = {
    "max_tokens_display": int(os.getenv("SOLANA_MAX_TOKENS_DISPLAY", "50")),
    "decimal_places": int(os.getenv("SOLANA_DECIMAL_PLACES", "9")),
    "address_short_length": int(os.getenv("SOLANA_ADDRESS_SHORT_LEN", "8")),
    "signature_short_length": int(os.getenv("SOLANA_SIGNATURE_SHORT_LEN", "20")),
    "max_logs_display": int(os.getenv("SOLANA_MAX_LOGS_DISPLAY", "5")),
}

# ===== 缓存配置 =====

CACHE_CONFIG = {
    "enabled": os.getenv("SOLANA_CACHE_ENABLED", "true").lower() == "true",
    "ttl": int(os.getenv("SOLANA_CACHE_TTL", "60")),  # 缓存60秒
    "max_size": int(os.getenv("SOLANA_CACHE_MAX_SIZE", "500")),
}

# ===== 错误处理配置 =====

ERROR_CONFIG = {
    "log_errors": os.getenv("SOLANA_LOG_ERRORS", "true").lower() == "true",
    "retry_on_errors": [429, 500, 502, 503, 504],
    "circuit_breaker_enabled": os.getenv("SOLANA_CIRCUIT_BREAKER", "true").lower() == "true",
    "failure_threshold": int(os.getenv("SOLANA_FAILURE_THRESHOLD", "5")),
    "recovery_timeout": int(os.getenv("SOLANA_RECOVERY_TIMEOUT", "300")),
}

# ===== 调试配置 =====

DEBUG_CONFIG = {
    "enabled": os.getenv("SOLANA_DEBUG", "false").lower() == "true",
    "log_requests": os.getenv("SOLANA_LOG_REQUESTS", "false").lower() == "true",
    "log_responses": os.getenv("SOLANA_LOG_RESPONSES", "false").lower() == "true",
    "show_timing": os.getenv("SOLANA_SHOW_TIMING", "false").lower() == "true",
}

# ===== 工具函数 =====

def format_lamports(lamports: int, show_sol: bool = True) -> str:
    """格式化 lamports 为 SOL"""
    sol = lamports / 1e9
    if show_sol:
        return f"{sol:.9f} SOL"
    return f"{sol:.9f}"

def format_address(address: str, short: bool = True) -> str:
    """格式化地址显示"""
    if not address or len(address) < 20:
        return address
    
    if short:
        length = DISPLAY_CONFIG["address_short_length"]
        return f"{address[:length]}...{address[-length:]}"
    return address

def format_signature(signature: str, short: bool = True) -> str:
    """格式化交易签名显示"""
    if not signature or len(signature) < 40:
        return signature
    
    if short:
        length = DISPLAY_CONFIG["signature_short_length"]
        return f"{signature[:length]}..."
    return signature

def get_token_by_mint(mint: str) -> Optional[TokenInfo]:
    """根据 mint 地址获取代币信息"""
    for symbol, token_info in COMMON_TOKENS.items():
        if token_info.mint == mint:
            return token_info
    return None

def get_token_by_symbol(symbol: str) -> Optional[TokenInfo]:
    """根据符号获取代币信息"""
    return COMMON_TOKENS.get(symbol.upper())

def is_system_program(program_id: str) -> bool:
    """判断是否为系统程序"""
    system_programs = [
        SYSTEM_PROGRAM_ID,
        TOKEN_PROGRAM_ID,
        TOKEN_2022_PROGRAM_ID,
        ASSOCIATED_TOKEN_PROGRAM_ID,
    ]
    return program_id in system_programs

def validate_config() -> List[str]:
    """验证配置的完整性"""
    errors = []
    
    # 检查 RPC 端点
    if not RPC_PROVIDERS:
        errors.append("没有配置任何 RPC 端点")
    
    # 检查请求配置
    if REQUEST_CONFIG.timeout <= 0:
        errors.append("timeout 必须大于0")
    
    if REQUEST_CONFIG.max_retries <= 0:
        errors.append("max_retries 必须大于0")
    
    # 检查显示配置
    if DISPLAY_CONFIG["max_tokens_display"] <= 0:
        errors.append("max_tokens_display 必须大于0")
    
    return errors

# 配置验证（如果启用调试模式）
if DEBUG_CONFIG["enabled"]:
    config_errors = validate_config()
    if config_errors:
        import logging
        logger = logging.getLogger(__name__)
        for error in config_errors:
            logger.warning(f"Solana配置警告: {error}")

# ===== Helius 特殊功能（仅标记是否可用） =====

HELIUS_FEATURES = {
    "available": bool(os.getenv('HELIUS_API_KEY')),
    "das_api": bool(os.getenv('HELIUS_API_KEY')),  # Digital Asset Standard API
    "enhanced_transactions": bool(os.getenv('HELIUS_API_KEY')),
    "parsed_transactions": bool(os.getenv('HELIUS_API_KEY')),
}