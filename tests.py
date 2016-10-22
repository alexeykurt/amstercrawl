import unittest
from unittest.mock import Mock

from crawler import Crawler


class TestParseLinks(unittest.TestCase):
    cls_mock = Mock(spec=Crawler)

    def test_parse_url_basic(self):
        html = """
            <a href="http://hscake.ru/jieguo_buyu/" class="entry-featured-image-url">
        """
        self.assertEqual(Crawler.parse_links(self.cls_mock, html), ["http://hscake.ru/jieguo_buyu/"])

    def test_parse_url_1(self):
        html = """
            <a href='http://hscake.ru/jieguo_buyu/' class="entry-featured-image-url">
        """
        self.assertEqual(Crawler.parse_links(self.cls_mock, html), ["http://hscake.ru/jieguo_buyu/"])

    def test_parse_url_different_braces(self):
        html = """
            <a href="http://hscake.ru/jieguo_buyu/' class="entry-featured-image-url">
        """
        self.assertEqual(Crawler.parse_links(self.cls_mock, html), ["http://hscake.ru/jieguo_buyu/"])

    def test_parse_url_forgotten_brace(self):
        html = """
            <a href="http://hscake.ru/jieguo_buyu/ class="entry-featured-image-url">
        """
        self.assertEqual(Crawler.parse_links(self.cls_mock, html), ["http://hscake.ru/jieguo_buyu/"])

    def test_parse_url_bad_html(self):
        html = """
            <a href="http://hscake.ru/jieguo_buyu/>
        """
        self.assertEqual(Crawler.parse_links(self.cls_mock, html), ["http://hscake.ru/jieguo_buyu/"])

    def test_parse_url_css(self):
        html = """
    <link rel='stylesheet' id='dashicons-css'  href='http://hscake.ru/wp-includes/css/dashicons.min.css?ver=4.6.1' type='text/css' media='all' />
        """
        self.assertEqual(Crawler.parse_links(self.cls_mock, html), ["http://hscake.ru/wp-includes/css/dashicons.min.css?ver=4.6.1"])

    def test_parse_url_javascript(self):
        html = """
        <script type='text/javascript' src='http://hscake.ru/wp-includes/js/wp-embed.min.js?ver=4.6.1'></script>
        """
        self.assertEqual(Crawler.parse_links(self.cls_mock, html), ["http://hscake.ru/wp-includes/js/wp-embed.min.js?ver=4.6.1"])


class TestFilterLinks(unittest.TestCase):
    cls_mock = Mock(spec=Crawler)
    cls_mock.domain = "expert.ru"
    
    def test_true_normal_link(self):
        url = "http://expert.ru/expert/2016/42/algoritm-kompromissa/"
        self.assertTrue(Crawler.filter_link(self.cls_mock, url))

    def test_false_js_link(self):
        url = "#"
        self.assertFalse(Crawler.filter_link(self.cls_mock, url))
    
    def test_false_media(self):
        url = "http://expert.ru/data/public/517501/517540/35-01c.jpg"
        self.assertFalse(Crawler.filter_link(self.cls_mock, url))

    def test_false_data_instead_of_url(self):
        url = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
        self.assertFalse(Crawler.filter_link(self.cls_mock, url))

    def test_false_mailto(self):
        url = "mailto:docs@python.org"
        self.assertFalse(Crawler.filter_link(self.cls_mock, url))
    
    def test_false_login_and_redirect(self):
        url = "http://expert.ru/signin/?next=/russian_reporter/2008/25/izgotovlenie_pasporta/"
        self.assertFalse(Crawler.filter_link(self.cls_mock, url))

class TestPrepareLink(unittest.TestCase):
    cls_mock = Mock(spec=Crawler)
    cls_mock.domain = "docs.python.org"
    
    def test_normal_link(self):
        source_url = "https://docs.python.org/3/library/urllib.html"
        url = "https://docs.python.org/3/library/urllib.parse.html"
        result_url = url
        self.assertEqual(Crawler.prepare_link(self.cls_mock, source_url, url), result_url)

    def test_relative_link(self):
        source_url = "https://docs.python.org/3/library/"
        url = "urllib.parse.html"
        result_url = "https://docs.python.org/3/library/urllib.parse.html"
        self.assertEqual(Crawler.prepare_link(self.cls_mock, source_url, url), result_url)

    def test_link_with_fragment(self):
        source_url = "https://docs.python.org/3/library/urllib.html"
        url = "https://docs.python.org/3/library/urllib.parse.html#urlparse-result-object"
        result_url = "https://docs.python.org/3/library/urllib.parse.html"
        self.assertEqual(Crawler.prepare_link(self.cls_mock, source_url, url), result_url)

class TestLinkToFilePath(unittest.TestCase):
    cls_mock = Mock(spec=Crawler)

    def test_root(self):
        url = "http://hscake.ru"
        self.assertEqual(Crawler.link_to_file_path(self.cls_mock, url),
                         "hscake.ru/index.html")

    def test_root_with_get_params(self):
        url = "http://hscake.ru/?p=209"
        self.assertEqual(Crawler.link_to_file_path(self.cls_mock, url),
                         "hscake.ru/index.html?p=209")

    def test_many_dirs(self):
        url = "http://hscake.ru/category/grammar/feed/"
        self.assertEqual(Crawler.link_to_file_path(self.cls_mock, url),
                         "hscake.ru/category/grammar/feed/index.html")

    def test_russian_urls(self):
        url = "http://hscake.ru/5-%d0%bf%d1%80%d0%b8%d1%87%d0%b8%d0%bd-%d1%81%d0%b4%d0%b0%d1%82%d1%8c-hsk/"
        self.assertEqual(Crawler.link_to_file_path(self.cls_mock, url),
                         "hscake.ru/5-%d0%bf%d1%80%d0%b8%d1%87%d0%b8%d0%bd-%d1%81%d0%b4%d0%b0%d1%82%d1%8c-hsk/index.html")

    def test_max_filename_length(self):
        url = "http://hscake.ru/wp-json/oembed/1.0/embed?url=http%3A%2F%2Fhscake.ru%2F%25d1%2587%25d1%2582%25d0%25be-%25d1%2582%25d0%25b0%25d0%25ba%25d0%25be%25d0%25b5-hscake-%25d0%25b8-%25d0%25ba%25d0%25b0%25d0%25ba-%25d0%25b5%25d0%25b3%25d0%25be-%25d0%25bf%25d1%2580%25d0%25b8%25d0%25b3%25d0%25be%25d1%2582%25d0%25be%25d0%25b2%25d0%25b8%25d1%2582%25d1%258c%2F"
        result_url = "hscake.ru/wp-json/oembed/1.0/embed?url=http%3A%2F%2Fhscake.ru%2F%25d1%2587%25d1%2582%25d0%25be-%25d1%2582%25d0%25b0%25d0%25ba%25d0%25be%25d0%25b5-hscake-%25d0%25b8-%25d0%25ba%25d0%25b0%25d0%25ba-%25d0%25b5%25d0%25b3%25d0%25be-%25d0%25bf%25d1%2580%25d0%25b8%25d0%25b3%25d0%25be%25d1%25"
        self.assertEqual(Crawler.link_to_file_path(self.cls_mock, url), result_url)


if __name__ == '__main__':
    unittest.main()
