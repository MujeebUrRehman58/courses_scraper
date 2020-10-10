# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CourseItem(scrapy.Item):
    extracted_from = scrapy.Field()
    title = scrapy.Field()
    category = scrapy.Field()
    youtube = scrapy.Field()
    money_back_guarantee = scrapy.Field()
    course_requirements = scrapy.Field()
    certification = scrapy.Field()
    address = scrapy.Field()
    images_fids = scrapy.Field()
    description = scrapy.Field()
    short_description = scrapy.Field()
    cancellation = scrapy.Field()
    suitable_for = scrapy.Field()
    amenities = scrapy.Field()
    age = scrapy.Field()
    products = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
