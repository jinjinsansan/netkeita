import sys
from html.parser import HTMLParser

class T(HTMLParser):
    def __init__(self):
        super().__init__()
        self.texts = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False
    def handle_data(self, data):
        if not self.skip:
            t = data.strip()
            if t and len(t) > 1:
                self.texts.append(t)

e = T()
with open("/tmp/horse_modal.html") as f:
    e.feed(f.read())
for t in e.texts:
    print(t)
