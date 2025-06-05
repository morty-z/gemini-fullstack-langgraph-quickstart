# app/agent/tools/coinmarketcap/__init__.py
"""
CoinMarketCap 工具模块
提供加密货币市场数据查询功能
"""

from app.agent.tools.coinmarketcap.cmc_tools import cmc_tools, CMC_TOOL_CATEGORIES

# CoinMarketCap 工具描述
CMC_TOOL_DESCRIPTIONS = {
    # 基础查询
    "GetCryptoPrice": "获取加密货币实时价格、市值、成交量等信息",
    "GetCryptoInfo": "获取加密货币详细信息，包括描述、标签、平台等",
    "SearchCrypto": "搜索加密货币，支持名称、符号、关键词搜索",
    
    # 排行榜
    "GetTopCryptos": "获取市值排名前N的加密货币，支持筛选币种类型",
    "GetGainersLosers": "获取涨跌幅排行榜，支持多个时间周期",
    "GetTrendingCryptos": "获取热门趋势加密货币",
    "GetNewListings": "获取最新上线的加密货币",
    "GetMostVisited": "获取最多访问的加密货币",
    
    # 市场数据
    "GetGlobalMetrics": "获取全球加密货币市场概况，包括总市值、BTC占比等",
    "GetCryptoOHLCV": "获取加密货币OHLCV数据（开高低收成交量）",
    "GetMarketPairs": "获取加密货币的交易对信息",
    "GetPricePerformance": "获取加密货币价格表现统计",
    
    # 分类
    "GetCryptoCategories": "获取加密货币分类列表",
    "GetCategoryCoins": "获取特定分类下的加密货币",
    
    # 交易所
    "GetExchangeInfo": "获取交易所详细信息",
    "GetTopExchanges": "获取顶级交易所排名",
    
    # 实用工具
    "ConvertCryptoPrice": "加密货币价格转换计算器",
    "GetAirdrops": "获取空投活动信息",
    "GetFiatList": "获取支持的法币列表",
    "GetCMCApiUsage": "查看 CoinMarketCap API 使用情况和配额"
}

# 使用示例
CMC_USAGE_EXAMPLES = {
    "GetCryptoPrice": [
        "GetCryptoPrice BTC",
        "GetCryptoPrice BTC,ETH,BNB",
        "GetCryptoPrice USDT,USDC,DAI"
    ],
    "GetCryptoInfo": [
        "GetCryptoInfo BTC",
        "GetCryptoInfo ETH"
    ],
    "SearchCrypto": [
        "SearchCrypto bitcoin",
        "SearchCrypto defi",
        "SearchCrypto game"
    ],
    "GetTopCryptos": [
        "GetTopCryptos 10",
        "GetTopCryptos 20 coins",
        "GetTopCryptos 15 tokens"
    ],
    "GetGainersLosers": [
        "GetGainersLosers 涨幅 24h 10",
        "GetGainersLosers 跌幅 7d 20",
        "GetGainersLosers gainers 30d 15"
    ],
    "GetTrendingCryptos": [
        "GetTrendingCryptos 24h 10",
        "GetTrendingCryptos 7d 20"
    ],
    "GetNewListings": [
        "GetNewListings 20",
        "GetNewListings 50"
    ],
    "GetMostVisited": [
        "GetMostVisited 20"
    ],
    "GetGlobalMetrics": [
        "GetGlobalMetrics"
    ],
    "GetCryptoOHLCV": [
        "GetCryptoOHLCV BTC daily 7",
        "GetCryptoOHLCV ETH hourly 24",
        "GetCryptoOHLCV BNB weekly 4"
    ],
    "GetMarketPairs": [
        "GetMarketPairs BTC 20",
        "GetMarketPairs ETH 10"
    ],
    "GetPricePerformance": [
        "GetPricePerformance BTC",
        "GetPricePerformance ETH all_time"
    ],
    "GetCryptoCategories": [
        "GetCryptoCategories",
        "GetCryptoCategories 30"
    ],
    "GetCategoryCoins": [
        "GetCategoryCoins defi",
        "GetCategoryCoins gaming",
        "GetCategoryCoins layer-1"
    ],
    "GetExchangeInfo": [
        "GetExchangeInfo binance",
        "GetExchangeInfo coinbase"
    ],
    "GetTopExchanges": [
        "GetTopExchanges 10",
        "GetTopExchanges 20 spot",
        "GetTopExchanges 15 derivatives"
    ],
    "ConvertCryptoPrice": [
        "ConvertCryptoPrice 1 BTC USD",
        "ConvertCryptoPrice 100 ETH BTC",
        "ConvertCryptoPrice 1000 USDT EUR"
    ],
    "GetAirdrops": [
        "GetAirdrops ongoing",
        "GetAirdrops upcoming",
        "GetAirdrops ended"
    ],
    "GetFiatList": [
        "GetFiatList"
    ],
    "GetCMCApiUsage": [
        "GetCMCApiUsage"
    ]
}

__all__ = [
    'cmc_tools',
    'CMC_TOOL_CATEGORIES',
    'CMC_TOOL_DESCRIPTIONS',
    'CMC_USAGE_EXAMPLES'
]