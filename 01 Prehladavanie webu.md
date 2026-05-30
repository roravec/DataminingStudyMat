# Prehľadávanie webu – Študijný materiál

---

## Čo skript robí (stručne)

Program automaticky stiahne obsah webovej stránky cez HTTP, spracuje HTML kód pomocou knižnice BeautifulSoup, vytiahne z neho čistý text bez HTML tagov a uloží ho do `.txt` súboru.

---

## Postup riešenia – krok za krokom

1. Definujeme URL adresu, ktorú chceme stiahnuť
2. Pošleme HTTP GET požiadavku na server pomocou `requests.get()`
3. Skontrolujeme, či server vrátil úspešnú odpoveď (`raise_for_status()`)
4. Spracujeme HTML odpoveď pomocou `BeautifulSoup`
5. Vytiahnutie titulku stránky z tagu `<title>`
6. Vytiahnutie čistého textu z tagu `<body>` pomocou `get_text()`
7. Otvoríme súbor a uložíme výsledok

---

## Knižnice

| Knižnica | Účel |
|---|---|
| `requests` | Posiela HTTP požiadavky (GET, POST...) a sťahuje obsah webových stránok |
| `bs4` (BeautifulSoup) | Parsuje HTML/XML do stromovej štruktúry, umožňuje ľahké vyhľadávanie elementov |

---

## Vysvetlenie metód

### `requests.get(url)`
Pošle HTTP GET požiadavku na server a vráti objekt `Response` s vlastnosťami `status_code`, `text` (HTML ako string) a `content` (surové byty).

**Dôležité HTTP stavové kódy:**

| Kód | Význam |
|---|---|
| 200 | OK – úspech |
| 404 | Not Found – stránka neexistuje |
| 403 | Forbidden – prístup zamietnutý |
| 500 | Internal Server Error – chyba servera |

---

### `response.raise_for_status()`
Skontroluje stavový kód. Ak je **4xx alebo 5xx**, vyhodí výnimku `HTTPError`. Pri kóde 200 nič nerobí.

---

### `BeautifulSoup(response.text, 'html.parser')`
Rozparsuje HTML text do stromovej štruktúry. Druhý argument `'html.parser'` je vstavaný Python parser – nevyžaduje inštaláciu. Výsledok `soup` umožňuje vyhľadávať elementy podľa tagu, triedy, atribútu.

---

### `soup.title.string`
`soup.title` vráti element `<title>`. `.string` vytiahne jeho textový obsah. Podmienka `if soup.title else 'No Title Found'` ochráni pred pádom, ak `<title>` v HTML chýba.

---

### `soup.body.get_text(separator='\n', strip=True)`
Najdôležitejšia metóda – vytiahne **čistý text** z celého `<body>` bez HTML tagov.
- `separator='\n'` – medzi bloky vloží nový riadok
- `strip=True` – oreže biele znaky z každého bloku

---

### `open(filename, 'w', encoding='utf-8')` a `f.write()`
Otvorí súbor pre zápis. `encoding='utf-8'` je nutné pre správne uloženie diakritiky. Blok `with` zabezpečí automatické zatvorenie súboru aj pri chybe.

---

### `soup.find_all('a')` a `link.get('href')` (zakomentované)
`find_all('a')` vráti zoznam všetkých odkazov `<a>` v HTML. `link.get('href')` vytiahne URL z atribútu `href`. Podmienka `if href` preskočí odkazy bez cieľa.

---

## Ošetrenie chýb – `try / except`

```python
try:
    # hlavný kód
except requests.exceptions.RequestException as e:
    print(f"Error fetching {url}: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```

Program má **dve vrstvy ochrany:**

| `except` blok | Čo zachytáva |
|---|---|
| `requests.exceptions.RequestException` | Všetky sieťové chyby: nedostupný server, neplatná URL, timeout, SSL chyba |
| `Exception` | Akákoľvek iná neočakávaná chyba (napr. chyba pri parsovaní) |

**Prečo je to dôležité?**  
Práca so sieťou je **nespoľahlivá** – server môže byť nedostupný, spojenie môže vypadnúť, URL môže byť neplatná. Bez `try/except` by každá taká situácia spôsobila pád celého programu.

---

## Vstupné a výstupné súbory

### URL adresy, ktoré boli crawlované:

| Výstupný súbor | Zdrojová URL |
|---|---|
| `ukf.txt` | `https://ukf.sk` |
| `ukfkonzorcium.txt` | `https://www.ukf.sk/univerzita/konzorcium-umb-a-ukf` |
| `fpvai.txt` | `https://www.ukf.sk/fakulty-a-sucasti/fakulta-prirodnych-vied-a-informatiky` |
| `podknamstudovat.txt` | `https://www.ukf.sk/prijimacie-konanie/pod-k-nam-studovat` |
| `dslsk.txt` | `https://dsl.sk` |

### Štruktúra výstupného `.txt` súboru:

Každý súbor začína hlavičkou s URL adresou a oddeľovačom, za ktorým nasleduje čistý text zo stránky:

```
CONTENT FROM: https://www.ukf.sk/univerzita/konzorcium-umb-a-ukf
==================================================

UKF.sk
Adresár
Informačné systémy
...
```

---

## Zhrnutie najdôležitejších metód

| Metóda | Knižnica | Účel |
|---|---|---|
| `requests.get(url)` | `requests` | Stiahnutie obsahu webovej stránky cez HTTP GET |
| `response.raise_for_status()` | `requests` | Overenie úspešnosti HTTP odpovede |
| `BeautifulSoup(html, parser)` | `bs4` | Parsovanie HTML do stromovej štruktúry |
| `soup.title.string` | `bs4` | Získanie textu z `<title>` tagu |
| `soup.body.get_text(separator, strip)` | `bs4` | Extrahovanie čistého textu z `<body>` |
| `soup.find_all('a')` | `bs4` | Nájdenie všetkých odkazov v HTML |
| `link.get('href')` | `bs4` | Získanie URL z atribútu odkazu |
| `open(file, 'w', encoding)` | Python | Otvorenie súboru pre zápis |
| `f.write(text)` | Python | Zápis textu do súboru |

---

## Otázky, ktoré môže položiť profesor

**Q: Čo je HTTP GET požiadavka a čím sa líši od POST?**  
A: GET slúži len na získanie dát zo servera, parametre sú viditeľné v URL. POST posiela dáta telu požiadavky (napr. prihlasovací formulár), nie sú viditeľné v URL a môže meniť stav servera.

**Q: Čo je parsovanie HTML?**  
A: Parsovanie je proces rozloženia textového reťazca (HTML kódu) na štruktúrovanú formu – strom DOM, kde každý HTML tag je uzol. Umožňuje to programaticky pristupovať k jednotlivým elementom.

**Q: Prečo používame `encoding='utf-8'` pri zápise do súboru?**  
A: UTF-8 je kódovanie znakov, ktoré podporuje celú Unicode tabuľku vrátane slovenských znakov (á, é, í, ó, ú, č, š, ž, ď, ľ, ŕ, ĺ, ť, ň). Bez správneho kódovania by sa diakritika uložila nesprávne alebo by nastala chyba.

**Q: Prečo je crawler obalený v `try/except`?**  
A: Sieťové operácie sú nespoľahlivé – server môže byť nedostupný, URL môže byť neplatná, spojenie môže vypadnúť (timeout). `try/except` zabezpečí, že program pri chybe nespadne, ale vypíše chybovú správu a pokračuje.

**Q: Čo robí `soup.body.get_text(separator='\n', strip=True)`?**  
A: Prechádza celý HTML strom elementov v `<body>`, vytiahne len textový obsah (bez tagov), vloží `\n` medzi bloky a oreže biele znaky z každého bloku.

**Q: Aký je rozdiel medzi `response.text` a `response.content`?**  
A: `response.text` je reťazec (string) dekódovaný podľa kódovania odpovede. `response.content` sú surové byty (`bytes`) – používa sa napr. pri sťahovaní obrázkov alebo binárnych súborov.

**Q: Čo je DOM?**  
A: Document Object Model – stromová reprezentácia HTML dokumentu. Každý HTML element (tag) je uzol stromu. Koreň je `<html>`, jeho deti sú `<head>` a `<body>`, atď. BeautifulSoup vytvára vlastnú stromovú štruktúru podobnú DOM.

**Q: Prečo je `<a href="...">` dôležité pri crawlovaní?**  
A: `<a href>` obsahuje URL adresy odkazov na ďalšie stránky. Skutočný web crawler tieto URL extrahuje a rekurzívne prehľadáva – tak fungujú napríklad Google crawlery.

**Q: Čo je web crawling vs. web scraping?**  
A: **Crawling** = automatické prechádzanie a objavovanie stránok (sledovanie odkazov). **Scraping** = extrakcia konkrétnych dát z webovej stránky. Náš skript robí scraping (extrahuje text), s prvkami crawlingu (sťahuje konkrétnu URL).
