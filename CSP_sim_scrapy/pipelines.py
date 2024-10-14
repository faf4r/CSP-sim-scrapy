# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from pathlib import Path
from urllib.parse import urljoin
import re

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from scrapy import Request
from scrapy.http.request import NO_CALLBACK
from scrapy.utils.defer import maybe_deferred_to_future
from twisted.internet.defer import DeferredList


# 参考https://docs.scrapy.org/en/latest/topics/item-pipeline.html#take-screenshot-of-item的写法
# 即https://docs.scrapy.org/en/latest/topics/coroutines.html#inline-requests
# 但也许可以用内置的FilesPipeline实现
class ProblemPipeline:
    """
    1. numbered the problem title
    2. download and set the problem description
    """
    async def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if adapter.get("done"):
            return item

        # numbered the problem title
        adapter["title"] = f"{adapter['problem_number']}.{adapter['title']}"

        # download and set the problem description
        request = Request(adapter["description_url"], callback=NO_CALLBACK)
        response = await maybe_deferred_to_future(
            spider.crawler.engine.download(request)
        )
        if response.status != 200:
            raise DropItem(f"Failed to download "
                           f"{adapter['contest_title']}-{adapter['title']}: "
                           f"{adapter['description_url']}")

        adapter["description"] = response.text
        adapter["description_filepath"] = Path(spider.settings["OUTPUT_DIR"]) / adapter["contest_title"]
        adapter["description_filepath"].mkdir(parents=True, exist_ok=True)
        # 不写入，经过后面处理完文本内路径后写入

        return item


class AttachmentPipeline:
    """extract attachment urls(zip and images) and download attachment"""
    async def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if not adapter.get("description"):  # 未经ProblemPipeline处理
            return item
        if adapter.get("done"):  # 已经处理过
            return item
        adapter["done"] = True  # 标记已处理

        description = adapter["description"]
        attachment_related_urls = re.findall("/staticdata/down/.*?.zip", description)  # extract attachment url
        image_related_urls = re.findall('src="(/staticdata/.*?)"', description)  # extract image urls
        attachment_related_urls.extend(image_related_urls)

        if not attachment_related_urls:
            return item
        attachment_urls = [urljoin("https://sim.csp.thusaac.com", url) for url in attachment_related_urls]

        # download attachments
        deferred_list = []
        for attachment_url in attachment_urls:
            request = Request(attachment_url, callback=NO_CALLBACK)
            deferred = spider.crawler.engine.download(request)
            deferred_list.append(deferred)
        result = await maybe_deferred_to_future(DeferredList(deferred_list))

        # save attachment
        file_dir = adapter["description_filepath"] / "attachment"
        file_dir.mkdir(exist_ok=True)

        # result变量将包含一个列表，该列表中的每个元素是一个元组，表示每个Deferred的结果。这个元组通常有两种形式：
        # (True, result)：如果对应的Deferred成功完成，result是回调链最终返回的结果。
        # (False, failure)：如果对应的Deferred因错误而终止，failure是一个Failure实例，代表发生的异常。
        for i, (success, response) in enumerate(result):
            if not success:
                continue
            file_name = attachment_urls[i].split("/")[-1]
            file_path = file_dir / file_name
            file_path.write_bytes(response.body)

            # replace path in the description
            related_path = file_path.relative_to(adapter["description_filepath"])
            adapter["description"] = adapter["description"].replace(
                attachment_related_urls[i], str(related_path)
            )

        return item
    

class DonePipeline:
    """store the processed description"""
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if not adapter.get("done"):
            return item
        
        file_path = adapter["description_filepath"] / f"{adapter['title']}.md"
        file_path.write_text(adapter["description"], encoding="utf-8")
        adapter["description"] = ""  # 避免log大段文字
        return item
