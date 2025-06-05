# app/agent/tools/graph/subgraph_registry.py
"""
Subgraph Registry - 简化版
本质上就是 (protocol, network, version) → subgraph_id 的映射缓存
"""

import json
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.agent.tools.graph.graph_config import CACHE_SETTINGS

logger = logging.getLogger(__name__)

@dataclass
class SubgraphRecord:
    """子图记录 - 极简版"""
    # === 查找键 ===
    protocol: str           # "uniswap"
    network: str           # "ethereum" 
    version: Optional[str]  # "v3"
    
    # === 核心值 ===
    subgraph_id: str       # "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    name: str              # "Uniswap V3"
    
    # === 可选元信息 ===
    health_status: str = "unknown"
    last_checked: Optional[datetime] = None
    query_count: int = 0
    
    def __post_init__(self):
        if self.last_checked is None:
            self.last_checked = datetime.now()
    
    @property
    def cache_key(self) -> str:
        """生成缓存键"""
        parts = [self.protocol, self.network]
        if self.version:
            parts.append(self.version)
        return "-".join(parts)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "protocol": self.protocol,
            "network": self.network,
            "version": self.version,
            "subgraph_id": self.subgraph_id,
            "name": self.name,
            "health_status": self.health_status,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "query_count": self.query_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SubgraphRecord':
        """从字典创建"""
        last_checked = None
        if data.get('last_checked'):
            last_checked = datetime.fromisoformat(data['last_checked'])
        
        return cls(
            protocol=data['protocol'],
            network=data['network'],
            version=data.get('version'),
            subgraph_id=data['subgraph_id'],
            name=data['name'],
            health_status=data.get('health_status', 'unknown'),
            last_checked=last_checked,
            query_count=data.get('query_count', 0)
        )

class SubgraphRegistry:
    """子图注册表 - 简化版缓存"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or CACHE_SETTINGS["cache_dir"])
        self.cache_dir.mkdir(exist_ok=True)
        self.registry_file = self.cache_dir / "subgraph_cache.json"
        
        # 内存缓存：key -> SubgraphRecord
        self.cache: Dict[str, SubgraphRecord] = {}
        
        # 加载缓存
        self._load_cache()
    
    def find(self, protocol: str, network: str, version: Optional[str] = None) -> Optional[str]:
        """
        查找 subgraph_id
        
        Args:
            protocol: 协议名 (如 "uniswap")
            network: 网络名 (如 "ethereum")
            version: 版本号 (如 "v3", 可选)
            
        Returns:
            subgraph_id 或 None
        """
        # 1. 精确匹配 (protocol + network + version)
        if version:
            key = f"{protocol}-{network}-{version}"
            if key in self.cache:
                record = self.cache[key]
                record.query_count += 1
                logger.info(f"✅ 精确匹配: {key} → {record.subgraph_id}")
                return record.subgraph_id
        
        # 2. 协议 + 网络匹配 (忽略版本)
        key = f"{protocol}-{network}"
        if key in self.cache:
            record = self.cache[key]
            record.query_count += 1
            logger.info(f"✅ 协议匹配: {key} → {record.subgraph_id}")
            return record.subgraph_id
        
        # 3. 模糊匹配 (找到同协议的任意版本)
        for cache_key, record in self.cache.items():
            if record.protocol == protocol and record.network == network:
                record.query_count += 1
                logger.info(f"✅ 模糊匹配: {cache_key} → {record.subgraph_id}")
                return record.subgraph_id
        
        logger.info(f"❌ 未找到: {protocol}-{network}-{version}")
        return None
    
    def add(self, protocol: str, network: str, subgraph_id: str, name: str, 
            version: Optional[str] = None, **kwargs) -> bool:
        """
        添加新的映射关系
        
        Args:
            protocol: 协议名
            network: 网络名
            subgraph_id: 子图ID
            name: 子图名称
            version: 版本号 (可选)
            **kwargs: 其他可选参数
            
        Returns:
            是否添加成功
        """
        try:
            record = SubgraphRecord(
                protocol=protocol.lower(),
                network=network.lower(),
                version=version.lower() if version else None,
                subgraph_id=subgraph_id,
                name=name,
                **kwargs
            )
            
            cache_key = record.cache_key
            self.cache[cache_key] = record
            
            # 保存到文件
            self._save_cache()
            
            logger.info(f"✅ 添加映射: {cache_key} → {subgraph_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 添加映射失败: {e}")
            return False
    
    def remove(self, protocol: str, network: str, version: Optional[str] = None) -> bool:
        """移除映射关系"""
        parts = [protocol, network]
        if version:
            parts.append(version)
        key = "-".join(parts)
        
        if key in self.cache:
            del self.cache[key]
            self._save_cache()
            logger.info(f"✅ 移除映射: {key}")
            return True
        
        logger.warning(f"⚠️ 未找到要移除的映射: {key}")
        return False
    
    def update_health(self, protocol: str, network: str, health_status: str, 
                     version: Optional[str] = None):
        """更新健康状态"""
        parts = [protocol, network]
        if version:
            parts.append(version)
        key = "-".join(parts)
        
        if key in self.cache:
            self.cache[key].health_status = health_status
            self.cache[key].last_checked = datetime.now()
            self._save_cache()
            logger.info(f"✅ 更新健康状态: {key} → {health_status}")
    
    def get_all_protocols(self) -> List[str]:
        """获取所有协议名称"""
        protocols = set()
        for record in self.cache.values():
            protocols.add(record.protocol)
        return list(protocols)
    
    def get_protocol_networks(self, protocol: str) -> List[str]:
        """获取指定协议支持的网络"""
        networks = set()
        for record in self.cache.values():
            if record.protocol == protocol:
                networks.add(record.network)
        return list(networks)
    
    def get_statistics(self) -> Dict:
        """获取缓存统计信息"""
        total_records = len(self.cache)
        
        # 按协议统计
        protocol_stats = {}
        network_stats = {}
        health_stats = {"unknown": 0, "healthy": 0, "unhealthy": 0}
        
        for record in self.cache.values():
            # 协议统计
            protocol_stats[record.protocol] = protocol_stats.get(record.protocol, 0) + 1
            
            # 网络统计
            network_stats[record.network] = network_stats.get(record.network, 0) + 1
            
            # 健康状态统计
            status = record.health_status
            if status in health_stats:
                health_stats[status] += 1
        
        # 最常用的子图
        most_used = sorted(self.cache.values(), key=lambda x: x.query_count, reverse=True)[:5]
        
        return {
            "total_records": total_records,
            "protocols": protocol_stats,
            "networks": network_stats,
            "health_status": health_stats,
            "most_used": [
                {
                    "key": record.cache_key,
                    "name": record.name,
                    "query_count": record.query_count
                }
                for record in most_used
            ]
        }
    
    def _load_cache(self):
        """从文件加载缓存"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查版本兼容性
                if data.get('version') != '1.0':
                    logger.info("缓存版本不兼容，重新初始化")
                    self._init_default_cache()
                    return
                
                # 加载记录
                for key, record_data in data.get('records', {}).items():
                    try:
                        record = SubgraphRecord.from_dict(record_data)
                        self.cache[key] = record
                    except Exception as e:
                        logger.error(f"加载记录失败 {key}: {e}")
                
                logger.info(f"✅ 加载了 {len(self.cache)} 个缓存记录")
            else:
                # 首次运行，初始化默认缓存
                self._init_default_cache()
                
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            self._init_default_cache()
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            data = {
                'version': '1.0',
                'last_update': datetime.now().isoformat(),
                'records': {
                    key: record.to_dict()
                    for key, record in self.cache.items()
                }
            }
            
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 保存了 {len(self.cache)} 个缓存记录")
            
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def _init_default_cache(self):
        """初始化默认缓存"""
        logger.info("🚀 初始化默认子图缓存...")
        
        # 一些已知的子图映射
        default_mappings = [
            {
                "protocol": "uniswap",
                "network": "ethereum",
                "version": "v3",
                "subgraph_id": "5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
                "name": "Uniswap V3"
            }
        ]
        
        for mapping in default_mappings:
            self.add(**mapping)
        
        logger.info(f"✅ 初始化了 {len(default_mappings)} 个默认映射")