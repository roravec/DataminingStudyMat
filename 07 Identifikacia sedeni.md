# Task 4 – Identifikácia sedení (Session Identification)

---

## Čo skript robí (podrobne)

### Základný problém, ktorý skript rieši

**Sedenie (session)** je súvislá séria navigačných požiadavkov jedného používateľa bez dlhej prestávky. Jeden používateľ môže navštíviť web ráno (1. sedenie), popoludní (2. sedenie) a večer (3. sedenie). Medzi sedeniami si oddýchol — to je kľúčový signál pre rozdelenie.

Webový log neobsahuje explicitnú informáciu "tu začína sedenie, tu končí". Musíme to odvodiť zo vzoru časov v záznome — konkrétne z hodnôt `Length` vypočítaných v Task 3.

Skript implementuje **5 rôznych metód** identifikácie sedení. Každá metóda sa líši spôsobom výpočtu **prahovej hodnoty** (threshold) — hranice, po prekročení ktorej sa prestávka považuje za koniec sedenia. Každá metóda pridá do DataFrame **vlastný stĺpec** s číselným ID sedenia.

---

### Vstup a výstup

```
wm2020projekt_users.csv
          │
          │  add_stt_mean()   ← prah = priemer Length
          │  add_stt_q()      ← prah = Q3 + 1.5 × IQR
          │  add_slength()    ← prah = fixných 600 sekúnd
          │  add_rlength()    ← prah = odvod. z exponenciálneho rozdelenia
          │  add_href()       ← čas + zhoda referrer s predošlou URL
          ▼
wm2020projekt_sessions.csv
  (pôvodné stĺpce + nové: STT_MEAN, STT_Q, SLength, RLength, hRef)
```

---

## Spoločná logika – `compute_new_session_flags()`

Metódy STT MEAN, STT Q, SLength a RLength zdieľajú rovnakú logiku — líšia sa **len prahovú hodnotou**. Nový záznam je začiatkom nového sedenia, ak predchádzajúci záznam spĺňa aspoň jednu z troch podmienok:

```python
def compute_new_session_flags(df, threshold):
    prev_userid = df["UserID"].shift(1)    # UserID predošlého riadku
    prev_length = df["Length"].shift(1)    # Length predošlého riadku

    cond_new_user       = (prev_userid != df["UserID"])   # (A) zmena používateľa
    cond_length_none    = prev_length.isnull()             # (B) Length je None/NaN
    cond_over_threshold = (prev_length >= threshold)       # (C) prestávka > prah

    is_new_session = cond_new_user | cond_length_none | cond_over_threshold
    is_new_session.iloc[0] = True    # prvý riadok celého DataFrame = vždy nové sedenie
    return is_new_session
```

**Tri podmienky — prečo každá:**

| Podmienka | Kód | Prečo je nutná |
|---|---|---|
| (A) Zmena používateľa | `prev_userid != df["UserID"]` | Keď sa zmení UserID, začína záznamy iný človek — nové sedenie triviálne |
| (B) Length = None | `prev_length.isnull()` | `None` bola nastavená v Task 3 ak bola prestávka > 60 min — to je jednoznačný koniec sedenia |
| (C) Length >= prah | `prev_length >= threshold` | Prestávka síce < 60 min, ale dlhšia ako prahová hodnota metódy |

**`shift(1)` — prečo predošlý riadok?**  
Pre každý riadok musíme vedieť, ako dlho trvala prestávka **pred** ním. `shift(1)` posunie stĺpec o 1 nadol — teda riadok `i` dostane hodnotu pôvodného riadku `i-1`. Prvý riadok dostane `NaN` (žiadny predošlý).

```
UserID:      5     5     5     5     7
Length:    180   None   240   120   300
           ↓  shift(1) ↓
prev_Length: NaN    180   None   240   120
              ↑       ↑     ↑      ↑    ↑
             (A)    (C?)   (B)   (C?)  (A) → podmienky pre každý riadok
```

**`cumsum()` — ako generuje ID sedení:**  
`is_new_session` je bool stĺpec (`True`/`False`). `cumsum()` počíta kumulatívny súčet: `False`=0 nemení súčet, `True`=1 ho zvýši o 1. Každý `True` teda "spustí" nové ID.

```
is_new_session:  True  False  False  True  False  True  False
cumsum():           1      1      1     2      2     3      3
                 ↑ sedenie 1 ↑       ↑ sedenie 2 ↑  ↑ sedenie 3 ↑
```

---

## Metóda 1: STT MEAN (Session Time Threshold – priemer)

**STT** = Session Time Threshold = prahová hodnota časového okna sedenia.

```python
def add_stt_mean(df):
    threshold = df["Length"].mean()   # .mean() ignoruje NaN automaticky
    is_new_session = compute_new_session_flags(df, threshold)
    df["STT_MEAN"] = is_new_session.cumsum()
```

**Vzorec:**

$$\text{STT\_Mean} = \overline{Length} = \frac{\sum_{i : Length_i \neq NaN} Length_i}{n}$$

kde $n$ = počet záznamov s platnou (nie `NaN`) hodnotou `Length`.

**Interpretácia:** Ak prestávka medzi dvoma kliknutiami trvá dlhšie ako priemerný čas medzi kliknutiami, považujeme to za koniec sedenia.

**Nevýhoda — citlivosť na outliery:**  
Priemer je silne ovplyvnený extrémnymi hodnotami. Ak niekto nechal prehliadač otvorený cez noc (Length = 50 000 sekúnd), priemer sa výrazne posunie nahor a metóda bude identifikovať menej a dlhších sedení.

---

## Metóda 2: STT Q (Session Time Threshold – kvartilový odhad)

Robustnejšia alternatíva. Používa **Tukeyho metódu detekcie odľahlých hodnôt (outlierov)**.

```python
def add_stt_q(df):
    q1  = df["Length"].quantile(0.25)   # 25. percentil
    q3  = df["Length"].quantile(0.75)   # 75. percentil
    iqr = q3 - q1                        # interkvartilové rozpätie
    threshold = q3 + 1.5 * iqr
    is_new_session = compute_new_session_flags(df, threshold)
    df["STT_Q"] = is_new_session.cumsum()
```

**Vzorce:**

$$Q_1 = \text{25. percentil(Length)}$$

$$Q_3 = \text{75. percentil(Length)}$$

$$IQR = Q_3 - Q_1 \quad \text{(interkvartilové rozpätie)}$$

$$\text{STT\_Q} = Q_3 + 1.5 \times IQR$$

**Čo je percentil?**  
$Q_1 = $ 25. percentil znamená: 25 % hodnôt `Length` je menších alebo rovných $Q_1$, 75 % je väčších. $Q_3 = $ 75. percentil: 75 % hodnôt je menších alebo rovných $Q_3$.

**Prečo $Q_3 + 1.5 \times IQR$?**  
Toto je Tukeyho pravidlo z roku 1977. Hodnoty nad touto hranicou sa považujú za **štatisticky neobvyklé** (outliery). Pre normálne rozdelenie zachytí táto hranica ~99,3 % dát — len extrémne dlhé prestávky sú nad ňou.

**Vizualizácia:**

```
|──────────────────────────────────────────────────────────────|
0     Q1         median         Q3          Q3 + 1.5*IQR
       ↑                         ↑                    ↑
    25% hodnôt              75% hodnôt           STT_Q prah
    pod Q1                  pod Q3
    ←── IQR (50% stredných hodnôt) ──►←── 1.5×IQR ──►
```

**Prečo je STT Q lepší ako STT Mean?**  
Kvartiely sa počítajú zo stredných 50 % dát — extrémne hodnoty (cez noc otvorený prehliadač) ich neovplyvnia. STT Q je **robustný estimátor** — poskytuje stabilnejšiu prahovú hodnotu aj pri zašumených dátach.

---

## Metóda 3: SLength (fixný prah 600 sekúnd)

Najjednoduchšia metóda — pevne stanovená hranica bez akéhokoľvek výpočtu z dát.

```python
SLENGTH_THRESHOLD = 600   # sekúnd = 10 minút

def add_slength(df):
    is_new_session = compute_new_session_flags(df, SLENGTH_THRESHOLD)
    df["SLength"] = is_new_session.cumsum()
```

**Prah:** 600 sekúnd = 10 minút. Toto je **odporúčaný štandard** webovej analytiky — používa ho Google Analytics, Adobe Analytics aj väčšina analytických nástrojov.

**Výhoda:** Jednoduchosť, zrozumiteľnosť, medzinárodná komparabilita.

**Nevýhoda:** Ignoruje skutočné správanie používateľov na konkrétnom webe. Na stránkach s dlhými článkami (napr. akademický web UKF) môže 10 minút byť príliš krátke okno.

---

## Metóda 4: RLength (odvodený z exponenciálneho rozdelenia)

Táto metóda je matematicky najkomplexnejšia. Predpokladá, že hodnoty `Length` majú **exponenciálne rozdelenie**, a odvodzuje prahovú hodnotu z parametrov tohto rozdelenia.

### Krok 4a: Test exponenciálneho rozdelenia

Pred výpočtom prahu overíme, či `Length` naozaj má exponenciálne rozdelenie. Ak nie, použijeme fallback (STT Q).

**Prečo exponenciálne rozdelenie?**  
Exponenciálne rozdelenie opisuje čas medzi nezávislými náhodne sa vyskytujúcimi udalosťami (Poissonov proces). Kliknutia na web sa modelujú ako takéto udalosti — každý používateľ kliká náhodne, nezávisle od predchádzajúcich kliknutí. Čas medzi kliknutiami by teda teoreticky mal mať exponenciálne rozdelenie.

**Šikmosť (skewness) ako orientačný ukazovateľ:**  
Pre exponenciálne rozdelenie je šikmosť vždy $= 2$. Vypočítaná šikmosť dát blízka 2 naznačuje exponenciálne rozdelenie (ale nie je to formálny dôkaz).

#### Test 1: Kolmogorov-Smirnov (KS) test

Porovnáva **empirickú CDF** (z dát) s **teoretickou CDF** exponenciálneho rozdelenia.

$$D_n = \sup_{x} |F_n(x) - F(x)|$$

kde $F_n(x)$ = empirická CDF (podiel dát $\leq x$), $F(x)$ = teoretická CDF exponenciálneho rozdelenia s odhadnutým $\lambda$.

```python
loc, scale = stats.expon.fit(valid_lengths, floc=0)
# scale = 1/lambda  (MLE odhad)
ks_stat, ks_p = stats.kstest(valid_lengths, "expon", args=(0, scale))
```

- **Nulová hypotéza $H_0$:** dáta pochádzajú z exponenciálneho rozdelenia
- Ak **p-hodnota $< 0.05$** → zamietame $H_0$ → dáta **nemajú** exponenciálne rozdelenie

#### Test 2: Chi-square test zhody (Goodness-of-Fit)

Rozdelíme dáta do $k = 20$ tried s **rovnakou teoretickou pravdepodobnosťou** ($1/k$ pre každú triedu) a porovnáme pozorované vs. očakávané početnosti.

$$\chi^2 = \sum_{i=1}^{k} \frac{(O_i - E_i)^2}{E_i}$$

kde $O_i$ = pozorovaná početnosť triedy $i$, $E_i$ = očakávaná početnosť triedy $i = n/k$.

**Stupne voľnosti:**

$$df = k - 1 - 1 = k - 2 = 18$$

(odčítavame 1 za odhad parametra $\lambda$)

**p-hodnota:**

$$p = 1 - F_{\chi^2}(\chi^2_{stat},\ df)$$

kde $F_{\chi^2}$ = CDF chi-square rozdelenia.

```python
N_BINS = 20
# Hranice tried = kvantiley teoretického exp. rozdelenia (rovnaká pravdepodobnosť)
quantile_points = np.linspace(0.0, 1.0, N_BINS + 1)
bin_edges = stats.expon.ppf(quantile_points[:-1], loc=0, scale=scale)
bin_edges = np.append(bin_edges, np.inf)

observed, _ = np.histogram(valid_lengths, bins=bin_edges)
expected    = np.full(N_BINS, n_total / N_BINS, dtype=float)

chi2_stat = sum((observed[i] - expected[i])**2 / expected[i] for i in range(N_BINS))
dof   = N_BINS - 2
chi2_p = 1.0 - stats.chi2.cdf(chi2_stat, dof)
```

**Prečo hranice tried sú kvantiley teoretického rozdelenia?**  
Pre rovnomerne pravdepodobné triedy ($E_i = n/k$ pre každú) je chi-square test najcitlivejší. Ak by sme použili rovnomerne rozložené hranice na číselnej osi, niektoré triedy by mali veľmi nízke $E_i$ → delenie malým číslom → nestabilný test.

**Prečo `stats.expon.ppf()` pre hranice?**  
`ppf` = Percent Point Function = inverzná CDF (kvantilová funkcia). `ppf(0.05)` pre exponenciálne rozdelenie vráti hodnotu, pod ktorou leží 5 % dát podľa teoretického modelu. Tým dostaneme hranice tried, kde každá trieda má rovnakú teoretickú pravdepodobnosť.

### Krok 4b: Výpočet prahu z exponenciálneho rozdelenia

**MLE odhad parametra $\lambda$:**

Pre exponenciálne rozdelenie platí $E[X] = 1/\lambda$, teda maximálna vierohodnosť (MLE) dáva:

$$\hat{\lambda} = \frac{1}{\overline{Length}}$$

(priemer ako odhad strednej hodnoty)

**Kvantilová funkcia exponenciálneho rozdelenia:**

CDF exponenciálneho rozdelenia: $F(x) = 1 - e^{-\lambda x}$

Inverzia: ak chceme nájsť $C$ také, že $F(C) = p$:

$$1 - e^{-\lambda C} = p$$
$$e^{-\lambda C} = 1 - p$$
$$-\lambda C = \ln(1 - p)$$
$$C = -\frac{\ln(1 - p)}{\lambda}$$

```python
p         = 0.40   # RLENGTH_NAV_PAGE_RATIO
threshold = -np.log(1.0 - p) / lam
```

**Interpretácia:** $p = 0.40$ = predpokladáme, že 40 % všetkých medzichodov sú **navigačné stránky** (krátke návštevy — používateľ rýchlo preskočil ďalej). $C$ je čas, pod ktorým leží 40 % medzichodov podľa modelu. Ak prestávka > $C$, pravdepodobnosť, že ide o normálne navigačné správanie, je < 60 % — teda predpokladáme koniec sedenia.

**Fallback:** Ak KS test zamietne exponenciálne rozdelenie (p < 0.05), použijeme STT Q ako záložnú prahovú hodnotu.

---

## Metóda 5: hRef (Hyperlink Reference)

Úplne odlišný prístup — berie do úvahy nielen čas, ale aj **navigačnú štruktúru** (referrer záznamu).

```python
def add_href(df):
    delta = df["Length"].mean()   # rovnaké ako STT_Mean

    df["Referrer_path"] = df["Referrer"].apply(strip_domain)
    prev_url      = df.groupby("UserID")["URL"].shift(1)
    prev_unixtime = df.groupby("UserID")["unixtime"].shift(1)

    cond_ref_match = (df["Referrer_path"] == prev_url)
    time_diff      = df["unixtime"] - prev_unixtime
    cond_time_ok   = (time_diff <= delta)

    same_session   = cond_ref_match | cond_time_ok
    is_new_session = ~same_session | prev_url.isnull()
    is_new_session.iloc[0] = True
    df["hRef"] = is_new_session.cumsum()
    df.drop(columns=["Referrer_path"], inplace=True)
```

**Dve podmienky pre patrienie do rovnakého sedenia (OR):**

| Podmienka | Kód | Popis |
|---|---|---|
| Referrer zhoda | `Referrer_path == prev_url` | Aktuálny referrer = predošlá URL → klikol na odkaz |
| Čas v okne | `time_diff <= delta` | Prestávka ≤ STT Mean |

Záznam je v **novom** sedení až keď **ani jedna** podmienka neplatí (de Morgan: `~(A|B) = ~A & ~B`).

**Funkcia `strip_domain(url)`:**

```python
def strip_domain(url):
    if "://" in url:
        start     = url.find("://") + 3
        slash_pos = url.find("/", start)
        return url[slash_pos:] if slash_pos != -1 else "/"
    return url
```

Referrer v logu môže byť absolútna URL (`https://www.ukf.sk/o-nas`) alebo len cesta (`/o-nas`). URL v stĺpci `URL` je vždy len cesta. Aby porovnanie fungovalo, obidva formáty prevedieme na samotný path:

```
"https://www.ukf.sk/o-nas"  →  "/o-nas"
"/o-nas"                    →  "/o-nas"
"-"                         →  "-"      (chýbajúci referrer, nezhoda)
```

**Prečo `groupby("UserID")` pri `shift(1)` v hRef?**  
Na rozdiel od `compute_new_session_flags()` kde používame globálny `shift(1)`, v hRef potrebujeme porovnávať referrer s URL predošlého záznamu **toho istého** používateľa. `groupby("UserID").shift(1)` zabezpečí, že prvý záznam každého používateľa dostane `NaN` (žiadna predošlá URL) — `prev_url.isnull()` ho označí ako nové sedenie.

---

## Celkový code flow

```
main()
    │
    ├─► pd.read_csv("wm2020projekt_users.csv")  →  df
    ├─► sort_values(["UserID", "unixtime"])
    │
    ├─► add_stt_mean(df)
    │       threshold = df["Length"].mean()
    │       compute_new_session_flags(df, threshold)  →  is_new
    │       df["STT_MEAN"] = is_new.cumsum()
    │
    ├─► add_stt_q(df)
    │       q1=quantile(0.25), q3=quantile(0.75), iqr=q3-q1
    │       threshold = q3 + 1.5*iqr
    │       df["STT_Q"] = is_new.cumsum()
    │
    ├─► add_slength(df)
    │       threshold = 600
    │       df["SLength"] = is_new.cumsum()
    │
    ├─► add_rlength(df)
    │       test_exponential(df):
    │           stats.expon.fit(valid_lengths, floc=0)  →  loc, scale
    │           stats.kstest(...)                        →  ks_p
    │           chi2 ručne cez np.histogram + stats.chi2.cdf  →  chi2_p
    │       if exponential: threshold = -ln(1-0.4) / lam
    │       else:           threshold = STT_Q  (fallback)
    │       df["RLength"] = is_new.cumsum()
    │
    ├─► add_href(df)
    │       delta = df["Length"].mean()
    │       strip_domain(Referrer) → Referrer_path
    │       groupby("UserID").shift(1) → prev_url, prev_unixtime
    │       cond_ref_match | cond_time_ok → same_session
    │       df["hRef"] = (~same_session | prev_url.isnull()).cumsum()
    │
    └─► df.to_csv("wm2020projekt_sessions.csv", index=False)
```

---

## Porovnanie všetkých 5 metód

| Metóda | Vzorec prahu | Typ | Výhoda | Nevýhoda |
|---|---|---|---|---|
| STT MEAN | $\overline{Length}$ | Štatistický | Jednoduchý | Citlivý na outliery |
| STT Q | $Q_3 + 1.5 \times IQR$ | Štatistický | Robustný, odolný outlierom | Zložitejší |
| SLength | $600\ s$ (fixný) | Heuristický | Najjednoduchší, štandardný | Ignoruje reálne dáta |
| RLength | $-\ln(1-0.4)/\hat{\lambda}$ | Modelový | Mat. odvodený z distribúcie | Predpokladá exp. rozdelenie |
| hRef | $\delta$ + referrer zhoda | Navigačný | Berie do úvahy štruktúru webu | Najzložitejší |

---

## Štatistické základy – hlbší pohľad (dôležité pre skúšku)

### Exponenciálne rozdelenie – úplný prehľad

**PDF (hustota pravdepodobnosti / Probability Density Function):**

$$f(x;\, \lambda) = \lambda\, e^{-\lambda x}, \quad x \geq 0,\quad \lambda > 0$$

**CDF (kumulatívna distribučná funkcia):**

$$F(x;\, \lambda) = 1 - e^{-\lambda x}, \quad x \geq 0$$

**Stredná hodnota a rozptyl:**

$$E[X] = \frac{1}{\lambda}, \qquad Var[X] = \frac{1}{\lambda^2}$$

**Šikmosť (skewness) — vždy rovnaká:**

$$\gamma_1 = 2 \quad \text{pre akékoľvek } \lambda$$

Šikmosť = 2 znamená silne pravostranné rozdelenie (long right tail). Väčšina hodnôt Length je malá (rýchle kliknutia), no občas sa vyskytujú veľmi veľké (dlhé prestávky). Práve to zodpovedá skutočnému správaniu návštevníkov webu.

**Vizualizácia PDF:**

```
f(x)
 │\
 │ \       λ = 0.01  →  pomalý pokles (dlhý priemer = 100s)
 │  \
 │   \─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
 │         λ = 0.1   →  strmý pokles (krátky priemer = 10s)
 └────────────────────────────────► x
 0                               ∞
```

---

### Vlastnosť "bez pamäte" (Memoryless Property)

Exponenciálne rozdelenie je **jediné spojité rozdelenie** s touto vlastnosťou:

$$P(X > t + s \mid X > t) = P(X > s) \quad \text{pre všetky } t, s \geq 0$$

**Dôkaz:**

$$P(X > t + s \mid X > t) = \frac{P(X > t + s)}{P(X > t)} = \frac{e^{-\lambda(t+s)}}{e^{-\lambda t}} = e^{-\lambda s} = P(X > s)$$

**Interpretácia pre web log:** Ak používateľ neklikol 5 minút, pravdepodobnosť, že klikne v nasledujúcej minúte, je **rovnaká** ako keby sme čakali od začiatku. Minulosť neovplyvňuje budúcnosť — každé kliknutie je nezávislé od predchádzajúcich. Táto vlastnosť ospravedlňuje použitie exponenciálneho modelu pre `Length`.

---

### Odvod MLE odhadu $\hat{\lambda}$

MLE (Maximum Likelihood Estimation) = hľadáme $\lambda$, ktoré **maximalizuje** pravdepodobnosť pozorovaných dát $x_1, x_2, \ldots, x_n$.

**Krok 1 — Likelihood funkcia** (súčin PDF pre každé pozorovanie):

$$L(\lambda) = \prod_{i=1}^{n} \lambda\, e^{-\lambda x_i} = \lambda^n \cdot e^{-\lambda \sum_{i=1}^{n} x_i}$$

**Krok 2 — Log-likelihood** (logaritmus zjednodušuje deriváciu, maximum sa nemení):

$$\ell(\lambda) = \ln L(\lambda) = n \ln\lambda - \lambda \sum_{i=1}^{n} x_i$$

**Krok 3 — Derivácia a položenie = 0** (podmienka extrému):

$$\frac{d\ell}{d\lambda} = \frac{n}{\lambda} - \sum_{i=1}^{n} x_i = 0$$

**Krok 4 — Vyriešenie:**

$$\frac{n}{\hat{\lambda}} = \sum_{i=1}^{n} x_i \implies \hat{\lambda} = \frac{n}{\sum_{i=1}^{n} x_i} = \frac{1}{\bar{x}}$$

**Výsledok:** $\hat{\lambda} = 1/\overline{Length}$ — MLE odhad je prevrátená hodnota priemeru. V kóde: `loc, scale = stats.expon.fit(data, floc=0)` → `scale = 1/lambda` → `lam = 1/scale`.

---

### Číselný príklad: výpočet prahu RLength

Nech $\overline{Length} = 250\,\text{s}$, pomer navigačných stránok $p = 0.40$.

**Krok 1 — MLE odhad:**
$$\hat{\lambda} = \frac{1}{250} = 0.004\ \text{s}^{-1}$$

**Krok 2 — Kvantilová funkcia:**
$$C = -\frac{\ln(1 - p)}{\hat{\lambda}} = -\frac{\ln(0.60)}{0.004} = -\frac{-0.5108}{0.004} = \frac{0.5108}{0.004} \approx 127.7\ \text{s}$$

**Krok 3 — Overenie** (kontrola že $F(C) = p$):
$$F(127.7) = 1 - e^{-0.004 \times 127.7} = 1 - e^{-0.5108} = 1 - 0.60 = 0.40\ ✓$$

Prah = ~128 sekúnd. Prestávka dlhšia ako 128 sekúnd = koniec sedenia.

---

### Číselný príklad: chi-square test goodness-of-fit

Nech $n = 1000$ hodnôt Length, $k = 20$ tried.

**Očakávaná početnosť každej triedy** (rovnomerne rozdelená pravdepodobnosť):
$$E_i = \frac{n}{k} = \frac{1000}{20} = 50 \quad \text{pre každú triedu}$$

**Výpočet štatistiky** (príklad pre 3 triedy):

| Trieda $i$ | $O_i$ | $E_i$ | $(O_i - E_i)^2$ | $(O_i - E_i)^2 / E_i$ |
|---|---|---|---|---|
| 1 | 48 | 50 | 4 | 0.08 |
| 2 | 57 | 50 | 49 | 0.98 |
| 3 | 44 | 50 | 36 | 0.72 |
| ... | ... | ... | ... | ... |
| Spolu | — | — | — | $\chi^2_{stat}$ |

**Stupne voľnosti:** $df = k - 2 = 20 - 2 = 18$

(Odčítame 2: 1 za celkový počet $n$ = fixovaný, 1 za odhadnutý parameter $\hat{\lambda}$.)

**p-hodnota:** $p = 1 - F_{\chi^2}(\chi^2_{stat},\ 18)$

Ak $p \geq 0.05$ → nezamietame $H_0$ → dáta **môžu** mať exponenciálne rozdelenie → použijeme RLength vzorec.

---

### Poissonov proces → exponenciálne rozdelenie (súvislosť)

```
Kliknutia na web = náhodné nezávislé udalosti v čase
          ↓
Modelujeme ako Poissonov proces s intenzitou λ [udalostí/sekundu]
          ↓
Čas MEDZI po sebe idúcimi udalosťami ~ Exponenciálne(λ)
          ↓
Length hodnoty by mali mať exponenciálne rozdelenie
          ↓
Overíme KS testom a chi-square testom
          ↓
Ak áno → odvodíme prah C = -ln(1-p)/λ
          ↓
Ak nie  → fallback na STT_Q (robustný kvantilový odhad)
```

---

### Porovnanie: outlier (Length = 50 000 s) vs STT Mean a STT Q

Predpokladajme 1000 záznamov, väčšina Length okolo 200 s, jeden outlier 50 000 s.

**STT Mean bez outlieru:** $\overline{Length} \approx 200$ s  
**STT Mean s outlierom:** $\overline{Length} \approx 200 + 50000/1000 = 250$ s → prah sa posunie o 25 %

**STT Q bez outlieru:** $Q_3 \approx 300$ s, $IQR \approx 200$ s → prah $\approx 600$ s  
**STT Q s outlierom:** $Q_3 \approx 300$ s, $IQR \approx 200$ s → prah $\approx 600$ s ← **nezmenilo sa**

Záver: STT Q je imúnny voči outlierom, STT Mean je citlivý.

---

## Kľúčové otázky na obhajobu

**Čo je IQR a prečo je robustný?**  
IQR (Interquartile Range) = $Q_3 - Q_1$ = rozpätie stredných 50 % dát. Extrémne hodnoty (outliery) neovplyvnia $Q_1$ ani $Q_3$, pretože kvartiely závisia len od poradového čísla hodnôt, nie od ich absolútnej veľkosti. Napríklad ak zmeníme najväčšiu hodnotu z 1000 na 1 000 000, IQR zostane rovnaký.

**Prečo `floc=0` pri `stats.expon.fit()`?**  
`floc=0` fixuje parameter posunutia (location) na nulu. Exponenciálne rozdelenie začína od nuly — nie má zmysel ho posúvať. Bez `floc=0` by `fit()` odhadoval aj posunutie, čo by skreslilo odhad $\lambda$.

**Čo je nulová hypotéza $H_0$ a čo znamená p-hodnota < 0.05?**  
$H_0$ = tvrdenie, ktoré testujeme (tu: "dáta pochádzajú z exponenciálneho rozdelenia"). p-hodnota = pravdepodobnosť, že by sme pozorovali také alebo ešte extrémnejšie dáta, keby $H_0$ bola pravda. p < 0.05 = táto pravdepodobnosť je tak malá, že $H_0$ s 95% istotou zamietame.

**Prečo KS test aj chi-square test? Nestačí jeden?**  
KS test je citlivý na **tvar** distribúcie (odchýlky v strede rozsahu). Chi-square test je citlivý na **frekvencie v triedach** (odchýlky v konkrétnych intervaloch). Oba môžu zachytiť iné typy odchýlok — ich kombinácia dáva spoľahlivejší záver. Ak jeden zamietne a druhý nie, zamietame $H_0$ (konzervatívny prístup).

**Napíš PDF exponenciálneho rozdelenia a vysvetli parametre.**  
$f(x; \lambda) = \lambda e^{-\lambda x}$ pre $x \geq 0$. $\lambda > 0$ = intenzita (rate parameter) = priemerný počet udalostí za sekundu. $1/\lambda$ = priemerný čas medzi udalosťami. Čím väčší $\lambda$, tým rýchlejšie klikanie (kratší priemerný čas).

**Čo je vlastnosť "bez pamäte" exponenciálneho rozdelenia?**  
$P(X > t + s \mid X > t) = P(X > s)$. Ak vieme, že klik nenastal počas prvých $t$ sekúnd, pravdepodobnosť, že nenastane ani v nasledujúcich $s$ sekundách, je rovnaká ako na začiatku. Minulosť neovplyvňuje budúcnosť. Exponenciálne rozdelenie je jedinou spojitou distribúciou s touto vlastnosťou.

**Odvod: prečo je $\hat{\lambda} = 1/\overline{x}$ MLE odhadom?**  
Log-likelihood: $\ell(\lambda) = n\ln\lambda - \lambda \sum x_i$. Derivácia: $d\ell/d\lambda = n/\lambda - \sum x_i = 0$. Riešenie: $\hat{\lambda} = n/\sum x_i = 1/\bar{x}$.

**Čo je Poissonov proces a aká je jeho súvislosť s exponenciálnym rozdelením?**  
Poissonov proces modeluje náhodné nezávislé udalosti v čase s konštantnou priemernou intenzitou $\lambda$. Počet udalostí za čas $t$ má Poissonovo rozdelenie. Čas **medzi** po sebe idúcimi udalosťami má **exponenciálne rozdelenie** s rovnakým $\lambda$ — to je kľúčová súvislosť.

**Prečo sú stupne voľnosti $df = k - 2$ a nie $k - 1$?**  
Štandardne pre chi-square test zhody: $df = k - 1 - p$, kde $p$ = počet odhadovaných parametrov z dát. Tu odhadujeme jeden parameter ($\hat{\lambda}$), teda $df = k - 1 - 1 = k - 2 = 18$.

**Prečo sú hranice tried v chi-square teste kvantiley teoretického rozdelenia a nie rovnomerne rozložené?**  
Rovnomerne rozložené hranice by dali triedy s veľmi malou $E_i$ (napr. pre veľmi veľké $x$ by do triedy padlo len pár hodnôt). Delenie malým $E_i$ nestabilizuje chi-square štatistiku. Kvantiley zaručia $E_i = n/k$ pre každú triedu — test je najcitlivejší a najpresnejší.

**Čo je šikmosť (skewness) a prečo je pre exponenciálne rozdelenie vždy 2?**  
Šikmosť = tretí štandardizovaný centrálny moment: $\gamma = E[(X-\mu)^3]/\sigma^3$. Pre exponenciálne rozdelenie platí $\mu = 1/\lambda$, $\sigma = 1/\lambda$, tretí centrálny moment = $2/\lambda^3$. Výsledok: $\gamma = (2/\lambda^3)/(1/\lambda^3) = 2$ — nezávisí od $\lambda$.

**Prečo `is_new_session.iloc[0] = True`?**  
Prvý riadok celého DataFrame nemá predchodcu — `shift(1)` pre neho vráti `NaN`. Podmienka `prev_userid != UserID` by bola `NaN != 5` = `NaN` (nie `True`). Keby zostal `NaN`, `cumsum()` by nefungoval správne. Preto explicitne nastavíme prvý riadok na `True` — vždy začína nové sedenie.

**Aký je rozdiel medzi `shift(1)` v `compute_new_session_flags()` (globálny) a `groupby().shift(1)` v `add_href()`?**  
Globálny `shift(1)` (bez groupby) posunie hodnoty naprieč celým DataFrame — posledný záznam používateľa A dostane UserID/Length prvého záznamu používateľa B. V `compute_new_session_flags()` to nevadí, pretože podmienka `prev_userid != df["UserID"]` práve detekuje takéto hranice. V `add_href()` porovnávame `Referrer` s predošlou URL **toho istého** používateľa — tam by globálny shift dal nesprávny výsledok, preto `groupby("UserID").shift(1)`.

