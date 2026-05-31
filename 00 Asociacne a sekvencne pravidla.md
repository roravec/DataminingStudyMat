# 📚 Študijný materiál: Asociačné a sekvenčné pravidlá
*(Pripravené z podkladov ASOCIACNE_PRAVIDLA.pdf a SEKVENCNE_PRAVIDLA.pdf s vysvetlivkami)*

---

## 1. Asociačné pravidlá (Úvod a základné pojmy)
Asociačné pravidlá patria medzi najpopulárnejšie **symbolické metódy hĺbkovej analýzy dát** (data miningu) a strojového učenia. Sú ideálne pre **kvalitatívne (kategorické) dáta**.

💡 **CHÁPANIE POLOPATISTICKY:** Predstav si databázu nákupov v supermarkete. Cieľom asociačných pravidiel je zistiť, ktoré tovary ľudia kupujú *spolu*. Nehľadáme príčinu (že chlieb spôsobuje kúpu masla), ale čistú štatistickú súvislosť (asociáciu).

* **Využitie:** Analýza nákupného košíka, finančné dáta, cenzus a pod.
* **Úprava dát:** Ak máme čísla (kvantitatívne dáta), musíme ich najskôr **diskretizovať** – rozdeliť do intervalov (napr. vek 0-18, 19-30), aby sme s nimi vedeli pracovať ako s kategóriami.
* **Formát pravidla:** Používa sa konštrukcia **IF (podmienka / antecedent) THEN (záver / consequent)**.
  * **Príklad z praxe:** `{chlieb, syr} => {maslo}`
  * **Interpretácia:** Ak si zákazník kúpi chlieb a syr, s 57% pravdepodobnosťou kúpi aj maslo.
* **Matematický zápis:** Implikácia `X => Y`, pričom predpoklad `X` a záver `Y` sú podmnožiny všetkých položiek a ich prienik je prázdny. Množiny položiek sa nazývajú **položkové množiny (itemsets)**.

---

## 2. Tri kľúčové miery (Čo tie čísla znamenajú?)
Pravidlá sa nehľadajú náhodne, musíme ich zmerať pomocou troch veličín:

| Miera | Definícia | 💡 Čo to hovorí v praxi? |
| :--- | :--- | :--- |
| **Podpora** *(Support)* | `Support(X => Y) = P(X U Y)` | **Ako často sa to stáva?** Hovorí nám, aké percento zo *všetkých* nákupov v databáze obsahuje celú kombináciu X aj Y spolu. Ak je podpora nízka, pravidlo sa týka málokoho. |
| **Spoľahlivosť** *(Confidence)* | `Confidence(X => Y) = Support(X U Y) / Support(X)` | **Aké silné je to pravidlo?** Predstav si len ľudí, ktorí už majú v košíku X. Koľko percent z nich si k tomu prihodí aj Y? Vyjadruje to percentuálny podiel pravidiel zo všetkých, ktoré obsahujú X. |
| **Zdvih** *(Lift)* | `Lift(X => Y) = Confidence(X => Y) / Support(Y)` | **Je to užitočné, alebo je to len náhoda?** Určuje, koľko-krát častejšie sa kupujú spolu, než keby nakupovali úplne nezávisle. <br>• **Lift > 1:** Kupujú sa spolu častejšie ako zvlášť, je tam väzba. |

* Analytik si na začiatku nastaví **minimum support** a **minimum confidence**.
* Množina, ktorá prejde cez filter minimálnej podpory, sa nazýva **frekventovaná položková množina**.

---

## 3. Algoritmus Apriori (Ako nájsť pravidlá bez toho, aby počítač zhorel?)
Keby sme mali v obchode veľa položiek, kombinácií všetkých tovarov by bolo obrovské množstvo. Algoritmus Apriori prináša trik, ako tento priestor osekať.

💡 **HLAVNÁ MYŠLIENKA (Apriori vlastnosť):**
Každá podmnožina frekventovanej množiny musí byť tiež frekventovaná. Ak nejakú podkombináciu ľudia nekupujú, nebudú kupovať ani jej väčšiu verziu.
* **Príklad:** Ak ľudia nekupujú dvojicu položiek `{3, 4}`, je zbytočné testovať trojicu `{1, 3, 4}`. Automaticky ju môžeme zahodiť.

### Proces prebieha v dvoch fázach:
1. **Fáza: Nájdenie frekventovaných množín do šírky** (od 1-prvkových po k-prvkové):
   * **Spájanie:** Vezmeme úspešné položky z minulého kroku a pospájame ich do väčších kandidátov.
   * **Orezávanie (Pruning):** Ak zistíme, že nejaká podkombinácia nového kandidáta minule neuspela, kandidáta rovno vymažeme.
   * **Test podpory:** Pre die kombinácie, ktoré prežili orezanie, overíme reálny výskyt v databázi a úspešné si odložíme.
2. **Fáza: Generovanie pravidiel zo získaných množín**:
   * Vezmeme vygenerovanú frekventovanú množinu a rozdelíme ju na podmienku X a následok Y.
   * Trik so spoľahlivosťou: Ak nespĺňa podmienku spoľahlivosti pravidlo s úzkou podmienkou (napr. `{1, 2} => {4}`), potom ju nebudú spĺňať ani ešte voľnejšie pravidlá (napr. `{1} => {2, 4}`) a netreba ich vôbec počítať.

---

## 4. Sekvenčné pravidlá a algoritmus AprioriAll
Sekvenčné pravidlá sú odvodené od asociačných, no zavádzajú do hry **ČAS A PORADIE**.

💡 **CHÁPANIE POLOPATISTICKY:**
Pri asociačných pravidlách nahádžeš veci do jedného košíka naraz. Pri sekvenčných pravidlách ťa zaujíma história správania jedného človeka v čase.
* **Asociačné:** Zákazník si kúpil naraz `[Kryt na mobil, Nabíjačku]`.
* **Sekvenčné:** Zákazník si najprv kúpil `[Mobil]`, neskôr si pozrel `[Kryt]` a nakoniec kúpil `[Ochranné sklo]`.

### Hlavné rozdiely v bodoch:

1. **Časová pečiatka:** Sekvenčné dáta vyžadujú identifikátor používateľa a čas, kedy akciu/transakciu vykonal.
2. **Definícia Podpory (Support):**
   * **Pri asociačných:** podpora je percento **transakcií** v databáze.
   * **Pri sekvenčných:** podpora je percento **používateľov**, ktorí majú vo svojej histórii danú sekvenciu.
3. **Nesúvislosť:** Kroky nemusia nasledovať tesne po sebe, sekvencia môže pozostávať z viacerých transakcií bez nutnosti súvislých prístupov.

### Prečo klasické Apriori zlyháva pri analýze webu (Web Log Mining)?
Ak analyzujeme klikanie ľudí na webe, klasické Apriori nevie, čo bolo skôr a čo neskôr. Nedokáže zachytiť, že používateľ prechádza stránkami dopredu alebo dozadu.

Algoritmus **AprioriAll** preto najskôr zoradí dáta chronologicky podľa používateľov. Pri hľadaní dvojprvkových kandidátov robí **úplné spájanie**. To znamená, že generuje a testuje obe možnosti zvlášť (napr. sekvenciu `<A, B>` aj sekvenciu `<B, A>`), pretože na webe ide o dva úplne odlišné scénáre správania.
