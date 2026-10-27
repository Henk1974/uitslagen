# Uitslagen.nl exporteren

Deze Windows-app haalt uitslagen op van Uitslagen.nl en exporteert ze naar
Excel (`.xlsx`) of CSV (`.csv`). Je kunt de desktopapp of de lokale webversie
gebruiken.

> **Let op: deze app werkt alleen op Windows** (Windows 10 of 11, op een pc of
> laptop). Op een Mac, Chromebook, Linux-computer, tablet of telefoon werkt de
> installer niet.

## Installeren

Download `Uitslagen-installatie.exe` via de
[nieuwste release](https://github.com/Henk1974/uitslagen/releases/latest) en
dubbelklik erop. Python is daarvoor niet nodig. Toont Windows de melding
*"Windows heeft uw pc beschermd"*, klik dan op **Meer informatie** en daarna
op **Toch uitvoeren**. Na de installatie start je de app via **Uitslagen** op
het bureaublad of in het startmenu.

De onderstaande startbestanden zijn bedoeld voor wie de app vanuit de
broncode draait.

## Desktopapp starten

- Dubbelklik op `uitslagen-verborgen.vbs` om de app te starten met het
  opdrachtpromptvenster geminimaliseerd.
- `uitslagen.bat` start de launcher en sluit het eigen opdrachtpromptvenster
  meteen. Windows kan bij rechtstreeks starten van een `.bat` kort een venster
  tonen; start de `.vbs` rechtstreeks om dat te vermijden. Gebruik
  `uitslagen.bat /console` vanuit een opdrachtprompt om eventuele
  foutmeldingen zichtbaar te maken.

De batchfiles installeren de Python-pakketten uit `requirements.txt` voor de
huidige gebruiker, maar alleen als ze nog ontbreken. Python moet beschikbaar zijn via het `py`-commando.

## Lokale webversie starten

- Dubbelklik op `uitslagen-web.vbs`. De lokale server start en de webpagina
  opent automatisch in je browser (http://127.0.0.1:8765/).
- Je kunt ook `uitslagen-web.bat` starten om eventuele foutmeldingen in het
  opdrachtpromptvenster te zien.
- Vul de uitslagcode of URL in en klik op **Uitslagen ophalen**. Je ziet dan
  het evenement, het aantal uitslagen en een voorbeeld van de tabel. Je kunt
  filteren op categorie en zoeken op naam of woonplaats/vereniging.
- Klik op **Download Excel** of **Download CSV**. Als er een categorie is
  gekozen, bevat de download alleen die categorie.
- Recent opgehaalde uitslagen staan als knoppen onder het invoerveld.
- Klik op **Afsluiten** wanneer je klaar bent. Sluit je alleen de browser,
  dan stopt de server na ongeveer drie minuten vanzelf.
- Start je de webversie terwijl die al draait, dan wordt de bestaande pagina
  geopend in plaats van een tweede server te starten.

De server is alleen bereikbaar vanaf deze computer; dit is geen website die
vanaf internet toegankelijk is. De webversie gebruikt dezelfde Python-installatie
en pakketten als de desktopapp. Een losse HTML-snelkoppeling kan de
Python-server niet starten; gebruik daarom `uitslagen-web.vbs` als
startbestand. Je kunt daarvan eventueel zelf een snelkoppeling op het
bureaublad maken.

## Excel-export

Het Excel-bestand bevat een tabblad **Uitslagen** met een opgemaakte kopregel,
vastgezette eerste rij, filterknoppen en passende kolombreedtes, en een
tabblad **Evenement** met naam, plaats, datum, uitslagcode, bron-URL en
exportmoment.

## Gebruik

Vul een uitslagcode of volledige URL van Uitslagen.nl in, kies Excel of CSV en
selecteer waar het bestand moet worden opgeslagen. Resultaten uit meerdere
tabellen worden samengevoegd; de tabelcaption wordt gebruikt als categorie en
wordt bij een komma opgesplitst in klasse en afstand. De export bevat
ook bruto- en nettotijd wanneer de pagina die vermeldt. De voorgestelde
bestandsnaam bevat de runnaam, plaats en datum van het evenement als die
gegevens op de pagina beschikbaar zijn. Klik op **Stoppen** om de applicatie
te sluiten.
