import time
import urllib.parse
import urllib.request
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def scan_wildberries(driver, query: str):
    print(f"[WB] Сканирование: {query}")
    search_url = f"https://www.wildberries.ru/catalog/0/search.aspx?sort=priceup&search={urllib.parse.quote(query)}"
    
    try:
        driver.get(search_url)
        time.sleep(7)
        
        cards = driver.find_elements(By.CSS_SELECTOR, "article.product-card, .product-card")
        found = 0
        
        for card in cards[:25]:
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
                    f"🟣 **Найден пластик на Wildberries!**\n\n"
                    f"🔍 **Запрос:** {query}\n"
                    f"📦 **Товар:** {name}\n"
                    f"💰 **Цена:** {price} ₽\n"
                    f"🔗 [Перейти на Wildberries]({item_url})"
                )
                send_telegram(msg)
                print(f"[WB] -> Найдено: {name} — {price} ₽")
                found += 1
                
        if found == 0:
            print(f"[WB] Подходящих товаров по '{query}' нет.")
            
    except Exception as e:
        print(f"[WB] Ошибка при сканировании '{query}': {e}")

def scan_ozon(driver, query: str):
    print(f"[Ozon] Сканирование: {query}")
    encoded_text = urllib.parse.quote(query)
    search_url = f"https://www.ozon.ru/category/rashodnye-materialy-dlya-3d-printerov-34720/?sorting=price&text={encoded_text}"
    
    try:
        driver.get(search_url)
        time.sleep(7)
        
        link_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/product/')]")
        found = 0
        seen_urls = set()
        
        for link in link_elements:
            href = link.get_attribute("href")
            if not href:
                continue
                
            clean_url = href.split("?")[0]
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            
            card_text = link.text.strip()
            if not card_text:
                try:
                    parent = link.find_element(By.XPATH, "./..")
                    card_text = parent.text.strip()
                except:
                    continue
                    
            lines = [line.strip() for line in card_text.split("\n") if line.strip()]
            
            price = 0
            for line in lines:
                if "₽" in line:
                    digits = "".join(ch for ch in line if ch.isdigit())
                    if digits:
                        price = int(digits)
                        break
                        
            name = ""
            for line in lines:
                if len(line) > len(name) and "₽" not in line and "%" not in line:
                    name = line
                    
            if not name or price == 0:
                continue
                
            if any(stop in name.lower() for stop in STOP_WORDS):
                continue
                
            if 0 < price <= MAX_PRICE:
                msg = (
                    f"🔵 **Найден пластик на Ozon!**\n\n"
                    f"🔍 **Запрос:** {query}\n"
                    f"📦 **Товар:** {name}\n"
                    f"💰 **Цена:** {price} ₽\n"
                    f"🔗 [Перейти на Ozon]({clean_url})"
                )
                send_telegram(msg)
                print(f"[Ozon] -> Найдено: {name} — {price} ₽")
                found += 1
                
            if len(seen_urls) >= 25:
                break
                
        if found == 0:
            print(f"[Ozon] Подходящих товаров по '{query}' нет.")
            
    except Exception as e:
        print(f"[Ozon] Ошибка при сканировании '{query}': {e}")

def main():
    print("Старт объединенного сканирования WB и Ozon...")
    driver = init_driver()
    try:
        # Проверка Wildberries
        for q in SEARCH_QUERIES:
            scan_wildberries(driver, q)
            time.sleep(2)
            
        # Проверка Ozon
        for q in SEARCH_QUERIES:
            scan_ozon(driver, q)
            time.sleep(2)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
