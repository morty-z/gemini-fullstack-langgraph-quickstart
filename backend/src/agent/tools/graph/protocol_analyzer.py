# app/agent/tools/graph/protocol_analyzer.py
"""
Protocol Analyzer - 支持多协议
提取查找 subgraph 的关键信息，可能包含多个协议
"""

import logging
import json
import re
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProtocolInfo:
    """单个协议信息"""
    protocol: str           # "uniswap"
    network: str           # "ethereum"
    version: Optional[str]  # "v3"
    confidence: float       # 0.95

@dataclass
class ProtocolAnalysisResult:
    """协议分析结果 - 支持多协议"""
    protocols: List[ProtocolInfo]  # 可能包含多个协议
    raw_query: str                 # 原始用户查询
    overall_confidence: float      # 整体置信度

class ProtocolAnalyzer:
    """协议分析器 - 支持多协议识别"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
        # 协议别名映射
        self.protocol_aliases = {
            "uni": "uniswap",
            "uniswap": "uniswap",
            "univ2": "uniswap",
            "univ3": "uniswap",
            "aave": "aave",
            "compound": "compound",
            "comp": "compound",
            "curve": "curve",
            "crv": "curve",
            "sushi": "sushiswap",
            "sushiswap": "sushiswap",
            "balancer": "balancer",
            "bal": "balancer",
            "pancake": "pancakeswap",
            "pancakeswap": "pancakeswap",
            "cake": "pancakeswap",
            "gmx": "gmx",
            "lido": "lido",
            "maker": "maker",
            "mkr": "maker",
            "synthetix": "synthetix",
            "snx": "synthetix",
            "yearn": "yearn",
            "yfi": "yearn"
        }
        
        # 网络别名映射
        self.network_aliases = {
            "ethereum": "ethereum",
            "eth": "ethereum", 
            "mainnet": "ethereum",
            "以太坊": "ethereum",
            "polygon": "polygon",
            "matic": "polygon",
            "马蹄": "polygon",
            "arbitrum": "arbitrum",
            "arb": "arbitrum",
            "optimism": "optimism",
            "op": "optimism",
            "bsc": "bsc",
            "binance": "bsc",
            "bnb": "bsc",
            "avalanche": "avalanche",
            "avax": "avalanche",
            "fantom": "fantom",
            "ftm": "fantom"
        }
    
    def analyze_query(self, user_query: str) -> ProtocolAnalysisResult:
        """
        分析用户查询，提取所有涉及的协议信息
        """
        logger.info(f"🔍 分析查询: {user_query}")
        
        if self.llm_client:
            try:
                return self._llm_analyze_query(user_query)
            except Exception as e:
                logger.error(f"LLM 分析失败: {e}")
                return self._rule_based_analyze(user_query)
        else:
            return self._rule_based_analyze(user_query)
    
    def _llm_analyze_query(self, user_query: str) -> ProtocolAnalysisResult:
        """使用 LLM 分析查询"""
        
        prompt = f"""
分析以下用户查询，提取所有涉及的 DeFi 协议信息。

用户查询: "{user_query}"

请返回 JSON 格式：
```json
{{
  "protocols": [
    {{
      "protocol": "标准化协议名(如uniswap,aave,compound)",
      "network": "网络名(ethereum,polygon,arbitrum等)",
      "version": "版本号(如v2,v3,无明确版本则为null)",
      "confidence": 0.95
    }}
  ],
  "overall_confidence": 0.9
}}
```

**重要规则：**
1. 协议名必须标准化：uniswap, aave, compound, curve, sushiswap, balancer 等
2. 网络名标准化：ethereum, polygon, arbitrum, optimism, bsc, avalanche
3. 如果查询涉及多个协议，都要列出
4. 如果没有明确指定网络，默认为 ethereum
5. 只有明确提到版本才填写 version 字段

**示例：**
- "比较 Uniswap 和 SushiSwap 的流动性" → 两个协议
- "Aave V3 在 Polygon 上的数据" → 一个协议，有版本和网络
- "所有 DEX 协议的数据" → 可能识别出多个 DEX 协议

请仔细分析并返回准确结果。
"""
        
        response = self.llm_client.complete(prompt)
        result = self._parse_llm_response(response)
        
        return self._build_analysis_result(result, user_query)
    
    def _parse_llm_response(self, response: str) -> dict:
        """解析 LLM 响应"""
        try:
            # 提取 JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 直接解析
            if response.strip().startswith('{'):
                return json.loads(response.strip())
            
            logger.warning("无法解析 LLM JSON 响应")
            return {}
            
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            return {}
    
    def _rule_based_analyze(self, user_query: str) -> ProtocolAnalysisResult:
        """基于规则的分析"""
        query_lower = user_query.lower()
        
        # 识别所有协议
        found_protocols = []
        for alias, standard_name in self.protocol_aliases.items():
            if alias in query_lower:
                # 避免重复添加同一协议
                if not any(p.protocol == standard_name for p in found_protocols):
                    found_protocols.append(ProtocolInfo(
                        protocol=standard_name,
                        network="ethereum",  # 默认网络
                        version=None,
                        confidence=0.8
                    ))
        
        # 识别网络
        detected_network = "ethereum"  # 默认
        for alias, standard_network in self.network_aliases.items():
            if alias in query_lower:
                detected_network = standard_network
                break
        
        # 更新所有协议的网络
        for protocol_info in found_protocols:
            protocol_info.network = detected_network
        
        # 识别版本
        version_match = re.search(r'v(\d+)', query_lower)
        detected_version = None
        if version_match:
            detected_version = f"v{version_match.group(1)}"
            
            # 更新所有协议的版本
            for protocol_info in found_protocols:
                protocol_info.version = detected_version
        
        # 如果没有找到任何协议，尝试通用关键词识别
        if not found_protocols:
            # DEX 相关关键词
            if any(keyword in query_lower for keyword in ["dex", "swap", "pool", "liquidity", "amm"]):
                found_protocols.extend([
                    ProtocolInfo("uniswap", detected_network, None, 0.5),
                    ProtocolInfo("sushiswap", detected_network, None, 0.5)
                ])
            
            # Lending 相关关键词  
            elif any(keyword in query_lower for keyword in ["lend", "borrow", "deposit", "供应", "借贷"]):
                found_protocols.extend([
                    ProtocolInfo("aave", detected_network, None, 0.5),
                    ProtocolInfo("compound", detected_network, None, 0.5)
                ])
        
        overall_confidence = sum(p.confidence for p in found_protocols) / len(found_protocols) if found_protocols else 0.0
        
        return ProtocolAnalysisResult(
            protocols=found_protocols,
            raw_query=user_query,
            overall_confidence=overall_confidence
        )
    
    def _build_analysis_result(self, llm_result: dict, user_query: str) -> ProtocolAnalysisResult:
        """构建分析结果"""
        
        protocols = []
        
        for protocol_data in llm_result.get("protocols", []):
            # 标准化协议名
            protocol_name = protocol_data.get("protocol", "").lower()
            protocol_name = self.protocol_aliases.get(protocol_name, protocol_name)
            
            # 标准化网络名
            network_name = protocol_data.get("network", "ethereum").lower()
            network_name = self.network_aliases.get(network_name, network_name)
            
            if protocol_name:  # 只添加有效的协议
                protocols.append(ProtocolInfo(
                    protocol=protocol_name,
                    network=network_name,
                    version=protocol_data.get("version"),
                    confidence=protocol_data.get("confidence", 0.5)
                ))
        
        overall_confidence = llm_result.get("overall_confidence", 0.5)
        
        return ProtocolAnalysisResult(
            protocols=protocols,
            raw_query=user_query,
            overall_confidence=overall_confidence
        )
    
    def extract_single_protocol(self, user_query: str) -> Optional[ProtocolInfo]:
        """
        便捷方法：提取单个协议（取置信度最高的）
        用于简单场景
        """
        result = self.analyze_query(user_query)
        
        if result.protocols:
            # 返回置信度最高的协议
            return max(result.protocols, key=lambda p: p.confidence)
        
        return None