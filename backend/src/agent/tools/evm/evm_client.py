# app/agent/tools/evm/evm_client.py
"""
EVM RPC 客户端
支持多个 RPC 端点，自动故障转移
"""

import requests
import logging
import time
from typing import Dict, Any, List, Optional, Union
from app.agent.tools.evm.evm_config import (
    RPC_ENDPOINTS, REQUEST_CONFIG, get_rpc_endpoints,
    SECURITY_CONFIG, ERROR_CONFIG
)

logger = logging.getLogger(__name__)

class EVMRPCClient:
    """EVM RPC 客户端，支持多个端点和故障转移"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        # 记录每个 RPC 的失败次数，用于智能选择
        self.failure_counts = {}
    
    def call_rpc(self, chain: str, method: str, params: List[Any] = None) -> Any:
        """
        调用 RPC 方法，自动故障转移
        
        Args:
            chain: 链名称
            method: RPC 方法名
            params: 方法参数
            
        Returns:
            RPC 响应结果
        """
        chain_lower = chain.lower()
        rpc_urls = get_rpc_endpoints(chain)
        
        if not rpc_urls:
            raise ValueError(f"不支持的链: {chain}")
        
        # 按失败次数排序 RPC URLs（失败少的优先）
        sorted_urls = sorted(
            rpc_urls, 
            key=lambda url: self.failure_counts.get(url, 0)
        )
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1
        }
        
        last_error = None
        
        for attempt, url in enumerate(sorted_urls[:REQUEST_CONFIG.max_retries]):
            try:
                # 添加速率限制
                if attempt > 0:
                    time.sleep(REQUEST_CONFIG.rate_limit_delay)
                
                logger.debug(f"尝试 RPC: {url} (方法: {method})")
                
                response = self.session.post(
                    url, 
                    json=payload, 
                    timeout=REQUEST_CONFIG.timeout
                )
                
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    error_msg = data["error"]
                    
                    # 如果是需要认证的错误，标记这个 RPC
                    if any(word in str(error_msg).lower() for word in ["unauthorized", "forbidden", "api key"]):
                        self.failure_counts[url] = self.failure_counts.get(url, 0) + 10
                        logger.warning(f"RPC {url} 需要认证")
                        last_error = f"RPC 错误: {error_msg}"
                        continue
                    else:
                        raise Exception(f"RPC 错误: {error_msg}")
                
                # 成功，重置失败计数
                if url in self.failure_counts:
                    self.failure_counts[url] = max(0, self.failure_counts[url] - 1)
                
                return data.get("result")
                
            except requests.exceptions.Timeout:
                logger.warning(f"RPC {url} 超时")
                self.failure_counts[url] = self.failure_counts.get(url, 0) + 1
                last_error = "请求超时"
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"RPC {url} 网络错误: {str(e)}")
                self.failure_counts[url] = self.failure_counts.get(url, 0) + 1
                last_error = f"网络错误: {str(e)}"
                
            except Exception as e:
                logger.warning(f"RPC {url} 错误: {str(e)}")
                self.failure_counts[url] = self.failure_counts.get(url, 0) + 1
                last_error = str(e)
        
        # 所有 RPC 都失败了
        raise Exception(f"所有 RPC 端点都失败了。最后的错误: {last_error}")
    
    def batch_call(self, chain: str, requests: List[Dict[str, Any]]) -> List[Any]:
        """
        批量 RPC 调用
        
        Args:
            chain: 链名称
            requests: 请求列表，每个请求包含 method 和 params
            
        Returns:
            结果列表
        """
        # 检查批量大小限制
        if len(requests) > SECURITY_CONFIG["max_batch_size"]:
            raise ValueError(f"批量请求数量超过限制: {len(requests)} > {SECURITY_CONFIG['max_batch_size']}")
        
        batch_payload = []
        for i, req in enumerate(requests):
            batch_payload.append({
                "jsonrpc": "2.0",
                "method": req["method"],
                "params": req.get("params", []),
                "id": i + 1
            })
        
        # 使用第一个可用的 RPC
        chain_lower = chain.lower()
        rpc_urls = get_rpc_endpoints(chain)
        
        if not rpc_urls:
            raise ValueError(f"不支持的链: {chain}")
        
        # 按失败次数排序
        sorted_urls = sorted(
            rpc_urls, 
            key=lambda url: self.failure_counts.get(url, 0)
        )
        
        for url in sorted_urls[:3]:  # 只尝试前3个
            try:
                response = self.session.post(
                    url,
                    json=batch_payload,
                    timeout=REQUEST_CONFIG.timeout * 2  # 批量请求给更多时间
                )
                response.raise_for_status()
                
                results = response.json()
                # 按 ID 排序并提取结果
                sorted_results = sorted(results, key=lambda x: x.get("id", 0))
                return [r.get("result") for r in sorted_results]
                
            except Exception as e:
                logger.warning(f"批量请求失败 {url}: {str(e)}")
                continue
        
        raise Exception("批量请求失败")
    
    def get_best_rpc(self, chain: str) -> str:
        """获取当前最佳的 RPC URL"""
        chain_lower = chain.lower()
        rpc_urls = get_rpc_endpoints(chain)
        
        if not rpc_urls:
            raise ValueError(f"不支持的链: {chain}")
        
        # 返回失败次数最少的
        return min(
            rpc_urls,
            key=lambda url: self.failure_counts.get(url, 0)
        )
    
    def get_rpc_status(self) -> Dict[str, Any]:
        """获取 RPC 状态信息"""
        status = {}
        for chain in RPC_ENDPOINTS.keys():
            rpc_urls = get_rpc_endpoints(chain)
            chain_status = []
            for url in rpc_urls:
                failures = self.failure_counts.get(url, 0)
                chain_status.append({
                    "url": url,
                    "failures": failures,
                    "status": "healthy" if failures == 0 else "degraded" if failures < 5 else "unhealthy"
                })
            status[chain] = chain_status
        return status

# 全局客户端实例
evm_client = EVMRPCClient()