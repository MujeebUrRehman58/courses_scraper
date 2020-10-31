# -*- coding: UTF-8 -*-
import json
from urllib.parse import urlparse
import pathlib
from datetime import datetime as dt
from datetime import timedelta
import re
import csv
import requests
from time import sleep

import scrapy
from bs4 import BeautifulSoup as BS
from unidecode import unidecode
from dateutil.parser import parse as date_parser

from ..items import CourseItem

user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'
session = requests.session()
session.headers = {'User-Agent': user_agent}
OBBY_NETLOC = 'obby.co.uk'
CRAFT_NETLOC = 'www.craftcourses.com'
cancellation = 'Rigid'
suitable_for = 'Both'
offer_valid_from = '6-Jun-2020 16:30'
offer_valid_untill = '21-Aug-2021 17:30'


def is_url_valid(parsed_url):
    return all([parsed_url.scheme, parsed_url.netloc, parsed_url.path])


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


def strf_course_date(obj):
    return obj.strftime("%-d-%b-%Y")


def extract_category(meta):
    return [int(meta['category']), int(meta['sub'])]


def safe_get_by_index(obj, index):
    try:
        val = '' if obj[index] in ['at', 'and'] else obj[index]
    except:
        val = ''
    return val


def safe_get_request(url):
    res = None
    try:
        res = session.get(url, timeout=(15, 60))
    except Exception:
        print(f'Could not get {url}\nRetrying with delay now.')
        try:
            sleep(5)
            res = session.get(url)
        except:
            print(f'Retry with delay failed as well for {url}. Skipping..')
    return res


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
                                     errback=self.err_back, meta={'category': url[1], 'sub': url[2],
                                                                  'owner': safe_get_by_index(url, 3)})

    def parse_obby(self, response):
        def make_address(obj):
            return dict(
                postal_code=obj.get('postcode', '').strip(),
                street=obj.get('line1', obj.get('line2', '')).strip(),
                city=obj.get('city', '').strip(),
                venue=obj.get('line2', 'some venue').strip(),
                country="gb"
            ) if isinstance(obj, dict) else obj

        def make_products(dates, teacher):
            _products = []
            dates = dates if dates else [{'startDateTime': '2020-11-27T18:30:00.000Z'}]
            for d in dates:
                start_date = dt.strptime(d['startDateTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                end_date = start_date + timedelta(minutes=d.get('duration', 360))
                _products.append(
                    {
                        'timing': [{'value': start_date, 'value2': end_date}],
                        'discounted_price': d.get('price', 5000)/100,
                        "initial_price": d.get('price', 5000)/100,
                        'start_date': strf_course_date(start_date),
                        'end_date': strf_course_date(end_date),
                        'sessions': 1,
                        'batch_size': d.get('totalAvailability', 5),
                        'tutor': teacher,
                        'stock': d.get('totalAvailability', 5),
                        'trial_class': 0,
                        'status': 1
                    }
                )
            return _products

        script = json.loads(response.css('#__NEXT_DATA__::text').extract_first())['props']['pageProps']['data']
        title = script['title']
        category = extract_category(response.meta)
        owner = response.meta['owner']
        title = f'{title} - {owner}' if owner else title
        course_requirements = script.get('notes', '')
        session = script['singleSession']
        description = session['description']
        short_description = script.get('shortDescription', title)
        tutor = response.css('.teacher-card__title-link::text').extract_first()
        address = make_address(script.get('address'))
        session_type = 'online' if not address else 'offline'
        age = get_age_group(script['requirements'])
        products = make_products(session['dates'], tutor)
        image_urls = [i['url'] for i in script['galleryImages']]
        yield CourseItem(
            extracted_from='obby', session_type=session_type, title=title, category=category, youtube=[],
            money_back_guarantee=0, course_requirements=course_requirements, certification=[], address=address,
            images_fids=[], description=description, short_description=short_description, cancellation=cancellation,
            suitable_for=suitable_for, amenities=[], age=age, offer_valid_from=offer_valid_from,
            offer_valid_untill=offer_valid_untill, products=products, image_urls=image_urls
        )

    def parse_craft(self, response):
        def make_address(_address):
            return dict(
                postal_code=_address[-1].strip(),
                street=_address[1].strip(),
                city=_address[-2].strip(),
                venue=_address[0].strip(),
                country="gb"
            ) if _address else _address

        def make_age(course_checklist):
            checklist = ['children', 'teenagers', 'adults']
            for i in course_checklist:
                i = i.strip().lower()
                if i in checklist:
                    return i
            return None

        def parse_craft_dates(url, teacher, price):
            res = None
            date_format = '%d %B %Y'
            if url:
                res = safe_get_request(url)
            _products = []
            if res:
                res = BS(res.content, 'html.parser')
                dates = [str(d.find(text=True, recursive=False)).strip() for d in
                         res.select('#course-list .course-card')[:90]]
            else:
                date = response.css('.next-date::text').extract_first()
                dates = [date_parser(date).strftime(date_format)] if date else []
            dates = dates if dates else [dt.now().strftime(date_format)]
            for date in dates:
                date = dt.strptime(date, date_format)
                _products.append(
                    {
                        'timing': [{'value': date, 'value2': date}],
                        'discounted_price': price,
                        "initial_price": price,
                        'start_date': strf_course_date(date),
                        'end_date': strf_course_date(date),
                        'sessions': 1,
                        'batch_size': 5,
                        'tutor': teacher,
                        'stock': 5,
                        'trial_class': 0,
                        'status': 1
                    }
                )
            return _products

        title = unidecode(response.css('.course-title::text').extract_first())
        category = extract_category(response.meta)
        owner = response.meta['owner']
        title = f'{title} - {owner}' if owner else title
        tutor = ''.join(response.css('.course-description .read-more::text').extract()).strip().split(' ')
        tutor = (safe_get_by_index(tutor, 0) + ' ' + safe_get_by_index(tutor, 1)).strip()
        description = unidecode(''.join(response.css('.course-description .read-more p::text').extract()).strip())
        price_row = response.css('.price::text').extract()
        price = int(re.findall(r'\d+', price_row[0])[0])
        address = make_address(response.css('address::text').extract())
        session_type = 'online' if not address else 'offline'
        age = get_age_group(make_age(response.css('.course-checklists li::text').extract()))
        dates_url = response.css('.course-side-bar .btn.btn-primary.btn-block::attr(href)').extract_first()
        products = parse_craft_dates(dates_url, tutor, price)
        image_urls = response.css('.course-slideshow a::attr(data-href)').extract() or [response.css(
            '.row .text-center img::attr(data-src)').extract_first()]
        yield CourseItem(
            extracted_from='craft-courses', title=title, session_type=session_type, category=category, youtube=[],
            money_back_guarantee=0, course_requirements='', certification=[], address=address, images_fids=[],
            description=description, short_description=title, cancellation=cancellation, amenities=[],
            suitable_for=suitable_for, age=age, offer_valid_from=offer_valid_from,
            offer_valid_untill=offer_valid_untill, products=products, image_urls=image_urls
        )

    def err_back(self, response):
        pass

