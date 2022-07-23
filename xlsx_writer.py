from openpyxl import Workbook
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


class XlsxWriter:
    template: Workbook
    sheet: Worksheet
    category_name: str

    def __init__(self, data, category_name):
        self.read_template()
        self.category_name = category_name
        self.write_new_data(data)
        self.save()

    def read_template(self):
        self.template = load_workbook('template.xlsx')
        worksheets = self.template.worksheets
        self.sheet = worksheets[1]

    def write_new_data(self, data):
        for index, offer in enumerate(data):
            self.sheet.cell(index+5, 3).value = offer.SKU
            self.sheet.cell(index+5, 4).value = offer.name
            self.sheet.cell(index+5, 5).value = offer.img
            self.sheet.cell(index+5, 6).value = offer.get_description()
            self.sheet.cell(index+5, 7).value = self.category_name
            self.sheet.cell(index+5, 8).value = offer.brand
            self.sheet.cell(index+5, 17).value = offer.get_detail_str()
            self.sheet.cell(index+5, 18).value = offer.home_url
            self.sheet.cell(index+5, 20).value = offer.price
            self.sheet.cell(index+5, 21).value = offer.get_non_sale_price()
            self.sheet.cell(index+5, 22).value = offer.currency
            self.sheet.cell(index+5, 29).value = 4
            self.sheet.cell(index+5, 30).value = 4
            print("AAA")
            self.sheet.cell(index+5, 31).value = offer.availability

    def save(self):
        self.template.save(self.category_name.replace(" ", "_")+".xlsx")


if __name__ == '__main__':
    a = XlsxWriter()
    a.read_template()