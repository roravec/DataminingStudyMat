# 📚 Študijný materiál: Asociačné a sekvenčné pravidlá
*(Pripravené z podkladov ASOCIACNE_PRAVIDLA.pdf a SEKVENCNE_PRAVIDLA.pdf)*

## 1. Asociačné pravidlá (Úvod a základné pojmy)
Asociačné pravidlá patria medzi najpopulárnejšie **symbolické metódy hĺbkovej analýzy dát** (data miningu) a strojového učenia. Sú ideálne pre **kvalitatívne (kategorické) dáta**. 

> 💡 **Poznámka k dátam:** Ak pracujeme s kvantitatívnymi (numerickými) dátami, musíme ich najskôr **diskretizovať** – nahradiť čísla intervalmi, s ktorými sa následne narába ako s kategóriami.

* **Využitie:** Analýza nákupného košíka, finančné dáta, cenzus a pod.
* **Formát pravidla:** Využívajú konštrukciu **IF (podmienka/antecedent) THEN (záver/consequent)**, čo sa dá veľmi ľahko vyjadriť v prirodzenom jazyku (napr. *AK si zákazník kúpi chlieb a syr, POTOM si kúpi aj maslo*).
* **Matematický zápis:** Implikácia $X \Rightarrow Y$, kde $X, Y \subset I$ a zároveň ich prienik je prázdna množina ($X \cap Y = \emptyset$). Množiny položiek (ako $X$ alebo $Y$) sa nazývajú **položkové množiny (itemsets)**.

---

## 2. Kľúčové miery asociačných pravidiel
Pravidlá sa určujú na základe ich početnosti výskytu v dátach pomocou troch základných mier:

| Miera | Význam | Matematický vzorec / Definícia |
| :--- | :--- | :--- |
| **Podpora** *(Support)* | Ako často sa daná množina položiek vyskytuje v databáze (reprezentuje frekvenciu). | $Support(X \Rightarrow Y) = P(X \cup Y)$ |
| **Spoľahlivosť** *(Confidence)* | Sila pravidla. Vyjadruje pravdepodobnosť výskytu pravej strany za podmienky výskytu ľavej strany. | $Confidence(X \Rightarrow Y) = \frac{Support(X \cup Y)}{Support(X)}$ |
| **Zdvih** *(Lift)* | Miera zaujímavosti. Určuje, koľko-krát častejšie sa $X$ a $Y$ vyskytujú spolu, než keby boli štatisticky nezávislé. | $Lift(X \Rightarrow Y) = \frac{Confidence(X \Rightarrow Y)}{Support(Y)}$ |

* Ak je **$Lift > 1$**, indikuje to, že sa položky $X$ a $Y$ vyskytujú častejšie spolu ako zvlášť.
* Cieľom analýzy je nájsť všetky pravidlá, ktoré spĺňajú vopred nastavenú minimálnu podporu (**minimum support**) a minimálnu spoľahlivosť (**minimum confidence**). Množina s podporou $\ge$ min s sa nazýva **frekventovaná** (veľká) množina položiek.

---

## 3. Algoritmus Apriori
Proces získavania pravidiel prebieha v dvoch krokoch: najprv sa nájdu všetky frekventované množiny položiek a z nich sa následne vygenerujú samotné pravidlá.

Algoritmus Apriori funguje na princípe **generovania kombinácií do šírky** (od jednoprvkových $L_1$, cez dvojprvkové $L_2$ atď.) Využíva kľúčovú vlastnosť: **Každá podmnožina frekventovanej množiny musí byť tiež frekventovaná**. Vďaka tomu nemusí prehľadávať všetkých $2^m$ možných podmnožín.

### Tri základné kroky algoritmu:
1. **Spájanie:** Vygenerovanie množiny kandidátov $C_k$ na základe predchádzajúcich frekventovaných množín $L_{k-1}$.
2. **Orezávanie:** Odstránenie kandidátov z $C_k$, ktorých akákoľvek podmnožina sa nenachádza v $L_{k-1}$ (nie je frekventovaná).
3. **Testovanie podpory:** Zaradenie zostávajúcich množín z $C_k$ do $L_k$, pokiaľ spĺňajú stanovenú minimálnu podporu.

> 📉 **Príklad orezávania:** Ak máme kandidáta dĺžky 3, napr. $\{1, 3, 4\}$, a zistíme, že jeho dvojprvková podmnožina $\{3, 4\}$ nebola v predchádzajúcom kroku ($L_2$) vyhodnotená ako frekventovaná, tak celú množinu $\{1, 3, 4\}$ ihneď vyradíme (orežeme) bez toho, aby sme počítali jej podporu.

### Generovanie pravidiel zo získaných množín
Pri pevnej kombinácii položiek $T$ zostáva podpora pravidla nemenná ($Support(T)$). Pri hľadaní pravidiel s vyhovujúcou spoľahlivosťou platí pravidlo:
* Ak pravidlo $X' \Rightarrow T - X'$ (kde $X'$ je prísnejšia nadkombinácia predpokladu $X$) nespĺňa minimálnu spoľahlivosť, **nebude ju spĺňať ani žiadne voľnejšie pravidlo** $X \Rightarrow T - X$.
* *Príklad:* Ak pre množinu $\{1, 2, 4\}$ nespĺňa podmienku pravidlo $\{1, 2\} \Rightarrow \{4\}$, potom ju nemôžu spĺňať ani pravidlá $\{1\} \Rightarrow \{2, 4\}$ alebo $\{2\} \Rightarrow \{1, 4\}$ a algoritmus ich rovno ignoruje.

---

## 4. Sekvenčné pravidlá a algoritmus AprioriAll
Sekvenčné pravidlá sú odvodené od asociačných, no zavádzajú do analýzy **faktor času/poradia**.

### Hlavné rozdiely: Asociačné vs. Sekvenčné pravidlá

| Charakteristika | Asociačné pravidlá (Apriori) | Sekvenčné pravidlá (AprioriAll) |
| :--- | :--- | :--- |
| **Základná jednotka** | Transakcia (napr. jeden nákup v danom čase). | Sekvencia (množina transakcií jedného používateľa usporiadaná v čase). |
| **Výpočet podpory** | Percento **transakcií** v databáze, ktoré obsahujú danú položkovú množinu. | Percento **používateľov**, ktorí majú vo svojej histórii danú sekvenciu. |
| **Nadväznosť prístupov**| Sleduje sa len spoločný výskyt v rámci jednej transakcie. | Nevyžadujú sa súvislé prístupy na stránky, berie sa do úvahy prechod dopredu aj dozadu. |

### Prečo klasické Apriori nestačí na analýzu webu (Web Log Mining)?
Algoritmus **Apriori nie je vhodný** na objavovanie znalostí z webových prístupov, pretože nedokáže zachytiť, že používateľ prechádza stránkami v určitom čase dopredu alebo dozadu. 

Na tento účel slúži **AprioriAll**, ktorý v prvom kroku zoradí transakcie podľa používateľov a časových nálepiek. Následne generuje kandidátov pomocou tzv. **úplného spájania**, čím dokáže zachytiť sekvenčné správanie (napr. sekvencia stránok $\langle A, B \rangle$ je iná ako $\langle B, A \rangle$).
