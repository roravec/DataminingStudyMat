import pandas as pd                       # pd.read_csv(), pd.concat(), groupby(), sort_values(), ...
from collections import deque             # deque() – fronta pre BFS algoritmus

# ============================================================
# TASK 5 – Doplnanie chybajucich medzistranok (Missing Path Completion)
# ============================================================
# Vstup:  wm2020projekt_sessions.csv  (vystup z Task 4)
# Vystupy (pre kazdy subtask vlastny subor):
#   wm2020projekt_paths_sttmean.csv  – doplnene cesty pre STT_MEAN sedenia
#   wm2020projekt_paths_sttq.csv     – doplnene cesty pre STT_Q sedenia
# ------------------------------------------------------------
# Problem:
#   V logu chybaju niektoré medzistranky v navigacnych cestach pouzivatela.
#   Napr. pouzivatel bol na /a, potom je v logu /c, ale /b chyba.
#   Referrer zaznamu /c vsak ukazuje na /b -> vieme ze /b existuje.
#
# Riesenie (podla tasks_additional_info.txt):
#   1. Zostavime MAPU WEBU zo stlpca Referrer:
#      slovnik {zdrojova_stranka: mnozina stranok kam vedu odkazy}
#      Tato mapa nam hovori ktore stranky su navzajom prepojene.
#   2. Pre kazde sedenie prechadzame zaznamy chronologicky.
#      Ak referrer aktualneho zaznamu != URL predosleho zaznamu
#      -> pouzivatel "preskocil" nejake stranky -> chybajuca medzistrenka.
#   3. BFS algoritmom hladame cestu v mape webu od predoslej URL ku aktualnej URL.
#      Ak cesta existuje -> doplnime chybajuce medzistranky ako nove zaznamy.
#      Cas novych zaznamov = rovnomerne interpolovany medzi predoslym a aktualnym.
#   4. Povodne + doplnene zaznamy zlucime, zoradime a ulozime do CSV.
# ============================================================

# ----------------------------------------
# KONFIGURACNE KONSTANTY (ekvivalent #define v C)
# ----------------------------------------

INPUT_FILE = "wm2020projekt_sessions.csv"  # vstup: sessions zo vsetkymi metodami

# Vystupne subory – pre kazdy subtask vlastny (podla tasks.txt)
OUTPUT_STTMEAN = "wm2020projekt_paths_sttmean.csv"
OUTPUT_STTQ    = "wm2020projekt_paths_sttq.csv"
OUTPUT_RLENGTH = "wm2020projekt_paths_rlength.csv"
OUTPUT_HREF    = "wm2020projekt_paths_href.csv"

# Maximalna hlbka BFS prehliadania (kolko medzistranok maximalne doplnime)
# STT_Mean a STT_Q pouzivaju hlbku 4 (podla tasks_additional_info.txt)
BFS_MAX_DEPTH = 4

# Znacka pre doplnene zaznamy v stlpci DateTime
# Podla toho vieme rozlisit povodne vs. doplnene zaznamy
FILLED_MARKER = "FILLED"


# ============================================================
# POMOCNA FUNKCIA: strip_domain
# ============================================================
def strip_domain(url):
    """
    Odstrani domenu z URL a vrati len cestu.
    Priklad: "https://www.ukf.sk/o-nas" -> "/o-nas"
             "/o-nas"                   -> "/o-nas"  (uz je len cesta)
             "-"                        -> "-"        (chybajuci referrer)
    Ekvivalent C: char* p = strstr(url, "//"); p = strchr(p+2, '/');
    """
    if not isinstance(url, str):
        return url     # NaN alebo None -> vratime tak ako je

    if "://" in url:
        # Preskocime "https://" alebo "http://"
        # Hladame prvy "/" za domenou
        start     = url.find("://") + 3        # index za "//"
        slash_pos = url.find("/", start)       # prvy "/" za domenou
        if slash_pos != -1:
            return url[slash_pos:]             # vratime len cestu
        else:
            return "/"                         # URL bez cesty -> root

    return url   # uz je to len cesta


# ============================================================
# FUNKCIA: build_web_map
# ============================================================
def build_web_map(df):
    """
    Zostaví slovnik (mapu webu) zo stlpca Referrer a URL.
    Kluc  = zdrojova stranka (referrer bez domeny)
    Hodnota = mnozina (set) stranok kam vedu odkazy z tejto zdrojovej stranky

    Priklad:
      Referrer = "https://www.ukf.sk/o-nas", URL = "/kontakt"
      -> web_map["/o-nas"].add("/kontakt")

    Ekvivalent C: hash_map<string, set<string>> web_map;
    """
    print("Zostavujem mapu webu z Referrer stlpca...")

    # Prazdny slovnik – ekvivalent C: hash_map<string, set<string>> web_map = {};
    web_map = {}

    # Prechádzame kazdy riadok DataFrame
    # itertuples() je rychlejsi ako iterrows() pre velke DataFrame
    for row in df.itertuples(index=False):

        # Odstranime domenu z Referreru
        ref_path = strip_domain(row.Referrer)

        # Preskocime chybajuci referrer ("-") alebo prazdne hodnoty
        if not isinstance(ref_path, str) or ref_path == "-" or ref_path == "":
            continue

        # Pridame prepojenie: ref_path -> row.URL
        # setdefault(key, set()) – ak kluc neexistuje, vytvori prazdny set
        # Ekvivalent C: if (!web_map.count(ref)) web_map[ref] = {}; web_map[ref].insert(url);
        web_map.setdefault(ref_path, set()).add(row.URL)

    print("  Pocet stranok v mape webu: " + str(len(web_map)))
    return web_map


# ============================================================
# FUNKCIA: bfs_find_path
# ============================================================
def bfs_find_path(web_map, start_url, end_url, max_depth):
    """
    BFS algoritmus – hlada cestu v mape webu od start_url po end_url.
    Hlbka prehliadania je obmedzena na max_depth krokov.

    Vrati zoznam medzistranok (bez start_url a bez end_url),
    alebo None ak cesta neexistuje.

    BFS = prehladavanie do sirky:
      - Zacneme na start_url
      - Pridame vsetky susedne stranky do fronty (deque)
      - Pre kazdu stranku z fronty pridame dalej jej susedov
      - Zastavime ked najdeme end_url alebo prekrocime max_depth

    Ekvivalent C: queue<pair<string,vector<string>>> q; BFS_loop(q, web_map);
    """

    # Ak start alebo end nie su v mape -> cesta neexistuje
    if start_url not in web_map:
        return None

    # Fronta pre BFS: kazdy prvok je (aktualna_stranka, cesta_sem)
    # deque = double-ended queue – efektivna fronta (append/popleft = O(1))
    # Ekvivalent C: queue<pair<char*, char**>> q;
    queue = deque()
    queue.append((start_url, []))    # zaciname na start_url, cesta je prazdna

    # Navstivene stranky – aby sme nechodili v kruhoch
    # Ekvivalent C: hash_set<string> visited;
    visited = set()
    visited.add(start_url)

    # BFS cyklus – pokracujeme kym fronta nie je prazdna
    # Ekvivalent C: while (!q.empty()) { ... }
    while queue:
        current_url, path_so_far = queue.popleft()   # vyberieme prvok z fronty

        # Prekrocili sme maximalnu hlbku -> preskocime
        if len(path_so_far) >= max_depth:
            continue

        # Prejdeme vsetkych susedov aktualnej stranky
        # Ekvivalent C: for (neighbor in web_map[current]) { ... }
        for neighbor in web_map.get(current_url, set()):

            if neighbor in visited:
                continue    # uz sme tu boli -> preskocime (zamedzenie cyklov)

            # Cesta k tomuto susedovi
            new_path = path_so_far + [neighbor]

            # Nasli sme cielovu stranku?
            if neighbor == end_url:
                # Vratime cestu BEZ start_url a BEZ end_url (len medzistranky)
                return new_path[:-1]   # new_path[-1] je end_url -> vyhodime

            visited.add(neighbor)
            queue.append((neighbor, new_path))   # pridame do fronty

    return None    # cesta sa nenasla


# ============================================================
# FUNKCIA: fill_missing_paths
# ============================================================
def fill_missing_paths(df, session_col, web_map, max_depth=BFS_MAX_DEPTH):
    """
    Pre kazde sedenie (definovane stlpcom session_col) doplni chybajuce medzistranky.
    Vracia novy DataFrame s povodymi + doplnenymi zaznamami, zoradeny.

    Algoritmus pre kazde sedenie:
      1. Zoradime zaznamy chronologicky (podla unixtime)
      2. Pre po sebe iduce zaznamy (prev -> curr):
         - Ak referrer curr == URL prev -> priame prepojenie, ok, nic nedoplname
         - Inak -> chybaju medzistranky -> BFS hlada cestu v mape webu
         - Ak BFS najde cestu -> doplnime medzistranky s interpolovanym casom
    """
    print("  Doplnam chybajuce cesty (session_col='" + session_col + "')...")

    # Zoznam doplnenych zaznamov (ekvivalent C: struct Record* filled_records;)
    filled_rows = []

    # Pocitace pre statistiku
    total_sessions  = 0
    filled_count    = 0

    # Iterujeme cez sedenia – groupby rozdeluje DataFrame podla ID sedenia
    # Ekvivalent C: for (session_id = 0; session_id < n_sessions; session_id++)
    for session_id, session_df in df.groupby(session_col):

        total_sessions += 1

        # Zoradime zaznamy sedenia chronologicky
        session_df = session_df.sort_values("unixtime").reset_index(drop=True)

        # Prechádzame po sebe iduce dvojice zaznamov v sedeni
        # i = index aktualneho zaznamu (zaciname od 1 lebo porovnavame s i-1)
        # Ekvivalent C: for (i = 1; i < n; i++)
        i = 1
        while i < len(session_df):

            # Aktualny zaznam
            curr = session_df.iloc[i]
            # Predosly zaznam
            prev = session_df.iloc[i - 1]

            # Referrer aktualneho zaznamu (bez domeny)
            curr_ref = strip_domain(curr["Referrer"])

            # Ak referrer aktualneho == URL predosleho -> priame prepojenie -> ok
            # Ekvivalent C: if (strcmp(curr_ref, prev_url) == 0) continue;
            if curr_ref == prev["URL"]:
                i += 1
                continue

            # Referrer sa nezhoduje s predoslou URL -> chyba medzistrenka
            # Hladame cestu BFS od prev["URL"] po curr["URL"]
            path = bfs_find_path(web_map, prev["URL"], curr["URL"], max_depth)

            if path is None or len(path) == 0:
                # BFS nenasiel cestu -> nedoplname nic
                i += 1
                continue

            # BFS nasiel cestu -> doplname medzistranky
            # Cas novych zaznamov = rovnomerne interpolovany medzi prev a curr
            # Ekvivalent C: double step = (curr_time - prev_time) / (n_steps + 1);
            prev_time = prev["unixtime"]
            curr_time = curr["unixtime"]
            n_steps   = len(path)   # pocet medzistranok

            # Interpolacia casu: rozdel interval rovnomerne na (n_steps + 1) usekoch
            # krok = (curr_time - prev_time) / (n_steps + 1)
            time_step = (curr_time - prev_time) / (n_steps + 1)

            # Vytvorime novy zaznam pre kazdu medzistranku
            # Ekvivalent C: for (j = 0; j < n_steps; j++) { create_record(path[j]); }
            j = 0
            while j < n_steps:
                interpolated_time = int(prev_time + time_step * (j + 1))

                # Novy zaznam – kopirujeme meta-data z predosleho zaznamu
                # (IP, UserID, Agent zostanu rovnake – je to ten isty pouzivatel)
                new_row = {
                    "IP":            prev["IP"],
                    "DateTime":      FILLED_MARKER,   # oznacime ze je to doplneny zaznam
                    "RequestMethod": prev["RequestMethod"],
                    "URL":           path[j],          # doplnena medzistrenka
                    "RequestVersion":prev["RequestVersion"],
                    "StatusCode":    prev["StatusCode"],
                    "Referrer":      FILLED_MARKER,   # oznacime ze referrer bol doplneny
                    "Agent":         prev["Agent"],
                    "unixtime":      interpolated_time,
                    "UserID":        prev["UserID"],
                    "Length":        None,             # nevieme dlzku pre doplneny zaznam
                    session_col:     session_id,       # zaradi do toho isteho sedenia
                }

                filled_rows.append(new_row)
                filled_count += 1
                j += 1

            i += 1

    print("    Celkovo sedeni:        " + str(total_sessions))
    print("    Doplnenych zaznamov:   " + str(filled_count))

    # Ak neboli doplnene ziadne zaznamy -> vratime povodny DataFrame
    if len(filled_rows) == 0:
        print("    Ziadne chybajuce cesty nenajdene.")
        return df

    # Zlucime povodne zaznamy s doplnenymi
    # pd.concat() = ekvivalent C: memcpy(result, original); memcpy(result+n, filled);
    df_filled = pd.DataFrame(filled_rows)
    df_result = pd.concat([df, df_filled], ignore_index=True)

    # Zoradime podla sedenia a casu
    df_result = df_result.sort_values(by=[session_col, "unixtime"]).reset_index(drop=True)

    return df_result


# ============================================================
# POMOCNA FUNKCIA: run_subtask
# ============================================================
def run_subtask(df, web_map, session_col, output_file, bfs_depth=BFS_MAX_DEPTH):
    """
    Spusti dopĺňanie ciest pre jeden subtask (jednu metodu sedenia).
    Ulozi vysledok do output_file.
    bfs_depth – maximalna hlbka BFS (default=4, RLength pouziva 6)
    """
    print("\n" + "=" * 50)
    print("Subtask: " + session_col + " -> " + output_file + "  (BFS hlbka=" + str(bfs_depth) + ")")
    print("=" * 50)

    # Vyberieme len stlpce relevantne pre tento subtask
    # (ostatne session stlpce nepotrebujeme v tomto subore)
    cols_to_keep = ["IP", "DateTime", "RequestMethod", "URL", "RequestVersion",
                    "StatusCode", "Referrer", "Agent", "unixtime", "UserID",
                    "Length", session_col]
    df_sub = df[cols_to_keep].copy()

    print("  Zaznamov pred doplnenim: " + str(len(df_sub)))

    # Doplnime chybajuce cesty
    df_result = fill_missing_paths(df_sub, session_col, web_map, bfs_depth)

    print("  Zaznamov po doplneni:    " + str(len(df_result)))
    print("  Ukladam do: " + output_file + " ...")
    df_result.to_csv(output_file, index=False, encoding="utf-8")
    print("  Hotovo!")


# ============================================================
# HLAVNA FUNKCIA – ekvivalent int main() v C
# ============================================================
def main():
    # --- Nacitanie CSV z Task 4 ---
    print("Nacitavam: " + INPUT_FILE + " ...")
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    print("  Nacitanych zaznamov: " + str(len(df)))
    print("  Stlpce: " + str(list(df.columns)))

    # --- Zostavenie mapy webu (raz pre vsetky subtasky) ---
    web_map = build_web_map(df)

    # --- Subtask 1: Doplnit cesty pre STT_MEAN sedenia ---
    run_subtask(df, web_map, "STT_MEAN", OUTPUT_STTMEAN)

    # --- Subtask 2: Doplnit cesty pre STT_Q sedenia ---
    run_subtask(df, web_map, "STT_Q", OUTPUT_STTQ)

    # --- Subtask 3: Doplnit cesty pre RLength sedenia ---
    # RLength vytvara viac a kratsich sedeni -> vacsiu pravdepodobnost chybajucich stranok
    # tasks_additional_info.txt: RLength pouziva vacsiu BFS hlbku (6 namiesto 4)
    run_subtask(df, web_map, "RLength", OUTPUT_RLENGTH, bfs_depth=6)

    # --- Subtask 4: Doplnit cesty pre hRef sedenia ---
    run_subtask(df, web_map, "hRef", OUTPUT_HREF)

    print("\nVsetky subtasky hotove.")


# Spustenie iba pri priamom spusteni (python task5_missing_path.py)
# ekvivalent C: int main() { ... }
if __name__ == "__main__":
    main()
