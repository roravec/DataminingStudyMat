# Analýza webových logov banky – `analyze_logs5.py`

---

## Čo skript robí

Skript číta veľký CSV súbor s logmi prístupov na web komerčnej banky a vykonáva štyri kroky:

1. **Načíta a agreguje dáta** po chunckoch (nečíta celý súbor naraz – šetrí pamäť)
2. **Zostaví tabuľky** (DataFrame) z nazbieraných počítadiel
3. **Spustí tri štatistické testy** a uloží výsledky do `statistics.txt`
4. **Vykreslí prehľadový graf** `overview.png` so všetkými analýzami

### Tok dát – diagram

```
logs5.csv
    │
    ▼  pd.read_csv(chunksize=N)  → iterácia po chunckoch
    │
    ▼  normalize_text_columns()  → zjednotenie textu (UNKNOWN pre prázdne)
    │
    ├──► _process_unique_values()       → sety unikátnych IP, agentov
    ├──► _process_count_analyses()      → Counter pre každý stĺpec (category, webPart...)
    ├──► _process_weekly_visits()       → Counter: dátum týždňa → počet návštev
    ├──► _process_chi2_counts()         → Counter: (crisis, category) → počet
    ├──► _process_length_sample()       → slovník: category → vzorky hodnôt length
    └──► _process_custom_analysis()     → vlastné agregácie (priemery, filtre)
    │
    ▼  build_tables()            → Counter/slovníky → DataFrame tabuľky
    │
    ▼  compute_statistics()      → Spearman + Chi-kvadrát + Kruskal-Wallis
    │
    ▼  save_statistics()         → statistics.txt
    │
    ▼  make_overview_plot()      → overview.png
```

---

## Vstupné a výstupné súbory

```
logs5.csv
    └──► analyze_logs5.py ──► analysis_output/
                                  ├── overview.png
                                  └── statistics.txt
```

### Vstup: `logs5.csv`

Oddeľovač: `;`, uvodzovky: `"`. Skript načíta len tieto stĺpce (ostatné ignoruje):

| Stĺpec | Obsah |
|---|---|
| `anonIP` | Anonymizovaná IP adresa |
| `agent` | Identifikátor agenta |
| `ipPart` | Časť IP adresy |
| `userAgent` | User-agent reťazec prehliadača |
| `unixTime` | Čas prístupu ako Unix timestamp |
| `yearQuartal` | Rok a kvartál (napr. 2020Q1) |
| `week` | Číslo týždňa |
| `webPart` | Časť webu |
| `category` | Kategória obsahu stránky |
| `urlExt` | Prípona URL |
| `length` | Čas strávený na stránke (sekundy) |
| `internal` | Interný / externý prístup |
| `crisis` | 1 = krízové obdobie, 0 = bežné |

### Výstup: `analysis_output/statistics.txt`

```
1. Trend navstevnosti: poradie tyzdna vs. pocet navstev
   Metoda: Spearmanova korelacia
   r = 0.1090
   p = 1.1633e-01
   Zaver: Korelacia nie je statisticky vyznamna (p >= 0.05)

2. Zavislost obsahu webu od obdobia: crisis vs. category
   Metoda: Chi-kvadrat test + Cramerov V
   chi2 = 225219.72,  df = 5
   p    = 0.0000e+00
   Cramerov V = 0.3298
   Zaver: Statisticky vyznamna zavislost (p < 0.05)
   Sila: stredna (V >= 0.3)

3. Rozdiel dlzky navstevy medzi kategoriami obsahu
   Metoda: Kruskal-Wallis test
   H = 491.58
   p = 5.2436e-104
   Zaver: Statisticky vyznamne rozdiely medzi kategoriami (p < 0.05)
```

### Výstup: `analysis_output/overview.png`

Graf s viacerými panelmi:
- Panel 1: trend návštevnosti po týždňoch (čiara)
- Panel 2: top kategórie podľa počtu návštev (barh)
- Ďalšie panely: vlastné analýzy (priemerný čas na stránke, populárne kategórie počas krízy...)
- Posledný panel: výsledky štatistických testov

---

## Postup riešenia – krok za krokom

### 1. Spustenie a argumenty

```python
parser = argparse.ArgumentParser(...)
parser.add_argument("--input",     default=Path("logs5.csv"))
parser.add_argument("--outdir",    default=Path("analysis_output"))
parser.add_argument("--chunksize", default=5_000_000, type=int)
args = parser.parse_args()
```

Skript sa spúšťa z terminálu:

```
python analyze_logs5.py --input logs5.csv --outdir analysis_output
```

`argparse` automaticky spracuje argumenty z príkazového riadka.

---

### 2. Načítanie CSV po chunkoch – `process_csv()`

Celý súbor sa nikdy nečíta do pamäte naraz. Namiesto toho `pd.read_csv()` vráti **iterátor**, ktorý pri každom prechode cyklu načíta `chunksize` riadkov:

```python
reader = pd.read_csv(
    input_path,
    sep=";",
    quotechar='"',
    usecols=USECOLS,       # nacitame len potrebne stlpce
    chunksize=chunksize,   # velkost jedneho chunku
    low_memory=True,
)

for chunk in reader:      # kazdy chunk je DataFrame
    chunk = normalize_text_columns(chunk, text_columns)
    _process_unique_values(chunk, ...)
    _process_count_analyses(chunk, ...)
    ...
```

Výhodou je, že pri súbore s miliónmi riadkov nestačí zhruba jeden chunk v pamäti, nie celý súbor.

---

### 3. Normalizácia textu – `normalize_text_columns()`

Pred každou analýzou sa textové stĺpce "upracú":

```python
def normalize_text_series(series, default="UNKNOWN"):
    return series.astype("string").fillna(default).replace({"": default, "-": default})
```

- `astype("string")` – prevedie stĺpec na textový typ
- `fillna(default)` – prázdne hodnoty (NaN) → `"UNKNOWN"`
- `replace({...})` – prázdny reťazec alebo pomlčka → `"UNKNOWN"`

**Prečo je to dôležité?** Bez normalizácie by ta istá hodnota existovala vo viacerých podobách (`""`, `"-"`, `NaN`), čo by pokazilo agregácie.

---

### 4. Zber unikátnych identifikátorov – `_process_unique_values()`

```python
def _process_unique_values(chunk, unique_ips, unique_agents, ...):
    unique_ips.update(chunk["anonIP"].tolist())
    unique_agents.update(chunk["agent"].tolist())
    ...
```

Namiesto zoznamu sa používa **set (množina)**, pretože:
- automaticky ignoruje duplikáty
- `set.update()` je rýchlejšie než kontrolovanie každej hodnoty osobitne
- Na konci `len(unique_ips)` dá presný počet unikátnych IP

---

### 5. Počítanie výskytov – `_process_count_analyses()`

```python
for analysis in COUNT_ANALYSES:
    if analysis.get("kind") != "column":
        continue
    column = analysis["column"]
    count_counters[analysis["table_key"]].update(chunk[column].tolist())
```

`Counter.update()` prijme zoznam hodnôt a automaticky inkrementuje počítadlá. Napríklad pre stĺpec `category` dostaneme niečo ako `Counter({"news": 150000, "finance": 89000, ...})`.

---

### 6. Týždenné návštevy – `_process_weekly_visits()`

```python
unix_time   = pd.to_numeric(chunk["unixTime"], errors="coerce")
timestamp   = pd.to_datetime(unix_time, unit="s", errors="coerce", utc=True)
week_start  = build_week_start(timestamp)

weekly_counts = week_start.value_counts(dropna=True)
for week_value, count in weekly_counts.items():
    visits_by_week[str(week_value.date())] += int(count)
```

**`build_week_start()`** prevedie každý timestamp na **dátum pondelka toho týždňa**:

```python
def build_week_start(timestamp_series):
    timestamp_naive = timestamp_series.dt.tz_localize(None)
    return timestamp_naive.dt.to_period("W").dt.start_time
```

- `tz_localize(None)` – odstráni timezone, aby `to_period` fungoval
- `to_period("W")` – zaradí každý timestamp do týždenného "bucketu"
- `dt.start_time` – vráti dátum začiatku toho týždňa (pondelok)

Výsledok: slovník `{ "2020-01-06": 12500, "2020-01-13": 13200, ... }`.

---

### 7. Zber dát pre štatistické testy

#### Kontingencia pre chi-kvadrát – `_process_chi2_counts()`

```python
counts = chunk.groupby(["crisis", "category"]).size()
for (crisis_val, cat_val), count in counts.items():
    chi2_counter[(str(crisis_val), str(cat_val))] += int(count)
```

`groupby().size()` spočíta počet riadkov pre každú kombináciu hodnôt `crisis` a `category`. Napríklad: `("1", "news") → 45000`.

#### Vzorky dĺžky návštevy pre Kruskal-Wallis – `_process_length_sample()`

```python
for cat_val, group in valid_frame.groupby("category"):
    current_count = len(length_sample_by_category[cat_val])
    if current_count >= MAX_SAMPLE_PER_CATEGORY:   # limit = 5000
        continue
    values = group["length"].to_numpy(dtype=float)
    space  = MAX_SAMPLE_PER_CATEGORY - current_count
    length_sample_by_category[cat_val].extend(values[:space].tolist())
```

Pre každú kategóriu sa zbierajú maximálne 5 000 hodnôt `length`. Limit chráni pred nadmernou spotrebou pamäte pri miliónoch riadkov.

---

### 8. Zostavenie tabuliek – `build_tables()`

Z interných počítadiel (Counter, defaultdict) sa vytvoria DataFrame tabuľky, ktoré idú do grafov aj štatistík:

```python
# Priklad: weekly_df
weekly_df = counter_to_dataframe(results["visits_by_week"], ["week_start", "visits"])
weekly_df["week_start"] = pd.to_datetime(weekly_df["week_start"])
weekly_df = weekly_df.sort_values("week_start").reset_index(drop=True)

# Priklad: tabulka s priemerom (avg_length_by_category)
for group_key, total_value in sums.items():
    count     = counts[group_key]
    avg_value = total_value / count if count else float("nan")
    rows.append({"category": group_key, "n": count, "avg_value": avg_value})
```

**`counter_to_dataframe()`** prevedie `Counter` → zoznam riadkov → DataFrame a zoradí podľa počtu zostupne.

---

### 9. Výpočet štatistík – `compute_statistics()`

Táto funkcia spúšťa tri testy. Výsledky vráti ako slovník, ktorý sa uloží do súboru a vykreslí v poslednom paneli grafu.

---

### 10. Uloženie výsledkov a kreslenie

```python
save_statistics(stat_results, args.outdir)  → statistics.txt
make_overview_plot(args.outdir, tables, stat_results)  → overview.png
```

`make_overview_plot()` vytvorí `matplotlib` figure s `total_plots = 2 + len(CUSTOM_ANALYSES) + 1` panelmi a uloží ho ako PNG.

---

## Štatistické metódy a vzorce

---

### 1. Spearmanová korelácia – trend návštevnosti

**Otázka:** Rastie alebo klesá návštevnosť webu v čase?

**Nezávislá premenná (IV):** poradie týždňa (0, 1, 2, ...) – premená reprezentujúca čas

**Závislá premenná (DV):** počet návštev v danom týždni

**Prečo Spearman a nie Pearson?**

Pearsonova korelácia predpokladá normálne rozdelenie a lineárny vzťah. Spearmanová korelácia pracuje s **poradiami hodnôt** – je robustnejšia voči outlierom a nevyžaduje lineárny vzťah, len monotónny (keď jedna premenná rastie, druhá tiež rastie alebo klesá).

#### Vzorec

Spearmanová korelácia = **Pearsonova korelácia aplikovaná na poradia**:

$$
r_s = \frac{\text{cov}(R_X, R_Y)}{\sigma_{R_X} \cdot \sigma_{R_Y}}
$$

kde $R_X$ a $R_Y$ sú poradia hodnôt $X$ a $Y$.

Zjednodušený vzorec (keď nie sú viazané poradie):

$$
r_s = 1 - \frac{6 \sum_{i=1}^{n} d_i^2}{n(n^2 - 1)}
$$

kde:
- $n$ = počet dátových bodov (počet týždňov)
- $d_i$ = rozdiel poradí pre $i$-ty bod: $d_i = \text{rank}(X_i) - \text{rank}(Y_i)$

#### Kód v skripte

```python
week_rank = np.arange(n_weeks, dtype=float)       # 0, 1, 2, ..., n-1
visits    = weekly_df["visits"].to_numpy(dtype=float)

sp_result = scipy_stats.spearmanr(week_rank, visits)
stat_results["spearman_r"] = float(sp_result.statistic)
stat_results["spearman_p"] = float(sp_result.pvalue)
```

Bez scipy sa počíta manuálne cez `np.corrcoef` aplikovaný na poradia:

```python
def _rank_array(arr):
    order = np.argsort(arr)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(arr) + 1, dtype=float)
    return ranks

r_matrix = np.corrcoef(_rank_array(week_rank), _rank_array(visits))
stat_results["spearman_r"] = float(r_matrix[0, 1])
```

#### Interpretácia rozsahov

| Hodnota $r_s$ | Interpretácia |
|---|---|
| $+1.0$ | Dokonalý rastúci trend |
| $+0.7$ až $+1.0$ | Silná pozitívna korelácia |
| $+0.3$ až $+0.7$ | Stredná pozitívna korelácia |
| $-0.3$ až $+0.3$ | Slabá alebo žiadna korelácia |
| $-0.7$ až $-0.3$ | Stredná negatívna korelácia |
| $-1.0$ | Dokonalý klesajúci trend |

#### Výsledok z datasetu

```
r = 0.1090,  p = 1.1633e-01
Záver: Korelácia nie je štatisticky významná (p >= 0.05)
```

$r_s = 0.109$ je slabá kladná korelácia. Keďže $p = 0.116 > 0.05$, **neodmietame nulovú hypotézu** – dáta nepotvrdzujú štatisticky významný rastúci ani klesajúci trend v návštevnosti.

**Nulová hypotéza $H_0$:** Medzi poradím týždňa a počtom návštev neexistuje monotónna závislosť ($r_s = 0$).

---

### 2. Chi-kvadrát test + Cramerov V – obsah webu a krízové obdobie

**Otázka:** Závisí kategória obsahu, ktorú používatelia navštevujú, od toho, či je krízové alebo bežné obdobie?

**Nezávislá premenná (IV):** `crisis` (0 = bežné, 1 = krízové)

**Závislá premenná (DV):** `category` (kategória obsahu stránky)

Obe premenné sú **nominálne (kategorické)** – preto sa používa chi-kvadrát test, nie t-test ani ANOVA.

#### Kontingentná tabuľka

Pred testom sa zostaví kontingentná tabuľka. Každá bunka obsahuje počet riadkov s danou kombináciou:

|  | category A | category B | category C | ... |
|---|---|---|---|---|
| crisis = 0 | 80 000 | 45 000 | 32 000 | ... |
| crisis = 1 | 12 000 | 30 000 | 18 000 | ... |

#### Vzorec chi-kvadrát

$$
\chi^2 = \sum_{i} \sum_{j} \frac{(O_{ij} - E_{ij})^2}{E_{ij}}
$$

kde:
- $O_{ij}$ = **pozorovaný** počet v bunke $(i, j)$
- $E_{ij}$ = **očakávaný** počet pri platnosti $H_0$ (nezávislosť): $E_{ij} = \frac{R_i \cdot C_j}{N}$
  - $R_i$ = súčet $i$-teho riadka (celkový počet prístupov v danom krízovm stave)
  - $C_j$ = súčet $j$-teho stĺpca (celkový počet prístupov v danej kategórii)
  - $N$ = celkový počet pozorovaní

#### Stupne voľnosti

$$
df = (r - 1)(c - 1)
$$

kde $r$ = počet riadkov, $c$ = počet stĺpcov kontingentnej tabuľky.

V datasete: $df = (2-1)(6-1) = 5$.

#### Cramerov V – sila závislosti

Chi-kvadrát samotný hovorí len o tom, **či** závislosť existuje, nie o tom, **ako silná** je. Cramerov V normalizuje chi-kvadrát do rozsahu $\langle 0, 1 \rangle$:

$$
V = \sqrt{\frac{\chi^2}{N \cdot \min(r-1,\; c-1)}}
$$

kde:
- $N$ = celkový počet pozorovaní
- $\min(r-1, c-1)$ = menší z rozmerov tabuľky mínus 1

| Cramerov V | Interpretácia (podľa Cohena) |
|---|---|
| $V < 0.1$ | Zanedbateľná sila |
| $0.1 \leq V < 0.3$ | Malá sila |
| $0.3 \leq V < 0.5$ | Stredná sila |
| $V \geq 0.5$ | Silná závislosť |

#### Kód v skripte

```python
# Zostavenie kontingentnej tabulky
cont_table = np.zeros((len(crisis_vals), len(category_vals)), dtype=float)
for (cv, catv), cnt in chi2_counter.items():
    cont_table[crisis_idx[cv], category_idx[catv]] = float(cnt)

# Chi-kvadrat test
chi2_stat, chi2_p, chi2_dof, _ = scipy_stats.chi2_contingency(cont_table)

# Cramerov V
n_total  = float(cont_table.sum())
min_dim  = min(len(crisis_vals), len(category_vals)) - 1
cramer_v = float(np.sqrt(chi2_stat / (n_total * min_dim)))
```

#### Výsledok z datasetu

```
chi2 = 225219.72,  df = 5,  p = 0.0000e+00
Cramerov V = 0.3298
Záver: Štatisticky významná závislosť (p < 0.05) – stredná sila
```

$\chi^2 = 225\,219.72$ je extrémne vysoké – s toľkými pozorovaniami aj malý rozdiel v rozložení kategórií sa prejaví ako štatisticky významný. Cramerov $V = 0.33$ hovorí, že sila je **stredná** – rozloženie kategórií sa v krízovom a bežnom období reálne líši.

**Nulová hypotéza $H_0$:** Kategória obsahu a krízový stav sú nezávislé (rozloženie kategórií je rovnaké v krízovom aj bežnom období).

---

### 3. Kruskal-Wallis test – čas na stránke podľa kategórie

**Otázka:** Trávia používatelia štatisticky rôzne dlhý čas na stránkach rôznych kategórií?

**Nezávislá premenná (IV):** `category` (nominálna, viac skupín)

**Závislá premenná (DV):** `length` (čas strávený na stránke, číselná)

**Prečo Kruskal-Wallis a nie ANOVA?**

ANOVA predpokladá normálne rozdelenie a homogénne rozptyly v skupinách. Webové logovanie typicky generuje dáta s výrazne nesymetrickým rozdelením (väčšina návštev je krátka, občas veľmi dlhé – outliere). Kruskal-Wallis je **neparametrická** alternatíva k jednosmernej ANOVA – pracuje s **poradiami hodnôt** namiesto so surovými číslami a nevyžaduje žiadne predpoklady o rozdelení.

#### Vzorec Kruskal-Wallis

$$
H = \frac{12}{N(N+1)} \sum_{i=1}^{k} \frac{n_i \bar{R}_i^2}{1} - 3(N+1)
$$

Presnejší tvar (štandardný):

$$
H = \left(\frac{12}{N(N+1)} \sum_{i=1}^{k} \frac{T_i^2}{n_i}\right) - 3(N+1)
$$

kde:
- $k$ = počet skupín (počet kategórií obsahu)
- $N$ = celkový počet pozorovaní vo všetkých skupinách
- $n_i$ = počet pozorovaní v $i$-tej skupine
- $T_i$ = súčet poradí v $i$-tej skupine (každé pozorovanie dostane globálne poradie od 1 do $N$)
- $\bar{R}_i = T_i / n_i$ = priemerné poradie v $i$-tej skupine

Štatistika $H$ sa pri platnosti $H_0$ riadi **chi-kvadrát rozdelením** s $df = k - 1$ stupňami voľnosti.

#### Intuitívne vysvetlenie

1. Všetkým hodnotám `length` (zo všetkých kategórií dohromady) priradíme poradie od 1 (najkratšia návšteva) po $N$ (najdlhšia).
2. Pre každú kategóriu spočítame priemerné poradie.
3. Ak sú priemerné poradia vo všetkých kategóriách podobné → $H$ je malé → kategória nemá vplyv na čas.
4. Ak niektoré kategórie majú konzistentne vyššie poradia (dlhšie návštevy) a iné nižšie → $H$ je veľké → zamietame $H_0$.

#### Kód v skripte

```python
# Zostavenie zoznamov vzoriek pre kazdu kategoriu (min. 5 hodnot)
kw_groups = [
    np.array(samples, dtype=float)
    for samples in results["length_sample_by_category"].values()
    if len(samples) >= 5
]

# Kruskal-Wallis test
h_stat, kw_p = scipy_stats.kruskal(*kw_groups)
```

`*kw_groups` rozbalí zoznam skupín ako samostatné argumenty – `scipy_stats.kruskal()` prijíma ľubovoľný počet skupín.

Zber vzoriek sa robí v `_process_length_sample()` s limitom 5 000 hodnôt na kategóriu (`MAX_SAMPLE_PER_CATEGORY = 5000`), aby sa predišlo nadmernej spotrebe pamäte.

#### Výsledok z datasetu

```
H = 491.58,  p = 5.2436e-104
Záver: Štatisticky významné rozdiely medzi kategóriami (p < 0.05)
```

$H = 491.58$ s $p \approx 5.2 \times 10^{-104}$ je extrémne silný výsledok. **Odmietame $H_0$** – čas strávený na stránke sa štatisticky významne líši medzi rôznymi kategóriami obsahu.

**Nulová hypotéza $H_0$:** Rozdelenie času stráveného na stránke (`length`) je rovnaké pre všetky kategórie obsahu.

---

## Prehľad všetkých použitých funkcií

| Funkcia | Čo robí |
|---|---|
| `main()` | Vstupný bod: parsuje argumenty, volá ostatné funkcie v správnom poradí |
| `build_arg_parser()` | Vytvorí `argparse` parser pre `--input`, `--outdir`, `--chunksize` |
| `ensure_outdir()` | Vytvorí výstupný priečinok ak neexistuje (`mkdir parents=True`) |
| `process_csv()` | Číta CSV po chunkoch, zbiera všetky agregácie, vracia slovník výsledkov |
| `normalize_text_columns()` | Zavolá `normalize_text_series()` na každý textový stĺpec |
| `normalize_text_series()` | Prevedie na string, nahradí NaN / prázdne / pomlčku za `"UNKNOWN"` |
| `get_text_columns_for_normalization()` | Zostavi zoznam stĺpcov na normalizáciu z konfigurácií |
| `_process_unique_values()` | Do setov zbiera unikátne IP, agentov, user-agentov |
| `_process_count_analyses()` | `Counter.update()` pre každý stĺpec z `COUNT_ANALYSES` |
| `_process_weekly_visits()` | Unix timestamp → týždenný bucket, počíta návštevy po týždňoch |
| `build_week_start()` | `to_period("W").dt.start_time` – dátum pondelka daného týždňa |
| `_process_chi2_counts()` | `groupby(["crisis","category"]).size()` → Counter pre chi-kvadrát |
| `_process_length_sample()` | Zbiera vzorky `length` na kategóriu (max 5 000) pre K-W test |
| `_process_custom_analysis()` | Vlastné agregácie: filter, počet alebo priemer podľa `CUSTOM_ANALYSES` |
| `build_tables()` | Counter/slovníky → DataFrame tabuľky zoradené podľa počtu |
| `counter_to_dataframe()` | Counter (key → hodnota) → DataFrame s pomenovanými stĺpcami |
| `compute_statistics()` | Spearman + Chi-kvadrát/Cramerov V + Kruskal-Wallis, vracia slovník |
| `save_statistics()` | Formátuje výsledky ako text a uloží do `statistics.txt` |
| `make_overview_plot()` | Vytvorí multi-panel PNG graf a uloží do `overview.png` |

---

## Konfigurácia analýz

Skript je riadený dvoma konfiguračnými zoznamami na vrchu súboru:

### `COUNT_ANALYSES`

Definuje jednoduché agregácie (koľkokrát sa každá hodnota stĺpca vyskytuje):

```python
COUNT_ANALYSES = [
    {"table_key": "weekly_df",   "kind": "weekly",  "column": "week"},
    {"table_key": "category_df", "kind": "column",  "column": "category"},
    {"table_key": "webpart_df",  "kind": "column",  "column": "webPart"},
    ...
]
```

### `CUSTOM_ANALYSES`

Definuje vlastné analýzy s filtrami, priemermi a typom grafu:

```python
CUSTOM_ANALYSES = [
    {
        "name":       "avg_length_by_category",
        "group_cols": ["category"],
        "value_col":  "length",          # ak je vyplnene -> pocita priemer
        "chart":      "barh",
        "top_n":      10,
        "title":      "Priemerná dĺžka návštevy podľa kategórie",
    },
    {
        "name":       "categories_during_crisis",
        "group_cols": ["category"],
        "chart":      "barh",
        "top_n":      15,
        "filter":     {"crisis": "1"},   # len krizove obdobie
        "title":      "Najpopulárnejšie kategórie počas krízy",
    },
    ...
]
```

Pridanie nového grafu = pridanie nového slovníka do `CUSTOM_ANALYSES`. Skript ho automaticky spracuje a vykreslí.

---

## Najdôležitejšie technické koncepty

### Prečo Counter a nie DataFrame pre agregáciu?

`Counter` je oveľa pamäťovo efektívnejší pri chunkovanom spracovaní. Keby sme každý chunk ukladali ako DataFrame a potom ich spájali (`pd.concat`), pamäť by rástla lineárne. `Counter.update()` iba pripočítava hodnoty, pamäť ostáva konštantná.

### `defaultdict(list)` vs. bežný slovník

```python
length_sample_by_category = defaultdict(list)
# ...
length_sample_by_category[cat_val].extend(values)
```

`defaultdict(list)` automaticky vytvorí prázdny zoznam pre každý nový kľúč. Bez neho by sme museli písať:

```python
if cat_val not in length_sample_by_category:
    length_sample_by_category[cat_val] = []
length_sample_by_category[cat_val].extend(values)
```

### `errors="coerce"` pri konverzii čísel

```python
unix_time = pd.to_numeric(chunk["unixTime"], errors="coerce")
```

Ak sa hodnota nedá previesť na číslo, namiesto výnimky sa vloží `NaN`. Tým sa predíde pádu skriptu pri poškodených riadkoch.

### Voliteľné knižnice – `try/except` import

```python
try:
    import matplotlib.pyplot as plt
    PLOT_AVAILABLE = True
except Exception:
    PLOT_AVAILABLE = False
```

Skript beží aj bez `matplotlib` alebo `scipy` – len preskočí grafy alebo štatistické p-hodnoty.

---

## Súhrn štatistických výsledkov

| Test | IV | DV | Výsledok | Záver |
|---|---|---|---|---|
| Spearmanová korelácia | Poradie týždňa | Počet návštev | $r_s = 0.109$, $p = 0.116$ | Trend **nie je** štatisticky významný |
| Chi-kvadrát + Cramerov V | `crisis` | `category` | $\chi^2 = 225\,219$, $V = 0.33$ | Závislosť **je** štatisticky významná, stredná sila |
| Kruskal-Wallis | `category` | `length` | $H = 491.58$, $p \approx 0$ | Rozdiely **sú** štatisticky významné |

---

## Možné otázky profesora – otázky a odpovede

---

### Otázky o p-hodnote a štatistickej významnosti

**Q: Čo je p-hodnota?**

A: p-hodnota je pravdepodobnosť, že by sme dostali taký istý alebo extrémnejší výsledok, keby platila nulová hypotéza (teda keby žiadna závislosť neexistovala). Čím menšia p-hodnota, tým menej pravdepodobné je, že výsledok je náhoda.

**Q: Prečo používame hranicu 0.05?**

A: Je to konvencia – 5 % riziko, že odmietame nulovú hypotézu, aj keď platí (chyba 1. druhu). Inak povedané: akceptujeme 5 % šancu falošného poplachu. V praxi sa používa aj 0.01 alebo 0.001 pre prísnejšie testy.

**Q: Čo znamená, že výsledok je "štatisticky významný"?**

A: Znamená to, že zamietame nulovú hypotézu – závislosť pozorovaná v dátach je natoľko silná, že je nepravdepodobné, že by vznikla náhodou. **Neznamená to, že závislosť je prakticky dôležitá** – pri veľkom datasete (milióny riadkov) môže byť aj veľmi slabá závislosť štatisticky významná.

---

### Otázky o Spearmanovej korelácie

**Q: Prečo ste použili Spearmanovú koreláciu a nie Pearsonovu?**

A: Pearsonova korelácia meria silu **lineárneho** vzťahu a predpokladá normálne rozdelenie. Spearmanová korelácia pracuje s **poradiami hodnôt** a meria len to, či je vzťah **monotónny** (keď rastie jedna premenná, druhá tiež rastie alebo klesá) – nevyžaduje lineárnosť ani normálne rozdelenie. Návštevnosť webu môže mať nesymetrické rozdelenie (skokové udalosti, výpadky), preto je Spearman vhodnejší.

**Q: Čo je nezávislá (IV) a závislá premenná (DV) v Spearmanovej korelácie?**

A: IV = poradie týždňa (0, 1, 2, ...) – reprezentuje plynutie času. DV = počet návštev v danom týždni. Skúmame, či sa návštevnosť mení systematicky s časom.

**Q: Vysvetlite vzorec Spearmanovej korelácie.**

A: Spearmanová korelácia je Pearsonova korelácia aplikovaná na **poradia** hodnôt. Každej hodnote sa priradí jej poradie (1 = najmenšia, n = najväčšia). Potom:

$$r_s = 1 - \frac{6 \sum_{i=1}^{n} d_i^2}{n(n^2 - 1)}$$

kde $d_i$ je rozdiel poradí pre $i$-ty bod (poradie v týždennej osi mínus poradie v počte návštev). Ak sú poradia totožné, $d_i = 0$ pre každý bod a $r_s = 1$.

**Q: Čo znamená $r_s = 0.109$ v kontexte vašich dát?**

A: Je to veľmi slabá kladná korelácia – takmer žiadna. Keďže $p = 0.116 > 0.05$, neodmietame nulovú hypotézu. Dáta nepotvrdzujú, že by návštevnosť bankovej webstránky systematicky rástla alebo klesala v čase počas sledovaného obdobia.

**Q: Ako ste v kóde vypočítali Spearmanovú koreláciu bez scipy?**

A: Manuálne cez `np.corrcoef` aplikovaný na poradia. Funkcia `_rank_array()` prevedie pole hodnôt na pole poradí pomocou `np.argsort()` – najprv zistí poradie indexov pri zoradení, potom priradí každej hodnote jej poradie (1 až n). Potom `np.corrcoef` vypočíta Pearsonov r na týchto poradiach, čo je ekvivalentné Spearmanovmu r.

---

### Otázky o Chi-kvadrát teste

**Q: Prečo ste použili Chi-kvadrát test pre vzťah crisis a category?**

A: Obe premenné sú **nominálne (kategorické)** – `crisis` má hodnoty 0/1, `category` má niekoľko textových hodnôt. Pre kategorické premenné sa nemôže použiť t-test ani ANOVA (tie vyžadujú číselné DV). Chi-kvadrát test porovnáva **pozorované** rozloženie hodnôt s **očakávaným** rozložením pri nezávislosti.

**Q: Čo je kontingentná tabuľka a ako ste ju zostavili?**

A: Kontingentná tabuľka je matica, kde riadky = hodnoty jednej premennej (crisis: 0 alebo 1) a stĺpce = hodnoty druhej premennej (kategórie obsahu). Každá bunka obsahuje počet riadkov s danou kombináciou. V kóde sa zostavuje takto:

```python
cont_table = np.zeros((len(crisis_vals), len(category_vals)), dtype=float)
for (cv, catv), cnt in chi2_counter.items():
    cont_table[crisis_idx[cv], category_idx[catv]] = float(cnt)
```

`chi2_counter` bol plnený počas chunkovania cez `groupby(["crisis","category"]).size()`.

**Q: Vysvetlite vzorec chi-kvadrát – čo je $O_{ij}$ a $E_{ij}$?**

A: $O_{ij}$ = **pozorovaný** počet v bunke (koľko riadkov skutočne má danú kombináciu crisis a category). $E_{ij}$ = **očakávaný** počet, ktorý by sme dostali, keby obe premenné boli úplne nezávislé:

$$E_{ij} = \frac{R_i \cdot C_j}{N}$$

kde $R_i$ = súčet $i$-teho riadka, $C_j$ = súčet $j$-teho stĺpca, $N$ = celkový počet riadkov. Ak sú pozorované a očakávané počty veľmi podobné → $\chi^2$ je malé → premenné sú nezávislé.

**Q: Čo sú stupne voľnosti pri chi-kvadrát teste a prečo df = 5?**

A: $df = (r-1)(c-1)$, kde $r$ = počet riadkov a $c$ = počet stĺpcov tabuľky. V datasete: `crisis` má 2 hodnoty (0 a 1), `category` má 6 kategórií → $df = (2-1)(6-1) = 1 \times 5 = 5$. Stupne voľnosti hovoria, koľko buniek tabuľky je "voľných" – keď poznáme súčty riadkov a stĺpcov, zvyšné bunky sú jednoznačne určené.

**Q: Prečo je $\chi^2 = 225\,219$ tak obrovské? Je to problém?**

A: Nie je to problém, ale je to dôsledok veľkého datasetu. Chi-kvadrát je kumulatívna suma cez všetky bunky tabuľky – pri miliónoch riadkov aj malý percentuálny rozdiel medzi pozorovaným a očakávaným rozložením dá veľké absolútne číslo. Preto sa pridáva **Cramerov V**, ktorý normalizuje chi-kvadrát na rozsah 0–1 a hovorí o skutočnej **sile** závislosti nezávisle od veľkosti datasetu.

**Q: Čo je Cramerov V a ako sa interpretuje?**

A: Cramerov V meria silu závislosti medzi dvoma kategorickými premennými v rozsahu 0 (žiadna závislosť) až 1 (dokonalá závislosť):

$$V = \sqrt{\frac{\chi^2}{N \cdot \min(r-1,\; c-1)}}$$

Podľa Cohena: $V < 0.1$ zanedbateľné, $0.1$–$0.3$ malá, $0.3$–$0.5$ stredná, $\geq 0.5$ silná. V datasete $V = 0.33$ → stredná sila – rozloženie kategórií obsahu sa reálne líši medzi krízovým a bežným obdobím.

**Q: Aká je nulová hypotéza chi-kvadrát testu?**

A: $H_0$: Kategória obsahu a krízový stav sú **nezávislé** – rozloženie kategórií je rovnaké bez ohľadu na to, či je krízové alebo bežné obdobie. Zamietame $H_0$ (p ≈ 0) – teda krízové obdobie súvisí s iným rozložením kategórií obsahu.

---

### Otázky o Kruskal-Wallis teste

**Q: Prečo ste použili Kruskal-Wallis a nie jednosmernú ANOVA?**

A: ANOVA predpokladá **normálne rozdelenie** hodnôt v každej skupine a **homogenitu rozptylov** (Leveneov test). Čas strávený na webstránke (`length`) má typicky výrazne nesymetrické rozdelenie – väčšina návštev je krátka, ale niektoré sú extrémne dlhé (outliere). Kruskal-Wallis je **neparametrický** test – nepredpokladá normálne rozdelenie, pracuje s **poradiami** hodnôt namiesto surovými číslami.

**Q: Vysvetlite intuitívne, čo Kruskal-Wallis počíta.**

A: Zoberieme všetky hodnoty `length` zo všetkých kategórií dohromady a priradíme im globálne poradia (1 = najkratšia návšteva, N = najdlhšia). Potom pre každú kategóriu spočítame priemerné poradie. Ak sú priemerné poradia vo všetkých kategóriách podobné, kategória nemá vplyv na dĺžku návštevy ($H$ je malé). Ak niektoré kategórie majú konzistentne vysoké poradia (dlhé návštevy) a iné nízke, $H$ je veľké a zamietame $H_0$.

**Q: Vysvetlite vzorec Kruskal-Wallis.**

$$H = \left(\frac{12}{N(N+1)} \sum_{i=1}^{k} \frac{T_i^2}{n_i}\right) - 3(N+1)$$

- $N$ = celkový počet pozorovaní (súčet vzoriek zo všetkých kategórií)
- $k$ = počet skupín (kategórií obsahu)
- $n_i$ = počet pozorovaní v $i$-tej kategórii
- $T_i$ = **súčet poradí** v $i$-tej kategórii

Ak sú poradia rovnomerne rozdelené medzi skupinami, $T_i / n_i$ je rovnaké pre každú skupinu a $H$ je blízke nule. Štatistika $H$ sa riadi chi-kvadrát rozdelením s $df = k - 1$.

**Q: Aká je nulová hypotéza Kruskal-Wallis testu?**

A: $H_0$: Rozdelenie času stráveného na stránke (`length`) je **rovnaké pre všetky kategórie** obsahu – kategória obsahu nemá vplyv na to, ako dlho používateľ na stránke zostane. Zamietame $H_0$ ($H = 491.58$, $p \approx 5.2 \times 10^{-104}$).

**Q: Prečo zbieráte maximálne 5 000 vzoriek na kategóriu?**

A: Kruskal-Wallis nepotrebuje všetky dáta – test je dostatočne presný aj so vzorkou. Pri miliónoch riadkov by uloženie všetkých hodnôt `length` pre každú kategóriu spotrebovalo príliš veľa pamäte. Konštanta `MAX_SAMPLE_PER_CATEGORY = 5000` je kompromis medzi presnosťou testu a spotrebou pamäte.

**Q: Čo znamená $p \approx 5.2 \times 10^{-104}$?**

A: Je to astronomicky malá p-hodnota – prakticky nula. Pravdepodobnosť, že by sme dostali $H = 491.58$ náhodou (pri platnosti $H_0$), je $5.2 \times 10^{-104}$. Jednoznačne odmietame nulovú hypotézu – kategória obsahu má preukázateľný vplyv na dĺžku návštevy.

---

### Otázky o kóde a implementácii

**Q: Prečo CSV čítate po chunkoch a nie naraz?**

A: `pd.read_csv()` bez `chunksize` načíta celý súbor do RAM. Pri logoch s miliónmi riadkov to môže byť gigabajty. S `chunksize=N` dostaneme **iterátor**, ktorý do pamäte načíta vždy len N riadkov, spracuje ich a uvoľní. Pamäťová náročnosť je tak konštantná, nie lineárna s veľkosťou súboru.

**Q: Prečo používate `Counter` namiesto toho, aby ste každý chunk uložili do DataFrame a nakoniec ich spájali?**

A: `pd.concat()` pri každom volání alokuje novú pamäť pre výsledný DataFrame – pamäť by rástla lineárne. `Counter.update()` iba inkrementuje existujúce hodnoty v slovníku, bez alokácie nových štruktúr. Je to rádovo efektívnejšie pre agregáciu veľkého množstva dát.

**Q: Prečo používate `set` pre unikátne IP adresy?**

A: Set (množina) garantuje unikátnosť – duplikáty sa automaticky ignorujú. Vyhľadávanie v sete je O(1) (konštantný čas) oproti O(n) v zozname. `set.update()` hromadne pridá hodnoty z iterovateľného objektu a ignoruje existujúce.

**Q: Čo robí `errors="coerce"` pri `pd.to_numeric()`?**

A: Ak sa hodnota nedá previesť na číslo (napr. text v stĺpci `unixTime`), namiesto vyhodenia výnimky sa vloží `NaN`. Skript tak nezlyhá pri poškodených alebo neočakávaných hodnotách v dátach.

**Q: Prečo normalizujete textové stĺpce pred analýzou?**

A: Bez normalizácie by tá istá "chýbajúca hodnota" existovala v rôznych podobách: `NaN`, `""` (prázdny reťazec), `"-"` (pomlčka). Pri agregácii (`Counter.update()`, `groupby()`) by sa tieto formy počítali oddelene, čo by skreslilo výsledky. Po normalizácii majú všetky tri podoby jednotnú hodnotu `"UNKNOWN"`.

**Q: Čo je `defaultdict(list)` a prečo ste ho použili?**

A: `defaultdict(list)` je slovník, ktorý pre každý nový kľúč automaticky vytvorí prázdny zoznam. Bez neho by sme pred každým `extend()` museli kontrolovať, či kľúč existuje. Použité pre `length_sample_by_category` – zbieranie vzoriek dĺžky návštevy podľa kategórie.

**Q: Čo robí `to_period("W").dt.start_time`?**

A: `to_period("W")` zaradí každý timestamp do **týždenného intervalu** (bucketu) – napríklad všetky dátumy od pondelka 6.1.2020 do nedele 12.1.2020 dostanú rovnaký period. `.dt.start_time` vráti dátum **začiatku** tohto intervalu (pondelok), čo slúži ako jednotná reprezentácia daného týždňa pri agregácii.

**Q: Čo je `*kw_groups` pri volaní `scipy_stats.kruskal(*kw_groups)`?**

A: `*` je **unpacking operator** – rozbalí zoznam na samostatné argumenty. `kruskal()` prijíma ľubovoľný počet skupín ako pozicionálne argumenty: `kruskal(group1, group2, group3, ...)`. Keďže počet kategórií nie je dopredu známy, zoznam rozbalíme dynamicky.

**Q: Prečo sú `matplotlib` a `scipy` importované v `try/except` bloku?**

A: Skript je navrhnutý tak, aby fungoval aj v prostredí, kde tieto knižnice nie sú nainštalované – iba preskočí grafy alebo štatistické p-hodnoty. Globálne premenné `PLOT_AVAILABLE` a `SCIPY_AVAILABLE` sa nastavujú pri importe a ďalší kód podľa nich rozhoduje, čo vynechá.

**Q: Čo sú `COUNT_ANALYSES` a `CUSTOM_ANALYSES` a prečo sú to zoznamy slovníkov?**

A: Sú to **konfiguračné zoznamy** na vrchu súboru – miesto, kde sa definuje, čo a ako sa analyzuje, bez toho, aby sme menili logiku kódu. Každý slovník je jeden "recept" na analýzu: aký stĺpec, aký typ grafu, aký filter. Pridanie novej analýzy = pridanie nového slovníka do zoznamu. Funkcie `_process_count_analyses()`, `_process_custom_analysis()` a `make_overview_plot()` iterujú cez tieto zoznamy a každú definíciu automaticky spracujú.

---

### Otázky o výsledkoch a interpretácii

**Q: Aký je hlavný záver analýzy?**

A: Tri závery:
1. **Návštevnosť v čase** – žiadny štatisticky významný trend ($r_s = 0.109$, $p = 0.116$). Návštevnosť bankovej webstránky sa počas sledovaného obdobia systematicky nemenila.
2. **Kríza a obsah** – stredne silná závislosť ($V = 0.33$, $p \approx 0$). Počas krízového obdobia používatelia navštevujú iné kategórie obsahu ako v bežnom období.
3. **Čas na stránke podľa kategórie** – štatisticky významné rozdiely ($H = 491.58$, $p \approx 0$). Rôzne kategórie obsahu priťahujú rôzne dlhé návštevy.

**Q: Prečo je chi-kvadrát štatisticky významný, ale Spearman nie?**

A: Sú to rôzne testy, ktoré skúmajú rôzne vzťahy. Chi-kvadrát testuje závislosť medzi dvoma kategorickými premennými (`crisis` vs. `category`) – a závislosť tam je (stredná sila). Spearman testuje monotónny trend medzi poradím týždňa a počtom návštev – a tento trend je veľmi slabý a štatisticky nevýznamný. Fakt, že krízové obdobie ovplyvňuje kategórie, nehovorí nič o celkovom trende návštevnosti.

**Q: Čo by ste urobili ako ďalší krok po zistení štatisticky významného Kruskal-Wallis testu?**

A: Kruskal-Wallis hovorí, že **aspoň jedna** kategória sa líši, ale nehovorí **ktorá**. Ďalší krok by bol **post-hoc test** – napríklad Dunnov test (neparametrická verzia), ktorý porovná každú dvojicu kategórií a identifikuje, medzi ktorými pármi sú štatisticky významné rozdiely.
