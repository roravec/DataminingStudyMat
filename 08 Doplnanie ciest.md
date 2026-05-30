# Task 5 – Dopĺňanie chýbajúcich ciest (Missing Path Completion)

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Web log zachytáva len stránky, ktoré používateľ **skutočne navštívil** (HTTP požiadavky na server). Ak používateľ preskočil z `/index.php` priamo na `/katedra/matematika`, log môže obsahovať iba tieto dve URL. No realita navigácie webu je, že medzi nimi mohla existovať jedna alebo viac **prechodných stránok** (napr. `/katedra`), cez ktoré musel prejsť podľa štruktúry webu — no tieto stránky mu server dodal z cache a v logu nie sú.

Skript sa snaží tieto chýbajúce medzikroky **zrekonštruovať** pomocou BFS (Breadth-First Search) prehľadávania mapy webu vybudovanej priamo z logu.

**Spracovávajú sa 4 metódy sedenií** (výstupy Task 4) — každá metóda má vlastný výstupný súbor.

---

### Vstup a výstup

```
wm2020projekt_sessions.csv
          │
          │  strip_domain()           ← normalizácia URL
          │  build_web_map()          ← mapa odkazov z Referrer→URL párov
          │  bfs_find_path()          ← BFS hľadanie cesty medzi stránkami
          │  fill_missing_paths()     ← vkladanie chýbajúcich záznamov
          │  run_subtask()            ← wrapper pre jednu metódu sedení
          ▼
wm2020projekt_paths_sttmean.csv
wm2020projekt_paths_sttq.csv
wm2020projekt_paths_rlength.csv
wm2020projekt_paths_href.csv
```

---

## Postup riešenia – krok za krokom

### Krok 1: Normalizácia URL — `strip_domain()`

```python
def strip_domain(url):
    if "://" in url:
        start     = url.find("://") + 3
        slash_pos = url.find("/", start)
        return url[slash_pos:] if slash_pos != -1 else "/"
    return url
```

V logu sa URL vyskytujú v dvoch formátoch:
- **Absolútna URL:** `https://www.ukf.sk/o-nas`
- **Relatívna URL (path):** `/o-nas`

Pre porovnanie a budovanie mapy webu potrebujeme oba formáty previesť na samotný path.

**Ako `strip_domain()` funguje:**

```
"https://www.ukf.sk/o-nas"
         ↑   find("://") → pozícia 5
         start = 5 + 3 = 8  → začíname od "www.ukf.sk/o-nas"
         slash_pos = find("/", 8) → pozícia 18
         výsledok: "/o-nas"

"/o-nas"
         "://" sa nenachádza → vracia sa "/o-nas" bez zmeny

"-"      (prázdny referrer v logu)
         "://" sa nenachádza → vracia sa "-"
```

---

### Krok 2: Budovanie mapy webu — `build_web_map()`

```python
def build_web_map(df):
    web_map = {}   # dict: {zdrojová_stránka: set(cieľové_stránky)}

    for i in range(len(df)):
        referrer = strip_domain(df["Referrer"].iloc[i])
        url      = df["URL"].iloc[i]

        if referrer and referrer != "-" and referrer != url:
            if referrer not in web_map:
                web_map[referrer] = set()
            web_map[referrer].add(url)

    return web_map
```

**Čo je web mapa (web map)?**  
Orientovaný graf, kde vrcholy sú stránky a hrany sú hyperlinky (hypertextové spojenia). `web_map["/o-nas"] = {"/o-nas/historia", "/o-nas/zamestnanci"}` znamená, že zo stránky `/o-nas` vedú linky na dve ďalšie stránky.

**Odkiaľ pochádza informácia o linkách?**  
Zo stĺpca `Referrer` — keď používateľ klikne na odkaz na stránke `/o-nas` a dostane sa na `/o-nas/historia`, server dostane požiadavok s `Referrer: /o-nas`. Toto hovorí: "na stránke `/o-nas` existuje odkaz na `/o-nas/historia`."

```
Log záznam:
  URL      = "/o-nas/historia"
  Referrer = "/o-nas"

→ web_map["/o-nas"].add("/o-nas/historia")
```

**Prečo `set()` namiesto `list()`?**  
Jedna hrana (odkaz) sa môže objaviť v logu tisíckrát (ak ju veľa ľudí kliklo). `set` automaticky uchováva každú hranu len raz — duplicity sú automaticky ignorované. `list.append()` by každý výskyt uložil znova.

**Prečo `referrer != url`?**  
Vylúčime samoreflexy (stránka odkazujúca samu na seba) — tie by v BFS mohli vytvoriť zbytočné cykly.

---

### Krok 3: BFS hľadanie cesty — `bfs_find_path()`

**BFS (Breadth-First Search)** = prehľadávanie do šírky. Prechádza grafom vrstvu po vrstve: najprv všetky stránky vo vzdialenosti 1, potom vo vzdialenosti 2, atď. Garantuje, že nájde **najkratšiu cestu** medzi dvoma uzlami.

```python
from collections import deque

def bfs_find_path(web_map, start_url, end_url, max_depth):
    if start_url == end_url:
        return []
    if start_url not in web_map:
        return None

    queue   = deque()
    visited = set()

    queue.append([start_url])   # fronta obsahuje cesty (zoznamy), nie len uzly
    visited.add(start_url)

    while len(queue) > 0:
        current_path = queue.popleft()   # O(1) operácia – preto deque
        current_node = current_path[-1]  # posledný uzol v aktuálnej ceste

        if len(current_path) > max_depth:
            return None   # príliš hlboké – zastavíme

        if current_node not in web_map:
            continue   # slepá ulička

        for neighbor in web_map[current_node]:
            if neighbor in visited:
                continue   # vyhnutie sa cyklom

            new_path = current_path + [neighbor]

            if neighbor == end_url:
                return new_path[1:-1]   # vracia MEDZIKROKY (bez start a end)

            visited.add(neighbor)
            queue.append(new_path)

    return None   # cesta neexistuje
```

**Vizualizácia BFS na príklade:**

```
Hľadáme cestu: "/index" → "/katedra/matematika"
web_map: {"/index": {"/o-nas", "/katedra"},
          "/katedra": {"/katedra/matematika", "/katedra/fyzika"}}

Štart: queue = [["/index"]], visited = {"/index"}

Iterácia 1:
  current_path = ["/index"], current_node = "/index"
  susedia: "/o-nas", "/katedra"
  
  neighbor "/o-nas": nový → new_path = ["/index", "/o-nas"]
    ≠ end_url → pridáme do queue, visited.add("/o-nas")
  
  neighbor "/katedra": nový → new_path = ["/index", "/katedra"]
    ≠ end_url → pridáme do queue, visited.add("/katedra")

  queue = [["/index","/o-nas"], ["/index","/katedra"]]

Iterácia 2:
  current_path = ["/index", "/o-nas"], current_node = "/o-nas"
  "/o-nas" nie je v web_map → continue (slepá ulička)

Iterácia 3:
  current_path = ["/index", "/katedra"], current_node = "/katedra"
  susedia: "/katedra/matematika", "/katedra/fyzika"
  
  neighbor "/katedra/matematika": == end_url!
    new_path = ["/index", "/katedra", "/katedra/matematika"]
    return new_path[1:-1] = ["/katedra"]   ← iba medzikrok!
```

**Prečo `new_path[1:-1]` (bez start a end)?**  
`new_path[0]` = `start_url` — tá v logu **už existuje** (aktuálny záznam). `new_path[-1]` = `end_url` — tá v logu **tiež existuje** (nasledujúci záznam). Vkladáme len stránky, ktoré chýbajú medzi nimi.

**Prečo `deque` a nie `list`?**  

| Operácia | `list` | `deque` |
|---|---|---|
| `append()` (pridanie na koniec) | $O(1)$ | $O(1)$ |
| `pop(0)` (odobranie zo začiatku) | $O(n)$ | $O(1)$ |

`list.pop(0)` musí posunúť **všetky** zvyšné prvky — preto je $O(n)$. Pri veľkej fronte (stovky ciest) by to bolo výrazne pomalšie. `deque.popleft()` je vždy $O(1)$.

**`max_depth` parameter — prečo obmedziť hĺbku?**  
Bez obmedzenia by BFS mohol prehľadávať celý web, hľadajúc cestu aj cez desiatky medzikrokov. Dlhé cesty sú nerealistické — ak BFS nenájde cestu do hĺbky 4 (resp. 6 pre RLength), pravdepodobne žiadna realistická cesta neexistuje.

| Metóda | max\_depth |
|---|---|
| STT\_MEAN | 4 |
| STT\_Q | 4 |
| hRef | 4 |
| RLength | 6 |

**Prečo RLength má hĺbku 6?**  
RLength generuje tendenčne **dlhšie sedenia** (väčší prah → menej delení). Dlhšie sedenia = väčšie navigačné skoky medzi po sebe idúcimi stránkami → je pravdepodobnejšie, že medzi nimi je viac medzikrokov.

---

### Krok 4: Vyplnenie chýbajúcich záznamov — `fill_missing_paths()`

Pre každé sedenie každého používateľa iterujeme cez po sebe idúce páry záznamov a hľadáme BFS cestu:

```python
def fill_missing_paths(df, session_col, web_map, max_depth):
    new_rows = []

    for session_id in df[session_col].unique():
        session_df = df[df[session_col] == session_id].sort_values("unixtime")

        for j in range(len(session_df) - 1):
            curr_row  = session_df.iloc[j]
            next_row  = session_df.iloc[j + 1]

            start_url = curr_row["URL"]
            end_url   = next_row["URL"]
            curr_time = curr_row["unixtime"]
            next_time = next_row["unixtime"]

            path = bfs_find_path(web_map, start_url, end_url, max_depth)

            if path is None or len(path) == 0:
                continue   # žiadne medzikroky

            # Lineárna interpolácia času pre medzikroky
            n_steps   = len(path)
            time_step = (next_time - curr_time) / (n_steps + 1)

            for k in range(n_steps):
                t_k = curr_time + (k + 1) * time_step   # čas medzikroku

                filled_row = {
                    "IP"       : curr_row["IP"],
                    "DateTime" : "FILLED",
                    "URL"      : path[k],
                    "StatusCode": curr_row["StatusCode"],
                    "Method"   : curr_row["Method"],
                    "Referrer" : "FILLED",
                    "Agent"    : curr_row["Agent"],
                    "unixtime" : int(t_k),
                    "UserID"   : curr_row["UserID"],
                    "Length"   : None,
                    session_col: session_id,
                }
                new_rows.append(filled_row)

    if len(new_rows) == 0:
        return df

    df_filled = pd.DataFrame(new_rows)
    df_result = pd.concat([df, df_filled], ignore_index=True)
    df_result = df_result.sort_values(["UserID", "unixtime"])
    df_result = df_result.reset_index(drop=True)
    return df_result
```

**Interpolácia časov:**

Medzikrokové záznamy nemajú skutočný čas. Predpokladáme **rovnomernú distribúciu** — každý medzikrok zaberá rovnako dlhý čas.

$$t_j = t_A + j \cdot \frac{t_B - t_A}{k + 1} \quad j = 1, 2, \ldots, k$$

kde:
- $t_A$ = unixtime aktuálneho záznamu (pred medzerou)
- $t_B$ = unixtime nasledujúceho záznamu (po medzere)
- $k$ = počet medzikrokov (dĺžka vrátenej BFS cesty)
- $j$ = poradie medzikroku (1 = prvý, $k$ = posledný)

**Numerický príklad:**

```
t_A = 1000,  t_B = 1060,  k = 2  (2 medzikroky)

time_step = (1060 - 1000) / (2 + 1) = 60 / 3 = 20 sekúnd

j=1: t_1 = 1000 + 1 × 20 = 1020   (1. medzikrok)
j=2: t_2 = 1000 + 2 × 20 = 1040   (2. medzikrok)

Výsledok:
  1000  URL_A        (pôvodný)
  1020  URL_mid_1    (FILLED)
  1040  URL_mid_2    (FILLED)
  1060  URL_B        (pôvodný)
```

**Prečo `DateTime = "FILLED"` a `Referrer = "FILLED"`?**  
Tieto polia sú textové a nemáme ich skutočnú hodnotu. Reťazec `"FILLED"` slúži ako **marker** — pri ďalšej analýze vieme okamžite identifikovať, ktoré záznamy boli dopĺňané a nie sú originálne z logu.

**Prečo `pd.concat([df, df_filled])` namiesto insertu?**  
DataFrame nie sú dynamické štruktúry — vkladanie riadkov doprostred je pomalé (musí sa preusporiadať pamäť). Efektívnejší je postup:
1. Zozbierať všetky nové riadky v Python liste `new_rows`
2. Raz vytvoriť `pd.DataFrame(new_rows)`
3. Spojiť `pd.concat([pôvodný, nové])`
4. Zoradiť podľa `UserID, unixtime` → správne poradie

---

## Celkový code flow

```
main()
    │
    ├─► pd.read_csv("wm2020projekt_sessions.csv")  →  df
    ├─► build_web_map(df)  →  web_map  {path: set(paths)}
    │
    ├─► run_subtask(df, "STT_MEAN", "...paths_sttmean.csv", web_map, max_depth=4)
    │   run_subtask(df, "STT_Q",    "...paths_sttq.csv",    web_map, max_depth=4)
    │   run_subtask(df, "RLength",  "...paths_rlength.csv", web_map, max_depth=6)
    │   run_subtask(df, "hRef",     "...paths_href.csv",    web_map, max_depth=4)
    │
    └─► run_subtask(df, session_col, out_file, web_map, max_depth):
            fill_missing_paths(df, session_col, web_map, max_depth)  →  df_result
            df_result.to_csv(out_file, index=False)


fill_missing_paths(df, session_col, web_map, max_depth):
    │
    ├─► for session_id in df[session_col].unique():
    │       session_df = záznamy daného sedenia (zoradené)
    │
    │       for j in range(len(session_df) - 1):
    │           start_url, end_url, curr_time, next_time
    │           bfs_find_path(web_map, start_url, end_url, max_depth)  →  path
    │
    │           if path: interpoluj časy, vytvor FILLED záznamy → new_rows
    │
    ├─► pd.DataFrame(new_rows)          →  df_filled
    ├─► pd.concat([df, df_filled])      →  df_result
    └─► sort_values(["UserID","unixtime"])  →  správne poradie
```

---

## Prehľad najdôležitejších funkcií

| Funkcia | Čo robí a prečo |
|---|---|
| `strip_domain(url)` | Normalizuje URL na samotný path; bez toho by sa absolútne a relatívne URL nezhodovali |
| `build_web_map(df)` | Buduje graf `{src: set(dst)}` z Referrer→URL párov; `set` eliminuje duplicity |
| `bfs_find_path(...)` | BFS garantuje najkratšiu cestu; `deque.popleft()` = O(1); `visited` zabraňuje cyklom |
| `deque.popleft()` | Odobranie z predu fronty v O(1) — kľúč pre efektívnosť BFS |
| `new_path[1:-1]` | Vráti len medzikroky, bez `start_url` a `end_url` (tie sú v originálnom logu) |
| `time_step = (next-curr)/(n+1)` | Lineárna interpolácia — rovnomerne rozloží čas medzi medzikrokmi |
| `pd.concat([df1, df2])` | Efektívne spojenie DataFrames; rýchlejšie ako iteratívne vkladanie riadkov |
| `sort_values(["UserID","unixtime"])` | Obnoví chronologické poradie po concat |

---

## Kľúčové otázky na obhajobu

**Prečo BFS a nie DFS (Depth-First Search)?**  
DFS (prehľadávanie do hĺbky) by mohol nájsť dlhú okľukovú cestu, kým by existovala kratšia priama cesta. BFS vždy nájde **najkratšiu cestu** (minimálny počet medzikrokov) — to je pre nás správne, keďže hľadáme realistickú navigačnú cestu, nie ľubovoľnú.

**Prečo nie je SLength zahrnutá vo výstupných súboroch?**  
Skript spracováva len STT\_MEAN, STT\_Q, RLength a hRef. SLength (fixných 600s) je najjednoduchšia metóda a slúži ako referenčný bod v Task 4; pre analýzu ciest sa spravidla nepovažuje za hlavnú metódu.

**Čo sa stane, ak BFS nenájde cestu?**  
`bfs_find_path()` vráti `None`. `fill_missing_paths()` ignoruje tento pár (`continue`) — do výstupu sa nevloží žiadny medzikrok. Pôvodné záznamy zostanú nezmenené.

**Prečo `visited` set? Čo by sa stalo bez neho?**  
Bez `visited` by BFS mohol v cyklickom grafe (napr. `/a` → `/b` → `/a` → `/b` → ...) behať donekonečna, pričom by hromadil čoraz dlhšie cesty. `visited` zaručuje, že každý uzol je navštívený **najviac raz** — BFS vždy skončí.

**Prečo `new_path = current_path + [neighbor]` a nie `current_path.append(neighbor)`?**  
`current_path.append(neighbor)` by modifikoval originálnu cestu v pamäti. Keďže jedna cesta v rade môže mať viacerých susedov, každý sused musí dostať **kópiu** cesty predĺženú o seba. `current_path + [neighbor]` vytvorí novú kópiu zoznamu. `append` by modifikoval cesty pre všetkých susedov súčasne.

**Aká je časová zložitosť BFS a čo znamenajú $V$ a $E$?**  
$O(V + E)$, kde $V$ = počet vrcholov (stránok v web mape), $E$ = počet hrán (odkazov). Každý vrchol je navštívený najviac raz (zaručuje `visited`). Každá hrana je spracovaná najviac raz. V praxi je BFS oveľa rýchlejší, pretože `max_depth` obmedzuje prehľadávanie dlho predtým, ako by sme navštívili celý graf.

**Čo je orientovaný graf a prečo je web mapa orientovaná?**  
V orientovanom grafe každá hrana má smer — hrana z $A$ do $B$ neznamená, že existuje hrana z $B$ do $A$. Web mapa je orientovaná: ak stránka `/katedra` odkazuje na `/katedra/matematika`, neznamená to, že `/katedra/matematika` odkazuje späť na `/katedra`. V kóde: `web_map["/katedra"].add("/katedra/matematika")` — jedna hrana, jeden smer.

**Prečo `set()` pre hodnoty web\_map a nie `list()`?**  
Jedna hrana (Referrer → URL) sa môže objaviť v logu tisíckrát. `list.append()` by každý výskyt uložil znova — web\_map by mala milióny duplicitných hrán a BFS by ich prechádzal všetky. `set.add()` automaticky ignoruje duplicity — každá hrana je uložená práve raz.

**Čo sa stane, ak `start_url == end_url`?**  
`bfs_find_path()` okamžite vráti prázdny zoznam `[]` (špeciálny prípad na začiatku funkcie). `fill_missing_paths()` skontroluje `if len(path) == 0: continue` — nevloží žiadne medzikroky. Toto je správne: ak URL záznamu je rovnaká ako nasledujúca URL, nie je čo dopĺňať.

**Prečo `int(t_k)` pri tvorbe doplneného záznamu?**  
Interpolovaný čas $t_k = t_A + j \cdot (t_B - t_A)/(k+1)$ je float (výsledok delenia). Stĺpec `unixtime` v celom DataFrame je `int64`. Keby sme uložili float, `pd.concat()` by zmiešal typy v stĺpci — niektoré hodnoty `int`, iné `float`. `int(t_k)` zabezpečí konzistentný typ.

**Čo obsahuje výsledný FILLED záznam v porovnaní s pôvodným?**

| Pole | Pôvodný záznam | FILLED záznam |
|---|---|---|
| `IP` | reálna IP | skopírovaná z curr\_row |
| `DateTime` | napr. `"12/Nov/2017:..."` | `"FILLED"` |
| `URL` | reálna URL | medzikrok z BFS |
| `Referrer` | reálny referrer | `"FILLED"` |
| `unixtime` | reálny timestamp | interpolovaný |
| `Length` | vypočítaná hodnota | `None` |
| `UserID` | reálne ID | skopírované z curr\_row |
| session stĺpec | reálne ID sedenia | skopírované (rovnaké sedenie) |

**Prečo `pd.concat()` + `sort_values()` namiesto priameho vkladania riadkov do DataFrame?**  
DataFrame je interné NumPy pole — vkladanie riadku doprostred vyžaduje realokáciu celej pamäte ($O(n)$ pre každý insert). Ak by sme vkladali tisíce medzikrokov jednotlivo, celková zložitosť by bola $O(n^2)$. `pd.concat()` spája celé DataFrames naraz — jedna alokácia, potom jedno zoradenie.

**Prečo sa doplnené záznamy označia ako `DateTime = "FILLED"` a nie sa tam vloží odhadnutý dátum?**  
Dátum by sa dal odvodiť z interpolovaného `unixtime`. Avšak `"FILLED"` marker je **explicitné označenie syntetických dát** — pri ďalšej analýze (napr. filtrovanie podľa dátumu, štatistiky len skutočných záznamov) vieme okamžite, ktoré záznamy sú pôvodné a ktoré boli dopočítané.

