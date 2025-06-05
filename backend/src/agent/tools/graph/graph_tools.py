# app/agent/tools/graph/graph_tools.py
"""
Graph 工具集 - 按照正确的流程设计
1. Agent 调用 tool
2. Tool 调用 analyzer 获得协议列表
3. Tool 为每个协议找 subgraph_id
4. Tool 把信息传给 query engine
5. Engine 调用 builder 和执行查询
"""

import logging
from typing import Dict, Any, Optional, List

from app.agent.tools.graph.protocol_analyzer import ProtocolAnalyzer, ProtocolAnalysisResult
from app.agent.tools.graph.graph_registry import SubgraphRegistry
from app.agent.tools.graph.subgraph_discovery import SubgraphDiscovery
from app.agent.tools.graph.query_engine import query_engine
from app.agent.tools.graph.graph_config import GRAPH_API_KEY, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# 创建全局实例
_analyzer = None
_registry = None
_discovery = None

def get_analyzer():
    """获取协议分析器实例"""
    global _analyzer
    if _analyzer is None:
        # 创建 LLM 适配器
        llm_client = _create_analyzer_llm_client()
        _analyzer = ProtocolAnalyzer(llm_client)
    return _analyzer

def _create_analyzer_llm_client():
    """为 ProtocolAnalyzer 创建 LLM 客户端"""
    try:
        from app.config import LLM_PROVIDER
        
        # 创建一个简单的适配器类
        class LLMClientAdapter:
            def __init__(self):
                self.llm = None
                self._initialize_llm()
            
            def _initialize_llm(self):
                """初始化 LLM - 使用与 GraphQLBuilder 相同的配置"""
                if LLM_PROVIDER == "qwen":
                    from langchain_community.chat_models.tongyi import ChatTongyi
                    from app.config import DASHSCOPE_API_KEY, MODEL_NAME
                    
                    self.llm = ChatTongyi(
                        model=MODEL_NAME,
                        dashscope_api_key=DASHSCOPE_API_KEY,
                        temperature=0.1,  # 稍微高一点，用于理解查询意图
                        max_tokens=500,   # 分析不需要太长的输出
                        top_p=0.8
                    )
                    
                elif LLM_PROVIDER == "anthropic":
                    from langchain_anthropic import ChatAnthropic
                    from app.config import ANTHROPIC_API_KEY, MODEL_NAME
                    
                    self.llm = ChatAnthropic(
                        model=MODEL_NAME,
                        temperature=0.1,
                        anthropic_api_key=ANTHROPIC_API_KEY,
                        max_tokens=500
                    )
                    
                elif LLM_PROVIDER == "openai":
                    from langchain_openai import ChatOpenAI
                    from app.config import OPENAI_API_KEY, MODEL_NAME
                    
                    self.llm = ChatOpenAI(
                        model=MODEL_NAME,
                        temperature=0.1,
                        openai_api_key=OPENAI_API_KEY,
                        max_tokens=500
                    )
                else:
                    logger.warning(f"不支持的 LLM_PROVIDER: {LLM_PROVIDER}")
                    self.llm = None
            
            def complete(self, prompt: str) -> str:
                """适配 ProtocolAnalyzer 期望的 complete 方法"""
                if self.llm is None:
                    raise ValueError("LLM 未初始化")
                
                try:
                    # 将 prompt 转换为消息格式
                    from langchain_core.messages import HumanMessage
                    response = self.llm.invoke([HumanMessage(content=prompt)])
                    return response.content
                except Exception as e:
                    logger.error(f"LLM 调用失败: {e}")
                    raise
        
        # 返回适配器实例
        return LLMClientAdapter()
        
    except Exception as e:
        logger.warning(f"创建 LLM 客户端失败: {e}，将使用规则分析")
        return None  # 返回 None，ProtocolAnalyzer 会 fallback 到规则分析
    
def get_registry():
    """获取子图注册表实例"""
    global _registry
    if _registry is None:
        _registry = SubgraphRegistry()
    return _registry

def get_discovery():
    """获取子图发现器实例"""
    global _discovery
    if _discovery is None:
        _discovery = SubgraphDiscovery()
    return _discovery

def smart_graph_query(query: str) -> str:
    """
    智能图查询 - 主要工具函数
    
    Args:
        query: 用户的自然语言查询
        
    Returns:
        str: 查询结果的字符串表示
    """
    try:
        # 检查 API Key
        if not GRAPH_API_KEY:
            return ERROR_MESSAGES.get("api_key_missing", "Graph 功能未配置，请设置 GRAPH_API_KEY 环境变量")
        
        logger.info(f"🚀 智能图查询: {query}")
        
        # Step 1: 调用 analyzer 获得协议列表
        analyzer = get_analyzer()
        analysis_result = analyzer.analyze_query(query)
        
        if not analysis_result.protocols:
            return f"❌ 未识别出任何协议\n建议：请在查询中明确提及协议名称，如 Uniswap、Aave、Compound 等"
        
        logger.info(f"📊 识别出 {len(analysis_result.protocols)} 个协议")
        
        # Step 2: 为每个协议找 subgraph_id
        subgraph_infos = []
        registry = get_registry()
        discovery = get_discovery()
        
        for protocol_info in analysis_result.protocols:
            logger.info(f"🔍 查找子图: {protocol_info.protocol} on {protocol_info.network}")
            
            # 先在注册表中查找
            subgraph_id = registry.find(
                protocol_info.protocol,
                protocol_info.network,
                protocol_info.version
            )
            
            source = "registry"
            
            # 如果注册表没有，尝试联网发现
            if not subgraph_id:
                logger.info(f"📡 注册表未找到，尝试联网发现...")
                subgraph_id = discovery.search_and_add_to_registry(
                    protocol_info.protocol,
                    protocol_info.network,
                    registry,
                    protocol_info.version
                )
                source = "discovery"
            
            if subgraph_id:
                subgraph_infos.append({
                    "protocol": protocol_info.protocol,
                    "network": protocol_info.network,
                    "version": protocol_info.version,
                    "subgraph_id": subgraph_id,
                    "confidence": protocol_info.confidence,
                    "source": source
                })
                logger.info(f"✅ 找到: {protocol_info.protocol} → {subgraph_id[:16]}...")
            else:
                logger.warning(f"❌ 未找到: {protocol_info.protocol} on {protocol_info.network}")
        
        if not subgraph_infos:
            return f"❌ 未找到任何可用的子图\n建议：请检查协议名称和网络是否正确"
        
        # Step 3: 把信息传给 query engine
        logger.info(f"🔧 传递 {len(subgraph_infos)} 个子图信息给 query engine")
        
        # 如果只有一个协议，直接查询
        if len(subgraph_infos) == 1:
            result = _execute_single_protocol_query(query, subgraph_infos[0], analysis_result)
        else:
            # 多个协议，执行对比查询
            result = _execute_multi_protocol_query(query, subgraph_infos, analysis_result)
        
        return result
        
    except Exception as e:
        logger.error(f"智能图查询失败: {e}", exc_info=True)
        return f"❌ 查询失败: {str(e)}\n建议：请检查查询语句或稍后重试"

def _execute_single_protocol_query(query: str, subgraph_info: Dict[str, Any], analysis_result: ProtocolAnalysisResult) -> str:
    """执行单协议查询"""
    
    # Step 4: 构建传给 engine 的上下文
    engine_context = {
        "user_query": query,
        "protocol": subgraph_info["protocol"],
        "network": subgraph_info["network"],
        "version": subgraph_info["version"],
        "subgraph_id": subgraph_info["subgraph_id"],
        "confidence": subgraph_info["confidence"],
        "source": subgraph_info["source"],
        "analysis_result": analysis_result
    }
    
    # Step 5: Query Engine 处理
    result = query_engine.execute_natural_language_query(engine_context)
    
    if not result["success"]:
        return f"❌ 查询执行失败: {result.get('error', '未知错误')}\n建议：请尝试使用更明确的查询语句"
    
    # Step 6: 格式化输出
    output = []
    output.append(f"✅ 查询成功")
    output.append(f"📊 协议: {subgraph_info['protocol'].title()}")
    output.append(f"🌐 网络: {subgraph_info['network'].title()}")
    output.append(f"🆔 子图 ID: {subgraph_info['subgraph_id'][:16]}...")
    output.append(f"🔧 来源: {subgraph_info['source']}")
    output.append(f"🎯 置信度: {subgraph_info['confidence']:.2f}")
    
    # 添加查询解释
    query_context = result.get("query_context", {})
    if query_context.get("explanation"):
        output.append(f"💡 解释: {query_context['explanation']}")
    
    output.append("")
    output.append("📈 查询结果:")
    output.append(result["formatted_result"])
    
    return "\n".join(output)

def _execute_multi_protocol_query(query: str, subgraph_infos: List[Dict[str, Any]], analysis_result: ProtocolAnalysisResult) -> str:
    """执行多协议查询"""
    
    output = []
    output.append(f"📊 多协议查询 (找到 {len(subgraph_infos)} 个协议)")
    output.append("=" * 50)
    
    for i, subgraph_info in enumerate(subgraph_infos, 1):
        output.append(f"\n{i}. {subgraph_info['protocol'].upper()} on {subgraph_info['network'].title()}")
        output.append("-" * 30)
        
        # 为每个协议执行查询
        engine_context = {
            "user_query": query,
            "protocol": subgraph_info["protocol"],
            "network": subgraph_info["network"],
            "version": subgraph_info["version"],
            "subgraph_id": subgraph_info["subgraph_id"],
            "confidence": subgraph_info["confidence"],
            "source": subgraph_info["source"],
            "analysis_result": analysis_result
        }
        
        result = query_engine.execute_natural_language_query(engine_context)
        
        if result["success"]:
            output.append(f"✅ 查询成功 (来源: {subgraph_info['source']})")
            output.append(result["formatted_result"])
        else:
            output.append(f"❌ 查询失败: {result.get('error', '未知错误')}")
    
    return "\n".join(output)

def graph_multi_query(queries: str) -> str:
    """
    批量查询 - 执行多个独立查询
    
    Args:
        queries: 用分号分隔的查询列表
        
    Returns:
        str: 所有查询结果的组合
    """
    try:
        # 检查 API Key
        if not GRAPH_API_KEY:
            return ERROR_MESSAGES.get("api_key_missing", "Graph 功能未配置，请设置 GRAPH_API_KEY 环境变量")
        
        # 分割查询
        query_list = [q.strip() for q in queries.split(';') if q.strip()]
        
        if len(query_list) > 5:
            return "❌ 最多支持 5 个查询，请减少查询数量"
        
        if not query_list:
            return "❌ 请提供至少一个查询"
        
        logger.info(f"🔍 批量查询 ({len(query_list)} 个)")
        
        results = []
        results.append(f"🔍 批量查询 ({len(query_list)} 个查询)")
        results.append("=" * 50)
        
        for i, query in enumerate(query_list, 1):
            results.append(f"\n📋 查询 {i}: {query}")
            results.append("-" * 30)
            
            # 执行单个查询
            result = smart_graph_query(query)
            results.append(result)
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"批量查询失败: {e}", exc_info=True)
        return f"❌ 批量查询失败: {str(e)}"

def graph_explain_query(query: str) -> str:
    """
    解释查询 - 显示完整的执行流程
    
    Args:
        query: 要解释的查询
        
    Returns:
        str: 查询执行过程的详细说明
    """
    try:
        # 检查 API Key
        if not GRAPH_API_KEY:
            return ERROR_MESSAGES.get("api_key_missing", "Graph 功能未配置，请设置 GRAPH_API_KEY 环境变量")
        
        logger.info(f"🔍 解释查询: {query}")
        
        explanation = []
        explanation.append(f"🔍 查询解释: {query}")
        explanation.append("=" * 50)
        
        # Step 1: 协议分析
        explanation.append("\n1️⃣ 协议分析阶段:")
        analyzer = get_analyzer()
        analysis_result = analyzer.analyze_query(query)
        
        if analysis_result.protocols:
            explanation.append(f"  ✅ 识别出 {len(analysis_result.protocols)} 个协议")
            for i, protocol in enumerate(analysis_result.protocols, 1):
                explanation.extend([
                    f"    {i}. {protocol.protocol}",
                    f"       网络: {protocol.network}",
                    f"       版本: {protocol.version or '未指定'}",
                    f"       置信度: {protocol.confidence:.2f}"
                ])
            explanation.append(f"  🎯 整体置信度: {analysis_result.overall_confidence:.2f}")
        else:
            explanation.append("  ❌ 未识别出任何协议")
            return "\n".join(explanation)
        
        # Step 2: 子图查找
        explanation.append("\n2️⃣ 子图查找阶段:")
        registry = get_registry()
        discovery = get_discovery()
        
        found_subgraphs = []
        
        for protocol in analysis_result.protocols:
            explanation.append(f"  🔍 查找 {protocol.protocol} on {protocol.network}:")
            
            # 注册表查找
            subgraph_id = registry.find(protocol.protocol, protocol.network, protocol.version)
            if subgraph_id:
                explanation.append(f"    ✅ 注册表找到: {subgraph_id[:16]}...")
                found_subgraphs.append(subgraph_id)
            else:
                explanation.append(f"    ❌ 注册表未找到")
                
                # 联网发现
                if discovery.endpoint:
                    explanation.append(f"    🌐 尝试联网发现...")
                    discovered_id = discovery.find(protocol.protocol, protocol.network, protocol.version)
                    if discovered_id:
                        explanation.append(f"    ✅ 发现新子图: {discovered_id[:16]}...")
                        found_subgraphs.append(discovered_id)
                    else:
                        explanation.append(f"    ❌ 联网发现失败")
                else:
                    explanation.append(f"    ⚠️ 无法联网发现 (未设置 API Key)")
        
        # Step 3: 查询执行计划
        explanation.append("\n3️⃣ 查询执行计划:")
        if found_subgraphs:
            explanation.append(f"  📋 将对 {len(found_subgraphs)} 个子图执行查询")
            explanation.append(f"  🔧 Query Engine 将调用 GraphQL Builder")
            explanation.append(f"  🏗️ GraphQL Builder 将使用 LLM 生成查询")
            explanation.append(f"  🚀 然后执行生成的 GraphQL 查询")
        else:
            explanation.append(f"  ❌ 没有可用的子图，无法执行查询")
        
        # Step 4: 系统状态
        explanation.append("\n4️⃣ 系统状态:")
        stats = registry.get_statistics()
        explanation.extend([
            f"  📊 已缓存子图: {stats['total_records']} 个",
            f"  🌐 支持协议: {', '.join(stats['protocols'].keys()) if stats['protocols'] else '无'}",
            f"  🔗 支持网络: {', '.join(stats['networks'].keys()) if stats['networks'] else '无'}",
            f"  🔑 API Key: {'✅ 已配置' if GRAPH_API_KEY else '❌ 未配置'}",
            f"  🤖 LLM Analyzer: {'✅ 可用' if analyzer.llm_client else '❌ 使用规则分析'}",
            f"  🌐 Discovery: {'✅ 可用' if discovery.endpoint else '❌ 不可用'}"
        ])
        
        return "\n".join(explanation)
        
    except Exception as e:
        logger.error(f"解释查询失败: {e}", exc_info=True)
        return f"❌ 解释查询失败: {str(e)}"

def get_registry_stats() -> str:
    """获取注册表统计信息"""
    try:
        registry = get_registry()
        stats = registry.get_statistics()
        
        output = []
        output.append("📊 Graph 系统统计")
        output.append("=" * 30)
        output.append(f"📈 总子图数: {stats['total_records']}")
        output.append(f"🔑 API Key: {'✅ 已配置' if GRAPH_API_KEY else '❌ 未配置'}")
        
        if stats['protocols']:
            output.append(f"\n🔧 支持协议:")
            for protocol, count in stats['protocols'].items():
                output.append(f"   • {protocol}: {count} 个子图")
        
        if stats['networks']:
            output.append(f"\n🌐 支持网络:")
            for network, count in stats['networks'].items():
                output.append(f"   • {network}: {count} 个子图")
        
        if stats.get('most_used'):
            output.append(f"\n🏆 最常用子图:")
            for item in stats['most_used'][:3]:
                output.append(f"   • {item['key']}: {item['query_count']} 次查询")
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        return f"❌ 获取统计信息失败: {str(e)}"

def add_known_subgraph(protocol: str, network: str, subgraph_id: str, name: str = "") -> str:
    """手动添加已知子图"""
    try:
        registry = get_registry()
        
        if not name:
            name = f"{protocol.title()} on {network.title()}"
        
        success = registry.add(
            protocol=protocol,
            network=network,
            subgraph_id=subgraph_id,
            name=name
        )
        
        if success:
            return f"✅ 成功添加子图: {protocol}-{network} → {subgraph_id}"
        else:
            return f"❌ 添加子图失败: {protocol}-{network}"
            
    except Exception as e:
        logger.error(f"添加子图失败: {e}", exc_info=True)
        return f"❌ 添加子图失败: {str(e)}"

# 导出的工具函数 - 供 agent 调用
__all__ = [
    'smart_graph_query',       # 主要的智能查询工具
    'graph_multi_query',       # 批量查询工具  
    'graph_explain_query',     # 查询解释工具
    'get_registry_stats',      # 获取统计信息
    'add_known_subgraph'       # 手动添加子图
]