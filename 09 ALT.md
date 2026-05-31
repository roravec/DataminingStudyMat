# Vysvetlenie skriptu `analyze_logs5.py` – pre obhajobu

---

## 1. Čo tento skript vôbec robí? (1 veta)

Skript načíta veľký CSV súbor s logmi webstránky (`logs5.csv`), spočíta rôzne štatistiky (navštevnosť, kategórie, čas na stránke) a uloží výsledky ako **graf** (`overview.png`) a **textový súbor** (`statistics.txt`).

---

## 2. Ako ho spustiť?

```powershell
python analyze_logs5.py --input logs5.csv --outdir analysis_output
```

- `--input` → ktorý CSV súbor čítať (default: `logs5.csv`)
- `--outdir` → kam uložiť výsledky (default: `analysis_output`)
- `--chunksize` → koľko riadkov spracovať naraz (default: 5 000 000)

---

## 3. Prečo "chunky" (časti)?

CSV súbor môže mať **milióny riadkov** a celý by sa nezmestil do pamäte.  
Preto sa číta **po kuskoch (chunks)** – napr. 5 miliónov riadkov naraz.  
Každý kus sa spracuje a výsledky sa postupne **sčítavajú** do počítadiel.

```
Súbor:  [chunk 1] → spracuj → pridaj do počítadiel
        [chunk 2] → spracuj → pridaj do počítadiel
        [chunk 3] → spracuj → pridaj do počítadiel
                    ↓
              Výsledky (súčty)
```

---

## 4. Aké stĺpce z CSV sa používajú? (`USECOLS`)

Skript nenačítava všetky stĺpce, len tie potrebné:

| Stĺpec | Čo znamená |
|---|---|
| `anonIP` | Anonymizovaná IP adresa návštevníka |
| `agent` | Identifikátor agenta (prehliadač/bot) |
| `ipPart` | Časť IP adresy |
| `userAgent` | Reťazec User-Agent prehliadača |
| `unixTime` | Čas návštevy ako číslo (sekundy od 1.1.1970) |
| `yearQuartal` | Rok a kvartál (napr. "2020Q1") |
| `week` | Číslo týždňa |
| `webPart` | Časť webu |
| `category` | Kategória obsahu stránky |
| `urlExt` | Prípona URL (napr. `.html`, `.pdf`) |
| `length` | Čas strávený na stránke (v sekundách) |
| `internal` | Či je návštevník interný (0/1) |
| `crisis` | Či ide o krízové obdobie (0/1) |

---

## 5. Konfigurácia analýz – čo sa počíta

### `COUNT_ANALYSES` – základné počty
Toto je zoznam vecí, kde sa len **počíta výskyt** hodnôt:

```python
COUNT_ANALYSES = [
    {"table_key": "weekly_df",   "kind": "weekly",  "column": "week_start"},   # počty návštev po týždňoch
    {"table_key": "quarter_df",  "kind": "column",  "column": "yearQuartal"},  # počty po kvartáloch
    {"table_key": "category_df", "kind": "column",  "column": "category"},     # počty podľa kategórie
    {"table_key": "webpart_df",  "kind": "column",  "column": "webPart"},      # počty podľa časti webu
    {"table_key": "ext_df",      "kind": "column",  "column": "urlExt"},       # počty podľa prípony
    {"table_key": "internal_df", "kind": "column",  "column": "internal"},     # interní vs externí
    {"table_key": "crisis_df",   "kind": "column",  "column": "crisis"},       # krízové vs normálne
]
```

### `CUSTOM_ANALYSES` – vlastné analýzy
Pokročilejšie analýzy s filtrom alebo priemerom:

| Názov | Čo robí |
|---|---|
| `avg_length_by_category` | Priemerný čas na stránke podľa kategórie |
| `categories_during_crisis` | Najpopulárnejšie kategórie **počas krízy** |
| `avg_length_during_crisis` | Priemerný čas na stránke **počas krízy** |
| `avg_length_normal` | Priemerný čas na stránke **mimo krízy** |

---

## 6. Funkcie – čo každá robí (od začiatku po koniec)

### `main()` – štartovacia funkcia
```
Spustí celý program v tomto poradí:
  1. Spracuj argumenty (--input, --outdir)
  2. Zavolaj process_csv() → načítaj dáta
  3. Zavolaj build_tables() → urob tabuľky
  4. Zavolaj compute_statistics() → urob štatistiky
  5. Zavolaj save_statistics() → ulož do súboru
  6. Zavolaj make_overview_plot() → nakresli grafy
```

---

### `process_csv(input_path, chunksize)` – načítanie CSV

**Vstup:** cesta k súboru, veľkosť chunku  
**Výstup:** slovník so všetkými zozbieranými dátami

Číta súbor po kusoch. Pre každý kus zavolá pomocné funkcie:

```
chunk (pandas DataFrame)
   │
   ├── normalize_text_columns()     → uprace text (UNKNOWN miesto prázdnych)
   ├── _process_unique_values()     → zbiera unikátne IP, agenty
   ├── _process_count_analyses()    → počíta kategórie, webPart, atď.
   ├── _process_weekly_visits()     → počíta návštevy po týždňoch
   ├── _process_chi2_counts()       → počíta kombinácie (crisis, category)
   ├── _process_length_sample()     → zbiera vzorky dĺžky návštevy
   └── _process_custom_analysis()  → spracuje každú custom analýzu
```

---

### `normalize_text_columns()` a `normalize_text_series()` – čistenie textu

**Problém:** V CSV môžu byť prázdne bunky, `None`, alebo pomlčky `"-"`.  
**Riešenie:** Všetky sa nahradia reťazcom `"UNKNOWN"`.

```
""   → "UNKNOWN"
"-"  → "UNKNOWN"
None → "UNKNOWN"
```

Prečo? Aby sa tá istá vec nepočítala ako viac rôznych hodnôt.

---

### `_process_weekly_visits()` – návštevy po týždňoch

1. Stĺpec `unixTime` (číslo sekúnd) → prevedie na dátum
2. Dátum → zaokrúhli na **začiatok týždňa**
3. Spočíta, koľko návštev bolo v každom týždni

```
1609459200  →  datetime(2021-01-01)  →  week: "2020-12-28"  →  +1 do počítadla
```

---

### `_process_chi2_counts()` – počítanie pre chi-kvadrát test

Počíta, koľkokrát sa vyskytla každá kombinácia `(crisis, category)`.

```
("0", "sport")  →  150 krát
("1", "sport")  →  80 krát
("0", "news")   →  200 krát
("1", "news")   →  310 krát
```

Tieto čísla sa neskôr použijú na zistenie, či **typ obsahu závisí od krízy**.

---

### `_process_length_sample()` – vzorky dĺžky návštevy

Zbiera hodnoty stĺpca `length` pre každú kategóriu (max 5000 hodnôt na kategóriu).  
Tieto hodnoty sa použijú na **Kruskal-Wallis test** (či sa dĺžka líši medzi kategóriami).

---

### `build_tables()` – zostavenie tabuľiek

Z počítadiel (Counter) urobia pandas **DataFrame** tabuľky.  
Každá tabuľka = jeden graf.

```
Counter({"sport": 150, "news": 200})
        ↓
DataFrame:
  category  |  visits
  news      |  200
  sport     |  150
```

---

### `compute_statistics()` – štatistické testy

Počíta **3 testy**. Tu je vysvetlenie každého:

---

#### Test 1: Spearmanova korelácia

**Otázka:** Rastie alebo klesá návštevnosť v čase?

- **Nezávislá premenná (IV):** poradie týždňa (0, 1, 2, 3, ...)
- **Závislá premenná (DV):** počet návštev v danom týždni

**Výsledok `r`:**
- `r = +1.0` → perfektný rast
- `r = -1.0` → perfektný pokles
- `r ≈ 0.0` → žiadny trend

**Výsledok `p`:**
- `p < 0.05` → trend je štatisticky **významný** (nie je náhoda)
- `p ≥ 0.05` → trend **nebol potvrdený**

> **Prečo Spearman a nie Pearson?**  
> Spearman pracuje s **poradím** hodnôt, nie priamo s číslami. Je odolnejší voči extrémnym hodnotám (outliery) a nevyžaduje normálne rozdelenie dát.

---

#### Test 2: Chi-kvadrát test + Cramérovo V

**Otázka:** Závisí typ obsahu (category) od toho, či ide o krízu alebo nie?

Zostaví sa **kontingentná tabuľka** (kríza × kategória):

```
            sport   news   tech   ...
crisis=0     150    200    300
crisis=1      80    310    120
```

- **Chi-kvadrát (`χ²`):** meria, či sú rozdiely medzi riadkami väčšie, ako by bola náhoda
- **p-hodnota:** `p < 0.05` = závislosť existuje
- **Cramérovo V:** sila závisnosti (0 = žiadna, 1 = úplná)
  - `V < 0.1` → zanedbateľná
  - `V ≥ 0.1` → malá
  - `V ≥ 0.3` → stredná
  - `V ≥ 0.5` → silná

---

#### Test 3: Kruskal-Wallis test

**Otázka:** Líši sa čas strávený na stránke (`length`) medzi kategóriami obsahu?

- Porovnáva **viac skupín** naraz (sport, news, tech, ...)
- Neparametrický test – nevyžaduje normálne rozdelenie
- Podobá sa ANOVA, ale pre neparametrické dáta

**Výsledok:**
- `H` → testová štatistika
- `p < 0.05` → rozdiely medzi kategóriami sú štatisticky **významné**

---

### `save_statistics()` – uloženie výsledkov

Zapíše výsledky všetkých 3 testov do `analysis_output/statistics.txt` a vytlačí ich do terminálu.

---

### `make_overview_plot()` – kreslenie grafov

Nakreslí **jeden veľký obrázok** (`overview.png`) so všetkými panelmi pod sebou:

| Panel | Obsah |
|---|---|
| 1 | Návštevnosť webu po týždňoch (čiarový graf) |
| 2 | Top 10 kategórií podľa počtu návštev (barh) |
| 3 | Priemerná dĺžka návštevy podľa kategórie |
| 4 | Najpopulárnejšie kategórie počas krízy |
| 5 | Priemerný čas na stránke – počas krízy |
| 6 | Priemerný čas na stránke – mimo krízy |
| 7 | Textový prehľad štatistických testov |

---

### `counter_to_dataframe()` – pomocná funkcia

Prevádza `Counter` (slovník `kľúč → počet`) na pandas `DataFrame`.

```python
Counter({"sport": 150, "news": 200})
# ↓
#   category  visits
# 0     news     200
# 1    sport     150
```

---

### `ensure_outdir()` – vytvorenie priečinka

Ak výstupný priečinok (`analysis_output`) neexistuje, vytvorí ho.  
Ak existuje, nič sa nestane.

---

## 7. Celkový tok dát (od súboru po výsledok)

```
logs5.csv
    │
    ▼
process_csv()          ← čítanie po chunkoch
    │
    ├── normalize_text_columns()
    ├── _process_unique_values()
    ├── _process_count_analyses()
    ├── _process_weekly_visits()
    ├── _process_chi2_counts()
    ├── _process_length_sample()
    └── _process_custom_analysis()
    │
    ▼
results (slovník s počítadlami)
    │
    ▼
build_tables()         ← Counter → DataFrame
    │
    ▼
tables (slovník DataFramov)
    │
    ├──▶ compute_statistics()  →  save_statistics()  →  statistics.txt
    │
    └──▶ make_overview_plot()  →  overview.png
```

---

## 8. Čo odpovedať na skúške

### "Prečo čítaš po chunkoch?"
> Súbor môže mať desiatky miliónov riadkov. Keby sme ho načítali celý, mohol by zabrať niekoľko GB pamäte a program by spadol. Chunkovanie riešime tak, že spracovávame časť, aktualizujeme počítadlá a pamäť uvoľníme.

### "Čo je Counter?"
> Counter je špeciálny slovník z modulu `collections`. Automaticky počíta výskyty – `counter["sport"] += 1` sa dá skrátiť na `counter.update(["sport"])`.

### "Čo je DataFrame?"
> DataFrame je tabuľka z knižnice `pandas` – má stĺpce a riadky, podobne ako Excel. Dá sa filtrovať, triediť, agregovať.

### "Prečo Spearman a nie Pearson?"
> Spearman počíta koreláciu na **poradí** hodnôt, nie na samotných číslach. Je odolnejší voči outlieram a nevyžaduje normálne rozdelenie – čo pre webové logy platí.

### "Čo meria Cramérovo V?"
> Meria **silu závisnosti** po chi-kvadrát teste. Chi-kvadrát len hovorí áno/nie, ale Cramérovo V hovorí aj ako veľmi – od 0 (žiadna závislosť) po 1 (úplná závislosť).

### "Prečo Kruskal-Wallis a nie ANOVA?"
> ANOVA vyžaduje normálne rozdelenie a rovnaké rozptyly. Webové logy majú dlhý chvost (veľa krátkych návštev, málo veľmi dlhých), takže Kruskal-Wallis je vhodnejší.

### "Čo robí normalize_text_series?"
> Zjednotí prázdne hodnoty (`""`, `"-"`, `None`) na jeden reťazec `"UNKNOWN"`. Bez toho by sa prázdna bunka a pomlčka počítali ako dve rôzne hodnoty.

---

## 9. Výstupné súbory

| Súbor | Obsah |
|---|---|
| `analysis_output/overview.png` | Všetky grafy v jednom obrázku |
| `analysis_output/statistics.txt` | Výsledky 3 štatistických testov s interpretáciou |
