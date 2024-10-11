from datetime import datetime

import scrapy
from scrapy.http import Request
from CSP_sim_scrapy.items import ProblemItem

class CSP_sim_Spider(scrapy.Spider):
    name = "CSP_sim_Spider"
    start_urls = ["https://sim.csp.thusaac.com/api/contest/list"]

    def parse(self, response):
        for contest in response.json()["contests"]:
            _id = contest["_id"]
            contest_title = contest["title"]
            start_ts = int(contest["startTime"]) / 1000
            date = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d")
            init_item = ProblemItem(
                contest_id = _id,
                contest_title = contest_title,
                contest_date = date
            )
            yield Request(
                url=f"https://sim.csp.thusaac.com/api/contest/{_id}/problem/list",
                callback=self.parse_content,
                cb_kwargs={"init_item": init_item},
            )

    def parse_content(self, response, init_item):
        for i in range(len(response.json()["problems"])):
            problem_config_url = f"https://sim.csp.thusaac.com/api/contest/{init_item["contest_id"]}/problem/{i}/config"
            item = init_item.copy()
            item["problem_number"] = i + 1
            yield Request(
                url=problem_config_url,
                callback=self.parse_problem_config,
                cb_kwargs={"item": item},
            )

    def parse_problem_config(self, response, item):
        config = response.json()["config"]
        problem_title = config["title"]
        description_code = config["description"]
        description_url = f"https://sim.csp.thusaac.com/staticdata/{description_code}.description"
        item["title"] = problem_title
        item["description_url"] = description_url
        return item
