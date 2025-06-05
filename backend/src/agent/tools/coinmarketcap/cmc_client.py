# app/agent/tools/coinmarketcap/cmc_client.py
"""
CoinMarketCap API 客户端
处理 API 调用、缓存、错误处理等
"""

import requests
import logging
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.agent.tools.coinmarketcap.cmc_config import (
    BASE_URL, REQUEST_CONFIG, CACHE_CONFIG, ERROR_CONFIG,
    CMC_ERROR_CODES, validate_api_key, get_endpoint_url
)

logger = logging.getLogger(__name__)

class CMCClient:
    """CoinMarketCap API 客户端"""
    
    def __init__(self):
        # 验证 API Key
        if not validate_api_key():
            raise ValueError("CMC_API_KEY 未设置，请在环境变量中配置")
        
        self.session = requests.Session()
        self.session.headers.update(REQUEST_CONFIG.headers)
        
        # 缓存
        self.cache: Dict[str, tuple] = {}  # {cache_key: (data, timestamp)}
        
        # 断路器状态
        self.circuit_breaker = {
            "failures": 0,
            "last_failure": None,
            "is_open": False
        }
        
        # API 调用计数（用于限流）
        self.api_calls = []  # 存储调用时间戳
        
        logger.info("CoinMarketCap 客户端初始化完成")
    
    def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        发送 API 请求
        
        Args:
            endpoint: API 端点
            params: 查询参数
            method: HTTP 方法
            
        Returns:
            API 响应数据
        """
        # 检查断路器
        if self._is_circuit_open():
            raise Exception("API 断路器打开，暂时无法访问")
        
        # 速率限制检查
        self._check_rate_limit()
        
        # 构建 URL
        url = get_endpoint_url(endpoint)
        
        # 缓存检查
        cache_key = self._get_cache_key(endpoint, params)
        if CACHE_CONFIG["enabled"] and method == "GET":
            cached_data = self._get_from_cache(cache_key, endpoint)
            if cached_data:
                logger.debug(f"使用缓存数据: {cache_key}")
                return cached_data
        
        try:
            # 发送请求
            logger.debug(f"发送请求: {method} {url}")
            
            if method == "GET":
                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_CONFIG.timeout
                )
            else:
                response = self.session.post(
                    url,
                    json=params,
                    timeout=REQUEST_CONFIG.timeout
                )
            
            # 记录 API 调用
            self.api_calls.append(datetime.now())
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = CMC_ERROR_CODES.get(
                    response.status_code, 
                    f"未知错误: {response.status_code}"
                )
                
                # 尝试获取详细错误信息
                try:
                    error_data = response.json()
                    if "status" in error_data:
                        error_msg = f"{error_msg} - {error_data['status'].get('error_message', '')}"
                except:
                    pass
                
                raise requests.HTTPError(error_msg)
            
            # 解析响应
            data = response.json()
            
            # 检查 API 返回的状态
            if "status" in data and data["status"].get("error_code") != 0:
                raise Exception(f"API 错误: {data['status'].get('error_message', '未知错误')}")
            
            # 重置断路器
            self._reset_circuit_breaker()
            
            # 缓存结果
            if CACHE_CONFIG["enabled"] and method == "GET":
                self._cache_data(cache_key, data, endpoint)
            
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            self._record_failure()
            raise Exception("请求超时")
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP 错误: {str(e)}")
            self._record_failure()
            
            # 如果是 429 错误，需要特殊处理
            if response.status_code == 429:
                # 等待更长时间
                time.sleep(60)  # 等待1分钟
                
            raise
            
        except Exception as e:
            logger.error(f"请求失败: {str(e)}")
            self._record_failure()
            raise
    
    def get_cryptocurrency_map(
        self,
        listing_status: str = "active",
        start: int = 1,
        limit: int = 100,
        sort: str = "cmc_rank",
        symbol: Optional[str] = None,
        aux: str = "platform,first_historical_data,last_historical_data,is_active"
    ) -> Dict[str, Any]:
        """
        获取加密货币 ID 映射
        
        Args:
            listing_status: active, inactive, untracked
            start: 起始位置
            limit: 返回数量
            sort: 排序字段
            symbol: 筛选特定符号
            aux: 辅助字段
            
        Returns:
            加密货币映射数据
        """
        params = {
            "listing_status": listing_status,
            "start": start,
            "limit": limit,
            "sort": sort,
            "aux": aux
        }
        
        if symbol:
            params["symbol"] = symbol
        
        return self._make_request("crypto_map", params)
    
    def get_cryptocurrency_info(
        self,
        ids: Optional[str] = None,
        slugs: Optional[str] = None,
        symbols: Optional[str] = None,
        addresses: Optional[str] = None,
        aux: str = "urls,logo,description,tags,platform,date_added,notice"
    ) -> Dict[str, Any]:
        """
        获取加密货币详细信息
        
        Args:
            ids: CMC ID 列表（逗号分隔）
            slugs: slug 列表（逗号分隔）
            symbols: 符号列表（逗号分隔）
            addresses: 合约地址列表（逗号分隔）
            aux: 辅助字段
            
        Returns:
            加密货币详细信息
        """
        params = {"aux": aux}
        
        # 至少需要一个标识符
        if ids:
            params["id"] = ids
        elif slugs:
            params["slug"] = slugs
        elif symbols:
            params["symbol"] = symbols
        elif addresses:
            params["address"] = addresses
        else:
            raise ValueError("至少需要提供一个标识符: ids, slugs, symbols 或 addresses")
        
        return self._make_request("crypto_info", params)
    
    def get_cryptocurrency_quotes_latest(
        self,
        ids: Optional[str] = None,
        slugs: Optional[str] = None,
        symbols: Optional[str] = None,
        convert: str = "USD",
        aux: str = "num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,is_active,is_fiat"
    ) -> Dict[str, Any]:
        """
        获取加密货币最新价格
        
        Args:
            ids: CMC ID 列表
            slugs: slug 列表
            symbols: 符号列表
            convert: 转换货币
            aux: 辅助字段
            
        Returns:
            最新价格数据
        """
        params = {
            "convert": convert,
            "aux": aux
        }
        
        if ids:
            params["id"] = ids
        elif slugs:
            params["slug"] = slugs
        elif symbols:
            params["symbol"] = symbols
        else:
            raise ValueError("至少需要提供一个标识符")
        
        return self._make_request("crypto_quotes_latest", params)
    
    def get_cryptocurrency_listings_latest(
        self,
        start: int = 1,
        limit: int = 100,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        market_cap_min: Optional[float] = None,
        market_cap_max: Optional[float] = None,
        volume_24h_min: Optional[float] = None,
        volume_24h_max: Optional[float] = None,
        circulating_supply_min: Optional[float] = None,
        circulating_supply_max: Optional[float] = None,
        percent_change_24h_min: Optional[float] = None,
        percent_change_24h_max: Optional[float] = None,
        convert: str = "USD",
        sort: str = "market_cap",
        sort_dir: str = "desc",
        cryptocurrency_type: str = "all",
        tag: Optional[str] = None,
        aux: str = "num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply"
    ) -> Dict[str, Any]:
        """
        获取最新加密货币列表
        
        Args:
            start: 起始位置
            limit: 返回数量
            price_min/max: 价格范围
            market_cap_min/max: 市值范围
            volume_24h_min/max: 24小时交易量范围
            circulating_supply_min/max: 流通量范围
            percent_change_24h_min/max: 24小时涨跌幅范围
            convert: 转换货币
            sort: 排序字段
            sort_dir: 排序方向
            cryptocurrency_type: 类型 (all, coins, tokens)
            tag: 标签筛选
            aux: 辅助字段
            
        Returns:
            加密货币列表数据
        """
        params = {
            "start": start,
            "limit": limit,
            "convert": convert,
            "sort": sort,
            "sort_dir": sort_dir,
            "cryptocurrency_type": cryptocurrency_type,
            "aux": aux
        }
        
        # 添加可选参数
        if price_min is not None:
            params["price_min"] = price_min
        if price_max is not None:
            params["price_max"] = price_max
        if market_cap_min is not None:
            params["market_cap_min"] = market_cap_min
        if market_cap_max is not None:
            params["market_cap_max"] = market_cap_max
        if volume_24h_min is not None:
            params["volume_24h_min"] = volume_24h_min
        if volume_24h_max is not None:
            params["volume_24h_max"] = volume_24h_max
        if circulating_supply_min is not None:
            params["circulating_supply_min"] = circulating_supply_min
        if circulating_supply_max is not None:
            params["circulating_supply_max"] = circulating_supply_max
        if percent_change_24h_min is not None:
            params["percent_change_24h_min"] = percent_change_24h_min
        if percent_change_24h_max is not None:
            params["percent_change_24h_max"] = percent_change_24h_max
        if tag:
            params["tag"] = tag
        
        return self._make_request("crypto_listings_latest", params)
    
    def get_global_metrics_latest(
        self,
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取全球加密货币市场指标
        
        Args:
            convert: 转换货币
            
        Returns:
            全球市场数据
        """
        params = {"convert": convert}
        return self._make_request("global_metrics_latest", params)
    
    def get_trending_latest(
        self,
        start: int = 1,
        limit: int = 10,
        time_period: str = "24h",
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取趋势加密货币
        
        Args:
            start: 起始位置
            limit: 返回数量
            time_period: 时间周期 (24h, 30d, 7d)
            convert: 转换货币
            
        Returns:
            趋势数据
        """
        params = {
            "start": start,
            "limit": limit,
            "time_period": time_period,
            "convert": convert
        }
        return self._make_request("crypto_trending_latest", params)
    
    def get_trending_gainers_losers(
        self,
        start: int = 1,
        limit: int = 10,
        time_period: str = "24h",
        convert: str = "USD",
        sort: str = "percent_change_24h",
        sort_dir: str = "desc"
    ) -> Dict[str, Any]:
        """
        获取涨跌幅排行
        
        Args:
            start: 起始位置
            limit: 返回数量
            time_period: 时间周期
            convert: 转换货币
            sort: 排序字段
            sort_dir: 排序方向 (desc=涨幅榜, asc=跌幅榜)
            
        Returns:
            涨跌幅数据
        """
        params = {
            "start": start,
            "limit": limit,
            "time_period": time_period,
            "convert": convert,
            "sort": sort,
            "sort_dir": sort_dir
        }
        return self._make_request("crypto_trending_gainers_losers", params)
    
    def get_price_conversion(
        self,
        amount: float,
        symbol: Optional[str] = None,
        id: Optional[int] = None,
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        价格转换工具
        
        Args:
            amount: 数量
            symbol: 源币种符号
            id: 源币种 CMC ID
            convert: 目标币种
            
        Returns:
            转换结果
        """
        params = {
            "amount": amount,
            "convert": convert
        }
        
        if symbol:
            params["symbol"] = symbol
        elif id:
            params["id"] = id
        else:
            raise ValueError("需要提供 symbol 或 id")
        
        return self._make_request("price_conversion", params)
    
    def get_key_info(self) -> Dict[str, Any]:
        """
        获取 API Key 信息
        
        Returns:
            API Key 使用情况
        """
        return self._make_request("key_info")
    
    # ===== 缓存相关方法 =====
    
    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        if params:
            param_str = urlencode(sorted(params.items()))
            return f"{endpoint}:{param_str}"
        return endpoint
    
    def _get_from_cache(self, key: str, endpoint: str) -> Optional[Dict]:
        """从缓存获取数据"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            
            # 获取该类型数据的 TTL
            ttl = CACHE_CONFIG["ttl"]
            for data_type, type_ttl in CACHE_CONFIG["ttl_by_type"].items():
                if data_type in endpoint:
                    ttl = type_ttl
                    break
            
            # 检查是否过期
            if datetime.now() - timestamp < timedelta(seconds=ttl):
                return data
            else:
                # 删除过期缓存
                del self.cache[key]
        
        return None
    
    def _cache_data(self, key: str, data: Dict, endpoint: str):
        """缓存数据"""
        self.cache[key] = (data, datetime.now())
        
        # 清理过多的缓存
        if len(self.cache) > CACHE_CONFIG["max_size"]:
            self._cleanup_cache()
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp) in self.cache.items():
            if now - timestamp > timedelta(seconds=CACHE_CONFIG["ttl"]):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        logger.debug(f"清理了 {len(expired_keys)} 个过期缓存")
    
    # ===== 断路器相关方法 =====
    
    def _is_circuit_open(self) -> bool:
        """检查断路器是否打开"""
        if not ERROR_CONFIG["circuit_breaker_enabled"]:
            return False
        
        if not self.circuit_breaker["is_open"]:
            return False
        
        # 检查恢复时间
        if self.circuit_breaker["last_failure"]:
            recovery_time = timedelta(seconds=ERROR_CONFIG["recovery_timeout"])
            if datetime.now() - self.circuit_breaker["last_failure"] > recovery_time:
                logger.info("断路器恢复")
                self.circuit_breaker["is_open"] = False
                self.circuit_breaker["failures"] = 0
                return False
        
        return True
    
    def _record_failure(self):
        """记录失败"""
        self.circuit_breaker["failures"] += 1
        self.circuit_breaker["last_failure"] = datetime.now()
        
        if self.circuit_breaker["failures"] >= ERROR_CONFIG["failure_threshold"]:
            logger.warning(f"断路器打开: 连续失败 {self.circuit_breaker['failures']} 次")
            self.circuit_breaker["is_open"] = True
    
    def _reset_circuit_breaker(self):
        """重置断路器"""
        if self.circuit_breaker["failures"] > 0:
            logger.debug("重置断路器")
            self.circuit_breaker["failures"] = 0
            self.circuit_breaker["is_open"] = False
    
    # ===== 速率限制 =====
    
    def _check_rate_limit(self):
        """检查速率限制"""
        # 清理过期的调用记录
        now = datetime.now()
        self.api_calls = [
            call_time for call_time in self.api_calls
            if now - call_time < timedelta(days=1)
        ]
        
        # 检查是否超过限制
        if len(self.api_calls) >= REQUEST_CONFIG.daily_limit:
            logger.warning(f"接近 API 调用限制: {len(self.api_calls)}/{REQUEST_CONFIG.daily_limit}")
            # 可以选择抛出异常或等待
            # raise Exception("超过每日 API 调用限制")
        
        # 基本的速率限制
        time.sleep(REQUEST_CONFIG.rate_limit_delay)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        now = datetime.now()
        
        # 计算各时间段的调用次数
        calls_1h = sum(1 for t in self.api_calls if now - t < timedelta(hours=1))
        calls_24h = len(self.api_calls)
        
        return {
            "cache_size": len(self.cache),
            "api_calls_1h": calls_1h,
            "api_calls_24h": calls_24h,
            "daily_limit": REQUEST_CONFIG.daily_limit,
            "circuit_breaker": {
                "is_open": self.circuit_breaker["is_open"],
                "failures": self.circuit_breaker["failures"]
            }
        }

    def get_cryptocurrency_ohlcv_latest(
        self,
        ids: Optional[str] = None,
        symbols: Optional[str] = None,
        convert: str = "USD",
        time_period: str = "daily",
        count: int = 10,
        interval: str = "daily",
        time_start: Optional[str] = None,
        time_end: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取加密货币 OHLCV 数据
        
        Args:
            ids: CMC ID 列表
            symbols: 符号列表
            convert: 转换货币
            time_period: 时间周期
            count: 数据点数量
            interval: 时间间隔
            time_start: 开始时间
            time_end: 结束时间
            
        Returns:
            OHLCV 数据
        """
        params = {
            "convert": convert,
            "count": count,
            "interval": interval
        }
        
        if ids:
            params["id"] = ids
        elif symbols:
            params["symbol"] = symbols
        else:
            raise ValueError("需要提供 ids 或 symbols")
        
        if time_start:
            params["time_start"] = time_start
        if time_end:
            params["time_end"] = time_end
        
        return self._make_request("crypto_ohlcv_latest", params)

    def get_cryptocurrency_market_pairs(
        self,
        ids: Optional[str] = None,
        slugs: Optional[str] = None,
        symbols: Optional[str] = None,
        start: int = 1,
        limit: int = 100,
        aux: str = "num_market_pairs,category,fee_type",
        matched: Optional[str] = None,
        category: str = "all",
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取加密货币交易对信息
        
        Args:
            ids: CMC ID
            slugs: slug
            symbols: 符号
            start: 起始位置
            limit: 返回数量
            aux: 辅助字段
            matched: 匹配的报价资产
            category: 类别 (all, spot, derivatives)
            convert: 转换货币
            
        Returns:
            交易对数据
        """
        params = {
            "start": start,
            "limit": limit,
            "aux": aux,
            "category": category,
            "convert": convert
        }
        
        if ids:
            params["id"] = ids
        elif slugs:
            params["slug"] = slugs
        elif symbols:
            params["symbol"] = symbols
        else:
            raise ValueError("需要提供标识符")
        
        if matched:
            params["matched"] = matched
        
        return self._make_request("crypto_market_pairs", params)

    def get_cryptocurrency_categories(
        self,
        start: int = 1,
        limit: int = 100,
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取所有加密货币分类
        
        Args:
            start: 起始位置
            limit: 返回数量
            convert: 转换货币
            
        Returns:
            分类列表
        """
        params = {
            "start": start,
            "limit": limit,
            "convert": convert
        }
        
        return self._make_request("crypto_categories", params)

    def get_cryptocurrency_category(
        self,
        id: str,
        start: int = 1,
        limit: int = 100,
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取特定分类的加密货币
        
        Args:
            id: 分类 ID 或 slug
            start: 起始位置
            limit: 返回数量
            convert: 转换货币
            
        Returns:
            分类内的加密货币
        """
        params = {
            "id": id,
            "start": start,
            "limit": limit,
            "convert": convert
        }
        
        return self._make_request("crypto_category", params)

    def get_cryptocurrency_airdrops(
        self,
        start: int = 1,
        limit: int = 100,
        status: str = "ongoing",
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取空投信息
        
        Args:
            start: 起始位置
            limit: 返回数量
            status: 状态 (ongoing, ended, upcoming)
            convert: 转换货币
            
        Returns:
            空投列表
        """
        params = {
            "start": start,
            "limit": limit,
            "status": status,
            "convert": convert
        }
        
        return self._make_request("crypto_airdrops", params)

    def get_cryptocurrency_price_performance(
        self,
        ids: Optional[str] = None,
        slugs: Optional[str] = None,
        symbols: Optional[str] = None,
        time_period: str = "all_time",
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取价格表现统计
        
        Args:
            ids: CMC ID 列表
            slugs: slug 列表
            symbols: 符号列表
            time_period: 时间周期
            convert: 转换货币
            
        Returns:
            价格表现数据
        """
        params = {
            "time_period": time_period,
            "convert": convert
        }
        
        if ids:
            params["id"] = ids
        elif slugs:
            params["slug"] = slugs
        elif symbols:
            params["symbol"] = symbols
        else:
            raise ValueError("需要提供标识符")
        
        return self._make_request("crypto_price_performance", params)

    def get_exchange_map(
        self,
        listing_status: str = "active",
        start: int = 1,
        limit: int = 100,
        sort: str = "volume_24h",
        aux: str = "first_historical_data,last_historical_data,is_active,status"
    ) -> Dict[str, Any]:
        """
        获取交易所 ID 映射
        
        Args:
            listing_status: 状态
            start: 起始位置
            limit: 返回数量
            sort: 排序字段
            aux: 辅助字段
            
        Returns:
            交易所映射数据
        """
        params = {
            "listing_status": listing_status,
            "start": start,
            "limit": limit,
            "sort": sort,
            "aux": aux
        }
        
        return self._make_request("exchange_map", params)

    def get_exchange_info(
        self,
        ids: Optional[str] = None,
        slugs: Optional[str] = None,
        aux: str = "urls,logo,description,date_launched,notice,status"
    ) -> Dict[str, Any]:
        """
        获取交易所详细信息
        
        Args:
            ids: 交易所 ID 列表
            slugs: slug 列表
            aux: 辅助字段
            
        Returns:
            交易所详细信息
        """
        params = {"aux": aux}
        
        if ids:
            params["id"] = ids
        elif slugs:
            params["slug"] = slugs
        else:
            raise ValueError("需要提供 ids 或 slugs")
        
        return self._make_request("exchange_info", params)

    def get_exchange_listings_latest(
        self,
        start: int = 1,
        limit: int = 100,
        sort: str = "volume_24h",
        sort_dir: str = "desc",
        market_type: str = "all",
        category: str = "all",
        aux: str = "num_market_pairs,category,fee_type",
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取最新交易所列表
        
        Args:
            start: 起始位置
            limit: 返回数量
            sort: 排序字段
            sort_dir: 排序方向
            market_type: 市场类型
            category: 分类
            aux: 辅助字段
            convert: 转换货币
            
        Returns:
            交易所列表
        """
        params = {
            "start": start,
            "limit": limit,
            "sort": sort,
            "sort_dir": sort_dir,
            "market_type": market_type,
            "category": category,
            "aux": aux,
            "convert": convert
        }
        
        return self._make_request("exchange_listings_latest", params)

    def get_exchange_market_pairs(
        self,
        ids: Optional[str] = None,
        slugs: Optional[str] = None,
        start: int = 1,
        limit: int = 100,
        aux: str = "num_market_pairs,category,fee_type",
        matched: Optional[str] = None,
        category: str = "all",
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """
        获取交易所的交易对
        
        Args:
            ids: 交易所 ID
            slugs: slug
            start: 起始位置
            limit: 返回数量
            aux: 辅助字段
            matched: 匹配的资产
            category: 分类
            convert: 转换货币
            
        Returns:
            交易对数据
        """
        params = {
            "start": start,
            "limit": limit,
            "aux": aux,
            "category": category,
            "convert": convert
        }
        
        if ids:
            params["id"] = ids
        elif slugs:
            params["slug"] = slugs
        else:
            raise ValueError("需要提供 ids 或 slugs")
        
        if matched:
            params["matched"] = matched
        
        return self._make_request("exchange_market_pairs", params)

    def get_fiat_map(
        self,
        start: int = 1,
        limit: int = 100,
        sort: str = "id",
        include_metals: bool = False
    ) -> Dict[str, Any]:
        """
        获取法币列表
        
        Args:
            start: 起始位置
            limit: 返回数量
            sort: 排序字段
            include_metals: 是否包含贵金属
            
        Returns:
            法币列表
        """
        params = {
            "start": start,
            "limit": limit,
            "sort": sort,
            "include_metals": include_metals
        }
        
        return self._make_request("fiat_map", params)

    def get_blockchain_statistics(
        self,
        symbols: str
    ) -> Dict[str, Any]:
        """
        获取区块链统计数据
        
        Args:
            symbols: 符号列表
            
        Returns:
            区块链统计数据
        """
        params = {
            "symbol": symbols
        }
        
        return self._make_request("blockchain_statistics_latest", params)

# 全局客户端实例
cmc_client = CMCClient()