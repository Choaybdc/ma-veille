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
    ("l3", 'site:foad.cnam.fr "licence informatique"'),
    ("l3", 'site:cnam.fr "licence informatique" distance'),
    ("l3", '"licence informatique" "formation ouverte à distance"'),
    ("l3", '"licence informatique" candidature 2026 2027 université'),
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

def verify_l3_page(url):
    """Check page reachability and explicit admissions-status indicators."""
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Ma-Veille/2.1"})
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            final_url = response.geturl()
            status = getattr(response, "status", 200)
            raw = response.read(700_000)
            charset = response.headers.get_content_charset() or "utf-8"
        page_text = clean(raw.decode(charset, errors="replace")).lower()
        closed_markers = (
            "candidatures sont closes", "candidature est close", "candidatures closes",
            "inscriptions sont closes", "inscriptions closes", "campagne est terminée",
            "campagne est terminee", "admissions are closed", "applications are closed",
            "application period has ended", "deadline has passed", "formation complète",
            "formation complete", "candidatures ne sont plus possibles",
            "les candidatures ne sont plus ouvertes",
        )
        open_markers = (
            "candidatures ouvertes", "candidature ouverte", "déposer une candidature",
            "deposer une candidature", "candidater", "postuler", "e-candidat", "ecandidat",
            "inscription ouverte", "applications are open", "apply now", "candidatez",
        )
        if status in (404, 410):
            return {"isOpen": False, "verificationStatus": "page_indisponible",
                    "verifiedAt": checked_at, "verifiedUrl": final_url,
                    "verificationNote": f"La page source répond HTTP {status}."}
        if any(marker in page_text for marker in closed_markers):
            return {"isOpen": False, "verificationStatus": "candidatures_probablement_closes",
                    "verifiedAt": checked_at, "verifiedUrl": final_url,
                    "verificationNote": "Indicateur explicite de clôture trouvé ; vérifier l'année universitaire."}
        if any(marker in page_text for marker in open_markers):
            return {"isOpen": True, "verificationStatus": "page_accessible_candidature_a_confirmer",
                    "verifiedAt": checked_at, "verifiedUrl": final_url,
                    "verificationNote": "Page accessible avec un indice de candidature ; confirmer l'année et la date limite."}
        return {"isOpen": True, "verificationStatus": "page_accessible_a_verifier",
                "verifiedAt": checked_at, "verifiedUrl": final_url,
                "verificationNote": "Page accessible, mais le statut d'admission n'est pas déterminable automatiquement."}
    except urllib.error.HTTPError as exc:
        closed = exc.code in (404, 410)
        return {"isOpen": not closed,
                "verificationStatus": "page_indisponible" if closed else "erreur_http_a_verifier",
                "verifiedAt": checked_at, "verifiedUrl": url,
                "verificationNote": f"Erreur HTTP {exc.code} lors de la vérification de la source."}
    except Exception as exc:
        return {"isOpen": True, "verificationStatus": "verification_impossible",
                "verifiedAt": checked_at, "verifiedUrl": url,
                "verificationNote": f"Vérification impossible ({type(exc).__name__}) ; statut non confirmé."}

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
        "verificationStatus": item.get("verificationStatus") or ("a_verifier" if category in ("l3", "info") else "non_verifie"),
        "verifiedAt": item.get("verifiedAt") or "",
        "verifiedUrl": item.get("verifiedUrl") or "",
        "verificationNote": item.get("verificationNote") or "Vérifier la source originale.",
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
                item["conditions"] = "Annonce repérée par une recherche ciblée CDI ; vérifier le contrat exact, l'éligibilité et l'ouverture sur la source originale."
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
                "verificationStatus": "a_verifier" if category == "l3" else "non_verifie",
                "verifiedAt": "",
                "verifiedUrl": "",
                "verificationNote": "Vérifier la source originale.",
            }

    # Automatically check L3 source pages every run; uncertain statuses are never presented as confirmed open.
    l3_to_check = [item for item in list(found.values()) + list(previous.values()) if item.get("category") == "l3"]
    checked = set()
    for item in l3_to_check:
        url = item.get("url", "")
        if not url or url in checked:
            continue
        checked.add(url)
        item.update(verify_l3_page(url))
        status = item.get("verificationStatus")
        if status == "candidatures_probablement_closes":
            item["conditions"] = "Candidatures probablement closes selon la page source ; vérifier l'année universitaire et les sessions complémentaires."
        elif status == "page_indisponible":
            item["conditions"] = "Page source indisponible ; rechercher la formation sur le site officiel de l'établissement."
        elif status == "page_accessible_candidature_a_confirmer":
            item["conditions"] = "Page accessible avec un indice de candidature ; confirmer l'année universitaire, l'éligibilité et la date limite."

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
            "l3PagesChecked": len(checked),
            "l3StatusCounts": {
                status: sum(1 for item in items if item.get("category") == "l3" and item.get("verificationStatus") == status)
                for status in ("page_accessible_candidature_a_confirmer", "page_accessible_a_verifier", "candidatures_probablement_closes", "page_indisponible", "verification_impossible", "a_verifier")
            },
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
