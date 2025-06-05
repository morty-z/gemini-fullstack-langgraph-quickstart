# app/agent/tools/evm/evm_tools.py
"""
EVM 链工具集 - 纯 RPC 功能
只使用 EVM RPC API，不依赖外部价格源
"""

from langchain.tools import Tool
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
from app.agent.tools.evm.evm_client import evm_client
from app.agent.tools.evm.evm_config import (
    SUPPORTED_CHAINS, get_chain_info, get_common_tokens,
    DISPLAY_CONFIG, format_address, format_value
)

logger = logging.getLogger(__name__)

# ===== 账户相关工具 =====

def get_native_balance(query: str) -> str:
    """
    获取原生代币余额
    输入格式: "地址 链名" 或仅 "地址"（默认查询 ethereum）
    """
    try:
        parts = query.strip().split()
        if not parts:
            return "请提供地址"
        
        address = parts[0].strip()
        chain = parts[1] if len(parts) > 1 else "ethereum"
        
        # 验证地址格式
        if not address.startswith("0x") or len(address) != 42:
            return f"无效的地址格式: {address}"
        
        # 获取链信息
        chain_info = get_chain_info(chain)
        if not chain_info:
            supported = ", ".join(SUPPORTED_CHAINS.keys())
            return f"不支持的链: {chain}\n支持的链: {supported}"
        
        # 查询余额
        result = evm_client.call_rpc(chain, "eth_getBalance", [address, "latest"])
        
        # 转换余额
        balance_wei = int(result, 16)
        balance = balance_wei / (10 ** chain_info.decimals)
        
        # 获取当前区块
        block_hex = evm_client.call_rpc(chain, "eth_blockNumber", [])
        block_number = int(block_hex, 16)
        
        # 获取交易计数
        tx_count_hex = evm_client.call_rpc(chain, "eth_getTransactionCount", [address, "latest"])
        tx_count = int(tx_count_hex, 16)
        
        return f"""
🏦 {chain_info.name} 账户信息

📍 地址: {address}
💰 余额: {balance:.6f} {chain_info.native_token}
💵 Wei: {balance_wei:,}
📤 交易数: {tx_count}
📦 区块高度: {block_number:,}
🔗 浏览器: {chain_info.explorer_url}/address/{address}
"""
        
    except Exception as e:
        logger.error(f"查询余额失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_account_info(query: str) -> str:
    """
    获取账户详细信息（余额、nonce、代码等）
    输入格式: "地址 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) < 2:
            return "请提供: 地址 链名"
        
        address = parts[0]
        chain = parts[1]
        
        # 验证地址
        if not address.startswith("0x") or len(address) != 42:
            return f"无效的地址格式: {address}"
        
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 获取余额
        balance_hex = evm_client.call_rpc(chain, "eth_getBalance", [address, "latest"])
        balance_wei = int(balance_hex, 16)
        balance = balance_wei / (10 ** chain_info.decimals)
        
        # 获取 nonce
        nonce_hex = evm_client.call_rpc(chain, "eth_getTransactionCount", [address, "latest"])
        nonce = int(nonce_hex, 16)
        
        # 获取代码（判断是否为合约）
        code = evm_client.call_rpc(chain, "eth_getCode", [address, "latest"])
        is_contract = code != "0x"
        
        # 获取存储槽位（如果是合约）
        storage_info = ""
        if is_contract:
            # 尝试读取槽位 0（通常存储重要数据）
            slot0 = evm_client.call_rpc(chain, "eth_getStorageAt", [address, "0x0", "latest"])
            if slot0 != "0x0000000000000000000000000000000000000000000000000000000000000000":
                storage_info = f"\n💾 存储槽0: {slot0[:10]}..."
        
        account_type = "🤖 合约账户" if is_contract else "👤 外部账户(EOA)"
        
        return f"""
📋 账户详细信息

📍 地址: {address}
⛓️ 链: {chain_info.name}
🏷️ 类型: {account_type}
💰 余额: {balance:.6f} {chain_info.native_token}
🔢 Nonce: {nonce}
📏 代码大小: {len(code) // 2 - 1} 字节{storage_info}
🔗 浏览器: {chain_info.explorer_url}/address/{address}
"""
        
    except Exception as e:
        logger.error(f"查询账户信息失败: {str(e)}")
        return f"查询失败: {str(e)}"

def check_is_contract(query: str) -> str:
    """
    检查地址是否为合约
    输入格式: "地址 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) < 2:
            return "请提供: 地址 链名"
        
        address = parts[0]
        chain = parts[1]
        
        if not address.startswith("0x") or len(address) != 42:
            return f"无效的地址格式: {address}"
        
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 获取代码
        code = evm_client.call_rpc(chain, "eth_getCode", [address, "latest"])
        is_contract = code != "0x"
        
        if is_contract:
            code_size = len(code) // 2 - 1
            return f"""
✅ 是合约地址

📍 地址: {address}
⛓️ 链: {chain_info.name}
📏 合约代码大小: {code_size} 字节
🔍 代码哈希: {code[:66] if len(code) > 66 else code}
🔗 浏览器: {chain_info.explorer_url}/address/{address}#code
"""
        else:
            # 获取更多 EOA 信息
            balance_hex = evm_client.call_rpc(chain, "eth_getBalance", [address, "latest"])
            balance = int(balance_hex, 16) / (10 ** chain_info.decimals)
            nonce_hex = evm_client.call_rpc(chain, "eth_getTransactionCount", [address, "latest"])
            nonce = int(nonce_hex, 16)
            
            return f"""
❌ 不是合约地址

📍 地址: {address}
⛓️ 链: {chain_info.name}
🏷️ 类型: 外部账户(EOA)
💰 余额: {balance:.6f} {chain_info.native_token}
📤 发送交易数: {nonce}
🔗 浏览器: {chain_info.explorer_url}/address/{address}
"""
        
    except Exception as e:
        logger.error(f"检查合约失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== ERC20 代币相关工具 =====

def get_token_balance(query: str) -> str:
    """
    查询 ERC20 代币余额
    输入格式: "钱包地址 代币地址 链名" 或 "钱包地址 代币符号 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) < 3:
            return "请提供：钱包地址 代币地址/符号 链名"
        
        wallet_address = parts[0]
        token_input = parts[1]
        chain = parts[2]
        
        # 验证地址
        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            return f"无效的钱包地址: {wallet_address}"
        
        # 获取链信息
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 确定代币地址
        token_address = token_input
        if not token_input.startswith("0x"):
            # 尝试从常用代币中查找
            chain_tokens = get_common_tokens(chain)
            token_address = chain_tokens.get(token_input.upper())
            if not token_address:
                return f"未找到代币 {token_input}，请提供代币合约地址"
        
        # 验证代币地址是合约
        code = evm_client.call_rpc(chain, "eth_getCode", [token_address, "latest"])
        if code == "0x":
            return f"地址 {token_address} 不是合约地址"
        
        # 查询余额
        # balanceOf(address) 方法签名
        method_id = "0x70a08231"
        params = wallet_address[2:].zfill(64)
        call_data = method_id + params
        
        result = evm_client.call_rpc(chain, "eth_call", [{
            "to": token_address,
            "data": call_data
        }, "latest"])
        
        balance_raw = int(result, 16) if result != "0x" else 0
        
        # 获取代币信息
        token_info = get_token_info(token_address, chain)
        
        # 转换余额
        decimals = token_info.get("decimals", 18)
        balance = balance_raw / (10 ** decimals)
        
        return f"""
🪙 ERC20 代币余额查询

📍 钱包地址: {wallet_address}
🏷️ 代币: {token_info.get('symbol', 'UNKNOWN')} ({token_info.get('name', 'Unknown Token')})
📄 合约地址: {token_address}
💰 余额: {balance:,.6f} {token_info.get('symbol', 'UNKNOWN')}
🔢 原始余额: {balance_raw}
⚙️ 精度: {decimals}
⛓️ 链: {chain_info.name}
🔗 浏览器: {chain_info.explorer_url}/token/{token_address}?a={wallet_address}
"""
        
    except Exception as e:
        logger.error(f"查询代币余额失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_token_info(token_address: str, chain: str) -> dict:
    """获取代币基本信息"""
    info = {}
    
    try:
        # name()
        name_result = evm_client.call_rpc(chain, "eth_call", [{
            "to": token_address,
            "data": "0x06fdde03"
        }, "latest"])
        info["name"] = decode_string(name_result)
        
        # symbol()
        symbol_result = evm_client.call_rpc(chain, "eth_call", [{
            "to": token_address,
            "data": "0x95d89b41"
        }, "latest"])
        info["symbol"] = decode_string(symbol_result)
        
        # decimals()
        decimals_result = evm_client.call_rpc(chain, "eth_call", [{
            "to": token_address,
            "data": "0x313ce567"
        }, "latest"])
        info["decimals"] = int(decimals_result, 16) if decimals_result != "0x" else 18
        
        # totalSupply()
        supply_result = evm_client.call_rpc(chain, "eth_call", [{
            "to": token_address,
            "data": "0x18160ddd"
        }, "latest"])
        if supply_result != "0x":
            total_supply_raw = int(supply_result, 16)
            info["totalSupply"] = total_supply_raw / (10 ** info["decimals"])
        
    except Exception as e:
        logger.warning(f"获取代币信息失败: {str(e)}")
        info = {"name": "Unknown", "symbol": "UNKNOWN", "decimals": 18}
    
    return info

def get_token_metadata(query: str) -> str:
    """
    获取 ERC20 代币元数据
    输入格式: "代币地址 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) < 2:
            return "请提供: 代币地址 链名"
        
        token_address = parts[0]
        chain = parts[1]
        
        if not token_address.startswith("0x") or len(token_address) != 42:
            return f"无效的地址格式: {token_address}"
        
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 验证是合约
        code = evm_client.call_rpc(chain, "eth_getCode", [token_address, "latest"])
        if code == "0x":
            return f"地址 {token_address} 不是合约地址"
        
        # 获取代币信息
        info = get_token_info(token_address, chain)
        
        result = f"""
📋 ERC20 代币元数据

📍 合约地址: {token_address}
⛓️ 链: {chain_info.name}
🏷️ 符号: {info.get('symbol', 'UNKNOWN')}
📝 名称: {info.get('name', 'Unknown Token')}
⚙️ 精度: {info.get('decimals', 18)}
"""
        
        if 'totalSupply' in info:
            result += f"💎 总供应量: {info['totalSupply']:,.2f} {info.get('symbol', 'UNKNOWN')}\n"
        
        result += f"🔗 浏览器: {chain_info.explorer_url}/token/{token_address}"
        
        return result
        
    except Exception as e:
        logger.error(f"获取代币元数据失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_token_allowance(query: str) -> str:
    """
    查询 ERC20 代币授权额度
    输入格式: "代币地址 所有者地址 被授权地址 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) < 4:
            return "请提供: 代币地址 所有者地址 被授权地址 链名"
        
        token_address = parts[0]
        owner = parts[1]
        spender = parts[2]
        chain = parts[3]
        
        # 验证地址
        for addr, name in [(token_address, "代币"), (owner, "所有者"), (spender, "被授权者")]:
            if not addr.startswith("0x") or len(addr) != 42:
                return f"无效的{name}地址: {addr}"
        
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # allowance(owner, spender) 方法签名
        method_id = "0xdd62ed3e"
        params = owner[2:].zfill(64) + spender[2:].zfill(64)
        call_data = method_id + params
        
        result = evm_client.call_rpc(chain, "eth_call", [{
            "to": token_address,
            "data": call_data
        }, "latest"])
        
        allowance_raw = int(result, 16) if result != "0x" else 0
        
        # 获取代币信息
        token_info = get_token_info(token_address, chain)
        decimals = token_info.get("decimals", 18)
        allowance = allowance_raw / (10 ** decimals)
        
        # 检查是否为无限授权
        max_uint256 = 2**256 - 1
        is_unlimited = allowance_raw == max_uint256
        
        return f"""
🔓 ERC20 代币授权查询

🪙 代币: {token_info.get('symbol', 'UNKNOWN')} ({token_info.get('name', 'Unknown')})
📍 代币地址: {token_address}
👤 所有者: {owner}
🏢 被授权者: {spender}
⛓️ 链: {chain_info.name}

💰 授权额度: {'无限' if is_unlimited else f"{allowance:,.6f} {token_info.get('symbol', 'UNKNOWN')}"}
🔢 原始数值: {allowance_raw}

🔗 浏览器: {chain_info.explorer_url}/token/{token_address}?a={owner}
"""
        
    except Exception as e:
        logger.error(f"查询授权额度失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== 交易相关工具 =====

def get_transaction(query: str) -> str:
    """
    查询交易详情
    输入格式: "交易哈希 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) != 2:
            return "请提供：交易哈希 链名"
        
        tx_hash = parts[0]
        chain = parts[1]
        
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            return f"无效的交易哈希格式: {tx_hash}"
        
        # 获取链信息
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 获取交易信息
        tx = evm_client.call_rpc(chain, "eth_getTransactionByHash", [tx_hash])
        if not tx:
            return f"未找到交易: {tx_hash}"
        
        # 获取交易收据
        receipt = evm_client.call_rpc(chain, "eth_getTransactionReceipt", [tx_hash])
        
        # 解析信息
        from_addr = tx.get("from", "")
        to_addr = tx.get("to", "")
        value_wei = int(tx.get("value", "0x0"), 16)
        value = value_wei / (10 ** chain_info.decimals)
        
        gas_price = int(tx.get("gasPrice", "0x0"), 16) / 1e9
        gas_used = int(receipt.get("gasUsed", "0x0"), 16) if receipt else 0
        gas_limit = int(tx.get("gas", "0x0"), 16)
        tx_fee = (gas_used * int(tx.get("gasPrice", "0x0"), 16)) / (10 ** chain_info.decimals)
        
        status = "成功 ✅" if receipt and receipt.get("status") == "0x1" else "失败 ❌"
        block_number = int(tx.get("blockNumber", "0x0"), 16)
        
        # 获取区块时间
        block = evm_client.call_rpc(chain, "eth_getBlockByNumber", [tx["blockNumber"], False])
        timestamp = int(block.get("timestamp", "0x0"), 16)
        tx_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查是否为合约交互
        input_data = tx.get("input", "0x")
        is_contract_interaction = len(input_data) > 2
        
        result = f"""
📋 交易详情

🔗 哈希: {tx_hash}
⛓️ 链: {chain_info.name}
✨ 状态: {status}
📅 时间: {tx_time}

👤 发送方: {from_addr}
👤 接收方: {to_addr or '合约创建'}
💰 金额: {value:.6f} {chain_info.native_token}
"""
        
        if is_contract_interaction:
            result += f"📝 输入数据: {input_data[:10]}... ({len(input_data)//2-1} 字节)\n"
        
        result += f"""
⛽ Gas 信息:
  • Gas 价格: {gas_price:.2f} Gwei
  • Gas 限制: {gas_limit:,}
  • Gas 使用: {gas_used:,} ({gas_used/gas_limit*100:.1f}%)
  • 交易费: {tx_fee:.6f} {chain_info.native_token}

📦 区块: #{block_number:,}
🔍 浏览器: {chain_info.explorer_url}/tx/{tx_hash}
"""
        
        # 如果有日志，显示事件数量
        if receipt and receipt.get("logs"):
            result += f"\n📜 事件日志: {len(receipt['logs'])} 个事件"
        
        return result
        
    except Exception as e:
        logger.error(f"查询交易失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_transaction_receipt(query: str) -> str:
    """
    获取交易收据（包含日志）
    输入格式: "交易哈希 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) != 2:
            return "请提供：交易哈希 链名"
        
        tx_hash = parts[0]
        chain = parts[1]
        
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            return f"无效的交易哈希格式: {tx_hash}"
        
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 获取交易收据
        receipt = evm_client.call_rpc(chain, "eth_getTransactionReceipt", [tx_hash])
        if not receipt:
            return f"未找到交易收据: {tx_hash}"
        
        # 解析基本信息
        status = "成功 ✅" if receipt.get("status") == "0x1" else "失败 ❌"
        gas_used = int(receipt.get("gasUsed", "0x0"), 16)
        block_number = int(receipt.get("blockNumber", "0x0"), 16)
        
        result = f"""
📜 交易收据

🔗 交易哈希: {tx_hash}
⛓️ 链: {chain_info.name}
✨ 状态: {status}
📦 区块: #{block_number:,}
⛽ Gas 使用: {gas_used:,}
"""
        
        # 如果是合约创建
        if receipt.get("contractAddress"):
            result += f"🏭 创建的合约: {receipt['contractAddress']}\n"
        
        # 解析日志
        logs = receipt.get("logs", [])
        if logs:
            result += f"\n📝 事件日志 ({len(logs)} 个):\n"
            for i, log in enumerate(logs[:5]):  # 最多显示5个
                result += f"\n事件 {i+1}:\n"
                result += f"  • 合约: {log['address']}\n"
                result += f"  • 主题数: {len(log['topics'])}\n"
                if log['topics']:
                    result += f"  • 事件签名: {log['topics'][0][:10]}...\n"
                result += f"  • 数据长度: {len(log['data'])//2-1} 字节\n"
            
            if len(logs) > 5:
                result += f"\n... 还有 {len(logs) - 5} 个事件\n"
        else:
            result += "\n📝 无事件日志\n"
        
        result += f"\n🔍 浏览器: {chain_info.explorer_url}/tx/{tx_hash}#eventlog"
        
        return result
        
    except Exception as e:
        logger.error(f"查询交易收据失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== 区块和Gas相关工具 =====

def get_gas_price(chain: str) -> str:
    """查询当前 gas 价格"""
    try:
        # 获取链信息
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 获取 gas 价格
        gas_price_hex = evm_client.call_rpc(chain, "eth_gasPrice", [])
        gas_price_wei = int(gas_price_hex, 16)
        gas_price_gwei = gas_price_wei / 1e9
        
        # 获取最新区块
        latest_block = evm_client.call_rpc(chain, "eth_getBlockByNumber", ["latest", False])
        block_number = int(latest_block["number"], 16)
        
        # EIP-1559 信息
        base_fee_gwei = 0
        if "baseFeePerGas" in latest_block:
            base_fee_gwei = int(latest_block["baseFeePerGas"], 16) / 1e9
        
        # 计算不同优先级的建议费用
        priority_fees = {
            "🐌 慢速": gas_price_gwei * 0.8,
            "🚶 标准": gas_price_gwei,
            "🏃 快速": gas_price_gwei * 1.2,
            "🚀 极速": gas_price_gwei * 1.5,
        }
        
        # 计算不同交易的预估费用
        tx_costs = {
            "简单转账": 21000,
            "ERC20 转账": 65000,
            "Uniswap 交换": 150000,
            "NFT 铸造": 100000,
            "合约部署": 500000,
        }
        
        result = f"""
⛽ {chain_info.name} Gas 价格

📊 当前信息:
• Gas 价格: {gas_price_gwei:.2f} Gwei
• Base Fee: {base_fee_gwei:.2f} Gwei
• 区块高度: #{block_number:,}

⚡ 建议 Gas 价格:
"""
        for priority, price in priority_fees.items():
            result += f"• {priority}: {price:.2f} Gwei\n"
        
        result += f"\n💸 预估交易费用 (使用标准 Gas):\n"
        for tx_type, gas_limit in tx_costs.items():
            cost = gas_limit * gas_price_wei / (10 ** chain_info.decimals)
            result += f"• {tx_type}: {cost:.6f} {chain_info.native_token}\n"
        
        result += "\n💡 提示: 实际费用可能因网络拥堵而变化"
        
        return result
        
    except Exception as e:
        logger.error(f"查询 gas 价格失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_block_info(query: str) -> str:
    """
    获取区块信息
    输入格式: "区块号或latest 链名"
    """
    try:
        parts = query.strip().split()
        if len(parts) < 2:
            return "请提供: 区块号(或latest) 链名"
        
        block_id = parts[0]
        chain = parts[1]
        
        chain_info = get_chain_info(chain)
        if not chain_info:
            return f"不支持的链: {chain}"
        
        # 处理区块标识
        if block_id == "latest":
            block_param = "latest"
        else:
            try:
                block_num = int(block_id)
                block_param = hex(block_num)
            except:
                return f"无效的区块号: {block_id}"
        
        # 获取区块信息
        block = evm_client.call_rpc(chain, "eth_getBlockByNumber", [block_param, False])
        if not block:
            return f"未找到区块: {block_id}"
        
        # 解析信息
        block_number = int(block["number"], 16)
        timestamp = int(block["timestamp"], 16)
        block_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        tx_count = len(block.get("transactions", []))
        
        # Gas 信息
        gas_used = int(block["gasUsed"], 16)
        gas_limit = int(block["gasLimit"], 16)
        gas_usage_percent = (gas_used / gas_limit * 100) if gas_limit > 0 else 0
        
        result = f"""
📦 区块信息

🔢 区块号: #{block_number:,}
⛓️ 链: {chain_info.name}
📅 时间: {block_time}
🕐 时间戳: {timestamp}

📊 区块数据:
• 交易数: {tx_count}
• Gas 使用: {gas_used:,} / {gas_limit:,} ({gas_usage_percent:.1f}%)
• 区块哈希: {block['hash']}
• 父区块: {block['parentHash'][:10]}...
• 矿工: {block['miner']}
"""
        
        if "baseFeePerGas" in block:
            base_fee_gwei = int(block["baseFeePerGas"], 16) / 1e9
            result += f"• Base Fee: {base_fee_gwei:.2f} Gwei\n"
        
        # 额外数据
        extra_data = block.get("extraData", "0x")
        if len(extra_data) > 2:
            try:
                decoded = bytes.fromhex(extra_data[2:]).decode('utf-8', errors='ignore')
                printable = ''.join(c for c in decoded if c.isprintable())
                if printable:
                    result += f"• 额外数据: {printable[:50]}...\n"
            except:
                pass
        
        result += f"\n🔍 浏览器: {chain_info.explorer_url}/block/{block_number}"
        
        return result
        
    except Exception as e:
        logger.error(f"查询区块信息失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== 工具函数 =====

def decode_string(hex_str: str) -> str:
    """解码 ABI 编码的字符串"""
    try:
        if not hex_str or hex_str == "0x":
            return "Unknown"
        
        # 去掉 0x
        hex_data = hex_str[2:]
        
        # 简单处理：尝试直接解码
        # 跳过前 64 个字符（偏移量）和接下来的 64 个字符（长度）
        if len(hex_data) > 128:
            string_hex = hex_data[128:]
            # 去掉尾部的 0
            string_hex = string_hex.rstrip('0')
            if len(string_hex) % 2 == 1:
                string_hex += '0'
            
            bytes_data = bytes.fromhex(string_hex)
            return bytes_data.decode('utf-8').strip('\x00')
        else:
            # 尝试直接解码
            bytes_data = bytes.fromhex(hex_data)
            decoded = bytes_data.decode('utf-8', errors='ignore')
            # 提取可打印字符
            return ''.join(c for c in decoded if c.isprintable()).strip()
            
    except Exception:
        return "Unknown"

# ===== 创建工具对象 =====

# 账户相关
native_balance_tool = Tool(
    name="GetNativeBalance",
    description="查询 EVM 链原生代币余额。输入：'地址 链名' 或仅地址。支持：ethereum、bsc、polygon、arbitrum、optimism、avalanche、base、fantom",
    func=get_native_balance
)

account_info_tool = Tool(
    name="GetAccountInfo",
    description="获取账户详细信息（余额、nonce、是否合约等）。输入：'地址 链名'",
    func=get_account_info
)

check_contract_tool = Tool(
    name="CheckIsContract",
    description="检查地址是否为合约。输入：'地址 链名'",
    func=check_is_contract
)

# ERC20 代币相关
token_balance_tool = Tool(
    name="GetTokenBalance",
    description="查询 ERC20 代币余额。输入：'钱包地址 代币地址/符号 链名'。示例：'0x123... USDT ethereum'",
    func=get_token_balance
)

token_metadata_tool = Tool(
    name="GetTokenMetadata",
    description="获取 ERC20 代币元数据（名称、符号、精度、总供应量）。输入：'代币地址 链名'",
    func=get_token_metadata
)

token_allowance_tool = Tool(
    name="GetTokenAllowance",
    description="查询 ERC20 代币授权额度。输入：'代币地址 所有者地址 被授权地址 链名'",
    func=get_token_allowance
)

# 交易相关
transaction_tool = Tool(
    name="GetTransaction",
    description="查询交易详情。输入：'交易哈希 链名'",
    func=get_transaction
)

transaction_receipt_tool = Tool(
    name="GetTransactionReceipt",
    description="获取交易收据（包含事件日志）。输入：'交易哈希 链名'",
    func=get_transaction_receipt
)

# 区块和 Gas 相关
gas_price_tool = Tool(
    name="GetGasPrice",
    description="查询 EVM 链当前 gas 价格和费用估算。输入：链名",
    func=get_gas_price
)

block_info_tool = Tool(
    name="GetBlockInfo",
    description="获取区块信息。输入：'区块号或latest 链名'",
    func=get_block_info
)

# 导出所有工具
evm_tools = [
    # 账户相关
    native_balance_tool,
    account_info_tool,
    check_contract_tool,
    
    # ERC20 代币相关
    token_balance_tool,
    token_metadata_tool,
    token_allowance_tool,
    
    # 交易相关
    transaction_tool,
    transaction_receipt_tool,
    
    # 区块和 Gas 相关
    gas_price_tool,
    block_info_tool,
]

__all__ = [
    'evm_tools',
    'native_balance_tool',
    'account_info_tool',
    'check_contract_tool',
    'token_balance_tool',
    'token_metadata_tool',
    'token_allowance_tool',
    'transaction_tool',
    'transaction_receipt_tool',
    'gas_price_tool',
    'block_info_tool',
]