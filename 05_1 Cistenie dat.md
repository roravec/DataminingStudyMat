# Task 1 – Čistenie dát (Data Cleaning)

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Apache webový server zapisuje do logu **každý** HTTP požiadavok bez výnimky — od skutočných kliknutí ľudí, cez automatické načítavanie obrázkov a CSS súborov až po požiadavky robotov vyhľadávacích služieb. Surový log je teda zmes signálu a šumu.

Pre analýzu správania používateľov sú relevantné len záznamy o skutočných navigačných kliknutiach na stránky. Obrázok načítaný na pozadí, chybná požiadavka alebo interný monitorovací skript — to všetko komplikuje analýzu a musí byť odstránené.

Skript rieši tento problém v dvoch fázach:

1. **Parsovanie** — každý textový riadok logu rozloží regulárnym výrazom na štruktúrované polia (stĺpce tabuľky).
2. **Čistenie v 6 krokoch** — z výslednej tabuľky postupne vymaže záznamy, ktoré nie sú skutočnými kliknutiami návštevníka.

---

### Apache Combined Log Format – čo to je a ako vyzerá

Každý riadok logu opisuje **jeden HTTP požiadavok**. Príklad:

```
5.9.83.211 - - [12/Nov/2017:06:27:01 +0100] "GET /o-nas HTTP/1.1" 200 187383 "-" "Mozilla/5.0 (Windows NT 10.0)"
```

Polia zľava doprava, s ich názvami v kóde:

```
5.9.83.211             → IP        (stĺpec 1)
-                      → Cookie    (stĺpec 2 – RFC 1413 ident, vždy "-", vymažeme)
-                      → user      (stĺpec 3 – HTTP auth user, vždy "-", vymažeme)
12/Nov/2017:06:27:01   → DateTime  (stĺpec 4 – v hranatých zátvorkách)
GET                    → RequestMethod (stĺpec 5)
/o-nas                 → URL       (stĺpec 6)
HTTP/1.1               → RequestVersion (stĺpec 7)
200                    → StatusCode (stĺpec 8)
187383                 → Bytes     (stĺpec 9 – veľkosť odpovede, vymažeme)
"-"                    → Referrer  (stĺpec 10 – odkiaľ prišiel používateľ)
"Mozilla/5.0..."       → Agent     (stĺpec 11 – User-Agent reťazec)
```

**Prečo Combined a nie Common?**  
Apache Common Log (starší formát) obsahuje len 7 polí bez `Referrer` a `Agent`. Combined Log pridáva práve tieto dve polia — bez nich by sme nemohli identifikovať robotov (Task 2) ani doplňovať chýbajúce cesty (Task 5).

---

### Vstup a výstup

```
wm2020projekt_oravec.log
          │
          │  parse_log_to_dataframe()  ← regulárny výraz na každý riadok
          │  clean_data()              ← 6 krokov čistenia
          ▼
wm2020projekt_cleaned.csv
```

| Súbor | Popis |
|---|---|
| `wm2020projekt_oravec.log` | Surový Apache Combined Log, týždeň 12.–18.11.2017 |
| `wm2020projekt_cleaned.csv` | Očistená tabuľka: `IP`, `DateTime`, `RequestMethod`, `URL`, `RequestVersion`, `StatusCode`, `Referrer`, `Agent` |

---

## Postup riešenia – krok za krokom

### 1. Parsovanie logu regulárnym výrazom – `parse_log_to_dataframe()`

Funkcia číta log riadok po riadku (v C by to bolo `while (fgets(buf, ..., f) != NULL)`). Na každý riadok aplikuje regulárny výraz `LOG_LINE_REGEX`.

#### Regulárny výraz riadok po riadku

```python
LOG_LINE_REGEX = re.compile(
    r'(\S+)'            # sk.  1: IP adresa        – ľubovoľné non-whitespace znaky
    r' (\S+)'           # sk.  2: Cookie/ident      – vždy "-"
    r' (\S+)'           # sk.  3: user/auth         – vždy "-"
    r' \[([^\]]+)\]'    # sk.  4: DateTime          – obsah [...]  bez závoriek
    r' "(\S+)'          # sk.  5: RequestMethod     – prvé slovo za úvodzovkou
    r' (\S+)'           # sk.  6: URL               – druhé slovo (bez medzier)
    r' ([^"]+)"'        # sk.  7: RequestVersion    – zvyšok do uzatváracej "
    r' (\d{3})'         # sk.  8: StatusCode        – presne 3 číslice
    r' (\S+)'           # sk.  9: Bytes             – číslo alebo "-"
    r' "([^"]*)"'       # sk. 10: Referrer          – obsah v úvodzovkách (môže byť prázdny)
    r' "([^"]*)"'       # sk. 11: Agent             – User-Agent reťazec
)
```

**Vysvetlenie kľúčových regex prvkov:**

| Vzor | Popis | Prečo takto |
|---|---|---|
| `\S+` | 1+ non-whitespace znakov | IP, metóda, URL neobsahujú medzery |
| `\[([^\]]+)\]` | Obsah `[...]` – `[^\]]+` = akýkoľvek znak okrem `]` | DateTime je ohraničený `[` a `]` |
| `([^"]+)"` | Znaky iné ako `"`, ukončené `"` | Zachytí `HTTP/1.1` medzi metódou a `"` |
| `(\d{3})` | Presne 3 číslice | StatusCode je vždy 3-ciferný (200, 404, ...) |
| `"([^"]*)"` | Obsah v `"..."` – `*` = môže byť aj prázdny | Referrer môže byť `-` alebo URL |

**Prečo `re.compile()` pred cyklom, nie `re.match()` priamo?**  
`re.compile()` skompiluje vzor raz do internej formy. Pre milióny riadkov logu je rozdiel dramatický — regex engine preloží vzor raz a pri každom `.match()` ho len aplikuje, nestráca čas opätovnou kompiláciou.

**Prečo `.match()` a nie `.search()`?**  
`.match()` hľadá zhodu len **od začiatku** reťazca — čo je správne, lebo každý riadok Apache logu začína IP adresou. `.search()` by prehľadal celý reťazec a našiel by zhodu kdekoľvek, čo je pomalé a zbytočné.

#### Celý tok parsingu

```
Textový riadok logu:
"5.9.83.211 - - [12/Nov/2017:06:27:01 +0100] "GET /o-nas HTTP/1.1" 200 187383 "-" "Mozilla/5.0""
                │
                ▼  LOG_LINE_REGEX.match(line.strip())
                │
      ┌─── Zhoda? Nie ───►  continue  (prázdny riadok, komentar, ...)
      │
      └─── Zhoda? Áno ───►  m.group(1)  = "5.9.83.211"
                            m.group(4)  = "12/Nov/2017:06:27:01 +0100"
                            m.group(5)  = "GET"
                            m.group(6)  = "/o-nas"
                            m.group(8)  = "200"  → int("200") = 200
                            ...
                            record = { "IP": "5.9.83.211", "DateTime": ..., ... }
                            records.append(record)
                │
                ▼  (po prečítaní celého súboru)
        pd.DataFrame(records)
                │
                ▼
        DataFrame: jeden riadok = jeden HTTP požiadavok
```

---

### 2. Vymazanie nepotrebných stĺpcov (Krok 1)

```python
df.drop(columns=["Cookie", "user", "Bytes"], inplace=True)
```

**Prečo práve tieto tri:**

- `Cookie` (stĺpec 2 v logu, RFC 1413 identita) — na modernom internete sa nepoužíva, hodnota je vždy `-`. Nenesie žiadnu informáciu.
- `user` (stĺpec 3, HTTP Basic Auth používateľ) — web UKF nepoužíva HTTP autentifikáciu, vždy `-`.
- `Bytes` (stĺpec 9, veľkosť odpovede) — pre analýzu navigačného správania bezvýznamné. Analýza sa zaujíma o *kde* používateľ bol, nie o veľkosť odpovede.

**`inplace=True`** — modifikuje DataFrame priamo v pamäti namiesto vytvorenia kópie. Ekvivalent `df = df.drop(...)`, ale efektívnejší.

---

### 3. Filtrovanie podľa StatusCode (Krok 2)

```python
KEEP_STATUS_CODES = [200, 206, 304]
before = len(df)
df = df[df["StatusCode"].isin(KEEP_STATUS_CODES)]
```

**Ktoré kódy zachováme a prečo:**

| Kód | Názov | Dôvod zachovania |
|---|---|---|
| `200` | OK | Štandardná úspešná odpoveď — stránka bola zobrazená |
| `206` | Partial Content | Čiastočný obsah — streaming videa/audia; reálna akcia |
| `304` | Not Modified | Prehliadač použil cache — kliknutie bolo **skutočné**, len server nemusel znova poslať obsah |

**Prečo zachovávame 304? (dôležitá otázka na skúšku)**  
`304 Not Modified` vznikne takto: prehliadač pošle požiadavok so záhlavím `If-Modified-Since: <čas posledného načítania>`. Server porovná a ak sa stránka nezmenila, odpovie `304` — telo odpovede je prázdne, používateľ dostane stránku z cache. Používateľ **naozaj klikol** — iba obsah nebol znova preposlaný. Keby sme `304` vymazali, prišli by sme o reálne kliknutia.

**Čo vyradíme:**

| Skupina | Príklady | Dôvod vymazania |
|---|---|---|
| `1xx` | `100 Continue` | Informatívne odpovede, nie dokončené požiadavky |
| `4xx` | `404 Not Found`, `403 Forbidden` | Stránka neexistuje alebo zakázaná — žiadny obsah nebol zobrazený |
| `5xx` | `500 Internal Server Error` | Chyba servera — používateľ nevidel obsah |

---

### 4. Filtrovanie podľa RequestMethod (Krok 3)

```python
KEEP_METHODS = ["GET"]
df = df[df["RequestMethod"].isin(KEEP_METHODS)]
```

**Porovnanie HTTP metód:**

| Metóda | Popis | Zachováme? | Dôvod |
|---|---|---|---|
| `GET` | Požiadavok na načítanie stránky/zdroja | **ÁNO** | Navigačné kliknutia |
| `POST` | Odoslanie dát formulára na server | **NIE** | Nie je navigácia — prihlásenie, odoslanie komentára |
| `HEAD` | Kontrolný požiadavok — len záhlavie, bez tela | **NIE** | Automatické kontroly dostupnosti, nie kliknutia |

---

### 5. Vymazanie statických súborov (Krok 4)

Každá webová stránka pri načítaní vyvolá desiatky sekundárnych požiadavkov na obrázky, CSS, JavaScript — tieto záznamy zaplaví log, ale **nepredstavujú navigačné kliknutie**. Načítavajú sa automaticky.

```python
STATIC_FILE_PATTERN = (
    r'\.(?:bmp|jpe?g|png|gif|css|flv|ico|swf|rss|xml|cur|js|json|svg'
    r'|woff2?|eot|ttf|otf)(?:\?.*)?$'
)
mask_static = df["URL"].str.contains(STATIC_FILE_PATTERN, case=False, regex=True, na=False)
df = df[~mask_static]
```

**Rozbor regex vzoru:**

| Časť vzoru | Čo zachytí | Príklad |
|---|---|---|
| `jpe?g` | `jpg` aj `jpeg` (znak `?` = predchádzajúci znak nepovinný) | `/foto.jpg`, `/scan.jpeg` |
| `woff2?` | `woff` aj `woff2` (fonty) | `/font.woff`, `/font.woff2` |
| `(?:\?.*)?$` | Voliteľný query string za príponou | `/style.css?ver=5.9.3` |
| `(?:...)` | Nekaptúrujúca skupina | Zabraňuje `UserWarning` v pandas |

**Prečo `(?:...)` namiesto `(...)`?**  
Pandas `str.contains()` pri kaptúrujúcich skupinách `(...)` vypíše `UserWarning: This pattern has match groups`. Nekaptúrujúca skupina `(?:...)` sa správa rovnako pre matching, ale nepamätá si zachytený text — pandas preto nevypíše varovanie.

**Prečo `case=False`?**  
URL `/foto.JPG` a `/foto.jpg` sú oba statické súbory. Bez `case=False` by `.JPG` prešlo cez filter a zostalo v dátach.

**Prečo `na=False`?**  
Ak je v stĺpci URL hodnota `NaN` (chýbajúca), `str.contains()` by vrátil `NaN` namiesto `True`/`False`. `na=False` hovorí: "pre chýbajúce URL vráť `False`" — teda nezachyť ich ako statické súbory.

---

### 6. Vymazanie interného monitoringu (Krok 5 – Čistenie II)

```python
NAVBAR_URL = "/navbar/navbar-ukf.html"
mask_navbar = df["URL"].str.contains(NAVBAR_URL, regex=False, na=False)
df = df[~mask_navbar]
```

Po analýze dát sa ukázalo, že URL `/navbar/navbar-ukf.html` sa v logu opakuje tisíckrát. Ide o **interný monitoring šablóny webu UKF** — automatický požiadavok serverovej infraštruktúry, ktorý overuje dostupnosť navigačnej lišty. Nie je to kliknutie žiadneho návštevníka.

**Prečo `regex=False`?**  
Pre pevný textový reťazec je `regex=False` výrazne rýchlejšie — pandas vykoná priame porovnanie reťazcov namiesto spúšťania regexového enginu.

---

### 7. Kontrolná štatistika (Krok 6 – Čistenie II)

```python
print(df["RequestMethod"].value_counts().to_string())
print(df["StatusCode"].value_counts().to_string())
print(df["RequestVersion"].value_counts().to_string())
```

`value_counts()` spočíta výskyt každej unikátnej hodnoty v stĺpci a zoradí ich zostupne. Slúži ako **overenie konzistencie** — po čistení by mal zostať len `GET`, `200/206/304`, `HTTP/1.1`.

---

## Celkový code flow

```
main()
    │
    ├─► parse_log_to_dataframe("wm2020projekt_oravec.log")
    │       otvorí súbor s encoding="utf-8", errors="replace"
    │       pre každý riadok:
    │           LOG_LINE_REGEX.match(line.strip())
    │           ak zhoda: records.append({ IP, Cookie, user, DateTime,
    │                     RequestMethod, URL, RequestVersion, StatusCode,
    │                     Bytes, Referrer, Agent })
    │       pd.DataFrame(records)  →  df  (11 stĺpcov)
    │
    ├─► clean_data(df)
    │       Krok 1: df.drop(["Cookie","user","Bytes"])       →  8 stĺpcov
    │       Krok 2: isin([200,206,304])                      →  iba úspešné požiadavky
    │       Krok 3: isin(["GET"])                            →  iba navigačné metódy
    │       Krok 4: ~mask_static  (regex na prípony)         →  iba HTML stránky
    │       Krok 5: ~mask_navbar  (pevný reťazec)            →  bez interného monitoringu
    │       Krok 6: value_counts()  kontrolná štatistika
    │
    └─► df.to_csv("wm2020projekt_cleaned.csv", index=False, encoding="utf-8")
```

---

## Prehľad najdôležitejších funkcií

| Funkcia | Čo robí a prečo |
|---|---|
| `re.compile(pattern)` | Skompiluje regex **raz** — opakované `.match()` v cykle je oveľa rýchlejšie |
| `regex.match(line)` | Zhoda od **začiatku** reťazca; vráti objekt alebo `None` |
| `m.group(n)` | Obsah n-tej zachytenej skupiny `(...)` v regexe; `m.group(8)` = StatusCode |
| `int(m.group(8))` | Prevedie reťazec `"200"` na číslo `200` — nutné pre `isin([200, 206, 304])` |
| `pd.DataFrame(records)` | Vytvorí tabuľku zo zoznamu slovníkov — každý slovník = 1 riadok |
| `df.drop(columns=[...], inplace=True)` | Vymaže stĺpce; `inplace=True` = mení df priamo bez kópie |
| `df["col"].isin([...])` | Bool stĺpec: `True` kde hodnota je v zozname — ekvivalent `==` pre viacero hodnôt |
| `df["col"].str.contains(pat, case=False, regex=True, na=False)` | Bool stĺpec: regex matching; `case=False` = veľké/malé písmená |
| `~mask` | Negácia bool stĺpca — **zachová** riadky kde mask = `False` |
| `df.reset_index(drop=True)` | Znovu čísluje riadky od 0 po filtrovaní — nutné pre správny `shift()` v Task 3 |
| `value_counts()` | Spočíta unikátne hodnoty; zoradí zostupne |
| `df.to_csv(file, index=False)` | Uloží DataFrame do CSV bez automatického číselného indexu |

---

## Kľúčové otázky na obhajobu

**Prečo je potrebné `reset_index(drop=True)` po každom filtrovaní?**  
Po `df[mask]` zostanú pôvodné indexy — napr. po vymazaní riadkov 0–99 začína zostatok od indexu 100. V Task 3 používame `groupby().shift()`, v Task 5 `iloc[]` — obe predpokladajú súvislé číslovanie od 0. Ak by indexy "skákali", výsledky by boli nesprávne.

**Prečo `errors="replace"` pri otváraní logu?**  
Apache log môže obsahovať neplatné UTF-8 bajty (napríklad v User-Agent reťazcoch starých prehliadačov alebo robotov). Bez `errors="replace"` by Python vyhodil `UnicodeDecodeError` a skript by spadol. `"replace"` nahradí neplatné bajty znakom `?` a pokračuje.

**Čo je rozdiel medzi `bool` indexovaním `df[mask]` a `df.loc[mask]`?**  
`df[mask]` a `df.loc[mask]` v prípade boolean masky robia to isté — oba vyberú riadky kde je maska `True`. `df.loc` je explicitnejší a preferovaný v komplexnejších prípadoch, `df[mask]` je kratší a idiomatický pre čisté boolean indexovanie.

**Čo je Apache Combined Log Format a aké polia obsahuje?**  
Rozšírenie Common Log Format o dva ďalšie polia. Každý riadok obsahuje: IP adresa – identita klienta (zvyčajne `-`) – meno používateľa (zvyčajne `-`) – čas požiadavku – HTTP požiadavok (metóda + URL + protokol) – stavový kód – veľkosť odpovede – Referrer – User-Agent. Pole v úvodzovkách môže obsahovať medzery — preto regex s skupinami, nie delenie podľa medzier.

**Čo je regex skupina `(?P<name>...)` a na čo sa používa?**  
`(?P<name>...)` je **pomenovaná zachytávajúca skupina** v regexe. Čokoľvek, čo zodpovedá vzoru `...`, sa uloží pod menom `name`. Príklad: `(?P<IP>\d+\.\d+\.\d+\.\d+)` zachytí IP adresu pod kľúčom `"IP"`. Pristúpime k nej cez `m.group("IP")`. Výhoda oproti číselným skupinám `(...)` = kód je čitateľnejší a nezávisí od poradia skupín.

**Prečo `re.compile()` namiesto priameho `re.match(pattern, line)` v každej iterácii?**  
`re.compile(pattern)` skompiluje regex vzor **raz** do vnútornej reprezentácie (konečného automatu). Ak by sme volali `re.match(pattern, line)` v cykle, Python by kompiloval vzor znova pri každom riadku — pre log so 100 000 riadkami to je 100 000 zbytočných kompilácií. `re.compile()` = inicializácia raz, volanie `compiled.match(line)` v cykle = výrazne rýchlejšie.

**Aké HTTP stavové kódy sú v projekte povolené a čo každý znamená?**

| Kód | Názov | Popis |
|---|---|---|
| 200 | OK | Požiadavok úspešný, obsah vrátený |
| 206 | Partial Content | Čiastočný obsah (napr. veľký súbor, stiahnutie po častiach) |
| 304 | Not Modified | Obsah nezmenený, prehliadač použije vlastnú cache |

Kód 304 je dôležitý — znamená, že používateľ stránku **navštívil** (prehliadač spýtal server), len obsah prišiel z cache. Keby sme 304 vylúčili, stratili by sme legitímne navigačné záznamy.

**Prečo vymazávame statické súbory (css, js, png, ...)?**  
Každá HTML stránka automaticky stiahne desiatky statických súborov — obrázky, štýly, skripty. Tieto sú načítané prehliadačom **automaticky bez kliknutia používateľa**. Napríklad pri návšteve `/o-nas` sa automaticky stiahne `/static/style.css`, `/img/logo.png` atď. Keby sme ich nezmazali, každý klik by sa javil ako 20+ požiadavkov — analýza by bola úplne skreslená.

**Čo je `(?:...)` a prečo sa líši od `(...)`?**  
`(?:...)` je **nezachytávajúca skupina** — zoskupuje časti vzoru pre operátory `|` alebo `+`, ale výsledok **nezachytáva** do skupiny. Napr. `(?:css|js|png)` zhoduje s ktorýmkoľvek z troch slov, ale nevráti ich ako extra skupinu. Používame ho v `STATIC_FILE_PATTERN` pre efektívnosť — nepotrebujeme zachytávať prípony, len detekovať zhodu.

**Čo by sa stalo, keby sme nezmazali `/navbar/navbar-ukf.html`?**  
Táto URL je súčasť navigačného panelu — načítava sa automaticky pri každej stránke ako súčasť layoutu. Keby sme ju nezmazali, každý návštevník by mal v logu desiatky záznamov pre `/navbar/navbar-ukf.html` namiesto skutočných navigačných kliknutí. To by skreslilo frekvencie URL, sedenia aj analýzu správania.

**Prečo filtrujeme metódu GET a nie POST?**  
GET požiadavky sú **navigačné** — načítanie stránky kliknutím. POST požiadavky sú **akčné** — odoslanie formulára (prihlásenie, komentár). Analýza navigačného správania zaujíma len to, kde používateľ chodil, nie čo odosielal. POST záznamy by navyše neobsahovali URL stránky ale URL handlera formulára.

**Ako by si overil, že čistenie prebehlo správne?**  
Použijeme `df["URL"].value_counts()` — zobrazí top 20 najčastejších URL. Keby tam boli statické súbory (`.css`, `.js`), čistenie zlyhalo. Keby tam bola `/robots.txt`, Task 2 ešte nebehol. `df.shape` ukáže počet riadkov pred a po — môžeme skontrolovať, že sme neodstránili príliš veľa/málo.
