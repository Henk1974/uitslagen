# Uitslagen.nl exporteren

Deze Windows-app haalt uitslagen op van Uitslagen.nl en exporteert ze naar
Excel (`.xlsx`) of CSV (`.csv`).

## Starten

- Dubbelklik op `uitslagen-verborgen.vbs` om de app zonder zichtbaar
  opdrachtpromptvenster te starten.
- Start `uitslagen.bat` rechtstreeks als je eventuele foutmeldingen in het
  opdrachtpromptvenster wilt zien.

De batchfile installeert zo nodig de vereiste Python-pakketten voor de huidige
gebruiker. Python moet beschikbaar zijn via het `py`-commando.

## Gebruik

Vul een uitslagcode of volledige URL van Uitslagen.nl in, kies Excel of CSV en
selecteer waar het bestand moet worden opgeslagen. Resultaten uit meerdere
tabellen worden samengevoegd; de tabelcaption wordt gebruikt als categorie en
wordt bij een komma opgesplitst in gender/categorie en afstand. De export bevat
ook bruto- en nettotijd wanneer de pagina die vermeldt.
