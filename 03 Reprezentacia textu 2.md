
# NLP – Lematizácia a reprezentácia textu dátovou maticou

---

## Čo skript robí (podrobne)

Skript implementuje **NLP pipeline** (spracovanie prirodzeného jazyka), ktorý prevádza 5 surových textových súborov na číselné matice. Výstupom je Excel súbor s piatimi listami reprezentujúcimi rovnaké texty rôznymi štatistickými metódami.

### Vstup

Päť textových súborov `text1.txt` – `text5.txt`, každý s anglickým odborným textom z inej oblasti:

| Súbor | Téma |
|---|---|
| `text1.txt` | Umelá inteligencia a robotika |
| `text2.txt` | Klimatické zmeny |
| `text3.txt` | Ľudský mozog a neurológia |
| `text4.txt` | Vesmírny výskum |
| `text5.txt` | Globálna ekonomika |

### Čo skript počíta

Z týchto textov skript odvodí **štyri typy matíc** a jeden pomocný vektor:

1. **TF – frekvenčná matica** – absolútny počet výskytov každej lémy v každom dokumente
2. **Binárna matica** – iba 0 alebo 1 (vyskytuje sa / nevyskytuje sa)
3. **Logaritmická matica** – `log10(1 + TF)`, tlmí vplyv veľmi frekventovaných slov
4. **TF-IDF matica** – TF × IDF, zvýrazňuje slová typické pre konkrétny dokument
5. **IDF vektor** – inverzná dokumentová frekvencia pre každú lému

### Výstup

| Súbor | Typ | Obsah |
|---|---|---|
| `lemma_matrices.xlsx` (list `TF_frekvencia`) | Výstup | Absolútne frekvencie lém |
| `lemma_matrices.xlsx` (list `Binarna`) | Výstup | 0 / 1 prítomnosť lémy |
| `lemma_matrices.xlsx` (list `Logaritmicka`) | Výstup | log10(1 + TF) |
| `lemma_matrices.xlsx` (list `TF-IDF`) | Výstup | TF × IDF |
| `lemma_matrices.xlsx` (list `IDF`) | Výstup | IDF hodnota pre každú lému |

### Štruktúra výstupnej matice

```
              algorithm  artificial  ...  year
text1.txt          2          3     ...    1
text2.txt          0          0     ...    2
text3.txt          0          0     ...    0
...
```

- **Riadky** = dokumenty (`text1.txt` – `text5.txt`)
- **Stĺpce** = unikátne lémy (základné tvary slov) naprieč všetkými dokumentmi
- **Hodnota bunky** = závisí od reprezentácie (TF, 0/1, log-váha, TF-IDF váha)

---

## Vstupné a výstupné súbory

```
text1.txt   ─┐
text2.txt    │
text3.txt    ├──► lemmatization.py ──► lemma_matrices.xlsx
text4.txt    │
text5.txt   ─┘
```

---

## Postup riešenia – krok za krokom

### 1. Importy a stiahnutie NLTK dát

```python
import os, math
import nltk
import pandas as pd
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer

nltk.download('punkt_tab')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('wordnet')
```

| Knižnica / modul | Účel |
|---|---|
| `os`, `math` | Práca so súbormi, matematika (log10) |
| `nltk` | Natural Language Toolkit – NLP nástroje |
| `pandas` | Práca s DataFrame (tabuľková matica) |
| `numpy` | Vektorizované matematické operácie |
| `stopwords` | Zoznamy stop slov (the, is, and...) |
| `word_tokenize`, `sent_tokenize` | Rozdelenie textu na slová / vety |
| `WordNetLemmatizer` | Lematizátor – prevod na základný tvar |

NLTK pri prvom spustení stiahne potrebné jazykové modely: tokenizačné pravidlá (`punkt`), databázu anglických slov (`wordnet`) a zoznam stop slov.

---

### 2. Inicializácia

```python
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
```

- `set(...)` – stop slová uložíme do **množiny (set)**, lebo vyhľadávanie v sete je O(1) – každé slovo pri filtrovaní sa porovnáva v konštantnom čase, nie lineárne
- `WordNetLemmatizer()` – vytvoríme jeden objekt lematizátora, ktorý sa použije opakovane pre všetky slová všetkých dokumentov
- `SCRIPT_DIR` – absolútna cesta k priečinku skriptu, aby fungoval nezávisle od toho, odkiaľ ho spustíme

---

### 3. Načítanie textov

```python
documents = {}
for fname in TEXT_FILES:
    fpath = os.path.join(SCRIPT_DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        documents[fname] = f.read()
```

- `documents` = slovník `{ 'text1.txt': 'celý text...', ... }` – každý dokument je reťazec
- `encoding='utf-8'` – správne načítanie špeciálnych znakov

---

### 4. Tokenizácia a lematizácia – funkcia `extract_lemmas`

Toto je **jadro skriptu**. Funkcia dostane jeden text a vráti zoznam lém (základných tvarov slov).

```python
def extract_lemmas(text):
    lemmas = []
    tokenized = sent_tokenize(text)          # Krok 1: text → vety
    for word in tokenized:
        wordsList = nltk.word_tokenize(word) # Krok 2: veta → tokeny
        for w in wordsList:
            w_lower = w.lower()
            if (w_lower not in stop_words    # filter 1: stop slová
                and w_lower.isalpha()        # filter 2: len písmená
                and len(w_lower) > 2):       # filter 3: min. dĺžka
                lemma_word = lemmatizer.lemmatize(w_lower)  # Krok 4: lema
                lemmas.append(lemma_word)
    return lemmas
```

**Krok 1 – `sent_tokenize(text)`**: rozdelí text na zoznam viet podľa interpunkcie (`.`, `!`, `?`). Dôvod: lematizátor pracuje lepšie, keď pozná kontext vety.

**Krok 2 – `word_tokenize(veta)`**: rozdelí vetu na jednotlivé tokeny (slová + interpunkcia). Napríklad `"I'm running"` → `["I", "'m", "running"]`.

**Krok 3 – trojité filtrovanie**:
- `w_lower not in stop_words` – vylúčime funkčné slová bez sémantického obsahu (the, is, are, and, of...)
- `w_lower.isalpha()` – vylúčime čísla, interpunkciu, URL, špeciálne znaky
- `len(w_lower) > 2` – vylúčime príliš krátke slová (a, to, of – zvyčajne sú to stop slová, ale nie všetky)

**Krok 4 – `lemmatizer.lemmatize(w_lower)`**: konvertuje slovo na jeho základný slovníkový tvar (lemu):

| Vstupné slovo | Léma |
|---|---|
| running | run |
| companies | company |
| developing | develop |
| glaciers | glacier |
| algorithms | algorithm |

**Rozdiel Lematizácia vs. Stemming:**

| Vlastnosť | Lematizácia | Stemming |
|---|---|---|
| Výstup | Skutočné slovníkové slovo | Orezaná prípona (nemusí byť slovo) |
| Príklad | `running` → `run` | `running` → `runn` |
| Príklad | `better` → `good` | `better` → `better` |
| Rýchlosť | Pomalšia | Rýchlejšia |
| Presnosť | Vyššia | Nižšia |
| Požiadavka | Potrebuje WordNet databázu | Jednoduchý algoritmus |

---

### 5. Slovník unikátnych lém

```python
all_lemmas = sorted(set(l for lemmas in doc_lemmas.values() for l in lemmas))
```

- **generátorový výraz** `l for lemmas in doc_lemmas.values() for l in lemmas` – prechádza cez lémy všetkých dokumentov naraz (dvojitý for v jednom výraze)
- `set(...)` – odstráni duplicity, každá léma je zastúpená len raz
- `sorted(...)` – zoradí abecedne → stĺpce matíc budú vždy v rovnakom deterministickom poradí

Výsledok: `all_lemmas` je zoznam napr. 150–200 unikátnych slov, ktoré tvoria **stĺpce** všetkých matíc.

---

### 6. TF – frekvenčná matica

```python
tf_matrix = pd.DataFrame(0, index=doc_names, columns=all_lemmas)

for doc_name, lemmas in doc_lemmas.items():
    for lemma in lemmas:
        tf_matrix.loc[doc_name, lemma] += 1
```

- Vytvoríme DataFrame naplnený nulami, kde riadky sú dokumenty a stĺpce sú lémy
- Pre každý dokument prechádzame jeho lémy a inkrementujeme príslušnú bunku
- `tf_matrix.loc[doc_name, lemma]` – prístup k bunke cez **label-based indexing**

Výsledok: matica s **absolútnymi frekvenciami** – koľkokrát sa daná léma vyskytuje v danom dokumente.

---

### 7. Binárna matica

```python
binary_matrix = (tf_matrix > 0).astype(int)
```

- `(tf_matrix > 0)` – porovnanie každej bunky s nulou, výsledok je DataFrame s hodnotami `True`/`False`
- `.astype(int)` – konverzia: `True → 1`, `False → 0`
- Celá operácia je **vektorizovaná** – pandas ju aplikuje na celú maticu naraz bez cyklu

---

### 8. Logaritmická matica

```python
log_matrix = tf_matrix.apply(lambda col: col.map(lambda x: round(math.log10(1 + x), 4)))
```

- `tf_matrix.apply(lambda col: ...)` – prechádza každý **stĺpec** (lemu) ako pandas Series
- `col.map(lambda x: ...)` – aplikuje funkciu na každú **bunku** v stĺpci
- `math.log10(1 + x)` – aplikuje logaritmický vzorec
- `round(..., 4)` – zaokrúhlenie na 4 desatinné miesta

---

### 9. IDF a TF-IDF matica

```python
N = len(doc_names)
df_series  = (tf_matrix > 0).sum(axis=0)
idf_series = df_series.apply(lambda df: round(math.log10(N / df), 4) if df > 0 else 0)
tfidf_matrix = tf_matrix.multiply(idf_series, axis=1).round(4)
```

**Riadok 1:** `N = 5` – celkový počet dokumentov.

**Riadok 2:** `(tf_matrix > 0).sum(axis=0)` – pre každú lému spočíta, v koľkých dokumentoch sa vyskytuje:
- `(tf_matrix > 0)` – boolovská matica True/False
- `.sum(axis=0)` – sumuje **po stĺpcoch** (cez riadky/dokumenty); `True` sa počíta ako 1
- Výsledok: `df_series` je Series s jednou hodnotou (document frequency) na každú lému

**Riadok 3:** IDF pre každú lému; podmienka `if df > 0 else 0` chráni pred delením nulou.

**Riadok 4:** `tf_matrix.multiply(idf_series, axis=1)` – násobí každý **stĺpec** matice príslušnou IDF hodnotou; `axis=1` (alebo `axis='columns'`) hovorí pandasom, aby zarovnal IDF vektor podľa stĺpcov.

---

### 10. Export do Excelu

```python
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'lemma_matrices.xlsx')
with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
    tf_matrix.to_excel(writer,     sheet_name='TF_frekvencia')
    binary_matrix.to_excel(writer, sheet_name='Binarna')
    log_matrix.to_excel(writer,    sheet_name='Logaritmicka')
    tfidf_matrix.to_excel(writer,  sheet_name='TF-IDF')
    idf_df = idf_series.reset_index()
    idf_df.columns = ['Lema', 'IDF']
    idf_df.to_excel(writer,        sheet_name='IDF', index=False)
```

- `pd.ExcelWriter` použitý ako **context manager** (`with`) – súbor sa automaticky správne zatvorí a uloží aj pri chybe
- `engine='openpyxl'` – knižnica zodpovedná za zápis do formátu `.xlsx`
- `idf_series.reset_index()` – prevedie pandas Series na DataFrame (pridá stĺpec s názvami lém ako index)

---

## Štatistické metódy a vzorce

### 1. TF – Term Frequency (absolútna frekvencia)

$$
TF(d,\, t) = \text{počet výskytov lémy } t \text{ v dokumente } d
$$

kde $d$ = dokument, $t$ = term (léma).

**Čo reprezentuje:** Koľkokrát sa dané slovo objaví v texte. Základná miera relevancie.

**Výhoda:** Jednoduchosť, priama interpretácia.

**Nevýhoda:** Dlhší dokument bude mať vyššie TF pre všetky slová, aj keď nie je "viac o téme". Navyše bežné slová (aj po odstránení stop slov) môžu dominovať.

---

### 2. Binárna reprezentácia

$$
bin(d,\, t) =
\begin{cases}
1 & \text{ak } TF(d, t) > 0 \\
0 & \text{inak}
\end{cases}
$$

**Čo reprezentuje:** Iba prítomnosť alebo neprítomnosť lémy. Nezáleží na počte výskytov.

**Príklad:** Léma `algorithm` sa v `text1.txt` vyskytuje 5-krát → binárna hodnota = **1**.

**Výhoda:** Extrémne jednoduchá, rýchla.

**Nevýhoda:** Stratí sa celá informácia o frekvencii – slovo s výskytom 1× a 100× majú rovnakú váhu 1.

---

### 3. Logaritmická TF

$$
\log TF(d,\, t) =
\begin{cases}
1 + \log_{10}(TF(d,\, t)) & \text{ak } TF(d, t) > 0 \\
0 & \text{inak}
\end{cases}
$$

**Prečo +1:** Bez +1 by platilo $\log_{10}(1) = 0$, čo by dalo hodnotu 0 slovu s jedným výskytom – rovnako ako slovu, ktoré sa nevyskytuje vôbec. Posun o 1 zaručuje $\log TF > 0$ pre každé slovo, ktoré sa vyskytuje.

**Prečo logaritmus:** Surová frekvencia rastie lineárne, ale jej *informatívna hodnota* rastie oveľa pomalšie. Logaritmus "skrotí" rozsah hodnôt:

| TF (surové) | $\log_{10}(TF)$ | $1 + \log_{10}(TF)$ |
|---|---|---|
| 1 | 0 | 1.000 |
| 10 | 1 | 2.000 |
| 100 | 2 | 3.000 |
| 1 000 | 3 | 4.000 |

Slovo s TF = 100 je len **3×** dôležitejšie (nie 100×) ako slovo s TF = 1.

---

### 4. IDF – Inverse Document Frequency (inverzná dokumentová frekvencia)

$$
IDF(t) = \log_{10}\left(\frac{N}{df(t)}\right)
$$

kde:
- $N$ = celkový počet dokumentov v kolekcii (tu: 5)
- $df(t)$ = document frequency = počet dokumentov, v ktorých sa léma $t$ vyskytuje (má TF > 0)

**Čo reprezentuje:** Ako **vzácna** je léma naprieč celou kolekciou. Čím vzácnejšia, tým vyššie IDF.

**Limitné prípady (dôležité pre skúšku):**

| Situácia | Výpočet | IDF | Interpretácia |
|---|---|---|---|
| Léma je vo **všetkých** dokumentoch ($df = N$) | $\log_{10}(5/5) = \log_{10}(1)$ | **0** | Neinformatívna – nedokáže odlíšiť dokumenty |
| Léma je v **jedinom** dokumente ($df = 1$) | $\log_{10}(5/1) = \log_{10}(5)$ | **max ≈ 0.699** | Unikátna – maximálna diskriminačná sila |
| Léma je v **polovici** dokumentov ($df = N/2$) | $\log_{10}(2)$ | **≈ 0.301** | Stredná diskriminačná sila |

**Kód výpočtu:**
```python
df_series  = (tf_matrix > 0).sum(axis=0)
idf_series = df_series.apply(lambda df: round(math.log10(N / df), 4) if df > 0 else 0)
```

- `(tf_matrix > 0)` → boolovská matica
- `.sum(axis=0)` → pre každý stĺpec (lému) spočíta, v koľkých riadkoch (dokumentoch) je True
- `if df > 0 else 0` → ochrana pred `log10(5/0) = log10(∞)`

---

### 5. TF-IDF

$$
TFIDF(d,\, t) = TF(d,\, t) \times IDF(t) = TF(d,\, t) \times \log_{10}\left(\frac{N}{df(t)}\right)
$$

V implementácii je TF-IDF vypočítané z **absolútneho TF** (nie z logaritmického):

```python
tfidf_matrix = tf_matrix.multiply(idf_series, axis=1).round(4)
```

**Čo reprezentuje:** Dôležitosť lémy v konkrétnom dokumente *relatívne voči celej kolekcii*. Slovo musí byť:
- **Časté** v danom dokumente (vysoké TF), **A zároveň**
- **Vzácne** v ostatných dokumentoch (vysoké IDF)

**Príklady interpretácie:**

| Situácia | TF | IDF | TF-IDF | Záver |
|---|---|---|---|---|
| Slovo časté v 1 dok., vzácne inde | Vysoké | Vysoké | **Vysoké** | Kľúčové slovo dokumentu |
| Slovo časté vo VŠETKÝCH dok. | Vysoké | 0 | **0** | Neinformatívne |
| Slovo vzácne v 1 dok. | Nízke | Vysoké | **Nízke** | Marginálny výskyt |

---

## Vysvetlenie kľúčových operácií v kóde

### `axis=0` vs `axis=1`

```
            léma1  léma2  léma3
text1.txt     3      0      1
text2.txt     0      2      4
text3.txt     1      1      0

axis=0: sumujeme NADOL (cez riadky) → výsledok = 1 hodnota na STĹPEC
        → [4, 3, 5]   (document frequency pre každú lému)

axis=1: sumujeme DOPRAVA (cez stĺpce) → výsledok = 1 hodnota na RIADOK
        → [4, 6, 2]   (celkový počet lém v každom dokumente)
```

### `apply` + `map` vs `multiply`

- `tf_matrix.apply(lambda col: col.map(lambda x: ...))` – aplikuje vlastnú Python funkciu na každú bunku; flexibilné, ale pomalšie (Python overhead)
- `tf_matrix.multiply(idf_series, axis=1)` – čistá pandas/numpy operácia; automatické zarovnanie podľa stĺpcov (broadcasting); rýchlejšie

### Ochrana pred delením nulou

```python
idf_series = df_series.apply(lambda df: round(math.log10(N / df), 4) if df > 0 else 0)
```

Podmienka `if df > 0 else 0` zabezpečí, že ak by sa léma nevyskytovala v žiadnom dokumente (čo sa tu nemôže stať, ale je to obranný kód), nevyhodí sa `ZeroDivisionError`. Ak skript spustíme nad prázdnymi súbormi, nezlyhá.

### `os.path.join` a `os.path.abspath`

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
fpath = os.path.join(SCRIPT_DIR, fname)
```

- `__file__` = cesta k aktuálnemu `.py` súboru
- `os.path.abspath(...)` = prevod na absolútnu cestu (funguje aj pri relatívnych cestách)
- `os.path.dirname(...)` = extrakcia priečinka (bez názvu súboru)
- `os.path.join(...)` = zostavenie cesty kompatibilne so všetkými OS (Windows používa `\`, Unix `/`)

---

## Code flow – diagram

```
START
  │
  ├─► Stiahnutie NLTK dát (punkt, wordnet, stopwords)
  │
  ├─► Načítanie text1.txt – text5.txt → documents {}
  │
  ├─► Pre každý dokument: extract_lemmas(text)
  │     ├─ sent_tokenize → vety
  │     ├─ word_tokenize → tokeny
  │     ├─ .lower() + filtrovanie (stop slová, isalpha, dĺžka)
  │     └─ lemmatizer.lemmatize → lémy
  │
  ├─► all_lemmas = sorted(set( všetky lémy ))
  │
  ├─► tf_matrix  ← počítadlo výskytov lém (riadky=dok., stĺpce=lémy)
  ├─► binary_matrix = (tf_matrix > 0).astype(int)
  ├─► log_matrix = apply( log10(1 + TF) )
  ├─► df_series  = (tf_matrix > 0).sum(axis=0)
  ├─► idf_series = log10(N / df)
  └─► tfidf_matrix = tf_matrix × idf_series
        │
        └─► ExcelWriter → lemma_matrices.xlsx (5 listov)
END
```

---

## Porovnanie všetkých reprezentácií

| Vlastnosť | TF | Binárna | Logaritmická TF | TF-IDF |
|---|---|---|---|---|
| Rozsah hodnôt | $[0, \infty)$ | $\{0, 1\}$ | $[0, \infty)$ | $[0, \infty)$ |
| Zachováva frekvenciu? | Áno (lineárne) | Nie | Áno (log-škála) | Áno (log-škála) |
| Zohľadňuje vzácnosť slova? | Nie | Nie | Nie | **Áno** |
| Penalizuje bežné slová? | Nie | Nie | Nie | **Áno** |
| Typické použitie | Základná analýza | Boolean retrieval | Vyhľadávanie | Štandard v IR |

---

## Otázky, ktoré môže položiť profesor

**Q: Čo je tokenizácia a prečo delíme najprv na vety?**
A: Tokenizácia je rozbitie textu na menšie časti (tokeny). Delíme najprv na vety pomocou `sent_tokenize`, pretože niektoré NLP nástroje (napr. tagger slovných druhov) pracujú presnejšie v kontexte celej vety. Potom každú vetu rozdelíme na slová pomocou `word_tokenize`.

---

**Q: Čo je lematizácia a čím sa líši od stemmingu?**
A: **Lematizácia** konvertuje slovo na jeho základný slovníkový tvar (lemu) s použitím gramatických pravidiel a databázy WordNet. Výsledok je vždy platné slovo (`running → run`, `better → good`). **Stemming** len mechanicky odrežie príponu pomocou heuristík – výsledok nemusí byť platné slovo (`running → runn`). Lematizácia je presnejšia, ale pomalšia.

---

**Q: Prečo filtrujem stop slová, krátke slová a nealfabetické tokeny?**
A: **Stop slová** (the, is, are, and...) sú funkčné slová bez sémantického obsahu – nemôžu odlíšiť dokumenty od seba. **Krátke slová** (< 3 znaky) sú zvyčajne predložky alebo zámenká, ktoré nesú málo informácie. **Nealfabetické tokeny** (čísla, interpunkcia, URL) by "znečistili" slovník nepotrebnými symbolmi.

---

**Q: Prečo TF a nie raw word count?**
A: TF a raw count sú tu to isté – oba sú absolútne počty výskytov. Surová frekvencia má nevýhodu, že dlhší dokument bude mať prirodzene vyššie TF pre všetky slová. Preto sa v pokročilejších systémoch TF normalizuje dĺžkou dokumentu. V tomto skripte sa normalizácia nerobí – pracujeme so surovým TF a kompenzujeme pomocou log-škálovania a IDF.

---

**Q: Prečo pri log TF používame +1?**
A: Bez +1 by platilo $\log_{10}(1) = 0$, čo by dalo váhu 0 slovu s jedným výskytom – rovnako ako slovu s výskytom 0. Posun o +1 zaručí $1 + \log_{10}(1) = 1$, čo správne odlíši prítomnosť od neprítomnosti.

---

**Q: Čo sa stane, ak $df = N$ (léma je vo všetkých dokumentoch)?**
A: $IDF = \log_{10}(N/N) = \log_{10}(1) = 0$. TF-IDF bude nulové pre všetky dokumenty. Léma nedokáže odlíšiť dokumenty medzi sebou – nemá diskriminačnú silu.

---

**Q: Čo sa stane, ak $df = 1$ (léma je iba v jednom dokumente)?**
A: $IDF = \log_{10}(N/1) = \log_{10}(5) \approx 0.699$. Léma dostane maximálnu IDF hodnotu – je unikátna pre daný dokument, čo je veľmi informatívne. TF-IDF bude v tomto dokumente vysoké a v ostatných nulové.

---

**Q: Čo znamená `axis=0` pri `.sum(axis=0)`?**
A: `axis=0` znamená sumovanie **smerom nadol** – teda cez riadky (dokumenty). Pre každý stĺpec (lému) dostaneme jeden súčet. Výsledkom je Series s jednou hodnotou na každú lému. `axis=1` by sumovalo cez stĺpce – výsledkom by bolo jedno číslo na každý dokument.

---

**Q: Prečo ukladáme štyri rôzne matice namiesto jednej?**
A: Každá reprezentácia je vhodná pre inú úlohu:
- **TF** = základná analýza, vstup pre ďalšie výpočty
- **Binárna** = keď záleží len na prítomnosti (Boolean vyhľadávanie, spam filter)
- **Logaritmická TF** = keď záleží na frekvencii, ale chceme potlačiť dominanciu veľmi frekventovaných slov
- **TF-IDF** = keď chceme zvýrazniť charakteristické slová každého dokumentu (vyhľadávanie, klasifikácia, zhlukovanie)

---

**Q: Prečo `multiply(idf_series, axis=1)` a nie priame `*`?**
A: `idf_series` je jednorozmerný vektor (Series) s hodnotou pre každú lému. Pri použití `*` by pandas mohol zarovnávať indexy nesprávne. `multiply(..., axis=1)` explicitne hovorí: "zarovnaj tento vektor podľa **stĺpcov** matice" – každý stĺpec matice (každá léma) sa vynásobí príslušnou IDF hodnotou. Je to pandas Broadcasting.

---

**Q: Aký je rozdiel medzi `apply` a `map`?**
A: `df.apply(func)` aplikuje funkciu na **stĺpec alebo riadok** (Series). `series.map(func)` aplikuje funkciu na každý **element** Series. V kóde sú kombinované: `apply` prechádza stĺpce, `map` aplikuje vzorec na každú bunku v stĺpci.

---

**Q: Prečo sa používa `set()` na stop slová?**
A: Vyhľadávanie v `set` je O(1) – konštantný čas, nezávislý od počtu stop slov. V `list` by bolo O(n). Keďže filtrovanie prebehne pre každé slovo každého dokumentu, ide o tisíce porovnaní – set je výrazne efektívnejší.

---

**Q: Čo je `doc_frequency` a ako sa líši od `term_frequency`?**
A:
- **Term Frequency** (TF) – koľkokrát sa slovo vyskytuje **v konkrétnom dokumente**; závisí od dokumentu aj slova
- **Document Frequency** (df) – v koľkých dokumentoch sa slovo vôbec vyskytuje; závisí iba od slova, nie od konkrétneho dokumentu. Používa sa na výpočet IDF.

---

## Zhrnutie najdôležitejších funkcií

| Funkcia / operácia | Modul | Účel |
|---|---|---|
| `sent_tokenize(text)` | `nltk` | Rozdelenie textu na vety |
| `word_tokenize(veta)` | `nltk` | Rozdelenie vety na tokeny (slová + interpunkcia) |
| `lemmatizer.lemmatize(slovo)` | `nltk.stem` | Prevod slova na základný tvar (lemu) |
| `stopwords.words('english')` | `nltk.corpus` | Zoznam stop slov pre angličtinu |
| `set(...)` | Python | Množina pre O(1) vyhľadávanie |
| `str.isalpha()` | Python | True ak reťazec obsahuje iba písmená |
| `pd.DataFrame(0, index=..., columns=...)` | `pandas` | Vytvorenie matice naplnenej nulami |
| `df.loc[riadok, stlpec]` | `pandas` | Label-based prístup k bunke |
| `(df > 0).astype(int)` | `pandas` | Boolovská maska prevedená na 0/1 |
| `df.apply(lambda col: col.map(...))` | `pandas` | Aplikácia funkcie na každú bunku |
| `(df > 0).sum(axis=0)` | `pandas` | Počet nenulových hodnôt v každom stĺpci |
| `df.multiply(series, axis=1)` | `pandas` | Násobenie matice vektorom po stĺpcoch |
| `math.log10(x)` | `math` | Logaritmus base 10 |
| `series.reset_index()` | `pandas` | Prevod Series na DataFrame |
| `pd.ExcelWriter(...)` | `pandas` | Zápis viacerých listov do jedného xlsx |
