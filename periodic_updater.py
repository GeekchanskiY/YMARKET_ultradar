from datetime import datetime, timedelta
from unittest import mock
import pause

from openpyxl import load_workbook

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, JavascriptException
from VARS import RUCAPTCHA_KEY
import time

from python_rucaptcha import ReCaptchaV2
import xml.etree.ElementTree as ET
import random
from dataclasses import dataclass

# Set max font family value to 100
p = mock.patch('openpyxl.styles.fonts.Font.family.max', new=100)
p.start()


@dataclass(init=True, slots=True)
class Offer:
    """
        Offer dataclass with self formatting methods
    """
    name: str
    brand: str
    img: str
    detail_data: str
    SKU: str
    description: str
    category: str
    price: float
    fake_price: float

    availability: int
    home_url: str

    kvant: int
    min_order: int

    weight: str = "1.0"
    dimensions: str = "10/10/10"
    
    currency: str = "RUB"
    bar_code: str = None
    upd: bool = False


class UOffer:
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
    weight: str
    dimensions: str

    def __init__(self, name, brand, img, detail_data, SKU, category, sources: list, url, weight, dimensions):
        self.name = name
        self.brand = brand
        self.img = img
        self.detail_data = detail_data
        self.SKU = SKU
        self.category = category
        self.get_best_source(sources)
        self.home_url = url
        self.weight = weight
        self.dimensions = dimensions

    def get_best_source(self, sources: list):
        best_availability = 0
        best_price = 0

        for source in sources:
            try:
                if int(source["availability"]) > best_availability:
                    best_availability = int(source["availability"])
                    best_price = source["price"]
                elif int(source["availability"]) == best_availability:
                    if source["price"] < best_price:
                        best_price = source["price"]
            except ValueError:
                continue
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


class YMLCreator:
    def __init__(self, data: list[Offer]):
        self.data: list[Offer] = data

    def create_yml(self):
        tree = ET.parse("template.xml")
        offers: list[Offer] = self.data
        root = tree.getroot()
        root.set("date", str(datetime.now()))
        offers_tag = root.find('shop').find('offers')
        categories_tag = root.find('shop').find('categories')
        all_categories = []
        for offer in offers:
            all_categories.append(offer.category)
        all_categories = list(set(all_categories))
        for index, category in enumerate(all_categories):
            new_elem = ET.SubElement(categories_tag, "category", id=str(index + 1))
            new_elem.text = category
            for offer in filter(lambda l_offer: l_offer.category == category, offers):

                new_offer_elem = ET.SubElement(offers_tag, "offer", id=offer.SKU)
                offer_name = ET.SubElement(new_offer_elem, "name")
                offer_name.text = offer.name
                image = ET.SubElement(new_offer_elem, "picture")
                image.text = offer.img
                description = ET.SubElement(new_offer_elem, "description")
                description.text = offer.description
                brand = ET.SubElement(new_offer_elem, "vendor")
                brand.text = offer.brand
                category_id = ET.SubElement(new_offer_elem, "categoryId")
                category_id.text = str(index + 1)
                if offer.bar_code is not None:
                    bar_code = ET.SubElement(new_offer_elem, "barcode")
                    bar_code.text = offer.bar_code
                else:
                    bar_code = ET.SubElement(new_offer_elem, "barcode")
                    bar_code.text = str(4000000000000 + random.randint(1000000000, 1000000000000))

                for param in offer.detail_data.split(";"):
                    if len(param.split("|")) == 2:
                        param_el = ET.SubElement(new_offer_elem, "param", name=param.split("|")[0])
                        param_el.text = param.split("|")[1]
                    elif len(param.split("|")) == 3:
                        param_el = ET.SubElement(new_offer_elem, "param", name=param.split("|")[0],
                                                 unit=param.split("|")[2])
                        param_el.text = param.split("|")[1]
                price = ET.SubElement(new_offer_elem, "price")
                price.text = str(offer.price).replace(".", ",")
                old_price = ET.SubElement(new_offer_elem, "oldprice")
                old_price.text = str(offer.fake_price).replace(".", ",")
                currency = ET.SubElement(new_offer_elem, "currencyId")
                currency.text = "RUB"
                vat = ET.SubElement(new_offer_elem, "vat")
                vat.text = "NO_VAT"
                url = ET.SubElement(new_offer_elem, "url")
                url.text = offer.home_url
                min_quantity = ET.SubElement(new_offer_elem, "min-quantity")
                min_quantity.text = str(offer.min_order)
                step_quantity = ET.SubElement(new_offer_elem, "step-quantity")
                step_quantity.text = str(offer.kvant)
                dimensions = ET.SubElement(new_offer_elem, "dimensions")
                dimensions.text = str(offer.dimensions)
                weight = ET.SubElement(new_offer_elem, "weight")
                weight.text = str(offer.weight)
                disabled = ET.SubElement(new_offer_elem, "disabled")
                if offer.upd:
                    disabled.text = "false"
                else:
                    disabled.text = "true"

                count = ET.SubElement(new_offer_elem, "count")
                if offer.upd:
                    count.text = str(offer.availability)
                else:
                    count.text = str(0)
        with open("output.yml", "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)


class ScraperWithTimeLimit:
    def __init__(self, per_day, filename):
        self.start_time = datetime.now()
        self.per_day = per_day
        self.filename = filename
        self.driver = webdriver.Chrome("chromedriver.exe")
        self.wait = WebDriverWait(self.driver, 4)
        self.to_update: list[Offer] = []
        self.updated: list[Offer] = []
        self.read_to_update()
        self.run()
        self.save_updated()

    def read_to_update(self):
        workbook = load_workbook(self.filename)
        sheet = workbook.worksheets[1]
        for index, row in enumerate(sheet.rows):
            if index > 4:
                ean: str | None = None
                detail = row[16].value.split(";")
                for d_row in detail:
                    if d_row.split("|")[0] == "EAN-13":
                        ean = d_row.split("|")[1]
                self.to_update.append(
                    Offer(SKU=row[2].value,
                          name=row[3].value,
                          img=row[4].value,
                          description=row[5].value,
                          brand=row[7].value,
                          category=row[6].value,
                          bar_code=ean,
                          detail_data=row[16].value,
                          home_url=row[17].value,
                          price=row[19].value,
                          fake_price=row[20].value,
                          kvant=0,
                          min_order=0,
                          availability=row[25].value
                          )
                )
        self.updated = self.to_update

    def save_updated(self):
        ycreator = YMLCreator(self.updated)
        ycreator.create_yml()

    def save_progress(self):
        self.updated = self.to_update
        self.save_updated()

    def solve_captcha(self) -> None:
        """
            Passes recaptcha on the driver's page
        :return:
        """

        # getting all required params
        time.sleep(2)

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
        try:
            self.driver.execute_script('$("#data").val($.urlParam("data"));')
            self.driver.execute_script('$("#form4mcRecaptcha").submit();')
        except JavascriptException:
            inputs: list[WebElement] = self.driver.find_element(By.TAG_NAME, "form").find_elements(By.TAG_NAME, 'input')
            input_tag: WebElement
            for input_tag in inputs:
                if input_tag.get_attribute("type") == "submit":
                    input_tag.click()

    def find_on_ultradar(self, sku, name) -> UOffer | None:
        self.driver.get(f"https://ultradar.ru/search/{name}/{sku}")
        return self.get_ultradar_detail()

    def get_ultradar_detail(self) -> UOffer | None:
        self.wait.until(EC.visibility_of_element_located((By.ID, "searchResultsTable")))

        table: WebElement = self.driver.find_element(By.ID, "searchResultsTable")

        table_body: WebElement = table.find_element(By.TAG_NAME, "tbody")
        try:
            img: str = self.driver.find_element(By.CLASS_NAME, "article-image").find_element(By.TAG_NAME, "img") \
                .get_attribute("src")
        except Exception as e:
            print(str(e))
            return None
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
            return None

        if len(sources) == 0:
            return None

        detail_data_el: WebElement = self.driver.find_element(By.CLASS_NAME, "infoBlock")
        detail_data_table: WebElement = detail_data_el.find_element(By.CLASS_NAME, "propertiesTable")
        brand: str = detail_data_el.find_element(By.CLASS_NAME, "article-brand").text
        number: str = detail_data_el.find_element(By.CLASS_NAME, "article-number").text
        name: str = detail_data_el.find_element(By.CLASS_NAME, "brand").text.replace(number, "").replace(brand, "") \
            .strip()
        category: str = ""
        detail_data: list[dict] = []
        tr: WebElement
        weight: str = "1"
        height: int = 100
        width: int = 100
        length: int = 100
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
            elif item_name == "Масса, кг:":
                weight = item_value
            elif item_name == "Ширина, мм:":
                width = int(item_value)
            elif item_name == "Высота, мм:":
                height = int(item_value)
            elif item_name == "Длина, мм:":
                length = int(item_value)
            else:
                detail_data.append({"name": item_name.replace(":", ""), "value": item_value})

        dimensions: str = f"{int(width)/10}/{int(height)/10}/{int(length)/10}"
        print(dimensions)
        url = self.driver.current_url + "?utm_source=yandex&utm_medium=market&utm_campaign=script"
        return UOffer(name=name, brand=brand, img=img, detail_data=detail_data, category=category,
                      sources=sources, SKU=number, url=url, weight=weight, dimensions=dimensions)

    def run(self):
        to_update_len = len(self.to_update)
        print(f"Этап займёт: {to_update_len/self.per_day} дней")
        for index, offer in enumerate(self.to_update):
            if (index+1) % self.per_day == 0:

                self.save_progress()
                print("Данные сохранены, жду сутки")
                pause.until(self.start_time+timedelta(days=1))

                self.start_time = datetime.now()
            print(index+1)
            i = 0
            invalid = False
            new_data = None
            try:
                while i <= 3:
                    i += 1
                    try:
                        print(offer.SKU)
                        new_data = self.find_on_ultradar(offer.SKU, offer.brand)
                        if new_data is not None:
                            break

                    except Exception as e:

                        print(str(e))
                        self.solve_captcha()
                        time.sleep(5)


            except Exception as e:
                print(str(e))
                continue

            if new_data is None or invalid:
                continue
            offer.price = new_data.price
            offer.fake_price = (new_data.price/100)*120
            offer.dimensions = new_data.dimensions
            offer.weight = new_data.weight
            offer.upd = True
            if new_data.availability >= 5:
                offer.availability = new_data.availability
            else:
                offer.availability = 0
            offer.kvant = 1
            offer.min_order = 1
            if offer.category.lower().find("диск") != 1 or offer.category.lower().find("disk") != 1:
                if 20 >= offer.availability > 3:
                    offer.kvant = 4
                    offer.min_order = 4


if __name__ == '__main__':
    input_per_day = int(input("Введите сколько позиций в сутки парсить \n ->>"))
    input_filename = input("Введите название и формат файла (оставить пустым если to_update.xlsx)")
    if input_filename == "":
        input_filename = "to_update.xlsx"

    scraper = ScraperWithTimeLimit(per_day=input_per_day, filename=input_filename)
