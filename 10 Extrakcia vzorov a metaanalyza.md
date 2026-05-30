# Kvartálna asociačná a sekvenčná analýza webového logu banky (logs5.csv)

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Banka zaznamenávala správanie návštevníkov svojho webu počas rokov 2009 – 2012 – teda v období finančnej krízy (2009–2010) aj po nej (2011–2012). Každý riadok v logu hovorí: _kedy_, _kto_ (relácia/frame) a _čo_ navštívil (kategória stránky / podčasť webu).

Skript sa pýta: **Zmenilo sa správanie návštevníkov medzi krízou a post-krízou?** Odpovedá tak, že:

1. Rozdelí dáta na **16 kvartálov** (09Q1 – 12Q4)
2. Z každého kvartálu vyťaží **asociačné a sekvenčné pravidlá** (vzory)
3. Zostaví **dátovú maticu vzory × kvartály** (0/1 – vzor bol/nebol prítomný)
4. Testuje štatisticky, či sa vzory medzi kvartálmi líšia (**Cochran Q**) a do akej miery sú konzistentné (**Kendallovo W**)

---

## Vstupné a výstupné súbory

```
logs5.csv
    │
    └──► logs5_analysis.py
              │
              ├── analysis_outputs/
              │       ├── period_summary.csv
              │       ├── period_top_rules_assoc_cat.csv
              │       ├── period_top_rules_assoc_web.csv
              │       ├── period_top_rules_seq_cat.csv
              │       ├── period_top_rules_seq_web.csv
              │       ├── pattern_matrix_binary_assoc_cat.csv   (a ďalšie 3)
              │       ├── pattern_matrix_support_assoc_cat.csv  (a ďalšie 3)
              │       ├── pattern_recurrence_assoc_cat.csv      (a ďalšie 3)
              │       ├── summary.txt
              │       └── plots/
              │               ├── assoc_cat_binary_heatmap.png
              │               ├── assoc_web_binary_heatmap.png
              │               ├── seq_cat_binary_heatmap.png
              │               ├── seq_web_binary_heatmap.png
              │               ├── assoc_cat_recurrence.png
              │               ├── ...
              │               └── rule_counts_per_period.png
```

### Štruktúra `logs5.csv`

Oddeľovač: `;`

| Stĺpec | Typ | Popis |
|---|---|---|
| `frame` | int | ID relácie (session) – jeden používateľ, jedna návšteva |
| `yearQuartal` | string | Kvartál vo formáte `09Q1`, `10Q3`, atď. |
| `category` | string | Kategória stránky (napr. `Reputation`, `Pricing List`) |
| `webPart` | string | Podčasť webu (napr. `Awards`, `Rating`, `History`) |
| `unixTime` | int | Unix timestamp – čas kliknutia (na zoradenie v rámci relácie) |

---

## Code flow – diagram

```
START
  │
  ├─► load_dataframe()
  │     ├─ Načíta len potrebné stĺpce (usecols)
  │     ├─ Prevedie frame + unixTime na int64
  │     └─ Vymaže riadky s chýbajúcimi hodnotami
  │
  ├─► analyze_all_periods()
  │     └─► pre každý kvartál (09Q1 ... 12Q4):
  │           └─► analyze_one_period()
  │                 ├─► build_transactions_for_period()   → množiny pre Apriori
  │                 ├─► mine_apriori_rules()              → asociačné pravidlá
  │                 ├─► format_apriori_rules()            → čistá tabuľka
  │                 ├─► build_sequences_for_period()      → zoradené sekvencie
  │                 └─► mine_sequence_rules()             → sekvenčné pravidlá
  │
  ├─► plot_all_outputs()
  │     ├─► build_binary_matrix()  → matica 0/1
  │     ├─► plot_binary_heatmap()  → PNG heatmapy
  │     └─► plot_recurrence_histogram() + plot_period_rule_counts()
  │
  └─► write_all_outputs()
        ├─► build_binary_matrix() + build_support_matrix()  → CSV matice
        ├─► cochran_q_test()       → Cochran Q
        ├─► kendalls_w()           → Kendallovo W
        └─► summary.txt            → report s výsledkami
```

---

## Postup riešenia krok za krokom

### Krok 1 – Načítanie a čistenie dát (`load_dataframe`)

```python
usecols = [frame_col, period_col, action_col_cat, action_col_web, unix_col]

df = pd.read_csv(input_path, sep=";", usecols=usecols,
                 dtype="string", low_memory=False)

df[frame_col] = pd.to_numeric(df[frame_col], errors="coerce")
df[unix_col]  = pd.to_numeric(df[unix_col],  errors="coerce")
df = df.dropna(subset=[frame_col, period_col, action_col_cat,
                        action_col_web, unix_col])
```

- `usecols` – načítame len stĺpce, ktoré naozaj potrebujeme (šetrí RAM)
- `dtype="string"` – bezpečné čítanie; čísla prevedieme explicitne neskôr
- `errors="coerce"` – neplatné hodnoty (text v číselnom stĺpci) sa nahradia `NaN`
- `dropna` – vyhodíme riadky kde čokoľvek chýba

**Výsledok po čistení:** ~1 957 000 riadkov (závisí od verzie CSV)

---

### Krok 2 – Zoradenie kvartálov (`period_sort_key`)

```python
def period_sort_key(period_label):
    match = re.fullmatch(r"(\d{2,4})Q([1-4])", str(period_label).strip())
    year    = int(match.group(1)) + 2000   # 09 → 2009
    quarter = int(match.group(2))
    return (year, quarter)
```

Regex `(\d{2,4})Q([1-4])` rozloží napr. `"10Q3"` na rok `10` a kvartál `3`.
Funkcia `sorted(..., key=period_sort_key)` zoradí 16 kvartálov chronologicky: `09Q1, 09Q2, ..., 12Q4`.

**Rozdelenie na epochy:**

| Epocha | Kvartály | Počet |
|---|---|---|
| Krízové (2009 – 2010) | 09Q1, 09Q2, 09Q3, 09Q4, 10Q1, 10Q2, 10Q3, 10Q4 | 8 |
| Post-krízové (2011 – 2012) | 11Q1, 11Q2, 11Q3, 11Q4, 12Q1, 12Q2, 12Q3, 12Q4 | 8 |

---

### Krok 3 – Asociačná analýza (Apriori)

#### 3a – Zostavenie transakcií (`build_transactions_for_period`)

```python
for frame_id, group_df in period_df.groupby(frame_col):
    items = list(group_df[action_col].unique())   # množina stránok v relácii
    if len(items) >= 1:
        transactions.append(items)
```

**Transakcia = množina unikátnych stránok navštívených v jednej relácii.**

Príklad:
```
Relácia 7843: [Reputation, Pricing List, Pillar3 related]
Relácia 7844: [Pricing List, Pricing List, Pricing List]  →  [Pricing List]
Relácia 7845: [We support.., Reputation, Pillar3 related]
```

Na poradí nezáleží (oproti sekvenčnej analýze).

#### 3b – Apriori algoritmus (`run_apriori`)

Algoritmus prechádza transakcie a hľadá **frekventované množiny položiek** (itemsety) – teda kombinácie stránok, ktoré sa spolu vyskytujú v dostatočnom počte relácií.

```python
encoder = TransactionEncoder()
encoded_array = encoder.fit_transform(transactions)
df_encoded = pd.DataFrame(encoded_array, columns=encoder.columns_)

frequent = apriori(df_encoded, min_support=min_support, use_colnames=True)
rules = association_rules(frequent, metric="confidence",
                          min_threshold=min_confidence,
                          num_itemsets=len(frequent))
rules = rules[rules["lift"] >= min_lift]
```

- `TransactionEncoder` prevedie zoznam zoznamov na binárnu maticu (riadok = relácia, stĺpec = položka, hodnota = True/False)
- `apriori(...)` nájde všetky frekventované itemsety (množiny, ktorých support ≥ `min_support`)
- `association_rules(...)` z itemsetov vygeneruje pravidlá tvaru `A ⟹ B`

#### 3c – Automatické znižovanie support-u (`mine_apriori_rules`)

```python
current_support = initial_support
while current_support >= support_min:
    rules_df = run_apriori(transactions, current_support, ...)
    if not rules_df.empty and len(rules_df) >= min_rules_required:
        return rules_df, current_support
    current_support = round(current_support - support_step, 4)
```

Ak má kvartal málo transakcií a nezískami aspoň 10 pravidiel pri nastavenom `initial_support`, skript automaticky zníži support o `support_step = 0.01` a skúsi znova. Minimálna hranica je `0.01`.

**Nastavenia podľa stĺpca:**

| Stĺpec | `min_support` | `min_confidence` | `min_lift` | `max_len` |
|---|---|---|---|---|
| `category` | 0.05 | 0.50 | 1.0 | bez obmedzenia |
| `webPart` | 0.10 | 0.70 | 1.0 | 3 |

---

### Krok 4 – Sekvenčná analýza (AprioriAll – vlastná implementácia)

#### 4a – Zostavenie sekvencií (`build_sequences_for_period`)

```python
sorted_df = period_df.sort_values([frame_col, unix_col])
for frame_id, group_df in sorted_df.groupby(frame_col):
    seq = group_df[action_col].tolist()   # ZORADENÁ sekvencia
    if len(seq) >= 2:
        sequences.append(seq)
```

Na rozdiel od Apriori tu **záleží na poradí**. Stránky sú zoradené podľa `unixTime`.

Príklad:
```
Relácia 7843, zoradená: [Reputation, Pillar3 related, Pricing List]
               prechody: Reputation→Pillar3 related, Pillar3 related→Pricing List
```

#### 4b – Výpočet sekvenčných pravidiel (`mine_sequence_rules`)

```python
for seq in sequences:
    seen_actions = set(seq)
    for action in seen_actions:
        action_count[action] += 1          # v koľkých reláciách sa A vyskytlo

    seen_rules = set()
    for i in range(len(seq) - 1):
        seen_rules.add((seq[i], seq[i + 1]))   # unikátne prechody A→B
    for rule in seen_rules:
        rule_count[rule] += 1             # v koľkých reláciách bol prechod A→B
```

- Počítame na úrovni **relácií** (nie kliknutí), aby jeden dlhý log neovplyvnil výsledok
- `seen_rules = set()` zaručí, že každý prechod počítame v reláciu **najviac raz**

---

### Krok 5 – Dátová matica vzory × kvartály (`build_binary_matrix`)

```python
matrix = pd.DataFrame(0, index=all_patterns, columns=period_labels, dtype=int)

for period in period_labels:
    for val in results[period][rule_type][col_key]:
        matrix.loc[str(val), period] = 1
```

- Riadky = unikátne pravidlá naprieč všetkými kvartálmi (napr. `"We support.. => Reputation"`)
- Stĺpce = 16 kvartálov (`09Q1` – `12Q4`)
- Hodnota = 1 ak pravidlo bolo nájdené v tomto kvartáli, 0 ak nie

Príklad (skrátený):

| Vzor | 09Q1 | 09Q2 | ... | 12Q4 |
|---|---|---|---|---|
| `We support.. => Reputation` | 1 | 1 | ... | 0 |
| `Pricing List => Pricing List` | 1 | 1 | ... | 1 |
| `History, Rating => Awards` | 0 | 1 | ... | 1 |

---

### Krok 6 – Štatistické testy

Pozri sekciu **Štatistické metódy a vzorce** nižšie.

---

### Krok 7 – Vizualizácia (heatmapy + histogramy)

- **Binárna heatmapa** – riadky = vzory (zoradené od najstabilnejšieho), stĺpce = kvartály, farba = prítomnosť
- **Červená prerušovaná čiara** – hranica krízového/post-krízového obdobia (pred `11Q1`)
- **Histogram opakovania** – os X = počet kvartálov kde sa vzor vyskytol, os Y = počet takých vzorov

---

## Štatistické metódy a vzorce

### 1. Support (podpora)

$$
\text{support}(A) = \frac{\text{počet relácií obsahujúcich } A}{\text{celkový počet relácií}}
$$

$$
\text{support}(A \Rightarrow B) = \text{support}(A \cup B) = \frac{|\{t \in T : A \subseteq t \wedge B \subseteq t\}|}{|T|}
$$

- Hovorí, aká veľká časť relácií obsahuje daný itemset / prechod
- Pohybuje sa v rozsahu $[0, 1]$
- Príklad: `We support.. => Reputation`, support = 0.0749 v 09Q1 → pravidlo sa nachádza v ~7.5 % relácií

**Pre sekvenčné pravidlá:**

$$
\text{support}(A \to B) = \frac{\text{počet relácií kde prechod } A \to B \text{ nastáva aspoň raz}}{|T|}
$$

---

### 2. Confidence (spoľahlivosť)

$$
\text{confidence}(A \Rightarrow B) = \frac{\text{support}(A \cup B)}{\text{support}(A)} = \frac{|\{t : A \subseteq t \wedge B \subseteq t\}|}{|\{t : A \subseteq t\}|}
$$

- Pravdepodobnosť, že relácia obsahuje B za podmienky, že obsahuje A
- Pohybuje sa v rozsahu $[0, 1]$
- Príklad: `We support.. => Reputation`, confidence = 0.735 → ak relácia obsahuje stránku "We support..", v 73.5 % prípadov obsahuje aj "Reputation"

---

### 3. Lift (zdvihnutie)

$$
\text{lift}(A \Rightarrow B) = \frac{\text{confidence}(A \Rightarrow B)}{\text{support}(B)} = \frac{\text{support}(A \cup B)}{\text{support}(A) \cdot \text{support}(B)}
$$

- Meria, o koľko je výskyt B v relácii pravdepodobnejší, ak vie že relácia obsahuje A, oproti náhodnej relácii
- $\text{lift} = 1$ → A a B sú nezávislé
- $\text{lift} > 1$ → pozitívna korelácia (A pomáha predpovedať B)
- $\text{lift} < 1$ → negatívna korelácia
- Príklad: `We support.. => Reputation`, lift = 3.02 → spolu sa vyskytujú 3× častejšie, ako by sa dalo očakávať náhodou

---

### 4. Apriori algoritmus

**Kľúčová vlastnosť (Apriori princíp / monotónnosť support-u):**

> Ak itemset `{A, B}` má support < prahová hodnota, potom **každý nadset** `{A, B, C}` tiež nebude spĺňať prahovú hodnotu.

Vďaka tomu môžeme **odstrihávať** veľké vetvy prehľadávacieho priestoru bez ich vyhodnocovania.

**Postup Apriori:**

```
1. Nájdi všetky frekventované 1-itemsety {A}, {B}, {C}, ...
2. Z frekventovaných 1-itemsetov zostav kandidátne 2-itemsety {A,B}, {A,C}, ...
3. Otestuj support každého kandidátneho 2-itemsetu – vyraď tie pod prahom
4. Opakuj pre 3-itemsety, 4-itemsety, ... (kým sú frekventované itemsety)
5. Z frekventovaných itemsetov generuj pravidlá A ⟹ B kde confidence ≥ prah
```

**Zložitosť:** Exponenciálna v najhoršom prípade, ale Apriori princíp ju dramaticky znižuje v praxi.

**Vstup do skriptu:** 33 587 relácií (09Q1) s ~5–15 stránkami v každej.

---

### 5. AprioriAll – sekvenčné pravidlá (vlastná implementácia)

Skript implementuje **zjednodušenú variantu** – iba pravidlá tvaru $A \to B$ (dvojice sú za sebou idúce).

```
Pre každú reláciu (zoradenú podľa unixTime):
    Pre každý pár po sebe idúcich stránok (A, B) v reláciu:
        rule_count[(A, B)] += 1   (ak ešte nebol v tejto relácii)
        action_count[A]   += 1   (ak ešte nebol v tejto relácii)
```

Zavedieme skrátené značky (zodpovedajú premenným v kóde):
- $c_{AB}$ = počet relácií kde prechod $A \to B$ nastáva
- $c_A$ = počet relácií kde sa vyskytuje $A$
- $c_B$ = počet relácií kde sa vyskytuje $B$

$$
\text{support}(A \to B) = \frac{c_{AB}}{|T|}
$$

$$
\text{confidence}(A \to B) = \frac{c_{AB}}{c_A}
$$

$$
\text{lift}(A \to B) = \frac{\text{confidence}(A \to B)}{c_B / |T|}
$$

**Príklad zo skutočných dát (09Q1, category):**

| Pravidlo | Support | Confidence | Lift |
|---|---|---|---|
| `Pricing List => Pricing List` | 0.512 | 0.815 | 1.297 |
| `Pillar3 related => Pillar3 related` | 0.206 | 0.633 | 1.951 |
| `Reputation => Pillar3 related` | 0.140 | 0.626 | 1.928 |

Pravidlo `Pricing List => Pricing List` znamená: v 81.5 % relácií kde sa vyskytla stránka Pricing List, sa tam vyskytla znova – t.j. používateľ navštívil tú istú stránku viackrát počas jednej relácie.

---

### 6. Cochran Q Test

**Čo testuje:** Či sa proporcia prítomnosti vzorov **štatisticky líši** medzi kvartálmi.

**H₀:** Pravdepodobnosť prítomnosti vzoru je rovnaká vo všetkých kvartáloch (žiadna zmena).

**H₁:** Aspoň jeden kvartál sa líši od ostatných.

**Vstup:** Binárna matica $X$ rozmeru $(k \times n)$:
- $k$ = počet kvartálov (u nás 16)
- $n$ = počet unikátnych vzorov

**Výpočet:**

$$
Q = (k - 1) \cdot \frac{k \sum_{j=1}^{k} C_j^2 - \left(\sum_{j=1}^{k} C_j\right)^2}{k \sum_{i=1}^{n} R_i - \sum_{i=1}^{n} R_i^2}
$$

kde:
- $C_j$ = súčet stĺpca $j$ (počet vzorov prítomných v kvartáli $j$)
- $R_i$ = súčet riadku $i$ (počet kvartálov kde je vzor $i$ prítomný)
- $k$ = počet kvartálov = 16

**Distribúcia:** Pod $H_0$ sa $Q$ riadi distribúciou $\chi^2$ s $k - 1 = 15$ stupňami voľnosti.

**Kód výpočtu:**

```python
k = x.shape[1]                         # 16 kvartálov
row_sums = x.sum(axis=1)               # Ri pre každý vzor
col_sums = x.sum(axis=0)               # Cj pre každý kvartál

numerator   = k * np.sum(col_sums ** 2) - (np.sum(col_sums) ** 2)
denominator = k * np.sum(row_sums) - np.sum(row_sums ** 2)

q_stat  = (k - 1) * numerator / denominator
p_value = chi2.sf(q_stat, k - 1)      # 1 - CDF = p-hodnota (pravý chvost)
```

`chi2.sf(x, df)` = 1 - CDF = pravdepodobnosť, že $\chi^2$ náhodná premenná nadobudne hodnotu väčšiu ako `x` (p-hodnota pre pravostranný test).

**Skutočné výsledky:**

| Typ analýzy | Q | p-hodnota | Záver |
|---|---|---|---|
| `ASSOC_CAT` | 48.66 | 0.000020 | **Zamietame H₀** – vzory sa štatisticky líšia |
| `ASSOC_WEB` | 33.56 | 0.003922 | **Zamietame H₀** – vzory sa štatisticky líšia |
| `SEQ_CAT` | 0.00 | 1.000000 | Nezamietame H₀ – vzory sú stabilné naprieč kvartálmi |
| `SEQ_WEB` | 0.00 | 1.000000 | Nezamietame H₀ – vzory sú stabilné naprieč kvartálmi |

Prah hladiny významnosti: $\alpha = 0.05$.

**Interpretácia:** Asociačné vzory (Apriori) sa medzi kvartálmi štatisticky menia – to naznačuje, že kríza skutočne ovplyvnila, ktoré stránky si ľudia prezerajú spolu. Sekvenčné vzory (prechody medzi stránkami) sú naopak veľmi stabilné – poradie navigácie sa nezmenilo.

**Prečo Q = 0 pre sekvenčné pravidlá?** Pretože sekvenčné pravidlá sa nachádzajú v každom alebo takmer každom kvartáli (high stability). Ak sú všetky $C_j$ rovnaké (každý kvartál má rovnaký počet vzorov), čitateľ Q vzorca = 0.

---

### 7. Kendallovo W (koeficient konkordancie)

**Čo meria:** Mieru **zhody v poradovom hodnotení** vzorov medzi kvartálmi. Inými slovami: Či kvartály "súhlasia" na tom, ktoré vzory sú dôležitejšie (vyšší support) a ktoré menej.

**Vstup:** Matica support-hodnôt $S$ rozmeru $(m \times n)$:
- $m$ = počet vzorov (riadky) – len vzory prítomné v ≥ 2 kvartáloch
- $n$ = počet kvartálov = 16 (hodnotitelia)

**Postup výpočtu:**

**Krok 1:** Pre každý kvartál $j$ zoradíme vzory podľa support hodnôt a priradíme im **ranky** (1 = najvyšší support, $m$ = najnižší). Pri zhodách použijeme priemerný rank.

$$
r_{ij} = \text{rank vzoru } i \text{ v kvartáli } j
$$

**Krok 2:** Pre každý vzor $i$ spočítame súčet rankov naprieč všetkými kvartálmi:

$$
R_i = \sum_{j=1}^{n} r_{ij}
$$

**Krok 3:** Priemerný súčet rankov:

$$
\bar{R} = \frac{1}{m} \sum_{i=1}^{m} R_i = \frac{n(m+1)}{2}
$$

**Krok 4:** Suma štvorcov odchýlok:

$$
S = \sum_{i=1}^{m} \left(R_i - \bar{R}\right)^2
$$

**Krok 5:** Kendallovo W:

$$
W = \frac{12 S}{n^2 (m^3 - m)}
$$

- $W = 1$ → dokonalá zhoda (všetky kvartály poradie vzorov rovnako)
- $W = 0$ → náhodné poradie (kvartály sa nezhodujú)
- $0 < W < 1$ → čiastočná zhoda

**Kód výpočtu:**

```python
m = scores.shape[0]   # počet vzorov
n = scores.shape[1]   # počet kvartálov (raters)

ranks = np.zeros_like(scores, dtype=float)
for j in range(n):
    ranks[:, j] = rankdata(-scores[:, j], method="average")
    # mínus: rankdata triedi vzostupne, my chceme rank 1 = najvyšší support

rank_sums    = ranks.sum(axis=1)           # Ri pre každý vzor
mean_rank    = rank_sums.mean()            # R_bar
S            = np.sum((rank_sums - mean_rank) ** 2)
W            = 12.0 * S / (n ** 2 * (m ** 3 - m))
```

**Skutočné výsledky:**

| Typ analýzy | W | `n_items` | `n_raters` | Interpretácia |
|---|---|---|---|---|
| `ASSOC_CAT` | 0.2929 | 18 | 16 | Slabá zhoda – asociačné vzory sa v čase menia |
| `ASSOC_WEB` | 0.1388 | 28 | 16 | Veľmi slabá zhoda |
| `SEQ_CAT` | 0.6925 | 14 | 16 | **Silná zhoda** – sekvenčné vzory sú konzistentné |
| `SEQ_WEB` | 0.5074 | 18 | 16 | Stredná zhoda |

---

## Skutočné výsledky analýzy

### Prehľad kvartálov (z `period_summary.csv`)

| Kvartál | Kríza? | Počet udalostí | Počet relácií |
|---|---|---|---|
| 09Q1 | Áno | 144 041 | 33 587 |
| 09Q2 | Áno | 207 213 | 86 683 |
| 10Q4 | Áno | 90 448 | 32 661 |
| 11Q1 | Nie | 201 629 | 36 256 |
| 12Q3 | Nie | 184 216 | 40 397 |
| 12Q4 | Nie | 193 761 | 33 556 |

V post-krízovom období (2012) sa pre kategórie `assoc_cat` podarilo nájsť len 0–8 pravidiel aj pri minimálnom support 0.01 – trh sa stabilizoval a správanie sa stalo menej predvídateľným v zmysle asociácií.

### Top 5 najstabilnejších vzorov (prítomných v najväčšom počte kvartálov)

**Asociačná analýza – category (ASSOC\_CAT):**

| Pravidlo | Počet kvartálov z 16 |
|---|---|
| `Pillar3 related, We support.. => Reputation` | 14 |
| `Reputation, We support.. => Pillar3 related` | 14 |
| `We support.. => Reputation` | 12 |
| `Pillar3 disclosure requirements, Reputation => Pillar3 related` | 10 |
| `Pillar3 disclosure requirements => Pillar3 related` | 10 |

**Sekvenčná analýza – category (SEQ\_CAT):**

| Pravidlo | Počet kvartálov z 16 |
|---|---|
| `Pillar3 disclosure requirements => Pillar3 disclosure requirements` | 16 |
| `Pillar3 related => Pillar3 related` | 16 |
| `Pillar3 disclosure requirements => Pillar3 related` | 16 |
| `Pricing List => Pricing List` | 16 |
| `Reputation => Pillar3 related` | 16 |

Sekvenčné pravidlá sú oveľa stabilnejšie – `Pillar3 disclosure requirements => Pillar3 related` sa vyskytuje v každom jednom kvartáli.

---

## Popis výstupných súborov

| Súbor | Obsah |
|---|---|
| `period_summary.csv` | Prehľad kvartálov: počet udalostí, relácií, pravidiel, použitý support |
| `period_top_rules_assoc_cat.csv` | Všetky asociačné pravidlá pre category (všetky kvartály) s metriky |
| `period_top_rules_assoc_web.csv` | Asociačné pravidlá pre webPart |
| `period_top_rules_seq_cat.csv` | Sekvenčné pravidlá pre category |
| `period_top_rules_seq_web.csv` | Sekvenčné pravidlá pre webPart |
| `pattern_matrix_binary_*.csv` | Binárna matica vzory × kvartály (0/1) |
| `pattern_matrix_support_*.csv` | Matica support hodnôt vzory × kvartály |
| `pattern_recurrence_*.csv` | Koľko kvartálov obsahuje každý vzor (zoradené zostupne) |
| `summary.txt` | Textový report: Cochran Q, Kendallovo W, top vzory |

---

## Vysvetlenie kľúčových funkcií

| Funkcia | Vstup | Výstup | Čo robí |
|---|---|---|---|
| `load_dataframe` | cesta k CSV | DataFrame | Načíta a vyčistí dáta |
| `period_sort_key` | reťazec `"10Q3"` | tuple `(2010, 3)` | Chronologické triedenie kvartálov |
| `is_crisis_period` | reťazec `"10Q3"` | `True` / `False` | Určí, či je kvartál v kríze |
| `build_transactions_for_period` | DataFrame kvartálu | list of lists | Skupiny stránok v reláciách pre Apriori |
| `run_apriori` | transakcie, prahy | DataFrame pravidiel | Spustí mlxtend Apriori |
| `mine_apriori_rules` | transakcie, prahy | DataFrame + support | Apriori s automatickým znižovaním support-u |
| `format_apriori_rules` | mlxtend výstup | čistý DataFrame | Prevedie frozenset na textové pravidlá |
| `build_sequences_for_period` | DataFrame kvartálu | list of lists | Zoradené sekvencie akcií v reláciách |
| `mine_sequence_rules` | sekvencie, prah | DataFrame pravidiel | Vlastná implementácia sekvenčných pravidiel |
| `analyze_one_period` | DataFrame kvartálu | slovník výsledkov | Spustí asociačnú aj sekvenčnú analýzu |
| `analyze_all_periods` | celý DataFrame | labels, results, summary | Analyzuje všetkých 16 kvartálov |
| `build_binary_matrix` | výsledky, labels | DataFrame 0/1 | Vzory × kvartály binárna matica |
| `build_support_matrix` | výsledky, labels | DataFrame float | Vzory × kvartály support matica |
| `cochran_q_test` | binárna matica | dict {q, p, df} | Cochran Q štatistický test |
| `kendalls_w` | support matica | dict {w, ...} | Kendallovo W (koeficient konkordancie) |
| `plot_binary_heatmap` | binárna matica | PNG súbor | Heatmapa so zvýraznenou hranicou krízy |
| `write_all_outputs` | všetky výsledky | CSV + TXT | Zápis všetkých výstupných súborov |

---

## Otázky, ktoré môže položiť profesor

**Q: Čo je jedna transakcia v kontexte asociačnej analýzy?**

A: Jedna transakcia = jedna relácia (`frame`). Obsahuje **množinu unikátnych** kategórií / podčastí webu, ktoré používateľ navštívil počas jednej relácie. Na poradí nezáleží – `{A, B, C}` a `{C, A, B}` sú rovnaká transakcia.

---

**Q: Čo je podpora (support) a prečo ho automaticky znižujeme?**

A: Support = podiel relácií obsahujúcich daný itemset z celkového počtu relácií. Niektoré kvartály majú málo relácií alebo homogénne správanie – pri vysokom prahu support nenájdeme dostatok pravidiel. Skript preto automaticky znižuje prah po kroku 0.01, kým nenájde aspoň 10 pravidiel alebo nedosiahne minimum 0.01.

---

**Q: Aký je rozdiel medzi asociačnou a sekvenčnou analýzou?**

A: **Asociačná** analýza hľadá, ktoré stránky sa **spoločne vyskytujú** v reláciách, bez ohľadu na poradie (`{A, B}` = `{B, A}`). **Sekvenčná** analýza hľadá, ktoré stránky po sebe **nasledujú** – záleží na poradí: `A → B` ≠ `B → A`. V skripte je asociačná riešená cez mlxtend Apriori, sekvenčná vlastnou implementáciou počítajúcou prechody medzi po sebe idúcimi stránkami.

---

**Q: Čo znamená lift = 3.02 pre pravidlo `We support.. => Reputation`?**

A: Relácie obsahujúce stránku "We support.." obsahujú stránku "Reputation" 3.02× **častejšie**, ako by sme čakali pri náhodnom výskyte oboch stránok. Lift > 1 naznačuje pozitívnu asociáciu.

---

**Q: Prečo Cochran Q = 0 a p = 1.0 pre sekvenčné pravidlá?**

A: Sekvenčné pravidlá sú prítomné v takmer každom kvartáli (väčšina vzorov má $R_i = 16$). Keď sú všetky stĺpcové súčty $C_j$ rovnaké, čitateľ vzorca Q = 0, teda $Q = 0$. Toto znamená, že sekvenčné vzory sú extrémne stabilné – nie je možné zamietnut $H_0$.

---

**Q: Čo je Cochran Q test a kedy ho použijeme?**

A: Cochran Q test je neparametrický test pre **porovnanie závislých binárnych vzoriek** (matched samples). Použijeme ho, keď:
- Máme $k \geq 2$ skupín (tu: 16 kvartálov)
- Každá "jednotka" (vzor) je testovaná vo všetkých skupinách (prítomný / neprítomný)
- Dáta sú binárne (0/1)

Je to obdoba Friedmanovho testu, ale pre binárne dáta.

---

**Q: Čo meria Kendallovo W a ako ho interpretujeme?**

A: Kendallovo W meria **konzistentnosť poradia** – do akej miery sa kvartály zhodujú na tom, ktoré vzory sú "dôležitejšie" (vyšší support). $W = 0.69$ pre sekvenčné category vzory znamená pomerne silnú zhodu – kvartály sa skoro vždy zhodujú, ktoré sekvenčné vzory dominujú. $W = 0.14$ pre asociačné webPart vzory znamená slabú zhodu – podiel vzorov sa medzi kvartálmi výrazne mení.

---

**Q: Prečo `rankdata(-scores[:, j])` so záporným znamienkom?**

A: Funkcia `rankdata` priradzuje rank 1 **najmenšej** hodnote. Chceme rank 1 pre **najvyšší** support. Záporné znamienko obracia poradie: najväčší support sa stane najmenším číslom a dostane rank 1.

---

**Q: Čo je `TransactionEncoder` a prečo ho potrebujeme?**

A: `TransactionEncoder` z mlxtend prevedie zoznam transakcií (list of lists s reťazcami) na **binárnu maticu** NumPy/DataFrame. Každý riadok = jedna transakcia, každý stĺpec = jedna unikátna položka, hodnota = True/False (či sa položka v transakcii nachádza). Apriori algoritmus pracuje s touto binárnou maticou.

---

**Q: Čo je `chi2.sf(q, df)` a prečo ho používame?**

A: `chi2.sf(x, df)` = Survival Function = $1 - F(x)$ kde $F$ je CDF chi-kvadrát distribúcie. Dáva **pravostranný chvost** – pravdepodobnosť, že $\chi^2$ náhodná premenná s `df` stupňami voľnosti nadobudne hodnotu väčšiu ako `x`. Toto je naša p-hodnota: ak je malá ($< 0.05$), Q štatistika je extrémna a zamietame $H_0$.

---

**Q: Prečo je matica vzory × kvartály dôležitá?**

A: Táto matica je kľúčovým výstupom zadania. Umožňuje vidieť, ktoré vzory sú **stabilné** (prítomné v mnohých kvartáloch) a ktoré sa objavujú len v určitom období (napr. len počas krízy). Je vstupom do Cochran Q testu aj Kendallovho W.

---

**Q: Prečo `dropna` a `errors="coerce"` pri načítaní?**

A: `errors="coerce"` pri `pd.to_numeric` nahrádza nečíselné hodnoty za `NaN` namiesto výnimky. `dropna` následne vyhodí tieto riadky. Zaručuje, že skript nezlyhá na špinavých dátach (napr. text v stĺpci `unixTime`).

---

**Q: Prečo sa používa `set()` pri počítaní `seen_rules` v sekvenčnej analýze?**

A: Aby sme v každej relácii počítali každý prechod $A \to B$ **najviac raz**. Bez toho by dlhá relácia s mnohými opakovaním stránky A a B umelé zvyšovala count pravidla, čo by skresľovalo support na úrovni relácií.

---

## Zhrnutie celkového výsledku

Skript ukázal, že:

1. **Asociačné vzory sa medzi krízou a post-krízou štatisticky menili** (Cochran Q p < 0.05) – ľudia menili, ktoré stránky prehliadali spolu (napr. v neskorej kríze a post-kríze menej asociácií pre webPart, len 0–2 pravidlá v 12Q3/12Q4)
2. **Sekvenčné vzory boli veľmi stabilné** (Cochran Q = 0, Kendallovo W ≈ 0.51–0.69) – spôsob navigácie (poradie kliknutí) sa nezmenil napriek kríze
3. **Najstabilnejšie vzory** naznačujú, že stránky súvisiace s `Pillar3` (regulačné požiadavky bánk) a `Pricing List` boli navštevované konzistentne po celých 4 rokoch
