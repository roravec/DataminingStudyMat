# 📚 Študijný materiál: Asociačné a sekvenčné pravidlá
*(Pripravené z podkladov ASOCIACNE_PRAVIDLA.pdf a SEKVENCNE_PRAVIDLA.pdf s vysvetlivkami)*

---

## 1. Asociačné pravidlá (Úvod a základné pojmy)
[cite_start]Asociačné pravidlá patria medzi najpopulárnejšie **symbolické metódy hĺbkovej analýzy dát** (data miningu) a strojového učenia[cite: 2, 7]. [cite_start]Sú ideálne pre **kvalitatívne (kategorické) dáta**[cite: 7].

💡 **CHÁPANIE POLOPATISTICKY:** Predstav si databázu nákupov v supermarkete. Cieľom asociačných pravidiel je zistiť, ktoré tovary ľudia kupujú *spolu*. Nehľadáme príčinu (že chlieb spôsobuje kúpu masla), ale čistú štatistickú súvislosť (asociáciu).

* [cite_start]**Využitie:** Analýza nákupného košíka, finančné dáta, cenzus a pod. [cite: 3]
* [cite_start]**Úprava dát:** Ak máme čísla (kvantitatívne dáta), musíme ich najskôr **diskretizovať** – rozdeliť do intervalov (napr. vek 0-18, 19-30), aby sme s nimi vedeli pracovať ako s kategóriami[cite: 8].
* [cite_start]**Formát pravidla:** Používa sa konštrukcia **IF (podmienka / antecedent) THEN (záver / consequent)**[cite: 5, 12, 15].
  * [cite_start]*Príklad z praxe:* `{chlieb, syr} => {maslo}` [cite: 18]
  * [cite_start]*Interpretácia:* Ak si zákazník kúpi chlieb a syr, s 57% pravdepodobnosťou kúpi aj maslo[cite: 19].
* [cite_start]**Matematický zápis:** Implikácia `X => Y`, pričom predpoklad `X` a záver `Y` sú podmnožiny všetkých položiek a ich prienik je prázdny[cite: 11, 12]. [cite_start]Množiny položiek sa nazývajú **položkové množiny (itemsets)**[cite: 13].

---

## 2. Tri kľúčové miery (Čo tie čísla znamenajú?)
[cite_start]Pravidlá sa nehľadajú náhodne, musíme ich zmerať pomocou troch veličín[cite: 16]:

| Miera | Definícia | 💡 Čo to hovorí v praxi? |
| :--- | :--- | :--- |
| **Podpora** *(Support)* | [cite_start]`Support(X => Y) = P(X U Y)` [cite: 22] | [cite_start]**Como často sa to stáva?** Hovorí nám, aké percento zo *všetkých* nákupov v databáze obsahuje celú kombináciu X aj Y spolu[cite: 23, 24]. [cite_start]Ak je podpora nízka, pravidlo sa týka málokoho[cite: 30, 31]. |
| **Spoľahlivosť** *(Confidence)* | [cite_start]`Confidence(X => Y) = Support(X U Y) / Support(X)` [cite: 25] | [cite_start]**Aké silné je to pravidlo?** Predstav si len ľudí, ktorí už majú v košíku X[cite: 26]. Koľko percent z nich si k tomu prihodí aj Y? [cite_start]Vyjadruje to percentuálny podiel pravidiel zo všetkých, ktoré obsahujú X[cite: 26, 27]. |
| **Zdvih** *(Lift)* | [cite_start]`Lift(X => Y) = Confidence(X => Y) / Support(Y)` [cite: 28] | [cite_start]**Je to užitočné, alebo je to len náhoda?** Určuje, koľko-krát častejšie sa kupujú spolu, než keby nakupovali úplne nezávisle[cite: 28]. [cite_start]<br>• **Lift > 1:** Kupujú sa spolu častejšie ako zvlášť, je tam väzba[cite: 29]. |

* [cite_start]Analytik si na začiatku nastaví **minimum support** a **minimum confidence**[cite: 30].
* [cite_start]Množina, ktorá prejde cez filter minimálnej podpory, sa nazýva **frekventovaná položková množina**[cite: 32, 37].

---

## 3. Algoritmus Apriori (Ako nájsť pravidlá bez toho, aby počítač zhorel?)
Keby sme mali v obchode veľa položiek, kombinácií všetkých tovarov by bolo obrovské množstvo. [cite_start]Algoritmus Apriori prináša trik, ako tento priestor osekať[cite: 43, 48].

💡 **HLAVNÁ MYŠLIENKA (Apriori vlastnosť):**
[cite_start]Každá podmnožina frekventovanej množiny musí byť tiež frekventovaná[cite: 46]. [cite_start]Ak nejakú podkombináciu ľudia nekupujú, nebudú kupovať ani jej väčšiu verziu[cite: 46].
* [cite_start]*Príklad:* Ak ľudia nekupujú dvojicu položiek `{3, 4}`, je zbytočné testovať trojicu `{1, 3, 4}`[cite: 53]. [cite_start]Automaticky ju môžeme zahodiť[cite: 53].

### [cite_start]Proces prebieha v dvoch fázach[cite: 33]:
1. [cite_start]**Fáza: Nájdenie frekventovaných množín do šírky** (od 1-prvkových po k-prvkové)[cite: 45]:
   * [cite_start]**Spájanie:** Vezmeme úspešné položky z minulého kroku a pospájame ich do väčších kandidátov[cite: 47, 74].
   * [cite_start]**Orezávanie (Pruning):** Ak zistíme, že nejaká podkombinácia nového kandidáta minule neuspela, kandidáta rovno vymažeme[cite: 53, 75].
   * [cite_start]**Test podpory:** Pre tie kombinácie, ktoré prežili orezanie, overíme reálny výskyt v databázi a úspešné si odložíme[cite: 76].
2. [cite_start]**Fáza: Generovanie pravidiel zo získaných množín**[cite: 33]:
   * [cite_start]Vezmeme vygenerovanú frekventovanú množinu a rozdelíme ju na podmienku X a následok Y[cite: 78].
   * [cite_start]Trik so spoľahlivosťou: Ak nespĺňa podmienku spoľahlivosti pravidlo s úzkou podmienkou (napr. `{1, 2} => {4}`), potom ju nebudú spĺňať ani ešte voľnejšie pravidlá (napr. `{1} => {2, 4}`) a netreba ich vôbec počítať[cite: 84, 85].

---

## 4. Sekvenčné pravidlá a algoritmus AprioriAll
[cite_start]Sekvenčné pravidlá sú odvodené od asociačných, no zavádzajú do hry **ČAS A PORADIE**[cite: 89, 90].

💡 **CHÁPANIE POLOPATISTICKY:**
Pri asociačných pravidlách nahádžeš veci do jedného košíka naraz. [cite_start]Pri sekvenčných pravidlách ťa zaujíma história správania jedného človeka v čase[cite: 95, 101].
* *Asociačné:* Zákazník si kúpil naraz `[Kryt na mobil, Nabíjačku]`.
* *Sekvenčné:* Zákazník si najprv kúpil `[Mobil]`, neskôr si pozrel `[Kryt]` a nakoniec kúpil `[Ochranné sklo]`.

### Hlavné rozdiely v bodoch:

1. [cite_start]**Časová pečiatka:** Sekvenčné dáta vyžadujú identifikátor používateľa a čas, kedy akciu/transakciu vykonal[cite: 94, 95].
2. **Definícia Podpory (Support):**
   * [cite_start]*Pri asociačných* je podpora percento **transakcií** v databáze[cite: 23].
   * [cite_start]*Pri sekvenčných* je podpora percento **používateľov**, ktorí majú vo svojej histórii danú sekvenciu[cite: 99].
3. [cite_start]**Nesúvislosť:** Kroky nemusia nasledovať tesne po sebe, sekvencia môže pozostávať z viacerých transakcií bez nutnosti súvislých prístupov[cite: 98].

### Prečo klasické Apriori zlyháva pri analýze webu (Web Log Mining)?
Ak analyzujeme klikanie ľudí na webe, klasické Apriori nevie, čo bolo skôr a čo neskôr. [cite_start]Nedokáže zachytiť, že používateľ prechádza stránkami dopredu alebo dozadu[cite: 105, 106].

[cite_start]Algoritmus **AprioriAll** preto najskôr zoradí dáta chronologicky podľa používateľov[cite: 101, 102]. [cite_start]Pri hľadaní dvojprvkových kandidátov robí **úplné spájanie**[cite: 105]. [cite_start]To znamená, že generuje a testuje obe možnosti zvlášť (napr. sekvenciu `<A, B>` aj sekvenciu `<B, A>`), pretože na webe ide o dva úplne odlišné scenáre správania[cite: 107, 108].
