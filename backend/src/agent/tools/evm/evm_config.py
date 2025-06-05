# app/agent/tools/evm/evm_config.py
"""
EVM 工具模块配置文件 - 外部化配置
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ===== 基础配置类 =====

@dataclass
class ChainInfo:
    """链信息配置"""
    chain_id: int
    name: str
    native_token: str
    explorer_url: str
    decimals: int = 18
    is_testnet: bool = False

@dataclass
class APIConfig:
    """API 配置"""
    timeout: int = 10
    max_retries: int = 3
    rate_limit_delay: float = 0.2
    headers: Optional[Dict[str, str]] = None

# ===== API 配置 =====

# API Keys（从环境变量获取）
API_KEYS = {
    "infura": os.getenv("INFURA_API_KEY", ""),
    "alchemy": os.getenv("ALCHEMY_API_KEY", ""),
    "quicknode": os.getenv("QUICKNODE_API_KEY", ""),
    "moralis": os.getenv("MORALIS_API_KEY", ""),
    "ankr": os.getenv("ANKR_API_KEY", ""),
}

# 请求配置
REQUEST_CONFIG = APIConfig(
    timeout=int(os.getenv("EVM_TIMEOUT", "15")),
    max_retries=int(os.getenv("EVM_MAX_RETRIES", "3")),
    rate_limit_delay=float(os.getenv("EVM_RATE_LIMIT", "0.2")),
    headers={
        "Content-Type": "application/json",
        "User-Agent": "BlockchainAgent/1.0"
    }
)

# ===== 网络配置 =====

# 支持的 EVM 链
SUPPORTED_CHAINS = {
    "ethereum": ChainInfo(
        chain_id=1,
        name="Ethereum Mainnet",
        native_token="ETH",
        explorer_url=os.getenv("ETHEREUM_EXPLORER", "https://etherscan.io"),
        decimals=18
    ),
    
    "bsc": ChainInfo(
        chain_id=56,
        name="BNB Smart Chain",
        native_token="BNB", 
        explorer_url=os.getenv("BSC_EXPLORER", "https://bscscan.com"),
        decimals=18
    ),
    
    "polygon": ChainInfo(
        chain_id=137,
        name="Polygon",
        native_token="MATIC",
        explorer_url=os.getenv("POLYGON_EXPLORER", "https://polygonscan.com"),
        decimals=18
    ),
    
    "arbitrum": ChainInfo(
        chain_id=42161,
        name="Arbitrum One",
        native_token="ETH",
        explorer_url=os.getenv("ARBITRUM_EXPLORER", "https://arbiscan.io"),
        decimals=18
    ),
    
    "optimism": ChainInfo(
        chain_id=10,
        name="Optimism",
        native_token="ETH",
        explorer_url=os.getenv("OPTIMISM_EXPLORER", "https://optimistic.etherscan.io"),
        decimals=18
    ),
    
    "avalanche": ChainInfo(
        chain_id=43114,
        name="Avalanche C-Chain",
        native_token="AVAX",
        explorer_url=os.getenv("AVALANCHE_EXPLORER", "https://snowtrace.io"),
        decimals=18
    ),
    
    "base": ChainInfo(
        chain_id=8453,
        name="Base",
        native_token="ETH",
        explorer_url=os.getenv("BASE_EXPLORER", "https://basescan.org"),
        decimals=18
    ),
    
    "fantom": ChainInfo(
        chain_id=250,
        name="Fantom Opera",
        native_token="FTM",
        explorer_url=os.getenv("FANTOM_EXPLORER", "https://ftmscan.com"),
        decimals=18
    ),
}

# RPC 端点配置（按优先级排序）
RPC_ENDPOINTS = {
    "ethereum": [
        # 优先使用付费服务（如果有 API Key）
        f"https://mainnet.infura.io/v3/{API_KEYS['infura']}" if API_KEYS['infura'] else None,
        f"https://eth-mainnet.g.alchemy.com/v2/{API_KEYS['alchemy']}" if API_KEYS['alchemy'] else None,
        f"https://rpc.ankr.com/eth/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        
        # 免费公共 RPC
        os.getenv("ETHEREUM_RPC_1", "https://eth.llamarpc.com"),
        os.getenv("ETHEREUM_RPC_2", "https://ethereum.publicnode.com"),
        os.getenv("ETHEREUM_RPC_3", "https://rpc.ankr.com/eth"),
        os.getenv("ETHEREUM_RPC_4", "https://cloudflare-eth.com"),
        os.getenv("ETHEREUM_RPC_5", "https://eth-mainnet.public.blastapi.io"),
        "https://eth.drpc.org",
        "https://rpc.flashbots.net",
    ],
    
    "bsc": [
        f"https://rpc.ankr.com/bsc/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        os.getenv("BSC_RPC_1", "https://binance.llamarpc.com"),
        os.getenv("BSC_RPC_2", "https://bsc-dataseed.binance.org"),
        os.getenv("BSC_RPC_3", "https://bsc-dataseed1.defibit.io"),
        os.getenv("BSC_RPC_4", "https://bsc.publicnode.com"),
        "https://rpc.ankr.com/bsc",
        "https://bsc-dataseed1.ninicoin.io",
    ],
    
    "polygon": [
        f"https://polygon-mainnet.infura.io/v3/{API_KEYS['infura']}" if API_KEYS['infura'] else None,
        f"https://polygon-mainnet.g.alchemy.com/v2/{API_KEYS['alchemy']}" if API_KEYS['alchemy'] else None,
        f"https://rpc.ankr.com/polygon/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        os.getenv("POLYGON_RPC_1", "https://polygon.llamarpc.com"),
        os.getenv("POLYGON_RPC_2", "https://polygon-rpc.com"),
        os.getenv("POLYGON_RPC_3", "https://polygon.drpc.org"),
        "https://polygon-mainnet.public.blastapi.io",
        "https://polygon.publicnode.com",
    ],
    
    "arbitrum": [
        f"https://arbitrum-mainnet.infura.io/v3/{API_KEYS['infura']}" if API_KEYS['infura'] else None,
        f"https://arb-mainnet.g.alchemy.com/v2/{API_KEYS['alchemy']}" if API_KEYS['alchemy'] else None,
        f"https://rpc.ankr.com/arbitrum/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        os.getenv("ARBITRUM_RPC_1", "https://arbitrum.llamarpc.com"),
        os.getenv("ARBITRUM_RPC_2", "https://arb1.arbitrum.io/rpc"),
        "https://arbitrum-one.publicnode.com",
        "https://arbitrum.drpc.org",
    ],
    
    "optimism": [
        f"https://optimism-mainnet.infura.io/v3/{API_KEYS['infura']}" if API_KEYS['infura'] else None,
        f"https://opt-mainnet.g.alchemy.com/v2/{API_KEYS['alchemy']}" if API_KEYS['alchemy'] else None,
        f"https://rpc.ankr.com/optimism/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        os.getenv("OPTIMISM_RPC_1", "https://optimism.llamarpc.com"),
        os.getenv("OPTIMISM_RPC_2", "https://mainnet.optimism.io"),
        "https://optimism.publicnode.com",
        "https://optimism.drpc.org",
    ],
    
    "avalanche": [
        f"https://rpc.ankr.com/avalanche/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        os.getenv("AVALANCHE_RPC_1", "https://avalanche.public-rpc.com"),
        os.getenv("AVALANCHE_RPC_2", "https://api.avax.network/ext/bc/C/rpc"),
        "https://avalanche.drpc.org",
        "https://avalanche-c-chain.publicnode.com",
    ],
    
    "base": [
        f"https://rpc.ankr.com/base/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        os.getenv("BASE_RPC_1", "https://base.llamarpc.com"),
        os.getenv("BASE_RPC_2", "https://mainnet.base.org"),
        "https://base.publicnode.com",
        "https://base.drpc.org",
    ],
    
    "fantom": [
        f"https://rpc.ankr.com/fantom/{API_KEYS['ankr']}" if API_KEYS['ankr'] else None,
        os.getenv("FANTOM_RPC_1", "https://rpc.ftm.tools"),
        os.getenv("FANTOM_RPC_2", "https://fantom.publicnode.com"),
        "https://fantom.drpc.org",
        "https://rpcapi.fantom.network",
    ],
}

# 过滤掉 None 值的 RPC 端点
for chain in RPC_ENDPOINTS:
    RPC_ENDPOINTS[chain] = [rpc for rpc in RPC_ENDPOINTS[chain] if rpc]

# ===== 常用代币配置 =====

# 每个链的常用代币（从环境变量或使用默认值）
COMMON_TOKENS = {
    "ethereum": {
        "USDT": os.getenv("ETH_USDT_ADDRESS", "0xdAC17F958D2ee523a2206206994597C13D831ec7"),
        "USDC": os.getenv("ETH_USDC_ADDRESS", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),
        "DAI": os.getenv("ETH_DAI_ADDRESS", "0x6B175474E89094C44Da98b954EedeAC495271d0F"),
        "WETH": os.getenv("ETH_WETH_ADDRESS", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"),
        "LINK": os.getenv("ETH_LINK_ADDRESS", "0x514910771AF9Ca656af840dff83E8264EcF986CA"),
        "UNI": os.getenv("ETH_UNI_ADDRESS", "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"),
        "WBTC": os.getenv("ETH_WBTC_ADDRESS", "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"),
        "AAVE": os.getenv("ETH_AAVE_ADDRESS", "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9"),
    },
    
    "bsc": {
        "USDT": os.getenv("BSC_USDT_ADDRESS", "0x55d398326f99059fF775485246999027B3197955"),
        "USDC": os.getenv("BSC_USDC_ADDRESS", "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"),
        "BUSD": os.getenv("BSC_BUSD_ADDRESS", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"),
        "WBNB": os.getenv("BSC_WBNB_ADDRESS", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"),
        "CAKE": os.getenv("BSC_CAKE_ADDRESS", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"),
        "ETH": os.getenv("BSC_ETH_ADDRESS", "0x2170Ed0880ac9A755fd29B2688956BD959F933F8"),
    },
    
    "polygon": {
        "USDT": os.getenv("POLYGON_USDT_ADDRESS", "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"),
        "USDC": os.getenv("POLYGON_USDC_ADDRESS", "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"),
        "DAI": os.getenv("POLYGON_DAI_ADDRESS", "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063"),
        "WMATIC": os.getenv("POLYGON_WMATIC_ADDRESS", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"),
        "WETH": os.getenv("POLYGON_WETH_ADDRESS", "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"),
        "LINK": os.getenv("POLYGON_LINK_ADDRESS", "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39"),
    },
}

# ===== 缓存配置 =====

CACHE_CONFIG = {
    "enabled": os.getenv("EVM_CACHE_ENABLED", "true").lower() == "true",
    "balance_ttl": int(os.getenv("EVM_BALANCE_CACHE_TTL", "60")),  # 余额缓存1分钟
    "gas_price_ttl": int(os.getenv("EVM_GAS_CACHE_TTL", "30")),   # Gas价格缓存30秒
    "tx_info_ttl": int(os.getenv("EVM_TX_CACHE_TTL", "300")),     # 交易信息缓存5分钟
    "max_cache_size": int(os.getenv("EVM_MAX_CACHE_SIZE", "1000")),
    "cleanup_interval": int(os.getenv("EVM_CACHE_CLEANUP", "600")) # 10分钟清理一次
}

# ===== 显示配置 =====

DISPLAY_CONFIG = {
    "max_tokens_display": int(os.getenv("EVM_MAX_TOKENS_DISPLAY", "50")),
    "decimal_places": int(os.getenv("EVM_DECIMAL_PLACES", "6")),
    "thousands_separator": os.getenv("EVM_THOUSANDS_SEP", ","),
    "currency_symbol": os.getenv("EVM_CURRENCY_SYMBOL", "$"),
    "date_format": os.getenv("EVM_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
    "address_short_length": int(os.getenv("EVM_ADDRESS_SHORT_LEN", "6")),
    "min_value_display": float(os.getenv("EVM_MIN_VALUE_DISPLAY", "0.01")),  # 最小显示价值
}

# ===== 安全配置 =====

SECURITY_CONFIG = {
    "max_batch_size": int(os.getenv("EVM_MAX_BATCH_SIZE", "100")),  # 批量查询最大数量
    "max_concurrent_requests": int(os.getenv("EVM_MAX_CONCURRENT", "10")),
    "request_timeout": int(os.getenv("EVM_REQUEST_TIMEOUT", "30")),
    "verify_ssl": os.getenv("EVM_VERIFY_SSL", "true").lower() == "true",
}

# ===== 错误处理配置 =====

ERROR_CONFIG = {
    "log_errors": os.getenv("EVM_LOG_ERRORS", "true").lower() == "true",
    "retry_on_errors": [429, 500, 502, 503, 504],  # 可重试的HTTP状态码
    "circuit_breaker_enabled": os.getenv("EVM_CIRCUIT_BREAKER", "true").lower() == "true",
    "failure_threshold": int(os.getenv("EVM_FAILURE_THRESHOLD", "5")),
    "recovery_timeout": int(os.getenv("EVM_RECOVERY_TIMEOUT", "300")),  # 5分钟
}

# ===== 性能配置 =====

PERFORMANCE_CONFIG = {
    "connection_pool_size": int(os.getenv("EVM_POOL_SIZE", "10")),
    "keep_alive": os.getenv("EVM_KEEP_ALIVE", "true").lower() == "true",
    "use_session": os.getenv("EVM_USE_SESSION", "true").lower() == "true",
    "compress_requests": os.getenv("EVM_COMPRESS", "false").lower() == "true",
}

# ===== 调试配置 =====

DEBUG_CONFIG = {
    "enabled": os.getenv("EVM_DEBUG", "false").lower() == "true",
    "log_requests": os.getenv("EVM_LOG_REQUESTS", "false").lower() == "true",
    "log_responses": os.getenv("EVM_LOG_RESPONSES", "false").lower() == "true",
    "show_timing": os.getenv("EVM_SHOW_TIMING", "false").lower() == "true",
    "save_failed_requests": os.getenv("EVM_SAVE_FAILED", "false").lower() == "true",
}

# ===== 工具函数 =====

def get_chain_info(chain: str) -> Optional[ChainInfo]:
    """获取链信息"""
    return SUPPORTED_CHAINS.get(chain.lower())

def get_rpc_endpoints(chain: str) -> List[str]:
    """获取链的 RPC 端点列表"""
    return RPC_ENDPOINTS.get(chain.lower(), [])

def get_common_tokens(chain: str) -> Dict[str, str]:
    """获取链的常用代币"""
    return COMMON_TOKENS.get(chain.lower(), {})

def is_testnet(chain: str) -> bool:
    """判断是否是测试网"""
    chain_info = get_chain_info(chain)
    return chain_info.is_testnet if chain_info else False

def get_explorer_url(chain: str, tx_hash: str = None, address: str = None) -> str:
    """构建区块浏览器 URL"""
    chain_info = get_chain_info(chain)
    if not chain_info:
        return ""
    
    base_url = chain_info.explorer_url
    
    if tx_hash:
        return f"{base_url}/tx/{tx_hash}"
    elif address:
        return f"{base_url}/address/{address}"
    else:
        return base_url

def format_address(address: str, short: bool = True) -> str:
    """格式化地址显示"""
    if not address or len(address) < 10:
        return address
    
    if short:
        length = DISPLAY_CONFIG["address_short_length"]
        return f"{address[:length]}...{address[-length:]}"
    return address

def format_value(value: float, decimals: int = None) -> str:
    """格式化数值显示"""
    if decimals is None:
        decimals = DISPLAY_CONFIG["decimal_places"]
    
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.{decimals}f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.{decimals}f}K"
    else:
        return f"{value:.{decimals}f}"

def validate_config() -> List[str]:
    """验证配置的完整性"""
    errors = []
    
    # 检查必要的链配置
    for chain, info in SUPPORTED_CHAINS.items():
        if not info.explorer_url:
            errors.append(f"链 {chain} 缺少 explorer_url")
        
        # 检查是否有可用的 RPC 端点
        endpoints = get_rpc_endpoints(chain)
        if not endpoints:
            errors.append(f"链 {chain} 没有配置 RPC 端点")
    
    # 检查缓存配置
    if CACHE_CONFIG["balance_ttl"] < 0:
        errors.append("balance_ttl 不能为负数")
    
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
            logger.warning(f"EVM配置警告: {error}")

# ===== 默认导出 =====

# 向后兼容的默认配置
DEFAULT_TIMEOUT = REQUEST_CONFIG.timeout
MAX_RETRIES = REQUEST_CONFIG.max_retries 
RATE_LIMIT_DELAY = REQUEST_CONFIG.rate_limit_delay
