# app/agent/tools/defillama/defillama_client.py
"""
DeFiLlama API 客户端
处理所有 API 请求，支持错误处理（移除缓存功能）
"""

import requests
import logging
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from app.agent.tools.defillama.defillama_config import (
    BASE_URL, COINS_BASE_URL, YIELDS_BASE_URL, STABLECOINS_BASE_URL,
    ENDPOINTS, DEFAULT_TIMEOUT, MAX_RETRIES, RATE_LIMIT_DELAY,
    CHAIN_MAPPINGS
)

logger = logging.getLogger(__name__)

class DeFiLlamaClient:
    """DeFiLlama API 客户端"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; DeFiBot/1.0)"
        })
        
        # 请求记录（用于速率限制）
        self.last_request_time = 0
    
    def _make_request(self, url: str) -> Any:
        """
        发送 API 请求（无缓存版本）
        
        Args:
            url: 请求 URL
            
        Returns:
            API 响应结果
        """
        # 速率限制
        current_time = time.time()
        if current_time - self.last_request_time < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY)
        
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"请求 DeFiLlama API: {url} (尝试 {attempt + 1})")
                
                response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                self.last_request_time = time.time()
                
                return data
                
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"DeFiLlama API 超时: {url}")
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # 速率限制，增加等待时间
                    wait_time = min(2 ** attempt, 10)
                    logger.warning(f"触发速率限制，等待 {wait_time} 秒")
                    time.sleep(wait_time)
                    last_error = "速率限制"
                else:
                    last_error = f"HTTP 错误: {e.response.status_code}"
                    logger.error(f"DeFiLlama API HTTP 错误: {e}")
                    break
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"DeFiLlama API 请求失败: {e}")
                
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
        
        raise Exception(f"DeFiLlama API 请求失败: {last_error}")
    
    # === TVL 相关方法 ===
    
    def get_protocols(self) -> List[Dict]:
        """获取所有协议列表"""
        url = f"{BASE_URL}{ENDPOINTS['protocols']}"
        return self._make_request(url)
    
    def get_protocol_tvl(self, protocol: str) -> Dict:
        """获取协议的 TVL 数据"""
        url = f"{BASE_URL}{ENDPOINTS['protocol'].format(protocol=protocol)}"
        return self._make_request(url)
    
    def get_chain_tvl(self, chain: str) -> List[Dict]:
        """获取链的历史 TVL 数据"""
        chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
        url = f"{BASE_URL}{ENDPOINTS['tvl_chart'].format(chain=chain_name)}"
        return self._make_request(url)
    
    def get_current_tvl(self, chain: str) -> Dict:
        """获取链的当前 TVL"""
        chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
        url = f"{BASE_URL}{ENDPOINTS['tvl_current'].format(chain=chain_name)}"
        return self._make_request(url)
    
    # === 价格相关方法 ===
    
    def get_current_prices(self, coins: Union[str, List[str]]) -> Dict:
        """获取代币当前价格"""
        if isinstance(coins, list):
            coins = ",".join(coins)
        
        url = f"{COINS_BASE_URL}{ENDPOINTS['prices_current'].format(coins=coins)}"
        return self._make_request(url)
    
    def get_historical_prices(self, timestamp: int, coins: Union[str, List[str]]) -> Dict:
        """获取历史价格"""
        if isinstance(coins, list):
            coins = ",".join(coins)
            
        url = f"{COINS_BASE_URL}{ENDPOINTS['prices_historical'].format(timestamp=timestamp, coins=coins)}"
        return self._make_request(url)
    
    def get_price_chart(self, chain: str, timestamp: int = None) -> Dict:
        """获取链上代币价格图表"""
        if not timestamp:
            timestamp = int(time.time())
            
        chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
        url = f"{COINS_BASE_URL}{ENDPOINTS['prices_chart'].format(chain=chain_name, timestamp=timestamp)}"
        return self._make_request(url)
    
    # === 收益相关方法 ===
    
    def get_yield_pools(self) -> List[Dict]:
        """获取所有收益池"""
        url = f"{YIELDS_BASE_URL}{ENDPOINTS['pools']}"
        return self._make_request(url)
    
    def get_pool_chart(self, pool_id: str) -> Dict:
        """获取收益池历史数据"""
        url = f"{YIELDS_BASE_URL}{ENDPOINTS['pool'].format(pool_id=pool_id)}"
        return self._make_request(url)
    
    # === 稳定币相关方法 ===
    
    def get_stablecoins(self) -> Dict:
        """获取所有稳定币数据"""
        url = f"{STABLECOINS_BASE_URL}{ENDPOINTS['stablecoins']}"
        return self._make_request(url)
    
    def get_stablecoin(self, stablecoin_id: str) -> Dict:
        """获取特定稳定币数据"""
        url = f"{STABLECOINS_BASE_URL}{ENDPOINTS['stablecoin'].format(stablecoin_id=stablecoin_id)}"
        return self._make_request(url)
    
    def get_stablecoin_charts(self) -> Dict:
        """获取所有稳定币图表数据"""
        url = f"{STABLECOINS_BASE_URL}{ENDPOINTS['stablecoin_chart']}"
        return self._make_request(url)
    
    def get_stablecoin_chains(self) -> Dict:
        """获取稳定币在各链的分布"""
        url = f"{STABLECOINS_BASE_URL}{ENDPOINTS['stablecoin_chains']}"
        return self._make_request(url)
    
    # === DEX 相关方法 ===
    
    def get_dex_overview(self) -> Dict:
        """获取 DEX 概览"""
        url = f"{BASE_URL}{ENDPOINTS['dexs']}"
        return self._make_request(url)
    
    def get_dex_protocol(self, protocol: str) -> Dict:
        """获取特定 DEX 协议数据"""
        url = f"{BASE_URL}{ENDPOINTS['dex'].format(protocol=protocol)}"
        return self._make_request(url)
    
    def get_dex_chain(self, chain: str) -> Dict:
        """获取链上 DEX 数据"""
        chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
        url = f"{BASE_URL}{ENDPOINTS['dex_chains'].format(chain=chain_name)}"
        return self._make_request(url)
    
    # === 费用相关方法 ===
    
    def get_fees_overview(self) -> Dict:
        """获取费用概览"""
        url = f"{BASE_URL}{ENDPOINTS['fees']}"
        return self._make_request(url)
    
    def get_protocol_fees(self, protocol: str) -> Dict:
        """获取协议费用数据"""
        url = f"{BASE_URL}{ENDPOINTS['fees_protocol'].format(protocol=protocol)}"
        return self._make_request(url)
    
    def get_chain_fees(self, chain: str) -> Dict:
        """获取链费用数据"""
        chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
        url = f"{BASE_URL}{ENDPOINTS['fees_chain'].format(chain=chain_name)}"
        return self._make_request(url)
    
    # === 桥接相关方法 ===
    
    def get_bridges(self) -> List[Dict]:
        """获取所有桥接协议"""
        url = f"{BASE_URL}{ENDPOINTS['bridges']}"
        return self._make_request(url)
    
    def get_bridge(self, bridge_id: str) -> Dict:
        """获取特定桥接协议数据"""
        url = f"{BASE_URL}{ENDPOINTS['bridge'].format(bridge_id=bridge_id)}"
        return self._make_request(url)
    
    def get_bridge_volume(self, chain: str) -> Dict:
        """获取链的桥接量数据"""
        chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
        url = f"{BASE_URL}{ENDPOINTS['bridge_volume'].format(chain=chain_name)}"
        return self._make_request(url)
    
    # === 衍生品相关方法 ===
    
    def get_derivatives_overview(self) -> Dict:
        """获取衍生品概览"""
        url = f"{BASE_URL}{ENDPOINTS['derivatives']}"
        return self._make_request(url)
    
    def get_derivatives_protocol(self, protocol: str) -> Dict:
        """获取衍生品协议数据"""
        url = f"{BASE_URL}{ENDPOINTS['derivatives_protocol'].format(protocol=protocol)}"
        return self._make_request(url)
    
    # === CEX 和期权相关方法 ===
    
    def get_cex_overview(self) -> Dict:
        """获取 CEX 概览"""
        url = f"{BASE_URL}{ENDPOINTS['cex']}"
        return self._make_request(url)
    
    def get_options_overview(self) -> Dict:
        """获取期权概览"""
        url = f"{BASE_URL}{ENDPOINTS['options']}"
        return self._make_request(url)
    
    def get_options_chain(self, chain: str) -> Dict:
        """获取链上期权数据"""
        chain_name = CHAIN_MAPPINGS.get(chain.lower(), {}).get("llama_name", chain)
        url = f"{BASE_URL}{ENDPOINTS['options_chain'].format(chain=chain_name)}"
        return self._make_request(url)

# 全局客户端实例
defillama_client = DeFiLlamaClient()