import os

import requests
import pdfplumber



def download_file(url):
    local_filename = url.split('/')[-1]
    
    with requests.get(url) as r:
        assert r.status_code == 200, f'error, status code is {r.status_code}'
        with open(local_filename, 'wb') as f:
            f.write(r.content)
        
    return local_filename


invoice = 'https://seller-us.tiktok.com/wsos_v2/oec_fulfillment_doc_tts/object/wsos65b0b4e9841e8b2b?expire=1706165948&skipCookie=true&timeStamp=1706079548&sign=1953a9e05c3ae5c9eea322f77c0319510414b742234ce9d8447602dace39ea52'
invoice_pdf = download_file(invoice)

print(invoice_pdf)

with pdfplumber.open(invoice_pdf) as pdf:
    page = pdf.pages[0]
    text = page.extract_text()
    print(text)

os.system(f'ocrmypdf {invoice_pdf} output.pdf')
with pdfplumber.open('output.pdf') as pdf:
    page = pdf.pages[0]
    text = page.extract_text(x_tolerance=2)
    print(text)

lines = text.split('\n')
print(lines)