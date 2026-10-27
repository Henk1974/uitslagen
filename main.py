import argparse
import html
import io
import json
import re
import secrets
import threading
import time
import tkinter as tk
import webbrowser
from collections import OrderedDict
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tkinter import filedialog, messagebox, ttk
from urllib.parse import parse_qs, quote, urlparse, urlsplit

import pandas as pd
import requests
from bs4 import BeautifulSoup
from openpyxl.styles import Alignment, Font, PatternFill

VOORBEELD_URL = "https://uitslagen.nl/2026101900861"
VASTE_POORT = 8765
INACTIEF_TIMEOUT = 180  # seconden zonder contact met een browsertabblad
MAX_OPGESLAGEN = 10
KLEUR_KOP = "146C43"


def haal_identifier_op(value: str) -> str:
    """Accepteer zowel een identifier als een volledige uitslagen.nl-URL."""
    value = value.strip()
    if not value:
        raise ValueError("Vul een uitslagcode of URL in.")
    if "://" in value:
        parsed = urlparse(value)
        host = (parsed.netloc or "").lower()
        if not (host == "uitslagen.nl" or host.endswith(".uitslagen.nl")):
            raise ValueError("Gebruik een URL van uitslagen.nl.")
        identifier = parsed.path.strip("/").split("/")[0]
    else:
        identifier = value.strip("/").split("/")[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise ValueError("De uitslagcode bevat ongeldige tekens.")
    return identifier


def bron_url(identifier: str) -> str:
    return f"https://uitslagen.nl/{identifier}"


def haal_pagina_op(identifier: str) -> BeautifulSoup:
    response = requests.get(
        bron_url(identifier),
        headers={"User-Agent": "Mozilla/5.0 (compatible; UitslagenScraper/1.0)"},
        timeout=30,
    )
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def netwerk_foutmelding(exc: requests.RequestException) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        if exc.response.status_code == 404:
            return "Deze uitslag bestaat niet op Uitslagen.nl. Controleer de code of URL."
        return (
            "Uitslagen.nl gaf een foutmelding "
            f"({exc.response.status_code}). Probeer het later opnieuw."
        )
    if isinstance(exc, requests.Timeout):
        return "Uitslagen.nl reageert niet op tijd. Probeer het later opnieuw."
    if isinstance(exc, requests.ConnectionError):
        return "Geen verbinding met Uitslagen.nl. Controleer je internetverbinding."
    return f"De website kon niet worden opgehaald: {exc}"


def haal_evenementgegevens_op(soup: BeautifulSoup) -> dict[str, str]:
    gegevens = {}
    titel = soup.select_one(".uitslagencontainer h1")
    if titel:
        naam = re.sub(
            r"^Uitslagenlijst\s+",
            "",
            titel.get_text(" ", strip=True),
            flags=re.IGNORECASE,
        ).strip()
        if naam:
            gegevens["run"] = naam

    info = soup.select(".uitslagencontainer .event-info > span")
    if info:
        plaats = info[0].get_text(" ", strip=True).replace("•", "")
        plaats = re.sub(r"\s+[A-Z]{3}$", "", plaats).strip()
        if plaats:
            gegevens["plaats"] = plaats
    if len(info) > 1:
        datum_tekst = info[1].get_text(" ", strip=True)
        match = re.search(
            r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})",
            datum_tekst,
            flags=re.IGNORECASE,
        )
        if match:
            maanden = {
                "januari": 1,
                "februari": 2,
                "maart": 3,
                "april": 4,
                "mei": 5,
                "juni": 6,
                "juli": 7,
                "augustus": 8,
                "september": 9,
                "oktober": 10,
                "november": 11,
                "december": 12,
            }
            maand = maanden.get(match.group(2).casefold())
            if maand:
                gegevens["datum"] = date(
                    int(match.group(3)),
                    maand,
                    int(match.group(1)),
                ).isoformat()
    return gegevens


def veilige_bestandsnaam(waarde: str) -> str:
    waarde = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", waarde)
    waarde = re.sub(r"\s+", "_", waarde).strip(" ._")
    return waarde


def maak_bestandsnaam(
    identifier: str,
    gegevens: dict[str, str],
    extensie: str,
    categorie: str = "",
) -> str:
    onderdelen = [
        veilige_bestandsnaam(gegevens[sleutel])
        for sleutel in ("run", "plaats", "datum")
        if gegevens.get(sleutel)
    ]
    if categorie:
        onderdelen.append(veilige_bestandsnaam(categorie))
    onderdelen.append(veilige_bestandsnaam(identifier))
    return f"uitslagen_{'_'.join(onderdelen)}{extensie}"


def splits_categorie(categorie: str) -> tuple[str | None, str | None]:
    if "," not in categorie:
        return categorie.strip() or None, None
    klasse, afstand = (deel.strip() for deel in categorie.split(",", 1))
    return klasse, afstand


def lees_uitslag(identifier: str) -> pd.DataFrame:
    return parseer_uitslag(identifier, haal_pagina_op(identifier))


def parseer_uitslag(identifier: str, soup: BeautifulSoup) -> pd.DataFrame:
    resultaten = []

    for tabel in soup.select(".table.uitslagen"):
        caption = tabel.select_one(".caption")
        if caption is None:
            continue
        categorie = caption.get_text(" ", strip=True)
        klasse, afstand = splits_categorie(categorie)

        for rij in tabel.find_all("div", class_="tr", recursive=False):
            cellen = rij.find_all("div", class_="td", recursive=False)
            plaats_element = rij.select_one(".td.bold")
            if not cellen or plaats_element is None:
                continue
            plaats_tekst = plaats_element.get_text(" ", strip=True)
            if not plaats_tekst.isdigit():
                continue

            naam_element = rij.select_one(".td .naam")
            woonplaats_element = rij.select_one(".td .wpl")
            tijden = [
                cel.get_text(" ", strip=True)
                for cel in rij.select(".td.tijd")
            ]
            bruto = tijden[0] if tijden else None
            netto = tijden[1] if len(tijden) > 1 else None
            resultaten.append({
                "UitslagID": identifier,
                "Categorie": categorie,
                "Klasse": klasse,
                "Afstand": afstand,
                "Plaats": int(plaats_tekst),
                "Naam": (
                    naam_element.get_text(" ", strip=True)
                    if naam_element else ""
                ),
                "Woonplaats/Vereniging": (
                    woonplaats_element.get_text(" ", strip=True)
                    if woonplaats_element else ""
                ),
                "Bruto": bruto,
                "Netto": netto,
                "Tijd": netto or bruto,
            })

    if not soup.select(".table.uitslagen"):
        regels = [tekst.strip() for tekst in soup.stripped_strings if tekst.strip()]
        categorie = None
        i = 0
        while i < len(regels):
            tekst = regels[i]
            if tekst.upper().startswith(("HEREN", "DAMES")):
                categorie = tekst
                i += 1
                continue
            if tekst.casefold() == "tijd":
                i += 1
                continue
            if categorie and tekst.isdigit():
                try:
                    plaats = int(tekst)
                    naam = regels[i + 1]
                    woonplaats = regels[i + 2]
                    tijd = regels[i + 3]
                    if ":" in tijd:
                        klasse, afstand = splits_categorie(categorie)
                        resultaten.append({
                            "UitslagID": identifier,
                            "Categorie": categorie,
                            "Klasse": klasse,
                            "Afstand": afstand,
                            "Plaats": plaats,
                            "Naam": naam,
                            "Woonplaats/Vereniging": woonplaats,
                            "Bruto": None,
                            "Netto": None,
                            "Tijd": tijd,
                        })
                    i += 4
                    continue
                except (IndexError, ValueError):
                    pass
            i += 1

    df = pd.DataFrame(resultaten)
    if df.empty:
        raise ValueError(
            "Er zijn geen uitslagen herkend. Controleer de code/URL. "
            "De pagina-indeling kan gewijzigd zijn of deze uitslag kan een ander format gebruiken."
        )
    return df


def schrijf_excel(
    df: pd.DataFrame,
    gegevens: dict[str, str],
    identifier: str,
    doel,
) -> None:
    """Schrijf een opgemaakt Excel-bestand naar een pad of bestandsobject."""
    kop_font = Font(bold=True, color="FFFFFF")
    kop_vulling = PatternFill("solid", fgColor=KLEUR_KOP)

    info = pd.DataFrame(
        [
            ("Evenement", gegevens.get("run", "")),
            ("Plaats", gegevens.get("plaats", "")),
            ("Datum", gegevens.get("datum", "")),
            ("Uitslagcode", identifier),
            ("Bron", bron_url(identifier)),
            ("Aantal uitslagen", len(df)),
            ("Geëxporteerd op", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ],
        columns=["Gegeven", "Waarde"],
    )

    with pd.ExcelWriter(doel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Uitslagen")
        info.to_excel(writer, index=False, sheet_name="Evenement")

        for blad in writer.sheets.values():
            for cel in blad[1]:
                cel.font = kop_font
                cel.fill = kop_vulling
                cel.alignment = Alignment(vertical="center")
            blad.freeze_panes = "A2"
            for kolom in blad.columns:
                breedte = max(
                    len(str(cel.value)) if cel.value is not None else 0
                    for cel in kolom[:1000]
                )
                blad.column_dimensions[kolom[0].column_letter].width = min(
                    max(breedte + 2, 8), 60
                )

        uitslagen = writer.sheets["Uitslagen"]
        uitslagen.auto_filter.ref = uitslagen.dimensions


def maak_export(
    df: pd.DataFrame,
    gegevens: dict[str, str],
    identifier: str,
    export_format: str,
) -> bytes:
    if export_format == "csv":
        return df.to_csv(index=False).encode("utf-8-sig")
    output = io.BytesIO()
    schrijf_excel(df, gegevens, identifier, output)
    return output.getvalue()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Uitslagen.nl naar Excel / CSV")
        self.geometry("610x320")
        self.minsize(560, 300)
        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="Uitslagen.nl exporteren",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text="Vul de uitslagcode in of plak de volledige URL.",
        ).pack(anchor="w", pady=(5, 12))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(frame, textvariable=self.url_var)
        self.url_entry.pack(fill="x")
        self.url_entry.bind("<Return>", lambda _event: self.start())
        self.url_entry.focus_set()
        ttk.Label(
            frame,
            text=f"Bijvoorbeeld: {VOORBEELD_URL}",
            foreground="#5b6570",
        ).pack(anchor="w", pady=(4, 0))
        options = ttk.Frame(frame)
        options.pack(fill="x", pady=14)
        ttk.Label(options, text="Bestandsformaat:").pack(side="left")
        self.format_var = tk.StringVar(value="Excel (.xlsx)")
        self.format_box = ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=["Excel (.xlsx)", "CSV (.csv)"],
            state="readonly",
            width=16,
        )
        self.format_box.pack(side="left", padx=(8, 0))
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        self.run_button = ttk.Button(
            buttons, text="Uitslagen ophalen en opslaan", command=self.start
        )
        self.run_button.pack(side="left")
        ttk.Button(
            buttons,
            text="Stoppen",
            command=self.destroy,
        ).pack(side="right")
        self.status_var = tk.StringVar(value="Klaar.")
        ttk.Label(
            frame,
            textvariable=self.status_var,
            wraplength=560,
        ).pack(anchor="w", pady=(14, 0))

    def start(self):
        if str(self.run_button["state"]) == "disabled":
            return
        try:
            identifier = haal_identifier_op(self.url_var.get())
        except ValueError as exc:
            messagebox.showerror("Invoer controleren", str(exc))
            return
        self.run_button.config(state="disabled")
        self.status_var.set("Uitslagen ophalen… even geduld.")
        threading.Thread(
            target=self.verwerk,
            args=(identifier,),
            daemon=True,
        ).start()

    def verwerk(self, identifier):
        try:
            soup = haal_pagina_op(identifier)
            df = parseer_uitslag(identifier, soup)
            gegevens = haal_evenementgegevens_op(soup)
            self.after(
                0,
                lambda: self.kies_bestand(identifier, df, gegevens),
            )
        except requests.RequestException as exc:
            bericht = netwerk_foutmelding(exc)
            self.after(0, lambda: self.fout(bericht))
        except Exception as exc:
            bericht = str(exc)
            self.after(0, lambda: self.fout(bericht))

    def kies_bestand(self, identifier, df, gegevens):
        if self.format_var.get().startswith("Excel"):
            extensie = ".xlsx"
            bestandstype = ("Excel-bestand", ".xlsx")
            titel = "Excel-bestand opslaan"
        else:
            extensie = ".csv"
            bestandstype = ("CSV-bestand", ".csv")
            titel = "CSV-bestand opslaan"
        path = filedialog.asksaveasfilename(
            title=titel,
            defaultextension=extensie,
            initialfile=maak_bestandsnaam(identifier, gegevens, extensie),
            filetypes=[bestandstype],
        )
        if not path:
            self.run_button.config(state="normal")
            self.status_var.set("Klaar.")
            return
        self.status_var.set("Bestand opslaan… even geduld.")
        threading.Thread(
            target=self.sla_op,
            args=(identifier, df, gegevens, path),
            daemon=True,
        ).start()

    def sla_op(self, identifier, df, gegevens, path):
        try:
            if path.lower().endswith(".csv"):
                df.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                schrijf_excel(df, gegevens, identifier, path)
            self.after(0, lambda: self.klaar(path, len(df)))
        except Exception as exc:
            bericht = str(exc)
            self.after(0, lambda: self.fout(bericht))

    def klaar(self, path, aantal):
        self.run_button.config(state="normal")
        self.status_var.set(f"Klaar: {aantal} uitslagen opgeslagen.")
        messagebox.showinfo(
            "Export voltooid",
            f"{aantal} uitslagen opgeslagen in: {path}",
        )

    def fout(self, bericht):
        self.run_button.config(state="normal")
        self.status_var.set("Export mislukt.")
        messagebox.showerror("Export mislukt", bericht)


WEB_PAGINA = r"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Uitslagen exporteren</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23146c43'/%3E%3Cg stroke='white' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round' fill='none'%3E%3Cpath d='M19 10.5L15 17.5M18.4 11.6L22 14.2L25 12M18.4 11.6L14 12.6L11.5 16M15 17.5L20 20.5L19 26.5M15 17.5L12.5 22.5L7.5 23M3.5 11h4M2.5 15.5H6'/%3E%3C/g%3E%3Ccircle cx='20.5' cy='6.5' r='2.7' fill='white'/%3E%3C/svg%3E">
<style>
:root {
  --bg: #f3f5f7; --surface: #ffffff; --surface-2: #f7f9fa; --border: #dde3e8;
  --text: #17212b; --muted: #5b6672; --accent: #146c43; --accent-hover: #0f5734;
  --accent-soft: #e5f3ec; --danger: #b42318; --danger-soft: #fdecea;
  --shadow: 0 1px 2px rgba(16,24,40,.05), 0 8px 24px rgba(16,24,40,.06);
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f1419; --surface: #171d24; --surface-2: #1d252d; --border: #2b353f;
    --text: #e6eaee; --muted: #9aa5b1; --accent: #2fa36b; --accent-hover: #3cb97b;
    --accent-soft: #15301f; --danger: #f97066; --danger-soft: #3a1a18;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25);
    color-scheme: dark;
  }
}
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--text); margin: 0;
  font: 15px/1.5 "Segoe UI", system-ui, -apple-system, sans-serif; }
.wrap { margin: 0 auto; max-width: 1080px; padding: 24px 16px 40px; }
header { align-items: center; display: flex; gap: 12px; justify-content: space-between; margin-bottom: 20px; }
.brand { align-items: center; display: flex; gap: 12px; }
.logo { background: var(--accent); border-radius: 9px; display: grid; height: 36px; place-items: center; width: 36px; }
h1 { font-size: 1.25rem; margin: 0; }
.sub { color: var(--muted); font-size: .875rem; margin: 0; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  box-shadow: var(--shadow); padding: 20px; }
.card + .card { margin-top: 16px; }
label { display: block; font-size: .875rem; font-weight: 600; margin-bottom: 6px; }
.row { display: flex; flex-wrap: wrap; gap: 10px; }
input, select { background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); font: inherit; min-height: 40px; padding: 8px 12px; }
input:focus, select:focus, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
#identifier { flex: 1 1 320px; min-width: 0; }
button { align-items: center; border: 1px solid transparent; border-radius: 8px; cursor: pointer;
  display: inline-flex; font: inherit; font-weight: 600; gap: 8px; min-height: 40px; padding: 8px 16px; }
button:disabled { cursor: not-allowed; opacity: .6; }
.primary { background: var(--accent); color: #fff; }
.primary:hover:not(:disabled) { background: var(--accent-hover); }
.secondary { background: var(--surface); border-color: var(--border); color: var(--text); }
.secondary:hover:not(:disabled) { background: var(--surface-2); }
.ghost { background: transparent; border-color: var(--border); color: var(--muted); font-weight: 500; }
.ghost:hover { color: var(--text); }
.hint { color: var(--muted); font-size: .8125rem; margin: 8px 0 0; }
.recent { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.recent:empty { display: none; }
.chip { background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; color: var(--text);
  font-size: .8125rem; font-weight: 500; min-height: 0; padding: 3px 10px; }
.chip:hover { border-color: var(--accent); }
.error { background: var(--danger-soft); border-left: 4px solid var(--danger); border-radius: 6px;
  color: var(--text); margin: 14px 0 0; padding: 10px 12px; }
.spinner { animation: spin .8s linear infinite; border: 2px solid rgba(255,255,255,.4);
  border-radius: 50%; border-top-color: #fff; height: 16px; width: 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
.event { display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; }
.event h2 { font-size: 1.2rem; margin: 0 0 2px; }
.stats { display: flex; gap: 10px; }
.stat { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; min-width: 110px; padding: 8px 14px; }
.stat b { display: block; font-size: 1.25rem; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: .8125rem; }
.toolbar { align-items: end; display: flex; flex-wrap: wrap; gap: 12px; margin-top: 18px; }
.toolbar .field { display: flex; flex: 1 1 200px; flex-direction: column; }
.toolbar .actions { display: flex; flex-wrap: wrap; gap: 8px; }
.exportinfo { color: var(--muted); font-size: .8125rem; margin-top: 8px; }
.tablewrap { border: 1px solid var(--border); border-radius: 10px; margin-top: 16px; max-height: 60vh; overflow: auto; }
table { border-collapse: collapse; font-size: .875rem; width: 100%; }
th, td { border-bottom: 1px solid var(--border); padding: 8px 12px; text-align: left; white-space: nowrap; }
th { background: var(--surface-2); color: var(--muted); font-size: .75rem; letter-spacing: .03em;
  position: sticky; text-transform: uppercase; top: 0; }
td.num, th.num { font-variant-numeric: tabular-nums; text-align: right; }
tbody tr:hover { background: var(--surface-2); }
.tablenote { color: var(--muted); font-size: .8125rem; margin-top: 8px; }
.stopped { margin: 15vh auto; max-width: 460px; text-align: center; }
footer { color: var(--muted); font-size: .8125rem; margin-top: 24px; text-align: center; }
[hidden] { display: none !important; }
@media (max-width: 560px) {
  header { align-items: flex-start; }
  .stats { width: 100%; }
  .stat { flex: 1; min-width: 0; }
  .toolbar .actions, .toolbar .actions button { width: 100%; }
  .toolbar .actions button { justify-content: center; }
}
</style>
</head>
<body>
<div class="wrap" id="app">
  <header>
    <div class="brand">
      <div class="logo" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 32 32"><path d="M19 10.5L15 17.5M18.4 11.6L22 14.2L25 12M18.4 11.6L14 12.6L11.5 16M15 17.5L20 20.5L19 26.5M15 17.5L12.5 22.5L7.5 23M3.5 11h4M2.5 15.5H6" stroke="white" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="20.5" cy="6.5" r="2.7" fill="white"/></svg>
      </div>
      <div>
        <h1>Uitslagen exporteren</h1>
        <p class="sub">Uitslagen.nl naar Excel of CSV</p>
      </div>
    </div>
    <button class="ghost" id="stop" type="button">Afsluiten</button>
  </header>

  <section class="card">
    <form id="form">
      <label for="identifier">Uitslagcode of URL</label>
      <div class="row">
        <input id="identifier" autocomplete="off" spellcheck="false" placeholder="__VOORBEELD__" required>
        <button class="primary" id="fetch" type="submit"><span id="fetchlabel">Uitslagen ophalen</span></button>
      </div>
      <p class="hint">Plak de link van een uitslagenpagina, bijvoorbeeld __VOORBEELD__</p>
      <div class="recent" id="recent"></div>
      <p class="error" id="error" role="alert" hidden></p>
    </form>
  </section>

  <section class="card" id="result" hidden>
    <div class="event">
      <div>
        <h2 id="eventname"></h2>
        <p class="sub" id="eventmeta"></p>
      </div>
      <div class="stats">
        <div class="stat"><b id="statcount"></b><span>uitslagen</span></div>
        <div class="stat"><b id="statcats"></b><span>categorieën</span></div>
      </div>
    </div>
    <div class="toolbar">
      <div class="field">
        <label for="category">Categorie</label>
        <select id="category"></select>
      </div>
      <div class="field">
        <label for="search">Zoeken</label>
        <input id="search" type="search" placeholder="Naam of woonplaats/vereniging">
      </div>
      <div class="actions">
        <button class="primary" type="button" data-format="xlsx">Download Excel</button>
        <button class="secondary" type="button" data-format="csv">Download CSV</button>
      </div>
    </div>
    <p class="exportinfo" id="exportinfo"></p>
    <div class="tablewrap">
      <table>
        <thead><tr id="thead"></tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <p class="tablenote" id="tablenote"></p>
  </section>

  <footer>Draait lokaal op deze computer · alleen bereikbaar vanaf deze pc</footer>
</div>

<div class="wrap" id="stopped" hidden>
  <div class="card stopped">
    <h2>Uitslagen is afgesloten</h2>
    <p class="sub">De lokale server is gestopt. Je kunt dit tabblad sluiten.</p>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);
const MAX_RIJEN = 500;
const RECENT_KEY = "uitslagen.recent";
let data = null;

function laadRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY)) || []; } catch { return []; }
}
function bewaarRecent(item) {
  const lijst = [item, ...laadRecent().filter((r) => r.id !== item.id)].slice(0, 5);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(lijst)); } catch {}
  toonRecent();
}
function toonRecent() {
  const box = $("recent");
  box.replaceChildren();
  for (const r of laadRecent()) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = r.naam || r.id; b.title = r.id;
    b.onclick = () => { $("identifier").value = r.id; $("form").requestSubmit(); };
    box.append(b);
  }
}

function toonFout(tekst) { $("error").textContent = tekst; $("error").hidden = !tekst; }

function bezig(aan) {
  const knop = $("fetch");
  knop.disabled = aan;
  knop.querySelector(".spinner")?.remove();
  if (aan) { const s = document.createElement("span"); s.className = "spinner"; knop.prepend(s); }
  $("fetchlabel").textContent = aan ? "Ophalen…" : "Uitslagen ophalen";
}

function formatDatum(iso) {
  if (!iso) return "";
  const [j, m, d] = iso.split("-").map(Number);
  return new Date(j, m - 1, d).toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" });
}
const nl = (n) => n.toLocaleString("nl-NL");

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  toonFout("");
  bezig(true);
  try {
    const r = await fetch("/api/uitslag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: $("identifier").value }),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.fout || "Er ging iets mis bij het ophalen.");
    data = j;
    toonResultaat();
    bewaarRecent({ id: j.identifier, naam: j.evenement.run || "" });
  } catch (err) {
    toonFout(err instanceof TypeError ? "De lokale server is niet bereikbaar. Start Uitslagen opnieuw." : err.message);
  } finally {
    bezig(false);
  }
});

function toonResultaat() {
  const ev = data.evenement;
  $("eventname").textContent = ev.run || `Uitslag ${data.identifier}`;
  $("eventmeta").textContent = [ev.plaats, formatDatum(ev.datum), data.identifier].filter(Boolean).join(" · ");
  $("statcount").textContent = nl(data.aantal);
  $("statcats").textContent = nl(data.categorieen.length);

  const sel = $("category");
  sel.replaceChildren(new Option(`Alle categorieën (${nl(data.aantal)})`, ""));
  for (const c of data.categorieen) sel.append(new Option(`${c.naam} (${nl(c.aantal)})`, c.naam));
  $("search").value = "";

  const kolommen = ["Plaats", "Naam", "Woonplaats/Vereniging", "Klasse", "Afstand",
    ...(data.heeftBrutoNetto ? ["Bruto", "Netto"] : ["Tijd"])];
  data.kolommen = kolommen;
  $("thead").replaceChildren(...kolommen.map((k) => {
    const th = document.createElement("th");
    th.textContent = k;
    if (k === "Plaats") th.className = "num";
    return th;
  }));
  $("result").hidden = false;
  toonTabel();
}

function toonTabel() {
  const cat = $("category").value;
  const zoek = $("search").value.trim().toLocaleLowerCase("nl");
  const perCat = cat ? data.rijen.filter((r) => r.Categorie === cat) : data.rijen;
  const rijen = zoek
    ? perCat.filter((r) => `${r.Naam} ${r["Woonplaats/Vereniging"]}`.toLocaleLowerCase("nl").includes(zoek))
    : perCat;

  const frag = document.createDocumentFragment();
  for (const r of rijen.slice(0, MAX_RIJEN)) {
    const tr = document.createElement("tr");
    for (const k of data.kolommen) {
      const td = document.createElement("td");
      td.textContent = r[k] ?? "";
      if (k === "Plaats") td.className = "num";
      tr.append(td);
    }
    frag.append(tr);
  }
  $("tbody").replaceChildren(frag);

  $("tablenote").textContent = rijen.length === 0
    ? "Geen resultaten voor deze zoekopdracht."
    : rijen.length > MAX_RIJEN
      ? `De eerste ${nl(MAX_RIJEN)} van ${nl(rijen.length)} rijen worden getoond.`
      : `${nl(rijen.length)} ${rijen.length === 1 ? "rij" : "rijen"} getoond.`;
  $("exportinfo").textContent =
    `De download bevat ${cat ? `categorie “${cat}”` : "alle categorieën"} (${nl(perCat.length)} uitslagen). Het zoekveld filtert alleen de weergave.`;
}

$("category").addEventListener("change", toonTabel);
$("search").addEventListener("input", toonTabel);

document.querySelectorAll("[data-format]").forEach((knop) => {
  knop.addEventListener("click", () => {
    const params = new URLSearchParams({ token: data.token, format: knop.dataset.format, categorie: $("category").value });
    window.location.href = `/download?${params}`;
  });
});

function toonGestopt() {
  clearInterval(pingTimer);
  $("app").hidden = true;
  $("stopped").hidden = false;
}

$("stop").addEventListener("click", async () => {
  try {
    await fetch("/api/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
  } catch {}
  toonGestopt();
});

let gemist = 0;
const pingTimer = setInterval(async () => {
  try {
    const r = await fetch("/api/ping", { cache: "no-store" });
    gemist = r.ok ? 0 : gemist + 1;
  } catch { gemist += 1; }
  if (gemist >= 2) toonGestopt();
}, 20000);

toonRecent();
$("identifier").focus();
</script>
</body>
</html>"""


def maak_web_pagina() -> bytes:
    return WEB_PAGINA.replace(
        "__VOORBEELD__",
        html.escape(VOORBEELD_URL, quote=True),
    ).encode("utf-8")


def foutpagina(titel: str, bericht: str) -> bytes:
    return (
        "<!doctype html><html lang='nl'><meta charset='utf-8'>"
        f"<title>{html.escape(titel)}</title>"
        "<body style='font:15px Segoe UI,sans-serif;margin:15vh auto;max-width:480px;padding:0 16px'>"
        f"<h1 style='font-size:1.25rem'>{html.escape(titel)}</h1>"
        f"<p>{html.escape(bericht)}</p><p><a href='/'>Terug naar Uitslagen</a></p></body></html>"
    ).encode("utf-8")


class UitslagenServer(ThreadingHTTPServer):
    # Op Windows staat SO_REUSEADDR toe dat twee servers dezelfde poort delen;
    # uitzetten zodat een tweede start de draaiende server kan herkennen.
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = threading.Lock()
        self.uitslagen: OrderedDict[str, dict] = OrderedDict()
        self.laatste_contact = time.monotonic()

    def bewaar(self, item: dict) -> str:
        token = secrets.token_urlsafe(16)
        with self.lock:
            self.uitslagen[token] = item
            while len(self.uitslagen) > MAX_OPGESLAGEN:
                self.uitslagen.popitem(last=False)
        return token

    def zoek(self, token: str) -> dict | None:
        with self.lock:
            return self.uitslagen.get(token)


class WebHandler(BaseHTTPRequestHandler):
    server_version = "UitslagenLocal/2.0"
    server: UitslagenServer

    def log_message(self, format, *args):
        if not self.path.startswith("/api/ping"):
            super().log_message(format, *args)

    def _is_local_request(self) -> bool:
        host = self.headers.get("Host", "")
        try:
            if host and urlsplit(f"//{host}").hostname not in {
                "localhost",
                "127.0.0.1",
            }:
                return False
        except ValueError:
            return False

        origin = self.headers.get("Origin")
        if origin:
            try:
                if urlsplit(origin).hostname not in {"localhost", "127.0.0.1"}:
                    return False
            except ValueError:
                return False
        return True

    def _send(
        self,
        status: int,
        content: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        for naam, waarde in (extra_headers or {}).items():
            self.send_header(naam, waarde)
        self.end_headers()
        self.wfile.write(content)

    def _send_html(self, status: int, content: bytes) -> None:
        self._send(
            status,
            content,
            "text/html; charset=utf-8",
            {"X-Frame-Options": "DENY"},
        )

    def _send_json(self, status: int, data: dict) -> None:
        content = json.dumps(
            data,
            ensure_ascii=False,
            default=lambda waarde: waarde.item() if hasattr(waarde, "item") else str(waarde),
        ).encode("utf-8")
        self._send(status, content, "application/json; charset=utf-8")

    def _lees_json(self) -> dict | None:
        # Een JSON-content-type kan een andere website niet zonder CORS-preflight
        # meesturen, wat samen met de Origin-controle CSRF voorkomt.
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return None
        try:
            lengte = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if lengte < 0 or lengte > 4096:
            return None
        try:
            data = json.loads(self.rfile.read(lengte).decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self) -> None:
        if not self._is_local_request():
            self.send_error(403)
            return
        self.server.laatste_contact = time.monotonic()
        url = urlsplit(self.path)
        if url.path == "/":
            self._send_html(200, maak_web_pagina())
        elif url.path == "/api/ping":
            self._send_json(200, {"app": "uitslagen", "ok": True})
        elif url.path == "/download":
            self._download(parse_qs(url.query))
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if not self._is_local_request():
            self.send_error(403)
            return
        self.server.laatste_contact = time.monotonic()
        data = self._lees_json()
        if data is None:
            self._send_json(400, {"fout": "Ongeldige aanvraag."})
            return
        if self.path == "/api/uitslag":
            self._haal_uitslag(data)
        elif self.path == "/api/stop":
            self._send_json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_error(404)

    def _haal_uitslag(self, data: dict) -> None:
        try:
            identifier = haal_identifier_op(str(data.get("identifier", "")))
            soup = haal_pagina_op(identifier)
            df = parseer_uitslag(identifier, soup)
            gegevens = haal_evenementgegevens_op(soup)
        except ValueError as exc:
            self._send_json(400, {"fout": str(exc)})
            return
        except requests.RequestException as exc:
            self._send_json(502, {"fout": netwerk_foutmelding(exc)})
            return

        token = self.server.bewaar(
            {"identifier": identifier, "df": df, "gegevens": gegevens}
        )
        kolommen = ["Plaats", "Naam", "Woonplaats/Vereniging", "Categorie", "Klasse", "Afstand", "Bruto", "Netto", "Tijd"]
        rijen = df[kolommen].astype(object).where(df[kolommen].notna(), None)
        self._send_json(200, {
            "token": token,
            "identifier": identifier,
            "evenement": gegevens,
            "aantal": len(df),
            "categorieen": [
                {"naam": naam, "aantal": aantal}
                for naam, aantal in df.groupby("Categorie", sort=False).size().items()
            ],
            "heeftBrutoNetto": bool(df["Netto"].notna().any()),
            "rijen": rijen.to_dict("records"),
        })

    def _download(self, query: dict[str, list[str]]) -> None:
        token = query.get("token", [""])[0]
        export_format = query.get("format", [""])[0]
        categorie = query.get("categorie", [""])[0]
        item = self.server.zoek(token)
        if item is None:
            self._send_html(
                404,
                foutpagina(
                    "Export verlopen",
                    "Deze export is niet meer beschikbaar. Haal de uitslag opnieuw op.",
                ),
            )
            return
        if export_format not in {"xlsx", "csv"}:
            self._send_html(400, foutpagina("Ongeldig formaat", "Kies Excel of CSV."))
            return

        df = item["df"]
        if categorie:
            df = df[df["Categorie"] == categorie]
            if df.empty:
                self._send_html(
                    404,
                    foutpagina("Geen uitslagen", "Deze categorie bevat geen uitslagen."),
                )
                return

        extensie = f".{export_format}"
        bestandsnaam = maak_bestandsnaam(
            item["identifier"], item["gegevens"], extensie, categorie
        )
        content_type = (
            "text/csv; charset=utf-8"
            if export_format == "csv"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        self._send(
            200,
            maak_export(df, item["gegevens"], item["identifier"], export_format),
            content_type,
            {
                "Content-Disposition": (
                    f'attachment; filename="uitslagen_export{extensie}"; '
                    f"filename*=UTF-8''{quote(bestandsnaam)}"
                ),
            },
        )


def draait_al(poort: int) -> bool:
    try:
        response = requests.get(f"http://127.0.0.1:{poort}/api/ping", timeout=2)
        return response.ok and response.json().get("app") == "uitslagen"
    except (requests.RequestException, ValueError):
        return False


def bewaak_activiteit(server: UitslagenServer) -> None:
    """Stop de server als er een tijd geen browsertabblad meer contact heeft."""
    while True:
        time.sleep(10)
        if time.monotonic() - server.laatste_contact > INACTIEF_TIMEOUT:
            print("Geen browsertabblad meer actief; de server wordt gestopt.")
            server.shutdown()
            return


def start_webapp() -> None:
    try:
        server = UitslagenServer(("127.0.0.1", VASTE_POORT), WebHandler)
    except OSError:
        if draait_al(VASTE_POORT):
            url = f"http://127.0.0.1:{VASTE_POORT}/"
            print(f"Uitslagen draait al op {url}; de pagina wordt geopend.")
            webbrowser.open(url)
            return
        server = UitslagenServer(("127.0.0.1", 0), WebHandler)

    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Uitslagen is gestart op {url}")
    print("Sluit af via de knop in de pagina; na het sluiten van de browser stopt de server vanzelf.")
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    threading.Thread(target=bewaak_activiteit, args=(server,), daemon=True).start()
    try:
        if not webbrowser.open(url):
            print(f"Open {url} handmatig in je browser.")
        server_thread.join()
    except KeyboardInterrupt:
        server.shutdown()
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start de lokale webversie in plaats van de desktopapp.",
    )
    args = parser.parse_args()
    if args.web:
        start_webapp()
    else:
        App().mainloop()
