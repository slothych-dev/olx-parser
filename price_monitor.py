import requests
from bs4 import BeautifulSoup
import csv
import os
import schedule
import time

# === НАЛАШТУВАННЯ ===
BOT_TOKEN = "встав_свій_токен_сюди"
CHAT_ID = "встав_свій_chat_id_сюди"

# Посилання на конкретне оголошення OLX яке хочеш відслідковувати
OLX_URL = "https://www.olx.ua/uk/obyavlenie/..."  # встав реальне посилання

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

CSV_FILE = "price_history.csv"


# === ФУНКЦІЇ ===

def get_price(url):
    """Отримує поточну ціну з оголошення"""
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    price_tag = soup.find("div", attrs={"data-testid": "ad-price-container"})
    if price_tag:
        return price_tag.text.strip()
    return None


def send_telegram(message):
    """Надсилає повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message
    })


def save_to_csv(price):
    """Зберігає ціну з датою в CSV"""
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Час", "Ціна"])  # заголовки
        from datetime import datetime
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), price])


def get_last_price():
    """Читає останню збережену ціну з CSV"""
    if not os.path.exists(CSV_FILE):
        return None
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        if len(rows) > 1:
            return rows[-1][1]  # остання ціна
    return None


def check_price():
    """Головна функція — перевіряє ціну і сповіщає якщо змінилась"""
    print("Перевіряємо ціну...")
    current_price = get_price(OLX_URL)

    if not current_price:
        print("Не вдалось отримати ціну")
        return

    last_price = get_last_price()
    save_to_csv(current_price)

    print(f"Поточна ціна: {current_price}")

    if last_price is None:
        # Перший запуск
        send_telegram(f"🔍 Моніторинг запущено!\nПоточна ціна: {current_price}\n{OLX_URL}")

    elif current_price != last_price:
        # Ціна змінилась!
        send_telegram(
            f"⚡ Ціна змінилась!\n"
            f"Було: {last_price}\n"
            f"Стало: {current_price}\n"
            f"{OLX_URL}"
        )
    else:
        print("Ціна не змінилась")


# === ЗАПУСК ===
check_price()  # одразу перевіряємо при старті

# Перевіряємо кожні 30 хвилин
schedule.every(30).minutes.do(check_price)

print("Моніторинг запущено. Перевірка кожні 30 хвилин...")
while True:
    schedule.run_pending()
    time.sleep(60)