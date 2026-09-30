import gzip
import io
import json
import time
import urllib.parse
import urllib.request

# ================= НАСТРОЙКИ =================
SCRAPE_DO_TOKEN = "СЮДА_ВСТАВЬТЕ_ТОКЕН_ОТ_SCRAPE_DO"

SEARCH_QUERIES = [
    "пластик PLA 1.75 1кг",
    "пластик PETG 1.75 1кг"
]

MAX_PRICE = 850  # Порог цены (в рублях)

STOP_WORDS = [
    "3d-ручк", "3d ручк", "сопло", "сопла", "пробник", 
    "набор для", "термобарьер", "очиститель", "образец"
]

TG_BOT_TOKEN = "8492519933:AAHMGWZ87rLbk2p7WnOHf2hviw_6nqequos"
TG_CHAT_ID = "624336298"
# =============================================

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки TG: {e}")

def fetch_via_scrapedo(target_url: str):
    """Делает запрос через быстрый прокси-шлюз Scrape.do"""
    encoded_url = urllib.parse.quote(target_url)
    api_endpoint = f"http://api.scrape.do/?token={SCRAPE_DO_TOKEN}&url={encoded_url}"
    
    req = urllib.request.Request(api_endpoint, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            content = response.read()
            # Распаковываем gzip, если ответ сжат
            if response.info().get("Content-Encoding") == "gzip":
                buf = io.BytesIO(content)
                with gzip.GzipFile(fileobj=buf) as f:
                    content = f.read()
            return json.loads(content.decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"Ошибка запроса через шлюз: {e}")
        return None

def check_query(query: str):
    print(f"\n[WB] Сканирование по запросу: {query}")
    encoded_query = urllib.parse.quote(query)
    
    wb_target_url = (
        f"https://search.wb.ru/exactmatch/ru/common/v7/search?"
        f"appType=1&curr=rub&dest=-1257786&query={encoded_query}&"
        f"resultset=catalog&sort=priceup&spp=30"
    )
    
    data = fetch_via_scrapedo(wb_target_url)
    if not data:
        print("[WB] Не удалось получить данные от маркетплейса.")
        return

    products = data.get("data", {}).get("products", []) or data.get("products", [])
    print(f"[WB] Успешно получено товаров: {len(products)}")

    found = 0
    for item in products[:30]:
        article = item.get("id")
        name = item.get("name", "").strip()
        
        # Вычисление цены в рублях
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
    print("Запуск мониторинга WB через быстрый шлюз...")
    for q in SEARCH_QUERIES:
        check_query(q)
        time.sleep(2)

if __name__ == "__main__":
    main()
