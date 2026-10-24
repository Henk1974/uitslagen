import re
import threading
import tkinter as tk
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

def lees_uitslag(identifier: str) -> pd.DataFrame:
    url = f"https://uitslagen.nl/{identifier}"
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; UitslagenScraper/1.0)"},
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    resultaten = []

    for tabel in soup.select(".table.uitslagen"):
        caption = tabel.select_one(".caption")
        if caption is None:
            continue
        categorie = caption.get_text(" ", strip=True)
        gender, afstand = (None, None)
        if "," in categorie:
            gender, afstand = (deel.strip() for deel in categorie.split(",", 1))

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
                "Gender": gender,
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
                        gender, afstand = (None, None)
                        if "," in categorie:
                            gender, afstand = (
                                deel.strip() for deel in categorie.split(",", 1)
                            )
                        resultaten.append({
                            "UitslagID": identifier,
                            "Categorie": categorie,
                            "Gender": gender,
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
       self.run_button = ttk.Button(
           frame, text="Uitslagen ophalen en opslaan", command=self.start
       )
       self.run_button.pack(anchor="w")
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
       if self.format_var.get().startswith("Excel"):
           path = filedialog.asksaveasfilename(
               title="Excel-bestand opslaan",
               defaultextension=".xlsx",
               initialfile=f"uitslagen_{identifier}.xlsx",
               filetypes=[("Excel-bestand", ".xlsx")],
           )
       else:
           path = filedialog.asksaveasfilename(
               title="CSV-bestand opslaan",
               defaultextension=".csv",
               initialfile=f"uitslagen_{identifier}.csv",
               filetypes=[("CSV-bestand", ".csv")],
           )
       if not path:
           return
       self.run_button.config(state="disabled")
       self.status_var.set("Uitslagen ophalen… even geduld.")
       threading.Thread(
           target=self.verwerk,
           args=(identifier, path),
           daemon=True,
       ).start()

   def verwerk(self, identifier, path):
       try:
           df = lees_uitslag(identifier)
           if path.lower().endswith(".csv"):
               df.to_csv(path, index=False, encoding="utf-8-sig")
           else:
               df.to_excel(path, index=False)
           self.after(0, lambda: self.klaar(path, len(df)))
       except requests.RequestException as exc:
           bericht = f"De website kon niet worden opgehaald: {exc}"
           self.after(0, lambda: self.fout(bericht))
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