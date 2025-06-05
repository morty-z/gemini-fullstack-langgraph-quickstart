# app/agent/tools/graph/subgraph_discovery.py
"""
Subgraph Discovery - 简化版
联网搜索 subgraph_id
"""

import logging
import requests
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.agent.tools.graph.graph_config import GRAPH_API_KEY, get_graph_network_endpoint

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryResult:
    """发现结果"""
    subgraph_id: str
    name: str
    network: str
    signal: float
    is_synced: bool
    description: str = ""

class SubgraphDiscovery:
    """子图发现器 - 简化版"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GRAPH_API_KEY
        if not self.api_key:
            logger.warning("⚠️ 未设置 GRAPH_API_KEY，无法联网搜索")
            self.endpoint = None
        else:
            self.endpoint = get_graph_network_endpoint()
    
    def find(self, protocol: str, network: str, version: Optional[str] = None) -> Optional[str]:
        """
        查找 subgraph_id
        
        Args:
            protocol: 协议名
            network: 网络名
            version: 版本号 (可选)
            
        Returns:
            subgraph_id 或 None
        """
        if not self.endpoint:
            logger.error("❌ 无法联网搜索：未设置 API Key")
            return None
        
        logger.info(f"🌐 联网搜索: {protocol} on {network}")
        
        # 1. 基于协议名直接搜索
        result = self._search_by_protocol_name(protocol, network, version)
        if result:
            logger.info(f"✅ 协议名搜索成功: {result.name}")
            return result.subgraph_id
        
        # 2. 在高信号量子图中搜索
        result = self._search_in_high_signal_subgraphs(protocol, network)
        if result:
            logger.info(f"✅ 高信号量搜索成功: {result.name}")
            return result.subgraph_id
        
        logger.warning(f"❌ 未发现: {protocol} on {network}")
        return None
    
    def _search_by_protocol_name(self, protocol: str, network: str, version: Optional[str] = None) -> Optional[DiscoveryResult]:
        """基于协议名搜索"""
        
        # 构建搜索词
        search_terms = [protocol]
        if version:
            search_terms.append(f"{protocol} {version}")
            search_terms.append(f"{protocol}{version}")
        
        for search_term in search_terms:
            logger.debug(f"🔍 搜索词: {search_term}")
            
            results = self._execute_search_query(search_term)
            
            # 过滤匹配的结果
            for result in results:
                if (result.network.lower() == network.lower() and 
                    protocol.lower() in result.name.lower()):
                    return result
        
        return None
    
    def _search_in_high_signal_subgraphs(self, protocol: str, network: str) -> Optional[DiscoveryResult]:
        """在高信号量子图中搜索"""
        
        query = """
        query HighSignalSubgraphs($minSignal: String!) {
            subgraphs(
                first: 50,
                orderBy: currentSignalledTokens,
                orderDirection: desc,
                where: {
                    currentSignalledTokens_gt: $minSignal,
                    active: true
                }
            ) {
                id
                displayName
                description
                currentSignalledTokens
                currentVersion {
                    subgraphDeployment {
                        manifest {
                            network
                            description
                        }
                        indexingStatus {
                            synced
                            health
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "minSignal": str(int(1000 * 1e18))  # 1000 GRT
        }
        
        try:
            response = requests.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" not in data:
                    results = self._parse_search_results(data)
                    
                    # 查找匹配的协议
                    for result in results:
                        if (result.network.lower() == network.lower() and
                            (protocol.lower() in result.name.lower() or
                             protocol.lower() in result.description.lower())):
                            return result
            
        except Exception as e:
            logger.error(f"高信号量搜索失败: {e}")
        
        return None
    
    def _execute_search_query(self, search_term: str) -> List[DiscoveryResult]:
        """执行搜索查询"""
        
        query = """
        query SearchSubgraphs($text: String!) {
            subgraphs(
                where: {
                    displayName_contains_nocase: $text,
                    active: true
                },
                first: 10,
                orderBy: currentSignalledTokens,
                orderDirection: desc
            ) {
                id
                displayName
                description
                currentSignalledTokens
                currentVersion {
                    subgraphDeployment {
                        manifest {
                            network
                            description
                        }
                        indexingStatus {
                            synced
                            health
                        }
                    }
                }
            }
        }
        """
        
        variables = {"text": search_term}
        
        try:
            response = requests.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" not in data:
                    return self._parse_search_results(data)
            else:
                logger.error(f"搜索请求失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"搜索执行失败: {e}")
        
        return []
    
    def _parse_search_results(self, data: Dict[str, Any]) -> List[DiscoveryResult]:
        """解析搜索结果"""
        results = []
        subgraphs = data.get("data", {}).get("subgraphs", [])
        
        for subgraph in subgraphs:
            try:
                current_version = subgraph.get("currentVersion", {})
                if not current_version:
                    continue
                
                deployment = current_version.get("subgraphDeployment", {})
                if not deployment:
                    continue
                
                manifest = deployment.get("manifest", {})
                indexing_status = deployment.get("indexingStatus", {})
                
                # 跳过不健康的子图
                if indexing_status.get("health") == "failed":
                    continue
                
                # 计算信号量
                signal = float(subgraph.get("currentSignalledTokens", 0)) / 1e18
                
                result = DiscoveryResult(
                    subgraph_id=subgraph.get("id", ""),
                    name=subgraph.get("displayName", "Unknown"),
                    network=manifest.get("network", "unknown"),
                    signal=signal,
                    is_synced=indexing_status.get("synced", False),
                    description=manifest.get("description", subgraph.get("description", ""))
                )
                
                results.append(result)
                
            except Exception as e:
                logger.debug(f"解析子图结果时出错: {e}")
                continue
        
        return results
    
    def search_and_add_to_registry(self, protocol: str, network: str, registry, 
                                  version: Optional[str] = None) -> Optional[str]:
        """
        搜索并自动添加到注册表
        
        Args:
            protocol: 协议名
            network: 网络名
            registry: 注册表实例
            version: 版本号
            
        Returns:
            找到的 subgraph_id
        """
        subgraph_id = self.find(protocol, network, version)
        
        if subgraph_id:
            # 获取详细信息用于添加到注册表
            details = self._get_subgraph_details(subgraph_id)
            
            if details:
                success = registry.add(
                    protocol=protocol,
                    network=network,
                    version=version,
                    subgraph_id=subgraph_id,
                    name=details.get("name", f"{protocol.title()} on {network.title()}"),
                    health_status="healthy" if details.get("is_synced") else "syncing"
                )
                
                if success:
                    logger.info(f"✅ 自动添加到注册表: {protocol}-{network}")
                else:
                    logger.error(f"❌ 添加到注册表失败: {protocol}-{network}")
        
        return subgraph_id
    
    def _get_subgraph_details(self, subgraph_id: str) -> Optional[Dict[str, Any]]:
        """获取子图详细信息"""
        
        query = """
        query GetSubgraphDetails($id: ID!) {
            subgraph(id: $id) {
                id
                displayName
                description
                currentVersion {
                    subgraphDeployment {
                        manifest {
                            network
                        }
                        indexingStatus {
                            synced
                            health
                        }
                    }
                }
                currentSignalledTokens
            }
        }
        """
        
        variables = {"id": subgraph_id}
        
        try:
            response = requests.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                subgraph = data.get("data", {}).get("subgraph")
                
                if subgraph:
                    deployment = subgraph.get("currentVersion", {}).get("subgraphDeployment", {})
                    indexing_status = deployment.get("indexingStatus", {})
                    
                    return {
                        "name": subgraph.get("displayName", "Unknown"),
                        "description": subgraph.get("description", ""),
                        "network": deployment.get("manifest", {}).get("network", "unknown"),
                        "is_synced": indexing_status.get("synced", False),
                        "health": indexing_status.get("health", "unknown"),
                        "signal": float(subgraph.get("currentSignalledTokens", 0)) / 1e18
                    }
            
        except Exception as e:
            logger.error(f"获取子图详情失败: {e}")
        
        return None