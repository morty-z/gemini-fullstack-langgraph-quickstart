# app/agent/tools/defillama/defillama_tools.py
"""
DeFiLlama 工具集
提供 TVL、价格、收益、DEX、桥接等数据查询功能
"""

from langchain.tools import Tool
from typing import Optional, List, Dict, Union
import logging
from datetime import datetime, timedelta
from app.agent.tools.defillama.defillama_client import defillama_client
from app.agent.tools.defillama.defillama_config import (
    POPULAR_PROTOCOLS, POPULAR_STABLECOINS, MAX_RESULTS_DISPLAY,
    MIN_TVL_DISPLAY, MIN_VOLUME_DISPLAY, CHAIN_MAPPINGS
)

logger = logging.getLogger(__name__)

# === 协议和 TVL 查询工具 ===

def get_protocol_info(query: str) -> str:
    """
    获取 DeFi 协议详细信息
    输入: "协议名称" 或 "协议名称 详细信息"
    """
    try:
        # 清理输入 - 移除可能的额外格式
        query = query.strip()
        # 移除可能的引号
        query = query.strip('"').strip("'")
        # 如果输入包含冒号（如 "protocol: xxx"），提取冒号后的部分
        if ':' in query:
            query = query.split(':', 1)[1].strip().strip('"').strip("'")
        
        parts = query.split()
        if not parts:
            return "请提供协议名称"
        
        protocol_name = parts[0].lower()
        show_details = len(parts) > 1 and "详细" in query
        
        # 查找协议ID
        protocol_id = POPULAR_PROTOCOLS.get(protocol_name, protocol_name)
        
        logger.info(f"查询协议信息: {protocol_id}")
        
        # 获取协议数据
        protocol_data = defillama_client.get_protocol_tvl(protocol_id)
        
        if not protocol_data:
            return f"未找到协议: {protocol_name}"
        
        logger.debug(f"协议数据结构: {type(protocol_data)} - {list(protocol_data.keys()) if isinstance(protocol_data, dict) else 'Not a dict'}")
        
        # 安全获取数据
        name = protocol_data.get("name", "Unknown")
        category = protocol_data.get("category", "Unknown")
        
        # 处理 TVL 数据 - 可能是嵌套结构
        tvl = 0
        try:
            tvl_data = protocol_data.get("tvl")
            if tvl_data is not None:
                if isinstance(tvl_data, (int, float)):
                    tvl = float(tvl_data)
                elif isinstance(tvl_data, list) and tvl_data:
                    # 如果是列表，取最新的值
                    latest = tvl_data[-1]
                    if latest is not None:
                        if isinstance(latest, dict):
                            tvl = float(latest.get("totalLiquidityUSD", 0) or 0)
                        else:
                            tvl = float(latest)
        except (ValueError, TypeError) as e:
            logger.warning(f"TVL 数据处理错误: {e}")
            tvl = 0
        
        # 安全处理涨跌幅
        try:
            change_1d = float(protocol_data.get("change_1d", 0) or 0)
            change_7d = float(protocol_data.get("change_7d", 0) or 0)
            change_1m = float(protocol_data.get("change_1m", 0) or 0)
        except (ValueError, TypeError) as e:
            logger.warning(f"涨跌幅数据处理错误: {e}")
            change_1d = change_7d = change_1m = 0
        
        # 基础信息
        result = f"""
📊 {name} 协议信息

🏷️ 分类: {category}
💰 总锁仓价值 (TVL): ${tvl:,.0f}
📈 涨跌幅:
  • 24小时: {change_1d:+.2f}%
  • 7天: {change_7d:+.2f}%
  • 30天: {change_1m:+.2f}%
"""
        
        # 链分布
        chain_tvls = protocol_data.get("chainTvls", {})
        if chain_tvls and isinstance(chain_tvls, dict):
            result += "\n🔗 链分布:\n"
            sorted_chains = sorted(chain_tvls.items(), 
                                 key=lambda x: float(x[1]) if isinstance(x[1], (int, float)) else 0, 
                                 reverse=True)
            
            for chain, chain_tvl in sorted_chains[:10]:  # 只显示前10个链
                try:
                    chain_tvl_float = float(chain_tvl) if chain_tvl else 0
                    if chain_tvl_float > 1000:  # 只显示TVL > 1000的链
                        percentage = (chain_tvl_float / tvl) * 100 if tvl > 0 else 0
                        result += f"  • {chain}: ${chain_tvl_float:,.0f} ({percentage:.1f}%)\n"
                except (ValueError, TypeError):
                    continue
        
        # 详细信息
        if show_details:
            # 代币信息
            tokens = protocol_data.get("tokens", [])
            if tokens and isinstance(tokens, list):
                result += f"\n🪙 相关代币: {', '.join(str(token) for token in tokens[:5])}\n"
            
            # 官方链接
            url = protocol_data.get("url", "")
            if url:
                result += f"🌐 官网: {url}\n"
            
            # 审计信息
            audits = protocol_data.get("audits", "")
            if audits:
                result += f"🔍 审计: {audits}\n"
            
            # 描述
            description = protocol_data.get("description", "")
            if description and isinstance(description, str):
                result += f"\n📝 描述: {description[:200]}...\n"
        
        result += f"\n📅 数据更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return result
        
    except Exception as e:
        logger.error(f"查询协议信息失败: {str(e)}", exc_info=True)
        return f"查询失败: {str(e)}"

def get_chain_tvl_ranking(chain: str = "") -> str:
    """
    获取链的 TVL 排名或所有链排名
    输入: "链名" 或留空查看所有链排名
    """
    try:
        # 清理输入
        chain = chain.strip().strip('"').strip("'")
        if ':' in chain:
            chain = chain.split(':', 1)[1].strip().strip('"').strip("'")
            
        logger.info(f"查询链 TVL 排名: {chain}")
        
        # 获取所有协议数据
        protocols = defillama_client.get_protocols()
        
        if chain:
            # 查询特定链
            chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
            
            # 过滤该链的协议
            chain_protocols = []
            for protocol in protocols:
                chain_tvls = protocol.get("chainTvls", {})
                if isinstance(chain_tvls, dict) and (chain_name in chain_tvls or chain.lower() in str(protocol.get("chains", [])).lower()):
                    tvl = chain_tvls.get(chain_name, 0)
                    try:
                        tvl_float = float(tvl) if tvl else 0
                        if tvl_float > MIN_TVL_DISPLAY:
                            chain_protocols.append({
                                "name": protocol.get("name", "Unknown"),
                                "tvl": tvl_float,
                                "category": protocol.get("category", "Unknown"),
                                "change_1d": float(protocol.get("change_1d", 0)) if protocol.get("change_1d") else 0
                            })
                    except (ValueError, TypeError):
                        continue
            
            # 排序
            chain_protocols.sort(key=lambda x: x["tvl"], reverse=True)
            
            total_tvl = sum(p["tvl"] for p in chain_protocols)
            
            result = f"""
🏆 {chain_name.title()} 链 TVL 排名

💰 链总TVL: ${total_tvl:,.0f}
📊 协议数量: {len(chain_protocols)}

🥇 Top 协议:
"""
            
            for i, protocol in enumerate(chain_protocols[:MAX_RESULTS_DISPLAY], 1):
                percentage = (protocol["tvl"] / total_tvl) * 100 if total_tvl > 0 else 0
                change_emoji = "📈" if protocol["change_1d"] > 0 else "📉" if protocol["change_1d"] < 0 else "➡️"
                
                result += f"{i:2d}. {protocol['name']:<15} ${protocol['tvl']:>12,.0f} ({percentage:4.1f}%) {change_emoji}{protocol['change_1d']:+.1f}%\n"
        
        else:
            # 显示所有链的排名
            chain_tvls = {}
            
            for protocol in protocols:
                chain_tvls_data = protocol.get("chainTvls", {})
                for chain_name, tvl in chain_tvls_data.items():
                    if chain_name not in chain_tvls:
                        chain_tvls[chain_name] = 0
                    chain_tvls[chain_name] += tvl
            
            # 排序
            sorted_chains = sorted(chain_tvls.items(), key=lambda x: x[1], reverse=True)
            total_tvl = sum(chain_tvls.values())
            
            result = f"""
🌐 全链 TVL 排名

💰 总TVL: ${total_tvl:,.0f}
📊 活跃链数: {len(sorted_chains)}

🏆 Top 链排名:
"""
            
            for i, (chain_name, tvl) in enumerate(sorted_chains[:MAX_RESULTS_DISPLAY], 1):
                if tvl > MIN_TVL_DISPLAY:
                    percentage = (tvl / total_tvl) * 100 if total_tvl > 0 else 0
                    result += f"{i:2d}. {chain_name:<12} ${tvl:>15,.0f} ({percentage:5.1f}%)\n"
        
        result += f"\n📅 数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return result
        
    except Exception as e:
        logger.error(f"查询链TVL排名失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_defi_rankings_filtered(query: str = "") -> str:
    """
    获取 DeFi 协议排名（支持过滤特定协议）
    输入: "分类名称" 或 "协议1,协议2" 或留空查看总排名
    """
    try:
        # 清理输入
        query = query.strip().strip('"').strip("'")
        if ':' in query:
            query = query.split(':', 1)[1].strip().strip('"').strip("'")
            
        logger.info(f"查询 DeFi 排名: {query}")
        
        protocols = defillama_client.get_protocols()
        
        # 检查是否是协议列表查询
        if ',' in query or query.lower() in POPULAR_PROTOCOLS:
            # 用户想要查询特定的几个协议
            protocol_names = [p.strip().lower() for p in query.split(',')]
            filtered_protocols = []
            
            for p in protocols:
                p_name = p.get("name", "").lower()
                p_slug = p.get("slug", "").lower() if p.get("slug") else ""
                
                # 检查协议名是否匹配
                for requested in protocol_names:
                    requested_id = POPULAR_PROTOCOLS.get(requested, requested)
                    if (requested in p_name or 
                        requested_id in p_name or 
                        requested == p_slug or
                        requested_id == p_slug or
                        p_name.startswith(requested) or
                        p_name.startswith(requested_id)):
                        filtered_protocols.append(p)
                        break
            
            title = f"指定协议对比"
        elif query:
            # 按分类过滤
            filtered_protocols = [
                p for p in protocols 
                if query.lower() in p.get("category", "").lower()
            ]
            title = f"{query.title()} 协议排名"
        else:
            filtered_protocols = protocols
            title = "DeFi 协议总排名"
        
        # 过滤和排序 - 确保 TVL 是有效数字
        valid_protocols = []
        for p in filtered_protocols:
            try:
                # 获取 TVL 值并确保是数字
                tvl = p.get("tvl", 0)
                if tvl is None:
                    tvl = 0
                else:
                    tvl = float(tvl)
                
                # 更新协议数据中的 TVL
                p["tvl"] = tvl
                
                # 比较查询时不限制最小 TVL
                if ',' in query or query.lower() in POPULAR_PROTOCOLS:
                    valid_protocols.append(p)
                else:
                    # 非比较查询时检查最小 TVL
                    if tvl > 1000000:  # 直接使用数值，避免 None 比较
                        valid_protocols.append(p)
                        
            except (ValueError, TypeError):
                # 如果无法转换为数字，跳过这个协议
                continue
        
        valid_protocols.sort(key=lambda x: x.get("tvl", 0), reverse=True)
        
        if not valid_protocols:
            return f"未找到符合条件的协议: {query}"
        
        total_tvl = sum(p.get("tvl", 0) for p in valid_protocols)
        
        result = f"""
🏆 {title}

💰 总TVL: ${total_tvl:,.0f}
📊 协议数量: {len(valid_protocols)}

🥇 协议详情:
"""
        
        # 如果是特定协议查询，显示所有；否则显示 top 20
        display_count = len(valid_protocols) if ',' in query or query.lower() in POPULAR_PROTOCOLS else min(MAX_RESULTS_DISPLAY, len(valid_protocols))
        
        for i, protocol in enumerate(valid_protocols[:display_count], 1):
            name = protocol.get("name", "Unknown")
            tvl = protocol.get("tvl", 0)
            change_1d = protocol.get("change_1d", 0)
            category_name = protocol.get("category", "Unknown")
            
            percentage = (tvl / total_tvl) * 100 if total_tvl > 0 else 0
            change_emoji = "📈" if change_1d > 0 else "📉" if change_1d < 0 else "➡️"
            
            result += f"{i:2d}. {name:<18} ${tvl:>12,.0f} ({percentage:4.1f}%) {change_emoji}{change_1d:+.1f}% [{category_name}]\n"
        
        # 如果是比较查询，添加额外的分析
        if len(valid_protocols) == 2:
            p1, p2 = valid_protocols[0], valid_protocols[1]
            tvl_diff = p1["tvl"] - p2["tvl"]
            tvl_ratio = p1["tvl"] / p2["tvl"] if p2["tvl"] > 0 else float('inf')
            
            result += f"""
📊 对比分析:
• {p1["name"]} 的 TVL 比 {p2["name"]} 高 ${tvl_diff:,.0f}
• {p1["name"]} 的 TVL 是 {p2["name"]} 的 {tvl_ratio:.2f} 倍
"""
        
        result += f"\n📅 数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return result
        
    except Exception as e:
        logger.error(f"查询DeFi排名失败: {str(e)}", exc_info=True)
        return f"查询失败: {str(e)}"

# === 价格查询工具 ===

def get_token_prices(query: str) -> str:
    """
    获取代币价格信息
    输入: "代币地址1,代币地址2" 或 "ethereum:0x..." 或 "solana:mint..."
    """
    try:
        # 清理输入
        query = query.strip().strip('"').strip("'")
        if ':' in query and not query.startswith(('ethereum:', 'solana:', 'bsc:', 'polygon:')):
            query = query.split(':', 1)[1].strip().strip('"').strip("'")
            
        logger.info(f"查询代币价格: {query}")
        
        # 解析输入
        coins = [coin.strip() for coin in query.split(",")]
        
        # 获取价格
        prices_data = defillama_client.get_current_prices(coins)
        
        if not prices_data or "coins" not in prices_data:
            return f"未找到价格数据: {query}"
        
        coins_data = prices_data["coins"]
        
        result = f"""
💰 代币价格查询

🕐 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
📊 查询代币数: {len(coins_data)}

💵 价格信息:
"""
        
        for coin_id, coin_data in coins_data.items():
            symbol = coin_data.get("symbol", "UNKNOWN")
            price = coin_data.get("price", 0)
            confidence = coin_data.get("confidence", 0)
            timestamp = coin_data.get("timestamp", 0)
            
            # 格式化时间
            price_time = datetime.fromtimestamp(timestamp).strftime('%H:%M') if timestamp else "未知"
            
            result += f"• {symbol}: ${price:,.6f} (置信度: {confidence:.1f}, 时间: {price_time})\n"
        
        return result
        
    except Exception as e:
        logger.error(f"查询代币价格失败: {str(e)}")
        return f"查询失败: {str(e)}"

# === DEX 数据查询工具 ===

def get_dex_overview(chain: str = "") -> str:
    """
    获取 DEX 概览数据
    输入: "链名" 或留空查看全部
    """
    try:
        # 清理输入
        chain = chain.strip().strip('"').strip("'")
        if ':' in chain:
            chain = chain.split(':', 1)[1].strip().strip('"').strip("'")
            
        logger.info(f"查询 DEX 概览: {chain}")
        
        if chain:

             # 修复：正确获取链映射
            chain_mapping = CHAIN_MAPPINGS.get(chain.lower())
            if chain_mapping:
                chain_name = chain_mapping.llama_name
            else:
                chain_name = chain

            # 查询特定链的 DEX 数据
            chain_data = defillama_client.get_dex_chain(chain_name)
            protocols = chain_data.get("protocols", [])
            
            total_volume = sum(p.get("total24h", 0) for p in protocols)
            
            result = f"""
🔄 {chain.title()} DEX 概览

💱 24小时总交易量: ${total_volume:,.0f}
📊 DEX 数量: {len(protocols)}

🏆 Top DEX:
"""
            
            # 排序并显示
            protocols.sort(key=lambda x: x.get("total24h", 0), reverse=True)
            
            for i, protocol in enumerate(protocols[:15], 1):
                name = protocol.get("name", "Unknown")
                volume_24h = protocol.get("total24h", 0)
                change_24h = protocol.get("change_24h", 0)
                
                if volume_24h > MIN_VOLUME_DISPLAY:
                    percentage = (volume_24h / total_volume) * 100 if total_volume > 0 else 0
                    change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                    
                    result += f"{i:2d}. {name:<18} ${volume_24h:>12,.0f} ({percentage:4.1f}%) {change_emoji}{change_24h:+.1f}%\n"
        
        else:
            # 全局 DEX 概览
            overview_data = defillama_client.get_dex_overview()
            protocols = overview_data.get("protocols", [])
            
            total_volume = sum(p.get("total24h", 0) for p in protocols)
            
            result = f"""
🌐 全链 DEX 概览

💱 24小时全网交易量: ${total_volume:,.0f}
📊 活跃 DEX 数量: {len(protocols)}

🏆 Top DEX 排名:
"""
            
            # 排序并显示
            protocols.sort(key=lambda x: x.get("total24h", 0), reverse=True)
            
            for i, protocol in enumerate(protocols[:MAX_RESULTS_DISPLAY], 1):
                name = protocol.get("name", "Unknown")
                volume_24h = protocol.get("total24h", 0)
                change_24h = protocol.get("change_24h", 0)
                
                if volume_24h > MIN_VOLUME_DISPLAY:
                    percentage = (volume_24h / total_volume) * 100 if total_volume > 0 else 0
                    change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                    
                    result += f"{i:2d}. {name:<18} ${volume_24h:>12,.0f} ({percentage:4.1f}%) {change_emoji}{change_24h:+.1f}%\n"
        
        result += f"\n📅 数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return result
        
    except Exception as e:
        logger.error(f"查询DEX概览失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_yield_opportunities(min_apy: float = 5.0) -> str:
    """
    获取收益机会
    输入: "最小年化收益率" (默认5%)
    """
    try:
        # 处理输入
        if isinstance(min_apy, str):
            min_apy = min_apy.strip().strip('"').strip("'")
            if ':' in min_apy:
                min_apy = min_apy.split(':', 1)[1].strip().strip('"').strip("'")
            try:
                min_apy = float(min_apy)
            except:
                min_apy = 5.0
                
        logger.info(f"查询收益机会: 最小APY {min_apy}%")
        
        pools_data = defillama_client.get_yield_pools()
        
        if not pools_data:
            return "无法获取收益池数据"
        
        # 过滤高收益池
        high_yield_pools = []
        for pool in pools_data.get("data", []):
            apy = pool.get("apy", 0)
            tvl = pool.get("tvlUsd", 0)
            
            if apy >= min_apy and tvl > 100000:  # TVL > 10万美元
                high_yield_pools.append(pool)
        
        # 按APY排序
        high_yield_pools.sort(key=lambda x: x.get("apy", 0), reverse=True)
        
        result = f"""
💎 DeFi 收益机会 (APY ≥ {min_apy}%)

🎯 筛选条件: APY ≥ {min_apy}% 且 TVL > $100,000
📊 符合条件: {len(high_yield_pools)} 个池子

🏆 Top 收益池:
"""
        
        for i, pool in enumerate(high_yield_pools[:15], 1):
            project = pool.get("project", "Unknown")
            symbol = pool.get("symbol", "Unknown")
            apy = pool.get("apy", 0)
            tvl = pool.get("tvlUsd", 0)
            chain = pool.get("chain", "Unknown")
            
            # 风险评估
            risk = "🟢"  # 低风险
            if apy > 100:
                risk = "🔴"  # 高风险
            elif apy > 50:
                risk = "🟡"  # 中风险
            
            result += f"{i:2d}. {risk} {project:<12} {symbol:<15} {apy:6.1f}% APY | ${tvl:>10,.0f} TVL | {chain}\n"
        
        result += f"""
🔍 风险说明:
🟢 低风险 (APY < 50%)  🟡 中风险 (50% ≤ APY < 100%)  🔴 高风险 (APY ≥ 100%)

⚠️ 投资提醒: 高收益往往伴随高风险，请仔细研究后投资

📅 数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        return result
        
    except Exception as e:
        logger.error(f"查询收益机会失败: {str(e)}")
        return f"查询失败: {str(e)}"

# === 稳定币数据查询工具 ===

def get_stablecoin_overview() -> str:
    """获取稳定币市场概览"""
    try:
        logger.info("查询稳定币概览")
        
        stablecoins_data = defillama_client.get_stablecoins()
        
        if not stablecoins_data:
            return "无法获取稳定币数据"
        
        peggedAssets = stablecoins_data.get("peggedAssets", [])
        
        # 计算总市值
        total_mcap = sum(asset.get("circulating", 0) for asset in peggedAssets)
        
        result = f"""
🏛️ 稳定币市场概览

💰 总市值: ${total_mcap:,.0f}
📊 稳定币数量: {len(peggedAssets)}

🏆 市值排名:
"""
        
        # 按市值排序
        peggedAssets.sort(key=lambda x: x.get("circulating", 0), reverse=True)
        
        for i, asset in enumerate(peggedAssets[:15], 1):
            name = asset.get("name", "Unknown")
            symbol = asset.get("symbol", "Unknown")
            mcap = asset.get("circulating", 0)
            change_1d = asset.get("circulating1dChange", 0)
            
            if mcap > 1000000:  # 市值 > 100万
                percentage = (mcap / total_mcap) * 100 if total_mcap > 0 else 0
                change_emoji = "📈" if change_1d > 0 else "📉" if change_1d < 0 else "➡️"
                
                result += f"{i:2d}. {symbol:<6} {name:<20} ${mcap:>12,.0f} ({percentage:4.1f}%) {change_emoji}{change_1d:+.1f}%\n"
        
        # 获取链分布
        chains_data = defillama_client.get_stablecoin_chains()
        if chains_data:
            result += "\n🔗 主要链分布:\n"
            
            # 处理链数据
            for chain_info in chains_data[:8]:
                chain_name = chain_info.get("name", "Unknown")
                total_circulating = chain_info.get("totalCirculating", 0)
                
                if total_circulating > 1000000:
                    percentage = (total_circulating / total_mcap) * 100 if total_mcap > 0 else 0
                    result += f"  • {chain_name}: ${total_circulating:,.0f} ({percentage:.1f}%)\n"
        
        result += f"\n📅 数据时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return result
        
    except Exception as e:
        logger.error(f"查询稳定币概览失败: {str(e)}")
        return f"查询失败: {str(e)}"

# 创建工具对象
defillama_tools = [
    Tool(
        name="GetProtocolInfo",
        description="获取单个DeFi协议的详细信息。输入格式：直接输入协议名称，如 'aave' 或 'uniswap'。不要输入多个协议。支持的协议：uniswap、aave、compound、curve、makerdao等。",
        func=get_protocol_info
    ),
    Tool(
        name="GetChainTVLRanking", 
        description="获取链的TVL排名。输入格式：直接输入链名（如 'ethereum'）或留空查看所有链排名。支持：ethereum、bsc、polygon、arbitrum等",
        func=get_chain_tvl_ranking
    ),
    Tool(
        name="GetDeFiRankings",
        description="获取DeFi协议排名。支持三种输入：1) 留空查看总排名 2) 输入分类名(如'lending') 3) 输入协议名列表(如'aave,uni')进行比较",
        func=get_defi_rankings_filtered
    ),
    Tool(
        name="GetTokenPrices",
        description="获取代币价格。输入格式：'代币地址1,代币地址2' 或 'ethereum:0x...' 或 'solana:mint...'",
        func=get_token_prices
    ),
    Tool(
        name="GetDEXOverview",
        description="获取DEX交易概览。输入格式：直接输入链名（如 'ethereum'）或留空查看全部链。显示24小时交易量排名",
        func=get_dex_overview
    ),
    Tool(
        name="GetYieldOpportunities",
        description="获取DeFi收益机会。输入格式：直接输入数字表示最小年化收益率（默认5）。筛选高APY的流动性挖矿池",
        func=get_yield_opportunities
    ),
    Tool(
        name="GetStablecoinOverview",
        description="获取稳定币市场概览。无需输入参数。显示市值排名、链分布等信息",
        func=get_stablecoin_overview
    ),
]