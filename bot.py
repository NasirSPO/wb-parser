import json
import time
import urllib.parse
from curl_cffi import requests

# === НАСТРОЙКИ ПОИСКА ===
SEARCH_QUERIES = [
    "пластик PLA 1.75 1кг",
    "пластик PETG 1.75 1кг"
]

MAX_PRICE = 850  # Порог цены (в рублях)

# Стоп-слова (отсекаем ручки, сопла, пробники)
STOP_WORDS = [
    "3d-ручк", "3d ручк", "сопло", "сопла", "пробник", 
    "набор для", "термобарьер", "очиститель", "образец"
]

# === ДАННЫЕ TELEGRAM ===
TG_BOT_TOKEN = "8492519933:AAHMGWZ87rLbk2p7WnOHf2hviw_6nqequos"
TG_CHAT_ID = "624336298"

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        # В Telegram шлем напрямую без прокси
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки TG: {e}")

def get_free_proxies():
    """Скачивает свежий список живых публичных прокси"""
    proxy_urls = [
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    proxies = []
    for u in proxy_urls:
        try:
            r = requests.get(u, timeout=10)
            if r.status_code == 200:
                lines = [line.strip() for line in r.text.split("\n") if line.strip()]
                proto = "socks5://" if "socks5" in u else "http://"
                proxies.extend([f"{proto}{item}" for item in lines[:40]])
        except Exception:
            continue
    return proxies

def fetch_wb(url: str, proxies_pool):
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.wildberries.ru",
        "Referer": "https://www.wildberries.ru/"
    }

    # Сначала пробуем прямой запрос
    try:
        res = requests.get(url, headers=headers, impersonate="chrome124", timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass

    # Если 403 или таймаут — перебираем пул бесплатных прокси
    print("[WB] Пробуем обход через ротацию прокси...")
    for proxy in proxies_pool:
        try:
            res = requests.get(
                url,
                headers=headers,
                impersonate="chrome124",
                proxies={"http": proxy, "https": proxy},
                timeout=7
            )
            if res.status_code == 200:
                print(f"[WB] Успешно подключено через {proxy.split('@')[-1]}")
                return res.json()
        except Exception:
            continue

    return None

def check_wb(query: str, proxies_pool):
    print(f"\n[WB] Поиск: {query}")
    encoded = urllib.parse.quote(query)
    
    url = (
        f"https://u-search.wb.ru/exactmatch/ru/common/v7/search?"
        f"appType=1&curr=rub&dest=-1257786&query={encoded}&resultset=catalog&sort=priceup&spp=30"
    )

    data = fetch_wb(url, proxies_pool)
    if not data:
        print("[WB] Не удалось получить ответ (прокси не ответили).")
        return

    products = data.get("data", {}).get("products", []) or data.get("products", [])
    print(f"[WB] Получено товаров: {len(products)}")

    found = 0
    for item in products[:30]:
        article = item.get("id")
        name = item.get("name", "").strip()
        
        price = item.get("sizes", [{}])[0].get("price", {}).get("total", 0) // 100
        if not price:
            price = item.get("salePriceU", 0) // 100

        if not article or price == 0:
            continue

        if any(stop in name.lower() for stop in STOP_WORDS):
            continue

        if 0 < price <= MAX_PRICE:
            item_url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
            msg = (
                f"🟣 **Найден пластик на Wildberries!**\n\n"
                f"🔍 **Запрос:** {query}\n"
                f"📦 **Товар:** {name}\n"
                f"💰 **Цена:** {price} ₽\n"
                f"🔗 [Перейти на Wildberries]({item_url})"
            )
            send_telegram(msg)
            print(f"-> Найдено: {name} — {price} ₽")
            found += 1

    if found == 0:
        print(f"[WB] Товаров дешевле {MAX_PRICE} ₽ пока нет.")

def main():
    print("Запуск бесплатного мониторинга WB с авто-прокси...")
    proxies_pool = get_free_proxies()
    print(f"Загружено рабочих адресов для обхода: {len(proxies_pool)}")
    
    for q in SEARCH_QUERIES:
        check_wb(q, proxies_pool)
        time.sleep(2)

if __name__ == "__main__":
    main()
