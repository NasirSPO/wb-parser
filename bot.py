import json
import time
import urllib.parse
import urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    payload = json.dumps({"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Ошибка TG: {e}")

def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    return driver

def scan_wildberries(driver, query: str):
    print(f"\n[WB] Поиск: {query}")
    search_url = f"https://www.wildberries.ru/catalog/0/search.aspx?sort=priceup&search={urllib.parse.quote(query)}"
    
    try:
        driver.get(search_url)
        time.sleep(7)
        
        cards = driver.find_elements(By.CSS_SELECTOR, "article.product-card, .product-card")
        print(f"[WB] Найдено карточек: {len(cards)}")
        
        found = 0
        for card in cards[:30]:
            article = card.get_attribute("data-nm-id") or card.get_attribute("data-card-id")
            
            try:
                name_elem = card.find_element(By.CSS_SELECTOR, ".product-card__name, .goods-name")
                name = name_elem.text.strip()
            except:
                name = ""

            try:
                price_elem = card.find_element(By.CSS_SELECTOR, ".price__lower-price, .wallet-price, .product-card__price")
                raw_price = "".join(ch for ch in price_elem.text if ch.isdigit())
                price = int(raw_price) if raw_price else 0
            except:
                price = 0

            if not article or price == 0:
                continue

            if any(stop in name.lower() for stop in STOP_WORDS):
                continue

            if 0 < price <= MAX_PRICE:
                item_url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
                msg = (
                    f"🟣 **Wildberries: пластик до {MAX_PRICE} ₽!**\n\n"
                    f"🔍 **Запрос:** {query}\n"
                    f"📦 **Товар:** {name}\n"
                    f"💰 **Цена:** {price} ₽\n"
                    f"🔗 [Купить на WB]({item_url})"
                )
                send_telegram(msg)
                print(f"[WB] -> Отправлено: {name} — {price} ₽")
                found += 1
                
        if found == 0:
            print(f"[WB] Подходящих товаров ниже {MAX_PRICE} ₽ не найдено.")
            
    except Exception as e:
        print(f"[WB] Ошибка: {e}")

def scan_ozon(driver, query: str):
    print(f"\n[Ozon] Поиск: {query}")
    # Прямой поиск Ozon по каталогу с сортировкой от дешевых к дорогим
    encoded_text = urllib.parse.quote(query)
    search_url = f"https://www.ozon.ru/search/?sorting=price&text={encoded_text}"
    
    try:
        driver.get(search_url)
        time.sleep(8)
        
        # Эмуляция скролла вниз, чтобы прогрузились ленивые карточки
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(3)
        
        page_title = driver.title
        print(f"[Ozon] Заголовок страницы: {page_title}")
        
        if "доступ ограничен" in page_title.lower() or "captcha" in driver.page_source.lower():
            print("[Ozon] Внимание: Ozon выдал защиту/капчу для зарубежного IP сервера.")
            return

        # Ищем все ссылки на товары
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/product/')]")
        print(f"[Ozon] Найдено ссылок на карточки: {len(links)}")
        
        found = 0
        seen_articles = set()
        
        for link in links:
            href = link.get_attribute("href")
            if not href:
                continue
            clean_url = href.split("?")[0]
            
            # Извлекаем ID товара из ссылки Ozon
            product_id = clean_url.rstrip("/").split("-")[-1]
            if not product_id.isdigit() or product_id in seen_articles:
                continue
            seen_articles.add(product_id)
            
            # Получаем текст блока карточки
            parent = link
            for _ in range(3):
                try:
                    parent = parent.find_element(By.XPATH, "./..")
                except:
                    break
            
            card_text = parent.text
            lines = [l.strip() for l in card_text.split("\n") if l.strip()]
            
            # Извлекаем цену
            price = 0
            for l in lines:
                if "₽" in l:
                    digits = "".join(c for c in l if c.isdigit())
                    if digits:
                        price = int(digits)
                        break
            
            # Название товара
            name = ""
            for l in lines:
                if len(l) > len(name) and "₽" not in l and "%" not in l and "отзыв" not in l.lower():
                    name = l
                    
            if not name or price == 0:
                continue
                
            if any(stop in name.lower() for stop in STOP_WORDS):
                continue
                
            if 0 < price <= MAX_PRICE:
                msg = (
                    f"🔵 **Ozon: пластик до {MAX_PRICE} ₽!**\n\n"
                    f"🔍 **Запрос:** {query}\n"
                    f"📦 **Товар:** {name}\n"
                    f"💰 **Цена:** {price} ₽\n"
                    f"🔗 [Купить на Ozon]({clean_url})"
                )
                send_telegram(msg)
                print(f"[Ozon] -> Отправлено: {name} — {price} ₽")
                found += 1
                
            if len(seen_articles) >= 25:
                break
                
        if found == 0:
            print(f"[Ozon] По запросу '{query}' подходящих товаров дешевле {MAX_PRICE} ₽ не найдено.")
            
    except Exception as e:
        print(f"[Ozon] Ошибка: {e}")

def main():
    print("Запуск двойного мониторинга WB + Ozon...")
    driver = init_driver()
    try:
        for q in SEARCH_QUERIES:
            scan_wildberries(driver, q)
            time.sleep(2)
            
        for q in SEARCH_QUERIES:
            scan_ozon(driver, q)
            time.sleep(2)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
