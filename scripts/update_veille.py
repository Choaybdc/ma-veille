import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

OUT = "veille.json"
MAX_PER_FEED = 15
MAX_ITEMS = 80
MAX_AGE_DAYS = 60

# Google News RSS is used as a discovery feed. Always verify the original
# announcement before applying; this script does not guarantee vacancies remain open.
FEEDS = [
    ("cdi", '"enseignant anglais" CDI France'),
    ("cdi", '"professeur anglais" CDI recrutement France'),
    ("cdi", '"English teacher" CDI France emploi'),
    ("cdi", 'recrutement enseignant anglais contrat indéterminée France'),
    ("cdi", 'site:francetravail.fr enseignant anglais CDI'),
    ("cdi", 'site:enseignementsup-recherche.gouv.fr lecteur anglais recrutement'),
    ("l3", '"licence 3 informatique" candidature université'),
    ("l3", '"L3 informatique" admission université France'),
    ("l3", '"licence informatique" "à distance" L3'),
    ("l3", '"licence 3 informatique" enseignement à distance'),
    ("l3", '"L3 informatique" eCandidat'),
]

def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def fetch_feed(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query, "hl": "fr", "gl": "FR", "ceid": "FR:fr"
    })
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Ma-Veille/2.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return ET.fromstring(response.read())

def parse_date(value):
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()

def relevant(category, title, description, query):
    text = (title + " " + description).lower()
    if category == "cdi":
        language = any(word in text for word in ("anglais", "english"))
        role = any(word in text for word in (
            "enseignant", "enseignante", "professeur", "professeure",
            "teacher", "lecteur", "lectrice", "formateur", "formatrice",
            "enseignement", "cours d'anglais"
        ))
        contract = any(word in text for word in (
            "cdi", "contrat à durée indéterminée", "contrat a duree indeterminee",
            "indéterminée", "indeterminee"
        ))
        # The query is targeted, but still require role + language + CDI evidence.
        # Search query is CDI-targeted; use it only as a fallback when the result
        # clearly concerns an English-teaching role, never to infer the role itself.
        return language and role and (contract or "cdi" in query.lower())
    has_l3 = any(word in text for word in (
        "l3 informatique", "licence 3 informatique", "licence informatique",
        "informatique à distance", "informatique a distance"
    ))
    admissions = any(word in text for word in (
        "admission", "candidature", "e-candidat", "ecandidat", "inscription",
        "formation", "université", "universite", "distance", "licence"
    ))
    return has_l3 and admissions

def normalize_item(item):
    # Migrate older JSON records to the schema consumed by the current dashboard.
    url = clean(item.get("url"))
    title = clean(item.get("title"))
    if not url or not title:
        return None
    category = item.get("category") or item.get("cat") or "cdi"
    published = item.get("publishedAt") or item.get("date") or ""
    return {
        "id": item.get("id") or url,
        "category": "l3" if category in ("l3", "info") else category,
        "title": title,
        "organization": item.get("organization") or item.get("org") or item.get("source") or "Source à vérifier",
        "url": url,
        "conditions": item.get("conditions") or item.get("req") or "Vérifier les conditions sur la source originale.",
        "location": item.get("location") or item.get("place") or "France",
        "publishedAt": published,
        "deadline": item.get("deadline") or "",
        "isNew": bool(item.get("isNew", item.get("new", False))),
        "isOpen": bool(item.get("isOpen", item.get("open", True))),
        "source": item.get("source") or "Google Actualités",
    }

def main():
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=MAX_AGE_DAYS)).date().isoformat()
    try:
        with open(OUT, "r", encoding="utf-8") as handle:
            previous_data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        previous_data = {}

    previous = {}
    for raw in previous_data.get("items", []):
        item = normalize_item(raw)
        if item and (not item["publishedAt"] or item["publishedAt"] >= cutoff):
            category_query = "cdi" if item["category"] == "cdi" else ""
            if not relevant(item["category"], item["title"], item["conditions"], category_query):
                continue
            item["isNew"] = False
            if item["category"] == "cdi":
                item["conditions"] = "Annonce repérée par une recherche ciblée CDI ; vérifier la nature exacte du contrat sur la source originale."
            previous[item["url"]] = item

    found = {}
    successful_feeds = 0
    for category, query in FEEDS:
        try:
            root = fetch_feed(query)
            successful_feeds += 1
        except Exception as exc:
            print(f"Flux indisponible ({query}): {exc}")
            continue

        for node in root.findall("./channel/item")[:MAX_PER_FEED]:
            title = clean(node.findtext("title"))
            link = clean(node.findtext("link"))
            description = clean(node.findtext("description"))
            published = parse_date(node.findtext("pubDate") or "")
            if not title or not link or not link.startswith(("https://", "http://")):
                continue
            if published < cutoff or not relevant(category, title, description, query):
                continue

            source_node = node.find("source")
            source = clean(source_node.text if source_node is not None else "")
            old = previous.get(link)
            found[link] = {
                "id": link,
                "category": category,
                "title": title,
                "organization": source or "Source via Google Actualités",
                "url": link,
                "conditions": "Vérifier le contrat, l'éligibilité et la date limite sur la source originale.",
                "location": "France",
                "publishedAt": published,
                "deadline": "",
                "isNew": old is None,
                "isOpen": True,
                "source": "Google Actualités",
            }

    # Keep old items when a feed is temporarily empty or unavailable.
    # Do not replace the saved collection with an empty array after a failed search.
    combined = dict(previous)
    combined.update(found)
    items = list(combined.values())
    items.sort(key=lambda item: (item.get("publishedAt") or "", item.get("title") or ""), reverse=True)
    items = items[:MAX_ITEMS]

    data = {
        "updatedAt": now.date().isoformat(),
        "items": items,
        "searchStatus": {
            "feedsConfigured": len(FEEDS),
            "feedsSucceeded": successful_feeds,
            "resultsFoundThisRun": len(found),
        },
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Flux interrogés avec succès : {successful_feeds}/{len(FEEDS)}")
    print(f"Nouvelles opportunités détectées : {sum(1 for item in found.values() if item['isNew'])}")
    print(f"Opportunités conservées : {len(items)}")
    if successful_feeds == 0:
        raise RuntimeError("Tous les flux sont indisponibles ; vérifier le réseau avant de considérer la veille à jour.")

if __name__ == "__main__":
    main()
