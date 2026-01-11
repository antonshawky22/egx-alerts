print("EGX OFFICIAL SOURCE TEST")

import requests
import pandas as pd

url = "https://www.egx.com.eg/ar/CompanyDetails.aspx?ISIN=EGS33041C012&type=C"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers, timeout=30)

if response.status_code != 200:
    print("❌ Failed to load page")
    exit()

# قراءة الجداول من الصفحة
tables = pd.read_html(response.text)

close_price = None
trade_date = None

for table in tables:
    for col in table.columns:
        if "سعر الإقفال" in str(col):
            close_price = table[col].iloc[0]
        if "تاريخ" in str(col):
            trade_date = table[col].iloc[0]

if close_price:
    print("✅ EGX Close Price:", close_price)
    print("📅 Date:", trade_date)
else:
    print("❌ Close price not found")
