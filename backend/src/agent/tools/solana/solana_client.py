# app/agent/tools/solana/solana_client.py
"""
Solana RPC 客户端
支持多个 RPC 端点，自动故障转移
"""

import requests
import logging
import time
import base64
import base58
from typing import Dict, Any, List, Optional, Union
from app.agent.tools.solana.solana_config import (
    RPC_PROVIDERS, REQUEST_CONFIG, ERROR_CONFIG
)

logger = logging.getLogger(__name__)

class SolanaRPCClient:
    """Solana RPC 客户端"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
        })
        self.failure_counts = {}
        self.current_slot = None
    
    def call_rpc(self, method: str, params: List[Any] = None) -> Any:
        """
        调用 Solana RPC 方法
        
        Args:
            method: RPC 方法名
            params: 方法参数
            
        Returns:
            RPC 响应结果
        """
        # 按失败次数排序 RPC URLs
        sorted_urls = sorted(
            RPC_PROVIDERS, 
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
                if attempt > 0:
                    time.sleep(REQUEST_CONFIG.rate_limit_delay)
                
                logger.debug(f"尝试 Solana RPC: {url} (方法: {method})")
                
                response = self.session.post(
                    url, 
                    json=payload, 
                    timeout=REQUEST_CONFIG.timeout
                )
                
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    error_msg = data["error"]
                    logger.warning(f"RPC 错误: {error_msg}")
                    
                    # 如果是需要认证的错误，严重惩罚
                    if any(word in str(error_msg).lower() for word in ["unauthorized", "forbidden", "api key"]):
                        self.failure_counts[url] = self.failure_counts.get(url, 0) + 10
                        last_error = f"RPC 错误: {error_msg}"
                        continue
                    else:
                        # 其他 RPC 错误，轻微惩罚
                        self.failure_counts[url] = self.failure_counts.get(url, 0) + 1
                        last_error = f"RPC 错误: {error_msg}"
                        continue
                
                # 成功，减少失败计数
                if url in self.failure_counts:
                    self.failure_counts[url] = max(0, self.failure_counts[url] - 1)
                
                return data.get("result")
                
            except requests.exceptions.Timeout:
                logger.warning(f"Solana RPC {url} 超时")
                self.failure_counts[url] = self.failure_counts.get(url, 0) + 2
                last_error = "请求超时"
                
            except Exception as e:
                logger.warning(f"Solana RPC {url} 错误: {str(e)}")
                self.failure_counts[url] = self.failure_counts.get(url, 0) + 1
                last_error = str(e)
        
        raise Exception(f"所有 Solana RPC 端点都失败了。最后的错误: {last_error}")
    
    def get_balance(self, pubkey: str) -> int:
        """获取账户余额（lamports）"""
        result = self.call_rpc("getBalance", [pubkey, {"commitment": REQUEST_CONFIG.commitment}])
        return result.get("value", 0)
    
    def get_token_accounts_by_owner(self, owner: str, mint: Optional[str] = None) -> List[Dict]:
        """获取账户的所有代币账户"""
        params = [
            owner,
            {"mint": mint} if mint else {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed", "commitment": REQUEST_CONFIG.commitment}
        ]
        
        result = self.call_rpc("getTokenAccountsByOwner", params)
        return result.get("value", [])
    
    def get_account_info(self, pubkey: str) -> Optional[Dict]:
        """获取账户信息"""
        result = self.call_rpc("getAccountInfo", [
            pubkey, 
            {"encoding": "jsonParsed", "commitment": REQUEST_CONFIG.commitment}
        ])
        return result.get("value")
    
    def get_transaction(self, signature: str) -> Optional[Dict]:
        """获取交易信息"""
        result = self.call_rpc("getTransaction", [
            signature,
            {
                "encoding": "jsonParsed", 
                "commitment": REQUEST_CONFIG.commitment, 
                "maxSupportedTransactionVersion": 0
            }
        ])
        return result
    
    def get_recent_blockhash(self) -> Dict:
        """获取最近的区块哈希"""
        return self.call_rpc("getRecentBlockhash", [{"commitment": REQUEST_CONFIG.commitment}])
    
    def get_slot(self) -> int:
        """获取当前 slot"""
        return self.call_rpc("getSlot", [{"commitment": REQUEST_CONFIG.commitment}])
    
    def get_epoch_info(self) -> Dict:
        """获取 epoch 信息"""
        return self.call_rpc("getEpochInfo", [{"commitment": REQUEST_CONFIG.commitment}])
    
    def get_block_time(self, slot: int) -> Optional[int]:
        """获取区块时间戳"""
        return self.call_rpc("getBlockTime", [slot])
    
    def get_signatures_for_address(self, address: str, limit: int = 10) -> List[Dict]:
        """获取地址的交易签名列表"""
        result = self.call_rpc("getSignaturesForAddress", [
            address,
            {"limit": limit, "commitment": REQUEST_CONFIG.commitment}
        ])
        return result
    
    def get_token_supply(self, mint: str) -> Dict:
        """获取代币总供应量"""
        result = self.call_rpc("getTokenSupply", [mint, {"commitment": REQUEST_CONFIG.commitment}])
        return result.get("value", {})
    
    def get_minimum_balance_for_rent_exemption(self, data_length: int) -> int:
        """获取租金豁免所需的最小余额"""
        return self.call_rpc("getMinimumBalanceForRentExemption", [data_length])
    
    def is_valid_address(self, address: str) -> bool:
        """验证 Solana 地址格式"""
        try:
            # Solana 地址是 base58 编码的 32 字节
            decoded = base58.b58decode(address)
            return len(decoded) == 32
        except:
            return False
    
    def get_block(self, slot: int) -> Optional[Dict]:
        """获取区块信息"""
        result = self.call_rpc("getBlock", [
            slot,
            {
                "encoding": "jsonParsed",
                "transactionDetails": "none",
                "commitment": REQUEST_CONFIG.commitment
            }
        ])
        return result
    
    def get_block_height(self) -> int:
        """获取区块高度"""
        return self.call_rpc("getBlockHeight", [{"commitment": REQUEST_CONFIG.commitment}])
    
    def get_cluster_nodes(self) -> List[Dict]:
        """获取集群节点信息"""
        return self.call_rpc("getClusterNodes", [])
    
    def get_version(self) -> Dict:
        """获取节点版本信息"""
        return self.call_rpc("getVersion", [])
    
    def get_supply(self) -> Dict:
        """获取总供应量信息"""
        result = self.call_rpc("getSupply", [{"commitment": REQUEST_CONFIG.commitment}])
        return result.get("value", {})
    
    def get_stake_activation(self, pubkey: str) -> Dict:
        """获取质押激活状态"""
        result = self.call_rpc("getStakeActivation", [
            pubkey,
            {"commitment": REQUEST_CONFIG.commitment}
        ])
        return result
    
    def batch_call(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """
        批量 RPC 调用
        
        Args:
            requests: 请求列表，每个请求包含 method 和 params
            
        Returns:
            结果列表
        """
        batch_payload = []
        for i, req in enumerate(requests):
            batch_payload.append({
                "jsonrpc": "2.0",
                "method": req["method"],
                "params": req.get("params", []),
                "id": i + 1
            })
        
        # 按失败次数排序选择最佳 RPC
        sorted_urls = sorted(
            RPC_PROVIDERS, 
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
    
    def get_best_rpc(self) -> str:
        """获取当前最佳的 RPC URL"""
        if not RPC_PROVIDERS:
            raise ValueError("没有配置 RPC 端点")
        
        # 返回失败次数最少的
        return min(
            RPC_PROVIDERS,
            key=lambda url: self.failure_counts.get(url, 0)
        )
    
    def get_rpc_status(self) -> Dict[str, Any]:
        """获取 RPC 状态信息"""
        status = []
        for url in RPC_PROVIDERS:
            failures = self.failure_counts.get(url, 0)
            status.append({
                "url": url,
                "failures": failures,
                "status": "healthy" if failures == 0 else "degraded" if failures < 5 else "unhealthy"
            })
        return {"endpoints": status, "total": len(RPC_PROVIDERS)}

# 全局客户端实例
solana_client = SolanaRPCClient()