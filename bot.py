import json
import time
import urllib.parse
from curl_cffi import requests

# === НАСТРОЙКИ ПОИСКА ===
SEARCH_QUERIES = [
    "пластик PLA 1.75 1кг",
    "пластик PETG 1.75 1кг"
]

MAX_PRICE = 850  # Порог цены в рублях

STOP_WORDS = [
    "3d-ручк", "3d ручк", "сопло", "сопла", "пробник", 
    "набор для", "термобарьер", "очиститель", "образец"
]

# === ДАННЫЕ TELEGRAM ===
TG_BOT_TOKEN = "8492519933:AAHMGWZ87rLbk2p7WnOHf2hviw_6nqequos"
TG_CHAT_ID = "624336298"

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки TG: {e}")

def check_wb(query: str):
    print(f"\n[WB] Сканирование: {query}")
    encoded = urllib.parse.quote(query)
    
    # Список актуальных рабочих мобильных и веб-шлюзов WB
    urls = [
        f"https://u-search.wb.ru/exactmatch/ru/common/v7/search?appType=1&curr=rub&dest=-1257786&query={encoded}&resultset=catalog&sort=priceup&spp=30",
        f"https://catalog.wb.ru/catalog/electronic11/v4/filters?appType=1&curr=rub&dest=-1257786&query={encoded}&resultset=catalog&sort=priceup&spp=30"
    ]
    
    headers = {
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.wildberries.ru",
        "Referer": "https://www.wildberries.ru/"
    }

    data = None
    # impersonate="chrome124" имитирует настоящий сетевой стек Chrome
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, impersonate="chrome124", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                break
            else:
                print(f"Шлюз ответил кодом {resp.status_code}, пробуем следующий...")
        except Exception as err:
            print(f"Ошибка запроса: {err}")
            
    if not data:
        print("[WB] Не удалось получить ответ каталога.")
        return

    products = data.get("data", {}).get("products", []) or data.get("products", [])
    print(f"[WB] Получено товаров: {len(products)}")

    found = 0
    for item in products[:30]:
        article = item.get("id")
        name = item.get("name", "").strip()
        
        # Расчет цены с учетом скидки WB
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
            print(f"-> Отправлено: {name} — {price} ₽")
            found += 1

    if found == 0:
        print(f"[WB] По запросу '{query}' товаров дешевле {MAX_PRICE} ₽ пока нет.")

def main():
    print("Запуск сканирования WB в облаке...")
    for q in SEARCH_QUERIES:
        check_wb(q)
        time.sleep(2)

if __name__ == "__main__":
    main()
