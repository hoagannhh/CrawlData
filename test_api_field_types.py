#!/usr/bin/env python3
"""
Debug - xem API trả về dạng gì cho category field
"""

import requests

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://nhathuoclongchau.com.vn/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "X-Channel": "EStore",
    "order-channel": "1",
}

api_url = "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product/without-inventory/search/list"

test_skus = ["00004206", "00009723", "00002990"]

r = requests.post(api_url, json=test_skus, headers=headers, timeout=10)

if r.status_code == 200:
    products = r.json()
    
    print(f"Total products: {len(products)}\n")
    
    for idx, p in enumerate(products[:3], 1):
        print(f"Product {idx}: {p.get('name')[:40]}")
        
        # Check type of each field
        for field in ['category', 'webName', 'specification', 'shortDescription', 'slug', 'price']:
            val = p.get(field)
            val_type = type(val).__name__
            print(f"  {field}: {val_type}")
            if val_type == 'list':
                print(f"    → Content: {val}")
            elif isinstance(val, str):
                print(f"    → Value: {val[:60]}")
            else:
                print(f"    → Value: {val}")
