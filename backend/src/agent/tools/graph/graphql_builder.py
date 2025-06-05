# app/agent/tools/graph/graphql_builder.py
"""
GraphQL 查询构建器 - 使用 LLM 直接从自然语言生成 GraphQL
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List
from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.tools.graph.graph_config import (
    GRAPH_API_KEY, FORMAT_SETTINGS,
    format_number, format_address
)
from app.config import LLM_PROVIDER, TEMPERATURE

logger = logging.getLogger(__name__)

class GraphQLBuilder:
    """使用 LLM 构建 GraphQL 查询"""
    
    def __init__(self):
        """
        初始化 GraphQL 构建器
        使用系统配置的 LLM，但不带 tools
        """
        # 根据配置创建对应的 LLM 实例
        if LLM_PROVIDER == "qwen":
            from langchain_community.chat_models.tongyi import ChatTongyi
            from app.config import DASHSCOPE_API_KEY, MODEL_NAME
            
            self.llm = ChatTongyi(
                model=MODEL_NAME,
                dashscope_api_key=DASHSCOPE_API_KEY,
                temperature=0,  # GraphQL 生成需要稳定输出
                max_tokens=1000,
                top_p=0.8
            )
            
        elif LLM_PROVIDER == "anthropic":
            from langchain_anthropic import ChatAnthropic
            from app.config import ANTHROPIC_API_KEY, MODEL_NAME
            
            self.llm = ChatAnthropic(
                model=MODEL_NAME,
                temperature=0,
                anthropic_api_key=ANTHROPIC_API_KEY,
                max_tokens=1000
            )
            
        elif LLM_PROVIDER == "openai":
            from langchain_openai import ChatOpenAI
            from app.config import OPENAI_API_KEY, MODEL_NAME
            
            self.llm = ChatOpenAI(
                model=MODEL_NAME,
                temperature=0,
                openai_api_key=OPENAI_API_KEY,
                max_tokens=1000
            )
        else:
            raise ValueError(f"不支持的 LLM_PROVIDER: {LLM_PROVIDER}")
        
        logger.info(f"GraphQL Builder 使用 {LLM_PROVIDER} LLM (无 tools)")
        
        # 常见实体和字段映射
        
        # 常见实体和字段映射
        self.common_entities = {
            "pools": {
                "description": "流动性池/交易对",
                "common_fields": [
                    "id", "token0 { symbol name decimals }", 
                    "token1 { symbol name decimals }",
                    "totalValueLockedUSD", "volumeUSD", "feeTier",
                    "liquidity", "sqrtPrice", "tick"
                ]
            },
            "tokens": {
                "description": "代币信息",
                "common_fields": [
                    "id", "symbol", "name", "decimals",
                    "totalSupply", "volume", "volumeUSD",
                    "totalValueLocked", "totalValueLockedUSD"
                ]
            },
            "positions": {
                "description": "用户仓位",
                "common_fields": [
                    "id", "owner", "pool { id }",
                    "token0 { symbol }", "token1 { symbol }",
                    "liquidity", "depositedToken0", "depositedToken1",
                    "withdrawnToken0", "withdrawnToken1",
                    "collectedFeesToken0", "collectedFeesToken1"
                ]
            },
            "swaps": {
                "description": "交易记录",
                "common_fields": [
                    "id", "transaction { id }", "timestamp",
                    "pool { id }", "origin", "amount0", "amount1",
                    "amountUSD", "sqrtPriceX96", "tick"
                ]
            },
            "markets": {
                "description": "借贷市场",
                "common_fields": [
                    "id", "name", "inputToken { symbol name }",
                    "totalValueLockedUSD", "totalBorrowBalanceUSD",
                    "totalDepositBalanceUSD", "inputTokenBalance",
                    "rates { id rate side type }"
                ]
            }
        }
    
    def build_query(
        self,
        natural_language_query: str,
        protocol_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从自然语言构建 GraphQL 查询
        
        Args:
            natural_language_query: 用户的自然语言查询
            protocol_context: 协议上下文信息（名称、网络、可用实体等）
            
        Returns:
            包含 GraphQL 查询和变量的字典
        """
        try:
            # 自动获取协议相关的示例
            examples = self._get_protocol_examples(protocol_context.get('name', ''))
            
            # 构建系统提示
            system_prompt = self._build_system_prompt(protocol_context)
            
            # 构建用户提示
            user_prompt = self._build_user_prompt(
                natural_language_query,
                protocol_context,
                examples
            )
            
            # 调用 LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # 解析响应
            result = self._parse_llm_response(response.content)
            
            # 验证和修复查询
            validated_result = self._validate_and_fix_query(result, protocol_context)
            
            return validated_result
            
        except Exception as e:
            logger.error(f"构建 GraphQL 查询失败: {e}")
            # 返回一个默认查询
            return self._get_fallback_query(natural_language_query, protocol_context)
    
    def _build_system_prompt(self, protocol_context: Dict[str, Any]) -> str:
        """构建系统提示"""
        entities_info = "\n".join([
            f"- {entity}: {info['description']}"
            for entity, info in self.common_entities.items()
        ])
        
        protocol_name = protocol_context.get('name', 'Unknown')
        
        return f"""你是一个 GraphQL 查询构建专家，专门将自然语言查询转换为 The Graph Protocol 的 GraphQL 查询。

协议信息：
- 名称: {protocol_name}
- 网络: {protocol_context.get('network', 'ethereum')}
- 描述: {protocol_context.get('description', '')}

常见实体类型：
{entities_info}

重要的 GraphQL 字段映射规则：
1. 对于 DEX 协议的 pools：
   - 使用 token0_ 和 token1_ 前缀来过滤代币
   - 不要使用 token0Address 或 token1Address
   
2. 查询代币对时要考虑双向：
   - 使用 or 条件匹配两个方向


3. 关于 ETH 和 WETH：
   - 在 Uniswap V3 中，ETH 必须包装成 WETH（Wrapped ETH）才能交易
   - 如果用户查询 "ETH"，使用 symbol_contains_nocase: "ETH"，这样可以同时匹配 "ETH" 和 "WETH"

4. 处理多个费率池：
   - Uniswap V3 同一个代币对可能有多个不同费率的池子（100=0.01%、500=0.05%、3000=0.3%、10000=1%）
   - 默认应该返回所有费率的池子，不要限制为 first: 1
   - 使用合适的 first 值（通常 5-10）来获取所有相关池子
   - 可以按 feeTier 或 totalValueLockedUSD 排序

5. 常用字段：
   - id: 池子地址（必须小写）
   - token0/token1: 代币信息（包含 symbol, name, id, decimals）
   - feeTier: 费率（100=0.01%, 500=0.05%, 3000=0.3%, 10000=1%）
   - totalValueLockedUSD: TVL
   - volumeUSD: 历史总交易量
   - liquidity: 流动性
   - sqrtPrice: 价格的平方根
   - tick: 当前价格 tick

6. 查询策略：
   - 查询 TVL：返回所有费率的池子，按 totalValueLockedUSD 降序排序
   - 查询所有池子：按 feeTier 升序排序，展示从低费率到高费率
   - 查询特定费率：在 where 条件中添加 feeTier 过滤

7. 排序和限制：
   - orderBy: totalValueLockedUSD 或 feeTier
   - orderDirection: desc（降序）或 asc（升序）
   - first: 对于同一交易对查询，建议 5-10；对于全局查询，可以更多

输出格式要求：
返回一个 JSON 对象，包含：
{{
    "query": "GraphQL 查询字符串",
    "variables": {{变量对象}},
    "explanation": "简短解释查询的作用"
}}"""
    
    def _build_user_prompt(
        self,
        query: str,
        protocol_context: Dict[str, Any],
        examples: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """构建用户提示"""
        prompt_parts = []
        
        # 添加示例（如果有）
        if examples:
            prompt_parts.append("参考示例：")
            for ex in examples[:3]:  # 最多3个示例
                prompt_parts.append(f"\n自然语言: {ex['natural']}")
                prompt_parts.append(f"GraphQL: {ex['graphql']}")
            prompt_parts.append("")
        
        # 添加可用实体信息（如果有）
        if protocol_context.get('entities'):
            prompt_parts.append(f"该协议支持的实体: {', '.join(protocol_context['entities'])}")
            prompt_parts.append("")
        
        # 添加用户查询
        prompt_parts.append(f"请将以下查询转换为 GraphQL：")
        prompt_parts.append(f'"{query}"')
        prompt_parts.append("")
        prompt_parts.append("重要提示：")
        prompt_parts.append("1. 如果查询中包含 'ETH'，请保持为 'ETH'，不要自动转换为 'WETH'")
        prompt_parts.append("2. 如果查询涉及代币对（如 USDC/ETH），需要考虑双向匹配")

        
        return "\n".join(prompt_parts)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            # 尝试直接解析 JSON
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # 尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            
            # 如果无法解析，尝试提取代码块
            code_match = re.search(r'```(?:graphql|json)?\n([\s\S]*?)\n```', response)
            if code_match:
                content = code_match.group(1)
                if content.strip().startswith('{'):
                    return json.loads(content)
                else:
                    # 假设是纯 GraphQL
                    return {
                        "query": content,
                        "variables": {},
                        "explanation": "Extracted from code block"
                    }
            
            # 最后尝试：假设整个响应是 GraphQL
            if 'query' in response.lower() and '{' in response:
                return {
                    "query": response,
                    "variables": {},
                    "explanation": "Direct GraphQL extraction"
                }
            
            raise ValueError("无法解析 LLM 响应")
            
        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            logger.debug(f"原始响应: {response}")
            raise
    
    def _validate_and_fix_query(
        self,
        result: Dict[str, Any],
        protocol_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证并修复 GraphQL 查询"""
        query = result.get("query", "")
        variables = result.get("variables", {})
        
        # 基本验证
        if not query or not isinstance(query, str):
            raise ValueError("无效的查询格式")
        
        # 确保查询包含必要的结构
        if not re.search(r'query\s+\w*\s*(?:\([^)]*\))?\s*\{', query):
            # 尝试添加查询包装
            query = f"query GeneratedQuery {query}"
        
        # 确保有基本的变量定义
        if "$first" in query and "first" not in variables:
            variables["first"] = 10
        
        # 清理查询（移除多余的空格和换行）
        query = re.sub(r'\s+', ' ', query).strip()
        
        return {
            "query": query,
            "variables": variables,
            "explanation": result.get("explanation", "")
        }
    
    def _get_fallback_query(
        self,
        query: str,
        protocol_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取降级查询 - 更智能的 fallback 逻辑"""
        query_lower = query.lower()
        
        # 尝试提取代币符号
        token_symbols = []
        common_tokens = ["eth", "weth", "usdc", "usdt", "dai", "wbtc", "uni", "link", "aave", "matic"]
        for token in common_tokens:
            if token in query_lower:
                # 保持原样，不转换
                token_symbols.append(token.upper())
        
        # 根据关键词和提取的信息返回更精确的查询
        if any(word in query_lower for word in ["池", "pool", "交易对", "pair", "流动性"]):
            # 如果找到了两个代币，查询所有相关池子
            if len(token_symbols) >= 2:
                return {
                    "query": """
                        query SpecificPools($token0: String!, $token1: String!, $first: Int!) {
                            pools(
                                where: {
                                    or: [
                                        {token0_: {symbol_contains_nocase: $token0}, token1_: {symbol_contains_nocase: $token1}},
                                        {token0_: {symbol_contains_nocase: $token1}, token1_: {symbol_contains_nocase: $token0}}
                                    ]
                                },
                                first: $first,
                                orderBy: totalValueLockedUSD,
                                orderDirection: desc
                            ) {
                                id
                                token0 { symbol name decimals }
                                token1 { symbol name decimals }
                                feeTier
                                totalValueLockedUSD
                                volumeUSD
                                liquidity
                            }
                        }
                    """,
                    "variables": {
                        "token0": token_symbols[0],
                        "token1": token_symbols[1],
                        "first": 10  # 获取所有费率的池子
                    },
                    "explanation": f"Fallback: 查询所有 {token_symbols[0]}/{token_symbols[1]} 池子（包括所有费率）"
                }
            
            # 否则返回通用的池子查询
            return {
                "query": """
                    query FallbackPools($first: Int!) {
                        pools(first: $first, orderBy: totalValueLockedUSD, orderDirection: desc) {
                            id
                            token0 { symbol name }
                            token1 { symbol name }
                            feeTier
                            totalValueLockedUSD
                            volumeUSD
                        }
                    }
                """,
                "variables": {"first": 10},
                "explanation": "Fallback: 返回 TVL 最高的池子"
            }
        
        elif any(word in query_lower for word in ["代币", "token", "币"]) and token_symbols:
            # 如果提到了特定代币
            return {
                "query": """
                    query FallbackToken($symbol: String!) {
                        tokens(
                            where: {symbol_contains_nocase: $symbol},
                            first: 1
                        ) {
                            id
                            symbol
                            name
                            decimals
                            totalValueLockedUSD
                            volumeUSD
                        }
                    }
                """,
                "variables": {"symbol": token_symbols[0]},
                "explanation": f"Fallback: 查询 {token_symbols[0]} 代币信息"
            }
        
        elif any(word in query_lower for word in ["代币", "token", "币"]):
            return {
                "query": """
                    query FallbackTokens($first: Int!) {
                        tokens(first: $first, orderBy: totalValueLockedUSD, orderDirection: desc) {
                            id
                            symbol
                            name
                            totalValueLockedUSD
                            volumeUSD
                        }
                    }
                """,
                "variables": {"first": 10},
                "explanation": "Fallback: 返回 TVL 最高的代币"
            }
        
        # 默认查询 - 协议元数据
        return {
            "query": """
                query FallbackMeta {
                    _meta {
                        block { number timestamp }
                        deployment
                        hasIndexingErrors
                    }
                }
            """,
            "variables": {},
            "explanation": "Fallback: 返回子图元数据"
        }
    
    def format_result(self, result: Dict[str, Any], query_context: Dict[str, Any]) -> str:
        """
        格式化查询结果为用户友好的输出
        
        Args:
            result: GraphQL 查询结果
            query_context: 查询上下文（包含原始查询、解释等）
            
        Returns:
            格式化的字符串输出
        """
        if not result:
            return "❌ 未获取到数据"
        
        output = []
        explanation = query_context.get("explanation", "")
        if explanation:
            output.append(f"📊 {explanation}")
            output.append("")
        
        # 识别返回的数据类型并格式化
        for key, value in result.items():
            if key == "_meta":
                continue
                
            if isinstance(value, list) and value:
                # 处理列表数据
                output.append(f"找到 {len(value)} 个 {key}:")
                
                # 特殊处理：如果是同一交易对的多个池子，先总结
                if key == "pools" and len(value) > 1:
                    # 检查是否是同一交易对
                    first_pool = value[0]
                    token0_symbol = first_pool.get("token0", {}).get("symbol", "")
                    token1_symbol = first_pool.get("token1", {}).get("symbol", "")
                    
                    same_pair = all(
                        (p.get("token0", {}).get("symbol", "") == token0_symbol and 
                         p.get("token1", {}).get("symbol", "") == token1_symbol) or
                        (p.get("token0", {}).get("symbol", "") == token1_symbol and 
                         p.get("token1", {}).get("symbol", "") == token0_symbol)
                        for p in value
                    )
                    
                    if same_pair:
                        # 计算总 TVL
                        total_tvl = sum(float(p.get("totalValueLockedUSD", 0)) for p in value)
                        output.append(f"\n💰 **{token0_symbol}/{token1_symbol} 总 TVL: ${format_number(total_tvl)}**")
                        output.append("\n按费率分布：")
                
                output.append("")
                
                for i, item in enumerate(value[:10], 1):  # 最多显示10个
                    output.extend(self._format_item(key, item, i))
                    if i < min(10, len(value)):
                        output.append("")
                        
            elif isinstance(value, dict):
                # 处理单个对象
                output.extend(self._format_item(key, value))
        
        return "\n".join(output)
    
    def _format_item(self, entity_type: str, item: Dict[str, Any], index: Optional[int] = None) -> List[str]:
        """格式化单个数据项"""
        lines = []
        
        if index:
            prefix = f"{index}. "
        else:
            prefix = ""
        
        # 根据实体类型格式化
        if entity_type in ["pools", "pool"]:
            token0 = item.get("token0", {})
            token1 = item.get("token1", {})
            lines.append(f"{prefix}**{token0.get('symbol', '?')}/{token1.get('symbol', '?')} 池**")
            
            # 显示池子地址
            if "id" in item:
                lines.append(f"   🏠 池子地址: {item['id']}")
            
            if "totalValueLockedUSD" in item:
                tvl = float(item["totalValueLockedUSD"])
                lines.append(f"   💰 TVL: ${format_number(tvl)}")
            
            if "volumeUSD" in item:
                volume = float(item["volumeUSD"])
                lines.append(f"   📈 交易量: ${format_number(volume)}")
            
            if "feeTier" in item:
                fee = float(item["feeTier"]) / 10000
                lines.append(f"   💸 手续费: {fee}%")
            
            if "liquidity" in item:
                lines.append(f"   💧 流动性: {format_number(float(item['liquidity']))}")
                
        elif entity_type in ["tokens", "token"]:
            lines.append(f"{prefix}**{item.get('symbol', '?')} ({item.get('name', '')})**")
            
            if "totalValueLockedUSD" in item:
                tvl = float(item["totalValueLockedUSD"])
                lines.append(f"   💰 TVL: ${format_number(tvl)}")
            
            if "volumeUSD" in item:
                volume = float(item["volumeUSD"])
                lines.append(f"   📈 交易量: ${format_number(volume)}")
                
        elif entity_type in ["positions", "position"]:
            lines.append(f"{prefix}**仓位 {format_address(item.get('id', ''))}**")
            lines.append(f"   👤 所有者: {format_address(item.get('owner', ''))}")
            
            if "liquidity" in item:
                lines.append(f"   💧 流动性: {format_number(float(item['liquidity']))}")
                
        else:
            # 通用格式化
            lines.append(f"{prefix}**{entity_type} {format_address(item.get('id', ''))}**")
            
            # 显示所有数值字段
            for k, v in item.items():
                if k in ["id", "__typename"]:
                    continue
                    
                if isinstance(v, (int, float)):
                    lines.append(f"   {k}: {format_number(float(v))}")
                elif isinstance(v, str) and v:
                    lines.append(f"   {k}: {v}")
                elif isinstance(v, dict) and "symbol" in v:
                    lines.append(f"   {k}: {v.get('symbol', 'Unknown')}")
        
        return lines
    
    def _get_protocol_examples(self, protocol_name: str) -> List[Dict[str, str]]:
        """获取协议特定的查询示例"""
        examples = {
            "uniswap": [
                {
                    "natural": "USDC/ETH 所有费率池子的信息",
                    "graphql": """query { 
                        pools(
                            where: {
                                or: [
                                    {token0_: {symbol_contains_nocase: "USDC"}, token1_: {symbol_contains_nocase: "ETH"}},
                                    {token0_: {symbol_contains_nocase: "ETH"}, token1_: {symbol_contains_nocase: "USDC"}}
                                ]
                            },
                            orderBy: feeTier,
                            orderDirection: asc,
                            first: 10
                        ) {
                            id
                            token0 { symbol name }
                            token1 { symbol name }
                            feeTier
                            totalValueLockedUSD
                            volumeUSD
                        }
                    }"""
                },
                {
                    "natural": "USDC/ETH 池子的 TVL",
                    "graphql": """query { 
                        pools(
                            where: {
                                or: [
                                    {token0_: {symbol_contains_nocase: "USDC"}, token1_: {symbol_contains_nocase: "ETH"}},
                                    {token0_: {symbol_contains_nocase: "ETH"}, token1_: {symbol_contains_nocase: "USDC"}}
                                ]
                            },
                            orderBy: totalValueLockedUSD,
                            orderDirection: desc,
                            first: 5
                        ) {
                            id
                            token0 { symbol }
                            token1 { symbol }
                            feeTier
                            totalValueLockedUSD
                        }
                    }"""
                },
                {
                    "natural": "TVL 最高的前5个池子",
                    "graphql": """query {
                        pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc) {
                            id
                            token0 { symbol }
                            token1 { symbol }
                            totalValueLockedUSD
                            volumeUSD
                            feeTier
                        }
                    }"""
                },
                {
                    "natural": "查看特定池子的详细信息",
                    "graphql": """query {
                        pool(id: "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640") {
                            id
                            token0 { symbol name decimals }
                            token1 { symbol name decimals }
                            totalValueLockedUSD
                            volumeUSD
                            feeTier
                            liquidity
                            sqrtPrice
                            tick
                        }
                    }"""
                }
            ],
            "aave": [
                {
                    "natural": "USDC 借贷市场的总存款和借款",
                    "graphql": """query {
                        markets(where: {inputToken_: {symbol: "USDC"}}, first: 1) {
                            totalDepositBalanceUSD
                            totalBorrowBalanceUSD
                            rates {
                                rate
                                side
                            }
                        }
                    }"""
                },
                {
                    "natural": "最近的清算事件",
                    "graphql": """query {
                        liquidates(first: 10, orderBy: timestamp, orderDirection: desc) {
                            id
                            timestamp
                            amount
                            amountUSD
                            profitUSD
                        }
                    }"""
                }
            ]
        }
        
        # 返回协议相关示例，如果没有则返回通用示例
        protocol_lower = protocol_name.lower()
        for key, value in examples.items():
            if key in protocol_lower:
                return value
        
        # 返回一些通用示例
        return [
            {
                "natural": "查看 TVL 最高的数据",
                "graphql": """query {
                    pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc) {
                        id
                        totalValueLockedUSD
                    }
                }"""
            }
        ]

# 全局实例
graphql_builder = GraphQLBuilder()
