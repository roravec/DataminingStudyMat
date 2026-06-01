import numpy as np                        # np.log(), np.histogram() – logaritmus a histogramy
import pandas as pd                       # pd.read_csv(), groupby(), shift(), cumsum(), df.to_csv(), ...
from scipy import stats                   # stats.kstest() – KS test; stats.chi2 – Chi-square test

# ============================================================
# TASK 4 – Identifikacia sedeni (Session Identification)
# ============================================================
# Vstup:  wm2020projekt_users.csv  (vystup z Task 3)
# Vystup: wm2020projekt_sessions.csv
# ------------------------------------------------------------
# Kazda metoda prida do DataFrame vlastny stlpec s ID sedenia.
# "Pre kazdu metodu zvlast stlpec." (tasks.txt)
#
# Implementovane metody:
#   STT_MEAN  – prah = priemer stlpca Length
#   STT_Q     – prah = Q3 + 1.5 * IQR (kvartilove rozpatie)
#   SLength   – prah = fixnych 600 sekund (10 minut)
#   RLength   – prah = odvodeny z exponencialneho rozdelenia (p=0.40)
#   hRef      – casove okno (STT_Mean) + zhoda referrer s predoslou URL
#
# Logika zaciatku noveho sedenia (spolocna pre STT_MEAN, STT_Q, SLength, RLength):
#   Novy zaznam sa poklada za zaciatok noveho sedenia, ak PREDOSLY zaznam splna
#   aspon jednu z podmienok:
#     (A) iny UserID ako aktualny riadok (zmena pouzivatela)
#     (B) Length je None/NaN  (medzera > 60 min, koniec session v Task 3)
#     (C) Length >= prah      (medzera presahuje STT prah)
#   cumsum() na boolean stlpci vygeneruje rastuce ID sedenia.
# ============================================================

# ----------------------------------------
# KONFIGURACNE KONSTANTY (ekvivalent #define v C)
# ----------------------------------------

INPUT_FILE  = "wm2020projekt_users.csv"     # vstup: log s UserID, unixtime, Length
OUTPUT_FILE = "wm2020projekt_sessions.csv"  # vystup: log s pridanymi stlpcami sedeni

# Fixna prahova hodnota pre metodu SLength (10 minut = 600 sekund)
# Standard pouzivany napr. Google Analytics
SLENGTH_THRESHOLD = 600   # sekund

# Podiel navigacnych stranok pre metodu RLength
# p = 0.40 = 40% navstev stranok su navigacne (kratke – pouzivatelia rychlo preskocili)
RLENGTH_NAV_PAGE_RATIO = 0.40


# ============================================================
# POMOCNA FUNKCIA: compute_new_session_flags
# ============================================================
def compute_new_session_flags(df, threshold):
    """
    Vrati boolean array kde True = tento riadok je zaciatok noveho sedenia.
    Pouziva sa pre metody STT_MEAN, STT_Q, SLength, RLength – lisi sa len prah.

    Podmienky pre zaciatok noveho sedenia (kontrolujeme PREDOSLY riadok):
      (A) UserID sa zmenil   -> prvy zaznam noveho pouzivatela
      (B) predosla Length je NaN  -> bola dlhsia pauza ako 60 min (z Task 3)
      (C) predosla Length >= threshold  -> medzera presahuje STT prah

    shift(1) posunie hodnoty o 1 NADOL = ziskame hodnotu PREDOSLEHO riadku.
    Ekvivalent C: prev_userid = record[i-1].userid; prev_length = record[i-1].length;
    """

    # Predosle hodnoty (posunutie o 1 riadok nadol)
    prev_userid = df["UserID"].shift(1)    # UserID predosleho zaznamu
    prev_length = df["Length"].shift(1)    # Length predosleho zaznamu

    # Podmienka A: zmena pouzivatela
    # ekvivalent C: prev_userid != current_userid
    cond_new_user = (prev_userid != df["UserID"])

    # Podmienka B: predosla Length je None/NaN (pauza > 60 min z Task 3)
    # isnull() = True ak hodnota je None alebo NaN
    # ekvivalent C: prev_length == NULL
    cond_length_none = prev_length.isnull()

    # Podmienka C: predosla Length prekracuje prah
    # ekvivalent C: prev_length >= threshold
    cond_over_threshold = (prev_length >= threshold)

    # Kombinujeme podmienky OR – staci splnit jednu
    # ekvivalent C: if (cond_A || cond_B || cond_C)
    is_new_session = cond_new_user | cond_length_none | cond_over_threshold

    # Prvy riadok v DataFrame nema predosly zaznam -> vzdy zaciatok noveho sedenia
    is_new_session.iloc[0] = True

    return is_new_session


# ============================================================
# FUNKCIA: add_stt_mean
# ============================================================
def add_stt_mean(df):
    """
    Prida stlpec 'STT_MEAN' – ID sedenia podla priemeru Length.
    Prah = priemer vsetkych platnych (nie NaN) hodnot stlpca Length.
    """
    print("\nMetoda STT_MEAN: prah = priemer Length...")

    # .mean() ignoruje NaN hodnoty automaticky (skipna=True je default)
    # Ekvivalent C: double mean = sum(length) / count_valid(length);
    threshold = df["Length"].mean()
    print("  STT_Mean prah = " + str(round(threshold, 2)) + " sekund")

    # Zaradenie do sedeni
    is_new_session = compute_new_session_flags(df, threshold)

    # cumsum() na boolean stlpci: False=0, True=1 -> kumulativny sucet
    # Vzdy ked je True (novy zaciatok), cislo sedenia sa zvysi o 1
    # Ekvivalent C: session_id = 0; if (new_session) session_id++;
    df["STT_MEAN"] = is_new_session.cumsum()

    n_sessions = df["STT_MEAN"].nunique()
    print("  Pocet identifikovanych sedeni: " + str(n_sessions))

    return df


# ============================================================
# FUNKCIA: add_stt_q
# ============================================================
def add_stt_q(df):
    """
    Prida stlpec 'STT_Q' – ID sedenia podla kvartiloveho odhadu.
    Prah = Q3 + 1.5 * IQR  (standardna metoda detekcie outlierov).
    Q1 = 25. percentil, Q3 = 75. percentil, IQR = Q3 - Q1.
    """
    print("\nMetoda STT_Q: prah = Q3 + 1.5 * IQR...")

    # Vypocet kvartilov z platnych hodnot Length (bez NaN)
    # .quantile(0.25) = dolny kvartil Q1  (25% hodnot je mensich)
    # .quantile(0.75) = horny kvartil Q3  (75% hodnot je mensich)
    q1 = df["Length"].quantile(0.25)
    q3 = df["Length"].quantile(0.75)

    # IQR = Inter-Quartile Range = kvartilove rozpatie
    # Ekvivalent C: double iqr = q3 - q1;
    iqr = q3 - q1

    # STT_Q prah = Q3 + 1.5 * IQR (standardna formula pre outlier detekciu)
    # Hodnoty nad tym sa povazuju za statisticky neobvykle dlhe pauzy
    threshold = q3 + 1.5 * iqr

    print("  Q1 = " + str(round(q1, 2)) + ", Q3 = " + str(round(q3, 2))
          + ", IQR = " + str(round(iqr, 2)))
    print("  STT_Q prah = " + str(round(threshold, 2)) + " sekund")

    is_new_session = compute_new_session_flags(df, threshold)
    df["STT_Q"] = is_new_session.cumsum()

    n_sessions = df["STT_Q"].nunique()
    print("  Pocet identifikovanych sedeni: " + str(n_sessions))

    return df


# ============================================================
# FUNKCIA: add_slength
# ============================================================
def add_slength(df):
    """
    Prida stlpec 'SLength' – ID sedenia s pevnym prahom 600 sekund (10 minut).
    Najjednoduchsia metoda – rovnaky prah pre vsetkych pouzivatelov.
    """
    print("\nMetoda SLength: prah = " + str(SLENGTH_THRESHOLD) + " sekund (fixny)...")

    is_new_session = compute_new_session_flags(df, SLENGTH_THRESHOLD)
    df["SLength"] = is_new_session.cumsum()

    n_sessions = df["SLength"].nunique()
    print("  Pocet identifikovanych sedeni: " + str(n_sessions))

    return df


# ============================================================
# FUNKCIA: test_exponential
# ============================================================
def test_exponential(df):
    """
    Subtask 'Is R_Length exponential':
    Overi ci premenná Length ma exponencialne rozdelenie.
    Pouziva DVA testy:
      1. Kolmogorov-Smirnov test (KS test)
      2. Chi-square test zhody (goodness-of-fit)
    Vrati True ak Length MA exponencialne rozdelenie (oba testy p-value >= 0.05),
             False ak NEMA exponencialne rozdelenie (aspon jeden test p-value < 0.05).
    """
    print("\nSubtask: Overenie exponencialneho rozdelenia premennej Length...")

    # Vyberieme platne (nie NaN) hodnoty Length
    # Ekvivalent C: double *valid = filter_not_null(length, &count);
    valid_lengths = df["Length"].dropna().values

    # Vypocitame zakladnu statistiku
    mean_val  = valid_lengths.mean()
    std_val   = valid_lengths.std()
    # Sikmost exponencialneho rozdelenia by mala byt blizka 2
    # Ekvivalent C: double skewness = compute_skewness(valid_lengths, count);
    skewness  = stats.skew(valid_lengths)

    print("  Pocet platnych hodnot: " + str(len(valid_lengths)))
    print("  Priemer (mean):        " + str(round(mean_val, 4)))
    print("  Std. odchylka:         " + str(round(std_val, 4)))
    print("  Sikmost (skewness):    " + str(round(skewness, 4))
          + "  (exponencialne ~ 2.0)")

    # MLE odhad parametra lambda exponencialneho rozdelenia
    # Pre exp. rozdelenie: E[X] = 1/lambda => lambda = 1/mean
    # stats.expon.fit() vracia (loc, scale) kde scale = 1/lambda
    loc, scale = stats.expon.fit(valid_lengths, floc=0)  # floc=0 fixuje posunutie na 0
    lam = 1.0 / scale
    print("  MLE lambda = " + str(round(lam, 6)) + "  (scale = 1/lambda = " + str(round(scale, 4)) + ")")

    # ----------------------------------------------------------
    # TEST 1: Kolmogorov-Smirnov test
    # H0: data pochadza z exponencialneho rozdelenia
    # Porovnava empiricku CDF s teoretickou CDF exponencialneho rozdelenia
    # Ak p-value < 0.05 -> zamietneme H0 -> data NEMA exp. rozdelenie
    # Ekvivalent C: double p_value = ks_test(valid_lengths, expo_cdf);
    # ----------------------------------------------------------
    print("\n  --- Test 1: Kolmogorov-Smirnov test ---")
    ks_stat, ks_p = stats.kstest(valid_lengths, "expon",
                                 args=(0, scale))   # args=(loc, scale)
    print("  KS statistika: " + str(round(ks_stat, 6)))
    print("  KS p-value:    " + str(round(ks_p, 6)))
    if ks_p >= 0.05:
        print("  KS vysledok:   p >= 0.05 -> nezamietneme H0 (mozno exp. rozdelenie)")
    else:
        print("  KS vysledok:   p < 0.05  -> zamietneme H0 (NIE je exp. rozdelenie)")

    # ----------------------------------------------------------
    # TEST 2: Chi-square test zhody (goodness-of-fit)
    # Rozdelime data do N_BINS tried s ROVNAKOU TEORETICKOU pravdepodobnostou.
    # Pre kazdu triedu porovname pozoruvane (observed) vs ocakavane (expected)
    # pocetnosti. Testova statistika: chi2 = sum((O - E)^2 / E)
    # Stupne volnosti: df = N_BINS - 1 - 1 = N_BINS - 2
    #   (odcitame 1 za odhadnuty parameter lambda)
    # Ak p-value < 0.05 -> zamietneme H0 -> data NEMA exp. rozdelenie
    # Ekvivalent C: double chi2 = chi_square_test(observed, expected, n_bins);
    # ----------------------------------------------------------
    print("\n  --- Test 2: Chi-square test zhody (goodness-of-fit) ---")

    N_BINS = 20   # pocet tried (tried s rovnakou teoretickou pravdepodobnostou)

    # Hranice tried: rovnomerne rozdelene kvantiley exp. rozdelenia
    # np.linspace(0, 1, N_BINS+1) = [0.0, 0.05, 0.10, ..., 1.0]  (N_BINS+1 bodov)
    # stats.expon.ppf() = kvantilova funkcia (inverzna CDF)
    # Posledna hranica = +nekonecno (zachyti vsetky hodnoty nad poslednym kvantilom)
    # Ekvivalent C: double edges[N_BINS+1]; for (i=0; i<N_BINS; i++) edges[i] = expon_quantile(i/N_BINS);
    quantile_points = np.linspace(0.0, 1.0, N_BINS + 1)
    bin_edges = stats.expon.ppf(quantile_points[:-1], loc=0, scale=scale)  # dolne hranice
    bin_edges = np.append(bin_edges, np.inf)   # posledna horná hranica = +inf

    # Pocitame pozoruvane pocetnosti (koľko hodnot padne do kazdej triedy)
    # np.histogram() = ekvivalent C: for (i=0; i<n; i++) counts[bin_of(v[i])]++;
    observed, _ = np.histogram(valid_lengths, bins=bin_edges)

    # Ocakavane pocetnosti – pre rovnako pravdepodobne triedy je kazda E = n/N_BINS
    # Ekvivalent C: double expected = (double)n / N_BINS;
    n_total  = len(valid_lengths)
    expected = np.full(N_BINS, n_total / N_BINS, dtype=float)  # pole rovnakych hodnot

    # Vypocet Chi-square statistiky: chi2 = sum( (O-E)^2 / E )
    # Ekvivalent C: for (i=0; i<N_BINS; i++) chi2 += (obs[i]-exp[i])^2 / exp[i];
    chi2_stat = 0.0
    i = 0
    while i < N_BINS:
        chi2_stat += (observed[i] - expected[i]) ** 2 / expected[i]
        i += 1

    # Stupne volnosti = N_BINS - 1 - 1  (odcitame 1 za odhadnuty parameter lambda)
    # Ekvivalent C: int dof = N_BINS - 2;
    dof = N_BINS - 2

    # p-value z chi-square rozdelenia: 1 - CDF(chi2_stat, dof)
    # Ekvivalent C: double p_value = 1.0 - chi2_cdf(chi2_stat, dof);
    chi2_p = 1.0 - stats.chi2.cdf(chi2_stat, dof)

    print("  Pocet tried (bins):    " + str(N_BINS))
    print("  Chi2 statistika:       " + str(round(chi2_stat, 4)))
    print("  Stupne volnosti (dof): " + str(dof))
    print("  Chi2 p-value:          " + str(round(chi2_p, 6)))
    if chi2_p >= 0.05:
        print("  Chi2 vysledok:  p >= 0.05 -> nezamietneme H0 (mozno exp. rozdelenie)")
    else:
        print("  Chi2 vysledok:  p < 0.05  -> zamietneme H0 (NIE je exp. rozdelenie)")

    # ----------------------------------------------------------
    # Celkove rozhodnutie: MA exponencialne rozdelenie iba ak OBA testy nezvratia H0
    # Ekvivalent C: is_exponential = (ks_p >= 0.05) && (chi2_p >= 0.05);
    # ----------------------------------------------------------
    print()
    is_exponential = (ks_p >= 0.05) and (chi2_p >= 0.05)
    if is_exponential:
        print("  >>> Celkovy vysledok: OBA testy NEZAMIETAJU H0 -> Length MA exponencialne rozdelenie")
    else:
        print("  >>> Celkovy vysledok: Aspon jeden test ZAMIETOL H0 -> Length NEMA exponencialne rozdelenie")
        print("                        => RLength pouzije STT_Q ako fallback prah")

    return is_exponential, lam


# ============================================================
# FUNKCIA: add_rlength
# ============================================================
def add_rlength(df):
    """
    Prida stlpec 'RLength' – ID sedenia odvodeny z exponencialneho rozdelenia.
    Prah C = -ln(1 - p) / lambda, kde:
      lambda = 1 / mean(Length)   (MLE odhad parametra exponencialneho rozdelenia)
      p = RLENGTH_NAV_PAGE_RATIO  (podiel navigacnych stranok = 0.40)

    Ak KS test zamietne exponencialne rozdelenie (p-value < 0.05),
    pouzijeme ako fallback prah STT_Q (= Q3 + 1.5 * IQR).
    """
    print("\nMetoda RLength: prah z exponencialneho rozdelenia (p="
          + str(RLENGTH_NAV_PAGE_RATIO) + ")...")

    # --- Najprv otestujeme ci Length ma exponencialne rozdelenie ---
    is_exponential, lam = test_exponential(df)

    if is_exponential:
        # Length MA exponencialne rozdelenie -> pouzijeme vypocitany prah C
        # Kvantilna funkcia exp. rozdelenia: C = -ln(1 - p) / lambda
        # Ekvivalent C: double C = -log(1.0 - p) / lambda;
        p         = RLENGTH_NAV_PAGE_RATIO
        threshold = -np.log(1.0 - p) / lam
        print("\n  RLength prah C (exponencialny) = " + str(round(threshold, 2)) + " sekund")
    else:
        # Length NEMA exponencialne rozdelenie -> fallback: pouzijeme STT_Q
        # STT_Q = Q3 + 1.5 * IQR
        q1        = df["Length"].quantile(0.25)
        q3        = df["Length"].quantile(0.75)
        iqr       = q3 - q1
        threshold = q3 + 1.5 * iqr
        print("\n  RLength prah (fallback STT_Q) = " + str(round(threshold, 2)) + " sekund")

    is_new_session = compute_new_session_flags(df, threshold)
    df["RLength"] = is_new_session.cumsum()

    n_sessions = df["RLength"].nunique()
    print("  Pocet identifikovanych sedeni: " + str(n_sessions))

    return df


# ============================================================
# POMOCNA FUNKCIA: strip_domain
# ============================================================
def strip_domain(url):
    """
    Odstrani doménu z URL a vrati len cestu.
    Priklad: "https://www.ukf.sk/o-nas" -> "/o-nas"
             "/o-nas"                   -> "/o-nas"  (uz je len cesta)
             "-"                        -> "-"        (chybajuci referrer)
    Ekvivalent C: char* p = strstr(url, "//"); if (p) p = strchr(p+2, '/');
    """
    if not isinstance(url, str):
        return url   # NaN alebo None -> vratime tak ako je

    # Ak URL obsahuje "://" -> je to plna URL s domenou
    # Najdeme prvy znak "/" za "//" (zacatok cesty)
    if "://" in url:
        # Najdeme poziciu "//" a hladame "/" za domenou
        start = url.find("://") + 3            # preskocime "https://"
        slash_pos = url.find("/", start)       # hladame "/" za domenou
        if slash_pos != -1:
            return url[slash_pos:]             # vratime len cestu od "/"
        else:
            return "/"                         # URL bez cesty -> root "/"

    # Uz je to len cesta – vratime bez zmeny
    return url


# ============================================================
# FUNKCIA: add_href
# ============================================================
def add_href(df):
    """
    Prida stlpec 'hRef' – ID sedenia metodu h-ref (Hyperlink Reference).
    Kombinuje dve kriteria pre to iste sedenie:
      (1) Referrer aktualneho zaznamu == URL predosleho zaznamu (navigacny odkaz)
      (2) Casova medzera <= delta (= STT_Mean)
    Nove sedenie vznikne az ked neplatí ani jedna z podmienok,
    alebo ide o prvy zaznam pouzivatela.
    """
    print("\nMetoda hRef: casove okno (STT_Mean) + zhoda referrer s predoslou URL...")

    # Casove okno delta = STT_Mean (priemer Length, rovnaky ako pri STT_MEAN metode)
    delta = df["Length"].mean()
    print("  delta (STT_Mean) = " + str(round(delta, 2)) + " sekund")

    # Vytvorime pomocny stlpec kde je z Referreru odstranena domena
    # strip_domain() aplikujeme na kazdy riadok stlpca Referrer
    # Ekvivalent C: for (i=0; i<n; i++) ref_path[i] = strip_domain(ref[i]);
    df["Referrer_path"] = df["Referrer"].apply(strip_domain)

    # Predosle hodnoty (posunutie o 1 riadok nadol, v ramci toho isteho pouzivatela)
    # groupby("UserID") zabezpeci ze shift nepresahuje hranice pouzivatela
    prev_url      = df.groupby("UserID")["URL"].shift(1)       # predosla URL
    prev_unixtime = df.groupby("UserID")["unixtime"].shift(1)  # predosly cas

    # Podmienka 1: Referrer aktualnej stranky == URL predosleho zaznamu
    # = pouzivatel klikol na odkaz na predoslej stranke (navigacny prechod)
    # Ekvivalent C: strcmp(referrer_path, prev_url) == 0
    cond_ref_match = (df["Referrer_path"] == prev_url)

    # Podmienka 2: casova medzera medzi predoslym a aktualnym zaznamom <= delta
    # Ekvivalent C: (current_time - prev_time) <= delta
    time_diff = df["unixtime"] - prev_unixtime
    cond_time_ok = (time_diff <= delta)

    # Zaznam patri do TOHO ISTEHO sedenia ak plati aspon jedna podmienka
    # => novy zaciatok sedenia = ked NEPLATÍ ani jedna podmienka
    # Ekvivalent C: new_session = !(cond1 || cond2)  = (!cond1 && !cond2)
    same_session = cond_ref_match | cond_time_ok
    is_new_session = ~same_session

    # Prvy zaznam kazdeho pouzivatela je vzdy zaciatok noveho sedenia
    # groupby + shift(1) -> NaN na prvom riadku kazdeho pouzivatela -> is_new = True
    is_new_session = is_new_session | prev_url.isnull()

    # Prvy riadok celeho DataFrame
    is_new_session.iloc[0] = True

    # cumsum() generuje ID sedenia
    df["hRef"] = is_new_session.cumsum()

    # Odstranime pomocny stlpec Referrer_path
    df.drop(columns=["Referrer_path"], inplace=True)

    n_sessions = df["hRef"].nunique()
    print("  Pocet identifikovanych sedeni: " + str(n_sessions))

    return df


# ============================================================
# HLAVNA FUNKCIA – ekvivalent int main() v C
# ============================================================
def main():
    # --- Nacitanie CSV z Task 3 ---
    print("Nacitavam: " + INPUT_FILE + " ...")
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    print("  Nacitanych zaznamov: " + str(len(df)))
    print("  Stlpce: " + str(list(df.columns)))

    # Zoradime podla UserID a unixtime – vyzaduju to vsetky metody
    print("\nZoradujem podla UserID a unixtime...")
    df = df.sort_values(by=["UserID", "unixtime"])
    df = df.reset_index(drop=True)

    # --- Metoda 1: STT_MEAN ---
    df = add_stt_mean(df)

    # --- Metoda 2: STT_Q ---
    df = add_stt_q(df)

    # --- Metoda 3: SLength (fixny prah 600 s) ---
    df = add_slength(df)

    # --- Metoda 4: RLength (exponencialne rozdelenie) ---
    df = add_rlength(df)

    # --- Metoda 5: hRef (casove okno + referrer zhoda) ---
    df = add_href(df)

    # --- Zhrnutie ---
    print("\nVysledny DataFrame:")
    print("  Zaznamov: " + str(len(df)))
    print("  Stlpce:   " + str(list(df.columns)))

    # Porovnanie poctu sedeni podla metod
    print("\nPorovnanie poctu sedeni:")
    for col in ["STT_MEAN", "STT_Q", "SLength", "RLength", "hRef"]:
        print("  " + col + ": " + str(df[col].nunique()) + " sedeni")

    # --- Ulozenie vysledku ---
    print("\nUkladam do: " + OUTPUT_FILE + " ...")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print("Hotovo! Subor ulozeny: " + OUTPUT_FILE)


# Spustenie iba pri priamom spusteni (python task4_sessions.py)
# ekvivalent C: int main() { ... }
if __name__ == "__main__":
    main()
