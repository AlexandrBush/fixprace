import scrapy
import time
from urllib.parse import urljoin
from scrapy_playwright.page import PageMethod

class FixpriceSpider(scrapy.Spider):
    name = 'fixprice_spider'
    allowed_domains = ['fix-price.com']
    start_urls = [
        'https://fix-price.com/catalog/kosmetika-i-gigiena/ukhod-za-polostyu-rta?region=Екатеринбург',
        #'https://fix-price.com/catalog/bytovaya-khimiya?region=Екатеринбург',
        #'https://fix-price.com/catalog/produkty-i-napitki/chay-kofe-sakhar?region=Екатеринбург'
    ]
    custom_settings = {
        'FEEDS': {
            'output.json': {
                'format': 'json',
                'encoding': 'utf8',
            }
        },
        'RETRY_TIMES': 10,
        'DOWNLOAD_DELAY': 2,
        'HTTP_PROXY': 'http://your_proxy:port',  # Укажите ваш прокси
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'div.product-item')
                    ],
                    'region': 'Екатеринбург'
                }
            )

    def parse(self, response):
        products = response.css('div.product-item')
        for product in products:
            item = {
                'timestamp': int(time.time()),
                'RPC': product.css('::attr(data-product-id)').get(),
                'url': urljoin(response.url, product.css('a::attr(href)').get()),
                'title': product.css('div.product-title::text').get().strip(),
                'marketing_tags': product.css('div.product-tags::text').getall(),
                'brand': product.css('div.product-brand::text').get(),
                'section': response.css('ul.breadcrumbs li a::text').getall(),
                'price_data': {
                    'current': float(product.css('div.product-price-current::text').get().replace('₽', '').strip()),
                    'original': float(product.css('div.product-price-old::text').get().replace('₽', '').strip()),
                    'sale_tag': f"Скидка {int((1 - (float(product.css('div.product-price-current::text').get().replace('₽', '').strip()) / float(product.css('div.product-price-old::text').get().replace('₽', '').strip()))) * 100)}%"
                },
                'stock': {
                    'in_stock': 'Нет в наличии' not in product.css('div.product-stock::text').get(),
                    'count': int(product.css('div.product-stock::attr(data-stock)').get()) if product.css('div.product-stock::attr(data-stock)').get() else 0
                },
                'assets': {
                    'main_image': urljoin(response.url, product.css('img.product-image::attr(src)').get()),
                    'set_images': [urljoin(response.url, img) for img in product.css('div.product-images img::attr(src)').getall()],
                    'view360': [],
                    'video': []
                },
                'metadata': {
                    '__description': product.css('div.product-description::text').get().strip(),
                    **{detail.css('::attr(data-key)').get(): detail.css('::attr(data-value)').get() for detail in product.css('div.product-details div.detail-item')}
                },
                'variants': len(product.css('div.product-variants option'))
            }
            yield item

        next_page = response.css('a.pagination-next::attr(href)').get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)