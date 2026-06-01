import pandas as pd  # pd.read_csv(), pd.to_datetime(), pd.factorize(), df.to_csv(), ...

# ============================================================
# TASK 3 – Identifikacia pouzivatelov (User Identification)
# ============================================================
# Vstup:  wm2020projekt_no_robots.csv  (vystup z Task 2)
# Vystup: wm2020projekt_users.csv
# ------------------------------------------------------------
# Postup (podla tasks.txt + tasks_additional_info.txt):
#
# Krok 1: UNIXTIME
#         Vytvorime novu premennu unixtime z pola DateTime.
#         DateTime ma format Apache logu: "12/Nov/2017:06:27:01 +0100"
#         Konvertujeme na pocet sekund od 1.1.1970 00:00:00 UTC.
#
# Krok 2: User_ID
#         Identifikujeme pouzivatelov na zaklade kombinacie IP + Agent.
#         Kazda unikatna kombinacia IP + Agent = jeden pouzivatel.
#         pd.factorize() priradi kazdej kombinacii unikatne cislo.
#         Pred priradenim ID zoradime zaznamy podla IP, Agent, unixtime.
#
# Krok 3: Length
#         Cas straveny na stranke v sekundach pre kazdy zaznam.
#         = rozdiel unixtime medzi aktualnym zaznamom a NASLEDUJUCIM zaznamom
#           toho isteho pouzivatela.
#         Podmienka: ak je rozdiel < 3600 sekund (60 minut) => zapiseme rozdiel
#                    inak (dlha pauza alebo posledny zaznam pouzivatela) => None
# ============================================================

# ----------------------------------------
# KONFIGURACNE KONSTANTY (ekvivalent #define v C)
# ----------------------------------------

INPUT_FILE  = "wm2020projekt_no_robots.csv"  # vstup: log bez robotov z Task 2
OUTPUT_FILE = "wm2020projekt_users.csv"       # vystup: log s UserID, unixtime, Length

# Format datumu v stlpci DateTime (Apache Combined Log Format)
# Priklad hodnoty: "12/Nov/2017:06:27:01 +0100"
# %d = den (12), %b = mesiac skratka (Nov), %Y = rok (2017)
# %H:%M:%S = hodiny:minuty:sekundy,  %z = casova zona (+0100)
DATETIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"

# Separator medzi IP a Agent pri vytvarani kluca pre pd.factorize()
# Pouzijeme "|" – znak ktory sa v IP ani Agent normalne nevyskytuje
USER_KEY_SEPARATOR = "|"

# Maximalna dlzka sedenia v sekundach (60 minut = 3600 sekund)
# Ak je rozdiel medzi dvoma po sebe idúcimi zaznammi pouzivatela
# vacsi alebo rovny tomuto prahu, zapiseme None (novu session / odchod)
MAX_SESSION_GAP = 3600   # sekund = 60 minut


# ============================================================
# FUNKCIA: add_unixtime
# ============================================================
def add_unixtime(df):
    """
    Prida stlpec 'unixtime' do DataFrame.
    Konvertuje textovy DateTime (Apache format) na cele cislo – pocet sekund
    od 1. januara 1970 00:00:00 UTC.
    """
    print("\nKrok 1: Vytvaranie stlpca unixtime z DateTime...")

    # pd.to_datetime() parsuje retazec datumu na datetime objekt
    # format=DATETIME_FORMAT – explicitny format je rychlejsi ako automaticke hadanie
    # Ekvivalent C: struct tm t; strptime(str, "%d/%b/%Y:%H:%M:%S %z", &t);
    datetime_parsed = pd.to_datetime(df["DateTime"], format=DATETIME_FORMAT)

    # Konvertujeme na sekundy od 1.1.1970 UTC (unixtime)
    # POZNAMKA: pandas 2.0+ uklada timezone-aware datetime v MIKROSEKUNDACH (nie nanosekundach)
    #           preto NEpouzivame .astype('int64') // 10**9  (dalo by zly vysledok)
    # Spravne riesenie: odpocitame epoch a zavolame .dt.total_seconds()
    #   total_seconds() vracia vzdy float SEKUND, bez ohladu na interne rozlisenie
    # Ekvivalent C: time_t unix = difftime(t, epoch);
    epoch = pd.Timestamp("1970-01-01", tz="UTC")   # zaciatocny bod unix casu
    df["unixtime"] = (datetime_parsed - epoch).dt.total_seconds().astype("int64")

    print("  unixtime – prvy zaznam:      " + str(df["unixtime"].iloc[0]))
    print("  unixtime – posledny zaznam:  " + str(df["unixtime"].iloc[-1]))

    return df


# ============================================================
# FUNKCIA: add_user_id
# ============================================================
def add_user_id(df):
    """
    Zoradí DataFrame a pridá stlpec 'UserID'.
    Kazda unikatna kombinacia IP + Agent dostane vlastne cislo (0, 1, 2, ...).
    Zoradenie: IP -> Agent -> unixtime (chronologicky v ramci pouzivatela).
    """
    print("\nKrok 2: Identifikacia pouzivatelov (UserID = IP + Agent)...")

    # Zoradime zaznamy: prvy krit. IP, druhy krit. Agent, treti krit. unixtime
    # Zabezpecime ze zaznamy toho isteho pouzivatela su za sebou chronologicky
    # Ekvivalent C: qsort(records, n, sizeof(Record), compare_ip_agent_time);
    df = df.sort_values(by=["IP", "Agent", "unixtime"])

    # Resetujeme index po zoradeni – riadky sa znovu ocislia od 0
    df = df.reset_index(drop=True)

    # Spojime IP a Agent do jedneho retazca oddelenych separatorom
    # Priklad: "192.168.1.1|Mozilla/5.0 (Windows...)"
    # Ekvivalent C: sprintf(key, "%s|%s", ip, agent);
    user_key = df["IP"] + USER_KEY_SEPARATOR + df["Agent"]

    # pd.factorize() priradi kazdej unikatnej hodnote v user_key unikatne cislo
    # Vrati: (pole_cisel, pole_unikatnych_hodnot)
    # Ekvivalent C: hash_map kde kluc = user_key, hodnota = priradene ID
    user_ids, unique_keys = pd.factorize(user_key)

    # Ulozime ID do noveho stlpca UserID
    df["UserID"] = user_ids

    print("  Celkovy pocet unikatnych pouzivatelov: " + str(len(unique_keys)))
    print("  UserID od 0 do " + str(df["UserID"].max()))

    return df


# ============================================================
# FUNKCIA: add_length
# ============================================================
def add_length(df):
    """
    Prida stlpec 'Length' – cas straveny na stranke v sekundach.
    Pre kazdy zaznam = rozdiel unixtime medzi aktualnym a NASLEDUJUCIM
    zaznamom toho isteho pouzivatela.
    Ak je rozdiel >= MAX_SESSION_GAP alebo ide o posledny zaznam => None.
    """
    print("\nKrok 3: Vytvaranie stlpca Length (cas straveny na stranke)...")

    # Zoradime podla UserID a unixtime (chronologicky v ramci pouzivatela)
    # Ekvivalent C: qsort(records, n, sizeof(Record), compare_userid_time);
    df = df.sort_values(by=["UserID", "unixtime"])
    df = df.reset_index(drop=True)

    # groupby("UserID") rozdeluje DataFrame na skupiny podla pouzivatela
    # shift(-1) posunie hodnoty o 1 NAHOR = ziskame hodnotu NASLEDUJUCEHO riadku
    # Vysledok: pre kazdy riadok unixtime nasledujuceho zaznamu TOHO ISTEHO usera
    # Ekvivalent C: next_time = (i+1 < n && record[i+1].uid == record[i].uid)
    #                           ? record[i+1].unixtime : NaN;
    next_unixtime = df.groupby("UserID")["unixtime"].shift(-1)
    next_userid   = df.groupby("UserID")["UserID"].shift(-1)

    # Vypocitame rozdiel medzi aktualnym a nasledujucim unixtime
    # Ekvivalent C: int diff = next_time - current_time;
    diff = next_unixtime - df["unixtime"]

    # Podmienka pre zapísanie rozdielu (nie None):
    #   1. Nasledujuci zaznam patri TOMU ISTEMU pouzivatelu (next_userid == UserID)
    #   2. Rozdiel je MENSI ako MAX_SESSION_GAP (< 3600 sekund)
    # Ekvivalent C: if (same_user && diff < MAX_SESSION_GAP)
    condition = (next_userid == df["UserID"]) & (diff < MAX_SESSION_GAP)

    # where(condition, other=None):
    #   Tam kde je condition True  -> zapise diff (skutocny cas)
    #   Tam kde je condition False -> zapise None (koniec session / posledny zaznam)
    # Ekvivalent C: length[i] = condition ? diff : NULL;
    df["Length"] = diff.where(condition, other=None)

    # Statistika – kolko zaznamov ma platnu hodnotu Length (nie None)
    valid_count = df["Length"].notna().sum()
    total_count = len(df)
    print("  Zaznamov s platnou Length:  " + str(valid_count))
    print("  Zaznamov s None (koniec):   " + str(total_count - valid_count))
    print("  Priemerna Length (sekund):  " + str(round(df["Length"].mean(), 1)))

    return df


# ============================================================
# HLAVNA FUNKCIA – ekvivalent int main() v C
# ============================================================
def main():
    # --- Nacitanie CSV z Task 2 ---
    print("Nacitavam: " + INPUT_FILE + " ...")
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    print("  Nacitanych zaznamov: " + str(len(df)))
    print("  Stlpce: " + str(list(df.columns)))

    # --- Krok 1: UNIXTIME ---
    df = add_unixtime(df)

    # --- Krok 2: UserID ---
    df = add_user_id(df)

    # --- Krok 3: Length ---
    df = add_length(df)

    # --- Zhrnutie ---
    print("\nVysledny DataFrame:")
    print("  Zaznamov: " + str(len(df)))
    print("  Stlpce:   " + str(list(df.columns)))

    # --- Ulozenie vysledku ---
    print("\nUkladam do: " + OUTPUT_FILE + " ...")
    # index=False = nechceme automaticky cislovany index v CSV
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print("Hotovo! Subor ulozeny: " + OUTPUT_FILE)


# Spustenie iba pri priamom spusteni (python task3_users.py)
# ekvivalent C: int main() { ... }
if __name__ == "__main__":
    main()
