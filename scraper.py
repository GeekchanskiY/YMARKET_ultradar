import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

from xlsx_writer import XlsxWriter

from VARS import RUCAPTCHA_KEY

from python_rucaptcha import ReCaptchaV2, RuCaptchaControl, CallbackClient
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
    """
        Main Scraper class for ultradar.ru
    """
    offers: list[Offer] = []
    links: list
    driver: webdriver.Chrome
    wait: WebDriverWait
    rucaptcha: str = RUCAPTCHA_KEY

    def __init__(self, category: str):
        """
         Initialisation and running main data loop
        :param category: - output file name
        """
        self.driver: webdriver.Chrome = webdriver.Chrome(executable_path="chromedriver.exe")
        self.wait = WebDriverWait(self.driver, 10)
        self.links: list = self.get_category(category)
        self.get_detail_loop()

    def get_category(self, link: str) -> list[str]:
        """
            Gets all unit links in category
        :param link: category link
        :return: list of links (str)
        """
        pages: int
        self.driver.get(link+"?limit=100")
        self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "item_ul")))
        self.driver.find_element(By.CLASS_NAME, "last").click()
        pages = int(self.driver.find_element(By.CLASS_NAME, "active").text)
        output_data: list = []
        for i in range(0, pages):
            self.driver.get(link+f"?limit=100&start={i*100}")
            self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "item_ul")))
            time.sleep(1)
            try:
                item_wrapper: WebElement = self.driver.find_element(By.CLASS_NAME, "item_ul")
                items: list[WebElement] = item_wrapper.find_elements(By.TAG_NAME, "li")
            except Exception as e:
                print(str(e))
                input("fix error and press enter")
                continue
            for item in items:
                if item.text.lower().find("цена") != -1:
                    try:
                        item.find_element(By.CLASS_NAME, "articleImages_noImage")
                        continue
                    except NoSuchElementException:
                        pass
                    output_data.append(item.find_element(By.CLASS_NAME, "articleDesc").find_elements(By.TAG_NAME, "a")
                                       [1].get_attribute("href"))

            print(len(output_data))

        return output_data

    def get_detail_loop(self) -> None:
        """
           Calls get_detail method for each link or passing recaptcha method
        :return:
        """
        counter = 0
        links_length = len(self.links)
        for link in self.links:
            counter += 1
            print(f"{counter}/{links_length}")
            i = 0
            while i <= 5:
                i += 1
                try:
                    res = self.get_detail(link)

                    if res != 1:
                        print(f"{link} skipped (invalid data)")
                    break
                except Exception as e:
                    # error: str = str(e)
                    print("Solving captcha")
                    self.solve_captcha()
                     
    def solve_captcha(self) -> None:
        """
            Passes recaptcha on the driver's page
        :return:
        """

        # getting all required params

        SITE_KEY: str = self.driver.find_element(By.CLASS_NAME, "g-recaptcha").get_attribute("data-sitekey")
        url: str = self.driver.current_url

        # running rucaptcha

        answer_usual_re2: dict = ReCaptchaV2.ReCaptchaV2(rucaptcha_key=RUCAPTCHA_KEY).captcha_handler(
            site_key=SITE_KEY, page_url=url
        )

        # sending rucaptcha answer

        el: WebElement = self.driver.find_element(By.CLASS_NAME, "g-recaptcha-response")
        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", el,
                                   answer_usual_re2["captchaSolve"])
        self.driver.execute_script('$("#data").val($.urlParam("data"));')
        self.driver.execute_script('$("#form4mcRecaptcha").submit();')

    def get_detail(self, link) -> int:
        """
          Gets detail data of the unit and saves it to list of instance's scraped list
        :param link: link with detail data
        :return: 1 if scraped correctly, else 0
        """
        self.driver.get(link)
        self.wait.until(EC.visibility_of_element_located((By.ID, "searchResultsTable")))
        table: WebElement = self.driver.find_element(By.ID, "searchResultsTable")

        table_body: WebElement = table.find_element(By.TAG_NAME, "tbody")
        try:
            img: str = self.driver.find_element(By.CLASS_NAME, "article-image").find_element(By.TAG_NAME, "img") \
                .get_attribute("src")
        except Exception:
            return 0
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
            return 0

        if len(sources) == 0:
            return 0

        detail_data_el: WebElement = self.driver.find_element(By.CLASS_NAME, "infoBlock")
        detail_data_table: WebElement = detail_data_el.find_element(By.CLASS_NAME, "propertiesTable")
        brand: str = detail_data_el.find_element(By.CLASS_NAME, "article-brand").text
        number: str = detail_data_el.find_element(By.CLASS_NAME, "article-number").text
        name: str = detail_data_el.find_element(By.CLASS_NAME, "brand").text.replace(number, "").replace(brand, "") \
            .strip()
        category: str = ""
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
        url = link.split("?")[0] + "?utm_source=yandex&utm_medium=market&utm_campaign=script"
        self.offers.append(Offer(name=name, brand=brand, img=img, detail_data=detail_data, category=category,
                                 sources=sources, SKU=number, url=url))
        return 1

    def get_offers(self) -> list[Offer]:
        """
             Method for returning offers
        :return: list of scraped offers
        """
        return self.offers
            

if __name__ == '__main__':
    scraper: Scraper = Scraper("https://ultradar.ru/tires_catalog")
    xlsx_writer: XlsxWriter = XlsxWriter(scraper.get_offers(), "tires_catalog")
    scraper.driver.close()
    exit()
