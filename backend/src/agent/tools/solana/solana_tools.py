# app/agent/tools/solana/solana_tools.py
"""
Solana 工具集 - 纯 RPC 功能
只使用 Solana RPC API，不依赖外部价格源
"""

from langchain.tools import Tool
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
import base58
from app.agent.tools.solana.solana_client import solana_client
from app.agent.tools.solana.solana_config import (
    COMMON_TOKENS, EXPLORERS, DEX_PROGRAMS,
    TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID,
    SYSTEM_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID,
    format_lamports, format_address
)

logger = logging.getLogger(__name__)

# ===== 账户相关工具 =====

def get_sol_balance(address: str) -> str:
    """
    获取 SOL 余额
    输入：Solana 地址
    """
    try:
        logger.info(f"开始查询 SOL 余额: {address}")
        
        # 验证地址格式
        if not solana_client.is_valid_address(address):
            return f"无效的 Solana 地址格式: {address}"
        
        # 获取余额
        lamports = solana_client.get_balance(address)
        sol_balance = lamports / 1e9  # 转换为 SOL
        
        # 获取当前 slot 和 epoch
        current_slot = solana_client.get_slot()
        epoch_info = solana_client.get_epoch_info()
        
        # 获取账户信息
        account_info = solana_client.get_account_info(address)
        is_executable = False
        owner = None
        
        if account_info:
            is_executable = account_info.get("executable", False)
            owner = account_info.get("owner")
        
        account_type = "程序账户" if is_executable else "普通账户"
        
        result = f"""
🏦 Solana 账户查询

📍 地址: {address}
🏷️ 类型: {account_type}
💰 余额: {sol_balance:.9f} SOL
💵 Lamports: {lamports:,}
📦 当前 Slot: {current_slot:,}
🔄 当前 Epoch: {epoch_info.get('epoch', 0)}
"""
        
        if owner:
            result += f"👤 所有者: {format_address(owner)}\n"
        
        result += f"""
🔗 浏览器:
  • {EXPLORERS['solscan']}/account/{address}
  • {EXPLORERS['solana_explorer']}/address/{address}
"""
        
        logger.info(f"SOL 余额查询成功: {address}")
        return result
        
    except Exception as e:
        logger.error(f"查询 SOL 余额失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_account_info(address: str) -> str:
    """
    获取账户详细信息
    输入：Solana 地址
    """
    try:
        if not solana_client.is_valid_address(address):
            return f"无效的 Solana 地址格式: {address}"
        
        # 获取账户信息
        account_info = solana_client.get_account_info(address)
        
        if not account_info:
            return f"账户不存在或未初始化: {address}"
        
        # 解析账户数据
        lamports = account_info.get("lamports", 0)
        sol_balance = lamports / 1e9
        owner = account_info.get("owner", "")
        executable = account_info.get("executable", False)
        rent_epoch = account_info.get("rentEpoch", 0)
        data = account_info.get("data", [])
        
        # 获取数据大小
        data_size = 0
        if isinstance(data, list) and len(data) > 0:
            # base64 编码的数据
            if data[1] == "base64":
                import base64
                data_size = len(base64.b64decode(data[0]))
            else:
                data_size = len(data[0]) // 2  # hex 编码
        
        # 确定账户类型
        account_type = "未知"
        if executable:
            account_type = "程序账户 (可执行)"
        elif owner == SYSTEM_PROGRAM_ID:
            account_type = "系统账户"
        elif owner == TOKEN_PROGRAM_ID:
            account_type = "SPL Token 账户"
        elif owner == TOKEN_2022_PROGRAM_ID:
            account_type = "Token-2022 账户"
        else:
            account_type = "数据账户"
        
        result = f"""
📋 Solana 账户详细信息

📍 地址: {address}
🏷️ 类型: {account_type}
💰 余额: {sol_balance:.9f} SOL ({lamports:,} lamports)
👤 所有者: {owner}
🔐 可执行: {'是' if executable else '否'}
💾 数据大小: {data_size} 字节
🏠 租金纪元: {rent_epoch}
"""
        
        # 如果是 Token 账户，尝试解析代币信息
        if owner in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
            parsed_data = account_info.get("data", {}).get("parsed")
            if parsed_data and parsed_data.get("type") == "account":
                info = parsed_data.get("info", {})
                mint = info.get("mint", "")
                token_owner = info.get("owner", "")
                amount = info.get("tokenAmount", {}).get("uiAmountString", "0")
                
                result += f"""
🪙 代币账户信息:
  • Mint: {mint}
  • 持有者: {format_address(token_owner)}
  • 余额: {amount}
"""
        
        result += f"""
🔗 浏览器: {EXPLORERS['solscan']}/account/{address}
"""
        
        return result
        
    except Exception as e:
        logger.error(f"查询账户信息失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== SPL Token 相关工具 =====

def get_spl_tokens(address: str) -> str:
    """
    获取地址持有的所有 SPL 代币账户
    输入：Solana 地址
    """
    try:
        logger.info(f"开始查询 SPL 代币: {address}")
        
        # 验证地址格式
        if not solana_client.is_valid_address(address):
            return f"无效的 Solana 地址格式: {address}"
        
        # 获取所有代币账户
        token_accounts = solana_client.get_token_accounts_by_owner(address)
        
        if not token_accounts:
            return f"地址 {address} 没有持有任何 SPL 代币"
        
        # 构建结果
        result = f"""
🪙 SPL 代币持仓

📍 地址: {address}
📊 代币账户数: {len(token_accounts)}

💰 代币列表:
"""
        
        # 解析每个代币账户
        for i, account in enumerate(token_accounts, 1):
            account_data = account.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            pubkey = account.get("pubkey", "")
            mint = account_data.get("mint", "")
            owner = account_data.get("owner", "")
            
            # 获取代币余额
            token_amount = account_data.get("tokenAmount", {})
            ui_amount = token_amount.get("uiAmountString", "0")
            decimals = token_amount.get("decimals", 0)
            amount = token_amount.get("amount", "0")
            
            # 查找已知代币信息
            token_info = None
            for symbol, info in COMMON_TOKENS.items():
                if info.mint == mint:
                    token_info = info
                    break
            
            if token_info:
                result += f"\n{i}. 🏷️ {token_info.symbol} ({token_info.name})\n"
            else:
                result += f"\n{i}. 🏷️ 未知代币\n"
            
            result += f"   📍 Mint: {mint}\n"
            result += f"   💰 余额: {ui_amount}\n"
            result += f"   🔢 原始数量: {amount} (精度: {decimals})\n"
            result += f"   📂 账户: {format_address(pubkey)}\n"
        
        result += f"""
🔗 浏览器: {EXPLORERS['solscan']}/account/{address}#portfolio
"""
        
        logger.info(f"SPL 代币查询完成")
        return result
        
    except Exception as e:
        logger.error(f"查询 SPL 代币失败: {str(e)}", exc_info=True)
        return f"查询失败: {str(e)}"

def get_token_supply(mint: str) -> str:
    """
    获取代币总供应量
    输入：代币 Mint 地址
    """
    try:
        if not solana_client.is_valid_address(mint):
            return f"无效的 Mint 地址格式: {mint}"
        
        # 获取代币供应量
        supply_info = solana_client.get_token_supply(mint)
        
        if not supply_info:
            return f"无法获取代币供应量: {mint}"
        
        ui_amount = supply_info.get("uiAmountString", "0")
        amount = supply_info.get("amount", "0")
        decimals = supply_info.get("decimals", 0)
        
        # 查找已知代币信息
        token_info = None
        for symbol, info in COMMON_TOKENS.items():
            if info.mint == mint:
                token_info = info
                break
        
        result = f"""
💎 代币供应量信息

📍 Mint: {mint}
"""
        
        if token_info:
            result += f"🏷️ 代币: {token_info.symbol} ({token_info.name})\n"
        
        result += f"""💰 总供应量: {ui_amount}
🔢 原始数量: {amount}
⚙️ 精度: {decimals}
🔗 浏览器: {EXPLORERS['solscan']}/token/{mint}
"""
        
        return result
        
    except Exception as e:
        logger.error(f"查询代币供应量失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_token_account_info(query: str) -> str:
    """
    获取特定代币账户信息
    输入格式: "代币账户地址" 或 "钱包地址 mint地址"
    """
    try:
        parts = query.strip().split()
        
        if len(parts) == 1:
            # 直接查询代币账户
            token_account = parts[0]
        elif len(parts) == 2:
            # 通过钱包地址和mint查找
            wallet = parts[0]
            mint = parts[1]
            
            # 获取所有代币账户并查找匹配的
            token_accounts = solana_client.get_token_accounts_by_owner(wallet, mint)
            if not token_accounts:
                return f"未找到钱包 {wallet} 持有的 {mint} 代币账户"
            
            token_account = token_accounts[0].get("pubkey", "")
        else:
            return "请提供：代币账户地址 或 钱包地址 mint地址"
        
        # 获取账户信息
        account_info = solana_client.get_account_info(token_account)
        
        if not account_info:
            return f"代币账户不存在: {token_account}"
        
        # 解析代币账户数据
        parsed_data = account_info.get("data", {}).get("parsed")
        if not parsed_data or parsed_data.get("type") != "account":
            return f"这不是一个有效的代币账户: {token_account}"
        
        info = parsed_data.get("info", {})
        mint = info.get("mint", "")
        owner = info.get("owner", "")
        state = info.get("state", "")
        is_native = info.get("isNative", False)
        
        token_amount = info.get("tokenAmount", {})
        ui_amount = token_amount.get("uiAmountString", "0")
        amount = token_amount.get("amount", "0")
        decimals = token_amount.get("decimals", 0)
        
        # 查找已知代币信息
        token_info = None
        for symbol, token_data in COMMON_TOKENS.items():
            if token_data.mint == mint:
                token_info = token_data
                break
        
        result = f"""
📂 代币账户详情

📍 账户地址: {token_account}
🪙 Mint: {mint}
"""
        
        if token_info:
            result += f"🏷️ 代币: {token_info.symbol} ({token_info.name})\n"
        
        result += f"""👤 持有者: {owner}
💰 余额: {ui_amount}
🔢 原始数量: {amount} (精度: {decimals})
📊 状态: {state}
🏦 原生SOL: {'是' if is_native else '否'}
🔗 浏览器: {EXPLORERS['solscan']}/account/{token_account}
"""
        
        return result
        
    except Exception as e:
        logger.error(f"查询代币账户失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== 交易相关工具 =====

def get_transaction(signature: str) -> str:
    """
    查询交易详情
    输入：交易签名
    """
    try:
        # 获取交易信息
        tx = solana_client.get_transaction(signature)
        
        if not tx:
            return f"未找到交易: {signature}"
        
        # 解析交易信息
        slot = tx.get("slot", 0)
        block_time = tx.get("blockTime", 0)
        
        # 元数据
        meta = tx.get("meta", {})
        err = meta.get("err")
        fee = meta.get("fee", 0)
        
        # 交易前后余额
        pre_balances = meta.get("preBalances", [])
        post_balances = meta.get("postBalances", [])
        
        # 交易数据
        transaction = tx.get("transaction", {})
        message = transaction.get("message", {})
        account_keys = message.get("accountKeys", [])
        
        # 获取时间
        tx_time = "未知"
        if block_time:
            tx_time = datetime.fromtimestamp(block_time).strftime("%Y-%m-%d %H:%M:%S")
        
        status = "成功 ✅" if err is None else f"失败 ❌ ({err})"
        
        result = f"""
📋 交易详情

🔗 签名: {signature}
✨ 状态: {status}
📅 时间: {tx_time}
📦 Slot: {slot:,}
💸 手续费: {fee / 1e9:.9f} SOL

📊 账户变化:
"""
        
        # 显示账户余额变化
        for i, account in enumerate(account_keys[:5]):  # 最多显示5个
            if i < len(pre_balances) and i < len(post_balances):
                pre = pre_balances[i] / 1e9
                post = post_balances[i] / 1e9
                change = post - pre
                
                if isinstance(account, dict):
                    pubkey = account.get("pubkey", "")
                else:
                    pubkey = account
                
                if change != 0:
                    change_str = f"+{change:.9f}" if change > 0 else f"{change:.9f}"
                    result += f"• {format_address(pubkey)}: {change_str} SOL\n"
        
        if len(account_keys) > 5:
            result += f"... 还有 {len(account_keys) - 5} 个账户\n"
        
        # 显示日志
        logs = meta.get("logMessages", [])
        if logs:
            result += f"\n📝 日志消息 (前5条):\n"
            for log in logs[:5]:
                if "Program" in log or "Success" in log:
                    result += f"• {log}\n"
            
            if len(logs) > 5:
                result += f"... 还有 {len(logs) - 5} 条日志\n"
        
        result += f"""
🔍 浏览器: {EXPLORERS['solscan']}/tx/{signature}
"""
        
        return result
        
    except Exception as e:
        logger.error(f"查询交易失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_recent_transactions(address: str) -> str:
    """
    获取地址的最近交易
    输入：Solana 地址
    """
    try:
        if not solana_client.is_valid_address(address):
            return f"无效的 Solana 地址格式: {address}"
        
        # 获取最近的交易签名
        signatures = solana_client.get_signatures_for_address(address, limit=10)
        
        if not signatures:
            return f"地址 {address} 没有交易记录"
        
        result = f"""
📜 最近交易记录

📍 地址: {address}
📊 显示最近 {len(signatures)} 笔交易

交易列表:
"""
        
        for i, sig_info in enumerate(signatures, 1):
            signature = sig_info.get("signature", "")
            slot = sig_info.get("slot", 0)
            err = sig_info.get("err")
            block_time = sig_info.get("blockTime", 0)
            
            status = "✅" if err is None else "❌"
            
            # 格式化时间
            if block_time:
                tx_time = datetime.fromtimestamp(block_time).strftime("%Y-%m-%d %H:%M:%S")
            else:
                tx_time = "未知时间"
            
            result += f"\n{i}. {status} {tx_time}\n"
            result += f"   🔗 {signature[:20]}...\n"
            result += f"   📦 Slot: {slot:,}\n"
        
        result += f"""
🔍 浏览器: {EXPLORERS['solscan']}/account/{address}#transactions
"""
        
        return result
        
    except Exception as e:
        logger.error(f"查询最近交易失败: {str(e)}")
        return f"查询失败: {str(e)}"

# ===== 系统信息工具 =====

def get_slot_info(query: str = "latest") -> str:
    """
    获取 slot 信息
    输入：slot 号或 "latest"（默认）
    """
    try:
        if query == "latest" or not query:
            # 获取当前 slot
            current_slot = solana_client.get_slot()
            slot = current_slot
        else:
            try:
                slot = int(query)
            except:
                return f"无效的 slot 号: {query}"
        
        # 获取 epoch 信息
        epoch_info = solana_client.get_epoch_info()
        
        # 获取 block time
        block_time = None
        try:
            block_time = solana_client.get_block_time(slot)
        except:
            pass
        
        result = f"""
📦 Slot 信息

🔢 Slot: {slot:,}
🔄 当前 Epoch: {epoch_info.get('epoch', 0)}
📊 Epoch 进度: {epoch_info.get('slotIndex', 0):,} / {epoch_info.get('slotsInEpoch', 0):,}
"""
        
        if block_time:
            time_str = datetime.fromtimestamp(block_time).strftime("%Y-%m-%d %H:%M:%S")
            result += f"📅 时间: {time_str}\n"
        
        if query == "latest":
            result += f"📍 状态: 最新 Slot\n"
        
        result += f"""
🔍 浏览器: {EXPLORERS['solscan']}/block/{slot}
"""
        
        return result
        
    except Exception as e:
        logger.error(f"查询 slot 信息失败: {str(e)}")
        return f"查询失败: {str(e)}"

def get_rent_exemption(data_size: str) -> str:
    """
    计算租金豁免所需的最小余额
    输入：数据大小（字节）
    """
    try:
        try:
            size = int(data_size)
        except:
            return f"无效的数据大小: {data_size}"
        
        if size < 0:
            return "数据大小不能为负数"
        
        # 获取租金豁免余额
        lamports = solana_client.get_minimum_balance_for_rent_exemption(size)
        sol = lamports / 1e9
        
        # 计算常见账户类型的租金
        common_accounts = {
            "系统账户 (0 字节)": 0,
            "代币账户 (165 字节)": 165,
            "Mint 账户 (82 字节)": 82,
            "多签账户 (355 字节)": 355,
            "元数据账户 (679 字节)": 679,
        }
        
        result = f"""
🏠 租金豁免计算

📏 数据大小: {size} 字节
💰 所需余额: {sol:.9f} SOL ({lamports:,} lamports)

📊 常见账户类型参考:
"""
        
        for account_type, account_size in common_accounts.items():
            if account_size > 0:
                rent_lamports = solana_client.get_minimum_balance_for_rent_exemption(account_size)
                rent_sol = rent_lamports / 1e9
                result += f"• {account_type}: {rent_sol:.9f} SOL\n"
        
        result += """
💡 说明:
• 租金豁免意味着账户永远不会因余额不足而被删除
• 账户余额必须保持在最小值以上
• 关闭账户时可以回收租金
"""
        
        return result
        
    except Exception as e:
        logger.error(f"计算租金豁免失败: {str(e)}")
        return f"计算失败: {str(e)}"

# ===== 创建工具对象 =====

# 账户相关
sol_balance_tool = Tool(
    name="GetSolanaBalance",
    description="查询 Solana 地址的 SOL 余额。输入：Solana 地址",
    func=get_sol_balance
)

account_info_tool = Tool(
    name="GetSolanaAccountInfo",
    description="获取 Solana 账户详细信息。输入：Solana 地址",
    func=get_account_info
)

# SPL Token 相关
spl_tokens_tool = Tool(
    name="GetSolanaTokens",
    description="查询 Solana 地址持有的所有 SPL 代币。输入：Solana 地址",
    func=get_spl_tokens
)

token_supply_tool = Tool(
    name="GetTokenSupply",
    description="获取 SPL 代币的总供应量。输入：代币 Mint 地址",
    func=get_token_supply
)

token_account_tool = Tool(
    name="GetTokenAccountInfo",
    description="获取代币账户详情。输入：'代币账户地址' 或 '钱包地址 mint地址'",
    func=get_token_account_info
)

# 交易相关
transaction_tool = Tool(
    name="GetSolanaTransaction",
    description="查询 Solana 交易详情。输入：交易签名",
    func=get_transaction
)

recent_transactions_tool = Tool(
    name="GetSolanaRecentTransactions",
    description="获取地址的最近交易记录。输入：Solana 地址",
    func=get_recent_transactions
)

# 系统信息相关
slot_info_tool = Tool(
    name="GetSlotInfo",
    description="获取 Solana slot 信息。输入：slot号 或 'latest'",
    func=get_slot_info
)

rent_exemption_tool = Tool(
    name="GetRentExemption",
    description="计算 Solana 租金豁免所需余额。输入：数据大小（字节）",
    func=get_rent_exemption
)

# 导出所有工具
solana_tools = [
    # 账户相关
    sol_balance_tool,
    account_info_tool,
    
    # SPL Token 相关
    spl_tokens_tool,
    token_supply_tool,
    token_account_tool,
    
    # 交易相关
    transaction_tool,
    recent_transactions_tool,
    
    # 系统信息相关
    slot_info_tool,
    rent_exemption_tool,
]

__all__ = [
    'solana_tools',
    'sol_balance_tool',
    'account_info_tool',
    'spl_tokens_tool',
    'token_supply_tool',
    'token_account_tool',
    'transaction_tool',
    'recent_transactions_tool',
    'slot_info_tool',
    'rent_exemption_tool',
]