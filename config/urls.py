SOURCES = {
    "longchau": {
        "base_url": "https://nhathuoclongchau.com.vn",
        "list_url": "https://nhathuoclongchau.com.vn/thuoc?page={page}",
        "spider": "spiders.longchau.product_spider_optimized.LongChauOptimizedSpider",
        "enabled": True,
        # max_pages = số trang Selenium scroll mỗi category
        # 18 categories × 5 pages = 90 lần scroll → ~400-600 sản phẩm
        "max_pages": 5,
    },
    "thuocbietduoc": {
        "base_url": "https://thuocbietduoc.com.vn",
        "list_url": "https://thuocbietduoc.com.vn/thuoc/drgsearch.aspx",
        "spider": "spiders.thuocbietduoc.product_spider.ThuocBietDuocSpider",
        "enabled": True,
        # max_pages = số trang pagination mỗi nhóm thuốc
        # 35 nhóm × 3 pages × ~20 thuốc/trang = ~2100 thuốc (nhiều hơn cần)
        "max_pages": 3,
    },
    "vinmec": {
        "base_url": "https://www.vinmec.com",
        "list_url": "https://www.vinmec.com/sitemap/posts-vi-{page}.xml",
        "spider": "spiders.vinmec.article_spider.VinmecSpider",
        "enabled": True,
        # max_pages = số file sitemap đọc (mỗi file 1000 URLs)
        # 2 files = 2000 URLs, lọc còn ~1000 bài y tế → đủ 1000 câu
        "max_pages": 2,
    },
    "suckhoedoisong": {
        "base_url": "https://suckhoedoisong.vn",
        "list_url": "https://suckhoedoisong.vn/thuoc-va-suc-khoe.htm",
        "spider": "spiders.suckhoedoisong.article_spider.SucKhoeDoiSongSpider",
        "enabled": True,
        # max_pages = số category pages crawl (mỗi category ~50 bài)
        # 22 categories × 50 bài = ~1000 bài unique → đủ 600 câu
        "max_pages": 22,
    },
}
