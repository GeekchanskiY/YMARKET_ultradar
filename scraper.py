import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement


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

    def __init__(self, name, brand, img, detail_data, SKU, category, sources: list):
        self.name = name
        self.brand = brand
        self.img = img
        self.detail_data = detail_data
        self.SKU = SKU
        self.category = category
        self.get_best_source(sources)

    def get_best_source(self, sources: list):
        best_availability = 0
        best_price = 0
        for source in sources:
            if source["availability"] > best_availability:
                best_availability = source["availability"]
                best_price = source["price"]
            elif source["availability"] == best_availability:
                if source["price"] < best_price:
                    best_price = source["price"]
        self.price = best_price
        self.availability: best_availability

    def get_non_sale_price(self) -> float:
        return (self.price/100)*15+self.price

    def get_description(self) -> str:
        return f'{self.category} {self.name} {self.description} с доставкой на дом и в офис'

    def get_detail_str(self) -> str:
        output: str = ""
        for data_dict in self.detail_data:
            if data_dict["name"].find(",") != -1:
                output += f"{data_dict['name'].split(',')[0]}|{data_dict['value']}|{data_dict['name'].split(',')[1]};"
            else:
                output += f"{data_dict['name']}|{data_dict['value']};"
        return output


class Scraper:
    offers: list[Offer] = []

    def __init__(self, category: str):
        self.driver: webdriver.Chrome = webdriver.Chrome(executable_path="chromedriver.exe")
        self.links: list = self.get_category(category)
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
            self.driver.get(link)
            table: WebElement = self.driver.find_element(By.ID, "searchResultsTable")
            sources: list[dict] = []
            table_body: WebElement = table.find_element(By.TAG_NAME, "tbody")
            img: str = self.driver.find_element(By.CLASS_NAME, "article-image").find_element(By.TAG_NAME, "img")\
                .get_attribute("src")
            self.driver.find_element(By.CLASS_NAME, "infoLink").click()
            self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "infoBlock")))

            for tr in table_body.find_elements(By.TAG_NAME, "tr"):
                if tr.text == "Запрашиваемый артикул":
                    continue
                elif tr.text == "Аналоги":
                    break
                sources.append({
                    "availability": tr.find_element(By.CLASS_NAME, "resultAvailability").text,
                    "price": tr.find_element(By.CLASS_NAME, "resultPrice").text,
                    
                })
            if sources[0]["availability"] == "Нет в продаже":
                continue

            detail_data_el: WebElement = self.driver.find_element(By.CLASS_NAME, "infoBlock")
            detail_data_table: WebElement = detail_data_el.find_element(By.CLASS_NAME, "propertiesTable")
            brand: str = detail_data_el.find_element(By.CLASS_NAME, "article-brand").text
            number: str = detail_data_el.find_element(By.CLASS_NAME, "article-number").text
            name: str = detail_data_el.find_element(By.CLASS_NAME, "brand").text.replace(number, "").replace(brand, "") \
                .strip()
            

if __name__ == '__main__':
    scraper = Scraper("https://ultradar.ru/tires_catalog?limit=100")
