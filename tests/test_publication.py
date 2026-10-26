"""Static publication checks. Uses only the Python standard library."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import struct
import unittest
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
URL = "https://tictactoe.salsaparapizza.com/"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.structured = []
        self.in_structured = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        self.in_structured = tag == "script" and attrs.get("type") == "application/ld+json"

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_structured = False

    def handle_data(self, data):
        if self.in_structured:
            self.structured.append(data)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.page = Page()
        self.page.feed((ROOT / "index.html").read_text())

    def test_search_and_social_metadata(self):
        meta = {attrs.get("name", attrs.get("property")): attrs.get("content")
                for tag, attrs in self.page.tags if tag == "meta"}
        for key in ["description", "robots", "og:title", "og:description", "og:image", "twitter:card", "twitter:image:alt"]:
            self.assertTrue(meta.get(key), key)
        self.assertNotIn("noindex", meta["robots"])
        self.assertEqual(meta["og:url"], URL)
        canonical = [attrs["href"] for tag, attrs in self.page.tags if tag == "link" and attrs.get("rel") == "canonical"]
        self.assertEqual(canonical, [URL])
        self.assertEqual(sum(tag == "h1" for tag, _ in self.page.tags), 1)
        schema = json.loads("".join(self.page.structured))
        self.assertEqual(schema["@type"], "VideoGame")
        self.assertEqual(schema["url"], URL)
        self.assertEqual(schema["name"], "Sim Tac Toe")
        self.assertNotIn("aggregateRating", schema)

    def test_referenced_local_assets_exist(self):
        for _, attrs in self.page.tags:
            for key in ["href", "src"]:
                value = attrs.get(key)
                if value and not urlsplit(value).scheme:
                    self.assertTrue((ROOT / urlsplit(value).path.lstrip("/")).is_file(), value)
        self.assertTrue((ROOT / "TemplateData/fonts/FreeSerif.ttf").is_file())
        self.assertTrue((ROOT / "TemplateData/fonts/Lato-Regular.ttf").is_file())

    def test_wrapper_asset_versions_match_content(self):
        expected = {"TemplateData/style.css", "TemplateData/game.js"}
        found = set()
        for _, attrs in self.page.tags:
            reference = attrs.get("href", attrs.get("src", ""))
            parsed = urlsplit(reference)
            if parsed.path in expected:
                digest = hashlib.sha256((ROOT / parsed.path).read_bytes()).hexdigest()[:12]
                self.assertEqual(parse_qs(parsed.query).get("v"), [digest])
                found.add(parsed.path)
        self.assertEqual(found, expected)

    def test_sitemap_and_crawler_access(self):
        tree = ET.parse(ROOT / "sitemap.xml")
        urls = [node.text for node in tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertEqual(urls, [URL])
        robots = (ROOT / "robots.txt").read_text()
        self.assertIn("Allow: /", robots)
        self.assertIn("Sitemap: " + URL + "sitemap.xml", robots)
        self.assertNotIn("Disallow: /", robots)

    def test_favicon_family(self):
        root = ET.parse(ROOT / "TemplateData/favicon.svg").getroot()
        self.assertEqual(root.attrib["viewBox"], "0 0 64 64")
        for name, expected in [("favicon-96.png", (96, 96)), ("apple-touch-icon.png", (180, 180))]:
            png = (ROOT / "TemplateData" / name).read_bytes()
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), expected)
        ico = (ROOT / "favicon.ico").read_bytes()
        self.assertEqual(struct.unpack("<HHH", ico[:6]), (0, 1, 4))
        self.assertEqual(ico, (ROOT / "TemplateData/favicon.ico").read_bytes())

    def test_loader_order_and_accessibility(self):
        scripts = [attrs for tag, attrs in self.page.tags if tag == "script" and "src" in attrs]
        self.assertEqual([urlsplit(attrs["src"]).path for attrs in scripts], ["Build/simtactoc.loader.js", "TemplateData/game.js"])
        self.assertTrue(all("defer" in attrs for attrs in scripts))
        canvas = next(attrs for tag, attrs in self.page.tags if tag == "canvas")
        self.assertEqual(canvas["tabindex"], "0")
        self.assertTrue(canvas["aria-label"])
        button = next(attrs for tag, attrs in self.page.tags if tag == "button")
        self.assertEqual(button["type"], "button")
        self.assertIn("disabled", button)


if __name__ == "__main__":
    unittest.main()
