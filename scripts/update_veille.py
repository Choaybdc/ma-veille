import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

OUT = "veille.json"
MAX_PER_FEED = 12

FEEDS = [
    ("cdi", '"enseignant d\'anglais" CDI France'),
    ("cdi", 'professeur anglais CDI France recrutement'),
    ("cdi", 'enseignant anglais "CDI" université France'),
    ("info", '"L3 informatique" admission France'),
    ("info", '"Licence 3 informatique" France admission'),
    ("info", '"L3 informatique" distance France'),
]


def clean(text):
    return re.sub(r"\\s+", " ", (text or "")).strip()


def fetch_feed(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, "hl": "fr", "gl": "FR", "ceid": "FR:fr"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Ma-Veille/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return ET.fromstring(r.read())


def parse_date(value):
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def is_relevant(cat, title, desc):
    text = (title + " " + desc).lower()
    if cat == "cdi":
        must = any(x in text for x in ["anglais", "english"])
        contract = any(x in text for x in ["cdi", "indéterminée", "indeterminee"])
        return must and contract
    return any(x in text for x in ["l3 informatique", "licence 3 informatique", "licence informatique"])


def main():
    items = []
    seen = set()
    for cat, query in FEEDS:
        try:
            root = fetch_feed(query)
        except Exception as exc:
            print(f"Flux indisponible: {query} — {exc}")
            continue
        for node in root.findall("./channel/item")[:MAX_PER_FEED]:
            title = clean(node.findtext("title"))
            link = clean(node.findtext("link"))
            desc = clean(node.findtext("description"))
            pub = clean(node.findtext("pubDate"))
            if not title or not link or not is_relevant(cat, title, desc):
                continue
            key = link or title.lower()
            if key in seen:
                continue
            seen.add(key)
            source = ""
            source_node = node.find("source")
            if source_node is not None and source_node.text:
                source = clean(source_node.text)
            items.append({
                "cat": cat,
                "new": True,
                "open": True,
                "title": title,
                "org": source or "Source via Google Actualités",
                "place": "France",
                "date": parse_date(pub),
                "deadline": "À vérifier sur la source",
                "req": "Vérifier les conditions sur l’annonce / la formation",
                "url": link,
            })

    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    # Keep the feed compact and avoid an ever-growing JSON file.
    items = items[:40]
    data = {"updatedAt": datetime.now(timezone.utc).date().isoformat(), "items": items}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(items)} opportunité(s) enregistrée(s) dans {OUT}")


if __name__ == "__main__":
    main()
