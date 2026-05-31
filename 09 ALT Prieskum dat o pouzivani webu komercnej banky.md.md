# OBRANA SKRIPTU PODLA ZADANIA (MAPA: OTAZKA -> KDE V KODE)

Tento material je robeny presne na situaciu na skuske:
- ucitel da otazku zo zadania,
- ty ukazes presny riadok v kode,
- povies 1-2 vety co sa tam deje.

## 0. Co je zadanie
Subor zadania: task.txt

Zadanie ma 2 hlavne body:
1. Zahrnut aspon jednu premennu z kazdej skupiny premennych.
2. Analyzovat vybrane vztahy medzi premennymi.

Inspiracie v zadani:
- DV (obsah webu) odvodeny z URL
- IV (cas) odvodeny z casovej znamky
- trend navstevnosti v case + sila zavislosti
- cas straveny na stranke podla kategorii a obdobi

---

## 1. Najdolezitejsie "kotvy" v analyze_logs5.py

- Vyber stlpcov (premenne): analyze_logs5.py:67
- Zakladne analyzy (COUNT_ANALYSES): analyze_logs5.py:88
- Vlastne analyzy (CUSTOM_ANALYSES): analyze_logs5.py:110
- Chunk spracovanie CSV: analyze_logs5.py:353
- Statistiky (3 testy): analyze_logs5.py:443
- Ulozenie textoveho reportu: analyze_logs5.py:552
- Graficky vystup: analyze_logs5.py:738
- Hlavny orchestration flow: analyze_logs5.py:949

---

## 2. Priama mapa: bod zo zadania -> dokaz v kode

## Bod zadania A
"Zahrnte aspon jednu premennu z kazdej skupiny premennych"

### Co ukazat v kode
- analyze_logs5.py:67 (USECOLS)

### Co povedat
V USECOLS su pouzite premenne z viac skupin:
- Cas: unixTime, week, yearQuartal
- Obsah URL/DV: category, webPart, urlExt
- Pouzivatel/technicke: anonIP, agent, ipPart, userAgent
- Kontekst obdobia: crisis
- Spravanie: length

Tym je splneny bod "premenne z viac skupin".

## Bod zadania B
"Analyzujte vybrane vztahy medzi premennymi"

### Vztah 1: Cas -> navstevnost (trend)
- Priprava tyzdennych navstev: analyze_logs5.py:245
- Vypocet Spearman: analyze_logs5.py:459

Co povedat:
Sledujem, ci sa navstevnost meni v case. Tyzdne su IV, pocet navstev DV.

### Vztah 2: Obdobie crisis -> typ obsahu category
- Pocitanie dvojic (crisis, category): analyze_logs5.py:259
- Kontingencna tabulka + Chi2 + Cramer V: analyze_logs5.py:499

Co povedat:
Testujem, ci rozlozenie kategorii zavisi od krizoveho obdobia.

### Vztah 3: Kategoria + obdobie -> dlzka navstevy
- Zber vzoriek length podla category: analyze_logs5.py:276
- Kruskal-Wallis: analyze_logs5.py:539
- Custom analyzy pocas/mimo krizy: analyze_logs5.py:128 a analyze_logs5.py:137

Co povedat:
Testujem, ci sa cas na stranke statisticky lisi medzi kategoriami, a osobitne pocas/mimo krizy.

---

## 3. Co je IV a DV v tomto skripte

Podla inspiracie v zadani:

- IV (vysvetlujuce):
  - Casove: week/order tyzdna, yearQuartal, crisis
- DV (vysvetlovane):
  - Obsahove: category, webPart, urlExt
  - Spravanie: visits (pocet), length (cas na stranke)

Priklady z kodu:
- Spearman: IV = poradie tyzdna, DV = visits (analyze_logs5.py:468-469)
- Chi2: IV = crisis, DV = category (analyze_logs5.py:503-507)
- Kruskal: faktor = category, metrika = length (analyze_logs5.py:539)

---

## 4. 3 statisticke metody: kde sa pocitaju a co hovoria

## Spearmanova korelacia
- Kde: analyze_logs5.py:459-489
- Co testuje: monotonna zavislost medzi poradiom tyzdna a navstevnostou
- Vysledok:
  - spearman_r (sila + smer)
  - spearman_p (vyznamnost)

Interpretacia na skuske:
- p < 0.05 -> trend je vyznamny
- r > 0 -> rastuci trend
- r < 0 -> klesajuci trend

## Chi-kvadrat + Cramer V
- Kde: analyze_logs5.py:499-533
- Co testuje: zavislost medzi crisis a category
- Vysledok:
  - chi2_stat, chi2_p, chi2_dof
  - cramer_v (sila efektu)

Interpretacia na skuske:
- chi2_p < 0.05 -> zavislost je vyznamna
- Cramer V:
  - < 0.1 zanedbatelna
  - >= 0.1 mala
  - >= 0.3 stredna
  - >= 0.5 silna

## Kruskal-Wallis
- Kde: analyze_logs5.py:539-551
- Co testuje: rozdiely length medzi kategoriami
- Vysledok:
  - kruskal_h, kruskal_p

Interpretacia na skuske:
- p < 0.05 -> aspon jedna kategoria sa lisi

---

## 5. Co ukazat, ked sa ucitel pyta "ako to bezi"

Spustaci flow:
- __main__: analyze_logs5.py:997
- main: analyze_logs5.py:949

Poradie:
1. process_csv -> analyze_logs5.py:353
2. build_tables -> analyze_logs5.py:669
3. compute_statistics -> analyze_logs5.py:443
4. save_statistics -> analyze_logs5.py:552
5. make_overview_plot -> analyze_logs5.py:738

Jedna veta:
Skript najprv spracuje data po chunkoch, potom postavi tabulky, vypocita 3 testy, ulozi textovy report a nakresli graf.

---

## 6. Konkretne vystupy, ktore mas ukazat

- statistics.txt: analysis_output/statistics.txt
  - zapis sa robi tu: analyze_logs5.py:631

- overview.png: analysis_output/overview.png
  - ulozenie sa robi tu: analyze_logs5.py:924

---

## 7. Najcastejsie otazky od ucitela + presna odpoved

Otazka: "Kde je splnene, ze beries premenne z roznych skupin?"
Odpoved: "V USECOLS na analyze_logs5.py:67, su tam casove, obsahove, pouzivatelske aj behavioralne premenne."

Otazka: "Kde analyzujes vztah casu a navstevnosti?"
Odpoved: "Tyzdenne navstevy sa robia v _process_weekly_visits na analyze_logs5.py:245, statisticky test Spearman v compute_statistics na analyze_logs5.py:459."

Otazka: "Kde je zavislost medzi obdobim a obsahom webu?"
Odpoved: "Kombinacie crisis-category sa zbieraju v _process_chi2_counts na analyze_logs5.py:259 a testuju cez chi2 na analyze_logs5.py:520."

Otazka: "Kde mas cas na stranke podla kategorii a obdobi?"
Odpoved: "Custom analyzy avg_length_during_crisis a avg_length_normal su definovane na analyze_logs5.py:128 a analyze_logs5.py:137, samotny test rozdielov je Kruskal na analyze_logs5.py:547."

Otazka: "Preco chunky?"
Odpoved: "Aby skript nespadol na pamati pri velkom CSV. Chunk reader je v analyze_logs5.py:390 a cyklus je analyze_logs5.py:406."

---

## 8. 40-sekundovy text na ustnu obhajobu

"Zadanie som splnil tak, ze v USECOLS mam premenne z viac skupin: casove, obsahove z URL, pouzivatelske aj behavioralne. Data spracovavam po chunkoch v process_csv, kde agregujem navstevnost a vztahy medzi premennymi. Potom v compute_statistics pocitam tri testy: Spearman pre trend navstevnosti v case, Chi-kvadrat s Cramer V pre zavislost crisis a category a Kruskal-Wallis pre rozdiel dlzky navstevy medzi kategoriami. Vysledky ukladam do statistics.txt a grafov do overview.png."

---

## 9. Vysvetlene bloky kodu (priamo zo skriptu)

Toto je cast, ktoru vies doslova ukazovat na skuske.

## Blok A: hlavny pipeline v main
Miesto v kode: analyze_logs5.py:949

```python
results = process_csv(args.input, args.chunksize)
tables = build_tables(results)
stat_results = compute_statistics(results, tables)
save_statistics(stat_results, args.outdir)
make_overview_plot(args.outdir, tables, stat_results)
```

Co robi kazdy riadok:
1. process_csv: nacita CSV po chunkoch a vrati agregovane data do results.
2. build_tables: z agregacii spravi tabulky (DataFrame), ktore sa daju kreslit/testovat.
3. compute_statistics: vypocita Spearman, Chi2+CramerV, Kruskal.
4. save_statistics: ulozi textovy report statistics.txt.
5. make_overview_plot: ulozi overview.png s panelmi grafov.

Poznamka na obhajobu:
V komentaroch je pri kroku 3 stary text o Pearson/Welch, ale realne sa v kode pocita Spearman, Chi2 a Kruskal.

## Blok B: chunk citanie a spracovanie CSV
Miesto v kode: analyze_logs5.py:390 a analyze_logs5.py:406

```python
reader = pd.read_csv(
  input_path,
  sep=";",
  quotechar='"',
  usecols=USECOLS,
  chunksize=chunksize,
  low_memory=True,
)

for chunk in reader:
  total_rows += len(chunk)
  chunk = normalize_text_columns(chunk, text_columns)

  _process_unique_values(chunk, unique_ips, unique_agents, unique_ip_parts, unique_user_agents)
  _process_count_analyses(chunk, count_counters)
  _process_weekly_visits(chunk, visits_by_week)
  _process_chi2_counts(chunk, chi2_counter)
  _process_length_sample(chunk, length_sample_by_category)

  for analysis in CUSTOM_ANALYSES:
    _process_custom_analysis(chunk, analysis, results_counters)
```

Vysvetlenie:
1. read_csv s chunksize: data nejdu naraz do RAM, ale po kusoch.
2. normalize_text_columns: sjednoti prazdne a nejednotne textove hodnoty.
3. _process_unique_values: zbiera unikatne identifikatory.
4. _process_count_analyses: robi jednoduche pocty podla definovanych stlpcov.
5. _process_weekly_visits: robi navstevnost po tyzdnoch.
6. _process_chi2_counts: pripravuje podklady pre contingency tabulku crisis x category.
7. _process_length_sample: zbiera sample length pre Kruskal.
8. _process_custom_analysis: pocita custom analyzy definovane v CUSTOM_ANALYSES.

## Blok C: ako vznikne tyzdenna navstevnost
Miesto v kode: analyze_logs5.py:245

```python
unix_time = pd.to_numeric(chunk["unixTime"], errors="coerce")
timestamp = pd.to_datetime(unix_time, unit="s", errors="coerce", utc=True)
week_start = build_week_start(timestamp)

weekly_counts = week_start.value_counts(dropna=True)
for week_value, count in weekly_counts.items():
  visits_by_week[str(week_value.date())] += int(count)
```

Vysvetlenie:
1. unixTime sa prevedie na cislo.
2. cislo sa prevedie na UTC datetime.
3. datum sa zgrupuje na zaciatok tyzdna.
4. spocitaju sa pocty za kazdy tyzden.
5. pocty sa pripocitavaju do globalneho Countera visits_by_week.

## Blok D: priprava dat pre Chi-kvadrat
Miesto v kode: analyze_logs5.py:259

```python
counts = chunk.groupby(["crisis", "category"]).size()
for (crisis_val, cat_val), count in counts.items():
  chi2_counter[(str(crisis_val), str(cat_val))] += int(count)
```

Vysvetlenie:
1. groupby crisis+category spravi pocty pre kazdu kombinaciu.
2. kazda kombinacia sa pripocita do chi2_counter.
3. na konci celeho CSV mas kompletne contingency data na test zavislosti.

## Blok E: zber sample pre Kruskal
Miesto v kode: analyze_logs5.py:276

```python
length_series = pd.to_numeric(chunk["length"], errors="coerce")
valid_mask = length_series.notna()
if not valid_mask.any():
  return

valid_frame = chunk.loc[valid_mask, ["category"]].copy()
valid_frame["length"] = length_series.loc[valid_mask].to_numpy(dtype=float)

for cat_val, group in valid_frame.groupby("category"):
  current_count = len(length_sample_by_category[cat_val])
  if current_count >= MAX_SAMPLE_PER_CATEGORY:
    continue
  values = group["length"].to_numpy(dtype=float)
  space = MAX_SAMPLE_PER_CATEGORY - current_count
  length_sample_by_category[cat_val].extend(values[:space].tolist())
```

Vysvetlenie:
1. length sa konvertuje na cislo, nevalidne hodnoty vypadnu.
2. ostanu len validne riadky.
3. data sa rozdelia podla category.
4. pre kazdu kategoriu sa ulozi sample, ale max do limitu 5000.
5. limit chrani pamat a stabilitu skriptu.

## Blok F: Spearman v compute_statistics
Miesto v kode: analyze_logs5.py:459

```python
weekly_df = tables["weekly_df"]
n_weeks = len(weekly_df)

if n_weeks >= 3:
  week_rank = np.arange(n_weeks, dtype=float)
  visits    = weekly_df["visits"].to_numpy(dtype=float)

  if SCIPY_AVAILABLE:
    sp_result = scipy_stats.spearmanr(week_rank, visits)
    stat_results["spearman_r"] = float(sp_result.statistic)
    stat_results["spearman_p"] = float(sp_result.pvalue)
```

Vysvetlenie:
1. vezme sa tyzdenna tabulka a pocet tyzdnov.
2. ak su aspon 3 body, pripravi sa IV (poradie tyzdna) a DV (visits).
3. zavola sa Spearman a ulozi r + p.
4. bez scipy ide fallback cez ranky a corrcoef (nizsie v tom istom bloku).

## Blok G: Chi-kvadrat + Cramer V v compute_statistics
Miesto v kode: analyze_logs5.py:499

```python
chi2_counter = results["chi2_counter"]
crisis_vals   = sorted(set(k[0] for k in chi2_counter))
category_vals = sorted(set(k[1] for k in chi2_counter))

if len(crisis_vals) >= 2 and len(category_vals) >= 2 and SCIPY_AVAILABLE:
  crisis_idx   = {v: i for i, v in enumerate(crisis_vals)}
  category_idx = {v: i for i, v in enumerate(category_vals)}

  cont_table = np.zeros((len(crisis_vals), len(category_vals)), dtype=float)
  for (cv, catv), cnt in chi2_counter.items():
    cont_table[crisis_idx[cv], category_idx[catv]] = float(cnt)

  chi2_stat, chi2_p, chi2_dof, _ = scipy_stats.chi2_contingency(cont_table)

  n_total  = float(cont_table.sum())
  min_dim  = min(len(crisis_vals), len(category_vals)) - 1
  cramer_v = float(np.sqrt(chi2_stat / (n_total * min_dim))) if min_dim > 0 else float("nan")
```

Vysvetlenie:
1. z chi2_counter sa vytvoria unikatne riadky a stlpce contingency tabulky.
2. matica cont_table sa naplni poctami kombinacii.
3. chi2_contingency vrati chi2, p, dof.
4. z chi2 sa dopocita Cramer V ako sila efektu.

## Blok H: Kruskal-Wallis v compute_statistics
Miesto v kode: analyze_logs5.py:539

```python
kw_groups = [
  np.array(samples, dtype=float)
  for samples in results["length_sample_by_category"].values()
  if len(samples) >= 5
]

if len(kw_groups) >= 2 and SCIPY_AVAILABLE:
  h_stat, kw_p = scipy_stats.kruskal(*kw_groups)
  stat_results["kruskal_h"] = float(h_stat)
  stat_results["kruskal_p"] = float(kw_p)
```

Vysvetlenie:
1. pripravia sa skupiny length, kazda skupina = jedna category.
2. male skupiny (<5) sa vyhodia.
3. ak su aspon 2 skupiny, spusti sa Kruskal.
4. ulozi sa H statistika a p-hodnota.

## Blok I: ulozenie vysledkov do reportu
Miesto v kode: analyze_logs5.py:552

```python
output_text = "\n".join(lines)
output_path = outdir / "statistics.txt"
with open(output_path, "w", encoding="utf-8") as f:
  f.write(output_text)
```

Vysvetlenie:
1. najprv sa poskladaju textove riadky interpretacie.
2. urci sa cielovy subor statistics.txt.
3. report sa zapise na disk.

---

## 10. Statisticky dodatok na plnohodnotnu obhajobu

Tato cast je presne na otazky typu: "preco je to metodicky spravne".

## 10.1 Formalne hypotezy (H0/H1)

### Spearman (tyzden vs navstevnost)
- H0: neexistuje monotonna zavislost medzi poradim tyzdna a navstevnostou (rho = 0)
- H1: existuje monotonna zavislost (rho != 0)
- Kde v kode: analyze_logs5.py:459

### Chi-kvadrat (crisis vs category)
- H0: premenne crisis a category su nezavisle
- H1: crisis a category su zavisle
- Kde v kode: analyze_logs5.py:499

### Kruskal-Wallis (length medzi kategoriami)
- H0: rozdelenie/median length je rovnaky vo vsetkych kategoriach
- H1: aspon jedna kategoria sa lisi
- Kde v kode: analyze_logs5.py:539

## 10.2 Predpoklady testov a co na ne povedat

### Spearman
Predpoklady:
- data maju aspon ordinalny charakter,
- pozorovania su nezavisle,
- hladame monotonnost, nie nutne linearitu.

Co povedat ucitelovi:
"Volim Spearman, lebo navstevnost moze byt nelinearna a obsahovat outliery."

### Chi-kvadrat
Predpoklady:
- nezavisle pozorovania,
- primerane ocakavane frekvencie v bunkach kontingencnej tabulky.

Co povedat ucitelovi:
"Pri velmi malych expected bunkach moze byt chi2 menej stabilny. Preto pri interpretacii doplnam aj efektovu velkost Cramer V."

### Kruskal-Wallis
Predpoklady:
- nezavisle skupiny,
- aspon ordinalna metrika,
- test porovnava ranky, nie priame priemery.

Co povedat ucitelovi:
"Kruskal je vhodny, ked length nema normalne rozdelenie a su tam outliery."

## 10.3 Alfa hladina, p-hodnota, chyby testovania

V skripte sa pouziva hranica 0.05 pri interpretacii:
- p < 0.05 -> zamietam H0
- p >= 0.05 -> H0 nezamietam

Pozor pri obhajobe:
- p-hodnota nie je pravdepodobnost, ze H0 je pravda,
- je to pravdepodobnost vidiet tak extremne data, ak by H0 platila.

Chyby:
- Chyba I. druhu = zamietnem H0, aj ked je pravdiva
- Chyba II. druhu = nezamietnem H0, aj ked je nepravdiva

## 10.4 Efektova velkost (preco nestaci len p)

V skripte mas Cramer V:
- kde sa pocita: analyze_logs5.py:526
- kde sa interpretuje: analyze_logs5.py:606

Pre obhajobu:
"Pri velkych datasetoch moze byt aj slaby efekt statisticky vyznamny. Preto reportujem aj Cramer V, aby bolo jasne, aka silna je zavislost." 

## 10.5 Limity tvojej analyzy (povedz ich sam, je to plus)

1. Viacnasobne testovanie:
  - viac testov zvysuje riziko false positive
  - skript nerobi korekciu (napr. Bonferroni)

2. Kruskal je omnibus test:
  - povie, ze nejaky rozdiel je,
  - nepovie medzi ktorymi dvojicami kategorii

3. Sample limit pri length:
  - MAX_SAMPLE_PER_CATEGORY = 5000 (analyze_logs5.py:272)
  - je to kompromis medzi pamatou a presnostou

4. Spearman fallback bez scipy:
  - ak scipy chyba, p-hodnota pre Spearman je None
  - kde: analyze_logs5.py:477

## 10.6 Co by bol dalsi metodicky krok (ak sa ucitel pyta "a co dalej")

1. Po Kruskalovi urobit post-hoc test medzi dvojicami (napr. Dunn) + korekcia na viac porovnani.
2. Pri chi2 explicitne skontrolovat expected frekvencie a reportovat warning, ak su male.
3. Pri viac testoch aplikovat korekciu p-hodnot.
4. Dodat intervaly spolahlivosti alebo bootstrap pre klucove metriky.

## 10.7 Kratke odpovede na tvrde statisticke otazky

Otazka: "Preco nepouzivas Pearson?"
Odpoved: "Spearman je robustnejsi pri nelinearnych trendoch a outlieroch, co je pre webove logy realisticke."

Otazka: "Preco samotna p-hodnota nestaci?"
Odpoved: "P-hodnota hovori o vyznamnosti, nie o sile vztahu. Preto reportujem aj Cramer V."

Otazka: "Co znamena p >= 0.05?"
Odpoved: "Neznamena to, ze H0 je pravda. Znamena to, ze nemame dostatocny dokaz na jej zamietnutie pri zvolenej alfa hladine."

Otazka: "Preco je v Kruskalovi filter len na skupiny aspon 5?"
Odpoved: "Aby sme neporovnavali extremne male skupiny, ktore by boli nestabilne."
