# Vektorová reprezentácia textu – Študijný materiál

---

## Čo skript robí (podrobne)

Skript implementuje **vektorovú reprezentáciu textu** – proces, pri ktorom sa textové dokumenty prevedú na číselné vektory, aby s nimi mohol pracovať počítač (algoritmy strojového učenia, vyhľadávacie systémy, zhlukovanie).

### Vstup

Zo súboru `vektorova_reprezentacia.xlsx` (sheet `original`) načíta **maticu surových frekvencií slov** (WF – Word Frequency). Táto matica má:
- **riadky** = dokumenty (`dok1`, `dok2`, … `dok14`)
- **stĺpce** = kmene slov / termy (`kmen1` … `kmen100`)
- **hodnoty** = koľkokrát sa daný kmeň vyskytuje v danom dokumente (surová frekvencia, celé číslo ≥ 0)

Kmene slov sú výsledkom **stemmingu** – procesu, pri ktorom sa slová redukujú na svoj spoločný základ (napr. „bežal", „bežanie", „bežec" → kmeň „bež"). Tým sa znižuje počet unikátnych tokenov a rôzne tvary toho istého slova sa mapujú na jednu stĺpcovú pozíciu.

### Čo skript počíta

Z tejto vstupnej matice skript odvodí **tri rozdielne váhovacie schémy**, pričom každá zodpovedá inému prístupu k reprezentácii textu:

1. **Binárna reprezentácia (`bin.csv`)** – každá bunka obsahuje len `0` alebo `1`. Hovorí: „toto slovo sa v dokumente vyskytuje / nevyskytuje". Ignoruje, koľkokrát.

2. **Logaritmická TF (`log.csv`)** – každá bunka obsahuje `1 + log₁₀(wf)` (alebo `0` ak `wf = 0`). Zachováva informáciu o frekvencii, ale tlmí extrémne hodnoty – slovo, ktoré sa vyskytuje 1000×, nedostane 1000× vyššiu váhu ako slovo s výskytom 1×, ale len 3× vyššiu.

3. **TF-IDF (`inv.csv`)** – každá bunka je súčin logaritmickej TF a IDF (Inverse Document Frequency). IDF penalizuje slová, ktoré sa vyskytujú vo väčšine dokumentov (sú neinformatívne), a zvýhodňuje slová špecifické pre malý počet dokumentov. Výsledkom je, že každý dokument je reprezentovaný váhami, ktoré zvýrazňujú jeho jedinečný obsah.

### Výstup

Každá z troch reprezentácií sa uloží do samostatného CSV súboru (`bin.csv`, `log.csv`, `inv.csv`), ktorý má rovnakú štruktúru ako vstupná matica – riadky sú dokumenty, stĺpce sú kmene slov, menia sa len číselné hodnoty.

### Prečo je to dôležité

Tieto reprezentácie sú základným stavebným kameňom **informačného vyhľadávania (IR)** a **textového dolovania (text mining)**. Žiadny algoritmus strojového učenia nedokáže pracovať priamo s textom – text musí byť prevedený na čísla. Výber správnej váhovacej schémy ovplyvňuje kvalitu vyhľadávania, klasifikácie alebo zhlukovania dokumentov.

---

## Vstupné a výstupné súbory

| Súbor | Typ | Obsah |
|---|---|---|
| `vektorova_reprezentacia.xlsx` (sheet `original`) | Vstup | Matica surových frekvencií slov (WF) – koľkokrát sa každý kmeň vyskytuje v každom dokumente |
| `bin.csv` | Výstup | Binárna reprezentácia – 0 alebo 1 |
| `log.csv` | Výstup | Logaritmická TF – váhované frekvencie |
| `inv.csv` | Výstup | TF-IDF – kombinácia TF a IDF |

### Štruktúra matice (príklad z bin.csv)

```
         kmen1  kmen2  kmen3  ...  kmen100
dok1       1      1      1   ...     1
dok2       1      1      1   ...     0
dok3       1      1      1   ...     1
...
```

- **Riadky** = dokumenty (`dok1`, `dok2`, …)
- **Stĺpce** = kmene slov (`kmen1` … `kmen100`)
- **N** = celkový počet dokumentov (riadkov)
- **Hodnota bunky** = závisí od reprezentácie (0/1, log váha, TF-IDF váha)

---

## Postup riešenia – krok za krokom

### 1. Načítanie dát

```python
wf = pd.read_excel(INPUT_FILE, sheet_name="original", header=0, index_col=0)
wf = wf[wf.index.notna()].astype(float)
N = len(wf)
```

- `header=0` → prvý riadok Excelu sú názvy stĺpcov (kmene slov)
- `index_col=0` → prvý stĺpec sú názvy riadkov (dokumenty)
- `wf.index.notna()` → filtrujeme prázdne riadky (Excel môže obsahovať prázdne riadky na konci)
- `astype(float)` → konvertujeme všetky hodnoty na desatinné čísla (nie stringy)
- `N = len(wf)` → počet dokumentov, použité vo vzorci IDF

---

### 2. Binárna reprezentácia

```python
bin_df = (wf > 0).astype(int)
```

- `(wf > 0)` → vráti DataFrame s hodnotami `True`/`False`
- `.astype(int)` → `True → 1`, `False → 0`

---

### 3. Logaritmická TF

```python
log_df = wf.copy()
mask = wf > 0
log_df[mask] = 1 + np.log10(wf[mask])
log_df[~mask] = 0
```

- `mask` = boolovská maska – `True` tam kde slovo existuje
- `log_df[mask]` → aplikujeme vzorec len na nenulové bunky
- `log_df[~mask] = 0` → bunky kde wf == 0 ostávajú nulové

---

### 4. TF-IDF (inv)

```python
df_term = (wf > 0).sum(axis=0)
idf = np.log10(N / df_term)

inv_df = log_df.copy()
inv_df[~mask] = 0
inv_df[mask] = log_df[mask] * idf
```

- `(wf > 0).sum(axis=0)` → pre každý kmeň spočíta, v koľkých dokumentoch sa vyskytuje (`axis=0` = sumujeme cez riadky / cez dokumenty)
- `idf` = vektor s jednou hodnotou na každý kmeň (stĺpec)
- NumPy **broadcasting** automaticky roztiahne vektor `idf` na celú maticu po stĺpcoch

---

### 5. Export do CSV

```python
for name, df in [("bin", bin_df), ("log", log_df), ("inv", inv_df)]:
    df.to_csv(f"{name}.csv")
```

- Iterujeme cez zoznam dvojíc `(nazov_suboru, dataframe)`
- `df.to_csv()` uloží index (dokumenty) aj hlavičku (kmene slov)

---

## Knižnice

| Knižnica | Účel |
|---|---|
| `pandas` (`pd`) | Načítanie Excelu, práca s DataFrame (tabuľková štruktúra) |
| `numpy` (`np`) | Rýchle vektorizované matematické operácie – `log10`, boolovské masky |

---

## Štatistické metódy a vzorce

### 1. Binárna reprezentácia

$$
\text{bin}(d, t) =
\begin{cases}
1 & \text{ak } wf(d,t) > 0 \\
0 & \text{inak}
\end{cases}
$$

**Prečo:** Zachytáva len *prítomnosť* alebo *neprítomnosť* slova v dokumente. Nezáleží na tom, koľkokrát sa slovo vyskytuje.

**Výhoda:** Jednoduchosť, nízka pamäťová náročnosť (bitový vektor).

**Nevýhoda:** Stráca informáciu o dôležitosti slova – slovo, ktoré sa vyskytuje 1× a 100×, má rovnakú váhu.

---

### 2. Logaritmická TF (Term Frequency)

$$
\text{log\_TF}(d, t) =
\begin{cases}
1 + \log_{10}(wf(d,t)) & \text{ak } wf(d,t) > 0 \\
0 & \text{inak}
\end{cases}
$$

kde $wf(d, t)$ = surová frekvencia termu $t$ v dokumente $d$.

**Prečo +1:** Aby platilo $\text{log\_TF}(d,t) > 0$ pre každé slovo, ktoré sa vyskytuje. Bez +1 by $\log_{10}(1) = 0$, čo by zrovnalo slovo s výskytom 1 a slovo s výskytom 0.

**Prečo logaritmus:** Surová frekvencia môže byť veľmi veľká. Logaritmus „skrotí" rozsah hodnôt – slovo, ktoré sa vyskytuje 100×, je len **2×** dôležitejšie ako slovo s výskytom 10× (nie 10×).

| wf | log₁₀(wf) | 1 + log₁₀(wf) |
|---|---|---|
| 1 | 0 | 1.0 |
| 10 | 1 | 2.0 |
| 100 | 2 | 3.0 |
| 1000 | 3 | 4.0 |

---

### 3. TF-IDF (Term Frequency – Inverse Document Frequency)

TF-IDF je **dvojkrokový vzorec**:

#### Krok 1: Inverzná dokumentová frekvencia (IDF)

$$
\text{IDF}(t) = \log_{10}\left(\frac{N}{df(t)}\right)
$$

kde:
- $N$ = celkový počet dokumentov v kolekcii
- $df(t)$ = počet dokumentov, v ktorých sa term $t$ vyskytuje ($wf > 0$)

#### Krok 2: Výsledná TF-IDF váha

$$
\text{TF-IDF}(d, t) =
\begin{cases}
\text{log\_TF}(d,t) \times \text{IDF}(t) & \text{ak } wf(d,t) > 0 \\
0 & \text{inak}
\end{cases}
$$

**Prečo:** Slová, ktoré sa vyskytujú v **každom** dokumente (napr. „the", „je"), nesú málo informácie – sú potlačené nízkym IDF. Slová **špecifické pre malý počet dokumentov** dostanú vysokú váhu.

#### Limitné prípady IDF (dôležité pre skúšku):

| Situácia | Výpočet | Výsledok | Interpretácia |
|---|---|---|---|
| Term je vo **všetkých** dokumentoch (`df = N`) | $\log_{10}(N/N) = \log_{10}(1)$ | **0** | Nulová váha – term je neinformatívny |
| Term je v **jedinom** dokumente (`df = 1`) | $\log_{10}(N/1) = \log_{10}(N)$ | **maximum** | Najvyššia váha – term je unikátny |
| Term je v **polovici** dokumentov (`df = N/2`) | $\log_{10}(2) ≈ 0.301$ | stredná | Priemerná diskriminačná sila |

---

## Vysvetlenie kľúčových operácií v kóde

### Boolovská maska (`mask`)

```python
mask = wf > 0          # DataFrame s hodnotami True/False
log_df[mask]           # vyberie len bunky kde mask == True
log_df[~mask] = 0      # negácia: bunky kde mask == False nastav na 0
```

Maska sa vytvára **raz** z pôvodného `wf` a používa sa pre všetky tri výpočty. Zabezpečuje konzistenciu – nulové frekvencie vždy ostávajú nulové.

---

### NumPy Broadcasting

```python
idf = np.log10(N / df_term)   # vektor tvaru (100,) – jedna hodnota na kmeň
inv_df[mask] = log_df[mask] * idf
```

`idf` je jednorozmerný vektor (1 hodnota na každý stĺpec). NumPy ho automaticky roztiahne tak, že každý riadok matice sa vynásobí príslušnou IDF hodnotou pre daný stĺpec – **bez cyklu `for`**. To je rýchlejšie a čitateľnejšie.

```
         kmen1   kmen2  ...
IDF:    [0.033,  0.021, ...]

dok1:   [2.556,  2.959, ...]  ×  IDF  →  [0.084,  0.062, ...]
dok2:   [2.556,  2.832, ...]  ×  IDF  →  [0.084,  0.059, ...]
```

---

### `(wf > 0).sum(axis=0)` – dokumentová frekvencia

```python
df_term = (wf > 0).sum(axis=0)
```

- `(wf > 0)` → matica `True`/`False`
- `.sum(axis=0)` → sumuje **po stĺpcoch** (cez všetky riadky/dokumenty)
- `True` sa počíta ako `1`, `False` ako `0`
- Výsledok: pre každý kmeň dostaneme, v koľkých dokumentoch sa vyskytuje

```
axis=0 = sumujeme smerom "dolu" → výsledok je 1 riadok (pre každý stĺpec jeden súčet)
axis=1 = sumujeme smerom "doprava" → výsledok je 1 stĺpec (pre každý riadok jeden súčet)
```

---

## Zhrnutie najdôležitejších metód

| Metóda / Operácia | Knižnica | Účel |
|---|---|---|
| `pd.read_excel(file, sheet_name, header, index_col)` | `pandas` | Načítanie Excelu do DataFrame |
| `df.index.notna()` | `pandas` | Filtrácia riadkov s prázdnym indexom |
| `df.astype(float)` | `pandas` | Konverzia hodnôt na čísla |
| `(df > 0)` | `pandas` | Boolovská maska – porovnanie každej bunky |
| `.astype(int)` | `pandas` | Konverzia `True/False` na `1/0` |
| `np.log10(x)` | `numpy` | Logaritmus base 10 aplikovaný vektorizovane |
| `(df > 0).sum(axis=0)` | `pandas/numpy` | Súčet po stĺpcoch (dokumentová frekvencia) |
| `df[mask]` | `pandas` | Indexovanie pomocou boolovskej masky |
| `df.to_csv(path)` | `pandas` | Export DataFrame do CSV súboru |

---

## Porovnanie reprezentácií

| Vlastnosť | bin | log_TF | TF-IDF |
|---|---|---|---|
| Rozsah hodnôt | {0, 1} | [0, ∞) | [0, ∞) |
| Zachováva frekvenciu? | Nie | Áno (log-škála) | Áno (log-škála) |
| Zohľadňuje vzácnosť slova? | Nie | Nie | **Áno** |
| Typické použitie | Boolean IR, jednoduché klasifikátory | Vyhľadávanie, zhlukovanie | Najčastejší štandard v IR |

---

## Otázky, ktoré môže položiť profesor

**Q: Čo je TF a čo je IDF?**  
A: **TF** (Term Frequency) = miera toho, ako často sa term vyskytuje v konkrétnom dokumente. **IDF** (Inverse Document Frequency) = miera toho, ako vzácny je term naprieč celou kolekciou. TF-IDF kombinuje obe – slovo musí byť časté *v dokumente*, ale zároveň vzácne *v kolekcii*.

---

**Q: Prečo pri log_TF používame +1?**  
A: Bez +1 by platilo $\log_{10}(1) = 0$, čo by spôsobilo, že slovo s výskytom 1× by malo váhu 0 – rovnako ako slovo, ktoré sa nevyskytuje vôbec. Preto +1 posúva váhu na $1 + \log_{10}(1) = 1$, čo správne odlíši prítomnosť od neprítomnosti.

---

**Q: Čo sa stane ak df == N (term je vo všetkých dokumentoch)?**  
A: $\text{IDF} = \log_{10}(N/N) = \log_{10}(1) = 0$. TF-IDF bude nulové pre všetky dokumenty. Slovo je neinformatívne – nedokáže odlíšiť dokumenty od seba.

---

**Q: Čo sa stane ak df == 1 (term je len v jednom dokumente)?**  
A: $\text{IDF} = \log_{10}(N/1) = \log_{10}(N)$. Term dostane maximálnu váhu – je unikátny pre daný dokument, čo je veľmi informatívne.

---

**Q: Prečo používame logaritmus (base 10) a nie napr. prirodzený logaritmus?**  
A: Základ logaritmu mení iba škálovanie, nie poradie dokumentov. Výber base 10 je konvencia – výsledky sú rovnako platné s ln alebo log₂. V praxi na výsledku vyhľadávania nezáleží na základe.

---

**Q: Čo je boolovská maska a prečo ju používame?**  
A: Je to matica rovnakého tvaru ako `wf` s hodnotami `True`/`False`. Umožňuje aplikovať vzorec len na podmnožinu buniek bez explicitného cyklu `for`. Je to výkonnejšie (NumPy operuje nad celou maticou naraz) a kód je čitateľnejší.

---

**Q: Čo robí `axis=0` v `.sum(axis=0)`?**  
A: Sumuje smerom „dolu" – teda cez riadky. Pre každý stĺpec (kmeň) vráti jeden súčet. Výsledkom je vektor s jednou hodnotou na každý stĺpec. `axis=1` by sumovalo „doprava" – cez stĺpce, výsledok by bol jeden súčet na riadok (dokument).

---

**Q: Prečo TF-IDF váhy v `inv.csv` sú malé čísla (napr. 0.07)?**  
A: Pretože kolekcia má relatívne málo dokumentov (N je malé), teda väčšina slov sa vyskytuje vo väčšine dokumentov → `df` je blízke `N` → `IDF = log10(N/df)` je blízke 0. Výsledné TF-IDF (súčin log_TF × IDF) je preto nízke. V reálnych IR systémoch s miliónmi dokumentov sú hodnoty IDF oveľa vyššie.

---

**Q: Prečo ukladáme tri rôzne reprezentácie namiesto jednej?**  
A: Každá reprezentácia je vhodná pre iný typ úlohy:
- **bin** = keď záleží len na prítomnosti slova (Boolean retrieval, spam filter)
- **log_TF** = keď záleží na frekvencii, ale chceme potlačiť vplyv veľmi frekventovaných slov
- **TF-IDF** = keď chceme zvýrazniť slová, ktoré sú charakteristické pre konkrétny dokument (vyhľadávanie, klasifikácia, zhlukovanie)

---

**Q: Čo je NumPy broadcasting?**  
A: Mechanizmus, ktorý umožňuje aritmetické operácie medzi poliami rôznych tvarov. Keď vynásobíme maticu (14×100) vektorom (100,), NumPy automaticky „roztiahne" vektor na každý riadok matice – bez nutnosti explicitného cyklu. Je to pamäťovo efektívne a rýchle.

---

**Q: Prečo je surová frekvencia (raw TF) nevhodná priamo?**  
A: Dlhší dokument prirodzene obsahuje každé slovo viac-krát ako kratší, aj keď majú rovnaké tematické zloženie. Log-normalizácia čiastočne kompenzuje tento efekt. Navyše bez IDF by frekventované, ale neinformatívne slová dominovali – IDF ich potláča.
