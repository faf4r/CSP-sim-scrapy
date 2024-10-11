# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ProblemItem(scrapy.Item):
    # contest info
    contest_id = scrapy.Field()
    contest_title = scrapy.Field()
    contest_date = scrapy.Field()

    # problem info
    problem_number = scrapy.Field()
    title = scrapy.Field()
    description_url = scrapy.Field()
    description_filepath = scrapy.Field()
    description = scrapy.Field()
    attachment_urls = scrapy.Field()

    # flags to indicate whether the problem has been processed
    done = scrapy.Field()
