# Uitslagen.nl exporteren

Deze Windows-app haalt uitslagen op van Uitslagen.nl en exporteert ze naar
Excel (`.xlsx`) of CSV (`.csv`).

## Starten

- Dubbelklik op `uitslagen-verborgen.vbs` om de app te starten met het
  opdrachtpromptvenster geminimaliseerd.
- `uitslagen.bat` start de launcher en sluit het eigen opdrachtpromptvenster
  meteen. Windows kan bij rechtstreeks starten van een `.bat` kort een venster
  tonen; start de `.vbs` rechtstreeks om dat te vermijden. Gebruik
  `uitslagen.bat /console` vanuit een opdrachtprompt om eventuele
  foutmeldingen zichtbaar te maken.

De batchfile installeert zo nodig de vereiste Python-pakketten voor de huidige
gebruiker. Python moet beschikbaar zijn via het `py`-commando.

## Gebruik

Vul een uitslagcode of volledige URL van Uitslagen.nl in, kies Excel of CSV en
selecteer waar het bestand moet worden opgeslagen. Resultaten uit meerdere
tabellen worden samengevoegd; de tabelcaption wordt gebruikt als categorie en
wordt bij een komma opgesplitst in discipline en afstand. De export bevat
ook bruto- en nettotijd wanneer de pagina die vermeldt. De voorgestelde
bestandsnaam bevat de runnaam, plaats en datum van het evenement als die
gegevens op de pagina beschikbaar zijn. Klik op **Stoppen** om de applicatie
te sluiten.
