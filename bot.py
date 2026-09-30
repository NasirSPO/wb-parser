import gzip
import io
import json
import ssl
import time
import urllib.parse
import urllib.request

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

# Настройка SSL без проверки строгих сертификатов хоста
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10, context=ssl_context)
    except Exception as e:
        print(f"Ошибка TG: {e}")

def fetch_json(url: str):
    headers = {
        "User-Agent": "Wildberries/2311 CFNetwork/1410.0.3 Darwin/22.6.0",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Origin": "https://www.wildberries.ru",
        "Referer": "https://www.wildberries.ru/"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
            content = response.read()
            if response.info().get("Content-Encoding") == "gzip":
                buf = io.BytesIO(content)
                with gzip.GzipFile(fileobj=buf) as f:
                    content = f.read()
            return json.loads(content.decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"Ошибка запроса к каталогу: {e}")
        return None

def check_wildberries(query: str):
    print(f"\n[WB] Поиск: {query}")
    encoded_query = urllib.parse.quote(query)
    
    # Мобильный шлюз каталога WB, доступный с зарубежных серверов
    url = (
        f"https://search.wb.ru/exactmatch/ru/common/v7/search?"
        f"appType=1&curr=rub&dest=-1257786&query={encoded_query}&"
        f"resultset=catalog&sort=priceup&spp=30&suppressSpellcheck=false"
    )
    
    data = fetch_json(url)
    if not data:
        # Резервный шлюз
        url_fallback = (
            f"https://catalog.wb.ru/catalog/electronic11/v4/filters?"
            f"appType=1&curr=rub&dest=-1257786&query={encoded_query}&"
            f"resultset=catalog&sort=priceup&spp=30"
        )
        data = fetch_json(url_fallback)

    if not data:
        print("[WB] Не удалось получить ответ от серверов WB.")
        return

    products = data.get("data", {}).get("products", []) or data.get("products", [])
    print(f"[WB] Получено товаров из каталога: {len(products)}")

    found = 0
    for item in products[:30]:
        article = item.get("id")
        name = item.get("name", "").strip()
        
        # Получение цены
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
            print(f"[WB] -> Отправлено в TG: {name} — {price} ₽")
            found += 1

    if found == 0:
        print(f"[WB] По запросу '{query}' товаров дешевле {MAX_PRICE} ₽ пока нет.")

def main():
    print("Запуск мониторинга в облаке GitHub...")
    for q in SEARCH_QUERIES:
        check_wildberries(q)
        time.sleep(2)

if __name__ == "__main__":
    main()
