# Analýza webových logov banky – analyze.py

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Komerčná banka zaznamenáva každý prístup používateľov na svoju webstránku do logovacieho súboru. Každý záznam (riadok) v `logs5.csv` zodpovedá jednému prístupu a obsahuje informácie o tom:
- **KTO** pristúpil (`anonIP` – anonymizovaná IP adresa)
- **KEDY** pristúpil (`unixTime`, `year`, `quartal`, `week`, ...)
- **NA ČO** pristúpil (`category`, `webPart`, `urlExt` – odvodené z URL)
- **AKO DLHO** – (`length` – dĺžka obsahu/čas strávený)
- **ODKIAĽ** – (`internal` – či šlo o interný prístup)
- **V AKEJ SITUÁCII** – (`crisis` – krízové vs. normálne obdobie)

Skript tieto dáta načíta, vypočíta štatistiky a uloží výsledky (textový report + grafy).

---

### Otázka, ktorú skript zodpovedá

> Existuje štatisticky významná závislosť medzi **časom prístupu (IV)** a **navštíveným obsahom (DV)**?

Konkrétne sa testujú tri rôzne vzťahy pomocou troch rôznych štatistických metód.

---

### Vstup

Jeden CSV súbor `logs5.csv` so stredníkovým oddeľovačom (`;`).

Skript číta len 12 stĺpcov z celého súboru (ostatné ignoruje – efektívnosť):

| Stĺpec | Typ | Skupina | Popis |
|---|---|---|---|
| `anonIP` | text | – | Anonymizovaná IP adresa používateľa |
| `unixTime` | číslo | IV | Unix timestamp prístupu (sekundy od 1.1.1970) |
| `year` | číslo | IV | Rok prístupu |
| `quartal` | číslo | IV | Štvrťrok (1–4) |
| `yearQuartal` | text | IV | Rok+štvrťrok (napr. "2021Q1") |
| `week` | číslo | IV | Číslo týždňa v roku (1–53) |
| `category` | text | **DV** | Kategória navštíveného obsahu (z URL) |
| `webPart` | text | **DV** | Časť webu (z URL) |
| `urlExt` | text | **DV** | Prípona URL (z URL) |
| `length` | číslo | – | Dĺžka obsahu / čas strávený |
| `internal` | text | – | Interný vs. externý prístup |
| `crisis` | text | IV | Krízové vs. normálne obdobie |

---

### Výstup

```
logs5.csv  ──►  analyze.py  ──►  analysis_output_simple/
                                     ├── report.txt
                                     ├── visits_by_yearquartal.png
                                     ├── heatmap_day_hour.png
                                     ├── heatmap_week_year.png
                                     └── top_category.png
```

| Súbor | Obsah |
|---|---|
| `report.txt` | Textový report: profil dát, top hodnoty DV, výsledky 3 štat. testov |
| `visits_by_yearquartal.png` | Čiarový graf návštevnosti po štvrťrokoch (IV → DV trend) |
| `heatmap_day_hour.png` | Heatmapa: aktivita podľa dňa v týždni × hodiny dňa |
| `heatmap_week_year.png` | Heatmapa: aktivita podľa týždňa × roka |
| `top_category.png` | Horizontálny stĺpcový graf top kategórií obsahu |

---

## Postup riešenia – krok za krokom

### 1. Importy a konštanty

```python
import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
    PLOT_AVAILABLE = True
except Exception:
    PLOT_AVAILABLE = False

try:
    from scipy import stats as scipy_stats
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False
```

| Knižnica / modul | Účel |
|---|---|
| `argparse` | Spracovanie argumentov príkazového riadku (`--input`, `--outdir`) |
| `logging` | Výpis informačných správ počas behu (`INFO: Nacitavam data...`) |
| `pathlib.Path` | Objektovo-orientovaná práca so súborovými cestami |
| `numpy` | Matematické operácie s poľami čísel (rank, corrcoef, arange) |
| `pandas` | Načítanie CSV, práca s DataFrame (tabuľkami) |
| `matplotlib` | Kreslenie grafov |
| `scipy.stats` | Štatistické testy (Spearman, Chi-square, Kruskal-Wallis) |

Dôležité: `matplotlib` a `scipy` sú obalené v `try/except` – skript nevyhodí chybu, ak nie sú nainštalované. Grafy a niektoré štatistiky budú preskočené, ale zvyšok pobeží.

---

### 2. CLI argumenty – `build_arg_parser()`

```python
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Jednoducha analyza logs5.csv")
    parser.add_argument("--input",  default=Path("logs5.csv"),              type=Path)
    parser.add_argument("--outdir", default=Path("analysis_output_simple"), type=Path)
    return parser
```

Spustenie skriptu z terminálu:
```
python analyze.py --input logs5.csv --outdir analysis_output_simple
```

- `argparse` parsuje argumenty z príkazového riadku
- `default=...` – ak argument chýba, použije sa predvolená hodnota
- `type=Path` – automaticky konvertuje textový reťazec na objekt `Path`

---

### 3. Načítanie dát – `load_data()`

Toto je **najdôležitejšia funkcia** – transformuje surové CSV na čistý DataFrame.

```python
df = pd.read_csv(
    input_path,
    sep=";",
    quotechar='"',
    usecols=USECOLS,
    low_memory=False,
)
```

- `sep=";"` – oddeľovač stĺpcov je bodkočiarka (nie čiarka)
- `quotechar='"'` – textové hodnoty môžu byť ohraničené úvodzovkami
- `usecols=USECOLS` – načíta iba 12 potrebných stĺpcov (rýchlejšie, menej pamäte)
- `low_memory=False` – zabraňuje varovaniu o zmiešaných dátových typoch

#### Normalizácia textu

```python
for col in ["anonIP", "category", "webPart", "urlExt", "yearQuartal", "internal", "crisis"]:
    df[col] = normalize_text(df[col])
```

```python
def normalize_text(series: pd.Series, default: str = "UNKNOWN") -> pd.Series:
    return series.astype("string").fillna(default).replace({"": default, "-": default})
```

- `.astype("string")` – zabezpečí, že stĺpec je textový (nie `object`)
- `.fillna(default)` – prázdne (`NaN`) hodnoty nahrádza reťazcom `"UNKNOWN"`
- `.replace({"": default, "-": default})` – prázdny reťazec `""` a pomlčka `"-"` sa tiež nahradia

**Prečo?** Bez normalizácie by sa `""`, `"-"` a `NaN` počítali ako tri rôzne hodnoty, hoci všetky znamenajú "chýbajúca hodnota".

#### Konverzia čísel

```python
for col in ["year", "quartal", "week", "length", "unixTime"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
```

- `pd.to_numeric(..., errors="coerce")` – neplatné hodnoty (napr. text v číselnom stĺpci) sa prevedú na `NaN` namiesto vyhodenia chyby

#### Odvodenie hodiny a dňa v týždni

```python
ts = pd.to_datetime(df["unixTime"], unit="s", errors="coerce", utc=True)
df["hour"]      = ts.dt.hour
df["dayofweek"] = ts.dt.dayofweek   # 0=pondelok ... 6=nedeľa
```

- `pd.to_datetime(..., unit="s")` – prevod Unix timestamp (sekundy) na datetime objekt
- `utc=True` – interpretujeme čas ako UTC (dôležité pre konzistentnosť)
- `ts.dt.hour` – hodina dňa (0–23)
- `ts.dt.dayofweek` – deň v týždni (0=pondelok, 6=nedeľa)

Tieto dve nové premenné (`hour`, `dayofweek`) sú **odvodené IV** – nevyskytujú sa priamo v CSV, ale vytvárame ich z existujúceho stĺpca `unixTime`.

---

### 4. Výpočet štatistík – `compute_statistics()`

Funkcia vypočíta tri štatistické testy a vráti ich výsledky ako slovník `stats`.

---

#### 4a. Spearman – trend návštevnosti v čase

**Otázka:** Je tu monotónny trend v návštevnosti počas týždňov v roku?

```python
weekly = (
    df.dropna(subset=["year", "week"])
    .groupby(["year", "week"])
    .size()
    .reset_index(name="visits")
    .sort_values(["year", "week"])
)
```

- `.dropna(subset=["year", "week"])` – vyhodíme záznamy bez roku alebo týždňa
- `.groupby(["year", "week"]).size()` – spočíta, koľko prístupov bolo v každom týždni každého roka
- `.reset_index(name="visits")` – prevedie výsledok na DataFrame so stĺpcom `visits`
- `.sort_values(...)` – zoradí chronologicky

```python
for year, grp in weekly.groupby("year"):
    x = np.arange(len(grp), dtype=float)   # poradie: 0, 1, 2, ...
    y = grp["visits"].to_numpy(dtype=float) # počet návštev
    sp = scipy_stats.spearmanr(x, y)
```

- Spearmanova korelácia sa počíta **pre každý rok zvlášť**, aby sa nestratil smer trendu (jeden rok môže rásť, iný klesať)
- `x = np.arange(len(grp))` – poradové čísla týždňov (nie skutočné čísla týždňov, ale poradie)
- `sp.statistic` = $\rho$ (rho) – sila a smer monotónneho vzťahu (−1 až +1)
- `sp.pvalue` = p-hodnota pre test H0

**Fallback bez scipy:**
```python
rx = pd.Series(x).rank(method="average").to_numpy(dtype=float)
ry = pd.Series(y).rank(method="average").to_numpy(dtype=float)
rho = float(np.corrcoef(rx, ry)[0, 1])
```
Manuálny výpočet Spearmanovej korelácie: prevedieme hodnoty na **poradie (ranky)** a vypočítame Pearsonovu koreláciu z tých radov.

---

#### 4b. Chi-square + Cramér V – crisis vs. category

**Otázka:** Závisí navštívená kategória obsahu od toho, či je krízové obdobie?

```python
chi_df = df[["crisis", "category"]].dropna()
cont   = pd.crosstab(chi_df["crisis"], chi_df["category"])
```

- `pd.crosstab(...)` – kontingečná tabuľka: riadky = hodnoty `crisis`, stĺpce = hodnoty `category`, bunky = počty

```python
chi2_stat, chi2_p, chi2_dof, _ = scipy_stats.chi2_contingency(cont.to_numpy(dtype=float))
```

- `chi2_stat` = $\chi^2$ – testová štatistika
- `chi2_p` = p-hodnota
- `chi2_dof` = stupne voľnosti

```python
n_total  = float(cont.to_numpy(dtype=float).sum())
min_dim  = min(cont.shape[0], cont.shape[1]) - 1
cramer_v = float(np.sqrt(chi2_stat / (n_total * min_dim)))
```

Cramér V sa vypočíta z $\chi^2$ a udáva silu závislosti na škále $\langle 0, 1\rangle$.

---

#### 4c. Kruskal-Wallis – length podľa category

**Otázka:** Líši sa dĺžka obsahu (`length`) medzi rôznymi kategóriami webu?

```python
kr_df  = df[["category", "length"]].dropna()
groups = []
for cat, grp in kr_df.groupby("category"):
    vals = grp["length"].to_numpy(dtype=float)
    if len(vals) >= 5:
        groups.append(vals)

h_stat, p_val = scipy_stats.kruskal(*groups)
```

- Každá kategória tvorí samostatnú skupinu hodnôt `length`
- `if len(vals) >= 5` – malé skupiny vynecháme (nestabilné odhady)
- `*groups` – rozbalenie zoznamu skupín ako samostatných argumentov
- `h_stat` = H štatistika, `p_val` = p-hodnota

---

### 5. Uloženie reportu – `save_report()`

Funkcia zostaví textový report do zoznamu riadkov a zapíše ho do súboru:

```python
lines = []
lines.append("=" * 70)
lines.append("PRIESKUM DAT O POUZIVANI WEBU KOMERCNEJ BANKY")
# ... pridávanie riadkov ...
report_path = outdir / "report.txt"
report_path.write_text("\n".join(lines), encoding="utf-8")
```

- `outdir / "report.txt"` – operátor `/` na objektoch `Path` zostaví cestu (ekvivalent `os.path.join`)
- `"\n".join(lines)` – spojí zoznam riadkov do jedného reťazca
- `.write_text(..., encoding="utf-8")` – zapíše reťazec do súboru

---

### 6. Grafy – `make_plots()`

Skript generuje 4 grafy. Každý sa uloží ako PNG do výstupného priečinka.

#### Graf 1: Návštevnosť po yearQuartal
```python
q = df["yearQuartal"].value_counts(...).sort_values("yearQuartal")
ax.plot(q["yearQuartal"].astype(str), q["visits"], marker="o")
```
Čiarový graf zobrazuje trend návštevnosti v čase – vizualizuje ten istý vzťah, ktorý Spearman meria číselne.

#### Graf 2: Heatmapa deň × hodina
```python
h = df.groupby(["dayofweek", "hour"]).size().unstack(fill_value=0)
ax.imshow(h.to_numpy(), aspect="auto")
```
- `.unstack(fill_value=0)` – prevedie dvojúrovňový index na maticu (riadky=dni, stĺpce=hodiny)
- `ax.imshow(...)` – vykreslí maticu ako obrázok s farebnými intenzitami

#### Graf 3: Heatmapa týždeň × rok
```python
pivot_wy = wy.groupby(["year", "week"]).size().unstack(fill_value=0)
pivot_wy = pivot_wy.reindex(columns=list(range(1, 54)), fill_value=0)
```
- `.reindex(columns=list(range(1, 54)))` – zarovná os týždňov na rozsah 1–53 (aj ak niektoré týždne chýbajú) – zlepší porovnanie medzi rokmi

#### Graf 4: Top category
```python
top_cat = df["category"].value_counts(dropna=False).head(12)
ax.barh(top_cat.index.astype(str), top_cat.values)
ax.invert_yaxis()
```
- `barh` – horizontálne stĺpce (lepšia čitateľnosť dlhých názvov kategórií)
- `.invert_yaxis()` – najčastejšia kategória bude hore (nie dole)

---

### 7. Hlavná funkcia – `main()`

```python
def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_arg_parser()
    args   = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Vstupny subor neexistuje: {args.input}")

    ensure_outdir(args.outdir)
    df    = load_data(args.input)
    stats = compute_statistics(df)
    save_report(df, stats, args.outdir)
    make_plots(df, args.outdir)
```

Orchestrátor: volá ostatné funkcie v správnom poradí. Kontroluje existenciu vstupu pred načítaním.

---

## Štatistické metódy a vzorce

### 1. Spearmanova korelácia

$$
\rho = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}
$$

kde $d_i$ = rozdiel poradí hodnôt $x_i$ a $y_i$, $n$ = počet dvojíc.

**Alternatívne (ako v kóde):**
$$
\rho = r_{Pearson}(\text{rank}(x),\, \text{rank}(y))
$$

**Čo meria:** Monotónny trend – či s rastúcim $x$ (poradie týždňa) rastie aj $y$ (návštevnosť), bez ohľadu na to, či je vzťah lineárny.

**Rozsah:** $-1$ (klesajúci trend) až $+1$ (rastúci trend). $\rho = 0$ = žiadny monotónny vzťah.

**H0 / H1:**
- $H_0$: Medzi poradím týždňa a návštevnosťou neexistuje monotónna závislosť ($\rho = 0$)
- $H_1$: Monotónna závislosť existuje ($\rho \neq 0$)

**Prečo Spearman a nie Pearson?** Pearson predpokladá normalitu a lineárny vzťah. Návštevnosť môže mať výrazné outliere (sviatky, kampane) a vzťah nemusí byť lineárny – Spearman je robustný voči obom.

---

### 2. Chi-square test nezávislosti

$$
\chi^2 = \sum_{i} \sum_{j} \frac{(O_{ij} - E_{ij})^2}{E_{ij}}
$$

kde $O_{ij}$ = pozorovaná frekvencia, $E_{ij}$ = očakávaná frekvencia (ak sú premenné nezávislé).

**H0 / H1:**
- $H_0$: `crisis` a `category` sú nezávislé (krízové obdobie neovplyvňuje, ktorý obsah sa navštívi)
- $H_1$: `crisis` a `category` sú závislé

**Stupne voľnosti:**
$$
df = (r - 1)(c - 1)
$$
kde $r$ = počet riadkov kontingečnej tabuľky, $c$ = počet stĺpcov.

---

### 3. Cramér V (efektová miera)

$$
V = \sqrt{\frac{\chi^2}{n \cdot \min(r-1,\, c-1)}}
$$

**Čo meria:** Silu závislosti medzi dvoma kategorickými premennými po tom, čo Chi-square potvrdí, že závislosť existuje.

**Rozsah:** $0$ (žiadna závislosť) až $1$ (dokonalá závislosť).

**Orientačné hodnoty:**

| Cramér V | Interpretácia |
|---|---|
| ≈ 0.1 | Slabá závislosť |
| ≈ 0.3 | Stredná závislosť |
| ≈ 0.5+ | Silná závislosť |

**Prečo nestačí $\chi^2$?** $\chi^2$ rastie s veľkosťou vzorky – pri miliónoch záznamov bude skoro vždy štatisticky významné, aj keď je závislosť triviálne slabá. Cramér V normalizuje a dáva skutočnú silu efektu.

---

### 4. Kruskal-Wallis test

$$
H = \frac{12}{n(n+1)} \sum_{i=1}^{k} \frac{R_i^2}{n_i} - 3(n+1)
$$

kde $k$ = počet skupín, $n_i$ = veľkosť $i$-tej skupiny, $R_i$ = súčet poradí v $i$-tej skupine, $n$ = celkový počet hodnôt.

**H0 / H1:**
- $H_0$: Distribúcia `length` je rovnaká vo všetkých kategóriách (mediány sú rovnaké)
- $H_1$: Aspoň jedna kategória sa líši

**Prečo Kruskal-Wallis a nie ANOVA?** ANOVA predpokladá normalitu distribúcií v skupinách. `length` (dĺžka obsahu) typicky nie je normálne rozdelená (má dlhý chvost). Kruskal-Wallis je neparametrický ekvivalent ANOVA – nevyžaduje normalitu.

**Dôležité:** Kruskal-Wallis len povie "niečo sa líši". Ak $p < 0.05$, nevieme KDE je rozdiel (medzi ktorými dvojicami kategórií). Na to by sme potrebovali **post-hoc test** (napr. Dunn test).

---

## Vysvetlenie kľúčových operácií v kóde

### `groupby` + `size()` vs `value_counts()`

```python
# groupby variant – vhodný keď grupuješ podľa VIACERÝCH stĺpcov naraz
df.groupby(["year", "week"]).size().reset_index(name="visits")

# value_counts – skratka pre jeden stĺpec
df["category"].value_counts(dropna=False)
```

### `unstack()` – z dlhého formátu na maticu

```python
h = df.groupby(["dayofweek", "hour"]).size().unstack(fill_value=0)
```

```
Pred unstack:
dayofweek  hour  size
0          8     120
0          9     340
...
1          8     90

Po unstack (fill_value=0):
hour        0    1    2  ...  8    9   ...
dayofweek
0           0    0    0  ...  120  340 ...
1           0    0    0  ...  90   ...
```

`unstack()` prevedie posledný level indexu na stĺpce – ideálne pre heatmapy.

### `reindex` – doplnenie chýbajúcich hodnôt

```python
pivot_wy = pivot_wy.reindex(columns=list(range(1, 54)), fill_value=0)
```

Ak v dátach chýba napr. týždeň 53 pre niektorý rok, `reindex` ho doplní s hodnotou 0. Zabezpečí, že všetky roky majú rovnaký počet stĺpcov (1–53) pre správne zobrazenie heatmapy.

### `dropna(subset=[...])` – selektívne vyhadzovanie NaN

```python
weekly = df.dropna(subset=["year", "week"])
```

Vyhodí iba riadky, kde je `NaN` v stĺpcoch `year` alebo `week`. Ostatné stĺpce (aj s `NaN`) zostanú – nie sú pre tento výpočet relevantné.

### `*groups` – rozbalenie zoznamu ako argumentov

```python
groups = [array1, array2, array3, ...]
scipy_stats.kruskal(*groups)
# ekvivalentné:
scipy_stats.kruskal(array1, array2, array3, ...)
```

`kruskal()` očakáva každú skupinu ako samostatný argument. `*groups` rozbalí zoznam.

### `Path` – práca so cestami

```python
report_path = outdir / "report.txt"   # nie os.path.join(outdir, "report.txt")
report_path.write_text(...)           # nie open(...).write(...)
outdir.mkdir(parents=True, exist_ok=True)  # nie os.makedirs(...)
```

`pathlib.Path` je modernejší a čitateľnejší spôsob práce so súborovými cestami oproti `os.path`.

---

## Code flow – diagram

```
START
  │
  ├─► build_arg_parser() → args (--input, --outdir)
  │
  ├─► Kontrola: vstupný súbor existuje?
  │     └── NIE → FileNotFoundError
  │
  ├─► ensure_outdir() → vytvorí výstupný priečinok
  │
  ├─► load_data(input_path)
  │     ├─ pd.read_csv() → načíta 12 stĺpcov
  │     ├─ normalize_text() → textové stĺpce (NaN → "UNKNOWN")
  │     ├─ pd.to_numeric() → číselné stĺpce (chyby → NaN)
  │     └─ pd.to_datetime() → hour, dayofweek z unixTime
  │
  ├─► compute_statistics(df)
  │     ├─ Spearman: groupby(year,week).size() → rho, p pre každý rok
  │     ├─ Chi-square: pd.crosstab(crisis, category) → chi2, p, dof
  │     ├─ Cramér V: sqrt(chi2 / (n * min_dim))
  │     └─ Kruskal-Wallis: length skupiny podľa category → H, p
  │
  ├─► save_report(df, stats, outdir)
  │     └─ report.txt: profil dát + top DV + výsledky testov
  │
  └─► make_plots(df, outdir)
        ├─ visits_by_yearquartal.png  (čiarový graf)
        ├─ heatmap_day_hour.png       (heatmapa 7×24)
        ├─ heatmap_week_year.png      (heatmapa rok×53)
        └─ top_category.png           (horizontálne stĺpce)
END
```

---

## Premenné v skripte – prehľad

### Závislé premenné – DV (čo sa analyzuje / vysvetľuje)

| Premenná | Popis | Typ hodnôt |
|---|---|---|
| `category` | Kategória navštíveného obsahu (z URL) | Kategoriálna |
| `webPart` | Časť webu (z URL) | Kategoriálna |
| `urlExt` | Prípona URL | Kategoriálna |

### Nezávislé premenné – IV (čo vysvetľuje / predikuje)

| Premenná | Popis | Typ hodnôt |
|---|---|---|
| `year` | Rok prístupu | Numerická |
| `quartal` | Štvrťrok (1–4) | Numerická/Ordinálna |
| `yearQuartal` | Rok + štvrťrok (napr. "2021Q1") | Kategoriálna/Ordinálna |
| `week` | Číslo týždňa (1–53) | Numerická |
| `hour` | Hodina dňa (0–23) – **odvodená** z `unixTime` | Numerická |
| `dayofweek` | Deň v týždni (0=Po, 6=Ne) – **odvodená** z `unixTime` | Ordinálna |
| `crisis` | Krízové / normálne obdobie | Binárna kategória |

---

## Otázky, ktoré môže položiť profesor

**Q: Čo je DV a IV v tomto skripte?**
A: **DV** (závislé/vysvetľované premenné) sú `category`, `webPart`, `urlExt` – charakterizujú navštívený obsah, odvodený z URL. **IV** (nezávislé/vysvetľujúce premenné) sú časové premenné: `year`, `quartal`, `week`, `hour`, `dayofweek`, `crisis`. Analyzujeme, či čas prístupu (IV) ovplyvňuje navštívený obsah (DV).

---

**Q: Prečo `sep=";"` pri čítaní CSV?**
A: Štandardný CSV oddeľovač je čiarka, ale tento súbor používa bodkočiarku. Je to bežné v európskych exportoch, kde čiarka je desatinný oddeľovač čísel. Ak by sme nenastavili `sep=";"`, pandas by načítal celý riadok ako jeden stĺpec.

---

**Q: Prečo pri načítaní nastavujeme `errors="coerce"` pri `pd.to_numeric`?**
A: Niektoré záznamy v CSV môžu mať v číselnom stĺpci textovú hodnotu (napr. `"-"` alebo `"N/A"`). `errors="coerce"` prevedie tieto neplatné hodnoty na `NaN` namiesto vyhodenia `ValueError`. Skript tak pokračuje a neplatné záznamy sa neskôr automaticky vylúčia pri `dropna()`.

---

**Q: Prečo sa Spearmanova korelácia počíta pre každý rok zvlášť?**
A: Keby sme počítali jeden Spearman pre celé dátové obdobie (napr. 2015–2022), mohlo by dôjsť k tzv. Simpsonovmu paradoxu: v jednom roku návštevnosť rastie, v inom klesá, a celkový trend sa "vyzruší" – dostaneme $\rho \approx 0$, hoci v každom roku je silný trend. Počítaním per-rok vidíme skutočné trendy pre každé obdobie zvlášť.

---

**Q: Čo je monotónny vzťah a prečo sa meria Spearmanom?**
A: Monotónny vzťah znamená, že keď $x$ rastie, $y$ buď **vždy rastie** (rastúci trend) alebo **vždy klesá** (klesajúci trend) – ale nie nutne lineárne. Spearman meria tento trend cez koreláciu **poradí** hodnôt, nie samotných hodnôt. Je odolný voči outlierom a nevyžaduje normálne rozdelenie.

---

**Q: Čo je kontingečná tabuľka a na čo slúži?**
A: Kontingečná (krížová) tabuľka zobrazuje frekvencie kombinácií dvoch kategorických premenných. Riadky sú hodnoty premennej `crisis`, stĺpce sú hodnoty `category`, a bunky obsahujú počet záznamov pre každú kombináciu. Chi-square test overuje, či sú rozloženia frekvencií v riadkoch navzájom rovnaké (H0: nezávislosť).

---

**Q: Čo hovorí Chi-square test a čo Cramér V?**
A: **Chi-square** povie iba ÁNO/NIE – existuje štatisticky významná závislosť medzi `crisis` a `category`? **Cramér V** povie AKO SILNÁ je táto závislosť (0 = žiadna, 1 = dokonalá). Chi-square samo o sebe nestačí, pretože pri veľkých vzorkách sa takmer vždy stane štatisticky významným, aj keď je závislosť prakticky zanedbateľná.

---

**Q: Prečo Kruskal-Wallis a nie jednosmerná ANOVA?**
A: ANOVA predpokladá, že `length` je normálne rozdelená v každej kategórii. Dĺžka webových stránok typicky nie je normálne rozdelená – má výrazne zošikmené rozdelenie s dlhým pravým chvostom (veľa krátkych stránok, zopár veľmi dlhých). Kruskal-Wallis je neparametrický ekvivalent, ktorý nevyžaduje normalitu a pracuje s poradiami namiesto skutočných hodnôt.

---

**Q: Čo znamená p-hodnota v kontexte týchto testov?**
A: P-hodnota je pravdepodobnosť, že by sme dostali rovnako extrémny (alebo extrémnejší) výsledok za predpokladu, že H0 je pravdivá. Štandardná hladina významnosti $\alpha = 0.05$: ak $p < 0.05$, zamietame H0. Dôležité: zamietnutie H0 neznamená, že závislosť je **prakticky** dôležitá – pri milióne záznamov môže byť aj triviálny vzťah štatisticky významný.

---

**Q: Čo je `normalize_text` a prečo je potrebná?**
A: Textové stĺpce v reálnych logoch majú rôzne spôsoby zakódovania chýbajúcich hodnôt: `NaN` (pandas), prázdny reťazec `""`, alebo pomlčka `"-"`. Bez normalizácie by sa všetky tri počítali ako odlišné hodnoty, čo by skreslilo frekvenčné analýzy (napr. `value_counts()`). Funkcia ich zjednotí na jeden symbol `"UNKNOWN"`.

---

**Q: Prečo `unstack(fill_value=0)` pri heatmapách?**
A: `groupby` vracia výsledky iba pre kombinácie, ktoré v dátach skutočne existujú. Napríklad ak v noci o 3:00 v nedeľu nebol žiadny prístup, táto kombinácia chýba. `unstack(fill_value=0)` prevedie dvojúrovňový index na maticu a vyplní chýbajúce kombinácie nulou – inak by `imshow()` pri kreslení heatmapy zlyhalo alebo by heatmapa mala nesprávny tvar.

---

**Q: Čo je štatistická a čo praktická významnosť?**
A: **Štatistická významnosť** (p < 0.05) hovorí, že výsledok pravdepodobne nie je náhoda. **Praktická významnosť** (Cramér V, veľkosť efektu) hovorí, ako silný je vzťah v praxi. Pri tisíckach záznamov môže byť aj veľmi slabý vzťah štatisticky významný. Preto sa uvádza aj Cramér V – dáva kontext, či je závislosť len "štatistický artefakt veľkej vzorky" alebo skutočne relevantný vzťah.

---

## Zhrnutie funkcií

| Funkcia | Vstup | Výstup | Účel |
|---|---|---|---|
| `build_arg_parser()` | – | `ArgumentParser` | CLI argumenty (`--input`, `--outdir`) |
| `normalize_text(series)` | pandas Series | pandas Series | Zjednotí chýbajúce hodnoty na `"UNKNOWN"` |
| `ensure_outdir(outdir)` | `Path` | – | Vytvorí výstupný priečinok |
| `load_data(input_path)` | `Path` | `DataFrame` | Načíta CSV, normalizuje, odvodí `hour`+`dayofweek` |
| `compute_statistics(df)` | `DataFrame` | `dict` | Spearman + Chi2+CramérV + Kruskal-Wallis |
| `save_report(df, stats, outdir)` | `DataFrame`, `dict`, `Path` | `report.txt` | Textový report |
| `make_plots(df, outdir)` | `DataFrame`, `Path` | 4× PNG | Grafy návštevnosti a aktivity |
| `main()` | – | – | Orchestrátor celej analýzy |

---

## Zhrnutie štatistických metód

| Test | IV (vstup) | DV (výstup) | Čo meria | Výsledok |
|---|---|---|---|---|
| **Spearman** | poradie týždňa | počet návštev | Monotónny trend návštevnosti v čase | $\rho$, p-hodnota |
| **Chi-square** | `crisis` (binárna) | `category` (kat.) | Závislosť obsahu od krízového obdobia | $\chi^2$, p-hodnota, df |
| **Cramér V** | (z Chi-square) | (z Chi-square) | Sila závislosti crisis ↔ category | $V \in \langle 0, 1 \rangle$ |
| **Kruskal-Wallis** | `category` (skupiny) | `length` (číselná) | Rozdiel dĺžky obsahu medzi kategóriami | $H$, p-hodnota |
