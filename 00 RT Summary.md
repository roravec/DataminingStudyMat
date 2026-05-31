# Objavovanie znalostí – Kompletný prehľad zadaní a analýz

## Prehľadávanie webu
Program som vyriešil tak, že som najskôr pomocou knižnice `requests` automaticky načítal obsah webových stránok cez HTTP požiadavky. Následne som použil knižnicu `BeautifulSoup`, pomocou ktorej som spracoval HTML kód stránky a extrahoval z neho iba čistý textový obsah. 

Aby výsledný text neobsahoval zbytočné prvky, odstránil som HTML tagy ako `script`, `style` a `noscript`, ktoré obsahujú JavaScript alebo CSS štýly. Potom som text vyčistil od prázdnych riadkov a nepotrebných medzier. Nakoniec som pomocou práce so súbormi v Pythone exportoval získaný text do `.txt` súborov. Každá webová stránka bola uložená do samostatného textového súboru v pripravenom priečinku.

### Najdôležitejšie použité metódy na dosiahnutie cieľa:
* `requests.get()` – načítanie obsahu webovej stránky
* `BeautifulSoup()` – spracovanie HTML dokumentu
* `get_text()` – získanie čistého textu z HTML
* `decompose()` – odstránenie nepotrebných HTML elementov
* `open()` a `write()` – uloženie textu do `.txt` súborov

---

## Reprezentácia textu I
Zadanie som vyriešil tak, že som najskôr načítal Excel súbor obsahujúci frekvencie slov v dokumentoch pomocou knižnice `pandas`. Následne som z pôvodných frekvencií vytvoril tri rôzne textové reprezentácie – binárnu, logaritmickú a inverznú dokumentovú frekvenciu.

* **Pri binárnej reprezentácii** som kontroloval, či sa slovo v dokumente nachádza. Ak áno, zapísala sa hodnota 1, inak 0.
* **Pri logaritmickej reprezentácii** som upravil frekvencie pomocou logaritmu, aby veľmi časté slová nemali príliš veľký vplyv.
* **Pri inverznej dokumentovej frekvencii** som kombinoval frekvenciu slova v dokumente s informáciou o tom, v koľkých dokumentoch sa slovo nachádza. Tým sa zvýraznili dôležité slová, ktoré sa nevyskytujú vo všetkých dokumentoch.

Nakoniec som všetky transformácie exportoval do nového Excel súboru, kde mala každá reprezentácia vlastný hárok.

### Najdôležitejšie použité metódy:
* `pd.read_excel()` – načítanie Excel súboru
* `apply()` a `map()` – transformácia hodnôt
* `math.log10()` – výpočet logaritmickej frekvencie
* `sum()` – výpočet dokumentovej frekvencie
* `ExcelWriter()` a `to_excel()` – export výsledkov do jednotlivých hárkov Excelu

---

## Reprezentácia textu II
Zadanie som vyriešil tak, že som najskôr načítal textové súbory získané z webu a pomocou knižnice `nltk` som ich spracoval na jednotlivé slová. Text bol najskôr rozdelený na vety a následne na tokeny, teda jednotlivé slová.

Potom som odstránil stop slová, teda často používané anglické slová ako *"the"*, *"is"* alebo *"and"*, ktoré nemajú veľkú informačnú hodnotu. Následne som pomocou lematizácie previedol slová na ich základný tvar, teda lemy. Zo získaných lém som vytvoril dátovú maticu frekvencií, kde riadky predstavovali dokumenty a stĺpce jednotlivé lemy. Na základe tejto matice som následne vytvoril binárnu, logaritmickú a inverznú dokumentovú frekvenciu.

### Najdôležitejšie použité metódy:
* `sent_tokenize()` – rozdelenie textu na vety
* `word_tokenize()` – rozdelenie viet na slová
* `WordNetLemmatizer()` – inicializácia lematizátora
* `lemmatize()` – získanie základného tvaru slova
* `stopwords.words()` – odstránenie stop slov
* `DataFrame()` – vytvorenie dátovej matice
* `math.log10()` – výpočet logaritmickej a inverznej frekvencie
* `to_excel()` – export výsledkov do Excelu

---

## Reprezentácia textu III
Zadanie som vyriešil tak, že som načítal päť textových súborov a pomocou knižnice `nltk` som ich spracoval na úrovni jednotlivých slov s kontextom viet. Text bol najskôr rozdelený na vety pomocou `sent_tokenize()`, pričom každej vete bol priradený unikátny globálny identifikátor `sentence_id`, ktorý sa inkrementoval naprieč všetkými dokumentmi. Každá veta bola následne tokenizovaná na jednotlivé slová pomocou `word_tokenize()`.

Z tokenov som odstránil stop slová (pomocou `stopwords.words("english")`) a ponechal som iba slová tvorené výlučne písmenami (`isalpha()`), čím sa zároveň vylúčila interpunkcia. Zostávajúcim slovám som pomocou `pos_tag()` priradil morfologický tag a pomocou `WordNetLemmatizer` som ich previedol na základný tvar – lemu. Každé slovo som zaznamenal spolu s jeho poradím v rámci danej vety (*poradie*), tagom, lemou a identifikátorom vety. Výsledok som uložil do dátovej matice `DataFrame` a exportoval do Excel súboru.

### Najdôležitejšie použité metódy:
* `sent_tokenize()` – rozdelenie textu na vety
* `word_tokenize()` – rozdelenie viet na slová
* `pos_tag()` – morfologická anotácia (POS tagging) zoznamu slov
* `WordNetLemmatizer()` – inicializácia lematizátora
* `lemmatize()` – získanie základného tvaru slova (lemy)
* `stopwords.words()` – množina stop slov pre filtrovanie
* `isalpha()` – filtrovanie interpunkcie a nealfabetických tokenov
* `DataFrame()` – vytvorenie výslednej dátovej matice
* `to_excel()` – export výsledkov do Excel súboru

---

## Čistenie dát I
Zadanie som vyriešil tak, že som načítal logovací súbor vo formáte CSV pomocou `pd.read_csv()` a následne som ho postupne očistil od nepotrebných dát. Najskôr som odstránil stĺpce, ktoré neboli potrebné pre ďalšiu analýzu – konkrétne *Cookie*, *user* a *Bytes* – a zároveň som sa zbavil prázdnych stĺpcov označených ako *Unnamed*, ktoré vznikajú pri načítaní niektorých CSV súborov. Výsledný súbor tak obsahoval len relevantné premenné: *IP*, *DateTime*, *RequestMethod*, *URL*, *StatusCode*, *Referrer* a *Agent*.

Následne som pristúpil k samotným trom krokom čistenia:
1. **Filtrovanie podľa StatusCode:** Ponechal som iba záznamy s hodnotami 200, 206 a 304 (údaje o úspešných požiadavkách a o nezmenenom obsahu) a odstránil som chybové odpovede zo skupín 1xx, 4xx a 5xx.
2. **Filtrovanie podľa RequestMethod:** Ponechal som iba metódy GET a POST a odstránil ostatné typy požiadaviek ako HEAD.
3. **Čistenie stĺpca URL:** Pomocou regulárneho výrazu som odstránamil záznamy odkazujúce na statické súbory bez obsahovej hodnoty – obrázky, CSS štýly, JavaScript súbory, fonty a ďalšie.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `df.loc[:, ~df.columns.str.contains()]` – odstránenie nepomenovaných stĺpcov
* `df.drop()` – odstránenie nepotrebných stĺpcov (*Cookie*, *user*, *Bytes*)
* `df[df['StatusCode'].isin()]` – filtrovanie podľa stavových kódov
* `df[df['RequestMethod'].isin()]` – filtrovanie podľa HTTP metódy
* `str.contains()` s regulárnym výrazom – odstránenie URL so statickými príponami
* `df.to_csv()` – uloženie očisteného súboru

---

## Čistenie dát II
Zadanie som vyriešil tak, že som načítal už očistený logovací súbor z predchádzajúceho zadania a preskúmal jeho obsah s cieľom identificar ďalšie záznamy, ktoré nie sú výsledkom skutočnej aktivity používateľa.

Po analýze URL adries som zistil, že v logu sa tisíckrát opakuje záznam `/navbar/navbar-ukf.html`, ktorý predstavuje interný monitoring šablóny webu a nie je kliknutím používateľa. Tieto záznamy som odstránil pomocou filtrovania stĺpca URL. Po odstránení som skontroloval rozloženie zostávajúcich záznamov podľa `RequestMethod`, `StatusCode` a `Protocol`, aby som overil konzistentnosť výsledku.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru z predchádzajúceho kroku
* `df.copy()` – vytvorenie kópie dataframe pre bezpečné úpravy
* `str.contains()` – identifikácia a filtrovanie záznamov podľa konkrétnej URL
* `value_counts()` – kontrola rozloženia hodnôt v stĺpcoch po očistení
* `df.to_csv()` – uloženie výsledného súboru

---

## Čistenie dát III
Zadanie som vyriešil tak, že som načítal logovací súbor očistený v predchádzajúcich krokoch a identifikoval v ňom IP adresy robotov vyhľadávacích služieb. Roboty som identifikoval na základe prístupu k súboru `robots.txt` – tento súbor si totiž vyhľadávače čítajú ako prvé pri indexovaní webu, čo je spoľahlivý indikátor automatizovaného prístupu.

Pomocou `str.contains()` som vyhľadanú aktivitu s reťazcom `robots.txt` filtroval v stĺpci URL a z týchto špecifických záznamov som extrahoval príslušné IP adresy.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `df['URL'].str.contains()` – vyhľadanie záznamov s prístupom k `robots.txt` v stĺpci URL
* `df['IP']` – extrakcia stĺpca s IP adresami zo zodpovedajúcich záznamov
* `to_csv()` – uloženie zoznamu IP adries robotov do CSV súboru

---

## Čistenie dát IV
Zadanie som vyriešil tak, že som načítal logovací súbor z predchádzajúceho kroku a v troch krokoch som z neho odstránil záznamy, ktoré nepochádzajú od skutočných používateľov.

1. **Krok 1 (Odstránenie cron úloh):** Odstránil som záznamy automatických cron úloh systému *acymailing*, ktoré sa pravidelne opakovali v URL a nepredstavovali ľudskú aktivitu. Použil som na to `str.startswith()` s príslušnou URL predponou.
2. **Krok 2 (Kompletné očistenie IP robotov):** Identifikoval som IP adresy robotov na základe prístupu k súboru `robots.txt`. Tentokrát som však extrahoval unikátne IP adresy (`unique()`) a následne som z logu odstránil úplne všetky záznamy pochádzajúce z týchto IP adries, teda aj ich ostatnú aktivitu na webe, nielen samotný prístup k `robots.txt`.
3. **Krok 3 (Filtrovanie podľa User-Agenta):** Identifikoval som ďalších robotov a crawlerov podľa stĺpca *Agent* (*User-Agent*). Vytvoril som zoznam kľúčových slov typických pre automatizovaný prístup: *bot, crawl, spider, wget, libwww-perl, python, java/* a *facebookexternalhit*. Pomocou regulárneho výrazu som odstránil všetky záznamy, kde sa niektoré z týchto slov nachádzalo v poli Agent.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `str.startswith()` – identifikácia a odstránenie cron úloh podľa URL predpony
* `str.contains()` – vyhľadanie záznamov s `robots.txt` a kľúčových slov v Agentovi
* `unique()` – získanie unikátnych IP adries robotov
* `isin()` – filtrovanie všetkých záznamov patriacich IP adresám robotov
* `df.to_csv()` – uloženie výsledného očisteného súboru

---

## UNIXTIME
Zadanie som vyriešil tak, že som načítal logovací súbor z predchádzajúceho kroku a doplnil ho o novú premennú `unixtime`.

Stĺpec *DateTime* obsahoval dátum a čas v Apache formáte, canyhodnoty začínali úvodnou hranatou zátvorkou `[`, ktorú som najskôr odstránil pomocou `str.lstrip()`. Následne som reťazec skonvertoval na objekt datetime pomocou `pd.to_datetime()` so vzorom formátu `%d/%b/%Y:%H:%M:%S`. Z takto získaného datetime objektu som vytvoril stĺpec `unixtime` pretypovaním na 64-bitové celé číslo (`int64`) a celočíselným vydelením hodnotou $10^9$ (`// 10**9`), čím som získal čistý počet sekúnd od 1. januára 1970. Pomocný stĺpec `DateTime_parsed` som po použití odstránil.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `str.lstrip()` – odstránenie úvodnej hranatej zátvorky z hodnôt DateTime
* `pd.to_datetime()` – parsovanie reťazca dátumu a času na datetime objekt
* `.astype('int64') // 10**9` – konverzia datetime na UNIXTIME v sekundách
* `df.drop()` – odstránenie pomocného stĺpca po konverzii
* `df.to_csv()` – uloženie výsledného súboru

---

## Identifikácia používateľov
Zadanie som vyriešil tak, že som načítal logovací súbor z predchádzajúceho kroku a doplnil ho o novú premennú `UserID`. Najskôr som záznamy usporiadal podľa stĺpcov *IP*, *Agent* a *unixtime* pomocou `sort_values()`, čím som zabezpečil, že záznamy toho istého používateľa sú zoradené chronologicky za sebou. Po usporiadaní som resetoval index pomocou `reset_index()`.

Samotná identifikácia používateľov je založená na predpoklade, že každá unikátna kombinácia IP adresy a poľa User-Agent (*Agent*) predstavuje jedného používateľa. Tieto dva stĺpce som spojil do jedného reťazca oddeleného znakom `|` a pomocou `pd.factorize()` som každej unikátnej kombinácii priradil číselný identifikátor. Výsledné ID som uložil do nového stĺpca `UserID`. Takto bolo identifikovaných približne **4040 unikátnych používateľov**.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `sort_values()` – usporiadanie záznamov podľa IP, Agent a unixtime
* `reset_index()` – resetovanie indexu po usporiadaní
* `pd.factorize()` – priradenie unikátneho číselného ID každej kombinácii IP + Agent
* `nunique()` – zistenie celkového počtu identifikovaných používateľov
* `df.to_csv()` – uloženie výsledného súboru

---

## Premenná čas strávený na stránke - Length
Zadanie som vyriešil tak, že som načítal logovací súbor z predchádzajúceho kroku a doplnil ho o novú premennú `Length`, ktorá vyjadruje čas strávený na stránke v sekundách.

Záznamy som najskôr usporiadal podľa `UserID` a `unixtime`. Následne som pre každý záznam vypočítal rozdiel medzi jeho unixtime and unixtime nasledujúceho záznamu v rámci toho istého používateľa pomocou `groupby()` a `shift(-1)`.
* Ak bol rozdiel **menší ako 3600 sekúnd (60 minút)** a nasledujúci záznam patril tomu istému používateľovi, zapísala sa hodnota do stĺpca `Length`.
* V opačnom prípade – teda pri poslednom zázname používateľa alebo pri prístupovej prestávke dlhšej ako 60 minút – som zapísal prázdnu hodnotu `None`.

Pomocné stĺpce som po výpočte odstránil.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `sort_values()` – usporiadanie podľa UserID a unixtime
* `groupby() + shift(-1)` – získanie hodnoty nasledujúceho záznamu u rovnakého používateľa
* `where()` – podmienené priradenie hodnoty alebo None
* `df.drop()` – odstránenie pomocných stĺpcov
* `df.to_csv()` – uloženie výsledného súboru

---

## Identifikácia sedení: STT\_MEAN
Zadanie som vyriešil tak, že som načítal logovací súbor z predchádzajúceho kroku, pričom záznamy som usporiadal podľa `UserID` a `unixtime`. Následne som vypočítal priemernú hodnotu stĺpca `Length` – tzv. `STT_Mean` –, ktorá slúži ako prahová hodnota časového okna relácie (sedenia).

Nové sedenie začína vždy, keď nastane aspoň jedna z troch podmienok pre predchádzajúci záznam:
1. Ide o úplne prvý záznam daného používateľa (zmena `UserID`).
2. Predošlá hodnota `Length` je `None` (medzera medzi požiadavkami bola dlhšia než 60 minút).
3. Predošlá hodnota `Length` je väčšia alebo rovná vypočítanej `STT_Mean`.

Tieto podmienky som vyhodnotil pomocou `shift(1)` na predchádzajúci riadok a výsledný boolean stĺpec som pomocou `cumsum()` pretransformoval na postupné číselné ID sedenia.

### Teoretický koncept (STT\_Mean):
* **STT** znamená *Session Time Threshold* – prahová hodnota časového okna, ktorá rozhoduje o ukončení starej relácie a začatí novej.
* **STT\_Mean** je táto prahová hodnota vypočítaná ako priemer stĺpca `Length`. Funguje tak, že ak používateľ medzi dvoma kliknutiami čakal dlhšie, než je tento priemer, systém vygeneruje nové ID sedenia. Logika vychádza z toho, že bežní ľudia klikajú v rýchlom rytme a dlhšia pauza znamená odchod od počítača.

#### Príklad správania:
Ak je `STT_Mean` = 150 sekúnd:
* Používateľ klikol o 08:00:00 a potom o 08:02:00 $\rightarrow$ rozdiel je 120 sekúnd $\rightarrow$ **stále to isté sedenie**.
* Používateľ klikol o 08:02:00 a potom o 08:10:00 $\rightarrow$ rozdiel je 480 sekúnd $\rightarrow$ **vzniká nové sedenie**.

`STT_Mean` je najjednoduchší odhad. `STT_Q` (kvartilový odhad) je štatisticky sofistikovanejší, pretože nie je umelo posunutý extrémne dlhými pauzami nahor.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `sort_values()` – usporiadanie podľa UserID a unixtime
* `df['Length'].mean()` – výpočet priemernej hodnoty STT\_Mean
* `shift(1)` – získanie hodnôt predchádzajúceho záznamu
* `|` (bitový OR) – kombinácia troch podmienok pre začiatok nového sedenia
* `cumsum()` – generovanie postupného číselného ID sedenia
* `df.to_csv()` – uloženie výsledného súboru

---

## Identifikácia sedení: STT\_Q
Zadanie som vyriešil tak, že som načítal logovací súbor a doplnil ho o novú identifikáciu sedení pomocou kvartilového odhadu časového okna `STT_Q`.

Záznamy som zoradil podľa `UserID` a `unixtime`. Z hodnôt stĺpca `Length` som vypočítal dolný kvartil $Q_1$ (25. percentil), horný kvartil $Q_3$ (75. percentil) a kvartilové rozpätie $IQR = Q_3 - Q_1$. Prahová hodnota bola definovaná podľa vzorca pre detekciu odľahlých hodnôt (outlierov):

$$STT\_Q = Q_3 + 1.5 \times IQR$$

Hodnoty nad touto hranicou sa považujú za štatisticky neobvyklé (príliš dlhé pauzy). Logika priradenia nového sedenia zostáva identická (zmena UserID, predošlá hodnota None, alebo predošlý Length $\ge STT\_Q$). Výsledné ID sedenia sa zapísalo do stĺpca `STT_Q` pomocou `cumsum()`.

### Prečo je STT\_Q lepší ako STT\_Mean?
`STT_Mean` je vysoko citlivý na extrémne hodnoty (ak niekto nechá otvorený prehliadač cez noc, vznikne pauza napr. 50 000 sekúnd, ktorá priemer prudko skreslí nahor). `STT_Q` tento problém nemá, nakoľko kvartily počítajú so strednými 50 % dát a extrémy ich neovplyvnia. Vyjadruje tak objektívnejšie kritérium postavené na typickom správaní používateľa.

### Najdôležitejšie použité metódy:
* `pd.read_csv()` – načítanie logovacieho súboru
* `sort_values()` – usporiadanie podľa UserID a unixtime
* `quantile(0.25)` a `quantile(0.75)` – výpočet dolného a horného kvartilu
* `shift(1)` – prístup k predošlému záznamu
* `|` (bitový OR) – zjednotenie podmienok
* `cumsum()` – generovanie číselného ID sedenia
* `df.to_csv()` – uloženie výsledného súboru

---

## Identifikácia sedení: SLength
Zadanie som vyriešil tak, že som načítal logovací súbor `Log_jeden_den_cleaned_IV_sttq.csv` a doplnil ho o novú identifikáciu sedení pomocou fixne stanoveného časového okna **SLength**.

Na rozdiel od predošlých štatistických metód táto využíva **pevný prah 600 sekúnd (10 minút)**. Ak používateľ medzi kliknutiami čaká viac ako 10 minút, automaticky sa zakladá nové sedenie. Logika podmienok je rovnaká (zmena UserID, None predošlý Length, alebo predošlý Length $\ge 600$). Výsledné ID sedenia som uložil do stĺpca `SLength` pomocou `cumsum()` a výsledok uložil a zabalil do ZIP archívu.

### Výhody a nevýhody SLength:
* **Výhoda:** Maximálna jednoduchosť a zrozumiteľnosť; hodnota 10 minút predstavuje overený štandard v webovej analytike (využíva ho napr. staršie Google Analytics).
* **Nevýhoda:** Úplne ignoruje reálne a špecifické správanie používateľov na danom type webu (pri dlhých článkoch môže byť 10 minút príliš krátke okno).

### Najdôležitejšie použité metódy:
* `pd.read_csv()`, `sort_values()`, `shift(1)`, `|`, `cumsum()`, `df.to_csv()`

---

## RLength – overenie exponenciálneho rozdelenia
Zadanie som vyriešil tak, že som načítal logovací súbor a matematicky overoval, či premenná `Length` vykazuje vlastnosti exponenciálneho rozdelenia. Najskôr som spočítal základné deskriptívne štatistiky: priemer, smerodajnú odchýlku a šikmosť. Teoretická šikmosť exponenciálneho rozdelenia by mala byť blízka hodnote 2. Následne som pomocou metódy maximálnej vierohodnosti (MLE) nafitoval exponenciálne rozdelenie a odhadol parameter $\lambda$.

Na formálne overenie som vykonal dva testy:
* **Kolmogorov-Smirnov test:** porovnáva empirickú a teoretickú distribučnú funkciu (ak p-hodnota < 0.05, hypotézu o exponenciálnom rozdelení zamieta).
* **Chi-square test zhody (goodness-of-fit):** dáta rozdelil do 20 tried s rovnakou teoretickou pravdepodobnosťou a porovnal očakávané početnosti s pozorovanými.

**Oba testy striktne zamietli nulovú hypotézu na hladine významnosti 0.05.** Výsledok som doložil 4 grafmi: histogram s exponenciálnou krivkou, histogram s logaritmickou osou Y, porovnanie empirickej a teoretickej CDF a Q-Q plot. Zo všetkých testov a grafov jednoznačne vyplynulo, že **premenná Length nemá exponenciálne rozdelenie** (hustota hodnôt pri nule je príliš vysoká a Q-Q plot vykazuje masívne odchýlky).

### Najdôležitejšie použité metódy:
* `expon.fit()`, `kstest()`, `chi2.cdf()`, `np.histogram()`, `plt.hist() / semilogy()`, `expon.cdf() / expon.pdf()`, `expon.ppf()`, `plt.savefig()`.

---

## Identifikácia sedení: RLength Heuristika
Zadanie som vyriešil tak, že som načítal logovací súbor a identifikoval sedenia pomocou heuristiky **RLength**. Táto metóda predpokladá (napriek predošlému zamietnutiu), že premenná `Length` teoreticky sleduje exponenciálne rozdelenie a na základe tohto predpokladu hľadá hraničný čas sedenia $C$.

Z nenulových hodnôt som vypočítal priemer a pomocou MLE odhadol parameter $\lambda = 1 / \text{mean}(Length)$. Následne som cez kvantilovú funkciu vypočítal hraničný čas:

$$C = \frac{-\ln(1 - p)}{\lambda}$$

Kde parameter $p = 0.40$ (predpokladaný podiel navigačných stránok na webe, na ktorých používateľ trávi iba minimálny čas). Hodnota $C$ tak predstavuje čas, pod ktorým leží presne 40 % všetkých medzichodov. Ak je medzera dlhšia ako $C$, začína nové sedenie. Výsledné ID sa zapísalo do stĺpca `RLength` pomocou `cumsum()`.

### Teoretická podstata RLength:
Metóda uvažuje, že web pozostáva z dvoch typov stránok:
1. **Navigačné stránky:** Používateľ ich rýchlo preskočí (homepage, menu, vyhľadávanie).
2. **Obsahové stránky:** Používateľ na nich zostáva dlhšie (samotný článok, dlhé video, formulár).

Hlavnou výhodou oproti ostatným metódam je, že parameter $p = 0.40$ sa dá kalibrovať na mieru konkrétnemu webu. Ak má web prirodzene viac navigačných stránok, parameter $p$ sa zvýši, čím sa zníži prah $C$ a vznikne viac kratších sedení.

### Najdôležitejšie použité metódy:
* `dropna() + mean()`, `np.log()`, `shift(1)`, `|`, `cumsum()`, `df.to_csv()`.

---

## Identifikácia sedení: h-ref Heuristika
Zadanie som vyriešil tak, že som načítal logovací súbor `Log_jeden_den_cleaned_IV_rlength.csv` a identifikoval sedenia pomocou heuristiky **h-ref**. Táto metóda sa zásadne líši od ostatných tým, že okrem samotného času analyzuje pole **Referrer** (informáciu o tom, z akej konkrétnej adresy používateľ prišiel). Ako časové okno $\Delta$ (delta) bol zvolený priemer `STT_Mean`.

Dva po sebe idúce záznamy rovnakého používateľa patria do **rovnakého sedenia**, ak je splnená aspoň jedna z dvoch podmienok:
1. **Referrer aktuálneho záznamu == URL predošlého záznamu** (vyjadruje priamy navigačný odkaz na stránke – používateľ preukázateľne klikol na link priamo na webe).
2. **Časová medzera medzi záznamami je $\le \Delta$**.

Nové sedenie vzniká až vtedy, keď neplatí ani jedna z podmienok, alebo pri zmene používateľa. Keďže stĺpec *Referrer* obsahoval absolútnu URL (`https://www.ukf.sk/cesta`) a stĺpec *URL* iba relatívnu cestu (`/cesta`), pred porovnaním som z referrera odstránil doménu pomocou pomocnej funkcie. ID sedenia sa zapísalo do stĺpca `hRef` cez `cumsum()` a pomocný stĺpec sa zmazal.

### Najdôležitejšie použité metódy:
* `mean()`, `apply()`, `groupby() + shift(1)`, `& / | / ~` – kombinácia logických podmienok, `cumsum()`, `df.drop()`, `df.to_csv()`.

---

## Dopĺňanie ciest (STT\_Mean, STT\_Q, RLength, h-ref)
Všetky štyri zadania riešia identický problém – **rekonštrukciu (dopĺňanie) chýbajúcich medzistránok** v navigačných reťazcoch používateľov, líšia sa iba podkladovým stĺpcom identifikovaných sedení.

### Spoločný popis riešenia:
Načítal som logovací súbor `Log_jeden_den_cleaned_IV_href.csv`, ktorý obsahoval sedenia zo všetkých predošlých fáz. Z poľa Referrer (po očistení od domény) som zostavil **mapu webu** – slovník prepojení, kde kľúčom bola zdrojová stránka a hodnotou množina stránok, na ktoré z nej smerovali odkazy. 

Následne som pre každé sedenie chronologicky prechádzal záznamy a hľadal prerušenia reťazca – situácie, kedy referrer aktuálnej stránky nezodpovedal URL bezprostredne predošlej stránky (používateľ preskočil medzistránky). V takom prípade program pomocou **BFS algoritmu (prehľadávanie do šírky)** vyhľadal najkratšiu cestu medzi predošlou a aktuálnou URL v mape webu. Ak cesta existovala, doplnil som medzistránky ako nové riadky s rovnomerne interpolovaným časom `unixtime`. Záznamy sa zjednotili, zoradili a uložili.

### Špecifické odlišnosti a štatistika úkonov:

| Zadanie | Stĺpec sedení | Max. hĺbka BFS | Počet doplnených záznamov | Výstupný súbor |
| :--- | :--- | :---: | :---: | :--- |
| **STT\_Mean** | `STT_Mean` | 4 | ~750 | `..._STT_Mean.csv` |
| **STT\_Q** | `STT_Q` | 4 | ~750 | `..._paths_STT_Q.csv` |
| **RLength** | `RLength` | 6 | ~850 | `..._paths_RLength.csv` |
| **h-ref** | `hRef` | 4 | ~690 | `..._paths_hRef.csv` |

`RLength` vyžaduje najväčšiu hĺbku BFS (6) a generuje najviac doplnených záznamov, pretože produkuje väčšie množstvo kratších sedení, v ktorých chýbajú navigačné kroky najčastejšie. Výsledný súbor bol uložený pomocou `df.to_csv()`.

---

## Prieskum dát o používaní webu komerčnej banky (2009–2012)
Zadanie riešilo komplexnú exploračnú analýzu reálneho datasetu webového logu komerčnej banky (`logs5.csv`) s **2 071 235 záznamami a 24 premennými** za obdobie rokov 2009–2012. Analýza bola rozdelená do 11 tematických celkov tak, aby pokryla premenné zo všetkých podstatných skupín charakterizujúcich prístupy.

* **Závislé premenné (DV - navštívený obsah z URL):** `category` (kategória obsahu), `webPart` (časť webu) a `urlExt` (typ súboru).
* **Nezávislé premenné (IV - čas prístupu z timestampu):** `year`, `quartal`, `yearQuartal`, `week`, `hour`, `dayofweek` a binárna premenná `crisis` (rozdeľujúca obdobie finančnej krízy 2009–2010 od post-krízového obdobia 2011–2012).
* **Doplnkové premenné:** `internal` (interný/externý prístup) a `length` (čas strávený na stránke).

### Výsledky a štatistické overenia:
* Vývoj návštevnosti bol analyzovaný pomocou časových radov a heatmáp (hodina × deň v týždni, týždeň × rok). Odhalila sa masívna koncentrácia aktivity počas pracovných hodín (8:00–17:00) a pracovných dní. Vyčistená vzorka bola tvorená výlučne HTML stránkami.
* Vzťah medzi premennými `crisis` a `category` bol validovaný **Chi-square testom** a koeficientom **Cramérovo V** – závislosť sa ukázala ako štatisticky významná.
* Variabilita času stráveného na stránke (`length`) bola analyzovaná podľa kategórií obsahu pomocou boxplotov, deskriptívnej štatistiky (vrátane koeficientu variácie CV), histogramov a Q-Q plotov. **Kruskal-Wallis test** potvrdil štatisticky významné rozdiely v dĺžke návštevy medzi jednotlivými kategóriami obsahu.
* Stabilita/trend návštevnosti v priebehu roka bola overovaná **Spearmanovou koreláciou**, pričom nadobúdala striedavo kladné aj záporné hodnoty v závislosti od konkrétneho roku, čo značí nestabilitu trendu.

### Najdôležitejšie použité metódy:
* `pd.read_csv()`, `value_counts() / groupby()`.

---

## Extrakcia vzorov a metaanalýza (Komerčná banka)
Zadanie spracovávalo rovnaký dataset banky (`logs5.csv`, 2 071 235 záznamov) s cieľom extrahovať pokročilé vzory správania (asociačné pravidlá a sekvencie) a vykonať ich metaanalýzu naprieč 16 kvartálmi. 

* **Krok 1 (Filtrovanie období):** Dáta boli rozdelené na 16 kvartálov (od `09Q1` po `12Q4`). Prvých 8 kvartálov reprezentovalo krízu (2009–2010), druhých 8 post-krízu (2011–2012). Pre každý kvartál bol vytvorený samostatný subset.
* **Krok 2 (Príprava transakcií):** Pre asociačnú analýzu sa z každého sedenia (relácie) vytvorila množina navštívených kategórií (`category`), resp. podkategórií (`webPart`). Pre sekvenčnú analýzu boli dáta navyše chronologicky zoradené podľa `unixTime`, aby vznikli usporiadané sekvencie.
* **Krok 3 (Asociačná analýza - Apriori):** Spustená pre všetkých 16 kvartálov samostatne. Pre úroveň `category` boli nastavené parametre: $\text{min\\_support} = 0.05,\ \text{min\\_confidence} = 0.50,\ \text{min\\_lift} = 1.0$. Pre komplexnejší stĺpec `webPart` (hrozba kombinatorickej explózie) boli nastavené prísnejšie mantinely: $\text{min\\_support} = 0.10,\ \text{min\\_confidence} = 0.70,\ \text{max\\_len} = 3$. Ak algoritmus nenašiel aspoň 10 pravidiel, automaticky znižoval podporu o 0.01 až na úplné dno 0.01.* **Krok 4 (Sekvenčná analýza - AprioriAll):** Pre každý kvartál boli extrahované sekvenčné pravidlá (zohľadňujúce striktné poradie krokov v relácii) na úrovni `category` aj `webPart`.
* **Krok 5 (Dátová matica vzorov):** Zo všetkých extrahovaných pravidiel naprieč kvartálmi sa zostavila jedna veľká dátová matica jedinečných vzorov, kde riadky tvorili samotné pravidlá a stĺpce jednotlivé kvartály s binárnym ohodnotením 0 alebo 1 podľa prítomnosti vzoru v danom čase.

### Hlavné zistenia metaanalýzy:
* V období finančnej krízy dominovali pravidlá prepájajúce kategórie *Business Conditions*, *Pillar3 disclosure requirements* a *We support..*, čo jasne odrážalo zvýšený záujem o regulačné a obchodné podmienky.
* V post-krízovom období sa stredobodom záujmu stali témy *Pillar3 related* a *Reputation*.
* **Cochran Q test** jednoznačne potvrdil štatisticky významné rozdiely vo výskyte extrahovaných vzorov naprieč kvartálmi, čo matematicky dokazuje nestabilitu používateľských navigačných návykov v čase.

### Najdôležitejšie použité metódy:
* `groupby() + apply()` – príprava transakcií a sekvencií pre každý kvartál
* `TransactionEncoder()` – kódovanie transakcií do binárnej matice
* `apriori()` – extrakcia frekventovaných množín z knižnice `mlxtend`
* `association\_rules()` – generovanie finálnych asociačných pravidiel
* Vlastná implementácia algoritmu `AprioriAll` – extrakcia sekvenčných pravidiel
* `chi2.sf()` – výpočet p-hodnoty Cochran Q testu
* `kendalltau()` – výpočet Kendallovho W (koeficient konkordancie)
* `sns.heatmap()` – vizualizácia výslednej matice vzorov a období
* `pd.DataFrame()` – finálne zostavenie dátová matice jedinečných vzorov
