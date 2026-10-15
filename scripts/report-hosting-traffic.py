#!/usr/bin/env python3
"""Aggregate first-party Firebase Hosting HTML requests; never export identifiers."""
import collections
import csv
import datetime as dt
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROJECT = "zazomtek"
ZONE = ZoneInfo("Europe/Rome")
SITE_HOSTS = {"zazoomtek.it", "www.zazoomtek.it"}
ENDPOINT = "https://logging.googleapis.com/v2/entries:list"
RAW_LIMIT = 100000
DAY_COUNT = 30
BOT = re.compile(
    r"bot|crawler|spider|lighthouse|headless|pagespeed|uptime|pingdom|"
    r"monitoring|facebookexternalhit|twitterbot|slackbot|whatsapp|"
    r"python-requests|curl/|wget/|googleother|gptbot|bingpreview", re.I,
)

def summary(message):
    print(message, flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as out:
            out.write(message + "\n")

def build_filter(start_utc):
    # Only HTML responses, not stylesheets/images/scripts/other static assets.
    doc_urls = (
        r"^https://(www[.])?zazoomtek[.]it/"
        r"(([?][^#]*)?|[^?#]+[.]html([?][^#]*)?)$"
    )
    return (
        'resource.type="firebase_domain" AND '
        'logName="projects/zazomtek/logs/webrequests" AND '
        'httpRequest.requestMethod="GET" AND '
        '(httpRequest.status=200 OR httpRequest.status=304) AND '
        'httpRequest.requestUrl=~"' + doc_urls + '" AND '
        'timestamp>="' + start_utc.isoformat().replace("+00:00", "Z") + '"'
    )

def allowed_document(url):
    try:
        u = urlsplit(url)
    except ValueError:
        return False
    return (
        u.scheme == "https" and u.hostname in SITE_HOSTS
        and (u.path == "/" or u.path.lower().endswith(".html"))
    )

def fetch_counts():
    today = dt.datetime.now(ZONE).date()
    start_day = today - dt.timedelta(days=DAY_COUNT - 1)
    start_local = dt.datetime.combine(start_day, dt.time.min, ZONE)
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    params = {
        # API partial response: IP and referrer are not returned to this script.
        "fields": "nextPageToken,entries(timestamp,httpRequest(requestUrl,requestMethod,status,userAgent))"
    }
    payload = {
        "resourceNames": ["projects/" + PROJECT],
        "filter": build_filter(start_local.astimezone(dt.timezone.utc)),
        "orderBy": "timestamp desc",
        "pageSize": 1000,
    }
    counts = collections.Counter()
    total_scanned = 0
    page_token = ""
    first = None
    while True:
        if page_token:
            payload["pageToken"] = page_token
        response = session.post(ENDPOINT, json=payload, params=params, timeout=40)
        if response.status_code != 200:
            return response.status_code, counts, None, start_day, today
        result = response.json()
        entries = result.get("entries", [])
        total_scanned += len(entries)
        for entry in entries:
            request = entry.get("httpRequest") or {}
            if (
                request.get("requestMethod") != "GET"
                or request.get("status") not in (200, 304)
                or not allowed_document(request.get("requestUrl", ""))
                or BOT.search(request.get("userAgent", "") or "")
            ):
                continue
            try:
                when = dt.datetime.fromisoformat(
                    str(entry.get("timestamp", "")).replace("Z", "+00:00")
                )
                local_day = when.astimezone(ZONE).date()
            except ValueError:
                continue
            if start_day <= local_day <= today:
                counts[local_day] += 1
                if first is None or local_day < first:
                    first = local_day
        page_token = result.get("nextPageToken", "")
        if not page_token:
            break
        if total_scanned >= RAW_LIMIT:
            return "incomplete", counts, first, start_day, today
    return 200, counts, first, start_day, today

def main():
    summary("## ZazoomTek — richieste HTML degli ultimi 30 giorni\n")
    try:
        status, counts, first, start_day, today = fetch_counts()
    except Exception as exc:
        summary("**Cloud Logging non disponibile:** " + type(exc).__name__)
        return
    if status == 403:
        summary("**In attesa di autorizzazione:** serve il ruolo Cloud Logging Viewer "
                "per l'account tecnico GitHub nel progetto Firebase zazomtek.")
        summary("Collegare anche Firebase Hosting a Cloud Logging dalla console "
                "Firebase, se non e gia stato collegato.")
        return
    if status == 200 and first is None:
        summary("**Nessun dato Hosting rilevato:** controllare il collegamento "
                "Firebase Hosting > Cloud Logging e attendere circa 30 minuti.")
        return
    if status != 200:
        summary("**Rapporto indisponibile (stato " + str(status) +
                "):** nessun totale parziale viene presentato come dato reale.")
        return

    days = []
    day = first
    while day <= today:
        days.append((day.isoformat(), counts.get(day, 0)))
        day += dt.timedelta(days=1)
    with Path("zazoomtek-pagine-hosting-30gg.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["data_italiana", "richieste_pagine_html_non_bot"])
        writer.writerows(days)
    summary("**Periodo osservato:** " + first.isoformat() + " – " + today.isoformat())
    summary("**Richieste HTML rilevate (non utenti unici): " + str(sum(counts.values())) + "**")
    summary("")
    summary("| Giorno (Italia) | Richieste HTML |")
    summary("|---|---:|")
    for date, views in reversed(days[-14:]):
        summary("| " + date + " | " + str(views) + " |")
    summary("")
    summary(
        "**Interpretazione:** risposte HTTP a richieste di pagine HTML senza "
        "cookie Analytics, escluse le richieste di bot riconoscibili. Questi "
        "**non sono utenti unici o sessioni GA4**. I log possono essere "
        "ritardati, incompleti o contenere bot non riconosciuti; "
        "il CSV contiene esclusivamente totali giornalieri."
    )

if __name__ == "__main__":
    main()
