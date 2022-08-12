from datetime import datetime
from unittest import mock
# Set max font family value to 100
p = mock.patch('openpyxl.styles.fonts.Font.family.max', new=100)
p.start()

from openpyxl import load_workbook
from openpyxl import Workbook

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, JavascriptException
from VARS import RUCAPTCHA_KEY
import time

from python_rucaptcha import ReCaptchaV2, RuCaptchaControl, CallbackClient
import xml.etree.ElementTree as ET

from dataclasses import dataclass


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
    
    currency: str = "RUB"
    bar_code: str = None


class YMLCreator:
    def __init__(self, data: list[Offer]):
        self.data: list[Offer] = data

    def create_yml(self):
        tree = ET.parse("template.xml")
        root = tree.getroot()


class ScraperWithTimeLimit:
    def __init__(self, per_day, filename):
        self.per_day = per_day
        self.filename = filename
        self.to_update: list[Offer] = []
        self.updated: list[Offer] = []
        self.read_to_update()
        self.save_updated()
        self.run()
        # self.driver = webdriver.Chrome("chromedriver.exe")

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
        tree = ET.parse("template.xml")
        offers: list[Offer] = self.updated
        root = tree.getroot()
        root.set("date", str(datetime.now()))
        offers_tag = root.find('shop').find('offers')
        categories_tag = root.find('shop').find('categories')
        all_categories = []
        for offer in offers:
            all_categories.append(offer.category)
        all_categories = list(set(all_categories))
        for index, category in enumerate(all_categories):
            new_elem = ET.SubElement(categories_tag, "category", id=str(index+1))
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
                category_id.text = str(index+1)
                if offer.bar_code is not None:
                    bar_code = ET.SubElement(new_offer_elem, "barcode")
                    bar_code.text = offer.bar_code

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
                currency = ET.SubElement(new_offer_elem, "currencyID")
                currency.text = "RUB"
                vat = ET.SubElement(new_offer_elem, "vat")
                vat.text = "NO_VAT"
                url = ET.SubElement(new_offer_elem, "url")
                url.text = offer.home_url
                count = ET.SubElement(new_offer_elem, "count")
                count.text = "0"
                min_quantity = ET.SubElement(new_offer_elem, "min-quantity")
                min_quantity.text = offer.min_order
                step_quantity = ET.SubElement(new_offer_elem, "step-quantity")
                step_quantity.text = offer.kvant
                available = ET.SubElement(new_offer_elem, "available")
                available.text = "false"
                count = ET.SubElement(new_offer_elem, "count")
                count.text = str(offer.availability)


        with open("output.yml", "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
        print("Yay")

    def save_progress(self):
        pass

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

    def find_on_ultradar(self):
        pass

    def run(self):
        pass



if __name__ == '__main__':
    input_per_day = int(input("Введите сколько позиций в сутки парсить \n ->>"))
    input_filename = input("Введите название и формат файла (оставить пустым если to_update.xlsx)")
    if input_filename == "":
        input_filename = "to_update.xlsx"

    scraper = ScraperWithTimeLimit(per_day=input_per_day, filename=input_filename)