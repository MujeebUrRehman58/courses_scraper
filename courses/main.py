from scrapy import cmdline
# Replace 'json/scraped_data.json' with your json data file path
cmdline.execute("scrapy crawl courses_spider -o json/scraped_data.json".split())