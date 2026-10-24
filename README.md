# Uitslagen.nl exporteren

Deze Windows-app haalt uitslagen op van Uitslagen.nl en exporteert ze naar
Excel (`.xlsx`) of CSV (`.csv`). Je kunt de desktopapp of de lokale webversie
gebruiken.

## Desktopapp starten

- Dubbelklik op `uitslagen-verborgen.vbs` om de app te starten met het
  opdrachtpromptvenster geminimaliseerd.
- `uitslagen.bat` start de launcher en sluit het eigen opdrachtpromptvenster
  meteen. Windows kan bij rechtstreeks starten van een `.bat` kort een venster
  tonen; start de `.vbs` rechtstreeks om dat te vermijden. Gebruik
  `uitslagen.bat /console` vanuit een opdrachtprompt om eventuele
  foutmeldingen zichtbaar te maken.

De batchfile installeert zo nodig de vereiste Python-pakketten voor de huidige
gebruiker. Python moet beschikbaar zijn via het `py`-commando.

## Lokale webversie starten

- Dubbelklik op `uitslagen-web.vbs`. De lokale server start en de webpagina
  opent automatisch in je browser.
- Je kunt ook `uitslagen-web.bat` starten om eventuele foutmeldingen in het
  opdrachtpromptvenster te zien.
- Vul de uitslagcode of URL in en kies Excel of CSV. De browser downloadt het
  exportbestand.
- Klik op **Lokale server stoppen** in de webpagina wanneer je klaar bent.

De server is alleen bereikbaar vanaf deze computer; dit is geen website die
vanaf internet toegankelijk is. De webversie gebruikt dezelfde Python-installatie
en pakketten als de desktopapp. De bestaande `uitslagen.bat` en de desktopapp
blijven gewoon werken. Een losse HTML-snelkoppeling kan de Python-server niet
starten; gebruik daarom `uitslagen-web.vbs` als startbestand. Je kunt daarvan
eventueel zelf een snelkoppeling op het bureaublad maken.

## Gebruik

Vul een uitslagcode of volledige URL van Uitslagen.nl in, kies Excel of CSV en
selecteer waar het bestand moet worden opgeslagen. Resultaten uit meerdere
tabellen worden samengevoegd; de tabelcaption wordt gebruikt als categorie en
wordt bij een komma opgesplitst in discipline en afstand. De export bevat
ook bruto- en nettotijd wanneer de pagina die vermeldt. De voorgestelde
bestandsnaam bevat de runnaam, plaats en datum van het evenement als die
gegevens op de pagina beschikbaar zijn. Klik op **Stoppen** om de applicatie
te sluiten.
