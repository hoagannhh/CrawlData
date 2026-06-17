#!/usr/bin/env python3
"""
Test the optimized Long Châu spider
"""

import sys
sys.path.insert(0, '.')

from spiders.longchau.product_spider_optimized import LongChauOptimizedSpider

print("=" * 70)
print("Testing Optimized Long Châu Spider")
print("=" * 70)

spider = LongChauOptimizedSpider()

# Run with limited pages for testing
results = spider.run(max_pages=3)

print(f"\n" + "=" * 70)
print(f"✅ RESULTS: {len(results)} products scraped")
print("=" * 70)

if results:
    print("\nFirst 5 products:")
    for idx, product in enumerate(results[:5], 1):
        print(f"\n{idx}. {product['name'][:50]}")
        print(f"   SKU: {product['sku']}")
        print(f"   Price: {product['price']}")
        print(f"   Category: {product['category']}")
        print(f"   URL: {product['url'][:70]}")

print(f"\n✅ Test completed successfully!")
