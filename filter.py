import time
import xml.etree.ElementTree as ET


while True:
    tree = ET.parse('output.yml')
    root = tree.getroot()
    for offer in root.find("shop").find("offers").findall("offer"):
        try:
            if float(offer.find("price").text.replace(",", ".")) < 3000:
                offer.find("disabled").text = "true"
            if offer.find("categoryId").text == "2":
                offer.find("disabled").text = "true"
        except ValueError:
            pass

    with open("output.yml", "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)
    time.sleep(3600)