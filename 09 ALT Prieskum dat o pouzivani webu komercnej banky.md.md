# Prieskum dat o pouzivani webu banky

---

## Co skript robi (podrobne)

### Zakladny problem, ktory skript riesi

Subor logs5.csv obsahuje 2 071 235 zaznamov navstev webu banky. Kazdy riadok je jedna navsteva, ale samotne riadky neodpovedaju na analyzne otazky.

Skript analyze.py tento problem riesi tak, ze surove logy transformuje na:

1. vycistene analyzne data,
2. agregovane tabulky,
3. statisticke testy vztahov,
4. textovy report,
5. graficke vystupy.

Prakticky: zo surovych pristupov robi obhajitelny analyzny vystup.

---

### Preco cistenie a agregacia, a nie priama analyza surovych riadkov

Surove logy maju nejednotne textove hodnoty (prazdne, -, NaN), mozne nevalidne cisla a casovu znamku, ktoru treba rozlozit na analyzne pouzitelne casove premenne.

Bez cistenia by:

- vznikali falosne pseudo-kategorie,
- testy padali na nevalidnych hodnotach,
- porovnanie trendov v case nebolo stabilne.

Agregacia (groupby, crosstab, weekly visits) je nevyhnutna, lebo testy Spearman/Chi-square/Kruskal nebezia nad lubovolnym surovym textom, ale nad pripravenymi strukturami.

---

### Vstup

Vstupom je subor logs5.csv so separatorom ;.

Pouzite premenne:

| Premenna | Skupina | Ucel |
|---|---|---|
| category, webPart, urlExt | DV (obsah) | analyza navstiveneho obsahu |
| year, quartal, yearQuartal, week, hour, dayofweek, crisis | IV (cas/obdobie) | analyza vyvoja a zavislosti |
| length | behavior | dlzka navstevy |
| internal | kontext | interny vs externy pristup |
| anonIP | identifikator | unikatni navstevnici |
| unixTime | technicka casova znamka | zdroj pre hour/dayofweek |

---

### Datova pipeline - co sa deje s kazdym zaznamom

```text
logs5.csv
   |
   +--> read_csv(usecols)
   |
   +--> normalizacia textu
   |      +--> prazdne/-/NaN -> UNKNOWN
   |
   +--> konverzia numeriky
   |      +--> nevalidne hodnoty -> NaN
   |
   +--> derivacia casu z unixTime
   |      +--> hour, dayofweek
   |
   +--> agregacie pre testy
   |      +--> weekly visits
   |      +--> crisis x category
   |      +--> groups length by category
   |
   +--> statisticke testy
   |      +--> Spearman
   |      +--> Chi-square + Cramer V
   |      +--> Kruskal-Wallis
   |
   +--> report + grafy
```

---

### Co je agregacia a preco je dolezita

Agregacia znamena, ze viac surovych riadkov spojime do zmysluplnej sumarnej formy.

Priklady v analyze.py:

- groupby(year, week).size() -> navstevnost po tyzdnoch
- crosstab(crisis, category) -> kontingencna tabulka pre Chi-square
- groupby(category) nad length -> skupiny pre Kruskal-Wallis

Bez tychto agregacii by nebolo mozne spravne interpretovat vztahy medzi premennymi.

---

### Tri rozne analyzne pohlady na tie iste data

Skript sa na data pozera troma sposobmi:

1. Trendovy pohlad: navstevnost v case (Spearman po rokoch)
2. Strukturalny pohlad: zmena zlozenia obsahu podla obdobia crisis (Chi-square + Cramer V)
3. Behavioralny pohlad: rozdiely dlzky navstevy medzi kategoriami (Kruskal-Wallis)

Kazdy pohlad odpoveda na inu analyticku otazku, ale spolu tvoria konzistentny prieskum.

---

### Co skript pocita

1. Pocet zaznamov a pocet unikatnych anonIP
2. Top category, top webPart, top urlExt
3. Spearmanovu korelaciu pre kazdy rok
4. Chi-square test pre crisis x category
5. Cramer V ako silu zavislosti
6. Kruskal-Wallis pre length medzi category
7. Vizualizacie navstevnosti a struktury

---

### Vystup

Vsetky vystupy sa ukladaju do analysis_output_simple.

| Subor | Obsah |
|---|---|
| report.txt | textovy sumar analyzy a testov |
| visits_by_yearquartal.png | vyvoj navstevnosti po yearQuartal |
| heatmap_day_hour.png | intenzita navstev podla hodina x den |
| heatmap_week_year.png | intenzita navstev podla tyzden x rok |
| top_category.png | najnavstevovanejsie kategorie |

### Struktura vystupneho reportu (priklad)

```text
1) PREMENNE V ANALYZE
2) ZAKLADNY PROFIL DAT
3) TOP OBSAH
4) SPEARMAN
5) CHI-SQUARE + CRAMER V
6) KRUSKAL-WALLIS
7) POZNAMKA K ZADANIU
```

---

## Vstupne a vystupne subory

```text
logs5.csv
   |
   +--> analyze.py
          |
          +--> analysis_output_simple/report.txt
          +--> analysis_output_simple/visits_by_yearquartal.png
          +--> analysis_output_simple/heatmap_day_hour.png
          +--> analysis_output_simple/heatmap_week_year.png
          +--> analysis_output_simple/top_category.png
```

---

## Postup riesenia - krok za krokom

### 1. Importy a fallback mechanizmus

```python
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

| Modul | Ucel |
|---|---|
| pandas | cistenie, agregacia, tabulky |
| numpy | ciselne operacie |
| scipy.stats | statisticke testy |
| matplotlib | grafy |

Fallback znamena, ze pri chybe kniznice skript neskonci okamzite, ale bezne casti vykona dalej.

---

### 2. Inicializacia argumentov

```python
parser.add_argument("--input", default=Path("logs5.csv"), type=Path)
parser.add_argument("--outdir", default=Path("analysis_output_simple"), type=Path)
```

Spustenie:

```bash
python analyze.py --input logs5.csv --outdir analysis_output_simple
```

Skript overi, ze input existuje a pripravi output priecinok.

---

### 3. Nacitanie dat

```python
df = pd.read_csv(
    input_path,
    sep=";",
    quotechar='"',
    usecols=USECOLS,
    low_memory=False,
)
```

Nacitavaju sa iba relevantne stlpce, aby bol beh cistejsi a rychlejsi.

---

### 4. Cistenie textu a cisel

Text:

```python
series.astype("string").fillna("UNKNOWN").replace({"": "UNKNOWN", "-": "UNKNOWN"})
```

Numerika:

```python
pd.to_numeric(df[col], errors="coerce")
```

Efekt:

- text ma jednotnu reprezentaciu,
- nevalidne cisla nesposobia pad,
- dalsie groupby/testy maju konzistentny vstup.

---

### 5. Derivacia casovych premennych z unixTime

```python
ts = pd.to_datetime(df["unixTime"], unit="s", errors="coerce", utc=True)
df["hour"] = ts.dt.hour
df["dayofweek"] = ts.dt.dayofweek
```

Tieto premenne sluzia ako IV pre temporalne analyzy.

---

### 6. Spearman po rokoch

Priprava:

```python
weekly = (
    df.dropna(subset=["year", "week"])
      .groupby(["year", "week"])
      .size()
      .reset_index(name="visits")
      .sort_values(["year", "week"])
)
```

Vypocet:

```python
x = np.arange(len(grp), dtype=float)
y = grp["visits"].to_numpy(dtype=float)
sp = scipy_stats.spearmanr(x, y)
```

Po rokoch sa testuje samostatne, aby sa nezmazali rozdielne trendy medzi rokmi.

---

### 7. Chi-square + Cramer V

Kontingencna tabulka:

```python
cont = pd.crosstab(chi_df["crisis"], chi_df["category"])
```

Test + efekt:

```python
chi2_stat, chi2_p, chi2_dof, _ = scipy_stats.chi2_contingency(cont.to_numpy(dtype=float))
n_total = float(cont.to_numpy(dtype=float).sum())
min_dim = min(cont.shape[0], cont.shape[1]) - 1
cramer_v = float(np.sqrt(chi2_stat / (n_total * min_dim)))
```

Chi-square hovori o vyznamnosti, Cramer V o sile zavislosti.

---

### 8. Kruskal-Wallis

Priprava skupin:

```python
for cat, grp in kr_df.groupby("category"):
    vals = grp["length"].to_numpy(dtype=float)
    if len(vals) >= 5:
        groups.append(vals)
```

Vypocet:

```python
h_stat, p_val = scipy_stats.kruskal(*groups)
```

Porovnava sa rozdiel dlzky navstevy medzi viacerymi kategoriami.

---

### 9. Ulozenie reportu

```python
report_path = outdir / "report.txt"
report_path.write_text("\n".join(lines), encoding="utf-8")
```

Report je pripraveny pre rychlu obhajobu bez nutnosti citat cely kod.

---

### 10. Vizualizacie

year x week heatmapa:

```python
pivot_wy = wy.groupby(["year", "week"]).size().unstack(fill_value=0)
pivot_wy = pivot_wy.reindex(columns=list(range(1, 54)), fill_value=0)
```

Grafy pomahaju vysvetlit vysledky intuitivnejsie ako samotne tabulky.

---

## Statisticke metody a vzorce

### 1. Spearmanova korelacia

$$
r_s = corr(rank(X), rank(Y))
$$

Hypotezy:

- H0: neexistuje monotonna zavislost
- H1: existuje monotonna zavislost

---

### 2. Chi-square test nezavislosti

$$
\chi^2 = \sum_i\sum_j \frac{(O_{ij}-E_{ij})^2}{E_{ij}}
$$

Hypotezy:

- H0: crisis a category su nezavisle
- H1: crisis a category su zavisle

---

### 3. Cramer V

$$
V = \sqrt{\frac{\chi^2}{n \cdot min(r-1, c-1)}}
$$

Interpretacia:

- okolo 0.1 slaby efekt
- okolo 0.3 stredny efekt
- okolo 0.5 silny efekt

---

### 4. Kruskal-Wallisov test

$$
H = \frac{12}{N(N+1)}\sum_{i=1}^{k}\frac{R_i^2}{n_i} - 3(N+1)
$$

Hypotezy:

- H0: skupiny sa nelisia
- H1: aspon jedna skupina sa lisi

---

## Vysvetlenie klucovych operacii v kode

### groupby(...).size()

Spocita pocet riadkov v skupinach.

### reset_index(name="visits")

Agregovany vysledok vrati do klasickeho DataFrame formatu.

### pd.crosstab(a, b)

Vytvori kontingencnu tabulku dvoch kategorickych premennych.

### unstack(fill_value=0)

Zmeni indexovu uroven na stlpce a pripravi data pre maticove zobrazenie.

### reindex(columns=range(1,54), fill_value=0)

Doplni chybajuce tyzdne tak, aby mali vsetky roky rovnaku os.

### dropna(subset=[...])

Vyhodi iba riadky, ktore su pre konkretny vypocet nepouzitelne.

---

## Code flow - diagram

```text
START
  |
  +--> parse args
  |
  +--> load_data
  |      +--> read_csv
  |      +--> normalize text
  |      +--> to_numeric
  |      +--> derive hour/dayofweek
  |
  +--> compute_statistics
  |      +--> Spearman
  |      +--> Chi-square + Cramer V
  |      +--> Kruskal-Wallis
  |
  +--> save_report
  |
  +--> make_plots
  |
 END
```

---

## Porovnanie pouzitych testov

| Test | Typ dat | Co overuje | Vystup |
|---|---|---|---|
| Spearman | poradia + numerika | trend navstevnosti v case | rho, p |
| Chi-square | kategoricke x kategoricke | zavislost crisis vs category | chi2, p, dof |
| Cramer V | efektova miera | sila zavislosti | V |
| Kruskal-Wallis | viac skupin numeriky | rozdiely length medzi category | H, p |

---

## Aktualne vysledky

### Zakladny profil

- pocet zaznamov: 2 071 235
- unikatnych anonymnych IP: 6 912

### Spearman po rokoch

- 2009: rho=-0.5621, p=1.1880e-05 (vyznamne)
- 2010: rho=-0.2473, p=7.4211e-02 (nevyznamne)
- 2011: rho=-0.6305, p=4.2064e-07 (vyznamne)
- 2012: rho=0.4378, p=1.0454e-03 (vyznamne)

### Chi-square + Cramer V

- chi2=225219.72
- df=5
- p=0.0000e+00
- V=0.3298

### Kruskal-Wallis

- H=13606.97
- p=0.0000e+00

Prakticky zaver:

- crisis a category su vyznamne zavisle,
- length sa medzi kategoriami vyznamne lisi,
- trend navstevnosti sa medzi rokmi meni.

Detailna interpretacia:

- Spearman: roky 2009 a 2011 maju vyznamny klesajuci trend, rok 2012 vyznamny rastuci trend, rok 2010 nema vyznamny trend.
- Chi-square + Cramer V: zavislost medzi crisis a category je velmi silno statisticky potvrdena, s prakticky strednou silou efektu (V=0.3298).
- Kruskal-Wallis: rozdiely v dlzke navstevy medzi kategoriami nie su nahodne, ale systematicke.

---

## Ako citat grafy pri obhajobe

### visits_by_yearquartal.png

- ukazuje dlhodoby vyvoj navstevnosti po kvartaloch,
- vhodny na komentar, ci sa navstevnost dlhodobo zvysuje, znizuje alebo kolise.

### heatmap_day_hour.png

- os X je hodina, os Y je den v tyzdni,
- tmavsia farba znamena vyssiu aktivitu,
- vhodna na rychlu identifikaciu casovych spiciek navstevnosti.

### heatmap_week_year.png

- os X je tyzden 1-53, os Y je rok,
- vhodna na porovnanie sezonnych vzorov medzi rokmi,
- odhali obdobia s neobvyklym poklesom alebo rastom.

### top_category.png

- rychly prehlad dominantnych kategorii obsahu,
- vhodny uvodny graf pri ustnej obhajobe.

---

## Otazky, ktore moze polozit profesor

Q: Preco Spearman a nie Pearson?

A: Spearman je vhodny na monotonne vztahy a je robustny pri nenormalnych datach.

Q: Preco Chi-square?

A: crisis aj category su kategoricke premenne.

Q: Naco je Cramer V?

A: Na silu efektu po Chi-square teste.

Q: Co dokazuje Kruskal-Wallis?

A: Ze aspon jedna kategoria ma inu distribuciu dlzky navstevy.

Q: Ako viem, ze zadanie je splnene?

A: Su zahrnute premenne z oboch skupin a testovane su viacere vztahy medzi nimi.

---

## Predpoklady testov a limity

### Spearman

- nevyzaduje normalitu,
- predpoklada monotonnost.

### Chi-square

- predpoklada nezavislost pozorovani,
- citlivy na male ocakavane pocetnosti.

### Kruskal-Wallis

- nevyzaduje normalitu,
- po vyznamnom vysledku je vhodny post-hoc test.

### Vseobecne limity

- observacne data nie su kauzalny dokaz,
- pri velkom N su p-hodnoty velmi citlive,
- efektove miery (Cramer V) su dolezite.

---

## Minimalny scenar na obhajobu (90 sekund)

1. Vybral som DV premenne obsahu a IV premenne casu.
2. Data som vycistil a z unixTime odvodil hour a dayofweek.
3. Otestoval som Spearman, Chi-square + Cramer V a Kruskal-Wallis.
4. Vysledky som ulozil do reportu a grafov.
5. Zaver: zadanie je splnene a vysledky su statisticky podlozene.

---

## Zhrnutie najdolezitejsich funkcii

| Funkcia / operacia | Modul | Ucel |
|---|---|---|
| pd.read_csv(..., usecols=...) | pandas | nacitanie iba potrebnych stlpcov |
| normalize_text(series) | vlastna funkcia | zjednotenie textu |
| pd.to_numeric(..., errors="coerce") | pandas | bezpecna konverzia na cisla |
| pd.to_datetime(..., unit="s") | pandas | prevod unixTime |
| groupby(...).size() | pandas | agregacia poctov |
| pd.crosstab(a, b) | pandas | kontingencna tabulka |
| scipy_stats.spearmanr(x, y) | scipy | Spearmanov test |
| scipy_stats.chi2_contingency(table) | scipy | Chi-square test |
| np.sqrt(chi2/(n*min_dim)) | numpy | Cramer V |
| scipy_stats.kruskal(*groups) | scipy | Kruskal-Wallis |
| Path.write_text(...) | pathlib | zapis reportu |

---

## Kontrolny zoznam pred odovzdanim

- skript bezi bez chyby
- vznikne analysis_output_simple/report.txt
- vzniknu 4 PNG grafy
- report obsahuje Spearman, Chi-square, Cramer V, Kruskal
- vies vysvetlit kazdy test aj graf

---

## Co doplnit pre este silnejsiu verziu

- post-hoc test po Kruskalovi (napr. Dunn), aby bolo jasne, ktore dvojice kategorii sa lisia,
- boxplot length podla category,
- samostatna analyza internal vs external,
- kratke prakticke odporucania pre banku z vysledkov analyzy.

---

## Exam mode - tahak (v tom istom subore)

### 1) Co je ciel zadania

- pouzit premenne z viac skupin,
- otestovat vztahy medzi premennymi.

V analyze.py je to splnene:

- DV: category, webPart, urlExt
- IV: year, quartal, yearQuartal, week, hour, dayofweek, crisis
- dalsie: length, internal, anonIP

### 2) Pipeline v 5 bodoch

1. Nacitanie CSV (iba potrebne stlpce)
2. Cistenie dat (text normalizacia, numerika cez coerce)
3. Derivacia hour/dayofweek z unixTime
4. Statistika (Spearman, Chi-square + Cramer V, Kruskal-Wallis)
5. Vystup (report.txt + 4 grafy)

### 3) Klucove testy

Spearman (trend navstevnosti):

- data: navstevy po year + week,
- testuje monotonnu zavislost navstevnosti v case,
- interpretacia: rho > 0 rast, rho < 0 pokles, p < 0.05 vyznamne.

Chi-square + Cramer V (crisis vs category):

- data: kontingencna tabulka crisis x category,
- Chi-square: ci existuje zavislost,
- Cramer V: aka je silna.

Kruskal-Wallis (length medzi category):

- data: skupiny length podla category,
- testuje, ci sa aspon jedna skupina lisi.

### 4) Realne vysledky, ktore mas povedat

- N = 2 071 235 zaznamov
- unikatnych anonIP = 6 912
- Spearman:
    - 2009: rho=-0.5621, p=1.1880e-05 (vyznamne)
    - 2010: rho=-0.2473, p=7.4211e-02 (nevyznamne)
    - 2011: rho=-0.6305, p=4.2064e-07 (vyznamne)
    - 2012: rho=0.4378, p=1.0454e-03 (vyznamne)
- Chi-square + Cramer V:
    - chi2=225219.72, df=5, p=0.0000e+00, V=0.3298
- Kruskal-Wallis:
    - H=13606.97, p=0.0000e+00

### 5) Jedna veta na zaver

Zadanie je splnene, lebo analyza obsahuje IV aj DV premenne, testuje viacero vztahov (trend, zavislost, rozdiely medzi skupinami) a vysledky su reportovane textom aj grafmi.

### 6) 30-sekundovy oral script

Vybral som DV premenne obsahu a IV premenne casu. Data som vycistil, z unixTime som odvodil hour a dayofweek a potom som otestoval tri vztahy: Spearman pre trend navstevnosti, Chi-square s Cramer V pre crisis vs category a Kruskal-Wallis pre length medzi kategoriami. Vysledky su v reporte a 4 grafoch. Zaver je, ze vztahy su statisticky vyznamne a analyza splna zadanie.

---

## 20 otazok a odpovedi na skusku (v tom istom subore)

1. Co bolo hlavne zadanie?
Pouzit premenne z viac skupin a analyzovat vztahy medzi premennymi.

2. Ktore premenne su DV?
category, webPart, urlExt (obsah webu).

3. Ktore premenne su IV?
year, quartal, yearQuartal, week, hour, dayofweek, crisis (cas a obdobie).

4. Naco sluzi length?
Je to behavior premenna, dlzka navstevy stranky.

5. Preco sa robi normalizacia textu?
Aby prazdne, -, NaN neboli tri rozne kategorie; vsetko ide na jednotne UNKNOWN.

6. Preco sa pouziva errors="coerce" pri numerike?
Nevalidne hodnoty sa zmenia na NaN, skript nespadne.

7. Ako vznikaju hour a dayofweek?
Z unixTime cez pd.to_datetime(..., unit="s", utc=True), potom dt.hour a dt.dayofweek.

8. Co znamena dayofweek = 0?
Pondelok.

9. Preco Spearman a nie Pearson?
Spearman testuje monotonne vztahy cez poradia a je robustnejsi pri nenormalnych datach.

10. Na com je Spearman pocitany?
Na pocte navstev po dvojici year + week, osobitne pre kazdy rok.

11. Co testuje Chi-square v tomto skripte?
Ci su crisis a category nezavisle alebo zavisle.

12. Co je Cramer V?
Efektova miera k Chi-square, hovori o sile zavislosti.

13. Ako citat Cramer V = 0.3298?
Priblizne stredne silna zavislost.

14. Preco Kruskal-Wallis?
Porovnava viac skupin length medzi kategoriami bez nutnosti normalneho rozdelenia.

15. Co znamena vyznamny Kruskal-Wallis?
Aspoň jedna kategoria sa lisi od ostatnych v distribucii length.

16. Co su hlavne vystupy skriptu?
report.txt a 4 grafy: visits_by_yearquartal, heatmap_day_hour, heatmap_week_year, top_category.

17. Co hovoria realne vysledky Spearman?
2009 a 2011 vyznamny pokles, 2012 vyznamny rast, 2010 nevyznamny trend.

18. Co hovori Chi-square vysledok p=0?
Zavislost crisis x category je statisticky vyznamna.

19. Co je hlavny limit analyzy?
Je to observacna analyza, nie experiment; vyznamnost nie je kauzalita.

20. Jedna veta na obhajobu?
Analyza splna zadanie, lebo pokryva DV aj IV premenne, overuje viacero vztahov troma statistickymi testami a vysledky prezentuje textovo aj graficky.
