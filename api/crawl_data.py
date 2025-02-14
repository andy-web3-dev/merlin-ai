import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse

# requests slow due to ipv6 connection
# https://stackoverflow.com/questions/62599036/python-requests-is-slow-and-takes-very-long-to-complete-http-or-https-request
requests.packages.urllib3.util.connection.HAS_IPV6 = False

max_page_depth = 4
crawl_histories = {}

def get_dapps():
    data_range = 'DApp!A2:E100'
    sheet_id = '1hEkmaFzEYcm9qO0KG0sfDrQzNYmLdjeXTdmHpuFrCnY'
    api_key = os.environ.get('GOOGLE_SHEET_API_KEY')
    url = "https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{data_range}?majorDimension=ROWS&key={api_key}".format(
        data_range=data_range, sheet_id=sheet_id, api_key=api_key)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["values"]
    else:
        return []


def crawl_app(app):
    app_name = app[0]
    print("Crawling app {}".format(app[0]))
    app_landing_page = ""
    if len(app) > 1:
        app_landing_page = app[1]
    app_category = ""
    if len(app) > 2:
        app_category = app[2]
    app_insights = ""
    if len(app) > 3:
        app_insights = app[3]
    app_documentation = ""
    if len(app) > 4:
        app_documentation = app[4]
    output_path = f"./data/ecosystem/{app_name}.txt"
    file = open(output_path, "w")
    file.write(f"App name: {app_name}\n")
    file.write(f"Landing page: {app_landing_page}\n")
    file.write(f"App category: {app_category}\n")
    file.write(f"App insights: \n{app_insights}\n")
    file.write(f"App documentation: {app_documentation}\n")
    file.close()
    crawl_page(app)
    pass


def crawl_page(app):
    app_name = app[0]
    if len(app) > 4:
        app_documentation = app[4]
        base_page = get_base_document_domain(app_documentation)
        response = requests.get(app_documentation, timeout=5)
        output_path = f"./data/ecosystem/{app_name}.txt"
        if response.status_code != 200:
            return
        else:
            soup = BeautifulSoup(response.text, 'html.parser')
            file = open(output_path, "a")
            file.write(soup.get_text(separator='\n'))
            file.write("\n")
            file.close()
            for i in soup.find_all('a', href=True):
                href = i['href']
                if href.startswith('/') and href != '/':
                    crawl_sub_page(app_name, f'{base_page}{href}', 1)


def crawl_sub_page(app_name, page, page_dep):
    if page_dep > max_page_depth:
        return
    if app_name in crawl_histories and page in crawl_histories[app_name]:
        return
    print("Crawling sub page {}".format(page))
    if app_name not in crawl_histories:
        crawl_histories[app_name] = []
    base_page = get_base_document_domain(page)
    response = requests.get(page, timeout=5)
    output_path = f"./data/ecosystem/{app_name}.txt"
    if response.status_code != 200:
        return
    else:
        soup = BeautifulSoup(response.text, 'html.parser')
        file = open(output_path, "a")
        file.write(soup.get_text(separator='\n'))
        file.write("\n")
        file.close()
        crawl_histories[app_name].append(page)
        for i in soup.find_all('a', href=True):
            href = i['href']
            if href.startswith('/') and href != '/':
                crawl_sub_page(app_name, f'{base_page}{href}', page_dep + 1)

def get_base_document_domain(document_url):
    url_parse = urlparse(document_url)
    return f"{url_parse.scheme}://{url_parse.netloc}"

apps = get_dapps()
print(apps)
for app in apps:
    crawl_app(app)