import requests
from bs4 import BeautifulSoup
import pandas as pd

# Що шукаємо на OLX
SEARCH_QUERY = "ноутбук"
URL = f"https://www.olx.ua/uk/list/q-{SEARCH_QUERY}/"

# Заголовки щоб сайт думав що ми браузер
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def get_page(url):
    # Завантажуємо сторінку
    response = requests.get(url, headers=HEADERS)
    return BeautifulSoup(response.text, "html.parser")


def parse_ads(soup):
    results = []

    # Знаходимо всі оголошення на сторінці
    ads = soup.find_all("div", attrs={"data-cy": "l-card"})

    for ad in ads:
        try:
            # Назва
            title = ad.find("h4").text.strip()

            # Ціна
            price_tag = ad.find("p", attrs={"data-testid": "ad-price"})
            price = price_tag.text.strip() if price_tag else "Без ціни"

            # Посилання
            link_tag = ad.find("a")
            link = "https://www.olx.ua" + link_tag["href"] if link_tag else ""

            results.append({
                "Назва": title,
                "Ціна": price,
                "Посилання": link
            })
        except:
            continue

    return results


def save_to_excel(data):
    df = pd.DataFrame(data)
    df.to_excel("результати.xlsx", index=False)
    print(f"Збережено {len(data)} оголошень у файл результати.xlsx")


# Запускаємо
print("Парсимо OLX...")
soup = get_page(URL)
ads = parse_ads(soup)
save_to_excel(ads)