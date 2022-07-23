import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

from xlsx_writer import XlsxWriter
import random


class Offer:
    """
        Offer dataclass with self formatting methods
    """
    name: str
    brand: str
    img: str
    detail_data: list[dict[str, str]]
    SKU: str
    description: str
    category: str
    price: float
    availability: int
    currency: str = "RUB"
    source: dict
    home_url: str

    def __init__(self, name, brand, img, detail_data, SKU, category, sources: list, url):
        self.name = name
        self.brand = brand
        self.img = img
        self.detail_data = detail_data
        self.SKU = SKU
        self.category = category
        self.get_best_source(sources)
        self.home_url = url

    def get_best_source(self, sources: list):
        best_availability = 0
        best_price = 0
        for source in sources:
            if int(source["availability"]) > best_availability:
                best_availability = int(source["availability"])
                best_price = source["price"]
            elif int(source["availability"]) == best_availability:
                if source["price"] < best_price:
                    best_price = source["price"]
        self.price = best_price
        if best_availability > 5:
            self.availability = best_availability
        else:
            self.availability = 0


    def get_non_sale_price(self) -> float:
        return (self.price/100)*15+self.price

    def get_description(self) -> str:
        return f'{self.category} {self.name} {self.brand} с доставкой на дом и в офис'

    def get_detail_str(self) -> str:
        output: str = ""
        for data_dict in self.detail_data:
            if data_dict["name"].find(",") != -1:
                output += f"{data_dict['name'].split(',')[0]}|{data_dict['value']}|" \
                          f"{data_dict['name'].split(',')[1].replace(' ', '')};"
            else:
                output += f"{data_dict['name']}|{data_dict['value']};"
        return output

    def __str__(self):
        return f"{self.name} - {self.price} - {self.availability} - {self.brand}"


class Scraper:
    offers: list[Offer] = []

    def __init__(self, category: str):
        self.driver: webdriver.Chrome = webdriver.Chrome(executable_path="chromedriver.exe")
        self.links: list = self.get_category(category)
        self.links = self.links[0:5]
        self.wait = WebDriverWait(self.driver, 10)
        self.get_detail()

    def get_category(self, link: str) -> list:
        output_data: list = []
        self.driver.get(link)
        time.sleep(1)
        item_wrapper: WebElement = self.driver.find_element(By.CLASS_NAME, "item_ul")
        items: list[WebElement] = item_wrapper.find_elements(By.TAG_NAME, "li")
        for item in items:
            output_data.append(item.find_element(By.CLASS_NAME, "articleDesc").find_elements(By.TAG_NAME, "a")[1]
                               .get_attribute("href"))

        return output_data

    def get_detail(self):
        for link in self.links:
            try:
                self.driver.get(link)
                time.sleep(1)
                table: WebElement = self.driver.find_element(By.ID, "searchResultsTable")

                table_body: WebElement = table.find_element(By.TAG_NAME, "tbody")
                img: str = self.driver.find_element(By.CLASS_NAME, "article-image").find_element(By.TAG_NAME, "img")\
                    .get_attribute("src")
                self.driver.find_element(By.CLASS_NAME, "infoLink").click()
                self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "infoBlock")))
                i = 0
                sources: list[dict] = []
                while i <= 10:
                    try:

                        sources: list[dict] = []
                        for tr in table_body.find_elements(By.TAG_NAME, "tr"):
                            if tr.text == "Запрашиваемый артикул":
                                continue
                            elif tr.text == "Аналоги":
                                break
                            i = 1

                            try:
                                sources.append({
                                    "availability": tr.find_element(By.CLASS_NAME, "resultAvailability").text,
                                    "price": int(tr.find_element(By.CLASS_NAME, "resultPrice").text.replace("руб.", "")
                                                 .replace(" ", "")),
                                })
                            except (ValueError, NoSuchElementException):
                                continue
                        break
                    except StaleElementReferenceException:
                        i += 1
                        time.sleep(0.2)
                if i == 11:
                    continue

                if len(sources) == 0:
                    continue
                print(len(sources))

                detail_data_el: WebElement = self.driver.find_element(By.CLASS_NAME, "infoBlock")
                detail_data_table: WebElement = detail_data_el.find_element(By.CLASS_NAME, "propertiesTable")
                brand: str = detail_data_el.find_element(By.CLASS_NAME, "article-brand").text
                number: str = detail_data_el.find_element(By.CLASS_NAME, "article-number").text
                name: str = detail_data_el.find_element(By.CLASS_NAME, "brand").text.replace(number, "").replace(brand, "")\
                    .strip()
                category: str = ""
                model: str = ""
                detail_data: list[dict] = []
                tr: WebElement
                for tr in detail_data_table.find_elements(By.TAG_NAME, "tr"):
                    row_items: list[WebElement] = tr.find_elements(By.TAG_NAME, "td")
                    item_name: str = row_items[0].text
                    item_value: str = row_items[1].text
                    if item_name == "Товарная группа:":
                        pass
                    elif item_name == "Модель:":
                        pass
                    elif item_name == "Тип:":
                        pass
                    else:
                        detail_data.append({"name": item_name.replace(":", ""), "value": item_value})
                url = link.split("?")[0]+"?utm_source=yandex&utm_medium=market&utm_campaign=script"
                self.offers.append(Offer(name=name, brand=brand, img=img, detail_data=detail_data, category=category,
                                         sources=sources, SKU=number, url=url))
                time.sleep(random.randint(50, 200)/100)
            except Exception as e:
                print(str(e))
                input("Сделай же что-нибудь! и тыкни enter!")

    def get_offers(self) -> list[Offer]:
        return self.offers
            

if __name__ == '__main__':
    scraper = Scraper("https://ultradar.ru/disks_catalog?goods_group=disks&action=search&viewMode=tile&property%5Bdisk_type%5D%5B%5D=cast&property%5Bet%5D%5Bfrom%5D=&property%5Bet%5D%5Bto%5D=&property%5Bhub_diameter%5D%5Bfrom%5D=&property%5Bhub_diameter%5D%5Bto%5D=&limit=100")
    xlsx_writer = XlsxWriter(scraper.get_offers(), "диски литые")
