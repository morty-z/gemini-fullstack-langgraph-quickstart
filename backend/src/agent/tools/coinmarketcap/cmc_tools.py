# app/agent/tools/coinmarketcap/cmc_tools.py
"""
CoinMarketCap 工具集
提供各种加密货币市场数据查询工具
"""

from langchain.tools import Tool
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from app.agent.tools.coinmarketcap.cmc_client import cmc_client
from app.agent.tools.coinmarketcap.cmc_config import (
    DISPLAY_CONFIG, format_number, format_percentage,
    TIME_PERIODS, CRYPTOCURRENCY_TYPES
)

logger = logging.getLogger(__name__)

# ===== 价格查询工具 =====

def get_crypto_price(query: str) -> str:
    """
    获取加密货币价格
    输入格式: "符号" 或 "符号1,符号2,符号3"
    示例: "BTC" 或 "BTC,ETH,BNB"
    """
    try:
        symbols = query.strip().upper()
        
        if not symbols:
            return "请提供加密货币符号，如 BTC 或 BTC,ETH,BNB"
        
        # 获取价格数据
        data = cmc_client.get_cryptocurrency_quotes_latest(symbols=symbols)
        
        if "data" not in data:
            return "未找到数据"
        
        result = "💰 加密货币价格查询\n\n"
        
        for symbol, crypto_data in data["data"].items():
            name = crypto_data.get("name", "Unknown")
            rank = crypto_data.get("cmc_rank", "N/A")
            
            quote = crypto_data.get("quote", {}).get("USD", {})
            price = quote.get("price", 0)
            change_24h = quote.get("percent_change_24h", 0)
            change_7d = quote.get("percent_change_7d", 0)
            market_cap = quote.get("market_cap", 0)
            volume_24h = quote.get("volume_24h", 0)
            
            result += f"🪙 {symbol} - {name}\n"
            result += f"📊 排名: #{rank}\n"
            result += f"💵 价格: {format_number(price, is_currency=True)}\n"
            result += f"📈 24h: {format_percentage(change_24h)}\n"
            result += f"📊 7d: {format_percentage(change_7d)}\n"
            result += f"💰 市值: {format_number(market_cap, is_currency=True)}\n"
            result += f"📊 24h成交量: {format_number(volume_24h, is_currency=True)}\n"
            
            # 供应量信息
            circulating = crypto_data.get("circulating_supply", 0)
            total = crypto_data.get("total_supply", 0)
            max_supply = crypto_data.get("max_supply")
            
            if circulating:
                result += f"🔄 流通量: {format_number(circulating)}\n"
            if total:
                result += f"📦 总供应: {format_number(total)}\n"
            if max_supply:
                result += f"🔒 最大供应: {format_number(max_supply)}\n"
            
            result += "\n"
        
        result += f"⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return result
        
    except Exception as e:
        logger.error(f"获取价格失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_crypto_info(query: str) -> str:
    """
    获取加密货币详细信息
    输入格式: "符号" 或 "符号1,符号2"
    示例: "BTC" 或 "BTC,ETH"
    """
    try:
        symbols = query.strip().upper()
        
        if not symbols:
            return "请提供加密货币符号"
        
        # 获取详细信息
        data = cmc_client.get_cryptocurrency_info(symbols=symbols)
        
        if "data" not in data:
            return "未找到数据"
        
        result = "📋 加密货币详细信息\n\n"
        
        for symbol, info in data["data"].items():
            name = info.get("name", "Unknown")
            slug = info.get("slug", "")
            category = info.get("category", "N/A")
            description = info.get("description", "无描述")
            
            result += f"🪙 {symbol} - {name}\n"
            result += f"🔗 Slug: {slug}\n"
            result += f"📁 类别: {category}\n"
            
            # 添加日期
            date_added = info.get("date_added", "")
            if date_added:
                result += f"📅 添加日期: {date_added[:10]}\n"
            
            # 标签
            tags = info.get("tags", [])
            if tags:
                result += f"🏷️ 标签: {', '.join(tags[:5])}\n"
            
            # 平台信息
            platform = info.get("platform")
            if platform:
                result += f"🔧 平台: {platform.get('name', 'Unknown')}\n"
                result += f"📍 合约: {platform.get('token_address', 'N/A')}\n"
            
            # 描述（限制长度）
            if description and len(description) > 200:
                description = description[:200] + "..."
            result += f"📝 描述: {description}\n"
            
            # URLs
            urls = info.get("urls", {})
            if urls:
                result += "🔗 链接:\n"
                for url_type, url_list in urls.items():
                    if url_list:
                        result += f"  • {url_type}: {url_list[0]}\n"
            
            result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取详情失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_top_cryptos(query: str) -> str:
    """
    获取市值排名前N的加密货币
    输入格式: "数量" 或 "数量 类型"
    示例: "10" 或 "20 coins" 或 "15 tokens"
    """
    try:
        parts = query.strip().split()
        
        # 解析参数
        limit = 10  # 默认10个
        crypto_type = "all"  # 默认所有类型
        
        if parts:
            try:
                limit = int(parts[0])
                limit = min(limit, DISPLAY_CONFIG["max_results"])  # 限制最大数量
            except:
                return "请提供有效的数量"
        
        if len(parts) > 1:
            if parts[1].lower() in CRYPTOCURRENCY_TYPES:
                crypto_type = parts[1].lower()
        
        # 获取数据
        data = cmc_client.get_cryptocurrency_listings_latest(
            limit=limit,
            cryptocurrency_type=crypto_type
        )
        
        if "data" not in data:
            return "未找到数据"
        
        type_name = {
            "all": "所有",
            "coins": "币",
            "tokens": "代币"
        }.get(crypto_type, crypto_type)
        
        result = f"🏆 市值排名前 {limit} 的{type_name}加密货币\n\n"
        
        for i, crypto in enumerate(data["data"], 1):
            symbol = crypto.get("symbol", "")
            name = crypto.get("name", "")
            
            quote = crypto.get("quote", {}).get("USD", {})
            price = quote.get("price", 0)
            market_cap = quote.get("market_cap", 0)
            change_24h = quote.get("percent_change_24h", 0)
            volume_24h = quote.get("volume_24h", 0)
            
            change_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
            
            result += f"{i}. {symbol} - {name}\n"
            result += f"   💵 ${price:,.2f} {change_emoji} {format_percentage(change_24h)}\n"
            result += f"   💰 市值: {format_number(market_cap, is_currency=True)}\n"
            result += f"   📊 24h量: {format_number(volume_24h, is_currency=True)}\n\n"
        
        result += f"⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return result
        
    except Exception as e:
        logger.error(f"获取排行失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_gainers_losers(query: str) -> str:
    """
    获取涨跌幅排行榜
    输入格式: "涨幅/跌幅 时间 数量"
    示例: "涨幅 24h 10" 或 "跌幅 7d 20"
    """
    try:
        parts = query.strip().split()
        
        # 默认参数
        sort_dir = "desc"  # 默认涨幅
        time_period = "24h"
        limit = 10
        
        # 解析参数
        if parts:
            if parts[0] in ["涨幅", "gainers", "涨"]:
                sort_dir = "desc"
            elif parts[0] in ["跌幅", "losers", "跌"]:
                sort_dir = "asc"
        
        if len(parts) > 1:
            if parts[1] in TIME_PERIODS:
                time_period = parts[1]
        
        if len(parts) > 2:
            try:
                limit = int(parts[2])
                limit = min(limit, DISPLAY_CONFIG["max_results"])
            except:
                pass
        
        # 获取数据
        sort_field = TIME_PERIODS.get(time_period, "percent_change_24h")
        data = cmc_client.get_trending_gainers_losers(
            limit=limit,
            time_period=time_period,
            sort=sort_field,
            sort_dir=sort_dir
        )
        
        if "data" not in data:
            return "未找到数据"
        
        title = "📈 涨幅榜" if sort_dir == "desc" else "📉 跌幅榜"
        result = f"{title} - {time_period}\n\n"
        
        for i, crypto in enumerate(data["data"], 1):
            symbol = crypto.get("symbol", "")
            name = crypto.get("name", "")
            
            quote = crypto.get("quote", {}).get("USD", {})
            price = quote.get("price", 0)
            change = quote.get(sort_field, 0)
            market_cap = quote.get("market_cap", 0)
            volume_24h = quote.get("volume_24h", 0)
            
            result += f"{i}. {symbol} - {name}\n"
            result += f"   💵 ${price:,.4f}\n"
            result += f"   📊 {time_period}变化: {format_percentage(change)}\n"
            result += f"   💰 市值: {format_number(market_cap, is_currency=True)}\n"
            result += f"   📊 24h量: {format_number(volume_24h, is_currency=True)}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取涨跌榜失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_global_metrics(query: str = "") -> str:
    """
    获取全球加密货币市场数据
    输入: 任意或留空
    """
    try:
        # 获取全球数据
        data = cmc_client.get_global_metrics_latest()
        
        if "data" not in data:
            return "未找到数据"
        
        metrics = data["data"]
        quote = metrics.get("quote", {}).get("USD", {})
        
        result = "🌍 全球加密货币市场概况\n\n"
        
        # 基础指标
        result += f"📊 活跃加密货币: {metrics.get('active_cryptocurrencies', 0):,}\n"
        result += f"🏦 活跃交易所: {metrics.get('active_exchanges', 0):,}\n"
        result += f"💰 总市值: {format_number(quote.get('total_market_cap', 0), is_currency=True)}\n"
        result += f"📊 24h成交量: {format_number(quote.get('total_volume_24h', 0), is_currency=True)}\n"
        result += f"📈 24h变化: {format_percentage(quote.get('total_market_cap_yesterday_percentage_change', 0))}\n"
        
        # BTC 占比
        btc_dominance = metrics.get("btc_dominance", 0)
        eth_dominance = metrics.get("eth_dominance", 0)
        result += f"\n🟠 BTC 占比: {btc_dominance:.2f}%\n"
        result += f"🔷 ETH 占比: {eth_dominance:.2f}%\n"
        
        # DeFi 数据
        defi_volume = metrics.get("defi_volume_24h")
        defi_market_cap = metrics.get("defi_market_cap")
        if defi_volume:
            result += f"\n🏛️ DeFi 24h量: {format_number(defi_volume, is_currency=True)}\n"
        if defi_market_cap:
            result += f"🏛️ DeFi 市值: {format_number(defi_market_cap, is_currency=True)}\n"
        
        # 稳定币数据
        stablecoin_volume = metrics.get("stablecoin_volume_24h")
        stablecoin_market_cap = metrics.get("stablecoin_market_cap")
        if stablecoin_volume:
            result += f"\n💵 稳定币24h量: {format_number(stablecoin_volume, is_currency=True)}\n"
        if stablecoin_market_cap:
            result += f"💵 稳定币市值: {format_number(stablecoin_market_cap, is_currency=True)}\n"
        
        result += f"\n⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return result
        
    except Exception as e:
        logger.error(f"获取全球数据失败: {str(e)}")
        return f"查询失败: {str(e)}"

def search_crypto(query: str) -> str:
    """
    搜索加密货币
    输入格式: "关键词"
    示例: "bitcoin" 或 "defi"
    """
    try:
        keyword = query.strip()
        
        if not keyword:
            return "请提供搜索关键词"
        
        # 先获取映射数据
        map_data = cmc_client.get_cryptocurrency_map(limit=5000)  # 获取更多以便搜索
        
        if "data" not in map_data:
            return "未找到数据"
        
        # 搜索匹配的币种
        matches = []
        keyword_lower = keyword.lower()
        
        for crypto in map_data["data"]:
            name_lower = crypto.get("name", "").lower()
            symbol_lower = crypto.get("symbol", "").lower()
            slug_lower = crypto.get("slug", "").lower()
            
            # 检查是否匹配
            if (keyword_lower in name_lower or 
                keyword_lower in symbol_lower or 
                keyword_lower in slug_lower):
                matches.append(crypto)
            
            # 限制结果数量
            if len(matches) >= DISPLAY_CONFIG["max_results"]:
                break
        
        if not matches:
            return f"未找到匹配 '{keyword}' 的加密货币"
        
        result = f"🔍 搜索结果: '{keyword}'\n\n"
        
        # 获取这些币的价格信息
        ids = ",".join([str(m["id"]) for m in matches[:10]])  # 最多查询10个的价格
        
        try:
            price_data = cmc_client.get_cryptocurrency_quotes_latest(ids=ids)
            price_map = {}
            
            if "data" in price_data:
                for cid, pdata in price_data["data"].items():
                    quote = pdata.get("quote", {}).get("USD", {})
                    price_map[int(cid)] = {
                        "price": quote.get("price", 0),
                        "change_24h": quote.get("percent_change_24h", 0),
                        "market_cap": quote.get("market_cap", 0),
                        "rank": pdata.get("cmc_rank", "N/A")
                    }
        except:
            price_map = {}
        
        for i, crypto in enumerate(matches, 1):
            cid = crypto["id"]
            symbol = crypto.get("symbol", "")
            name = crypto.get("name", "")
            rank = crypto.get("rank", "N/A")
            
            result += f"{i}. {symbol} - {name}\n"
            result += f"   🆔 CMC ID: {cid}\n"
            
            # 添加价格信息（如果有）
            if cid in price_map:
                pinfo = price_map[cid]
                result += f"   📊 排名: #{pinfo['rank']}\n"
                result += f"   💵 价格: ${pinfo['price']:,.4f}\n"
                result += f"   📈 24h: {format_percentage(pinfo['change_24h'])}\n"
                result += f"   💰 市值: {format_number(pinfo['market_cap'], is_currency=True)}\n"
            else:
                result += f"   📊 排名: #{rank}\n"
            
            # 平台信息
            platform = crypto.get("platform")
            if platform:
                result += f"   🔧 平台: {platform.get('name', 'Unknown')}\n"
            
            # 状态
            is_active = crypto.get("is_active", 0)
            result += f"   ✅ 状态: {'活跃' if is_active == 1 else '非活跃'}\n"
            
            result += "\n"
        
        if len(matches) > DISPLAY_CONFIG["max_results"]:
            result += f"... 还有 {len(matches) - DISPLAY_CONFIG['max_results']} 个结果\n"
        
        return result
        
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return f"搜索失败: {str(e)}"

def convert_crypto_price(query: str) -> str:
    """
    加密货币价格转换
    输入格式: "数量 源币种 目标币种"
    示例: "1 BTC USD" 或 "100 ETH BTC"
    """
    try:
        parts = query.strip().split()
        
        if len(parts) < 2:
            return "请提供: 数量 源币种 [目标币种]（默认USD）"
        
        # 解析参数
        try:
            amount = float(parts[0])
        except:
            return "请提供有效的数量"
        
        source = parts[1].upper()
        target = parts[2].upper() if len(parts) > 2 else "USD"
        
        # 进行转换
        data = cmc_client.get_price_conversion(
            amount=amount,
            symbol=source,
            convert=target
        )
        
        if "data" not in data:
            return "转换失败"
        
        conversion_data = data["data"]
        quote = conversion_data.get("quote", {}).get(target, {})
        
        converted_price = quote.get("price", 0)
        
        result = f"💱 价格转换\n\n"
        result += f"🔄 {amount} {source} = {converted_price:,.6f} {target}\n"
        
        # 添加源币种信息
        source_name = conversion_data.get("name", "")
        source_symbol = conversion_data.get("symbol", "")
        
        if source_name:
            result += f"\n📊 {source_symbol} - {source_name}\n"
        
        # 如果转换为 USD，显示更多信息
        if target == "USD":
            result += f"💵 单价: ${converted_price/amount:,.4f}\n"
        
        result += f"\n⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return result
        
    except Exception as e:
        logger.error(f"转换失败: {str(e)}")
        return f"转换失败: {str(e)}"

def get_trending_cryptos(query: str) -> str:
    """
    获取热门趋势加密货币
    输入格式: "时间周期 数量" 
    示例: "24h 10" 或 "7d 20"
    """
    try:
        parts = query.strip().split()
        
        # 默认参数
        time_period = "24h"
        limit = 10
        
        # 解析参数
        if parts:
            if parts[0] in TIME_PERIODS:
                time_period = parts[0]
        
        if len(parts) > 1:
            try:
                limit = int(parts[1])
                limit = min(limit, DISPLAY_CONFIG["max_results"])
            except:
                pass
        
        # 获取趋势数据
        data = cmc_client.get_trending_latest(
            limit=limit,
            time_period=time_period
        )
        
        if "data" not in data:
            return "未找到数据"
        
        result = f"🔥 热门趋势 - {time_period}\n\n"
        
        for i, crypto in enumerate(data["data"], 1):
            symbol = crypto.get("symbol", "")
            name = crypto.get("name", "")
            rank = crypto.get("cmc_rank", "N/A")
            
            quote = crypto.get("quote", {}).get("USD", {})
            price = quote.get("price", 0)
            change = quote.get(TIME_PERIODS.get(time_period, "percent_change_24h"), 0)
            market_cap = quote.get("market_cap", 0)
            volume_24h = quote.get("volume_24h", 0)
            
            change_emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
            
            result += f"{i}. {symbol} - {name} (#{rank})\n"
            result += f"   💵 ${price:,.4f} {change_emoji} {format_percentage(change)}\n"
            result += f"   💰 市值: {format_number(market_cap, is_currency=True)}\n"
            result += f"   📊 24h量: {format_number(volume_24h, is_currency=True)}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取趋势失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_api_usage(query: str = "") -> str:
    """
    获取 API 使用情况
    输入: 任意或留空
    """
    try:
        # 获取 API 信息
        data = cmc_client.get_key_info()
        
        if "data" not in data:
            return "未找到数据"
        
        usage = data["data"].get("usage", {})
        plan = data["data"].get("plan", {})
        
        result = "🔑 CoinMarketCap API 使用情况\n\n"
        
        # 计划信息
        result += f"📋 当前计划: {plan.get('plan_name', 'Unknown')}\n"
        result += f"💳 信用额度限制: {plan.get('credit_limit_monthly', 0):,}\n"
        result += f"⏱️ 速率限制: {plan.get('rate_limit_minute', 0)} 次/分钟\n"
        
        # 使用情况
        current_minute = usage.get("current_minute", {})
        current_day = usage.get("current_day", {})
        current_month = usage.get("current_month", {})
        
        result += f"\n📊 当前使用:\n"
        result += f"• 本分钟: {current_minute.get('requests_made', 0)} / {current_minute.get('requests_left', 0) + current_minute.get('requests_made', 0)}\n"
        result += f"• 今日: {current_day.get('credits_used', 0)} 信用额度\n"
        result += f"• 本月: {current_month.get('credits_used', 0)} / {current_month.get('credits_left', 0) + current_month.get('credits_used', 0)} 信用额度\n"
        
        # 客户端统计
        client_stats = cmc_client.get_stats()
        result += f"\n📈 客户端统计:\n"
        result += f"• 缓存大小: {client_stats['cache_size']}\n"
        result += f"• API调用(1h): {client_stats['api_calls_1h']}\n"
        result += f"• API调用(24h): {client_stats['api_calls_24h']} / {client_stats['daily_limit']}\n"
        
        # 断路器状态
        cb_status = client_stats['circuit_breaker']
        if cb_status['is_open']:
            result += f"\n⚠️ 断路器状态: 打开 (失败 {cb_status['failures']} 次)\n"
        else:
            result += f"\n✅ 断路器状态: 正常\n"
        
        result += f"\n⏰ 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return result
        
    except Exception as e:
        logger.error(f"获取API使用情况失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== 新增工具 =====

def get_crypto_ohlcv(query: str) -> str:
    """
    获取加密货币 OHLCV 数据（开高低收成交量）
    输入格式: "符号 时间间隔 数量"
    示例: "BTC hourly 24" 或 "ETH daily 7"
    """
    try:
        parts = query.strip().split()
        if len(parts) < 2:
            return "请提供：符号 时间间隔(hourly/daily/weekly/monthly) [数量]"
        
        symbol = parts[0].upper()
        interval = parts[1].lower()
        count = int(parts[2]) if len(parts) > 2 else 10
        
        # 时间间隔映射
        interval_map = {
            "hourly": "hourly",
            "daily": "daily", 
            "weekly": "weekly",
            "monthly": "monthly",
            "1h": "hourly",
            "1d": "daily",
            "1w": "weekly",
            "1m": "monthly"
        }
        
        if interval not in interval_map:
            return "无效的时间间隔，请使用：hourly/daily/weekly/monthly"
        
        # 获取 OHLCV 数据
        data = cmc_client.get_cryptocurrency_ohlcv_latest(
            symbols=symbol,
            interval=interval_map[interval],
            count=count
        )
        
        if "data" not in data:
            return "未找到数据"
        
        result = f"📊 {symbol} OHLCV 数据 ({interval})\n\n"
        
        quotes = data["data"][symbol][0]["quotes"]
        for quote in quotes[-count:]:  # 显示最近的数据
            time_str = quote["time_open"][:10]
            ohlcv = quote["quote"]["USD"]
            
            result += f"📅 {time_str}\n"
            result += f"  开盘: ${ohlcv['open']:,.2f}\n"
            result += f"  最高: ${ohlcv['high']:,.2f}\n"
            result += f"  最低: ${ohlcv['low']:,.2f}\n"
            result += f"  收盘: ${ohlcv['close']:,.2f}\n"
            result += f"  成交量: {format_number(ohlcv['volume'], is_currency=True)}\n"
            result += f"  市值: {format_number(ohlcv['market_cap'], is_currency=True)}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取 OHLCV 失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_market_pairs(query: str) -> str:
    """
    获取加密货币的交易对信息
    输入格式: "符号 [数量]"
    示例: "BTC 20" 或 "ETH"
    """
    try:
        parts = query.strip().split()
        symbol = parts[0].upper()
        limit = int(parts[1]) if len(parts) > 1 else 10
        
        # 获取交易对数据
        data = cmc_client.get_cryptocurrency_market_pairs(
            symbols=symbol,
            limit=min(limit, 100)
        )
        
        if "data" not in data:
            return "未找到数据"
        
        market_pairs = data["data"]["market_pairs"]
        num_pairs = data["data"]["num_market_pairs"]
        
        result = f"💱 {symbol} 交易对信息\n"
        result += f"📊 总交易对数: {num_pairs}\n\n"
        
        # 按交易量排序
        market_pairs.sort(key=lambda x: x["quote"]["USD"]["volume_24h"], reverse=True)
        
        for i, pair in enumerate(market_pairs[:limit], 1):
            exchange = pair["exchange"]["name"]
            market_pair = pair["market_pair"]
            category = pair["category"]
            quote = pair["quote"]["USD"]
            
            result += f"{i}. {market_pair} @ {exchange}\n"
            result += f"   类型: {category}\n"
            result += f"   价格: ${quote['price']:,.6f}\n"
            result += f"   24h量: {format_number(quote['volume_24h'], is_currency=True)}\n"
            result += f"   深度±2%: {format_number(quote.get('depth_positive_two', 0), is_currency=True)}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取交易对失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_crypto_categories(query: str = "") -> str:
    """
    获取加密货币分类列表
    输入：留空或指定数量
    """
    try:
        limit = 20
        if query.strip():
            try:
                limit = int(query.strip())
            except:
                pass
        
        # 获取分类数据
        data = cmc_client.get_cryptocurrency_categories(limit=limit)
        
        if "data" not in data:
            return "未找到数据"
        
        result = "📂 加密货币分类\n\n"
        
        for i, category in enumerate(data["data"], 1):
            name = category["name"]
            num_tokens = category["num_tokens"]
            market_cap = category["market_cap"]
            market_cap_change = category["market_cap_change"]
            volume = category["volume"]
            
            change_emoji = "🟢" if market_cap_change > 0 else "🔴" if market_cap_change < 0 else "⚪"
            
            result += f"{i}. {name}\n"
            result += f"   代币数: {num_tokens}\n"
            result += f"   市值: {format_number(market_cap, is_currency=True)}\n"
            result += f"   24h变化: {change_emoji} {format_percentage(market_cap_change)}\n"
            result += f"   24h量: {format_number(volume, is_currency=True)}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取分类失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_category_coins(query: str) -> str:
    """
    获取特定分类下的加密货币
    输入格式: "分类ID或slug"
    示例: "defi" 或 "gaming"
    """
    try:
        category = query.strip()
        if not category:
            return "请提供分类名称或ID"
        
        # 获取分类下的币种
        data = cmc_client.get_cryptocurrency_category(
            id=category,
            limit=20
        )
        
        if "data" not in data:
            return "未找到数据"
        
        coins = data["data"]["coins"]
        name = data["data"]["name"]
        description = data["data"]["description"]
        
        result = f"📁 {name} 分类\n"
        if description:
            result += f"📝 {description[:100]}...\n"
        result += f"\n💎 包含币种:\n\n"
        
        for i, coin in enumerate(coins, 1):
            symbol = coin["symbol"]
            name = coin["name"]
            quote = coin["quote"]["USD"]
            
            result += f"{i}. {symbol} - {name}\n"
            result += f"   价格: ${quote['price']:,.4f}\n"
            result += f"   市值: {format_number(quote['market_cap'], is_currency=True)}\n"
            result += f"   24h: {format_percentage(quote['percent_change_24h'])}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取分类币种失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_exchange_info(query: str) -> str:
    """
    获取交易所详细信息
    输入格式: "交易所名称或slug"
    示例: "binance" 或 "coinbase"
    """
    try:
        exchange = query.strip()
        if not exchange:
            return "请提供交易所名称"
        
        # 获取交易所信息
        data = cmc_client.get_exchange_info(slugs=exchange)
        
        if "data" not in data:
            return "未找到数据"
        
        exchange_data = list(data["data"].values())[0]
        
        result = f"🏦 {exchange_data['name']} 交易所信息\n\n"
        result += f"🌐 网站: {exchange_data.get('urls', {}).get('website', ['N/A'])[0]}\n"
        result += f"📅 成立时间: {exchange_data.get('date_launched', 'N/A')}\n"
        result += f"📝 描述: {exchange_data.get('description', 'N/A')[:200]}...\n"
        
        # 如果有手续费信息
        if exchange_data.get('maker_fee'):
            result += f"\n💸 手续费:\n"
            result += f"  Maker: {exchange_data['maker_fee']}%\n"
            result += f"  Taker: {exchange_data['taker_fee']}%\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取交易所信息失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_top_exchanges(query: str) -> str:
    """
    获取顶级交易所排名
    输入格式: "[数量] [类型]"
    示例: "10" 或 "20 spot" 或 "15 derivatives"
    """
    try:
        parts = query.strip().split()
        limit = 10
        market_type = "all"
        
        if parts:
            try:
                limit = int(parts[0])
            except:
                pass
        
        if len(parts) > 1:
            if parts[1] in ["spot", "derivatives", "dex"]:
                market_type = parts[1]
        
        # 获取交易所列表
        data = cmc_client.get_exchange_listings_latest(
            limit=limit,
            market_type=market_type
        )
        
        if "data" not in data:
            return "未找到数据"
        
        result = f"🏆 顶级交易所排名 ({market_type})\n\n"
        
        for i, exchange in enumerate(data["data"], 1):
            name = exchange["name"]
            slug = exchange["slug"]
            quote = exchange["quote"]["USD"]
            
            result += f"{i}. {name}\n"
            result += f"   24h交易量: {format_number(quote['volume_24h'], is_currency=True)}\n"
            result += f"   7d交易量: {format_number(quote['volume_7d'], is_currency=True)}\n"
            result += f"   市场数: {exchange.get('num_market_pairs', 'N/A')}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取交易所排名失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_price_performance(query: str) -> str:
    """
    获取加密货币价格表现统计
    输入格式: "符号 [时间段]"
    示例: "BTC" 或 "ETH all_time"
    """
    try:
        parts = query.strip().split()
        symbol = parts[0].upper()
        time_period = parts[1] if len(parts) > 1 else "all_time"
        
        # 获取价格表现数据
        data = cmc_client.get_cryptocurrency_price_performance(
            symbols=symbol,
            time_period=time_period
        )
        
        if "data" not in data:
            return "未找到数据"
        
        stats = data["data"][symbol]["periods"][time_period]
        
        result = f"📈 {symbol} 价格表现分析 ({time_period})\n\n"
        
        # 价格统计
        result += f"💰 价格区间:\n"
        result += f"  开盘价: ${stats['open']:,.2f}\n"
        result += f"  最高价: ${stats['high']:,.2f}\n"
        result += f"  最低价: ${stats['low']:,.2f}\n"
        result += f"  收盘价: ${stats['close']:,.2f}\n"
        
        # 变化统计
        result += f"\n📊 变化统计:\n"
        result += f"  价格变化: {format_percentage(stats['price_change_percentage'])}\n"
        result += f"  最大回撤: {format_percentage(stats.get('max_drawdown', 0))}\n"
        
        # 时间统计
        if 'time_high' in stats:
            result += f"\n📅 时间记录:\n"
            result += f"  最高价时间: {stats['time_high'][:10]}\n"
            result += f"  最低价时间: {stats['time_low'][:10]}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取价格表现失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_new_listings(query: str) -> str:
    """
    获取最新上线的加密货币
    输入格式: "[数量]"
    示例: "20"
    """
    try:
        limit = 10
        if query.strip():
            try:
                limit = int(query.strip())
            except:
                pass
        
        # 获取最新上线币种
        data = cmc_client.get_cryptocurrency_listings_latest(
            limit=limit,
            sort="date_added",
            sort_dir="desc"
        )
        
        if "data" not in data:
            return "未找到数据"
        
        result = "🆕 最新上线加密货币\n\n"
        
        for i, crypto in enumerate(data["data"], 1):
            symbol = crypto["symbol"]
            name = crypto["name"]
            date_added = crypto.get("date_added", "N/A")
            quote = crypto["quote"]["USD"]
            
            result += f"{i}. {symbol} - {name}\n"
            result += f"   📅 上线时间: {date_added[:10]}\n"
            result += f"   💵 价格: ${quote['price']:,.4f}\n"
            result += f"   💰 市值: {format_number(quote['market_cap'], is_currency=True)}\n"
            result += f"   📊 24h量: {format_number(quote['volume_24h'], is_currency=True)}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取新币失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_airdrops(query: str) -> str:
    """
    获取空投信息
    输入格式: "[状态]" 
    示例: "ongoing" 或 "upcoming" 或 "ended"
    """
    try:
        status = query.strip().lower() if query.strip() else "ongoing"
        
        if status not in ["ongoing", "upcoming", "ended"]:
            status = "ongoing"
        
        # 获取空投数据
        data = cmc_client.get_cryptocurrency_airdrops(
            status=status,
            limit=20
        )
        
        if "data" not in data:
            return "未找到数据"
        
        status_name = {
            "ongoing": "进行中",
            "upcoming": "即将开始", 
            "ended": "已结束"
        }.get(status, status)
        
        result = f"🎁 {status_name}的空投活动\n\n"
        
        airdrops = data["data"]["airdrops"]
        
        if not airdrops:
            return f"当前没有{status_name}的空投活动"
        
        for i, airdrop in enumerate(airdrops, 1):
            name = airdrop["project_name"]
            symbol = airdrop["symbol"]
            start_date = airdrop.get("start_date", "N/A")
            end_date = airdrop.get("end_date", "N/A")
            
            result += f"{i}. {name} ({symbol})\n"
            result += f"   📅 开始: {start_date[:10]}\n"
            result += f"   📅 结束: {end_date[:10]}\n"
            
            if airdrop.get("description"):
                result += f"   📝 描述: {airdrop['description'][:100]}...\n"
                
            result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取空投失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_most_visited(query: str) -> str:
    """
    获取最多访问的加密货币
    输入格式: "[数量]"
    示例: "20"
    """
    try:
        limit = 10
        if query.strip():
            try:
                limit = int(query.strip())
            except:
                pass
        
        # 获取数据
        data = cmc_client.get_trending_most_visited(
            limit=limit
        )
        
        if "data" not in data:
            return "未找到数据"
        
        result = "👁️ 最多访问的加密货币\n\n"
        
        for i, crypto in enumerate(data["data"], 1):
            symbol = crypto["symbol"]
            name = crypto["name"]
            rank = crypto.get("cmc_rank", "N/A")
            
            quote = crypto["quote"]["USD"]
            price = quote["price"]
            change_24h = quote["percent_change_24h"]
            
            change_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "⚪"
            
            result += f"{i}. {symbol} - {name} (#{rank})\n"
            result += f"   💵 ${price:,.4f} {change_emoji} {format_percentage(change_24h)}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取热门访问失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_fiat_list(query: str = "") -> str:
    """
    获取支持的法币列表
    输入：留空
    """
    try:
        # 获取法币列表
        data = cmc_client.get_fiat_map(limit=50)
        
        if "data" not in data:
            return "未找到数据"
        
        result = "💱 支持的法币列表\n\n"
        
        for i, fiat in enumerate(data["data"], 1):
            symbol = fiat["symbol"]
            name = fiat["name"]
            sign = fiat.get("sign", "")
            
            result += f"{i}. {symbol} - {name}"
            if sign:
                result += f" ({sign})"
            result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"获取法币列表失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== 创建工具对象 =====

# 基础查询工具
get_crypto_price_tool = Tool(
    name="GetCryptoPrice",
    description="获取加密货币实时价格。输入：符号（支持多个，逗号分隔）。示例：'BTC' 或 'BTC,ETH,BNB'",
    func=get_crypto_price
)

get_crypto_info_tool = Tool(
    name="GetCryptoInfo",
    description="获取加密货币详细信息（描述、标签、平台等）。输入：符号。示例：'BTC' 或 'ETH'",
    func=get_crypto_info
)

search_crypto_tool = Tool(
    name="SearchCrypto",
    description="搜索加密货币。输入：关键词。示例：'bitcoin' 或 'defi'",
    func=search_crypto
)

# 排行榜工具
get_top_cryptos_tool = Tool(
    name="GetTopCryptos",
    description="获取市值排名前N的加密货币。输入：'数量 [类型]'。类型可选：all/coins/tokens。示例：'10' 或 '20 coins'",
    func=get_top_cryptos
)

get_gainers_losers_tool = Tool(
    name="GetGainersLosers",
    description="获取涨跌幅排行榜。输入：'涨幅/跌幅 时间周期 数量'。时间周期：1h/24h/7d/30d。示例：'涨幅 24h 10'",
    func=get_gainers_losers
)

get_trending_tool = Tool(
   name="GetTrendingCryptos",
   description="获取热门趋势加密货币。输入：'时间周期 数量'。示例：'24h 10' 或 '7d 20'",
   func=get_trending_cryptos
)

get_new_listings_tool = Tool(
   name="GetNewListings",
   description="获取最新上线的加密货币。输入：'[数量]'。示例：'20'",
   func=get_new_listings
)

get_most_visited_tool = Tool(
   name="GetMostVisited",
   description="获取最多访问的加密货币。输入：'[数量]'。示例：'20'",
   func=get_most_visited
)

# 市场数据工具
get_global_metrics_tool = Tool(
   name="GetGlobalMetrics",
   description="获取全球加密货币市场概况（总市值、BTC占比、活跃币种数等）",
   func=get_global_metrics
)

get_ohlcv_tool = Tool(
   name="GetCryptoOHLCV",
   description="获取加密货币OHLCV数据。输入：'符号 时间间隔 数量'。时间间隔：hourly/daily/weekly/monthly。示例：'BTC daily 7'",
   func=get_crypto_ohlcv
)

get_market_pairs_tool = Tool(
   name="GetMarketPairs",
   description="获取加密货币交易对信息。输入：'符号 [数量]'。示例：'BTC 20'",
   func=get_market_pairs
)

get_price_performance_tool = Tool(
   name="GetPricePerformance",
   description="获取价格表现统计。输入：'符号 [时间段]'。示例：'BTC all_time'",
   func=get_price_performance
)

# 分类工具
get_categories_tool = Tool(
   name="GetCryptoCategories",
   description="获取加密货币分类列表。输入：'[数量]'。示例：'30'",
   func=get_crypto_categories
)

get_category_coins_tool = Tool(
   name="GetCategoryCoins",
   description="获取特定分类的加密货币。输入：'分类名称'。示例：'defi' 或 'gaming'",
   func=get_category_coins
)

# 交易所工具
get_exchange_info_tool = Tool(
   name="GetExchangeInfo",
   description="获取交易所详细信息。输入：'交易所名称'。示例：'binance' 或 'coinbase'",
   func=get_exchange_info
)

get_top_exchanges_tool = Tool(
   name="GetTopExchanges",
   description="获取顶级交易所排名。输入：'[数量] [类型]'。类型：all/spot/derivatives/dex。示例：'20 spot'",
   func=get_top_exchanges
)

# 实用工具
convert_price_tool = Tool(
   name="ConvertCryptoPrice",
   description="加密货币价格转换。输入：'数量 源币种 目标币种'。示例：'1 BTC USD' 或 '100 ETH BTC'",
   func=convert_crypto_price
)

get_airdrops_tool = Tool(
   name="GetAirdrops",
   description="获取空投信息。输入：'[状态]'。状态：ongoing/upcoming/ended。示例：'ongoing'",
   func=get_airdrops
)

get_fiat_list_tool = Tool(
   name="GetFiatList",
   description="获取支持的法币列表",
   func=get_fiat_list
)

get_api_usage_tool = Tool(
   name="GetCMCApiUsage",
   description="获取 CoinMarketCap API 使用情况和配额",
   func=get_api_usage
)

# 导出所有工具
cmc_tools = [
   # 基础查询
   get_crypto_price_tool,
   get_crypto_info_tool,
   search_crypto_tool,
   
   # 排行榜
   get_top_cryptos_tool,
   get_gainers_losers_tool,
   get_trending_tool,
   get_new_listings_tool,
   get_most_visited_tool,
   
   # 市场数据
   get_global_metrics_tool,
   get_ohlcv_tool,
   get_market_pairs_tool,
   get_price_performance_tool,
   
   # 分类
   get_categories_tool,
   get_category_coins_tool,
   
   # 交易所
   get_exchange_info_tool,
   get_top_exchanges_tool,
   
   # 实用工具
   convert_price_tool,
   get_airdrops_tool,
   get_fiat_list_tool,
   get_api_usage_tool,
]

# ===== 工具分类（用于帮助和文档）=====

CMC_TOOL_CATEGORIES = {
   "基础查询": [
       "GetCryptoPrice",      # 获取价格
       "GetCryptoInfo",       # 获取详情
       "SearchCrypto",        # 搜索币种
   ],
   "排行榜": [
       "GetTopCryptos",       # 市值排行
       "GetGainersLosers",    # 涨跌幅榜
       "GetTrendingCryptos",  # 热门趋势
       "GetNewListings",      # 最新上线
       "GetMostVisited",      # 最多访问
   ],
   "市场数据": [
       "GetGlobalMetrics",    # 全球概况
       "GetCryptoOHLCV",      # OHLCV数据
       "GetMarketPairs",      # 交易对
       "GetPricePerformance", # 价格表现
   ],
   "分类": [
       "GetCryptoCategories", # 分类列表
       "GetCategoryCoins",    # 分类币种
   ],
   "交易所": [
       "GetExchangeInfo",     # 交易所信息
       "GetTopExchanges",     # 交易所排名
   ],
   "实用工具": [
       "ConvertCryptoPrice",  # 价格转换
       "GetAirdrops",         # 空投信息
       "GetFiatList",         # 法币列表
       "GetCMCApiUsage",      # API使用情况
   ]
}

# ===== 导出 =====

__all__ = [
   'cmc_tools',
   'CMC_TOOL_CATEGORIES',
   # 单独导出每个工具（可选）
   'get_crypto_price_tool',
   'get_crypto_info_tool',
   'search_crypto_tool',
   'get_top_cryptos_tool',
   'get_gainers_losers_tool',
   'get_trending_tool',
   'get_new_listings_tool',
   'get_most_visited_tool',
   'get_global_metrics_tool',
   'get_ohlcv_tool',
   'get_market_pairs_tool',
   'get_price_performance_tool',
   'get_categories_tool',
   'get_category_coins_tool',
   'get_exchange_info_tool',
   'get_top_exchanges_tool',
   'convert_price_tool',
   'get_airdrops_tool',
   'get_fiat_list_tool',
   'get_api_usage_tool',
]