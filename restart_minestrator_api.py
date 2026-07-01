#!/usr/bin/env python3
"""
Minestrator API restart — pure requests + SOCKS5 proxy
"""
import os, sys, json, datetime, requests

SERVER_ID  = os.environ.get("MINESTRATOR_SERVER_ID", "").strip()
AUTH_TOKEN = os.environ.get("MINESTRATOR_AUTH", "").strip()
PROXY_URL  = os.environ.get("MINESTRATOR_PROXY", "").strip()

_tg = os.environ.get("TG_BOT", "").strip()
TG_CHAT_ID = _tg.split(",")[0].strip() if _tg else ""
TG_TOKEN   = _tg.split(",")[1].strip() if _tg and "," in _tg else ""

API_URL = f"https://mine.sttr.io/server/{SERVER_ID}/poweraction"

# Session with optional SOCKS5 proxy
sess = requests.Session()
if PROXY_URL:
    sess.proxies.update({"http": PROXY_URL, "https": PROXY_URL})

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://minestrator.com",
    "Referer": f"https://minestrator.com/my/server/{SERVER_ID}",
}

def get_account_name():
    try:
        r = sess.get("https://mine.sttr.io/user/326193", headers=HEADERS, timeout=10)
        data = r.json()
        return data.get("api", {}).get("data", {}).get("user", {}).get("datas", {}).get("pseudo", "unknown")
    except:
        return "unknown"

ACCOUNT = get_account_name()

REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "minestrator")  # btpp03/Minestrator-Restart-losy

def send_tg(result, detail=''):
    if not TG_TOKEN or not TG_CHAT_ID: return
    msg = (
        f"[{REPO_NAME}] 🎮 Minestrator 重启通知\n🕐 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👤 账号: {ACCOUNT}\n🖥 服务器: {SERVER_ID}\n📊 结果: {result}\n{detail}"
    )
    try:
        sess.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                  json={"chat_id": TG_CHAT_ID, "text": msg}, timeout=15)
        print("📨 TG推送成功")
    except Exception as e:
        print(f"⚠️ TG推送失败：{e}")

def main():
    print(f"{'='*50}")
    print(f" Minestrator 重启 — API 版")
    print(f" 账号: {ACCOUNT}")
    print(f" Server: {SERVER_ID}")
    print(f" Proxy: {'✅' if PROXY_URL else '❌'} {PROXY_URL[:50] if PROXY_URL else ''}")
    print(f"{'='*50}")

    if not SERVER_ID or not AUTH_TOKEN:
        print("❌ 缺少 SERVER_ID 或 AUTH")
        sys.exit(1)

    print(f"\n📡 发送重启指令...")
    resp = sess.put(API_URL, json={"poweraction": "restart"}, headers=HEADERS, timeout=20)
    result = resp.json()
    print(f"📡 HTTP {resp.status_code}: {json.dumps(result, ensure_ascii=False)[:200]}")

    code = result.get("api", {}).get("code")
    if code == 200:
        print("✅ 重启成功！")
        send_tg("✅ 重启成功！", "")
    else:
        err = result.get("api", {}).get("error", "未知错误")
        print(f"❌ 失败：{err}")
        send_tg("❌ 重启失败", f"错误: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
