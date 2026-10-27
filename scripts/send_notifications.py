#!/usr/bin/env python3
"""Email only newly discovered, deduplicated Ma Veille opportunities."""
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

DATA_FILE = Path("veille.json")
STATE_FILE = Path("notifications_state.json")
CATEGORIES = {"cdi", "l3"}


def load_json(path, default):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def status_label(item):
    status = (item.get("verificationStatus") or "").lower()
    if status == "candidatures_confirmees_ouvertes":
        return "OUVERT — confirmé"
    if status == "page_accessible_candidature_a_confirmer":
        return "Page accessible — candidature à confirmer"
    if status == "source_officielle_accessible_statut_a_confirmer":
        return "Site officiel accessible — admissions à confirmer"
    if status == "candidatures_probablement_closes":
        return "Probablement clos — à revérifier"
    if status == "page_indisponible":
        return "Page indisponible"
    if item.get("category") == "cdi":
        return "Annonce repérée — contrat CDI et disponibilité à vérifier"
    return "Statut à confirmer"


def priority(item):
    status = (item.get("verificationStatus") or "").lower()
    if status == "candidatures_confirmees_ouvertes":
        return 0
    if status == "page_accessible_candidature_a_confirmer":
        return 1
    if status == "source_officielle_accessible_statut_a_confirmer":
        return 2
    if status == "candidatures_probablement_closes":
        return 4
    return 3


def make_email(items, data):
    items = sorted(items, key=lambda item: (priority(item), item.get("publishedAt", "")), reverse=False)
    lines = [
        f"Ma Veille a détecté {len(items)} nouvelle(s) opportunité(s).",
        f"Données mises à jour le : {data.get('updatedAt', 'date inconnue')}",
        "",
        "Les opportunités confirmées ouvertes apparaissent en premier. Une annonce détectée ne garantit pas que le poste ou les candidatures sont encore disponibles.",
        "",
    ]
    for i, item in enumerate(items, 1):
        category = "CDI – Enseignement de l’anglais" if item.get("category") == "cdi" else "L3 Informatique"
        lines.extend([
            f"{i}. [{category}] {item.get('title', 'Sans titre')}",
            f"   Statut : {status_label(item)}",
            f"   Organisme : {item.get('organization', 'Non précisé')}",
            f"   Localisation : {item.get('location', 'Non précisée')}",
            f"   Publication : {item.get('publishedAt', 'Non précisée')}",
        ])
        if item.get("deadline"):
            lines.append(f"   Date limite : {item['deadline']}")
        url = item.get("publisherUrl") or item.get("url")
        if url:
            lines.append(f"   Lien : {url}")
        if item.get("verificationNote"):
            lines.append(f"   Vérification : {item['verificationNote']}")
        lines.append("")
    lines.append("Ma Veille : https://choaybdc.github.io/ma-veille/")
    return "\n".join(lines)


def main():
    data = load_json(DATA_FILE, {"items": []})
    items = [
        item for item in data.get("items", [])
        if item.get("category") in CATEGORIES and item.get("id")
    ]
    # IDs make notifications idempotent even when RSS feeds return duplicates.
    unique = {}
    for item in items:
        unique[item["id"]] = item
    items = list(unique.values())

    state = load_json(STATE_FILE, None)
    if state is None or not state.get("initialized"):
        # First run establishes a baseline; it deliberately does not email the
        # existing backlog. Only offers discovered on later runs trigger alerts.
        STATE_FILE.write_text(json.dumps({
            "initialized": True,
            "notified_ids": sorted(item["id"] for item in items),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Initial notification baseline saved ({len(items)} existing items); no backlog email sent.")
        return

    notified = set(state.get("notified_ids", []))
    pending = [item for item in items if item["id"] not in notified]
    if not pending:
        print("No new deduplicated opportunities to email.")
        return

    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "").strip() or "465")
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    recipient = os.getenv("ALERT_EMAIL", "").strip()

    if not all([host, username, password, recipient]):
        print(f"{len(pending)} new opportunity/ies found, but email is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and ALERT_EMAIL in GitHub Actions secrets/variables.")
        # Leave them pending so they can be sent after configuration.
        return

    message = EmailMessage()
    message["Subject"] = f"[Ma Veille] {len(pending)} nouvelle(s) opportunité(s)"
    message["From"] = username
    message["To"] = recipient
    message.set_content(make_email(pending, data))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
        server.login(username, password)
        server.send_message(message)

    notified.update(item["id"] for item in pending)
    state["initialized"] = True
    state["notified_ids"] = sorted(notified)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Email sent for {len(pending)} new deduplicated opportunities to the configured recipient.")


if __name__ == "__main__":
    main()
