# Task 2 – Identifikácia robotov (Robot Detection)

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

Aj po čistení v Task 1 (vymazanie statických súborov, neplatných stavových kódov a metód) log stále obsahuje záznamy od **automatizovaných agentov** — robotov vyhľadávacích služieb (Googlebot, Bingbot), webových crawlerov, monitorovacích skriptov a pravidelne spúšťaných cron úloh. Tieto záznamy nie sú kliknutiami ľudí a výrazne by skreslili analýzu správania.

Skript identifikuje robotov **dvoma nezávislými metódami**:

1. **Prístup k `robots.txt`** — každý legitímny vyhľadávač si pri indexovaní webu *vždy* najskôr prečíta tento súbor. IP adresa, ktorá pristúpila k `robots.txt`, je s vysokou pravdepodobnosťou robot.
2. **Kľúčové slová v User-Agent** — roboti sa väčšinou identifikujú vo svojom `Agent` reťazci slovami ako `bot`, `crawl`, `spider`.

Kombinácia oboch metód zachytí roboty, ktoré preskočia `robots.txt` (porušovatelia), ale identifikujú sa cez User-Agent, aj tých, čo majú generický User-Agent, ale pristúpili k `robots.txt`.

---

### Vstup a výstup

```
wm2020projekt_cleaned.csv
          │
          │  remove_cron_jobs()       ← acymailing cron úlohy
          │  find_robot_ips()         ← robots.txt prístupy
          │  save_robot_ips()         ← uloženie IP zoznamu
          │  remove_robot_ips()       ← vymazanie všetkej aktivity robotov
          │  remove_bot_agents()      ← User-Agent kľúčové slová
          ▼
wm2020projekt_robots.csv      (zoznam IP adries robotov – použijeme ešte)
wm2020projekt_no_robots.csv   (log zbavený všetkých robotov)
```

| Súbor | Popis |
|---|---|
| `wm2020projekt_cleaned.csv` | Vstup z Task 1 |
| `wm2020projekt_robots.csv` | Unikátne IP adresy robotov — uložíme pre prípadné neskoršie použitie |
| `wm2020projekt_no_robots.csv` | Výstup: log len s reálnymi ľudskými návštevníkmi |

---

## Postup riešenia – krok za krokom

### Krok 1: Vymazanie cron úloh acymailing

Joomla s pluginom acymailing (newsletter systém) spúšťa pravidelné automatické HTTP požiadavky — **cron úlohy**. Tieto požiadavky prichádzajú z interného systému a nie sú kliknutiami žiadneho návštevníka.

```python
CRON_URL_PREFIX = "/index.php?option=com_acymailing"

mask_cron = df["URL"].str.startswith(CRON_URL_PREFIX, na=False)
df = df[~mask_cron]
df = df.reset_index(drop=True)
```

**Prečo `str.startswith()` a nie `str.contains()`?**  
`startswith()` overuje len **začiatok** reťazca — je rýchlejší ako regex a jasnejšie vyjadruje zámer (URL musí začínať touto predponou). `str.contains()` by hľadal výskyt kdekoľvek v reťazci.

**Prečo `na=False`?**  
Ak je v stĺpci URL hodnota `NaN`, `startswith()` by vrátil `NaN`. Argument `na=False` zabezpečí, že chýbajúce URL sa považujú za `False` (nie cron úloha).

---

### Krok 2: Identifikácia robotov cez prístup k robots.txt

Súbor `robots.txt` je štandardný protokol pre robotov — vyhľadávače a crawlery si ho **vždy prečítajú ako prvé** pri indexovaní webu. Toto je spoľahlivý signál automatizovaného prístupu.

```python
ROBOTS_TXT_KEYWORD = "robots.txt"

mask_robots = df["URL"].str.contains(ROBOTS_TXT_KEYWORD, regex=False, na=False)
robot_ips   = df[mask_robots]["IP"].unique()
```

Postup po krokoch:

```
df["URL"].str.contains("robots.txt", regex=False)
     │
     ▼  → bool stĺpec, napr.:
     │     False, False, True, False, True, False, ...
     │
     ▼  df[mask_robots]["IP"]
     │     → stĺpec IP len riadkov kde URL obsahuje "robots.txt"
     │       napr.: ["66.249.66.1", "66.249.66.1", "157.55.39.18", ...]
     │
     ▼  .unique()
          → pole unikátnych IP adries:
            ["66.249.66.1", "157.55.39.18", ...]
```

**Prečo `regex=False`?**  
Pre pevný reťazec `"robots.txt"` je textové porovnanie rýchlejšie ako regex matching. `regex=False` hovorí pandasom: "použi priame vyhľadávanie podreťazca, nie regex engine."

**Prečo `.unique()`?**  
Jeden robot mohol pristúpiť k `robots.txt` viackrát (napr. pri každom novom prehľadaní webu). `.unique()` vráti každú IP adresu len raz — chceme zoznam robotov, nie zoznam udalostí.

---

### Krok 3: Uloženie IP adries robotov

```python
df_robots = pd.DataFrame(robot_ips, columns=["IP"])
df_robots.to_csv(ROBOTS_FILE, index=False, encoding="utf-8")
```

Zoznam robotických IP adries sa ukladá do `wm2020projekt_robots.csv`. Hoci v tomto skripte ho hneď použijeme, uloženie ako samostatný súbor zaručuje **reprodukovateľnosť** — ak by sme analýzu opakovali alebo rozšírili, vieme presne, ktoré IP boli identifikované ako roboty.

---

### Krok 4: Vymazanie VŠETKÝCH záznamov robotických IP adries

```python
mask_robot_ip = df["IP"].isin(robot_ips)
df = df[~mask_robot_ip]
df = df.reset_index(drop=True)
```

**Prečo vymažeme VŠETKU aktivitu robotickej IP, nielen prístup k robots.txt?**  
Robot, ktorý si prečítal `robots.txt`, pokračoval v prehľadávaní celého webu. V logu zanechal tisícky ďalších záznamov — načítal `/`, `/o-nas`, `/kontakt`, ... Keby sme vymazali len záznam s `robots.txt`, zvyšok jeho aktivity by zostal v dátach a skreslil by analýzu.

**Ako funguje `isin()`?**  
Pre každý riadok DataFrame skontroluje, či je hodnota stĺpca `IP` obsiahnutá v poli `robot_ips`. Interne používa hashovanie — výsledok je `True`/`False` pre každý riadok.

```
robot_ips = ["66.249.66.1", "157.55.39.18"]

df["IP"]:        "192.168.1.1"  "66.249.66.1"  "10.0.0.5"  "66.249.66.1"
isin(robot_ips):     False           True          False         True
~mask:               True            False         True          False
                      ↑ zachová        ↑ vymaže      ↑ zachová     ↑ vymaže
```

---

### Krok 5: Vymazanie robotov podľa User-Agent

Nie všetci roboti pristupujú k `robots.txt`. Druhá metóda identifikuje robotov podľa ich `Agent` (User-Agent) reťazca, kde sa roboti väčšinou prezradí kľúčovými slovami.

```python
BOT_KEYWORDS = [
    "bot",              # Googlebot, Bingbot, YandexBot, ...
    "crawl",            # webcrawler, ...
    "spider",           # typické pre vyhľadávače
    "wget",             # command-line HTTP klient, cron skripty
    "libwww-perl",      # Perl HTTP knižnica – automatizácia
    "python",           # Python requests, urllib, ...
    "java/",            # Java HttpClient (Apache HttpComponents, ...)
    "facebookexternalhit",  # Facebook link preview bot
]

bot_pattern = "|".join(BOT_KEYWORDS)
# Výsledok: "bot|crawl|spider|wget|libwww-perl|python|java/|facebookexternalhit"

mask_bot_agent = df["Agent"].str.contains(bot_pattern, case=False, regex=True, na=False)
df = df[~mask_bot_agent]
```

**Prečo `"|".join(BOT_KEYWORDS)`?**  
`|` v regexe znamená OR — vzor `"bot|crawl|spider"` sa zhoduje ak reťazec obsahuje `bot` **alebo** `crawl` **alebo** `spider`. `join()` automaticky zostaví tento vzor zo zoznamu, bez nutnosti písať ho ručne.

**Prečo `case=False`?**  
User-Agent reťazce nie sú štandardizované — robot sa môže identifikovať ako `Googlebot`, `googlebot` alebo `GOOGLEBOT`. `case=False` zachytí všetky varianty.

**Prečo `na=False`?**  
Niektoré záznamy môžu mať prázdny Agent (`-` alebo skutočné `NaN`). `na=False` zabezpečí, že tieto riadky sa nepovažujú za robotov.

---

## Celkový code flow

```
main()
    │
    ├─► pd.read_csv("wm2020projekt_cleaned.csv")  →  df
    │
    ├─► remove_cron_jobs(df)
    │       str.startswith("/index.php?option=com_acymailing")  →  mask_cron
    │       df = df[~mask_cron]
    │       vracia: df bez cron záznamov
    │
    ├─► find_robot_ips(df)
    │       str.contains("robots.txt", regex=False)  →  mask_robots
    │       df[mask_robots]["IP"].unique()  →  robot_ips  (pole IP adries)
    │       vracia: robot_ips
    │
    ├─► save_robot_ips(robot_ips, "wm2020projekt_robots.csv")
    │       pd.DataFrame(robot_ips, columns=["IP"])  →  df_robots
    │       df_robots.to_csv(...)
    │
    ├─► remove_robot_ips(df, robot_ips)
    │       df["IP"].isin(robot_ips)  →  mask_robot_ip
    │       df = df[~mask_robot_ip]
    │       vracia: df bez VŠETKEJ aktivity robotov
    │
    ├─► remove_bot_agents(df)
    │       "|".join(BOT_KEYWORDS)  →  bot_pattern
    │       str.contains(bot_pattern, case=False, regex=True)  →  mask_bot
    │       df = df[~mask_bot]
    │       vracia: df bez User-Agent robotov
    │
    └─► df.to_csv("wm2020projekt_no_robots.csv", index=False)
        df_robots.to_csv("wm2020projekt_robots.csv", index=False)
```

---

## Prehľad najdôležitejších funkcií

| Funkcia | Čo robí a prečo |
|---|---|
| `str.startswith(prefix, na=False)` | `True` kde reťazec začína predponou; rýchlejší ako regex pre pevné predpony |
| `str.contains(text, regex=False, na=False)` | `True` kde reťazec obsahuje text; `regex=False` = priame porovnanie, rýchlejšie |
| `str.contains(pattern, case=False, regex=True, na=False)` | `True` kde reťazec zodpovedá regex vzoru; `case=False` = veľké/malé písmená |
| `df["col"].unique()` | Pole unikátnych hodnôt stĺpca — každá hodnota len raz |
| `df["col"].isin(array)` | `True` kde hodnota je v danom poli — efektívne (hashing) |
| `"|".join(list)` | Spojí zoznam reťazcov do regex OR vzoru: `"a|b|c"` |
| `~mask` | Negácia bool stĺpca — zachová riadky kde mask = `False` |
| `pd.DataFrame(array, columns=["IP"])` | Vytvorí DataFrame s jedným stĺpcom z poľa hodnôt |

---

## Kľúčové otázky na obhajobu

**Prečo dve metódy identifikácie (robots.txt + User-Agent)?**  
Niektorí roboti **porušujú protokol** a nečítajú `robots.txt`, ale identifikujú sa v User-Agent (zachytí ich Krok 5). Iní roboti môžu mať User-Agent napodobňujúci bežný prehliadač ("spoofing"), ale prezradí ich prístup k `robots.txt` (zachytí ich Krok 2–4). Kombinácia oboch metód maximalizuje pokrytie.

**Prečo ukladáme robotické IP adresy do samostatného súboru?**  
`wm2020projekt_robots.csv` zachováva identifikovaných robotov pre prípadné ďalšie použitie — napr. porovnanie aktivity robotov vs. ľudí, alebo ak by sme chceli zopakovať analýzu s iným filtrom. Je to dobrá prax — transformácie dát by mali byť **reprodukovateľné** a transparentné.

**Čo je `robots.txt` protokol?**  
Štandard RFC 9309 (pôvodne neformálny štandard z roku 1994). Súbor na URL `/robots.txt` obsahuje pravidlá pre robotov — ktoré URL smú/nesmú indexovať. Každý seriózny vyhľadávač ho rešpektuje a číta ako prvé. Preto jeho prítomnosť v logu spoľahlivo identifikuje automatizovaný prístup.

**Prečo `cron` úlohy acymailing nie sú identifikované cez User-Agent?**  
Cron úlohy Joomla/acymailing sú spúšťané priamo serverom (localhost alebo interná sieť) — ich User-Agent môže byť bežný curl alebo PHP, čo by mohlo nesprávne zasiahnuť aj legitímne požiadavky. Bezpečnejšia identifikácia je cez špecifickú URL predponu `/index.php?option=com_acymailing`, ktorá jednoznačne identifikuje tieto požiadavky.

**Čo je User-Agent spoofing a prečo je problém?**  
Niektorí roboti nastavujú User-Agent na reťazec bežného prehliadača (napr. `Mozilla/5.0 (Windows NT 10.0)`) aby neboli zablokovaní. Takéhoto robota `str.contains("bot|crawl|spider")` nezachytí — neidentifikuje sa. Preto kombinujeme User-Agent filter s detekciou prístupu k `robots.txt`.

**Ako funguje `"|".join(list)` pri tvorbe regex vzoru?**  
`"|".join(["bot", "crawl", "spider"])` vráti reťazec `"bot|crawl|spider"`. Znak `|` v regexe znamená OR — vzor zodpovedá reťazcu, ktorý obsahuje `bot` **alebo** `crawl` **alebo** `spider`. Výsledok je rovnaký ako keby sme písali vzor ručne, ale kód je udržiavateľnejší — na pridanie nového kľúčového slova stačí rozšíriť zoznam `BOT_KEYWORDS`.

**Prečo `isin()` namiesto cyklu `for`?**  
Cyklus `for ip in robot_ips: if df["IP"] == ip: ...` by prechádzal každú IP zvlášť a bol $O(n \cdot k)$ kde $n$ = riadky DataFrame, $k$ = počet robotických IP. Pandas `isin()` interne používa **hashovaciu tabuľku** (množinu) — každý riadok sa skontroluje v $O(1)$, celá operácia je $O(n)$.

**Čo vracia `df["IP"].unique()`? Aký je typ výsledku?**  
Vracia **numpy pole** (`numpy.ndarray`) obsahujúce každú unikátnu hodnotu stĺpca `IP` práve raz. Poradie zodpovedá prvému výskytu v DataFrame. Pre `isin()` je jedno, či je vstup pole, zoznam alebo množina — všetky fungujú rovnako.

**Čo by sa stalo, keby sme vymazali len záznamy s `robots.txt` a nie celú aktivitu robotickej IP?**  
Robot, ktorý navštívil `robots.txt`, pokračoval v prehľadávaní webu — zanechal v logu tisícky záznamov pre `/`, `/o-nas`, `/kontakt`, ... Keby sme vymazali len jeden riadok s `robots.txt`, zvyšok jeho aktivity by zostal v dátach. Výsledok: robot by sa javil ako "intenzívny ľudský používateľ" a skreslil by štatistiky sedení a navigačných vzorov.

**Môže jeden ľudský používateľ mať rovnakú IP adresu ako detekovaný robot?**  
Áno — ak robot pôsobil z firemnej siete za NATom, jeho verejná IP zdieľa všetkých zamestnancov. Ak takáto IP bola identifikovaná ako robotická, vymažeme celú jej aktivitu vrátane legitímnych ľudských záznamov. Toto je nevyhnutné obmedzenie metódy — bez cookies alebo prihlasovacích mien nemôžeme rozlíšiť robota od človeka za rovnakou IP.

