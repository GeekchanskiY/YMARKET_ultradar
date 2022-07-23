from openpyxl import Workbook
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


class XlsxWriter:
    template: Workbook
    sheet: Worksheet

    def __init__(self, data):
        self.read_template()

    def read_template(self):
        self.template = load_workbook('template.xlsx')
        worksheets = self.template.worksheets
        self.sheet = worksheets[1]


if __name__ == '__main__':
    a = XlsxWriter()
    a.read_template()