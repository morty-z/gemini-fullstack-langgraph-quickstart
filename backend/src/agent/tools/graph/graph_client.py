# app/agent/tools/graph/graph_client.py
"""
Graph API 客户端 - 使用 Subgraph IDs
"""

import logging
from typing import Dict, Any, Optional
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.exceptions import TransportQueryError

from app.agent.tools.graph.graph_config import (
    GRAPH_API_KEY, QUERY_SETTINGS, ERROR_MESSAGES,
    get_subgraph_endpoint, is_valid_subgraph_id
)

logger = logging.getLogger(__name__)

class GraphClient:
    """Graph 去中心化网络客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.clients: Dict[str, Client] = {}
        self.api_key = GRAPH_API_KEY
        
        if not self.api_key:
            logger.error(ERROR_MESSAGES["no_api_key"])
    
    def get_or_create_client(self, subgraph_id: str) -> Optional[Client]:
        """获取或创建子图客户端"""
        if not self.api_key:
            logger.error(ERROR_MESSAGES["no_api_key"])
            return None
        
        # 验证 subgraph ID
        if not is_valid_subgraph_id(subgraph_id):
            logger.error(f"无效的 subgraph ID: {subgraph_id}")
            return None
            
        if subgraph_id not in self.clients:
            try:
                # 构建端点 URL
                endpoint = get_subgraph_endpoint(subgraph_id)
                
                transport = RequestsHTTPTransport(
                    url=endpoint,
                    headers={
                        "User-Agent": "GraphProtocolClient/1.0",
                        "Content-Type": "application/json",
                    },
                    verify=True,
                    retries=QUERY_SETTINGS["max_retries"],
                    timeout=QUERY_SETTINGS["query_timeout"]
                )
                
                client = Client(
                    transport=transport,
                    fetch_schema_from_transport=False  # 避免额外的 schema 请求
                )
                
                self.clients[subgraph_id] = client
                logger.info(f"创建子图客户端: {subgraph_id[:16]}...")
                
            except Exception as e:
                logger.error(f"创建客户端失败 ({subgraph_id[:16]}...): {e}")
                return None
        
        return self.clients[subgraph_id]
    
    def execute_query(
        self,
        subgraph_id: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """执行 GraphQL 查询"""
        client = self.get_or_create_client(subgraph_id)
        if not client:
            return None
        
        try:
            # 解析查询
            gql_query = gql(query)
            
            # 执行查询
            result = client.execute(
                gql_query,
                variable_values=variables
            )
            
            return result
            
        except TransportQueryError as e:
            # 传输层错误（网络、认证等）
            logger.error(f"查询传输错误: {e}")
            if "API key" in str(e):
                logger.error("API Key 可能无效或已过期")
            return None
            
        except Exception as e:
            # 其他错误
            logger.error(f"查询执行异常: {type(e).__name__}: {e}")
            return None
    
    def test_connection(self, subgraph_id: str) -> bool:
        """测试连接是否正常"""
        try:
            # 简单的测试查询
            test_query = """
                query TestConnection {
                    _meta {
                        block {
                            number
                        }
                    }
                }
            """
            
            result = self.execute_query(subgraph_id, test_query)
            return result is not None
            
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def get_subgraph_meta(self, subgraph_id: str) -> Optional[Dict[str, Any]]:
        """获取子图元数据"""
        try:
            meta_query = """
                query GetMeta {
                    _meta {
                        block {
                            number
                            hash
                            timestamp
                        }
                        deployment
                        hasIndexingErrors
                    }
                }
            """
            
            result = self.execute_query(subgraph_id, meta_query)
            if result:
                return result.get("_meta")
            
        except Exception as e:
            logger.error(f"获取元数据失败: {e}")
        
        return None
    
    def close_all(self):
        """关闭所有客户端连接"""
        for client in self.clients.values():
            try:
                if hasattr(client.transport, 'close'):
                    client.transport.close()
            except Exception as e:
                logger.debug(f"关闭客户端时出错: {e}")
        
        self.clients.clear()
        logger.info("已关闭所有 Graph 客户端连接")

# 全局客户端实例
graph_client = GraphClient()