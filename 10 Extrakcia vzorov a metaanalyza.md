# Kvartálna asociačná a sekvenčná analýza webového logu banky (logs5.csv)

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Banka zaznamenávala správanie návštevníkov svojho webu počas rokov 2009 – 2012 – teda v období finančnej krízy (2009–2010) aj po nej (2011–2012). Každý riadok v logu hovorí: _kedy_, _kto_ (relácia identifikovaná stĺpcom `agent`) a _čo_ navštívil (kategória stránky `category` / podčasť webu `webPart`).

Skript sa pýta: **Zmenilo sa správanie návštevníkov medzi krízou a post-krízou?** Odpovedá tak, že:

1. Rozdelí dáta na **16 kvartálov** (09Q1 – 12Q4)
2. Pre asociačnú analýzu vytvorí **transakcie** (množiny stránok v relácii, poradie nezáleží)
3. Pre sekvenčnú analýzu vytvorí **sekvencie** (zoradené stránky podľa `unixTime`, poradie záleží)
4. Spustí **Apriori** (asociačné pravidlá) a **AprioriAll** (sekvenčné pravidlá) pre každý kvartál samostatne
5. Zostaví **dátovú maticu vzory × kvartály** (0/1 – vzor bol/nebol prítomný)
6. Testuje štatisticky, či sa vzory medzi kvartálmi líšia (**Cochran Q**) a do akej miery sú konzistentné (**Kendallovo W**)
7. Vizualizuje výsledky ako **heatmapy**

---

### Prečo dva rôzne typy analýzy?

**Asociačná analýza (Apriori):** Hľadá stránky, ktoré si ľudia prezerajú *spolu* v rámci jednej návštevy – bez ohľadu na poradie. Napríklad: "Ak niekto navštívi stránku `Reputation`, takmer vždy navštívi aj `Pillar3 related`."

**Sekvenčná analýza (AprioriAll):** Hľadá vzory v *poradí* krokov. Napríklad: "Ak niekto navštívi `Reputation`, nasledujúci krok bude `Pricing List`." Poradie je tu zásadné.

---

### Vstup

Súbor `logs5.csv` s 2 071 235 záznamami. Oddeľovač: `;`, uvodzovky: `"`.

| Stĺpec | Typ | Popis |
|---|---|---|
| `agent` | int | ID relácie (session) – jeden používateľ, jedna návšteva |
| `yearQuartal` | string | Kvartál vo formáte `09Q1`, `10Q3`, atď. |
| `category` | string | Kategória stránky (napr. `Reputation`, `Pricing List`) |
| `webPart` | string | Podčasť webu (napr. `Awards`, `Rating`, `History`) |
| `unixTime` | int | Unix timestamp – čas kliknutia (na chronologické zoradenie) |
| `crisis` | int | 1 = krízové obdobie (2009–2010), 0 = post-krízové (2011–2012) |

---

## Vstupné a výstupné súbory

```
logs5.csv
    │
    └──► analyze.py
              │
              └── analysis_outputs/
                      ├── pattern_matrix_binary_assoc_cat.csv
                      ├── pattern_matrix_binary_assoc_web.csv
                      ├── pattern_matrix_binary_seq_cat.csv
                      ├── pattern_matrix_binary_seq_web.csv
                      └── plots/
                              ├── heatmap_assoc_cat.png
                              ├── heatmap_assoc_web.png
                              ├── heatmap_seq_cat.png
                              └── heatmap_seq_web.png
```

---

## Code flow – diagram

```
START
  │
  ├─► Krok 0: pd.read_csv("logs5.csv")
  │     └─ čistenie chýbajúcich hodnôt (dropna)
  │
  ├─► Krok 1: rozdelenie na 16 kvartálov → quarter_data {}
  │
  ├─► Krok 5: hlavná slučka cez 16 kvartálov
  │     │
  │     ├─► priprav_transakcie(subset, 'category')
  │     │     └─ groupby(agent) → množiny stránok (poradie nezáleží)
  │     ├─► spusti_apriori(transakcie, 'category')
  │     │     ├─ TransactionEncoder → binárna matica True/False
  │     │     ├─ apriori(min_support) → frekventované itemsety
  │     │     ├─ association_rules(min_confidence, min_lift) → pravidlá
  │     │     └─ ak < 10 pravidiel: znížiť support o 0.01 a opakovať
  │     │
  │     ├─► priprav_sekvencie(subset, 'category')
  │     │     └─ groupby(agent) + sort_values(unixTime) → zoradené sekvencie
  │     └─► spusti_apriori_all(sekvencie, 'category')
  │           ├─ vzorkovanie (max 2000 sekvencií)
  │           ├─ frekventované 1-prvkové vzory (je_podpostupnost + vypocitaj_support)
  │           ├─ rozširovanie na 2,3,4-prvkové vzory
  │           └─ generovanie pravidiel (confidence ≥ prah)
  │
  ├─► Krok 6: zostav_maticu() → binárna matica vzory × kvartály (0/1)
  │
  ├─► Krok 7: cochran_q_test() + kendall_w() → štatistická analýza
  │
  ├─► Krok 8: vykresli_heatmapu() → PNG súbory
  │
  └─► Krok 9: sumarný výpis výsledkov
END
```

---

## Postup riešenia – krok za krokom

### Krok 0 – Načítanie dát

```python
df = pd.read_csv(
    "logs5.csv",
    sep=";",
    low_memory=False,
    quotechar='"'
)

df['unixTime'] = pd.to_numeric(df['unixTime'], errors='coerce')
df = df.dropna(subset=['agent', 'unixTime', 'category', 'webPart', 'yearQuartal'])
```

- `sep=";"` – CSV používa bodkočiarku ako oddeľovač (nie čiarku)
- `low_memory=False` – pandas načíta celý súbor naraz a určí typy stĺpcov správne (bez chyby pri veľkých súboroch)
- `quotechar='"'` – polia v uvodzovkách sa správne spoja do jedného reťazca
- `errors='coerce'` – ak je v stĺpci `unixTime` textová hodnota, prevedie sa na `NaN` namiesto pádu skriptu
- `dropna(...)` – vyhodíme riadky, kde čokoľvek z kľúčových stĺpcov chýba

**Výsledok:** ~2 miliónov čistých záznamov.

---

### Krok 1 – Rozdelenie na kvartály

```python
QUARTERS = sorted(df['yearQuartal'].unique())

quarter_data = {}
for q in QUARTERS:
    quarter_data[q] = df[df['yearQuartal'] == q].copy()
```

- `df['yearQuartal'].unique()` – nájde všetky unikátne hodnoty kvartálov (`09Q1`, `09Q2`, ..., `12Q4`)
- `sorted(...)` – zoradí ich chronologicky (reťazce sú zoraditeľné abecedne, čo tu zodpovedá aj časovej postupnosti)
- `quarter_data[q]` – slovník kde kľúč = názov kvartálu, hodnota = príslušný subset DataFramu
- `.copy()` – vytvoríme kópiu, aby prípadné zmeny v subsete neovplyvnili pôvodný `df`

**Výsledok:** 16 subsetov (kvartálov), prvých 8 krízové (2009–2010), druhých 8 post-krízové (2011–2012).

---

### Krok 2 – Príprava dát pre analýzu

#### 2a – Transakcie (pre asociačnú analýzu)

```python
def priprav_transakcie(subset, stlpec):
    transakcie = []
    skupiny = subset.groupby('agent')[stlpec]
    for agent_id, hodnoty in skupiny:
        unikatne = list(set(hodnoty.dropna().astype(str).tolist()))
        if len(unikatne) >= 1:
            transakcie.append(unikatne)
    return transakcie
```

**Transakcia = množina unikátnych stránok navštívených v jednej relácii.**

- `groupby('agent')` – zoskupíme riadky podľa ID relácie
- `set(...)` – z každej relácie zoberieme len **unikátne** stránky (poradie nezáleží, duplicity vyhodíme)

Príklad:
```
Relácia 7843: Reputation, Pricing List, Reputation, Pillar3 related
              ─→ transakcia: {Reputation, Pricing List, Pillar3 related}

Relácia 7844: Pricing List, Pricing List, Pricing List
              ─→ transakcia: {Pricing List}
```

#### 2b – Sekvencie (pre sekvenčnú analýzu)

```python
def priprav_sekvencie(subset, stlpec):
    sekvencie = []
    sorted_subset = subset.sort_values('unixTime')
    skupiny = sorted_subset.groupby('agent')[stlpec]
    for agent_id, hodnoty in skupiny:
        sekv = hodnoty.dropna().astype(str).tolist()
        if len(sekv) >= 2:
            sekvencie.append(sekv)
    return sekvencie
```

**Sekvencia = zoradený zoznam stránok v relácii (poradie = čas kliknutia).**

- `sort_values('unixTime')` – zoradíme chronologicky **pred** groupby, aby sekvencie zachovali časový poriadok
- **NEpoužívame `set()`** – zachovávame poradie aj duplicity, lebo pri sekvenčnej analýze záleží na poradí krokov
- `len(sekv) >= 2` – sekvencia musí mať aspoň 2 kroky, inak nemá zmysel hľadať prechody

Príklad:
```
Relácia 7843, zoradená podľa unixTime:
  [Reputation → Pillar3 related → Pricing List]
  prechody: Reputation→Pillar3 related, Pillar3 related→Pricing List
```

---

### Krok 3 – Asociačná analýza (Apriori)

```python
def spusti_apriori(transakcie, typ_stlpca):
    # ...
    te = TransactionEncoder()
    te_pole = te.fit(transakcie).transform(transakcie)
    df_bin = pd.DataFrame(te_pole, columns=te.columns_)

    freq_mnoziny = apriori(df_bin, min_support=aktualny_sup, use_colnames=True)
    kandidati = association_rules(freq_mnoziny, metric="confidence", min_threshold=min_conf)
    kandidati = kandidati[kandidati['lift'] >= min_lift]
```

#### TransactionEncoder

`TransactionEncoder` prevedie zoznam transakcií na binárnu maticu:

```
Transakcie:                         Binárna matica (True/False):
[Reputation, Pricing List]          Pillar3  Pricing  Reputation
[Pricing List, Pillar3 related]  →    F        T          T
[Reputation]                          T        T          F
                                       F        F          T
```

- Každý **riadok** = jedna transakcia (relácia)
- Každý **stĺpec** = jedna unikátna položka (stránka)
- Hodnota `True` = položka sa v transakcii nachádza

#### Apriori + association_rules

- `apriori(df_bin, min_support=...)` – nájde všetky frekventované itemsety (množiny stránok, ktorých support ≥ prah)
- `association_rules(freq_mnoziny, metric="confidence", min_threshold=min_conf)` – z itemsetov vygeneruje pravidlá tvaru `A ⟹ B`
- `rules[rules['lift'] >= min_lift]` – dodatočný filter: zachovávame len pravidlá kde A a B nie sú nezávislé

#### Automatické znižovanie support-u

```python
while aktualny_sup >= SPODNA_HRANICA:
    freq_mnoziny = apriori(df_bin, min_support=aktualny_sup, ...)
    kandidati = association_rules(...)
    if len(kandidati) >= MIN_PRAVIDIEL:
        pravidla = kandidati
        break
    aktualny_sup = round(aktualny_sup - 0.01, 2)
```

Ak sa nenájde aspoň 10 pravidiel, support sa automaticky zníži o 0.01 a algoritmus sa spustí znova. Minimálna hranica je `0.01`.

**Nastavenia podľa stĺpca:**

| Stĺpec | `min_support` | `min_confidence` | `min_lift` | `max_len` |
|---|---|---|---|---|
| `category` | 0.05 | 0.50 | 1.0 | bez obmedzenia |
| `webPart` | 0.10 | 0.70 | 1.0 | 3 |

`webPart` má prísnejšie parametre, lebo obsahuje oveľa viac unikátnych hodnôt – bez obmedzenia by hrozila **kombinatorická explózia** (príliš veľa kandidátnych itemsetov).

---

### Krok 4 – Sekvenčná analýza (AprioriAll – vlastná implementácia)

#### Pomocná funkcia: `je_podpostupnost`

```python
def je_podpostupnost(vzor, sekvencia):
    idx_vzoru = 0
    i = 0
    while i < len(sekvencia) and idx_vzoru < len(vzor):
        if sekvencia[i] == vzor[idx_vzoru]:
            idx_vzoru += 1
    return idx_vzoru == len(vzor)
```

Skontroluje, či vzor `[A, C]` je podpostupnosťou sekvencie `[A, B, C, D]`.
Prvky **nemusia byť susedné** – stačí zachovať poradie (A musí byť pred C).

```
vzor = ['A', 'C'],  sekvencia = ['A', 'B', 'C', 'D']  →  True
vzor = ['C', 'A'],  sekvencia = ['A', 'B', 'C', 'D']  →  False  (C je až na 3. mieste)
```

#### Pomocná funkcia: `vypocitaj_support`

```python
def vypocitaj_support(vzor, sekvencie):
    pocet_vyskytu = 0
    i = 0
    while i < len(sekvencie):
        if je_podpostupnost(vzor, sekvencie[i]):
            pocet_vyskytu += 1
        i += 1
    return pocet_vyskytu / len(sekvencie)
```

Support vzoru = podiel sekvencií, v ktorých sa vzor vyskytuje ako podpostupnosť.

#### Hlavná funkcia: `spusti_apriori_all`

Algoritmus prebieha v troch fázach:

**Fáza 1 – Frekventované 1-prvkové vzory:**
```python
while i < len(vsetky_itemy):
    vzor = [vsetky_itemy[i]]
    sup = vypocitaj_support(vzor, sekvencie)
    if sup >= aktualny_sup:
        freq_vzory[tuple(vzor)] = sup
    i += 1
```

**Fáza 2 – Rozširovanie na dlhšie vzory (AprioriAll princíp):**
```python
dlzka = 2
while dlzka <= max_dlzka:
    # Každý predchádzajúci vzor rozšírime o každý item
    novy_vzor = predchadzajuce[j] + [vsetky_itemy[k]]
    sup = vypocitaj_support(novy_vzor, sekvencie)
    if sup >= aktualny_sup:
        nove_freq[tuple(novy_vzor)] = sup
    dlzka += 1
```

**Fáza 3 – Generovanie sekvencných pravidiel:**
```python
for vzor_tuple, vzor_sup in vsetky_freq_vzory.items():
    vzor = list(vzor_tuple)
    if len(vzor) < 2:
        continue
    antecedent = vzor[:split_idx]
    konsekvent  = vzor[split_idx:]
    konfidencia = vzor_sup / vsetky_freq_vzory[tuple(antecedent)]
    if konfidencia >= min_conf:
        pravidla_list.append({...})
```

Príklad: vzor `[A, B, C]` generuje pravidlá `[A] → [B, C]` a `[A, B] → [C]`.

**Optimalizácie pre veľký dataset:**
- Vzorkujeme max **2000 sekvencií** na kvartál (pre rýchlosť)
- Pre `webPart` používame len **top-50 najfrekventovanejších** hodnôt (zabránenie kombinatorickej explózii)

---

### Krok 6 – Dátová matica vzory × kvartály

```python
def zostav_maticu(pravidla_per_quarter, quarters, typ):
    # Krok A: zozbierame všetky unikátne vzory naprieč kvartálmi
    vsetky_vzory = set()
    for q in quarters:
        for _, riadok in pravidla_per_quarter[q].iterrows():
            ant = str(sorted(list(riadok['antecedents'])))
            con = str(sorted(list(riadok['consequents'])))
            vsetky_vzory.add(ant + " -> " + con)

    # Krok B: inicializujeme maticu nulami
    matica = pd.DataFrame(0, index=sorted(vsetky_vzory), columns=quarters)

    # Krok C: vyplníme 1 tam kde vzor existuje v danom kvartáli
    for q in quarters:
        for _, riadok in pravidla_per_quarter[q].iterrows():
            kluc = ...
            matica.loc[kluc, q] = 1

    return matica
```

- **Riadky** = unikátne pravidlá naprieč všetkými kvartálmi
- **Stĺpce** = 16 kvartálov (`09Q1` – `12Q4`)
- **Hodnota 1** = pravidlo bolo nájdené v tomto kvartáli
- **Hodnota 0** = pravidlo sa v tomto kvartáli nevyskytlo

Príklad (skrátený):

| Vzor | 09Q1 | 09Q2 | ... | 12Q4 |
|---|---|---|---|---|
| `['Reputation'] -> ['Pillar3 related']` | 1 | 1 | ... | 0 |
| `['Pricing List'] -> ['Reputation']` | 1 | 0 | ... | 1 |
| `['We support..'] -> ['Reputation']` | 0 | 1 | ... | 0 |

---

### Krok 7 – Štatistická analýza

Pozri sekciu **Štatistické metódy a vzorce** nižšie.

---

### Krok 8 – Vizualizácia (heatmapy)

```python
def vykresli_heatmapu(matica, nazov, cesta_suboru):
    plt.figure(figsize=(sirka, vyska))
    sns.heatmap(
        matica,
        cmap='Blues',
        linewidths=0.3,
        vmin=0, vmax=1
    )
    plt.savefig(cesta_suboru, dpi=100)
    plt.close()
```

- **Heatmapa** vizualizuje binárnu maticu vzory × kvartály
- Modrá = vzor prítomný (1), biela = vzor nepritomný (0)
- `plt.close()` – zavrieme figure aby nedochádzalo k úniku pamäte pri 4 obrázkoch za sebou
- `matplotlib.use('Agg')` – neinteraktívny backend (bez GUI okna), vhodný pre serverové/skriptové spustenie

---

## Štatistické metódy a vzorce

### 1. Support (podpora)

$$
\text{support}(A) = \frac{\text{počet transakcií/sekvencií obsahujúcich } A}{\text{celkový počet transakcií/sekvencií}}
$$

$$
\text{support}(A \Rightarrow B) = \text{support}(A \cup B)
$$

- Pohybuje sa v rozsahu $[0, 1]$
- Hovorí, v akom podiele relácií sa daný vzor (alebo kombinácia stránok) vyskytuje
- Príklad: support = 0.12 → vzor sa nachádza v 12 % relácií daného kvartálu

---

### 2. Confidence (spoľahlivosť)

$$
\text{confidence}(A \Rightarrow B) = \frac{\text{support}(A \cup B)}{\text{support}(A)}
$$

- Pravdepodobnosť, že transakcia/sekvencia obsahuje B **za podmienky, že obsahuje A**
- Pohybuje sa v rozsahu $[0, 1]$
- Príklad: `Reputation ⟹ Pillar3 related`, confidence = 0.73 → ak relácia obsahuje stránku „Reputation", v 73 % prípadov obsahuje aj „Pillar3 related"

---

### 3. Lift (zdvihnutie)

$$
\text{lift}(A \Rightarrow B) = \frac{\text{confidence}(A \Rightarrow B)}{\text{support}(B)} = \frac{\text{support}(A \cup B)}{\text{support}(A) \cdot \text{support}(B)}
$$

- $\text{lift} = 1$ → A a B sú **nezávislé** (náhoda)
- $\text{lift} > 1$ → **pozitívna korelácia**: výskyt A zvyšuje pravdepodobnosť B
- $\text{lift} < 1$ → **negatívna korelácia**: výskyt A znižuje pravdepodobnosť B
- Príklad: lift = 3.0 → stránky sa vyskytujú spolu 3× častejšie, ako by sa dalo očakávať náhodou

---

### 4. Apriori algoritmus

**Kľúčová vlastnosť (Apriori princíp / anti-monotonicita support-u):**

> Ak itemset `{A, B}` má support **menší** ako prahová hodnota, potom **každý jeho nadset** `{A, B, C}` tiež nebude spĺňať prahovú hodnotu.

Vďaka tomu môžeme **odstrihávať** celé vetvy prehľadávacieho priestoru bez ich vyhodnocovania – ak je `{A, B}` nefrekventovaný, nikdy nekontrolujeme `{A, B, C}`, `{A, B, C, D}` atď.

**Postup Apriori:**

```
1. Nájdi všetky frekventované 1-itemsety {A}, {B}, {C}, ...
2. Z frekventovaných 1-itemsetov zostav kandidátne 2-itemsety {A,B}, {A,C}, ...
3. Otestuj support každého kandida – vyraď tie pod prahom
4. Opakuj pre 3-itemsety, 4-itemsety, ... (kým existujú frekventované)
5. Z frekventovaných itemsetov generuj pravidlá A ⟹ B kde confidence ≥ prah
```

**Vstup v skripte:** transakcie = množiny stránok z každého sedenia jedného kvartálu.

---

### 5. AprioriAll – sekvenčné pravidlá (vlastná implementácia)

Na rozdiel od Apriori tu **záleží na poradí** prvkov. Hľadáme vzory tvaru $[A, B, C]$ kde A nastáva pred B a B pred C.

**Podpostupnosť:** Vzor $[A, C]$ je podpostupnosťou sekvencie $[A, B, C, D]$ ak každý prvok vzoru sa v sekvencii nachádza v správnom poradí (prvky nemusia byť susedné).

**Výpočet support-u:**

$$
\text{support}([A, B]) = \frac{\text{počet sekvencií kde } [A, B] \text{ je podpostupnosťou}}{|T|}
$$

**Výpočet confidence:**

$$
\text{confidence}([A] \to [B]) = \frac{\text{support}([A, B])}{\text{support}([A])}
$$

Implementácia v skripte prechádza všetky sekvencie a testuje príslušnosť vzoru pomocou `je_podpostupnost`. Postup:
1. Nájde frekventované 1-prvkové vzory
2. Rozširuje ich na 2, 3, 4-prvkové (AprioriAll rozširovanie)
3. Generuje pravidlá zo všetkých frekventovaných vzorov dlžky ≥ 2

---

### 6. Cochran Q Test

**Čo testuje:** Či sa proporcia prítomnosti vzorov **štatisticky líši** medzi kvartálmi.

**H₀ (nulová hypotéza):** Pravdepodobnosť prítomnosti vzoru je rovnaká vo všetkých kvartáloch.

**H₁ (alternatívna hypotéza):** Aspoň jeden kvartál sa od ostatných štatisticky líši.

**Vstup:** Binárna matica $X$ rozmeru $(n \times k)$:
- $n$ = počet unikátnych vzorov (riadky)
- $k$ = počet kvartálov (stĺpce); u nás $k = 16$

**Výpočet:**

$$
Q = (k-1) \cdot \frac{k \displaystyle\sum_{j=1}^{k} C_j^2 - \left(\displaystyle\sum_{j=1}^{k} C_j\right)^2}{k \displaystyle\sum_{i=1}^{n} R_i - \displaystyle\sum_{i=1}^{n} R_i^2}
$$

kde:
- $C_j$ = súčet $j$-tého stĺpca (počet vzorov prítomných v $j$-tom kvartáli)
- $R_i$ = súčet $i$-tého riadku (v koľkých kvartáloch je vzor $i$ prítomný)
- $G = \sum C_j$ = celková suma všetkých hodnôt v matici

**Kód výpočtu:**

```python
def cochran_q_test(matica):
    hodnoty = matica.values.astype(float)
    k = hodnoty.shape[1]          # počet kvartálov

    sumy_stlpcov = hodnoty.sum(axis=0)   # Cj
    sumy_riadkov = hodnoty.sum(axis=1)   # Ri
    G = hodnoty.sum()                    # celková suma

    citatel   = (k - 1) * (k * np.sum(sumy_stlpcov ** 2) - G ** 2)
    menovatel = k * G - np.sum(sumy_riadkov ** 2)

    Q = citatel / menovatel
    p_hodnota = chi2.sf(Q, k - 1)       # p-hodnota: P(chi2 > Q)
    return Q, p_hodnota
```

`chi2.sf(Q, df)` = $1 - \text{CDF}$ = pravdepodobnosť, že $\chi^2$ náhodná premenná nadobudne hodnotu väčšiu ako $Q$ (pravostranný test).

**Distribúcia:** Pod $H_0$ sa $Q$ riadi distribúciou $\chi^2$ s $k - 1 = 15$ stupňami voľnosti.

**Prah hladiny významnosti:** $\alpha = 0.05$. Ak $p < 0.05$, zamietame $H_0$.

---

### 7. Kendallovo W (koeficient konkordancie)

**Čo meria:** Mieru **zhody v poradovom hodnotení** vzorov medzi kvartálmi – teda či kvartály „súhlasia" na tom, ktoré vzory sú prítomné a ktoré nie.

**Vstup:** Binárna matica $X$ rozmeru $(n \times k)$.

**Postup výpočtu:**

**Krok 1:** Pre každý kvartál $j$ pridelíme každému vzoru **rank** podľa jeho hodnoty (poradie prítomnosti).

$$
r_{ij} = \text{rank vzoru } i \text{ v kvartáli } j
$$

**Krok 2:** Suma rankov vzoru $i$ naprieč všetkými kvartálmi:

$$
R_i = \sum_{j=1}^{k} r_{ij}
$$

**Krok 3:** Priemerná suma rankov:

$$
\bar{R} = \frac{1}{n} \sum_{i=1}^{n} R_i
$$

**Krok 4:** Suma štvorcov odchýlok:

$$
S = \sum_{i=1}^{n} \left(R_i - \bar{R}\right)^2
$$

**Krok 5:** Kendallovo W:

$$
W = \frac{12 \cdot S}{k^2 \cdot (n^3 - n)}
$$

- $W = 1$ → dokonalá zhoda (všetky kvartály sa zhodujú v poradí vzorov)
- $W = 0$ → náhodné poradie (kvartály sa nezhodujú)

**Kód výpočtu:**

```python
def kendall_w(matica):
    hodnoty = matica.values.astype(float)
    n = hodnoty.shape[0]   # počet vzorov
    k = hodnoty.shape[1]   # počet kvartálov

    poradia = np.zeros_like(hodnoty)
    j = 0
    while j < k:
        poradia[:, j] = rankdata(hodnoty[:, j])
        j += 1

    sumy_poradii = poradia.sum(axis=1)     # Ri pre každý vzor
    priemer_sum  = sumy_poradii.mean()     # R_bar
    S = np.sum((sumy_poradii - priemer_sum) ** 2)
    W = (12.0 * S) / (k ** 2 * (n ** 3 - n))
    return W
```

**Interpretácia W:**

| Hodnota W | Interpretácia |
|---|---|
| $W > 0.7$ | Silná konkordancia – kvartály sa zhodujú v poradí vzorov |
| $0.3 < W \leq 0.7$ | Mierna konkordancia |
| $W \leq 0.3$ | Slabá konkordancia – poradie vzorov je nestabilné naprieč časom |

---

## Popis výstupných súborov

| Súbor | Obsah |
|---|---|
| `pattern_matrix_binary_assoc_cat.csv` | Binárna matica vzory × kvartály pre asociačné pravidlá (category) |
| `pattern_matrix_binary_assoc_web.csv` | Binárna matica pre asociačné pravidlá (webPart) |
| `pattern_matrix_binary_seq_cat.csv` | Binárna matica pre sekvenčné pravidlá (category) |
| `pattern_matrix_binary_seq_web.csv` | Binárna matica pre sekvenčné pravidlá (webPart) |
| `plots/heatmap_assoc_cat.png` | Vizualizácia matice ako heatmapa (asociácia, category) |
| `plots/heatmap_assoc_web.png` | Vizualizácia (asociácia, webPart) |
| `plots/heatmap_seq_cat.png` | Vizualizácia (sekvencia, category) |
| `plots/heatmap_seq_web.png` | Vizualizácia (sekvencia, webPart) |

---

## Otázky, ktoré môže položiť profesor

**Q: Čo je transakcia v kontexte tejto analýzy a čo je sekvencia? Aký je medzi nimi rozdiel?**
A: **Transakcia** je množina stránok navštívených v jednej relácii – poradie nezáleží (napr. `{Reputation, Pricing List}`). Používa sa v asociačnej analýze. **Sekvencia** je zoradený zoznam stránok podľa času kliknutia – poradie je zásadné (napr. `[Reputation → Pricing List → Pillar3 related]`). Používa sa v sekvenčnej analýze.

---

**Q: Prečo sa pri príprave transakcií používa `set()`, ale pri sekvenciách nie?**
A: Pri **transakciách** chceme vedieť len to, *ktoré* stránky sa v relácii nachádzali – počet opakovaní a poradie nezaujíma. `set()` automaticky odstráni duplicity. Pri **sekvenciách** nás zaujíma *poradie* krokov – ak používateľ navštívil `Reputation` dvakrát, obe výskyty zachovávame, lebo sú to reálne kroky navigácie.

---

**Q: Čo je Apriori princíp a na čo slúži?**
A: Apriori princíp hovorí, že ak itemset `{A, B}` je **nefrekventovaný** (support < prah), potom každý jeho nadset `{A, B, C}` bude tiež nefrekventovaný. To umožňuje odstrihávanie (*pruning*): keď nájdeme nefrekventovaný itemset, celú vetvu prehľadávacieho priestoru zahodíme bez testovania. Bez tohto princípu by algoritmus musel testovať exponenciálne veľa kombinácií.

---

**Q: Čo je `TransactionEncoder` a prečo ho potrebujeme?**
A: `TransactionEncoder` z knižnice `mlxtend` prevedie zoznam transakcií (zoznam zoznamov reťazcov) na **binárnu maticu True/False**, kde každý riadok je transakcia a každý stĺpec je jedna unikátna položka. Algoritmus `apriori()` potrebuje na vstupe práve takúto maticu.

---

**Q: Prečo má `webPart` prísnejšie parametre ako `category`?**
A: `webPart` obsahuje oveľa viac unikátnych hodnôt ako `category`. Pri nízkom support-e a veľkom počte unikátnych položiek by Apriori generoval obrovské množstvo kandidátnych itemsetov – **kombinatorická explózia**. Prísnejšie parametre (`min_support=0.10`, `max_len=3`) výrazne obmedzia priestor hľadania na prakticky zvládnuteľnú veľkosť.

---

**Q: Prečo skript znižuje support automaticky a aká je dolná hranica?**
A: Cieľom je mať aspoň 10 pravidiel pre každý kvartál (ako požaduje zadanie). Niektoré kvartály môžu mať menej transakcií alebo menej rozmanité správanie – pri nastavenej počiatočnej hodnote support-u sa nemusí nájsť dostatok pravidiel. Automatické znižovanie o 0.01 zaručí, že sa nájde aspoň minimálny počet pravidiel. Dolná hranica 0.01 zabraňuje, aby sa pravidlá generovali z príliš zriedkavých vzorov (zároveň by to bolo výpočtovo náročné).

---

**Q: Čo je podpostupnosť (`je_podpostupnost`) a ako sa líši od podreťazca?**
A: **Podpostupnosť** vyžaduje len zachovanie poradia prvkov – prvky nemusia byť susedné. Vzor `[A, C]` je podpostupnosťou `[A, B, C]` (A je pred C, hoci medzi nimi je B). **Podreťazec** by vyžadoval, aby prvky boli bezprostredne za sebou – `[A, C]` by podreťazcom `[A, B, C]` nebol. Sekvenčná analýza správania používa podpostupnosti, lebo medzi dvoma kliknutiami môže byť ľubovoľný počet iných kliknutí.

---

**Q: Čo znamená výsledok Cochran Q testu pri $p < 0.05$?**
A: Zamietame nulovú hypotézu, že proporcia prítomnosti vzoru je rovnaká vo všetkých kvartáloch. Znamená to, že vzory správania sa **štatisticky významne menia** naprieč kvartálmi – napríklad v krízovom období sa objavujú iné vzory ako v post-krízovom. Ak $p \geq 0.05$, nemáme dostatok dôkazov na zamietnutie stability.

---

**Q: Čo meria Kendallovo W a čo znamená hodnota blízka 1 vs. blízka 0?**
A: Kendallovo W meria mieru **zhody medzi kvartálmi v poradovom hodnotení** vzorov. $W = 1$ znamená, že všetky kvartály sa zhodujú na tom, ktoré vzory sú dôležitejšie (vyšší výskyt) a ktoré menej – navigačné návyky sú konzistentné. $W = 0$ znamená, že poradie vzorov sa medzi kvartálmi úplne líši – správanie je nestabilné. Hodnota napr. $W = 0.29$ (slabá konkordancia) naznačuje, že asociačné vzory sa medzi krízou a post-krízou výrazne zmenili.

---

**Q: Prečo sa vzorkuje maximálne 2000 sekvencií pri sekvenčnej analýze?**
A: Vlastná implementácia `apriori_all` prechádza pre každý kandidátny vzor všetky sekvencie (`O(n)` na vzor). Kvartál môže mať desiatky tisíc sekvencií a stovky kandidátnych vzorov – bez obmedzenenia by trvala analýza hodiny. Vzorkovaním 2000 sekvencií zachovávame štatistickú reprezentatívnosť (veľká vzorka) pri rozumnej rýchlosti výpočtu.

---

**Q: Prečo `matplotlib.use('Agg')` na začiatku skriptu?**
A: `Agg` je neinteraktívny backend matplotlibu, ktorý vykresľuje obrázky priamo do súborov **bez otvárania GUI okna**. Bez neho by na niektorých systémoch (server, spustenie cez terminál bez grafického prostredia) matplotlib zahlásil chybu, pretože by sa pokúsil otvoriť okno kde nie je dostupný display.

---

**Q: Čo je dátová matica vzory × kvartály a na čo slúži?**
A: Je to binárna matica, kde každý **riadok** je jedno unikátne pravidlo (vzor) a každý **stĺpec** je jeden kvartál. Hodnota `1` znamená, že dané pravidlo bolo extrahované v danom kvartáli, `0` znamená, že nie. Táto matica je vstupom pre štatistické testy (Cochran Q, Kendall W) – umožňuje analyzovať, ako sa výskyt vzorov mení v čase naprieč všetkými 16 kvartálmi naraz.

---

## Zhrnutie najdôležitejších funkcií

| Funkcia / operácia | Modul | Účel |
|---|---|---|
| `pd.read_csv(sep=";")` | `pandas` | Načítanie CSV s bodkočiarkovým oddeľovačom |
| `df.dropna(subset=[...])` | `pandas` | Vyhodenie riadkov s chýbajúcimi hodnotami |
| `df.groupby('agent')` | `pandas` | Zoskupenie záznamov podľa ID relácie |
| `sort_values('unixTime')` | `pandas` | Chronologické zoradenie pre sekvencie |
| `TransactionEncoder()` | `mlxtend` | Kódovanie transakcií do binárnej matice True/False |
| `apriori(df, min_support)` | `mlxtend` | Extrakcia frekventovaných itemsetov |
| `association_rules(freq, metric="confidence")` | `mlxtend` | Generovanie asociačných pravidiel |
| `je_podpostupnost(vzor, sekv)` | vlastná impl. | Test či vzor je podpostupnosťou sekvencie |
| `vypocitaj_support(vzor, sekv)` | vlastná impl. | Výpočet support-u vzoru naprieč sekvenciami |
| `chi2.sf(Q, df)` | `scipy.stats` | p-hodnota Cochran Q testu (pravý chvost chi²) |
| `rankdata(stlpec)` | `scipy.stats` | Pridelenie rankov hodnotám (pri zhodách priemerný rank) |
| `sns.heatmap(matica)` | `seaborn` | Vizualizácia matice ako heatmapa |
| `pd.DataFrame(0, index=..., columns=...)` | `pandas` | Vytvorenie matice naplnenej nulami |
| `matica.loc[kluc, q] = 1` | `pandas` | Label-based zápis do bunky matice |
