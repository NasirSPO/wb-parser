import time
import urllib.parse
import urllib.request
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# === НАСТРОЙКИ ПОИСКА ===
QUERY = "пластик PLA 1.75 1кг"
MAX_PRICE = 850

# Стоп-слова (отсекаем ручки, сопла, пробники)
STOP_WORDS = [
    "3d-ручк", "3d ручк", "сопло", "сопла", "пробник", 
    "набор для", "термобарьер", "очиститель", "образец"
]

# === ВАШИ ДАННЫЕ TELEGRAM ===
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
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def main():
    print("Запуск проверки WB в облаке...")
    driver = init_driver()
    search_url = f"https://www.wildberries.ru/catalog/0/search.aspx?sort=priceup&search={urllib.parse.quote(QUERY)}"
    
    try:
        driver.get(search_url)
        time.sleep(7)
        
        cards = driver.find_elements(By.CSS_SELECTOR, "article.product-card, .product-card")
        print(f"Найдено карточек: {len(cards)}")
        
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
                    f"🔥 **Найден пластик по выгодной цене!**\n\n"
                    f"📦 **Товар:** {name}\n"
                    f"💰 **Цена:** {price} ₽\n"
                    f"🔗 [Перейти на WB]({item_url})"
                )
                send_telegram(msg)
                print(f"Отправлено: {name} за {price} руб.")
                
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
