import aiohttp
import argparse
import asyncio
import datetime
import logging
import os
import re
import time
from glob import glob
from multiprocessing.dummy import Pool as ThreadPool, Queue
from urllib.parse import urlparse, urljoin, urlunparse


REG_FIND_LINK = re.compile("""(?i)(?:href|src)=['"]([^"'>\s]*)""")
REG_DEFINATELY_NOT_TEXT = re.compile("""(?i)\.(?:png|jpg|jpeg|pdf|mp4|doc)$""")
REG_IS_LOGIN_PAGE = re.compile("""(?:signin|login)""")

MAX_FILENAME_LENGTH = 255

SUPPORTED_CONTENT_TYPES = (
    'application/javascript',
    'application/json',
    'application/xml',
    'text/css',
    'text/html',
    'text/plain',
)


class Crawler(object):
    loop = None
    domain = None
    threads_number = None
    http_timeout = None
    requests_semaphore = None
    thread_pool = None
    processing_links = set()

    def __init__(self, max_requests=10, threads_number=4, http_timeout=60):
        self.loop = asyncio.get_event_loop()
        self.threads_number = threads_number
        self.http_timeout = http_timeout
        self.requests_semaphore = asyncio.Semaphore(max_requests)
        self.thread_pool = ThreadPool(threads_number)

    def parse_links(self, text):
        return REG_FIND_LINK.findall(text)

    def filter_link(self, link):
        parsed_link = urlparse(link)
        if parsed_link.scheme not in ("http", "https", ""):
            return False
        if parsed_link.netloc == '' and parsed_link.path == '' and parsed_link.query == '':
            return False
        if parsed_link.netloc == '' or parsed_link.netloc == self.domain:
            if REG_DEFINATELY_NOT_TEXT.search(parsed_link.path):
                return False
            if REG_IS_LOGIN_PAGE.search(parsed_link.path) and ("next" in parsed_link.query):
                return False
            return True
    
    def prepare_link(self, source_url, link):
        parsed_res = urlparse(urljoin(source_url, link))
        res = urlunparse((parsed_res.scheme,
                          parsed_res.netloc,
                          parsed_res.path,
                          parsed_res.params,
                          parsed_res.query,
                          '')) # we don't need fragment path
        return res
    
    def get_next_links(self, source_url, text):
        links = filter(self.filter_link, self.parse_links(text))
        return [self.prepare_link(source_url, link) for link in links]
    
    def get_next_unprocessed_links(self, source_url, body):
        links_to_check = []
        for link in self.get_next_links(source_url, body):
            if not link in self.processing_links:
                links_to_check.append(link)
                self.processing_links.add(link)
        return links_to_check

    def link_to_file_path(self, link):
        parsed_link = urlparse(link)
        domain = parsed_link.netloc
        path = parsed_link.path
        params = parsed_link.query
        if path.endswith("/") or path == '':
            path = "{0}index.html".format(path)
        if path.startswith("/"):
            path = path[1:]
        file_path = os.path.join(domain, path)
        if params:
            file_path = "{0}?{1}".format(file_path, params)
        if len(os.path.basename(file_path)) > MAX_FILENAME_LENGTH:
            path_head, path_tail = os.path.split(file_path)
            path_tail = path_tail[:MAX_FILENAME_LENGTH]
            file_path = os.path.join(path_head, path_tail)
        return file_path
    
    def save_to_file(self, link, content):
        try:
            path_to_file = self.link_to_file_path(link)
            os.makedirs(os.path.dirname(path_to_file), exist_ok=True)
            with open(path_to_file, "w") as f:
                f.write(content)
            logging.info("saved to file {0}".format(path_to_file))
        except Exception as e:
            logging.warning("error saving file {0} for link {1}: {2}".format(path_to_file, link, e))
    
    def get_body_from_file(self, link):
        file_path = self.link_to_file_path(link)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            with open(file_path) as f:
                body = f.read()
                return body

    async def get_body_from_internet(self, link):
        with await self.requests_semaphore:
            try:
                response = await aiohttp.get(link)
            except Exception as e:
                logging.warning("Error requesting {0}: {1}".format(link, e))
                return None
        logging.info("{0} {1}".format(response.status, link))
        if response.status == 200:
            content_type = response.headers.get('content-type')
            if any([sct in content_type for sct in SUPPORTED_CONTENT_TYPES]):
                body = await response.text()
                await response.release()
                return body
            else:
                logging.info("content_type={0} is not supported. {1}".format(content_type, link))
        await response.release()

    async def process_link(self, link):
        already_saved = False
        body = self.get_body_from_file(link)
        if body:
            already_saved = True
            logging.info("took {0} content from file".format(link))
        else:
            body = await self.get_body_from_internet(link)
        if body:
            if not already_saved:
                self.thread_pool.apply_async(self.save_to_file, (link, body))
            links_to_check = self.get_next_unprocessed_links(link, body)
            if links_to_check:
                logging.info("found {0} new links to check for in {1}".format(len(links_to_check), link))
                del body, link, already_saved
                await asyncio.wait([self.process_link(link) for link in links_to_check])

    def process(self, link):
        self.domain = urlparse(link).netloc
        self.loop.run_until_complete(self.process_link(link))
        self.loop.close()
        self.thread_pool.close()
        self.thread_pool.join()
        logging.info("OK")
    
def set_logging():
    logging.basicConfig(format='%(levelname)s %(message)s', level=logging.INFO)

if __name__ == '__main__':
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument("url_to_crawl",
                             help="site url to crawl")
    args_parser.add_argument("--max_requests",
                             help="maximum number of simultaneous http requests (we don't want to ddos sites), default 10",
                             type=int,
                             default=10)
    args_parser.add_argument("--threads_number",
                             help="number of file writing threads (default 4)",
                             type=int,
                             default=4)
    args_parser.add_argument("--http_timeout",
                             help="timeout used in http requests in seconds (default 60s)",
                             type=int,
                             default=60)
    parsed_args = args_parser.parse_args()
    set_logging()
    crawler = Crawler(max_requests=parsed_args.max_requests,
                      threads_number=parsed_args.threads_number,
                      http_timeout=parsed_args.http_timeout)
    crawler.process(parsed_args.url_to_crawl)
