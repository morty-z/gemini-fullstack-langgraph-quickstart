# app/agent/tools/graph/query_engine.py
"""
查询引擎 - 简化版，只负责执行 GraphQL 查询
不再处理协议分析，专注于查询执行
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.agent.tools.graph.graph_client import graph_client
from app.agent.tools.graph.graph_config import CACHE_SETTINGS

logger = logging.getLogger(__name__)

class QueryEngine:
    """查询引擎 - 接收上下文，调用 GraphQL Builder，执行查询"""
    
    def __init__(self):
        """初始化查询引擎"""
        self.cache = {}
        self.cache_ttl = CACHE_SETTINGS["ttl"]
    
    def execute_natural_language_query(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行自然语言查询 - 新的主要方法
        
        Args:
            context: 包含以下信息的上下文字典
                - user_query: 用户查询
                - protocol: 协议名
                - network: 网络名  
                - version: 版本号
                - subgraph_id: 子图ID
                - confidence: 置信度
                - source: 来源
                - analysis_result: 分析结果
                
        Returns:
            包含查询结果的字典
        """
        try:
            logger.info(f"🔧 Query Engine 接收上下文: {context['protocol']} on {context['network']}")
            
            # Step 5: 调用 GraphQL Builder
            from app.agent.tools.graph.graphql_builder import graphql_builder
            
            # 构建协议上下文给 GraphQL Builder
            protocol_context = {
                "name": f"{context['protocol'].title()} Protocol",
                "network": context["network"],
                "description": f"{context['protocol'].title()} Protocol on {context['network'].title()}",
                "entities": [],  # GraphQL Builder 会自己推测
                "categories": ["DeFi"]
            }
            
            logger.info(f"🏗️ 调用 GraphQL Builder...")
            query_result = graphql_builder.build_query(
                natural_language_query=context["user_query"],
                protocol_context=protocol_context
            )
            
            if not query_result or not query_result.get("query"):
                return {
                    "success": False,
                    "error": "GraphQL Builder 构建查询失败",
                    "formatted_result": ""
                }
            
            logger.info(f"✅ GraphQL 构建成功")
            logger.info(f"📄 查询: {query_result['query']}")
            logger.info(f"📊 变量: {query_result.get('variables', {})}")
            
            # Step 6: 执行 GraphQL 查询
            result = self.execute_query(
                subgraph_id=context["subgraph_id"],
                query=query_result["query"],
                variables=query_result.get("variables", {})
            )
            
            if not result:
                return {
                    "success": False,
                    "error": "GraphQL 查询执行失败",
                    "formatted_result": ""
                }
            
            # 格式化结果
            formatted_result = graphql_builder.format_result(
                result,
                {
                    "explanation": query_result.get("explanation", ""),
                    "original_query": context["user_query"]
                }
            )
            
            return {
                "success": True,
                "data": result,
                "formatted_result": formatted_result,
                "query_context": {
                    "explanation": query_result.get("explanation", ""),
                    "graphql_query": query_result["query"],
                    "variables": query_result.get("variables", {}),
                    "subgraph_id": context["subgraph_id"],
                    "protocol": context["protocol"],
                    "network": context["network"]
                }
            }
            
        except Exception as e:
            logger.error(f"执行自然语言查询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "formatted_result": f"❌ 查询失败: {str(e)}"
            }
    
    def execute_query(
        self,
        subgraph_id: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        执行 GraphQL 查询
        
        Args:
            subgraph_id: 子图 ID
            query: GraphQL 查询字符串
            variables: 查询变量
            use_cache: 是否使用缓存
            
        Returns:
            查询结果
        """
        # 检查缓存
        if use_cache and CACHE_SETTINGS["enabled"]:
            cache_key = f"{subgraph_id}:{hash(query)}:{hash(str(variables))}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                    logger.debug("使用缓存数据")
                    return cached_data
        
        # 记录查询详情
        logger.info(f"执行 GraphQL 查询到 Subgraph: {subgraph_id}")
        
        # 执行查询
        result = graph_client.execute_query(
            subgraph_id=subgraph_id,
            query=query,
            variables=variables
        )
        
        # 缓存结果
        if result and use_cache and CACHE_SETTINGS["enabled"]:
            self.cache[cache_key] = (result, datetime.now())
            
            # 清理过期缓存
            self._cleanup_cache()
        
        return result
    
    def execute_with_context(
        self,
        subgraph_id: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行查询并返回包含上下文的结果
        
        Args:
            subgraph_id: 子图 ID
            query: GraphQL 查询字符串
            variables: 查询变量
            context: 额外上下文信息
            
        Returns:
            包含查询结果和上下文的字典
        """
        try:
            logger.info("="*60)
            logger.info("执行 GraphQL 查询:")
            logger.info(f"Subgraph ID: {subgraph_id}")
            logger.info(f"GraphQL 查询:\n{query}")
            logger.info(f"变量: {variables}")
            if context:
                logger.info(f"上下文: {context}")
            logger.info("="*60)
            
            result = self.execute_query(subgraph_id, query, variables)
            
            if not result:
                return {
                    "success": False,
                    "error": "查询执行失败",
                    "data": None,
                    "context": context or {}
                }
            
            return {
                "success": True,
                "data": result,
                "context": {
                    **(context or {}),
                    "subgraph_id": subgraph_id,
                    "query": query,
                    "variables": variables,
                    "executed_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"执行查询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "context": context or {}
            }
    
    def test_connection(self, subgraph_id: str) -> bool:
        """
        测试与子图的连接
        
        Args:
            subgraph_id: 子图 ID
            
        Returns:
            是否连接成功
        """
        test_query = """
        query TestConnection {
            _meta {
                block {
                    number
                    timestamp
                }
                deployment
                hasIndexingErrors
            }
        }
        """
        
        try:
            result = self.execute_query(
                subgraph_id=subgraph_id,
                query=test_query,
                use_cache=False
            )
            
            return result is not None and "_meta" in result
            
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def get_subgraph_metadata(self, subgraph_id: str) -> Optional[Dict[str, Any]]:
        """
        获取子图元数据
        
        Args:
            subgraph_id: 子图 ID
            
        Returns:
            子图元数据
        """
        meta_query = """
        query GetMetadata {
            _meta {
                block {
                    number
                    timestamp
                    hash
                }
                deployment
                hasIndexingErrors
            }
        }
        """
        
        try:
            result = self.execute_query(
                subgraph_id=subgraph_id,
                query=meta_query,
                use_cache=False
            )
            
            if result and "_meta" in result:
                meta = result["_meta"]
                
                # 格式化时间戳
                if meta.get("block", {}).get("timestamp"):
                    timestamp = int(meta["block"]["timestamp"])
                    meta["block"]["formatted_time"] = datetime.fromtimestamp(timestamp).isoformat()
                
                return meta
            
            return None
            
        except Exception as e:
            logger.error(f"获取元数据失败: {e}")
            return None
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, time) in self.cache.items()
            if now - time > timedelta(seconds=self.cache_ttl)
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存")
    
    def clear_cache(self):
        """清空所有缓存"""
        self.cache.clear()
        logger.info("已清空查询缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.cache),
            "cache_enabled": CACHE_SETTINGS["enabled"],
            "cache_ttl": self.cache_ttl
        }

# 全局查询引擎实例
query_engine = QueryEngine()