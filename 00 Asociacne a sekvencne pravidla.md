# 📚 Študijný materiál: Asociačné a sekvenčné pravidlá
*(Pripravené z podkladov ASOCIACNE_PRAVIDLA.pdf a SEKVENCNE_PRAVIDLA.pdf s vysvetlivkami)*

---

## 1. Asociačné pravidlá (Úvod a základné pojmy)
[cite_start]Asociačné pravidlá patria medzi najpopulárnejšie **symbolické metódy hĺbkovej analýzy dát** (data miningu) a strojového učenia[cite: 2, 7]. [cite_start]Sú ideálne pre **kvalitatívne (kategorické) dáta**[cite: 7].

💡 **CHÁPANIE POLOPATISTICKY:** Predstav si databázu nákupov v supermarkete. Cieľom asociačných pravidiel je zistiť, ktoré tovary ľudia kupujú *spolu*. [cite_start]Nehľadáme príčinu (že chlieb spôsobuje kúpu masla), ale čistú štatistickú súvislosť (asociáciu)[cite: 4, 16].

* [cite_start]**Využitie:** Analýza nákupného košíka, finančné dáta, cenzus a pod[cite: 3].
* [cite_start]**Úprava dát:** Ak máme čísla (kvantitatívne dáta), musíme ich najskôr **diskretizovať** – rozdeliť do intervalov (napr. vek 0-18, 19-30), aby sme s nimi vedeli pracovať ako s kategóriami[cite: 8].
* [cite_start]**Formát pravidla:** Používa sa konštrukcia **IF (podmienka/antecedent) THEN (záver/consequent)**[cite: 5, 12, 15].
  * [cite_start]*Príklad z praxe:* $\{chlieb, syr\} \Rightarrow \{maslo\}$[cite: 18].
  * [cite_start]*Interpretácia:* Ak si zákazník kúpi chlieb a syr, s veľkou pravdepodobnosťou kúpi aj maslo[cite: 19].
* [cite_start]**Matematický zápis:** Implikácia $X \Rightarrow Y$, pričom predpoklad $X$ a záver $Y$ nesmú mať spoločné prvky ($X \cap Y = \emptyset$)[cite: 11, 12]. [cite_start]Množiny položiek sa nazývajú **položkové množiny (itemsets)**[cite: 13].

---

## 2. Tri kľúčové miery (Čo tie čísla znamenajú?)
[cite_start]Pravidlá sa nehľadajú náhodne, musíme ich zmerať pomocou troch veličín[cite: 16, 25, 28]:

| Miera | Matematický vzorec / Definícia | 💡 Čo to hovorí v praxi? |
| :--- | :--- | :--- |
| **Podpora** *(Support)* | [cite_start]$Support(X \Rightarrow Y) = P(X \cup Y)$ [cite: 22] | [cite_start]**Ako často sa to stáva?** Hovorí nám, aké percento zo *všetkých* nákupov v databáze obsahuje celú kombináciu (X aj Y spolu)[cite: 23, 24]. [cite_start]Ak je podpora nízka, pravidlo je bezvýznamné, lebo sa týka málokoho[cite: 31]. |
| **Spoľahlivosť** *(Confidence)* | [cite_start]$Confidence(X \Rightarrow Y) = \frac{Support(X \cup Y)}{Support(X)}$ [cite: 25] | **Aké silné je to pravidlo?** Predstav si len ľudí, ktorí už majú v košíku $X$ (napr. chlieb a syr). Koľko percent z nich si k tomu *naozaj* prihodí aj $Y$ (maslo)? [cite_start]Vyjadruje to silu/istotu pravidla[cite: 26, 31]. |
| **Zdvih** *(Lift)* | [cite_start]$Lift(X \Rightarrow Y) = \frac{Confidence(X \Rightarrow Y)}{Support(Y)}$ [cite: 28] | [cite_start]**Je to užitočné, alebo je to len náhoda?** Určuje, koľko-krát častejšie sa kupujú spolu, než keby nakupovali úplne náhodne[cite: 28]. [cite_start]<br>• **Lift > 1:** Kupujú sa spolu častejšie, je tam väzba[cite: 29].<br>• **Lift = 1:** Položky sú nezávislé (čistá náhoda). |

* [cite_start]Analytik si na začiatku nastaví **minimum support** (napr. pravidlo nás zaujíma, len ak sa objaví aspoň v 5 % nákupov) a **minimum confidence** (musí platiť aspoň na 60 % ľudí)[cite: 30].
* [cite_start]Množina, ktorá prejde cez filter minimálnej podpory, sa nazýva **frekventovaná položková množina**[cite: 32, 37].

---



## 3. Algoritmus Apriori (Ako nájsť pravidlá bez toho, aby počítač zhorel?)
Keby sme mali v obchode 1000 položiek, kombinácií všetkých tovarov by bolo gigantické množstvo ($2^{1000}$). [cite_start]Algoritmus Apriori prináša geniálny trik, ako tento priestor osekať[cite: 45, 46, 48].

💡 **HLAVNÁ MYŠLIENKA (Apriori vlastnosť):**
[cite_start]Ak nejaká množina položiek **nie je** frekventovaná (nikto ju nekupuje), tak **žiadna jej väčšia nadmnožina tiež nemôže byť frekventovaná**[cite: 46].
* *Príklad:* Ak ľudia nekupujú kombináciu `{kaviár, mlieko}`, je absolútne zbytočné testovať kombináciu `{kaviár, mlieko, chlieb}`. [cite_start]Automaticky ju môžeme zahodiť[cite: 46, 53].

### [cite_start]Proces prebieha v dvoch fázach[cite: 33]:
1.  [cite_start]**Fáza: Nájdenie frekventovaných množín do šírky** (od 1-prvkových po k-prvkové)[cite: 45]:
    * [cite_start]**Spájanie:** Vezmeme úspešné položky z minulého kroku ($L_{k-1}$) a pospájame ich do väčších kandidátov ($C_k$)[cite: 74].
    * [cite_start]**Orezávanie (Pruning):** Ak zistíme, že nejaká podkombinácia nového kandidáta minule neuspela, kandidáta rovno vymažeme[cite: 75].
    * [cite_start]**Test podpory:** Pre tie kombinácie, ktoré prežili orezanie, spočítame reálny výskyt v databáze a tie úspešné uložíme do $L_k$[cite: 76].
2.  [cite_start]**Fáza: Generovanie pravidiel zo získaných množín**[cite: 77]:
    * [cite_start]Vezmeme vygenerovanú frekventovanú množinu $T$ a rozdelíme ju na podmienku $X$ a následok $Y$[cite: 78].
    * [cite_start]Trik so spoľahlivosťou: Ak nespĺňa podmienku spoľahlivosti pravidlo s úzkou podmienkou (napr. `{1, 2} => {4}`), potom ju nebudú spĺňať ani ešte voľnejšie pravidlá (napr. `{1} => {2, 4}`) a netreba ich vôbec počítať[cite: 83, 85].

---

## 4. Sekvenčné pravidlá a algoritmus AprioriAll
[cite_start]Sekvenčné pravidlá posúvajú asociačné pravidlá na novú úroveň – pridávajú do hry **ČAS A PORADIE**[cite: 89, 90, 95].

💡 **CHÁPANIE POLOPATISTICKY:**
[cite_start]Pri asociačných pravidlách nahádžeš veci do jedného košíka naraz[cite: 14]. [cite_start]Pri sekvenčných pravidlách ťa zaujíma história správania jedného človeka v čase[cite: 95, 97, 101]. 
* *Asociačné:* Zákazník si kúpil `[Kryt na mobil, Nabíjačku]`.
* [cite_start]*Sekvenčné:* Zákazník si v pondelok kúpil `[Mobil]`, v stredu si pozrel `[Kryt]` a v piatok kúpil `[Ochranné sklo]`[cite: 95, 97, 102].

### Hlavné rozdiely v bodoch:

1.  [cite_start]**Časová pečiatka:** Sekvenčné dáta vyžadujú identifikátor používateľa a čas, kedy akciu vykonal[cite: 95, 101].
2.  **Definícia Podpory (Support):**
    * [cite_start]*Pri asociačných* je podpora percento **transakcií/nákupov**[cite: 23, 99].
    * [cite_start]*Pri sekvenčných* je podpora percento **používateľov**, v ktorých celej histórii sa táto sekvencia (poradie krokov) nachádza[cite: 99, 100].
3.  **Nesúvislosť:** Kroky nemusia nasledovať tesne po sebe. [cite_start]Ak používateľ navštívi stránku A, potom X a potom B, stále v tom je započítaná sekvencia $\langle A, B \rangle$[cite: 98].

### Prečo klasické Apriori zlyháva pri analýze webu (Web Log Mining)?
[cite_start]Ak analyzujeme klikanie ľudí na webe, klasické Apriori nevie, čo bolo skôr a čo neskôr, a ignoruje fakt, že ľudia chodia po stránkach dopredu aj dozadu[cite: 105, 106]. 

[cite_start]Algoritmus **AprioriAll** preto najskôr zoradí dáta chronologicky podľa používateľov a pri hľadaní dvojprvkových kandidátov ($C_2$) robí **úplné spájanie**[cite: 101, 105]. [cite_start]To znamená, že generuje a testuje obe možnosti zvlášť: sekvenciu $\langle A, B \rangle$ aj sekvenciu $\langle B, A \rangle$, pretože na webe ide o dva úplne odlišné scenáre správania[cite: 107, 108].
