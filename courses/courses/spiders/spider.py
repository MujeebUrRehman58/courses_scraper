# -*- coding: UTF-8 -*-
import json
from urllib.parse import urlparse
import pathlib
from datetime import datetime as dt
from datetime import timedelta
import re
import csv

import scrapy
from ..items import CourseItem
from unidecode import unidecode
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options

OBBY_NETLOC = 'obby.co.uk'
CRAFT_NETLOC = 'www.craftcourses.com'
cancellation = 'Rigid'
suitable_for = 'Both'
chrome_options = Options()
chrome_options.add_argument("--headless")


def is_url_valid(parsed_url):
    return all([parsed_url.scheme, parsed_url.netloc, parsed_url.path])


def wait_for_element_by_css(driver, path):
    element = None
    while True:
        try:
            element = driver.find_element_by_css_selector(path)
            break
        except NoSuchElementException:
            continue
    return element


def get_age_group(age):
    """
        Child 	  05 to 12
        Teenager  13 to 19
        Adult	  18+
    """
    if (isinstance(age, int) and age <= 12) or str(age) == 'children':
        return 5
    elif (isinstance(age, int) and age <= 18) or str(age) == 'teenagers':
        return 2
    elif (isinstance(age, int) and age <= 65) or str(age) == 'adults':
        return 1
    else:
        return 0


class CoursesSpider(scrapy.Spider):
    name = "courses_spider"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.map_call_back = {
            OBBY_NETLOC: self.parse_obby,
            CRAFT_NETLOC: self.parse_craft
        }

    def start_requests(self):
        urls = []
        with open(f'{pathlib.Path(__file__).parent.absolute()}/urls.csv', 'r') as f:
            reader = csv.reader(f, delimiter=',')
            for row in reader:
                urls.append(row)
        for url in urls:
            parsed_url = urlparse(url[0])
            if is_url_valid(parsed_url) and self.map_call_back.get(parsed_url.netloc):
                yield scrapy.Request(url=url[0], callback=self.map_call_back[parsed_url.netloc],
                                     errback=self.err_back, meta={'url': url[0], 'category': url[1], 'sub': url[2]})

    def parse_obby(self, response):
        def make_address(obj):
            return dict(
                postal_code=obj.get('postcode', '').strip(),
                street=obj.get('line2', '').strip(),
                city=obj.get('city', '').strip(),
                venue=obj.get('line1', '').strip(),
                country=obj.get('country', '').strip()
            ) if isinstance(obj, dict) else obj

        def make_products(dates, teacher):
            _products = []
            for d in dates:
                start_date = dt.strptime(d['startDateTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                end_date = start_date + timedelta(minutes=d['duration'])
                _products.append(
                    {
                        'timing': [{'value': start_date, 'value2': end_date}],
                        'discounted_price': d['price']/100,
                        "initial_price": None,
                        'start_date': start_date,
                        'end_date': end_date,
                        'sessions': d['duration']/60,
                        'batch_size': d['totalAvailability'],
                        'tutor': teacher,
                        'stock': d['totalAvailability'] - d['availability'],
                        'trial_class': None,
                        'status': 1
                    }
                )
            return _products

        script = json.loads(response.css('#__NEXT_DATA__::text').extract_first())['props']['pageProps']['data']
        title = script['title']
        category = [response.meta['category'], response.meta['sub']]
        course_requirements = script['notes']
        session = script['singleSession']
        description = session['description']
        short_description = script['shortDescription']
        tutor = response.css('.teacher-card__title-link::text').extract_first()
        address = make_address(script['address'] or {})
        age = get_age_group(script['requirements'])
        products = make_products(session['dates'], tutor)
        image_urls = [i['url'] for i in script['galleryImages']]
        yield CourseItem(
            extracted_from='obby', title=title, category=category, youtube=[],
            money_back_guarantee=1, course_requirements=course_requirements,
            certification=[], address=address, images_fids=[], description=description,
            short_description=short_description, cancellation=cancellation,
            suitable_for=suitable_for, amenities=[], age=age, products=products, image_urls=image_urls
        )

    def parse_craft(self, response):
        def make_age(course_checklist):
            checklist = ['children', 'teenagers', 'adults']
            for i in course_checklist:
                i = i.strip().lower()
                if i in checklist:
                    return i
            return None

        def make_products(teacher, _price, sessions):
            driver = webdriver.Chrome(f'{pathlib.Path(__file__).parent.absolute()}/chromedriver/chromedriver',
                                      chrome_options=chrome_options)
            driver.set_window_size(1804, 1096)
            driver.get(response.meta['url'])
            css = '.vc-h-full span:not(.vc-text-gray-400)'
            wait_for_element_by_css(driver, css)
            dates = []
            _products = []
            next_btn = driver.find_elements_by_css_selector('div.vc-arrows-container .vc-flex')[1]
            for i in range(2):
                for e in driver.find_elements_by_css_selector(css) or []:
                    try:
                        date = e.get_attribute('aria-label')
                        if date and date not in dates:
                            dates.append(date)
                            _products.append(
                                {
                                    'timing': [{'value': date, 'value2': date}],
                                    'discounted_price': price,
                                    "initial_price": None,
                                    'start_date': date,
                                    'end_date': date,
                                    'sessions': sessions,
                                    'batch_size': None,
                                    'tutor': teacher,
                                    'stock': None,
                                    'trial_class': None,
                                    'status': 1
                                }
                            )
                    except Exception as e:
                        continue
                next_btn.click()
            driver.close()
            return _products

        title = unidecode(response.css('.course-title::text').extract_first())
        category = [response.meta['category'], response.meta['sub']]
        tutor_and_venue = ''.join(response.css('.course-description .read-more::text').extract()).strip()
        description = unidecode(''.join(response.css('.course-description .read-more p::text').extract()).strip())
        short_description = ''
        price_row = response.css('.price::text').extract()
        price = int(re.findall(r'\d+', price_row[0])[0])
        duration = price_row[1] if len(price_row) > 1 else None
        address = {'street': unidecode(' '.join(response.css('address::text').extract())), 'venue': tutor_and_venue}
        course_requirements = ''
        amenities = [a.strip() for a in response.xpath("//h2[contains(text(), "
                     "'included in the price?')]""/following-sibling::p/text()").extract()]
        age = get_age_group(make_age(response.css('.course-checklists li::text').extract()))
        products = make_products(tutor_and_venue, price, duration)
        image_urls = response.css('.course-slideshow a::attr(data-href)').extract()
        yield CourseItem(
            extracted_from='craft-courses', title=title, category=category, youtube=[],
            money_back_guarantee=0, course_requirements=course_requirements,
            certification=[], address=address, images_fids=[], description=description,
            short_description=short_description, cancellation=cancellation, amenities=amenities,
            suitable_for=suitable_for, age=age, products=products, image_urls=image_urls
        )

    def err_back(self, response):
        pass

