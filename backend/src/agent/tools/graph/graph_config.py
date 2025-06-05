# app/agent/tools/graph/graph_config.py
"""
The Graph Protocol 配置文件 - 精简版
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# API Key
GRAPH_API_KEY = os.getenv("GRAPH_API_KEY", "")

# API 端点
API_ENDPOINTS = {
    "subgraph_gateway": "https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{subgraph_id}",
    "graph_network_subgraph": "https://gateway.thegraph.com/api/{api_key}/subgraphs/id/DZz4kDTdmzWLWsV373w2bSmoar3umKKH9y82SUKr5qmp"
}

# 支持的网络
SUPPORTED_NETWORKS = {
    "ethereum": {"name": "ethereum", "display_name": "Ethereum"},
    "polygon": {"name": "polygon", "display_name": "Polygon"},
    "arbitrum": {"name": "arbitrum", "display_name": "Arbitrum"},
    "optimism": {"name": "optimism", "display_name": "Optimism"},
    "bsc": {"name": "bsc", "display_name": "BSC"},
}

# 查询设置
QUERY_SETTINGS = {
    "default_first": 100,
    "max_first": 1000,
    "query_timeout": 30,
    "max_retries": 3,
}

# 缓存设置
CACHE_SETTINGS = {
    "enabled": True,
    "ttl": 300,
    "cache_dir": "cache",
    "registry_cache_days": 7,
}

# 协议分类
PROTOCOL_CATEGORIES = {
    "DEX": ["Decentralized Exchange", "AMM", "Swap"],
    "Lending": ["Lending Protocol", "Borrowing"],
    "Derivatives": ["Perpetuals", "Options"],
    "Yield": ["Yield Aggregator", "Farming"],
    "Staking": ["Liquid Staking"],
}

# 格式设置
FORMAT_SETTINGS = {
    "decimal_places": 2,
    "short_address_length": 6,
}

# 阈值
THRESHOLDS = {
    "min_tvl_display": 1000,
    "high_signal_grt": 1000,
}

# 错误消息
ERROR_MESSAGES = {
    "no_subgraph": "未找到合适的子图",
    "invalid_query": "无法确定查询类型",
    "no_params": "无法提取查询参数",
    "query_failed": "查询构建失败",
    "execution_failed": "查询执行失败",
    "no_api_key": "Graph 功能未配置，请设置 GRAPH_API_KEY 环境变量",
    "api_key_missing": "Graph 功能未配置，请设置 GRAPH_API_KEY 环境变量",
}

# 工具函数
def get_subgraph_endpoint(subgraph_id: str) -> str:
    """获取子图端点 URL"""
    if not GRAPH_API_KEY:
        raise ValueError(ERROR_MESSAGES["no_api_key"])
    
    return API_ENDPOINTS["subgraph_gateway"].format(
        api_key=GRAPH_API_KEY,
        subgraph_id=subgraph_id
    )

def get_graph_network_endpoint() -> str:
    """获取 Graph Network 子图端点"""
    if not GRAPH_API_KEY:
        raise ValueError(ERROR_MESSAGES["no_api_key"])
    
    return API_ENDPOINTS["graph_network_subgraph"].format(
        api_key=GRAPH_API_KEY
    )

def is_valid_subgraph_id(subgraph_id: str) -> bool:
    """验证 Subgraph ID 格式"""
    if not subgraph_id:
        return False
    
    # 长度检查
    if len(subgraph_id) < 30 or len(subgraph_id) > 60:
        return False
    
    # 字符检查 - 只允许字母数字
    return subgraph_id.isalnum()

def format_number(value: float, decimals: int = None) -> str:
    """格式化数字"""
    if decimals is None:
        decimals = FORMAT_SETTINGS["decimal_places"]
    
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.{decimals}f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.{decimals}f}K"
    else:
        return f"{value:.{decimals}f}"

def format_address(address: str) -> str:
    """格式化地址（缩短）"""
    if not address or len(address) < 10:
        return address
    
    length = FORMAT_SETTINGS["short_address_length"]
    return f"{address[:length]}...{address[-length:]}"

# 向后兼容
ENDPOINTS = API_ENDPOINTS
get_network_endpoint = get_subgraph_endpoint
is_valid_deployment_id = is_valid_subgraph_id