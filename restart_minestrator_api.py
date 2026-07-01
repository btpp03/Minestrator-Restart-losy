#!/usr/bin/env python3
"""
Minestrator 服务器重启 — 纯 API 版（无 Selenium，无 Turnstile）
要求：提供有效的 cf_clearance + api-key cookie（浏览器登录后复制）
"""
import os, sys, time, json, datetime, urllib.request, urllib.parse

# ─── 环境变量 ────────────────────────────────────────────────
SERVER_ID  = os.environ.get("MINESTRATOR_SERVER_ID", "").strip()
API_KEY    = os.environ.get("MINESTRATOR_API_KEY", "").strip()
CF_CLEAR   = os.environ.get("CF_CLEARANCE", "").strip()

_tg = os.environ.get("TG_BOT", "").strip()
TG_CHAT_ID = _tg.split(",")[0].strip() if _tg else ""
TG_TOKEN   = _tg.split(",")[1].strip() if _tg and "," in _tg else ""

API_URL = f"https://mine.sttr.io/server/{SERVER_ID}/poweraction"

# ─── TG 推送 ────────────────────────────────────────────────
def now_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def send_tg(result, detail=''):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("ℹ️ 未配置 TG_BOT，跳过推送")
        return
    msg = (
        f"🎮 Minestrator 重启通知\n"
        f"🕐 运行时间: {now_str()}\n"
        f"🖥 服务器 ID: {SERVER_ID}\n"
        f"📊 结果: {result}\n"
        f"{detail}"
    )
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TG_CHAT_ID, "text": msg}).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15):
            print("📨 TG推送成功")
    except Exception as e:
        print(f"⚠️ TG推送失败：{e}")

# ─── 获取服务器状态 ──────────────────────────────────────────
def get_server_status(cookies: str) -> dict:
    """GET 服务器信息，判断是否需要重启"""
    url = f"https://mine.sttr.io/server/{SERVER_ID}"
    req = urllib.request.Request(url)
    for c in cookies.split(";"):
        req.add_header("Cookie", c.strip())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"⚠️ 获取服务器状态失败：{e}")
        return {}

# ─── 发送重启指令 ────────────────────────────────────────────
def send_restart(cookies: str) -> dict:
    """PUT 电源操作，发送重启指令"""
    payload = json.dumps({"poweraction": "restart"}).encode()
    req = urllib.request.Request(API_URL, data=payload, method="PUT")
    for c in cookies.split(";"):
        req.add_header("Cookie", c.strip())
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("Origin", "https://minestrator.com")
    req.add_header("Referer", f"https://minestrator.com/my/server/{SERVER_ID}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

# ─── 检测服务器在线和利用期限 ────────────────────────────────
def check_server_online(cookies: str) -> str:
    """访问服务器管理页，解析利用期限"""
    url = f"https://minestrator.com/my/server/{SERVER_ID}"
    req = urllib.request.Request(url)
    for c in cookies.split(";"):
        req.add_header("Cookie", c.strip())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode()
            # 简单提取剩余时间（页面里可能显示 "58m" 或 "4h 30m"）
            import re
            match = re.search(r'(\d+[hms]\s*\d*[hms]?)', html)
            if match:
                return match.group(1)
            return "获取失败"
    except Exception as e:
        return f"获取失败: {e}"

# ─── 主流程 ──────────────────────────────────────────────────
def main():
    print(f"{'='*50}")
    print(f" Minestrator 服务器重启 — API 版")
    print(f" 服务器 ID: {SERVER_ID}")
    print(f"{'='*50}")

    # 检查必填变量
    if not SERVER_ID:
        print("❌ 未设置 MINESTRATOR_SERVER_ID")
        send_tg("❌ 失败", "未设置服务器 ID")
        sys.exit(1)

    # 构建 cookie
    cookie_parts = []
    if CF_CLEAR:
        cookie_parts.append(f"cf_clearance={CF_CLEAR}")
    if API_KEY:
        cookie_parts.append(f"api-key={API_KEY}")
    # 尝试从 env 读取额外 cookies
    extra = os.environ.get("MINESTRATOR_COOKIES", "").strip()
    if extra:
        cookie_parts.append(extra)

    cookies = "; ".join(cookie_parts)
    print(f"🍪 Cookie: {cookies[:80]}...")

    if not CF_CLEAR and not API_KEY:
        print("❌ 请设置 CF_CLEARANCE 和 MINESTRATOR_API_KEY")
        send_tg("❌ 失败", "缺少认证 Cookie")
        sys.exit(1)

    # 1. 获取服务器状态
    print(f"\n📡 获取服务器状态...")
    status = get_server_status(cookies)
    if status.get("api", {}).get("code") == 200:
        print(f"✅ 服务器状态获取成功")
    else:
        print(f"⚠️ 状态接口异常: {json.dumps(status, ensure_ascii=False)[:100]}")

    # 2. 发送重启指令
    print(f"\n🔃 发送重启指令...")
    result = send_restart(cookies)
    print(f"📡 API响应：{json.dumps(result, ensure_ascii=False)[:200]}")

    api_code = result.get("api", {}).get("code")
    if api_code == 200:
        print("✅ 重启指令已成功送达！")
        # 获取利用期限
        remaining = check_server_online(cookies)
        detail = f"⏰ 利用期限：{remaining}"
        print(f"⏱️ {detail}")
        send_tg("✅ 重启成功！", detail)
    else:
        error_msg = result.get("api", {}).get("error", "未知错误")
        print(f"❌ API 错误：{error_msg}")
        send_tg("❌ 重启失败", f"错误: {error_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
