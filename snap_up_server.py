import requests
import json
import time  
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from html import unescape

CONFIG = {
    "cookies_file": "cookies.json",
    "activity_page_url": "https://cloud.tencent.com/act/pro/warmup-202606?fromSource=gwzcw.10216579.10216579.10216579&utm_medium=cpc&utm_id=gwzcw.10216579.10216579.10216579&page=featured-202604&s_source=https%3A%2F%2Fcloud.tencent.com%2Fact%2Fpro%2Fdouble12-2025",
    "goods_type": "bundle_budget_mc_lg4_01",
    "target_product_name": "lighthouse_v5",
    "target_goods_keyword": "轻量 4核4G3M",
    "region_ids": [1, 4, 8],
    "server_time_url": "https://cloud.tencent.com/act/pro/double12-2025",
    "check_available_url": "https://act-api.cloud.tencent.com/dianshi/check-available",
    "do_goods_url": "https://act-api.cloud.tencent.com/dianshi/do-goods",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "poll_interval_seconds": 1,
}
activity_config = None

# 重要：请先运行get_cookies.py获取登录后的cookies，并确保cookies.json文件存在且格式正确
session = requests.Session()
skey = None

# 加载Cookie（确保cookies.json文件格式正确）
with open(CONFIG["cookies_file"], "r", encoding="utf-8") as f:
    cookies = json.load(f)
    for cookie in cookies:
        # 兼容Cookie字段缺失的情况
        session.cookies.set(
            cookie.get('name', ''),
            cookie.get('value', ''),
            domain=cookie.get('domain', ''),
            path=cookie.get('path', '/')  # 默认路径为/
        )
        if cookie.get("name") == "skey" and cookie.get("domain") == ".cloud.tencent.com":
            skey = cookie.get("value")

if not skey:
    raise RuntimeError(f"未在 {CONFIG['cookies_file']} 中找到 .cloud.tencent.com 的 skey，请重新运行 get_cookies.py")


def make_csrf_token(skey_value):
    token = 5381
    for char in skey_value:
        token += (token << 5) + ord(char)
    return str(token & 0x7fffffff)


headers = {
    "x-csrf-token": make_csrf_token(skey),
    "Origin": "https://cloud.tencent.com",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": CONFIG["user_agent"],
    "referer": CONFIG["activity_page_url"]
}


def extract_next_data(html):
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
        html,
        re.S,
    )
    if not match:
        raise RuntimeError("活动页中未找到 __NEXT_DATA__ 配置")
    return json.loads(unescape(match.group(1)))


def get_region_ids_from_limits(limits):
    region_limit = limits.get("regionId", {})
    if "option" in region_limit:
        return sort_region_ids(region_limit["option"])

    constraint = region_limit.get("constraint", {})
    values = constraint.get("value", {})
    for value in values.values():
        if isinstance(value, list):
            return sort_region_ids(value)
    return CONFIG["region_ids"]


def sort_region_ids(region_ids):
    order = {region_id: index for index, region_id in enumerate(CONFIG["region_ids"])}
    return sorted(region_ids, key=lambda region_id: order.get(region_id, len(order)))


def choose_target_sale(flash_result, now=None):
    beijing_tz = timezone(timedelta(hours=8))
    now = now or datetime.now(beijing_tz)
    today = now.strftime("%Y-%m-%d")

    candidates = []
    for date, groups in flash_result.items():
        for group in groups or []:
            for sale in group.get("sales", []) or []:
                goods = sale.get("$goods", {})
                text = " ".join(
                    str(part)
                    for part in [
                        sale.get("goods_name", ""),
                        sale.get("product_name", ""),
                        goods.get("name", ""),
                        goods.get("product_name", ""),
                    ]
                )
                goods_param = sale.get("defaultOrderParam") or sale.get("defaultGoodsParam") or {}
                if sale.get("product_name") != CONFIG["target_product_name"]:
                    continue
                if CONFIG["target_goods_keyword"] not in text:
                    continue
                if goods_param.get("type") != CONFIG["goods_type"]:
                    continue

                status = group.get("dynamic_status_cn", "")
                status_rank = 0 if status == "进行中" else 1 if status == "未开始" else 2
                date_rank = 0 if date == today else 1
                candidates.append((date_rank, status_rank, date, group, sale))

    if not candidates:
        raise RuntimeError("未在活动页配置中找到目标轻量应用服务器商品")

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidates[0]


def sync_activity_config():
    global activity_config
    resp = session.get(CONFIG["activity_page_url"], headers=headers, timeout=15)
    resp.raise_for_status()
    next_data = extract_next_data(resp.text)
    page_props = next_data["props"]["pageProps"]
    flash_result = page_props["activityData"]["twoDaySeckillState"]["flashResult"]
    date, group, sale = choose_target_sale(flash_result)[2:]
    goods = sale.get("$goods", {})
    goods_param = dict(sale.get("defaultOrderParam") or sale.get("defaultGoodsParam") or {})
    region_ids = get_region_ids_from_limits(goods.get("limits", {}))

    activity_config = {
        "date": date,
        "status": group.get("dynamic_status_cn", ""),
        "activity_id": group["activity_id"],
        "act_id": sale["act_id"],
        "business_id": group["id"],
        "goods_name": sale.get("goods_name", ""),
        "goods_param": goods_param,
        "region_ids": region_ids,
    }
    print(
        "🔄 已同步活动配置："
        f"{activity_config['goods_name']}，场次={activity_config['date']} {activity_config['status']}，"
        f"activity_id={activity_config['activity_id']}，act_id={activity_config['act_id']}，"
        f"business_id={activity_config['business_id']}，region_ids={activity_config['region_ids']}"
    )
    return activity_config


def get_activity_config():
    return activity_config or sync_activity_config()


def build_check_data():
    config = get_activity_config()
    return {
        "activity_id": config["activity_id"],
        "goods": [
            {
                "act_id": config["act_id"],
                "region_id": config["region_ids"],
            }
        ],
        "preview": 0,
    }

# =================== 检查是否可抢购 =================== #

def check_available():
    """
    检查库存，返回有货的地域ID（无货返回None）
    """
    try:
        resp = session.post(
            CONFIG["check_available_url"],
            json=build_check_data(),
            headers=headers,
            timeout=10  # 新增超时控制
        )
        resp.raise_for_status()  # 抛出HTTP错误（4xx/5xx）
        result = resp.json()
    except Exception as e:
        print(f"❌ 库存检查接口调用失败：{str(e)}")
        return None

    # 校验接口返回是否正常
    if result.get("code") != 0 or result.get("msg") != "ok":
        print(f"❌ 库存检查接口返回异常：{json.dumps(result, ensure_ascii=False)}")
        return None

    # 校验商品基础权限（修复：逻辑反转）
    goods_data = result.get("data", [{}])[0]
    if goods_data.get("available") != 1 or goods_data.get("user_available") != 1:
        print("❌ 商品无购买权限/整体无货")
        return None

    # 安全获取地域库存（修复：避免KeyError）
    quota = goods_data.get("quota") or {}
    # 优先级：1（华北）→4（华东）→8（华南）
    region_map = {
        1: "华北",
        4: "华东",
        8: "华南",
    }
    for region_id, region_name in region_map.items():
        # 逐层get，避免字段缺失报错
        available = quota.get(str(region_id), {})\
                        .get(CONFIG["goods_type"], {})\
                        .get("available", 0)
        if available > 0:
            print(f"✅ 检测到{region_name}（region_id={region_id}）有库存！")
            return region_id

    # 所有地域无货
    print("❌ 所有目标地域均无库存")
    return None


# =================== 立即购买（核心下单） =================== #
def buy_now(region_id):
    """
    调用do-goods接口完成购买
    :param region_id: 有货的地域ID
    """
    config = get_activity_config()
    goods_param = dict(config["goods_param"])
    goods_param["regionId"] = region_id
    do_data = {
        "activity_id": config["activity_id"],
        "agent_channel": {
            "fromChannel": "",
            "fromSales": "",
            "isAgentClient": False,
            "fromUrl": CONFIG["activity_page_url"]
        },
        
        "business": {
            "id": config["business_id"],
            "from": "lightningDeals"
        },
        "goods": [
            {
                "act_id": config["act_id"],
                "type": CONFIG["goods_type"],
                "goods_param": goods_param
            }
        ],
        
        "preview": 0
    }
    try:
        # 修复：传do_data而非pay_data
        resp = session.post(
            CONFIG["do_goods_url"],
            json=do_data,  # 关键修复：使用正确的购买参数
            headers=headers,
            timeout=10
        )
        print(f"🎯 核心购买接口返回：{resp.text}")
        return resp.json()
    except Exception as e:
        print(f"❌ 核心购买接口调用失败：{str(e)}")
        return None
    
def get_server_time():
    """获取服务器时间，校准本地时间"""
    url = CONFIG["server_time_url"]
    response = requests.head(url, timeout=5)
    server_time = response.headers.get("Date")

    if server_time:
        dt = datetime.strptime(server_time, "%a, %d %b %Y %H:%M:%S GMT").replace(
            tzinfo=timezone.utc
        )
        beijing_time = dt.astimezone(timezone(timedelta(hours=8)))
        timestamp_ms = int(beijing_time.timestamp() * 1000)
        print(f"服务器时间(GMT): {dt}")
        print(f"北京时间: {beijing_time}")
        print(f"时间戳(毫秒): {timestamp_ms}")
        return timestamp_ms
    else:
        print("未获取到服务器时间")
        return None


def get_next_seckill_timestamp(now=None):
    """自动选择最近的秒杀时间点：每天 10:00 / 15:00，超过 5 分钟则切到下一个时间点。"""
    beijing_tz = timezone(timedelta(hours=8))
    now = now or datetime.now(beijing_tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=beijing_tz)

    morning = now.replace(hour=10, minute=0, second=0, microsecond=0)
    afternoon = now.replace(hour=15, minute=0, second=0, microsecond=0)
    next_morning = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    if now <= morning + timedelta(minutes=5):
        return morning
    if now <= afternoon + timedelta(minutes=5):
        return afternoon
    return next_morning

def buy_now_concurrent(region_ids):
    """并发抢购多个地域"""
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(buy_now, rid) for rid in region_ids]
        for future in futures:
            result = future.result()
            if isinstance(result, dict) and result.get("code") == 0:
                print(f"🎉 抢购成功！地域ID: {result.get('region_id', '未知')}")
                return result
            # 也可以打印失败信息，方便调试
            else:
                region_id = result.get("region_id", "未知") if isinstance(result, dict) else "未知"
                print(f"地域 {region_id} 抢购失败: {result}")
    return None

# =================== 主程序 =================== #
if __name__ == "__main__":
    print("🚀 启动腾讯云抢购脚本...")
    activity = sync_activity_config()
    region_ids = activity["region_ids"]
    seckill_dt = get_next_seckill_timestamp()
    SECKILL_TIMESTAMP = int(seckill_dt.timestamp() * 1000)
    print(f"📅 自动选择的秒杀时间：{seckill_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        current_time = get_server_time()
        if current_time is None:
            time.sleep(3)
            continue
        if current_time >= SECKILL_TIMESTAMP:
            print("秒杀开始！")
            buy_now_concurrent(region_ids)
            break
        else:
            print(f"⏳ 当前时间未到达秒杀时间，当前服务器时间: {current_time}, 秒杀时间: {SECKILL_TIMESTAMP}")
            time.sleep(CONFIG["poll_interval_seconds"])
