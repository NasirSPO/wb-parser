import json
import time
import urllib.parse
import requests

# ================= НАСТРОЙКИ =================
SCRAPE_DO_TOKEN = "9596f394fd554b2ebe6fda8da9ae0be7ddca45811bf"

SEARCH_QUERIES = [
    "пластик PLA 1.75 1кг",
    "пластик PETG 1.75 1кг"
]

MAX_PRICE = 850  # Порог цены в рублях

STOP_WORDS = [
    "3d-ручк", "3d ручк", "сопло", "сопла", "пробник", 
    "набор для", "термобарьер", "очиститель", "образец"
]

TG_BOT_TOKEN = "8492519933:AAHMGWZ87rLbk2p7WnOHf2hviw_6nqequos"
TG_CHAT_ID = "624336298"
# =============================================

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки TG: {e}")

def fetch_via_scrapedo(target_url: str):
    """Делает быстрый защищенный запрос к шлюзу без рендеринга браузера"""
    encoded_target = urllib.parse.quote(target_url, safe="")
    # Используем HTTPS и отключаем тяжелый render=false для мгновенного ответа
    api_url = f"https://api.scrape.do?token={SCRAPE_DO_TOKEN}&url={encoded_target}&render=false"
    
    try:
        response = requests.get(api_url, timeout=35)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Шлюз ответил кодом {response.status_code}: {response.text[:120]}")
            return None
    except Exception as e:
        print(f"Ошибка запроса к шлюзу: {e}")
        return None

def check_query(query: str):
    print(f"\n[WB] Сканирование по запросу: {query}")
    
    encoded_query = urllib.parse.quote(query)
    wb_url = (
        f"https://search.wb.ru/exactmatch/ru/common/v7/search?"
        f"appType=1&curr=rub&dest=-1257786&query={encoded_query}&"
        f"resultset=catalog&sort=priceup&spp=30"
    )
    
    data = fetch_via_scrapedo(wb_url)
    if not data:
        print("[WB] Ответ от каталога не получен.")
        return

    products = data.get("data", {}).get("products", []) or data.get("products", [])
    print(f"[WB] Получено позиций из каталога: {len(products)}")

    found = 0
    for item in products[:30]:
        article = item.get("id")
        name = item.get("name", "").strip()
        
        # Получаем цену в рублях
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
        print(f"[WB] По запросу '{query}' предложений дешевле {MAX_PRICE} ₽ пока нет.")

def main():
    print("Запуск автономного мониторинга WB...")
    for q in SEARCH_QUERIES:
        check_query(q)
        time.sleep(1)

if __name__ == "__main__":
    main()
