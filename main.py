import re
import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse
import pandas as pd
import requests
from bs4 import BeautifulSoup

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

def haal_pagina_op(identifier: str) -> BeautifulSoup:
    url = f"https://uitslagen.nl/{identifier}"
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; UitslagenScraper/1.0)"},
        timeout=30,
    )
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


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
        plaats = info[0].get_text(" ", strip=True).replace("\u2022", "")
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
) -> str:
    onderdelen = [
        veilige_bestandsnaam(gegevens[sleutel])
        for sleutel in ("run", "plaats", "datum")
        if gegevens.get(sleutel)
    ]
    onderdelen.append(veilige_bestandsnaam(identifier))
    return f"uitslagen_{'_'.join(onderdelen)}{extensie}"


def lees_uitslag(identifier: str) -> pd.DataFrame:
    return parseer_uitslag(identifier, haal_pagina_op(identifier))


def parseer_uitslag(identifier: str, soup: BeautifulSoup) -> pd.DataFrame:
    resultaten = []

    for tabel in soup.select(".table.uitslagen"):
        caption = tabel.select_one(".caption")
        if caption is None:
            continue
        categorie = caption.get_text(" ", strip=True)
        discipline, afstand = (None, None)
        if "," in categorie:
            discipline, afstand = (
                deel.strip() for deel in categorie.split(",", 1)
            )

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
                "Discipline": discipline,
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
                        discipline, afstand = (None, None)
                        if "," in categorie:
                            discipline, afstand = (
                                deel.strip() for deel in categorie.split(",", 1)
                            )
                        resultaten.append({
                            "UitslagID": identifier,
                            "Categorie": categorie,
                            "Discipline": discipline,
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

class App(tk.Tk):
   def __init__(self):
       super().__init__()
       self.title("Uitslagen.nl naar Excel / CSV")
       self.geometry("610x300")
       self.minsize(560, 280)
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
       self.url_var = tk.StringVar(value="https://uitslagen.nl/2026101900861")
       self.url_entry = ttk.Entry(frame, textvariable=self.url_var)
       self.url_entry.pack(fill="x")
       self.url_entry.focus_set()
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
           bericht = f"De website kon niet worden opgehaald: {exc}"
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
           args=(df, path),
           daemon=True,
       ).start()

   def sla_op(self, df, path):
       try:
           if path.lower().endswith(".csv"):
               df.to_csv(path, index=False, encoding="utf-8-sig")
           else:
               df.to_excel(path, index=False)
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

if __name__ == "__main__":
    App().mainloop()