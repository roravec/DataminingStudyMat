# NLP – Tokenizácia viet, POS tagging a lematizácia

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Skript spracuje 5 anglických textových dokumentov a z každého vytvorí **plochú tabuľku tokenov**, kde každý riadok reprezentuje jedno plnovýznamové slovo. Pre každé slovo sa zaznamená, z ktorej vety pochádza, aký POS tag mu bol priradený, aký je jeho základný tvar (lema) a na ktorom mieste vo vete stojí (po odstránení stop slov).

Výsledok je uložený do Excelu `tokens.xlsx` – jeden riadok = jedno slovo.

---

### Vstup

Päť textových súborov `text1.txt` – `text5.txt`, každý s anglickým odborným textom z inej oblasti:

| Súbor | Téma |
|---|---|
| `text1.txt` | Umelá inteligencia a robotika |
| `text2.txt` | Klimatické zmeny |
| `text3.txt` | Ľudský mozog a neurológia |
| `text4.txt` | Vesmírny výskum |
| `text5.txt` | Globálna ekonomika |

---

### Výstup

Jeden Excel súbor `tokens.xlsx` s nasledujúcimi stĺpcami:

| Stĺpec | Popis | Príklad |
|---|---|---|
| `Dokument` | Zdrojový textový súbor | `text1.txt` |
| `ID_veta` | Globálny identifikátor vety (naprieč všetkými doc.) | `3` |
| `Slovo` | Originálny token (zachovaný originálny prípad) | `robots` |
| `Tag` | Penn Treebank POS tag | `NNS` |
| `Lemma` | Základný tvar slova (lema) | `robot` |
| `Poradie` | Poradie slova vo vete (bez stop slov) | `2` |
| `Slovny_Druh` | Jednopísmenná skratka slovného druhu | `N` |

### Tok súborov

```
text1.txt  ─┐
text2.txt   │
text3.txt   ├──► lemmatization.py ──► tokens.xlsx
text4.txt   │
text5.txt  ─┘
```

### Ukážka výstupu (prvých 11 riadkov)

```
ID_veta  Slovo       Tag   Lemma       Poradie  Slovny_Druh
1        train       JJ    train       1        J
1        robot       NN    robot       2        N
1        using       VBG   using       3        V
1        AI          NNP   ai          4        N
1        supercom    NNS   supercom    5        N
1        Before      IN    before      6        I
1        joined      JJ    joined      7        J
1        University  NNP   university  8        N
```

---

## NLP pipeline – čo sa deje s každým textom

Pre každý z 5 dokumentov, a pre každú vetu v ňom, prebehne táto séria krokov:

```
"Robots must be able to sense and make decisions."
          │
          ▼  sent_tokenize()
["Robots must be able to sense and make decisions."]
          │
          ▼  word_tokenize()
["Robots", "must", "be", "able", "to", "sense", "and", "make", "decisions", "."]
          │
          ▼  pos_tag()
[("Robots","NNS"), ("must","MD"), ("be","VB"), ("able","JJ"), ("to","TO"),
 ("sense","NN"), ("and","CC"), ("make","VB"), ("decisions","NNS"), (".","." )]
          │
          ▼  filter: word.lower() not in stop_words AND word.isalpha()
[("Robots","NNS"), ("sense","NN"), ("make","VB"), ("decisions","NNS")]
          │
          ▼  lemmatizer.lemmatize(word.lower())
  robot        sense       make        decision
```

---

## Postup riešenia – krok za krokom

### 1. Importy a stiahnutie NLTK dát

```python
import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer

nltk.download('punkt_tab',                      quiet=True)
nltk.download('punkt',                          quiet=True)
nltk.download('averaged_perceptron_tagger',     quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('stopwords',                      quiet=True)
nltk.download('wordnet',                        quiet=True)
```

| Knižnica / modul | Účel |
|---|---|
| `nltk` | Natural Language Toolkit – NLP nástroje |
| `pandas` | Práca s DataFrame (tabuľková matica, export do xlsx) |
| `stopwords` | Predpripravený zoznam stop slov pre angličtinu |
| `word_tokenize`, `sent_tokenize` | Rozdelenie textu na slová / vety |
| `WordNetLemmatizer` | Lematizátor – prevod slova na základný tvar |
| `punkt_tab` / `punkt` | Pravidlá pre tokenizáciu viet a slov |
| `averaged_perceptron_tagger` | Štatistický model pre POS tagging |
| `wordnet` | Lexikálna databáza anglických slov pre lematizáciu |

---

### 2. Inicializácia

```python
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()
```

- `set(...)` – stop slová uložené do **množiny**, lebo vyhľadávanie je O(1) namiesto O(n)
- `WordNetLemmatizer()` – jeden objekt lematizátora sa použije opakovane pre všetky slová

---

### 3. TAG\_MAP – prekladová tabuľka Penn Treebank tagov

```python
TAG_MAP = {
    'CC':'C', 'CD':'C', 'DT':'D', 'EX':'E', 'FW':'F', 'IN':'I',
    'JJ':'J', 'JJR':'J', 'JJS':'J', 'MD':'M',
    'NN':'N', 'NNS':'N', 'NNP':'N', 'NNPS':'N',
    'PRP':'P', 'PRP$':'P', 'PDT':'D', 'POS':'P',
    'RB':'R', 'RBR':'R', 'RBS':'R', 'RP':'R',
    'TO':'T', 'UH':'U',
    'VB':'V', 'VBD':'V', 'VBG':'V', 'VBN':'V', 'VBP':'V', 'VBZ':'V',
    'WDT':'W', 'WP':'W', 'WP$':'W', 'WRB':'W',
    '(':'(', ')':')', ',':',', '.':'.', ':':':',
}
```

Tagger vráti plné Penn Treebank tagy (napr. `NNS`). `TAG_MAP.get(tag, tag[0] if tag else '?')` ich preloží na jednopísmenné kategórie.

| Penn Treebank tag | Jednopísmenná skratka | Slovenský ekvivalent |
|---|---|---|
| `NN`, `NNS`, `NNP`, `NNPS` | `N` | podstatné meno |
| `VB`, `VBD`, `VBG`, `VBN`, `VBP`, `VBZ` | `V` | sloveso |
| `JJ`, `JJR`, `JJS` | `J` | prídavné meno |
| `RB`, `RBR`, `RBS`, `RP` | `R` | príslovka |
| `PRP`, `PRP$` | `P` | zámenko |
| `IN` | `I` | predložka / spojka |
| `DT`, `PDT` | `D` | člen / determiner |
| `MD` | `M` | modálne sloveso (can, will, must…) |
| `CC`, `CD` | `C` | koordinačná spojka / číslovka |
| `WDT`, `WP`, `WP$`, `WRB` | `W` | opytovacia forma |
| `TO` | `T` | particle "to" |
| `UH` | `U` | citoslovce |
| `FW` | `F` | cudzie slovo |
| `EX` | `E` | existenciálne "there" |

Záložné pravidlo `tag[0] if tag else '?'` vezme prvý znak tagu, ak tag nie je v `TAG_MAP`.

---

### 4. Načítanie textov a spracovanie

```python
TEXT_FILES = [f"text{i}.txt" for i in range(1, 6)]

rows = []
sentence_id = 0

for fname in TEXT_FILES:
    with open(fname, encoding='utf-8') as f:
        text = f.read()
    sentences = sent_tokenize(text)
    ...
```

- `TEXT_FILES` = list comprehension generujúci `['text1.txt', ..., 'text5.txt']`
- `sentence_id` je **globálny** – neresetuje sa medzi súbormi; každá veta dostane unikátne číslo naprieč všetkými 5 dokumentmi

---

### 5. Tokenizácia viet

```python
sentences = sent_tokenize(text)
```

`sent_tokenize()` použije **Punkt tokenizátor** (štatistický model) na rozdelenie textu na zoznam viet. Detekuje hranice viet na základe interpunkcie, ale aj skratiek (napr. `Mr.`, `Dr.` nie sú koniec vety). Výsledok: `["Veta prvá.", "Veta druhá.", ...]`

---

### 6. Tokenizácia slov + POS tagging

```python
words = word_tokenize(sentence)
tagged = nltk.pos_tag(words)
```

**`word_tokenize()`**: rozdelí vetu na tokeny. Rieši aj kontrakcie: `"I'm"` → `["I", "'m"]`, `"don't"` → `["do", "n't"]`.

**`nltk.pos_tag()`**: priradí každému tokenu Penn Treebank POS tag. Výstup je zoznam dvojíc:
```python
[("Robots", "NNS"), ("must", "MD"), ("sense", "VB"), ...]
```

Tagger je natrénovaný na **Penn Treebank** korpuse (americká angličtina, cca 1 milión tokenov). Používa **Averaged Perceptron** – diskriminatívny klasifikátor, ktorý sa učí lineárne váhy pre kombinácie príznakov (prefix slova, suffix, okolité slová, predchádzajúci tag).

---

### 7. Filtrovanie tokenov

```python
for word, tag in tagged:
    if word.lower() in stop_words:
        continue
    if not word.isalpha():
        continue
```

**Filter 1 – stop slová**: `word.lower() in stop_words` – neinformatívne funkčné slová ako `the`, `is`, `are`, `and`, `of`, `to` sú vylúčené. Normalizujeme na malé písmená pred porovnaním, lebo stop slová sú v množine malými písmenami.

**Filter 2 – `isalpha()`**: vylúči tokeny obsahujúce ne-písmenkové znaky:
- interpunkciu: `.`, `,`, `(`, `)`, `?`
- čísla: `360`, `2020`
- zmiešané tokeny: `AI-powered`, `sim2real`, `n't`
- apostrofy: `'s`, `'m`

Pozor: `isalpha()` vylúči aj tokeny ako `AI` – nie, `AI` prechádza, lebo obsahuje len písmená. Vylúčilo by sa napríklad `AI2` alebo `sim2real`.

---

### 8. Počítanie poradia a lematizácia

```python
position = 0
...
position += 1
lemma = lemmatizer.lemmatize(word.lower())
```

- `position` sa resetuje na `0` pre každú novú vetu a inkrementuje sa len pre tokeny, ktoré **prešli** oboma filtrami → poradie je bez stop slov
- `lemmatizer.lemmatize(word.lower())` – `word.lower()` normalizuje pred lematizáciou (lematizátor je case-sensitive)

---

### 9. Zostavenie riadku a export

```python
rows.append({
    'Dokument':    fname,
    'ID_veta':     sentence_id,
    'Slovo':       word,
    'Tag':         tag,
    'Lemma':       lemma,
    'Poradie':     position,
    'Slovny_Druh': slovny_druh,
})

df = pd.DataFrame(rows)
df.to_excel('tokens.xlsx', index=False)
```

- `rows` je Python list slovníkov; každý slovník = jeden riadok tabuľky
- `pd.DataFrame(rows)` – pandas automaticky vytvorí stĺpce z kľúčov slovníkov
- `to_excel(..., index=False)` – neuloží pandas row-index (0, 1, 2...) ako extra stĺpec

---

## Code flow – diagram

```
START
  │
  ├─► Stiahnutie NLTK dát (punkt, tagger, stopwords, wordnet)
  │
  ├─► Inicializácia: stop_words (set), lemmatizer, TAG_MAP
  │
  ├─► sentence_id = 0
  │
  ├─► Pre každý súbor (text1.txt – text5.txt):
  │     ├─ Načítanie textu (open + read)
  │     ├─ sent_tokenize(text)  →  zoznam viet
  │     │
  │     └─ Pre každú vetu:
  │           ├─ sentence_id += 1
  │           ├─ word_tokenize(veta)  →  zoznam tokenov
  │           ├─ nltk.pos_tag(tokeny)  →  [(slovo, tag), ...]
  │           ├─ position = 0
  │           │
  │           └─ Pre každý (word, tag):
  │                 ├─ IF word.lower() in stop_words → preskočiť
  │                 ├─ IF NOT word.isalpha()         → preskočiť
  │                 ├─ position += 1
  │                 ├─ lemma = lemmatizer.lemmatize(word.lower())
  │                 ├─ slovny_druh = TAG_MAP.get(tag, tag[0])
  │                 └─ rows.append({...})
  │
  ├─► pd.DataFrame(rows)
  │
  └─► df.to_excel('tokens.xlsx', index=False)
END
```

---

## Kľúčové NLP metódy a koncepty

### 1. Tokenizácia

Tokenizácia je rozbitie textu na menšie jednotky – tokeny. V skripte prebehne na dvoch úrovniach:

**Tokenizácia viet** (`sent_tokenize`): detekuje hranice viet. Punkt tokenizátor je **štatistický model** trénovaný na veľkom korpuse – naučil sa, pri ktorých znakoch je bodka koniec vety a kedy je to skratka. Nie je to jednoduchý split podľa `.`.

**Tokenizácia slov** (`word_tokenize`): rozdelí vetu na tokeny. Používa regulárne výrazy a pravidlá pre angličtinu. Rieši kontrakcie, interpunkciu, apostrofy.

---

### 2. POS Tagging (morfologická anotácia)

POS tagging (Part-of-Speech tagging) priradí každému tokenu jeho slovný druh v kontexte vety.

`nltk.pos_tag()` používa **Averaged Perceptron Tagger** – diskriminatívny sekvenčný klasifikátor.

**Príznaky (features)**, ktoré tagger používa pre každý token:
- prefix a suffix slova (napr. `-ing`, `-ed`, `-tion`)
- tvar slova (veľké písmeno, číslo v slove, interpunkcia)
- samotné slovo
- okolité slová (ľavý a pravý kontext)
- tag predchádzajúceho tokenu (sekvenčná závislosť)

**Výstup:** zoznam dvojíc `(token, penn_treebank_tag)`:

```python
nltk.pos_tag(["The", "robot", "learns", "fast"])
# → [("The","DT"), ("robot","NN"), ("learns","VBZ"), ("fast","RB")]
```

---

### 3. Lematizácia

Lematizácia prevedie slovo na jeho základný slovníkový tvar – **lemu**.

```python
lemmatizer = WordNetLemmatizer()
lemmatizer.lemmatize("robots")    # → "robot"
lemmatizer.lemmatize("running")   # → "running"  (!) – predvolená POS je N
lemmatizer.lemmatize("running", pos='v')  # → "run"
```

`WordNetLemmatizer` používa **WordNet** – lexikálnu databázu anglického jazyka, kde sú slová zoskupené do tzv. synsetov (skupín synoným). Lematizátor vyhľadá slovo v databáze a nájde jeho základný tvar.

**Dôležité:** predvolená hodnota parametra `pos` je `'n'` (noun). Ak nešpecifikujeme slovný druh, lematizátor vždy predpokladá podstatné meno. V skripte sa `pos` nešpecifikuje – to je zjednodušenie.

| Vstupné slovo | Lema (pos='n') | Lema (pos='v') |
|---|---|---|
| `running` | `running` | `run` |
| `better` | `better` | `better` |
| `robots` | `robot` | `robot` |
| `companies` | `company` | `company` |
| `algorithms` | `algorithm` | `algorithm` |

**Lematizácia vs. Stemming:**

| Vlastnosť | Lematizácia | Stemming |
|---|---|---|
| Výstup | Platné slovníkové slovo | Orezaná prípona (nemusí byť slovo) |
| Príklad | `running` → `run` | `running` → `runn` |
| Príklad | `better` → `good` | `better` → `better` |
| Rýchlosť | Pomalšia | Rýchlejšia |
| Presnosť | Vyššia | Nižšia |
| Požiadavka | WordNet databáza | Jednoduchý algoritmus (Porter, Snowball) |

---

### 4. Stop slová

Stop slová sú bežné funkčné slová anglického jazyka, ktoré nenesú sémantický obsah a nedokážu odlíšiť dokumenty od seba: `the`, `is`, `are`, `and`, `of`, `to`, `a`, `in`, `that`, `it`, `was`, `he`, `she`, ...

NLTK obsahuje predpripravený zoznam pre desiatky jazykov. Pre angličtinu má cca 179 slov.

```python
stop_words = set(stopwords.words('english'))
# Príklad: {'i', 'me', 'my', 'myself', 'we', 'our', 'the', 'a', 'an', ...}
```

Použitie `set()` namiesto `list()` zabezpečí O(1) vyhľadávanie pri každom porovnaní `word.lower() in stop_words`.

---

## Vysvetlenie kľúčových operácií v kóde

### `word.isalpha()`

Metóda vráti `True` iba ak reťazec obsahuje výhradne písmenkové znaky (a-z, A-Z, vrátane Unicode písmen). Praktický efekt filtrovania:

| Token | `isalpha()` | Dôvod |
|---|---|---|
| `robot` | `True` | len písmená |
| `AI` | `True` | len písmená |
| `sim2real` | `False` | obsahuje číslicu |
| `AI-powered` | `False` | obsahuje pomlčku |
| `n't` | `False` | obsahuje apostrof |
| `360` | `False` | len číslice |
| `.` | `False` | interpunkcia |

### `TAG_MAP.get(tag, tag[0] if tag else '?')`

`dict.get(key, default)` vráti hodnotu pre kľúč, alebo `default` ak kľúč neexistuje.
- Ak je tag v `TAG_MAP` (napr. `'NN'`) → vráti `'N'`
- Ak tag **nie je** v `TAG_MAP` → vráti prvý znak tagu (`tag[0]`), napr. pre neznámy tag `'XY'` vráti `'X'`
- Ak je tag prázdny reťazec → vráti `'?'`

### Globálny `sentence_id`

`sentence_id` sa **neresetuje** pri prechode na nový súbor – rastie monotónne naprieč všetkými 5 dokumentmi. Tým dostane každá veta unikátne číslo naprieč celou kolekciou. Ak by sa resetovalo per-dokument, veta č. 1 z `text1.txt` a veta č. 1 z `text2.txt` by mali rovnaké ID.

### `position` – poradie v rámci vety

`position` sa resetuje na `0` pre **každú novú vetu** (nie každý dokument). Inkrementuje sa len pre tokeny, ktoré prešli oboma filtrami (nie stop slovo, `isalpha()` = True). Výsledkom je poradie plnovýznamových slov vo vete bez stop slov.

---

## Zhrnutie najdôležitejších funkcií

| Funkcia / operácia | Modul | Účel |
|---|---|---|
| `sent_tokenize(text)` | `nltk` | Rozdelenie textu na vety (Punkt tokenizátor) |
| `word_tokenize(veta)` | `nltk` | Rozdelenie vety na tokeny |
| `nltk.pos_tag(zoznam)` | `nltk` | Priradenie Penn Treebank POS tagov tokenom |
| `lemmatizer.lemmatize(slovo)` | `nltk.stem` | Prevod slova na lemu (základný tvar) |
| `stopwords.words('english')` | `nltk.corpus` | Zoznam stop slov pre angličtinu |
| `set(...)` | Python | Množina pre O(1) vyhľadávanie |
| `str.isalpha()` | Python | True ak reťazec obsahuje iba písmená |
| `str.lower()` | Python | Normalizácia na malé písmená |
| `TAG_MAP.get(tag, default)` | Python | Preklad Penn Treebank tagu na skratku |
| `pd.DataFrame(rows)` | `pandas` | Vytvorenie tabuľky zo zoznamu slovníkov |
| `df.to_excel(...)` | `pandas` | Export tabuľky do xlsx súboru |

---

## Otázky, ktoré môže položiť profesor

**Q: Čo je tokenizácia a prečo delíme najprv na vety a potom na slová?**

A: Tokenizácia je rozbitie textu na menšie jednotky. Najprv delíme na vety pomocou `sent_tokenize`, pretože niektoré NLP nástroje (najmä POS tagger) pracujú presnejšie v kontexte celej vety – vedia využiť okolité slová na určenie slovného druhu. Potom každú vetu rozdelíme na slová pomocou `word_tokenize`.

---

**Q: Čo je POS tagging a akú metódu používa NLTK?**

A: POS tagging (Part-of-Speech tagging) je morfologická anotácia – každému tokenu sa priradí jeho slovný druh (podstatné meno, sloveso, prídavné meno...). NLTK používa **Averaged Perceptron Tagger** natrénovaný na Penn Treebank korpuse. Klasifikátor sa rozhoduje na základe príznakov: suffix slova, prefix, okolité slová a tag predchádzajúceho tokenu.

---

**Q: Čo je lematizácia a čím sa líši od stemmingu?**

A: **Lematizácia** konvertuje slovo na jeho základný slovníkový tvar pomocou WordNet databázy. Výsledok je vždy platné anglické slovo (`robots → robot`, `companies → company`). **Stemming** len mechanicky odrežie príponu pomocou heuristík – výsledok nemusí byť platné slovo (`running → runn` pri Porter stemmeri). Lematizácia je presnejšia, ale pomalšia a vyžaduje WordNet.

---

**Q: Prečo `lemmatizer.lemmatize(word.lower())` a nie `lemmatizer.lemmatize(word)`?**

A: `WordNetLemmatizer` je **case-sensitive** – vyhľadáva slovo v databáze WordNet. `"Robot"` (s veľkým R) by mohol nájsť iný záznam ako `"robot"`. Normalizáciou na malé písmená pred lematizáciou zabezpečíme konzistentné výsledky. Podobne pri porovnávaní so stop slovami: `word.lower() in stop_words` – stop slová sú v množine malými písmenami.

---

**Q: Prečo filtrujem stop slová a nealfabetické tokeny?**

A: **Stop slová** (`the`, `is`, `are`, `and`...) sú funkčné slová bez sémantického obsahu – nedokážu odlíšiť témy dokumentov. **Nealfabetické tokeny** (interpunkcia, čísla, URL, zmesi ako `sim2real`) by zaplnili tabuľku symbolmi bez lingvistickej hodnoty. Po oboch filtroch zostanú len plnovýznamové anglické slová.

---

**Q: Prečo používame `set()` na stop slová namiesto `list()`?**

A: Vyhľadávanie v `set` je **O(1)** – konštantný čas, nezávislý od počtu prvkov. V `list` by bolo O(n). Keďže filtrovanie prebehne pre každý token každého dokumentu (tisíce porovnaní), `set` je výrazne efektívnejší.

---

**Q: Čo je Penn Treebank a prečo je `NNS` iné od `NN`?**

A: Penn Treebank je referenčný lingvistický korpus americkej angličtiny (cca 1 milión tokenov) s ručne anotovanými POS tagmi. `NN` = podstatné meno v singulári (`robot`), `NNS` = podstatné meno v pluráli (`robots`), `NNP` = vlastné meno singulár (`Texas`), `NNPS` = vlastné meno plurál (`Vikings`). Skript ich všetky mapuje na `N` – rozlíšenie plurál/singulár pre naše účely nie je potrebné.

---

**Q: Čo sa stane, ak token prejde stop-slovným filtrom, ale nie `isalpha()` filtrom?**

A: Token sa preskočí. Napríklad `"n't"` nie je stop slovo, ale `isalpha()` vráti `False` (obsahuje apostrof) – token sa vylúči. Podobne čísla alebo interpunkcia prechádzajúca stop slovným filtrom sú vylúčené `isalpha()`.

---

**Q: Čo znamená, že `sentence_id` je globálny?**

A: `sentence_id` sa neresetuje pri prechode na nový súbor – rastie naprieč všetkými 5 dokumentmi. Prvá veta `text1.txt` dostane ID 1, posledná veta `text1.txt` napr. ID 15, prvá veta `text2.txt` dostane ID 16, atď. Tým je každá veta unikátne identifikovateľná v celej tabuľke. Stĺpec `Dokument` dodá informáciu, z ktorého súboru veta pochádza.

---

**Q: Prečo `position` počíta len slová po filtrovaní a nie všetky tokeny?**

A: Poradie `position` odráža pozíciu plnovýznamového slova vo vete **bez stop slov a interpunkcie**. Ak by sme počítali všetky tokeny, poradie by záviselo od počtu stop slov a interpunkcie pred daným slovom – čo je menej informatívne. Takto dostaneme poradie slov, ktoré sú skutočne zaujímavé.

---

**Q: Prečo `pos_tag()` voláme pred filtrovaním a nie po?**

A: POS tagger potrebuje **celú vetu** vrátane stop slov, interpunkcie a pomocných slov, pretože kontext okolitých slov je kľúčový pre správne určenie slovného druhu. Napríklad `"can"` môže byť modálne sloveso (`MD`) alebo podstatné meno (`NN`) – tagger to určí z kontextu. Ak by sme pred tagovaním odstránili stop slová, kontext by bol narušený a tagy by boli menej presné.

