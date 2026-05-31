# Prieskum Dat o Pouzivani Webu Banky - Studijny Material k analyze.py

---

## Co skript robi (podrobne)

### Zakladny problem, ktory skript riesi

Subor `logs5.csv` obsahuje viac ako 2 miliony zaznamov webovych pristupov. Kazdy riadok je jedna navsteva, ale samostatne riadky este nedavaju odpoved na analyticke otazky zo zadania.

Skript `analyze.py` riesi tento problem tak, ze surove logy transformuje na:

1. agregovane tabulky,
2. statisticke testy vztahov,
3. textovy report,
4. vizualizacie (grafy + heatmapy).

Teda: zo surovych dat vytvori obhajitelny analyticky vystup.

---

### Co presne treba splnit podla zadania

Zadanie chce:

- zahrnut aspon jednu premennu z kazdej skupiny,
- analyzovat vztahy medzi premennymi.

V skripte su zahrnute tieto skupiny:

- DV (obsah webu): `category`, `webPart`, `urlExt`
- IV (cas a obdobie): `year`, `quartal`, `yearQuartal`, `week`, `hour`, `dayofweek`, `crisis`
- doplnkove: `length`, `internal`, `anonIP`

Tym je formalna cast zadania splnena.

---

### Co je hlavny analyticky zmysel skriptu

Skript odpoveda na tri hlavne otazky:

1. Meni sa navstevnost v case? (Spearman)
2. Zavisi struktura obsahu (`category`) od krizoveho obdobia (`crisis`)? (Chi-square + Cramer V)
3. Lisi sa dlzka navstevy (`length`) medzi kategoriami obsahu? (Kruskal-Wallis)

Tieto tri otazky pokryvaju IV -> DV vztahy aj analyzu dlzky navstevy.

---

## Datovy tok (pipeline)

```text
logs5.csv
   |
   |-- build_arg_parser()
   |     |- spracovanie --input a --outdir
   |
   |-- load_data()
   |     |- read_csv(usecols=...)
   |     |- normalize_text() pre textove stlpce
   |     |- to_numeric() pre cisla
   |     |- hour, dayofweek z unixTime
   |
   |-- compute_statistics()
   |     |- Spearman po rokoch
   |     |- Chi-square + Cramer V (crisis x category)
   |     |- Kruskal-Wallis (length medzi category)
   |
   |-- save_report()
   |     |- report.txt
   |
   |-- make_plots()
         |- visits_by_yearquartal.png
         |- heatmap_day_hour.png
         |- heatmap_week_year.png
         |- top_category.png
```

---

## Vstup a vystupy

### Vstupny subor

| Subor | Typ | Popis |
|---|---|---|
| `logs5.csv` | CSV | webove logy banky, separator `;`, text v uvodzovkach `"` |

### Nacitavane stlpce (`USECOLS`)

| Stlpec | Ucel |
|---|---|
| `anonIP` | pocet unikatnych navstevnikov |
| `unixTime` | zdroj pre casove premenne |
| `year`, `quartal`, `yearQuartal`, `week` | casova os analyzy |
| `category`, `webPart`, `urlExt` | obsahove premenne (DV) |
| `length` | dlzka navstevy |
| `internal` | interny/externalny pristup |
| `crisis` | krizove vs nekrizove obdobie |

### Vystupne subory

| Subor | Co obsahuje |
|---|---|
| `analysis_output_simple/report.txt` | textovy sumar a vysledky testov |
| `analysis_output_simple/visits_by_yearquartal.png` | trend navstevnosti po kvartaloch |
| `analysis_output_simple/heatmap_day_hour.png` | aktivita hodina x den v tyzdni |
| `analysis_output_simple/heatmap_week_year.png` | aktivita tyzden x rok |
| `analysis_output_simple/top_category.png` | top kategorie navstevnosti |

---

## Postup riesenia - krok za krokom

### 1) Argumenty a spustenie

Skript sa spusta:

```bash
python analyze.py --input logs5.csv --outdir analysis_output_simple
```

Argumenty sa pripravia vo funkcii `build_arg_parser()`.

---

### 2) Nacitanie dat - `load_data()`

Zakladny kodovy blok:

```python
df = pd.read_csv(input_path, sep=";", quotechar='"', usecols=USECOLS, low_memory=False)
```

Potom nasleduju 3 klucove casti:

1. normalizacia textu,
2. konverzia numerickych stlpcov,
3. odvodenie casovych premennych.

#### 2.1 Normalizacia textu (`normalize_text`)

```python
series.astype("string").fillna("UNKNOWN").replace({"": "UNKNOWN", "-": "UNKNOWN"})
```

Preco:
- rovnaky stav "chybajucej" hodnoty sa nemoze tvarit ako 3 rozne hodnoty,
- zlepsuje kvalitu `groupby`, `value_counts`, `crosstab`.

#### 2.2 Konverzia cisiel (`pd.to_numeric`)

```python
pd.to_numeric(df[col], errors="coerce")
```

`errors="coerce"` znamena, ze nevalidna hodnota sa zmeni na `NaN`, aby kod nespadol.

#### 2.3 Derivacia hodin a dni

```python
ts = pd.to_datetime(df["unixTime"], unit="s", errors="coerce", utc=True)
df["hour"] = ts.dt.hour
df["dayofweek"] = ts.dt.dayofweek
```

`dayofweek` ma kodovanie 0=pondelok ... 6=nedela.

---

### 3) Statisticke testy - `compute_statistics()`

Funkcia vracia slovnik `stats` s tromi castami: `spearman_by_year`, `chi2`, `kruskal`.

#### 3.1 Spearman po rokoch

Pouzita logika:

```python
weekly = (
    df.dropna(subset=["year", "week"])
      .groupby(["year", "week"])
      .size()
      .reset_index(name="visits")
      .sort_values(["year", "week"])
)
```

Potom sa pre kazdy rok pocita:

```python
x = np.arange(len(grp), dtype=float)
y = grp["visits"].to_numpy(dtype=float)
scipy_stats.spearmanr(x, y)
```

Dolezite:
- analyza je po rokoch, nie jedna hodnota za cele obdobie,
- to odhali, ci ma kazdy rok iny trend.

#### 3.2 Chi-square + Cramer V

Kontingencna tabulka:

```python
cont = pd.crosstab(chi_df["crisis"], chi_df["category"])
```

Test:

```python
chi2_stat, chi2_p, chi2_dof, _ = scipy_stats.chi2_contingency(cont.to_numpy(dtype=float))
```

Sila efektu:

```python
cramer_v = np.sqrt(chi2_stat / (n_total * min_dim))
```

kde `min_dim = min(pocet_riadkov, pocet_stlpcov) - 1`.

#### 3.3 Kruskal-Wallis

Skupiny sa tvoria podla `category`:

```python
for cat, grp in kr_df.groupby("category"):
    vals = grp["length"].to_numpy(dtype=float)
    if len(vals) >= 5:
        groups.append(vals)
```

Test:

```python
h_stat, p_val = scipy_stats.kruskal(*groups)
```

Filter `len(vals) >= 5` obmedzi nestabilne mini-skupiny.

---

### 4) Report - `save_report()`

Report uklada:

- profil datasetu (pocet zaznamov, unikatne IP),
- top hodnoty DV (`category`, `webPart`, `urlExt`),
- vysledky Spearman/Chi-square/Kruskal,
- kratke slovne zavery.

Vystup je `analysis_output_simple/report.txt`.

---

### 5) Vizualizacie - `make_plots()`

Skript kresli 4 grafy:

1. line chart `visits_by_yearquartal.png`,
2. heatmap `heatmap_day_hour.png`,
3. heatmap `heatmap_week_year.png`,
4. horizontal bar `top_category.png`.

Heatmapa tyzden x rok pouziva pivot:

```python
pivot_wy = wy.groupby(["year", "week"]).size().unstack(fill_value=0)
pivot_wy = pivot_wy.reindex(columns=list(range(1, 54)), fill_value=0)
```

Dolezite:
- `unstack` premeni dvojity index na maticu,
- `reindex(1..53)` zarovna osi tyzdnov medzi rokmi.

---

## Matematicke metody a vzorce

### 1) Spearmanova korelacia

$$
r_s = corr(rank(X), rank(Y))
$$

- $X$: poradie tyzdna,
- $Y$: pocet navstev.

Hypotezy:
- $H_0$: monotonna zavislost neexistuje,
- $H_1$: monotonna zavislost existuje.

Rozhodnutie: ak $p < 0.05$, zamietame $H_0$.

---

### 2) Chi-square test nezavislosti

$$
\chi^2 = \sum_i\sum_j \frac{(O_{ij} - E_{ij})^2}{E_{ij}}
$$

- $O_{ij}$: pozorovana pocetnost,
- $E_{ij}$: ocakavana pocetnost pri nezavislosti.

Hypotezy:
- $H_0$: `crisis` a `category` su nezavisle,
- $H_1$: su zavisle.

---

### 3) Cramer V (sila vztahu)

$$
V = \sqrt{\frac{\chi^2}{n \cdot min(r-1, c-1)}}
$$

- $n$: velkost vzorky,
- $r, c$: rozmery kontingencnej tabulky.

Orientacna interpretacia:
- okolo 0.1 slaba,
- okolo 0.3 stredna,
- okolo 0.5 silna zavislost.

---

### 4) Kruskal-Wallis

$$
H = \frac{12}{N(N+1)}\sum_{i=1}^{k}\frac{R_i^2}{n_i} - 3(N+1)
$$

- $R_i$: suma poradi v skupine,
- $n_i$: velkost skupiny,
- $N$: celkovy pocet pozorovani.

Hypotezy:
- $H_0$: skupiny maju rovnake mediany/rozdelenie,
- $H_1$: aspon jedna skupina sa lisi.

---

## Aktualne vysledky (z reportu)

Aktualny beh vratil:

- pocet zaznamov: 2 071 235,
- unikatnych anonymnych IP: 6 912,
- Spearman:
  - 2009: rho=-0.5621, p=1.1880e-05 (vyznamne)
  - 2010: rho=-0.2473, p=7.4211e-02 (nevyznamne)
  - 2011: rho=-0.6305, p=4.2064e-07 (vyznamne)
  - 2012: rho=0.4378, p=1.0454e-03 (vyznamne)
- Chi-square + Cramer V:
  - chi2=225219.72, df=5, p=0.0000e+00, V=0.3298
- Kruskal-Wallis:
  - H=13606.97, p=0.0000e+00

Prakticky zaver:
- vztah `crisis` -> `category` je statisticky vyznamny a stredne silny,
- dlzka navstevy sa medzi kategoriami vyznamne lisi,
- trend navstevnosti sa medzi rokmi meni (nie je jednotny).

---

## Ako citat grafy pri obhajobe

### `visits_by_yearquartal.png`
- ukazuje dlhodoby vyvoj navstevnosti po kvartaloch,
- vhodny na komentar rast/pokles v case.

### `heatmap_day_hour.png`
- os X: hodina (0-23), os Y: den v tyzdni (0-6),
- intenzita farby = pocet navstev.

### `heatmap_week_year.png`
- os X: tyzden (1-53), os Y: rok,
- dobre odhali sezonnost a anomalie medzi rokmi.

### `top_category.png`
- poradie najnavstevovanejsich kategorii,
- rychly prehlad dominantneho obsahu.

---

## Vysvetlenie klucovych pandas operacii (ako v example style)

### `groupby(...).size()`

Vrati pocet riadkov v kazdej skupine.
Priklad: `(year, week) -> visits`.

### `reset_index(name="visits")`

Prevedie vysledok z indexovej formy na klasicky DataFrame so stlpcom `visits`.

### `pd.crosstab(a, b)`

Vytvori kontingencnu tabulku kategorickych premennych.
Presne to treba pre Chi-square.

### `unstack(fill_value=0)`

Jednu uroven indexu premeni na stlpce a vznikne matica vhodna na heatmapu.

### `dropna(subset=[...])`

Odstrani len tie riadky, ktore maju `NaN` v relevantnych stlpcoch testu.

---

## Predpoklady testov a limity (silna obhajoba)

### Spearman
- predpoklada monotonne spravanie,
- je robustny na odlahle hodnoty,
- netreba normalitu.

### Chi-square
- ocakavane pocetnosti by nemali byt prilis male,
- pozorovania by mali byt nezavisle.

### Kruskal-Wallis
- porovnava skupiny cez poradia,
- netreba normalne rozdelenie,
- pri vyznamnom vysledku sam o sebe nehovori, ktore dvojice skupin sa lisia (na to je post-hoc test).

### Vseobecne limity
- ide o observacne logy -> korelacia nie je kauzalita,
- pri velkom N je lahko dosiahnut statisticku vyznamnost aj pri mensom praktickom efekte,
- vhodne je doplnit aj efektove miery a prakticku interpretaciu.

---

## Minimalny scenar na obhajobu (90 sekund)

1. Zo zadania som vybral DV a IV premenne.
2. Data som vycistil a z `unixTime` som odvodil `hour` a `dayofweek`.
3. Otestoval som tri klucove vztahy:
   - Spearman pre trend navstevnosti v case,
   - Chi-square + Cramer V pre `crisis` vs `category`,
   - Kruskal-Wallis pre `length` medzi kategoriami.
4. Vysledky som reportoval textom aj grafmi.
5. Zaver: zadanie je splnene, vztahy su statisticky potvrdene a interpretovane.

---

## Typicke otazky na skuske (kratke odpovede)

Prečo Spearman a nie Pearson?
- Spearman testuje monotonne vztahy cez poradia a je odolnejsi pri nenormalnych datach.

Preco Chi-square?
- lebo `crisis` aj `category` su kategoricke premenne.

Preco Cramer V?
- povie silu vztahu po tom, co Chi-square potvrdi jeho existenciu.

Preco Kruskal-Wallis?
- porovnava viac skupin bez predpokladu normality.

Ako dokazem splnenie zadania?
- mam DV aj IV premenne a tri analyzovane vztahy medzi nimi.

---

## Kontrolny zoznam pred odovzdanim

- skript prejde bez chyby,
- vznika `report.txt`,
- vznika 4x PNG,
- report obsahuje Spearman, Chi-square, Cramer V, Kruskal,
- vies povedat slovny zaver pre kazdy test.

---

## Co doplnit, ak budes chciet este silnejsiu verziu

- boxplot `length` podla `category`,
- histogram a Q-Q plot `length`,
- post-hoc porovnania po Kruskal teste,
- doplnit intervaly spolahlivosti a robustne efektove miery.
