# app/agent/tools/defillama/defillama_config.py
"""
DeFiLlama API 配置文件
包含所有 API 端点和常量定义
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import os

# DeFiLlama API 基础配置
BASE_URL = "https://api.llama.fi"
COINS_BASE_URL = "https://coins.llama.fi"
YIELDS_BASE_URL = "https://yields.llama.fi"
STABLECOINS_BASE_URL = "https://stablecoins.llama.fi"

# API 端点
ENDPOINTS = {
    # TVL 相关
    "protocols": "/protocols",
    "protocol": "/protocol/{protocol}",
    "tvl_chart": "/charts/{chain}",
    "tvl_current": "/tvl/{chain}",
    
    # 价格相关
    "prices_current": "/prices/current/{coins}",
    "prices_historical": "/prices/historical/{timestamp}/{coins}",
    "prices_first": "/prices/first/{coins}",
    "prices_chart": "/chart/{chain}/{timestamp}",
    "prices_closest": "/prices/{chain}/{timestamp}",
    "prices_percentage": "/percentage/{chain}/{timestamp}",
    
    # 收益相关
    "pools": "/pools",
    "pool": "/chart/{pool_id}",
    
    # 稳定币相关
    "stablecoins": "/stablecoins",
    "stablecoin": "/stablecoin/{stablecoin_id}",
    "stablecoin_chart": "/stablecoincharts/all",
    "stablecoin_chains": "/stablecoinchains",
    
    # 桥接相关
    "bridges": "/bridges",
    "bridge": "/bridge/{bridge_id}",
    "bridge_volume": "/bridgevolume/{chain}",
    
    # DEX 相关
    "dexs": "/overview/dexs",
    "dex": "/summary/dexs/{protocol}",
    "dex_chains": "/overview/dexs/{chain}",
    
    # 费用相关
    "fees": "/overview/fees",
    "fees_protocol": "/summary/fees/{protocol}",
    "fees_chain": "/overview/fees/{chain}",
    
    # 衍生品相关
    "derivatives": "/overview/derivatives",
    "derivatives_protocol": "/summary/derivatives/{protocol}",
    
    # CEX 相关
    "cex": "/overview/cex",
    
    # 期权相关
    "options": "/overview/options",
    "options_chain": "/overview/options/{chain}"
}

@dataclass
class ChainMapping:
    """链名称映射"""
    name: str
    llama_name: str
    chain_id: Optional[int] = None
    native_token: str = ""

# 支持的链映射
CHAIN_MAPPINGS = {
    "ethereum": ChainMapping("Ethereum", "ethereum", 1, "ETH"),
    "bsc": ChainMapping("BSC", "bsc", 56, "BNB"),
    "polygon": ChainMapping("Polygon", "polygon", 137, "MATIC"),
    "arbitrum": ChainMapping("Arbitrum", "arbitrum", 42161, "ETH"),
    "optimism": ChainMapping("Optimism", "optimism", 10, "ETH"),
    "avalanche": ChainMapping("Avalanche", "avax", 43114, "AVAX"),
    "solana": ChainMapping("Solana", "solana", None, "SOL"),
    "base": ChainMapping("Base", "base", 8453, "ETH"),
    "fantom": ChainMapping("Fantom", "fantom", 250, "FTM"),
}

# 请求配置
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 0.5

# 缓存配置
CACHE_DURATION = {
    "protocols": 3600,      # 1小时
    "prices": 300,          # 5分钟
    "tvl": 300,            # 5分钟
    "yields": 1800,        # 30分钟
    "stablecoins": 3600,   # 1小时
    "bridges": 1800,       # 30分钟
    "dexs": 300,           # 5分钟
    "fees": 1800,          # 30分钟
}

# 分类定义
PROTOCOL_CATEGORIES = [
    "Dexes", "Lending", "CDP", "Yield", "Derivatives", "Payments",
    "Insurance", "Staking", "Bridge", "Privacy", "Synthetics",
    "Options", "Launchpad", "Gaming", "NFT Marketplace"
]

# 常用协议 ID 映射
POPULAR_PROTOCOLS = {
    # DeFi 蓝筹
    "uniswap": "uniswap",
    "aave": "aave",
    "compound": "compound",
    "makerdao": "makerdao",
    "curve": "curve",
    "balancer": "balancer",
    "sushiswap": "sushiswap",
    "pancakeswap": "pancakeswap",
    
    # 衍生品
    "gmx": "gmx",
    "dydx": "dydx",
    "synthetix": "synthetix",
    
    # 收益协议
    "yearn": "yearn-finance",
    "convex": "convex-finance",
    
    # Solana
    "raydium": "raydium",
    "orca": "orca",
    "jupiter": "jupiter",
    "marinade": "marinade-finance",
    
    # 桥接
    "stargate": "stargate",
    "multichain": "multichain",
    "hop": "hop-protocol",
}

# 稳定币映射
POPULAR_STABLECOINS = {
    "usdt": "1",
    "usdc": "2", 
    "busd": "3",
    "dai": "4",
    "ust": "5",
    "frax": "6",
    "tusd": "7",
    "usdd": "8",
}

# 显示配置
MAX_RESULTS_DISPLAY = 20
MIN_TVL_DISPLAY = 1000000  # 最小 TVL 显示阈值（100万美元）
MIN_VOLUME_DISPLAY = 100000  # 最小交易量显示阈值（10万美元）