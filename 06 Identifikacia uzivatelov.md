# Task 3 – Identifikácia používateľov (User Identification)

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Log po odstránení robotov obsahuje záznamy od ľudských návštevníkov, ale stále nevieme **kto je kto** — nemáme prihlasovacie mená, len IP adresy a User-Agent reťazce. Každý záznam tiež obsahuje čas iba ako textový reťazec (`"12/Nov/2017:06:27:01 +0100"`), s ktorým sa nedá matematicky počítať.

Skript rieši tri vzájomne závislé problémy:

1. **UNIXTIME** — Prevedie textový dátum na číslo (počet sekúnd od 1.1.1970 UTC). Bez číselného času by sme nemohli počítať rozdiely, zoraďovať záznamy ani identifikovať prestávky.
2. **UserID** — Priradí každej unikátnej kombinácii `IP + User-Agent` číselné ID. Toto je naša heuristika pre "jeden používateľ".
3. **Length** — Pre každý záznam vypočíta, koľko sekúnd strávil používateľ na danej stránke — odhadom cez čas do nasledujúceho kliknutia.

Výstup je vstupom pre Task 4 (identifikácia sedení), kde sa Length a UserID použijú intenzívne.

---

### Vstup a výstup

```
wm2020projekt_no_robots.csv
          │
          │  add_unixtime()   ← parsovanie DateTime → číslo sekúnd
          │  add_user_id()    ← IP + Agent → číselné UserID
          │  add_length()     ← čas do nasledujúceho kliknutia
          ▼
wm2020projekt_users.csv
  (pôvodné stĺpce + nové: unixtime, UserID, Length)
```

---

## Postup riešenia – krok za krokom

### Krok 1: UNIXTIME – konverzia dátumu na číslo

#### Čo je Unix timestamp (unixtime)?

Unix timestamp je **počet sekúnd, ktoré uplynuli od 1. januára 1970 00:00:00 UTC**. Je to celé číslo — napr. `1510465621`. Výhoda: s číslami sa dá jednoducho počítať. Rozdiel dvoch unixtimov je priamo počet sekúnd medzi udalosťami.

```
"12/Nov/2017:06:27:01 +0100"  →  1510464421
"12/Nov/2017:07:15:44 +0100"  →  1510467344

Rozdiel: 1510467344 - 1510464421 = 2923 sekúnd = ~48 minút
```

#### Parsovanie a konverzia

```python
DATETIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

datetime_parsed = pd.to_datetime(df["DateTime"], format=DATETIME_FORMAT)

epoch = pd.Timestamp("1970-01-01", tz="UTC")
df["unixtime"] = (datetime_parsed - epoch).dt.total_seconds().astype("int64")
```

**Formátové kódy `DATETIME_FORMAT`:**

| Kód | Popis | Príklad z logu |
|---|---|---|
| `%d` | Deň (2 číslice) | `12` |
| `%b` | Skratka mesiaca (3 znaky) | `Nov` |
| `%Y` | Rok (4 číslice) | `2017` |
| `%H:%M:%S` | Hodiny:minúty:sekundy | `06:27:01` |
| `%z` | Časová zóna | `+0100` (SEČ = UTC+1) |

**Prečo `dt.total_seconds()` a nie `.astype('int64') // 10**9`?**  
Toto je kritický detail. Pandas 2.0+ ukladá timezone-aware datetime interne v **mikrosekundách** (nie nanosekundách ako staršie verzie). Delenie `10**9` (ako pre nanosekundy) by dalo číslo 1000× väčšie ako správna hodnota — teda nezmyselný výsledok.

`(datetime - epoch).dt.total_seconds()` vráti vždy **sekundy** ako float, bez ohľadu na internú reprezentáciu pandasov. Následné `.astype("int64")` zaokrúhli na celé sekundy.

---

### Krok 2: UserID – identifikácia používateľov

#### Heuristika: IP + User-Agent = jeden používateľ

Nemáme cookies ani prihlasovacie mená. Najlepšia dostupná heuristika: každá **unikátna kombinácia IP adresy a User-Agent reťazca** pravdepodobne zodpovedá jednému zariadeniu (a teda jednému používateľovi).

**Prečo nestačí samotná IP adresa?**  
Celá kancelária, škola alebo bytový dom môžu zdieľať jednu verejnú IP adresu (NAT — Network Address Translation). Desiatky rôznych ľudí by mali rovnakú IP. User-Agent reťazec obsahuje informáciu o prehliadači a operačnom systéme — ľudia za rovnakou IP sa zvyčajne líšia aspoň verziou prehliadača alebo OS.

**Prečo nestačí samotný User-Agent?**  
Naopak, rovnaký User-Agent môže mať tisíce ľudí (napr. Firefox 117 na Windows 10 používajú milióny ľudí). Bez IP by sme ich všetkých považovali za jedného používateľa.

```python
df = df.sort_values(by=["IP", "Agent", "unixtime"])
df = df.reset_index(drop=True)

user_key = df["IP"] + "|" + df["Agent"]
user_ids, unique_keys = pd.factorize(user_key)
df["UserID"] = user_ids
```

**Ako funguje `pd.factorize()`?**  
Prechádza sériu hodnôt a každej unikátnej hodnote priradí celé číslo (0, 1, 2, ...):

```
user_key (vstup):               user_ids (výstup):
"192.168.1.1|Mozilla/5.0 Win"  →  0
"192.168.1.1|curl/7.64.1"      →  1
"10.0.0.5|Mozilla/5.0 Linux"   →  2
"192.168.1.1|Mozilla/5.0 Win"  →  0   (rovnaká kombinácia → rovnaké ID)
"10.0.0.5|Mozilla/5.0 Linux"   →  2
```

**Prečo separátor `"|"` medzi IP a Agent?**  
Ak by sme reťazce len zreťazili (bez oddeľovača), mohlo by dôjsť ku kolízii: IP `"192.168.1"` + Agent `"1|Mozilla"` by dala rovnaký kľúč ako IP `"192.168.1.1"` + Agent `"|Mozilla"`. Znak `|` sa v IP adresách ani User-Agent reťazcoch normálne nevyskytuje.

**Prečo zoradiť pred `factorize()`?**  
Zoradenie podľa `IP, Agent, unixtime` zabezpečí, že záznamy toho istého používateľa sú za sebou chronologicky. To je nevyhnutné pre správny výpočet `Length` v ďalšom kroku — `shift(-1)` musí posúvať v rámci záznamu toho istého používateľa, nie náhodne naprieč rôznymi.

---

### Krok 3: Length – čas strávený na stránke

#### Čo je Length a prečo sa nedá zmerať priamo?

`Length` = čas strávený na stránke v sekundách. Webový server zaznamená len **moment kliknutia** (požiadavok na novú stránku) — nemá informáciu, kedy používateľ klikol preč. Preto odhadujeme čas na stránke ako **rozdiel medzi aktuálnym a nasledujúcim požiadavkom toho istého používateľa**.

Príklad:
```
Používateľ ID=5:
  unixtime=1000  URL=/o-nas
  unixtime=1180  URL=/kontakt     → Length záznamu /o-nas = 1180 - 1000 = 180 sekúnd
  unixtime=1360  URL=/historia    → Length záznamu /kontakt = 1360 - 1180 = 180 sekúnd
  unixtime=5400  URL=/download    → rozdiel = 5400 - 1360 = 4040 s > 3600 s → Length = None
```

#### Implementácia pomocou `groupby` a `shift`

```python
df = df.sort_values(by=["UserID", "unixtime"])
df = df.reset_index(drop=True)

next_unixtime = df.groupby("UserID")["unixtime"].shift(-1)
next_userid   = df.groupby("UserID")["UserID"].shift(-1)

diff = next_unixtime - df["unixtime"]

condition = (next_userid == df["UserID"]) & (diff < MAX_SESSION_GAP)
df["Length"] = diff.where(condition, other=None)
```

**Ako funguje `groupby("UserID")["unixtime"].shift(-1)`?**  

`groupby("UserID")` rozdelí DataFrame na skupiny — každá skupina = záznamy jedného používateľa. `shift(-1)` v rámci každej skupiny posunie hodnoty o 1 riadok **nahor**, teda pre každý riadok dostaneme hodnotu **nasledujúceho** záznamu **toho istého** používateľa. Posledný záznam používateľa dostane `NaN` (žiadny nasledujúci).

```
UserID:        5     5     5     5     7     7     7
unixtime:    100   180   360  1400   200   500   800

groupby(UserID).shift(-1) na unixtime:
                180   360  1400   NaN   500   800   NaN
                 ↑     ↑     ↑     ↑     ↑     ↑     ↑
             nasl.   nasl.  nasl. posl. nasl. nasl. posl.
              záz.   záz.   záz.  záz.  záz.  záz.  záz.
              usr5   usr5   usr5  usr5  usr7  usr7  usr7
```

**Prečo potrebujeme `next_userid`?**  
Keby sme použili iba `df["unixtime"].shift(-1)` (bez groupby), pandas by posunul hodnoty naprieč celým DataFrame — posledný záznam používateľa 5 by dostal prvý unixtime používateľa 7. To by bol nesprávny výsledok. `next_userid == df["UserID"]` overuje, že nasledujúci záznam skutočne patrí **tomu istému** používateľovi.

**Podmienka pre zapísanie Length:**

| Podmienka | Popis |
|---|---|
| `next_userid == df["UserID"]` | Nasledujúci záznam patrí tomu istému používateľovi |
| `diff < MAX_SESSION_GAP` | Rozdiel < 3600 sekúnd (60 minút) |

Obe podmienky musia platiť naraz (`&` = AND). Ak nie — zapíše sa `None`.

**Prečo hranica 3600 sekúnd (60 minút)?**  
Ak používateľ neklikol 60+ minút, pravdepodobne odišiel od počítača. Čas na stránke by bol nerealisticky dlhý — napr. 8 hodín cez noc. Takéto hodnoty by skreslili štatistiky v Task 4. Hodnota 60 minút je štandardná hranica v analýze webových logov (používa ju aj Google Analytics).

**Funkcia `where(condition, other=None)`:**  
Pre každý riadok: ak `condition` je `True`, zachová pôvodnú hodnotu (`diff`). Ak `False`, zapíše `None`. Ekvivalent ternárneho operátora v C: `condition ? diff : NULL`.

---

## Celkový code flow

```
main()
    │
    ├─► pd.read_csv("wm2020projekt_no_robots.csv")  →  df
    │
    ├─► add_unixtime(df)
    │       pd.to_datetime(df["DateTime"], format="%d/%b/%Y:%H:%M:%S %z")
    │                              →  datetime_parsed  (timezone-aware)
    │       epoch = pd.Timestamp("1970-01-01", tz="UTC")
    │       (datetime_parsed - epoch).dt.total_seconds().astype("int64")
    │                              →  df["unixtime"]  (celé číslo sekúnd)
    │
    ├─► add_user_id(df)
    │       sort_values(["IP", "Agent", "unixtime"])
    │       user_key = df["IP"] + "|" + df["Agent"]
    │       pd.factorize(user_key)  →  user_ids (pole čísel), unique_keys
    │       df["UserID"] = user_ids
    │
    ├─► add_length(df)
    │       sort_values(["UserID", "unixtime"])
    │       groupby("UserID")["unixtime"].shift(-1)  →  next_unixtime
    │       groupby("UserID")["UserID"].shift(-1)    →  next_userid
    │       diff = next_unixtime - df["unixtime"]
    │       condition = (next_userid == df["UserID"]) & (diff < 3600)
    │       df["Length"] = diff.where(condition, other=None)
    │
    └─► df.to_csv("wm2020projekt_users.csv", index=False, encoding="utf-8")
```

---

## Prehľad najdôležitejších funkcií

| Funkcia | Čo robí a prečo |
|---|---|
| `pd.to_datetime(col, format=...)` | Parsuje reťazec na datetime objekt; explicitný formát je rýchlejší ako automatické hádanie |
| `pd.Timestamp("1970-01-01", tz="UTC")` | Bod Unix epochy — 0 sekúnd |
| `(datetime - epoch).dt.total_seconds()` | Časový rozdiel prevedie na float sekúnd — správne pre všetky verzie pandas |
| `.astype("int64")` | Zaokrúhli float sekúnd na celé číslo |
| `df.sort_values(by=[...])` | Zoradí DataFrame podľa viacerých stĺpcov; poradie stĺpcov v zozname = priorita zoradenia |
| `pd.factorize(series)` | Každej unikátnej hodnote priradí celé číslo; vracia `(pole_čísel, pole_unikátnych_hodnôt)` |
| `groupby("col")["col2"].shift(-1)` | Posunie hodnoty o 1 nahor **v rámci každej skupiny** — nepreskočí hranice skupiny |
| `groupby("col")["col2"].shift(1)` | Posunie o 1 nadol — pre každý riadok dostaneme hodnotu **predchádzajúceho** záznamu tej skupiny |
| `series.where(condition, other=None)` | Kde podmienka `True` → zachová hodnotu; kde `False` → zapíše `None` |
| `series.notna().sum()` | Spočíta riadky kde hodnota nie je `NaN` — na kontrolu počtu platných Length hodnôt |

---

## Kľúčové otázky na obhajobu

**Prečo Length reprezentuje čas na stránke a nie čas od stránky?**  
Length záznamu `/o-nas` = čas od kliknutia na `/o-nas` po kliknutie na ďalšiu stránku. Teda koľko sekúnd používateľ strávil na `/o-nas`, kým klikol preč. Je to najlepší dostupný odhad — webový server nemá iný spôsob zistenia, kedy používateľ opustil stránku.

**Prečo posledný záznam každého používateľa dostane `Length = None`?**  
Pre posledný záznam neexistuje nasledujúci požiadavok od toho istého používateľa — nevieme, kedy odišiel. `None` (NaN) signalizuje neznámu hodnotu. V Task 4 sa `None` Length interpretuje ako signál pre začiatok nového sedenia.

**Čo znamená `int64` a prečo to nestačí `int`?**  
Python `int` má neobmedzený rozsah, pandas interný typ `int64` je 64-bitové celé číslo. Unix timestamp pre rok 2017 je ~1 510 000 000 — to sa bez problémov zmestí do `int64` (max ~9.2 × 10¹⁸). Pandas používa `int64` pre číselné stĺpce štandardne.

**Čo ak dvaja ľudia zdieľajú rovnaký User-Agent za rovnakou IP?**  
Dostanú rovnaké UserID — to je nevyhnutná obmedzenie heuristiky. Bez cookies alebo prihlásenia nie je možná dokonalá identifikácia. V praxi sa táto situácia vyskytuje zriedkavo pre deskstopové zariadenia, keďže User-Agent obsahuje aj verziu prehliadača.

**Čo je UTC a prečo prevádzame na UTC epoch a nie lokálny čas?**  
UTC (Coordinated Universal Time) je svetový štandard času bez letného/zimného posunu. Záznamy v logu majú časovú zónu `+0100` (stredoeurópsky čas = UTC+1 zimný). Epoch = 1.1.1970 00:00:00 **UTC**. Prevádzame do UTC aby všetky záznamy mali jednotný základ — inak by záznamy pred/po zmene letného času mali "skok" o hodinu.

**Manuálny výpočet: koľko sekúnd je `"12/Nov/2017:06:27:01 +0100"`?**  
12. November 2017, 06:27:01, časová zóna UTC+1. V UTC = 05:27:01. Od 1.1.1970 00:00:00 UTC do 12.11.2017 00:00:00 UTC je 17 482 dní. 17 482 × 86 400 s/deň = 1 510 444 800 s. Prirátame 05×3600 + 27×60 + 01 = 18 000 + 1 620 + 1 = 19 621 s. Výsledok: 1 510 444 800 + 19 621 = **1 510 464 421** s.

**Čo je NAT (Network Address Translation) a prečo komplikuje identifikáciu používateľov?**  
NAT je technika, pri ktorej router prekladá interné IP adresy (napr. `192.168.x.x`) na jednu verejnú IP adresu. Celá kancelária, škola alebo bytový dom vystupujú navonok pod jednou IP. Webový server vidí len verejnú IP — nemôže rozlíšiť, ktoré zariadenie za tou IP poslalo požiadavok. Preto kombinujeme IP + User-Agent.

**Čo by sa stalo, keby sme nezoradili DataFrame pred `shift(-1)` pri výpočte Length?**  
Záznamy by neboli v chronologickom poradí pre každého používateľa. `shift(-1)` by posunul hodnoty v náhodnom poradí — napr. záznam z rána by dostal `next_unixtime` zo záznamu z iného dňa. Vypočítané `Length` hodnoty by boli úplne nezmyselné — záporné, alebo extrémne veľké.

**Môže byť `Length` záporná?**  
Teoreticky nie — záznamy sú zoradené podľa `unixtime` (rastúco), takže `next_unixtime >= current_unixtime`, teda `diff >= 0`. V praxi, ak má log nekonzistentné časy (napr. hodinový posun pri zmene letného času), `diff` by mohlo byť záporné. Skript to explicitne nešetrí — predpokladá konzistentné vstupy.

**Čo vracia `pd.factorize()` ako druhú hodnotu a na čo sa dá použiť?**  
`pd.factorize(series)` vracia dvojicu `(codes, uniques)`. `codes` = pole celých čísel (UserID pre každý riadok). `uniques` = pole unikátnych hodnôt kľúčov v poradí prvého výskytu. Napr. `uniques[0]` = IP+Agent kombinácia používateľa s `UserID=0`. Dá sa použiť na spätnú konverziu: `uniques[user_id]` vráti pôvodný kľúč.

**Prečo `drop=True` pri `reset_index(drop=True)`?**  
`reset_index()` štandardne presunie starý index do nového stĺpca (zachová ho). `drop=True` zahodí starý index namiesto jeho uloženia — nepotrebujeme ho a nechceme extra stĺpec s pôvodnými číslami riadkov v DataFrame.

**Aký je rozdiel medzi `NaN` a `None` v pandas?**  
`None` je Python objekt (null referencia). `NaN` (Not a Number) je špeciálna float hodnota podľa IEEE 754. Pandas pri ukladaní `None` do číselného stĺpca automaticky konvertuje na `NaN`. Pre textové (object) stĺpce môže zostať `None`. Funkcie ako `.isnull()`, `.isna()` zachytia obe — v pandas sa správajú ekvivalentne.

