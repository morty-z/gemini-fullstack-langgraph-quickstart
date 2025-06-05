# app/agent/tools/coinmarketcap/cmc_config.py
"""
CoinMarketCap API 配置文件
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ===== API 配置 =====

# API Key
CMC_API_KEY = os.getenv("CMC_API_KEY", "")

# API 端点
CMC_BASE_URL = "https://pro-api.coinmarketcap.com"
CMC_SANDBOX_URL = "https://sandbox-api.coinmarketcap.com"  # 测试环境

# 使用沙盒环境（测试时使用）
USE_SANDBOX = os.getenv("CMC_USE_SANDBOX", "false").lower() == "true"

# 选择正确的 base URL
BASE_URL = CMC_BASE_URL

# API 版本
API_VERSION = "v1"

# ===== 请求配置 =====

@dataclass
class RequestConfig:
    """请求配置"""
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.2  # 秒
    
    # CoinMarketCap 限制
    # Basic: 333 calls/day (约10次/小时)
    # Hobbyist: 10,000 calls/month
    # Startup: 100,000 calls/month
    # Standard: 500,000 calls/month
    # Professional: 2,000,000 calls/month
    daily_limit: int = 333  # 默认基础版
    
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {
                "Accept": "application/json",
                "Accept-Encoding": "deflate, gzip",
                "X-CMC_PRO_API_KEY": CMC_API_KEY
            }

REQUEST_CONFIG = RequestConfig(
    timeout=int(os.getenv("CMC_TIMEOUT", "30")),
    max_retries=int(os.getenv("CMC_MAX_RETRIES", "3")),
    rate_limit_delay=float(os.getenv("CMC_RATE_LIMIT", "0.2")),
    daily_limit=int(os.getenv("CMC_DAILY_LIMIT", "333"))
)

# ===== 端点配置 =====

ENDPOINTS = {
    # Cryptocurrency Endpoints
    "crypto_map": f"/{API_VERSION}/cryptocurrency/map",
    "crypto_info": f"/{API_VERSION}/cryptocurrency/info",
    "crypto_listings_latest": f"/{API_VERSION}/cryptocurrency/listings/latest",
    "crypto_listings_historical": f"/{API_VERSION}/cryptocurrency/listings/historical",
    "crypto_quotes_latest": f"/{API_VERSION}/cryptocurrency/quotes/latest",
    "crypto_quotes_historical": f"/{API_VERSION}/cryptocurrency/quotes/historical",
    "crypto_market_pairs": f"/{API_VERSION}/cryptocurrency/market-pairs/latest",
    "crypto_ohlcv_latest": f"/{API_VERSION}/cryptocurrency/ohlcv/latest",
    "crypto_ohlcv_historical": f"/{API_VERSION}/cryptocurrency/ohlcv/historical",
    "crypto_price_performance": f"/{API_VERSION}/cryptocurrency/price-performance-stats/latest",
    "crypto_categories": f"/{API_VERSION}/cryptocurrency/categories",
    "crypto_category": f"/{API_VERSION}/cryptocurrency/category",
    "crypto_airdrops": f"/{API_VERSION}/cryptocurrency/airdrops",
    "crypto_airdrop": f"/{API_VERSION}/cryptocurrency/airdrop",
    "crypto_trending_latest": f"/{API_VERSION}/cryptocurrency/trending/latest",
    "crypto_trending_gainers_losers": f"/{API_VERSION}/cryptocurrency/trending/gainers-losers",
    "crypto_trending_most_visited": f"/{API_VERSION}/cryptocurrency/trending/most-visited",
    
    # Exchange Endpoints
    "exchange_map": f"/{API_VERSION}/exchange/map",
    "exchange_info": f"/{API_VERSION}/exchange/info",
    "exchange_listings_latest": f"/{API_VERSION}/exchange/listings/latest",
    "exchange_listings_historical": f"/{API_VERSION}/exchange/listings/historical",
    "exchange_quotes_latest": f"/{API_VERSION}/exchange/quotes/latest",
    "exchange_quotes_historical": f"/{API_VERSION}/exchange/quotes/historical",
    "exchange_market_pairs": f"/{API_VERSION}/exchange/market-pairs/latest",
    
    # Global Metrics Endpoints
    "global_metrics_latest": f"/{API_VERSION}/global-metrics/quotes/latest",
    "global_metrics_historical": f"/{API_VERSION}/global-metrics/quotes/historical",
    
    # Tools Endpoints
    "price_conversion": f"/{API_VERSION}/tools/price-conversion",
    
    # Fiat Endpoints
    "fiat_map": f"/{API_VERSION}/fiat/map",
    
    # Key Info Endpoint
    "key_info": f"/{API_VERSION}/key/info",

    "crypto_trending_most_visited": f"/{API_VERSION}/cryptocurrency/trending/most-visited",
    "blockchain_statistics_latest": f"/{API_VERSION}/blockchain/statistics/latest",
}

# ===== 默认参数配置 =====

DEFAULT_PARAMS = {
    "convert": "USD",  # 默认转换为 USD
    "limit": 100,      # 默认返回数量
    "sort": "market_cap",  # 默认排序方式
    "sort_dir": "desc",    # 默认降序
    "cryptocurrency_type": "all",  # 默认所有类型
}

# ===== 缓存配置 =====

CACHE_CONFIG = {
    "enabled": os.getenv("CMC_CACHE_ENABLED", "true").lower() == "true",
    "ttl": int(os.getenv("CMC_CACHE_TTL", "300")),  # 5分钟
    "max_size": int(os.getenv("CMC_CACHE_MAX_SIZE", "1000")),
    
    # 不同数据类型的缓存时间（秒）
    "ttl_by_type": {
        "quotes": 60,        # 价格数据缓存1分钟
        "info": 3600,        # 基础信息缓存1小时
        "listings": 300,     # 列表数据缓存5分钟
        "map": 86400,        # 映射数据缓存1天
        "global": 300,       # 全局数据缓存5分钟
        "trending": 600,     # 趋势数据缓存10分钟
    }
}

# ===== 显示配置 =====

DISPLAY_CONFIG = {
    "max_results": int(os.getenv("CMC_MAX_RESULTS", "20")),
    "decimal_places": int(os.getenv("CMC_DECIMAL_PLACES", "2")),
    "percentage_decimals": int(os.getenv("CMC_PERCENTAGE_DECIMALS", "2")),
    "show_rank": True,
    "show_market_cap": True,
    "show_volume": True,
    "show_circulating_supply": True,
    "show_change_24h": True,
    "show_change_7d": True,
}

# ===== 错误配置 =====

ERROR_CONFIG = {
    "log_errors": os.getenv("CMC_LOG_ERRORS", "true").lower() == "true",
    "retry_on_errors": [429, 500, 502, 503, 504],  # 可重试的HTTP状态码
    "circuit_breaker_enabled": os.getenv("CMC_CIRCUIT_BREAKER", "true").lower() == "true",
    "failure_threshold": int(os.getenv("CMC_FAILURE_THRESHOLD", "5")),
    "recovery_timeout": int(os.getenv("CMC_RECOVERY_TIMEOUT", "300")),  # 5分钟
}

# ===== CMC 错误代码 =====

CMC_ERROR_CODES = {
    400: "Bad Request -- 请求无效",
    401: "Unauthorized -- API key 无效",
    402: "Payment Required -- 需要付费订阅",
    403: "Forbidden -- 无权访问该资源",
    429: "Too Many Requests -- 请求过于频繁",
    500: "Internal Server Error -- 服务器错误",
}

# ===== 币种类型 =====

CRYPTOCURRENCY_TYPES = [
    "all",      # 所有类型
    "coins",    # 币
    "tokens"    # 代币
]

# ===== 排序字段 =====

SORT_FIELDS = {
    "listings": [
        "name",
        "symbol", 
        "date_added",
        "market_cap",
        "market_cap_strict",
        "price",
        "circulating_supply",
        "total_supply",
        "max_supply",
        "num_market_pairs",
        "volume_24h",
        "percent_change_1h",
        "percent_change_24h",
        "percent_change_7d",
        "market_cap_by_total_supply_strict",
        "volume_7d",
        "volume_30d"
    ],
    "gainers_losers": [
        "percent_change_24h",
        "percent_change_7d", 
        "percent_change_30d",
        "percent_change_60d",
        "percent_change_90d"
    ],
    "trending": [
        "trending",
        "most_visited",
        "recently_added"
    ]
}

# ===== 时间周期 =====

TIME_PERIODS = {
    "1h": "percent_change_1h",
    "24h": "percent_change_24h",
    "7d": "percent_change_7d",
    "30d": "percent_change_30d",
    "60d": "percent_change_60d",
    "90d": "percent_change_90d"
}

# ===== 辅助函数 =====

def validate_api_key() -> bool:
    """验证 API Key 是否设置"""
    return bool(CMC_API_KEY)

def get_endpoint_url(endpoint_name: str) -> str:
    """获取完整的端点 URL"""
    if endpoint_name not in ENDPOINTS:
        raise ValueError(f"未知的端点: {endpoint_name}")
    return f"{BASE_URL}{ENDPOINTS[endpoint_name]}"

def format_number(value: float, decimals: int = None, is_currency: bool = False) -> str:
    """格式化数字显示"""
    if decimals is None:
        decimals = DISPLAY_CONFIG["decimal_places"]
    
    if value >= 1_000_000_000_000:  # 万亿
        return f"{'$' if is_currency else ''}{value / 1_000_000_000_000:.{decimals}f}T"
    elif value >= 1_000_000_000:  # 十亿
        return f"{'$' if is_currency else ''}{value / 1_000_000_000:.{decimals}f}B"
    elif value >= 1_000_000:  # 百万
        return f"{'$' if is_currency else ''}{value / 1_000_000:.{decimals}f}M"
    elif value >= 1_000:  # 千
        return f"{'$' if is_currency else ''}{value / 1_000:.{decimals}f}K"
    else:
        return f"{'$' if is_currency else ''}{value:.{decimals}f}"

def format_percentage(value: float) -> str:
    """格式化百分比"""
    decimals = DISPLAY_CONFIG["percentage_decimals"]
    if value > 0:
        return f"+{value:.{decimals}f}%"
    else:
        return f"{value:.{decimals}f}%"