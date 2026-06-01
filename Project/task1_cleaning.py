import re          # regularne vyrazy – re.compile(), re.match()
import pandas as pd  # dataframe – pd.DataFrame(), df.drop(), df.to_csv(), ...

# ============================================================
# TASK 1 – Cistenie dat (Data Cleaning)
# ============================================================
# Vstup:  wm2020projekt_oravec.log  (Apache Combined Log Format)
#         – vystup z Task 0 (filtrovanie casoveho obdobia 12.11. – 18.11.2017)
# Vystup: wm2020projekt_cleaned.csv
# ------------------------------------------------------------
# Cistenie dat I  (podla tasks_additional_info.txt):
#   1. Parseujeme Apache log do strukturovanych stlpcov:
#      IP, Cookie, user, DateTime, RequestMethod, URL,
#      RequestVersion, StatusCode, Bytes, Referrer, Agent
#   2. Vymazeme nepotrebne stlpce: Cookie, user, Bytes
#   3. Filtrujeme StatusCode – ponechame iba 200, 206, 304
#   4. Filtrujeme RequestMethod – ponechame iba GET (mazeme POST a HEAD)
#   5. Vymazeme URL so statickymi priponami suborov
#      (obrazky, CSS, JS, fonty, ...)
# Cistenie dat II (podla tasks_additional_info.txt):
#   6. Vymazeme URL /navbar/navbar-ukf.html
#      (interni monitoring sablony webu, nie kliknutie pouzivatela)
# ============================================================

# ----------------------------------------
# KONFIGURACNE KONSTANTY (ekvivalent #define v C)
# ----------------------------------------

INPUT_FILE  = "wm2020projekt_oravec.log"   # vstupny log (vystup z task 0)
OUTPUT_FILE = "wm2020projekt_cleaned.csv"  # vystupny ocisteny CSV subor

# Stavove kody HTTP ktore PONECHAME v logu:
#   200 = OK           – uspesna odpoved so obsahom
#   206 = Partial Content – castocny obsah (napr. video streaming)
#   304 = Not Modified  – obsah sa nezmenil, prehliadac pouzil cache
# Vsetky ostatne (1xx, 4xx, 5xx) su informacne/chybove – vymazeme ich
KEEP_STATUS_CODES = [200, 206, 304]

# HTTP metody ktore PONECHAME:
#   GET  – standardny poziadavok na stranku
# POST a HEAD vymazeme (podla tasks.txt: "Vymazat riadky s tymto: POST, HEAD")
KEEP_METHODS = ["GET"]

# Regex vzor pre pripony statickych suborov v URL
# Staticky subor = nema obsah pre analyzu – je to iba obrazok, styl, skript, font
# case=False v str.contains() zarucuje case-insensitive matching (JPG aj jpg)
# Pouzivame NON-CAPTURING skupiny (?:...) namiesto (...)
# – pandas by inak zobrazoval UserWarning o zachytavacich skupinach
STATIC_FILE_PATTERN = (
    r'\.(?:bmp|jpe?g|png|gif|css|flv|ico|swf|rss|xml|cur|js|json|svg'
    r'|woff2?|eot|ttf|otf)(?:\?.*)?$'
)

# URL interneho monitoringu UKF sablony – nie je to realna akcia pouzivatela
# (opakuje sa tisickrat v logu)
NAVBAR_URL = "/navbar/navbar-ukf.html"

# Apache Combined Log Format – regex pre jeden riadok logu
# Priklad riadku:
#   5.9.83.211 - - [12/Nov/2017:06:27:01 +0100] "GET /path HTTP/1.1" 200 187383 "-" "Mozilla/5.0..."
#
# Skupiny zachytene regexom (v poradi zachytenia):
#   1  IP adresa        napr. "5.9.83.211"
#   2  Cookie / ident   vzdy "-"  (RFC 1413 identita, nepouziva sa)
#   3  user   / auth    vzdy "-"  (autentifikovany pouzivatel, nepouziva sa)
#   4  DateTime         napr. "12/Nov/2017:06:27:01 +0100"  (bez zavorky)
#   5  RequestMethod    napr. "GET", "POST", "HEAD"
#   6  URL              napr. "/path/to/page?id=1"
#   7  RequestVersion   napr. "HTTP/1.1"
#   8  StatusCode       napr. "200"  (3 cislice)
#   9  Bytes            napr. "187383" alebo "-"
#  10  Referrer         napr. "http://example.com" alebo "-"
#  11  Agent            napr. "Mozilla/5.0 ..."
LOG_LINE_REGEX = re.compile(
    r'(\S+)'            # skupina  1: IP adresa
    r' (\S+)'           # skupina  2: Cookie / ident
    r' (\S+)'           # skupina  3: user / auth
    r' \[([^\]]+)\]'    # skupina  4: DateTime (obsah [] bez zavoriek)
    r' "(\S+)'          # skupina  5: RequestMethod
    r' (\S+)'           # skupina  6: URL
    r' ([^"]+)"'        # skupina  7: RequestVersion (napr. "HTTP/1.1")
    r' (\d{3})'         # skupina  8: StatusCode (presne 3 cislice)
    r' (\S+)'           # skupina  9: Bytes (cislo alebo -)
    r' "([^"]*)"'       # skupina 10: Referrer
    r' "([^"]*)"'       # skupina 11: Agent (User-Agent retazec)
)


# ============================================================
# FUNKCIA: parse_log_to_dataframe
# Ekvivalent C: struct Record* parse_log(FILE *f, int *count);
# ============================================================
def parse_log_to_dataframe(input_path):
    """
    Cita Apache Combined Log subor riadok po riadku.
    Z kazdeho riadku extrahuje polia pomocou regexu LOG_LINE_REGEX.
    Vrati pandas DataFrame so stlpcami:
      IP, Cookie, user, DateTime, RequestMethod, URL,
      RequestVersion, StatusCode, Bytes, Referrer, Agent
    """

    # Zoznam zaznamov (ekvivalent dynamickeho pola struktur v C)
    # records = malloc(N * sizeof(struct Record));
    records = []

    total   = 0   # celkovy pocet riadkov precitanych zo suboru
    matched = 0   # pocet uspesne parsovanych riadkov

    print("Parsovanie logu: " + input_path + " ...")

    # Otvorime subor na citanie
    # errors="replace" – neplatne UTF-8 bajty nahradi '?' namiesto chyby
    # ekvivalent C: FILE *f = fopen(input_path, "r");
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:

        # Citame jeden riadok naraz (ekvivalent C: while (fgets(buf, ..., f) != NULL))
        for line in f:
            total += 1

            # Progress vypis kazdych 100 000 riadkov
            if total % 100_000 == 0:
                print("  ... " + str(total) + " riadkov spracovanych, "
                      + str(matched) + " matchovanych")

            # Skusime matchnut riadok na Apache log format
            # .match() kontroluje od ZACIATKU riadku (rychlejsie ako .search())
            # ekvivalent C: if (regex_exec(&re, line) == 0)
            m = LOG_LINE_REGEX.match(line.strip())

            if m is None:
                # Riadok nema ocakavany format (prazdny riadok, komentar, ...)
                # Preskakujeme ho – ekvivalent C: continue;
                continue

            matched += 1

            # Ulozime parsovane hodnoty ako slovnik (ekvivalent C struct)
            # int(m.group(8)) = pretypovanie retazca na cele cislo (ako atoi() v C)
            record = {
                "IP":             m.group(1),
                "Cookie":         m.group(2),
                "user":           m.group(3),
                "DateTime":       m.group(4),
                "RequestMethod":  m.group(5),
                "URL":            m.group(6),
                "RequestVersion": m.group(7),
                "StatusCode":     int(m.group(8)),
                "Bytes":          m.group(9),
                "Referrer":       m.group(10),
                "Agent":          m.group(11),
            }

            # Pridame zaznam do zoznamu (ekvivalent C: records[matched] = record;)
            records.append(record)

    print("  Celkovo riadkov: " + str(total) + ", uspesne parsovanych: " + str(matched))

    # Vytvorime DataFrame zo zoznamu slovnikov
    # (ekvivalent: naplnime tabulku zo strukturovaneho pola)
    df = pd.DataFrame(records)

    return df


# ============================================================
# FUNKCIA: clean_data
# Ekvivalent C: struct Record* clean_data(struct Record *df, int *count);
# ============================================================
def clean_data(df):
    """
    Vykona cistenie DataFrame v 6 krokoch:
      Krok 1: Vymazanie stlpcov Cookie, user, Bytes
      Krok 2: Filtrovanie podla StatusCode (200, 206, 304)
      Krok 3: Filtrovanie podla RequestMethod (GET, POST)
      Krok 4: Vymazanie URL so statickymi priponami suborov
      Krok 5: Vymazanie URL /navbar/navbar-ukf.html
      Krok 6: Kontrola rozlozenia hodnot po cisteni
    """

    # ----------------------------------------------------------
    # KROK 1: Vymazanie nepotrebnych stlpcov
    # ----------------------------------------------------------
    # Cookie a user su vzdy "-" (nepouzivaju sa v Apache logu na tomto serveri)
    # Bytes je velkost odpovede v bajtoch – pre analyzu chovania nepotrebne
    print("\nKrok 1: Mazem stlpce Cookie, user, Bytes...")

    # df.drop() zmaze stlpce podla nazvov
    # axis=1 = stlpce (axis=0 by boli riadky)
    # inplace=True = menime df priamo (nechceme vytvorit novu kopiu)
    df.drop(columns=["Cookie", "user", "Bytes"], inplace=True)

    print("  Zostatok riadkov: " + str(len(df)))
    print("  Stlpce:           " + str(list(df.columns)))

    # ----------------------------------------------------------
    # KROK 2: Filtrovanie podla StatusCode
    # ----------------------------------------------------------
    # Ponechame iba uspesne requesty: 200, 206, 304
    # Vymazeme: 1xx (informacne), 4xx (chyby klienta), 5xx (chyby servera)
    print("\nKrok 2: Filtrujem StatusCode (ponechavam: " + str(KEEP_STATUS_CODES) + ")...")

    before = len(df)   # pocet riadkov pred filtrovanim (pre vypocet poctu vymazanych)

    # df['StatusCode'].isin([200, 206, 304]) vrati boolean stlpec:
    #   True  na riadku kde StatusCode je 200 alebo 206 alebo 304
    #   False na vsetkych ostatnych riadkoch
    # df[...] vyberie iba riadky kde je True (ekvivalent C: if (code == 200 || ...))
    df = df[df["StatusCode"].isin(KEEP_STATUS_CODES)]

    # reset_index() znovu ocisluje riadky od 0 po filtrovani
    # drop=True = stary index vyhodime, nechceme ho ako stlpec
    df = df.reset_index(drop=True)

    after = len(df)
    print("  Vymazanych: " + str(before - after) + ", zostatok: " + str(after))

    # ----------------------------------------------------------
    # KROK 3: Filtrovanie podla RequestMethod
    # ----------------------------------------------------------
    # Ponechame GET a POST, vymazeme HEAD a ostatne metody
    print("\nKrok 3: Filtrujem RequestMethod (ponechavam: " + str(KEEP_METHODS) + ")...")

    before = len(df)

    # Rovnaka logika ako Krok 2 – isin() kontroluje prislusnost k zoznamu
    df = df[df["RequestMethod"].isin(KEEP_METHODS)]
    df = df.reset_index(drop=True)

    after = len(df)
    print("  Vymazanych: " + str(before - after) + ", zostatok: " + str(after))

    # ----------------------------------------------------------
    # KROK 4: Vymazanie URL so statickymi priponami suborov
    # ----------------------------------------------------------
    # Obrazky, CSS, JS, fonty = prostriedky stranky, nie obsah
    # Pre analyzu chovania pouzivatela su tieto URL nepodstatne
    print("\nKrok 4: Mazem URL so statickymi priponami (.jpg, .png, .css, .js, ...)...")

    before = len(df)

    # str.contains() aplikuje regex na kazdy riadok v stlpci URL
    # case=False = case-insensitive (zachyti aj .JPG, .PNG, ...)
    # na=False   = prazdne hodnoty (NaN) sa povazuju za False (nie za staticke)
    # regex=True = pouzijeme regularny vyraz (nie jednoduchy text)
    mask_static = df["URL"].str.contains(STATIC_FILE_PATTERN, case=False, regex=True, na=False)

    # Ponechame iba riadky kde URL NEOBSAHUJE staticku priponu
    # mask_static == False  je to iste ako  !mask_static  v C
    mask_keep = (mask_static == False)
    # df.loc[mask_keep] = vyber riadky kde mask_keep[i] == True
    # ekvivalent C:  for(i=0;i<n;i++) if(mask_keep[i]) new_df[j++]=df[i];
    df = df.loc[mask_keep]
    df = df.reset_index(drop=True)

    after = len(df)
    print("  Vymazanych: " + str(before - after) + ", zostatok: " + str(after))

    # ----------------------------------------------------------
    # KROK 5: Vymazanie URL /navbar/navbar-ukf.html  (Cistenie dat II)
    # ----------------------------------------------------------
    # Tato URL sa v logu opakuje tisickrat
    # Je to interni monitoring sablony webu UKF – nie je to kliknutie pouzivatela
    print("\nKrok 5: Mazem URL '" + NAVBAR_URL + "' (interni monitoring)...")

    before = len(df)

    # regex=False = jednoduchy textovy match (rychlejsi ako regex pre pevny retazec)
    mask_navbar = df["URL"].str.contains(NAVBAR_URL, regex=False, na=False)

    # mask_navbar == False  znamena: URL NEOBSAHUJE navbar -> ponechame
    mask_keep = (mask_navbar == False)
    # df.loc[mask_keep] = vyber riadky kde mask_keep[i] == True
    # ekvivalent C:  for(i=0;i<n;i++) if(mask_keep[i]) new_df[j++]=df[i];
    df = df.loc[mask_keep]
    df = df.reset_index(drop=True)

    after = len(df)
    print("  Vymazanych: " + str(before - after) + ", zostatok: " + str(after))

    # ----------------------------------------------------------
    # KROK 6: Kontrolna statistika (value_counts)  (Cistenie dat II)
    # ----------------------------------------------------------
    # Skontrolujeme rozlozenie hodnot po cisteni – overime konzistentnost
    print("\nKrok 6: Kontrolna statistika po cisteni:")

    print("\n  Rozlozenie RequestMethod:")
    # value_counts() spocita vyskyt kazde unikatnej hodnoty v stlpci
    # ekvivalent C: for (i=0; i < n; i++) count[method[i]]++;
    print(df["RequestMethod"].value_counts().to_string())

    print("\n  Rozlozenie StatusCode:")
    print(df["StatusCode"].value_counts().to_string())

    print("\n  Rozlozenie RequestVersion:")
    print(df["RequestVersion"].value_counts().to_string())

    return df


# ============================================================
# HLAVNA FUNKCIA – ekvivalent int main() v C
# ============================================================
def main():
    # --- Krok A: Parsovanie Apache logu do DataFrame ---
    df = parse_log_to_dataframe(INPUT_FILE)

    print("\nNacitany DataFrame:")
    print("  Zaznamov: " + str(len(df)))
    print("  Stlpce:   " + str(list(df.columns)))

    # --- Krok B: Cistenie dat ---
    df = clean_data(df)

    print("\nOcisteny DataFrame:")
    print("  Zaznamov: " + str(len(df)))
    print("  Stlpce:   " + str(list(df.columns)))

    # --- Krok C: Ulozenie do CSV ---
    # index=False = nechceme ulozit automaticky cislovany index (0,1,2,...) do CSV
    # encoding="utf-8" = UTF-8 kodovanie (agent moze obsahovat specialne znaky)
    print("\nUkladam do: " + OUTPUT_FILE + " ...")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print("Hotovo! Subor ulozeny: " + OUTPUT_FILE)


# Spustenie iba pri priamom spusteni skriptu (python task1_cleaning.py)
# Ak by sme tento subor importovali do ineho skriptu, main() sa NESPUSTI automaticky
# ekvivalent C: int main() { ... }   (vstupny bod programu)
if __name__ == "__main__":
    main()
