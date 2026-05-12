#!/usr/bin/env python3
"""Minestrator Auto-Restart - DrissionPage version (handles Turnstile better)."""
import os, sys, time, json, re
from DrissionPage import ChromiumPage, ChromiumOptions

EMAIL = os.environ.get("MINESTRATOR_ACCOUNT", "").split(",")[0].strip()
PASSWORD = os.environ.get("MINESTRATOR_ACCOUNT", "").split(",")[1].strip() if "," in os.environ.get("MINESTRATOR_ACCOUNT", "") else ""
SERVER_ID = os.environ.get("MINESTRATOR_SERVER_ID", "").strip()
AUTH_TOKEN = os.environ.get("MINESTRATOR_AUTH", "").strip()
_proxy = os.environ.get("GOST_PROXY", "").strip()
_local_proxy = os.environ.get("LOCAL_PROXY", "").strip()
PROXY = _local_proxy if _local_proxy else ("http://127.0.0.1:8080" if _proxy else "")

_tg = os.environ.get("TG_BOT", "").strip()
TG_CHAT_ID = _tg.split(",")[0].strip() if _tg else ""
TG_TOKEN = _tg.split(",")[1].strip() if _tg and "," in _tg else ""

LOGIN_URL = "https://minestrator.com/connexion"
SERVER_URL = f"https://minestrator.com/my/server/{SERVER_ID}"
API_URL = f"https://mine.sttr.io/server/{SERVER_ID}/poweraction"

def send_tg(result, detail=""):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    import urllib.request, urllib.parse
    msg = f"🎮 Minestrator 重启通知\n📊 结果: {result}\n{detail}"
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TG_CHAT_ID, "text": msg}).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15):
            print("📨 TG推送成功")
    except Exception as e:
        print(f"⚠️ TG推送失败: {e}")

def solve_turnstile(page, timeout=60):
    """Wait for Turnstile invisible to complete using DrissionPage."""
    print("⏳ 等待 Turnstile 完成...")
    deadline = time.time() + timeout
    
    # First: check if turnstile already completed
    while time.time() < deadline:
        try:
            # Check for turnstile response input
            token = page.run_js("""
                (function(){
                    var inp = document.querySelector('input[name="cf-turnstile-response"]');
                    if (inp && inp.value && inp.value.length > 20) return inp.value;
                    inp = document.querySelector('input[name="cf_turnstile_response"]');
                    if (inp && inp.value && inp.value.length > 20) return inp.value;
                    var containers = document.querySelectorAll('[data-sitekey]');
                    for (var c of containers) {
                        var hidden = c.querySelector('input[type=hidden]');
                        if (hidden && hidden.value && hidden.value.length > 20) return hidden.value;
                    }
                    return '';
                })()
            """)
            if token and len(token) > 20:
                print(f"✅ Turnstile Token 获取成功 (长度 {len(token)})")
                return token
        except:
            pass
        
        # Try to find and click turnstile shadow DOM checkbox
        try:
            container = page.ele('css:[data-sitekey]', timeout=2)
            if container:
                shadow = container.shadow_root
                if shadow:
                    iframes = shadow.eles('tag:iframe')
                    if len(iframes) > 1:
                        iframe = iframes[1]
                    elif len(iframes) > 0:
                        iframe = iframes[0]
                    else:
                        iframe = None
                    if iframe:
                        try:
                            iframe_body = iframe.ele('tag:body')
                            if iframe_body:
                                body_shadow = iframe_body.shadow_root
                                if body_shadow:
                                    checkbox = body_shadow.ele('css:input[type=checkbox]', timeout=2)
                                    if checkbox:
                                        checkbox.click()
                                        print("✅ Turnstile checkbox 点击成功！")
                                        time.sleep(5)
                                        # Re-check for token
                                        continue
                        except Exception as e:
                            pass
        except:
            pass
        
        # Try using window.turnstile.execute
        try:
            page.run_js("""
                if (window.turnstile) {
                    var containers = document.querySelectorAll('[data-sitekey]');
                    containers.forEach(function(c) {
                        try { turnstile.execute(c); } catch(e) {}
                    });
                }
            """)
        except:
            pass
        
        time.sleep(3)
    
    print("❌ Turnstile 超时")
    return ""

def main():
    print("🔧 启动 DrissionPage 浏览器...")
    co = ChromiumOptions()
    # Don't use headless when Xvfb is available
    # co.headless()  # Xvfb provides virtual display instead
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    if PROXY:
        co.set_proxy(PROXY)
        print(f"🌐 使用代理: {PROXY}")
        print(f"🌐 使用代理: {PROXY}")
    
    try:
        page = ChromiumPage(co)
    except Exception as e:
        print(f"❌ 浏览器启动失败: {e}")
        send_tg("❌ 浏览器启动失败", str(e))
        return False
    
    try:
        # Verify IP
        print("🌐 验证出口IP...")
        try:
            page.get("https://api.ipify.org/?format=json")
            ip_text = page.html
            print(f"✅ 出口IP: {ip_text[:80]}")
        except:
            print("⚠️ IP验证跳过")
        
        # Login
        print("🔑 打开登录页面...")
        page.get(LOGIN_URL)
        time.sleep(3)
        
        try:
            page.ele('css:input[name="pseudo"]', timeout=15).input(EMAIL)
            page.ele('css:input[name="password"]', timeout=5).input(PASSWORD)
            time.sleep(1)
            page.ele('css:button[type="submit"]', timeout=5).click()
        except Exception as e:
            print(f"❌ 登录填写失败: {e}")
            page.get_screenshot(path="login_fail.png")
            send_tg("❌ 登录失败", str(e))
            return False
        
        # Wait for login
        print("⏳ 等待登录跳转...")
        for _ in range(40):
            if "/connexion" not in page.url:
                print(f"✅ 登录成功！当前页: {page.url}")
                break
            time.sleep(0.5)
        else:
            print("❌ 登录超时")
            page.get_screenshot(path="login_timeout.png")
            send_tg("❌ 登录超时")
            return False
        
        # Go to server page
        print(f"🔃 跳转服务器管理页: {SERVER_URL}")
        page.get(SERVER_URL)
        time.sleep(5)
        page.get_screenshot(path="server_page.png")
        
        # Solve Turnstile
        token = solve_turnstile(page, timeout=90)
        if not token:
            page.get_screenshot(path="token_timeout.png")
            send_tg("❌ Turnstile Token 获取超时")
            return False
        
        # Send restart API
        print("📡 发送重启指令...")
        result = page.run_js(f"""
            var done = arguments[0];
            fetch("{API_URL}", {{
                method: "PUT",
                headers: {{
                    "Authorization": "{AUTH_TOKEN}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                }},
                body: JSON.stringify({{poweraction: "restart", turnstile_token: {json.dumps(token)}}})
            }})
            .then(function(r){{ return r.json(); }})
            .then(function(data){{ done({{ok: true, data: data}}); }})
            .catch(function(err){{ done({{ok: false, error: err.toString()}}); }});
        """, timeout=15)
        
        print(f"📡 API响应: {result}")
        if result and result.get("ok") and result.get("data", {}).get("api", {}).get("code") == 200:
            print("✅ 重启成功！")
            send_tg("✅ 重启成功！")
            return True
        else:
            print(f"❌ API返回异常: {result}")
            page.get_screenshot(path="api_fail.png")
            send_tg("❌ API重启失败", str(result))
            return False
    finally:
        try:
            page.quit()
        except:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
