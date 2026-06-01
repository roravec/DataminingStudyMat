import pandas as pd  # pd.read_csv(), df.to_csv(), str.contains(), isin(), unique()

# ============================================================
# TASK 2 – Identifikacia robotov (Robot Detection)
# ============================================================
# Vstup:  wm2020projekt_cleaned.csv  (vystup z Task 1)
# Vystupy:
#   wm2020projekt_robots.csv    – zoznam IP adries robotov (este ich budeme potrebovat)
#   wm2020projekt_no_robots.csv – log bez robotov (vstup pre Task 3)
# ------------------------------------------------------------
# Postup (podla tasks.txt + tasks_additional_info.txt):
#
# Krok 1: Vymazanie cron uloh acymailing
#         Automaticke skripty systemu acymailing (newsletter plugin pre Joomla)
#         sa pravidelne spustaju cez HTTP – nie su to kliknutia pouzivatela.
#         Identifikacia: URL zacina predponou CRON_URL_PREFIX
#
# Krok 2: Identifikacia robotov cez robots.txt
#         Vyhladavace citaju /robots.txt ako prvy krok pri indexovani webu.
#         => Kazda IP ktora pristupila k robots.txt je pravdepodobne robot.
#         Unikatne IP adresy ulozime do wm2020projekt_robots.csv
#
# Krok 3: Vymazanie VSETKYCH zaznamov robotickych IP adries
#         Nielen pristup k robots.txt, ale VSETKA aktivita tychto IP adries.
#
# Krok 4: Vymazanie robotov podla User-Agent (Agent stlpec)
#         Klucove slova typicke pre automatizovane skripty a crawlery.
# ============================================================

# ----------------------------------------
# KONFIGURACNE KONSTANTY (ekvivalent #define v C)
# ----------------------------------------

INPUT_FILE   = "wm2020projekt_cleaned.csv"    # vstup: ocisteny log z Task 1
ROBOTS_FILE  = "wm2020projekt_robots.csv"     # vystup: zoznam IP adries robotov
OUTPUT_FILE  = "wm2020projekt_no_robots.csv"  # vystup: log bez robotov

# URL predpona acymailing cron uloh (Joomla newsletter plugin)
# Typicky format: /index.php?option=com_acymailing&ctrl=cron
# POZNAMKA: Ak po spusteni nenajde ziadne zaznamy, over aktualne URL v datach:
#   df[df['URL'].str.contains('acymailing', case=False, na=False)]['URL'].unique()
CRON_URL_PREFIX = "/index.php?option=com_acymailing"

# Retazec ktory identifikuje pristup k robots.txt v URL
ROBOTS_TXT_KEYWORD = "robots.txt"

# Klucove slova v poli Agent (User-Agent) typicke pre robotov a crawlery
# Pouzijeme ich v regex vzore (oddelene znakom |  = OR)
# Ekvivalent C: strcmp(agent, "bot") || strcmp(agent, "crawl") || ...
BOT_KEYWORDS = [
    "bot",              # vseobecne roboty (Googlebot, Bingbot, ...)
    "crawl",            # crawlery (webcrawler, ...)
    "spider",           # spidery (typicky vyhladavace)
    "wget",             # wget – command line HTTP klient, casto automatizovany
    "libwww-perl",      # Perl HTTP klient – automatizovane skripty
    "python",           # Python HTTP klient – automatizovane skripty
    "java/",            # Java HTTP klient (napr. Apache HttpClient)
    "facebookexternalhit",  # Facebook link preview robot
]


# ============================================================
# FUNKCIA: remove_cron_jobs
# ============================================================
def remove_cron_jobs(df):
    """
    Vymazeme zaznamy automatickych cron uloh acymailing.
    Identifikacia: URL stlpec ZACINA hodnotou CRON_URL_PREFIX.
    """
    print("\nKrok 1: Mazem cron uly acymailing (URL zacina: '" + CRON_URL_PREFIX + "')...")

    before = len(df)

    # str.startswith() vrati True ak retazec zacina danou predponou
    # na=False = prazdne hodnoty (NaN) sa povazuju za False
    # ekvivalent C: if (strncmp(url, CRON_URL_PREFIX, len(CRON_URL_PREFIX)) == 0)
    mask_cron = df["URL"].str.startswith(CRON_URL_PREFIX, na=False)

    # ~ = negacia (ekvivalent C: !mask_cron)
    # Ponechame riadky kde URL NEZACINA cron predponou
    df = df[~mask_cron]
    df = df.reset_index(drop=True)   # znovu ocislujeme riadky od 0

    after = len(df)
    print("  Vymazanych cron zaznamov: " + str(before - after) + ", zostatok: " + str(after))

    return df


# ============================================================
# FUNKCIA: find_robot_ips
# ============================================================
def find_robot_ips(df):
    """
    Najde unikatne IP adresy robotov na zaklade pristupu k robots.txt.
    Vrati zoznam (list) unikatnych IP adries.
    """
    print("\nKrok 2: Hladam IP adresy robotov cez prístup k robots.txt...")

    # str.contains() vrati True ak URL obsahuje retazec "robots.txt"
    # regex=False = jednoduchy textovy match (rychlejsi pre pevny retazec)
    # ekvivalent C: if (strstr(url, "robots.txt") != NULL)
    mask_robots = df["URL"].str.contains(ROBOTS_TXT_KEYWORD, regex=False, na=False)

    # Z riadkov kde je robots.txt vyberieme stlpec IP a ziskame unikatne hodnoty
    # .unique() = ekvivalent C: deduplicate(robot_ips, count);
    robot_ips = df[mask_robots]["IP"].unique()

    print("  Najdenych unikatnych robot IP adries: " + str(len(robot_ips)))

    # Vypis prikladu (prvych 10)
    print("  Priklady:")
    i = 0
    for ip in robot_ips:
        if i >= 10:
            break
        print("    " + ip)
        i += 1

    return robot_ips


# ============================================================
# FUNKCIA: save_robot_ips
# ============================================================
def save_robot_ips(robot_ips, output_path):
    """
    Ulozi zoznam robot IP adries do CSV suboru.
    Format: jeden stlpec 'IP', jeden zaznam per riadok.
    """
    # Vytvorime jednoduchy DataFrame s jednym stlpcom
    df_robots = pd.DataFrame(robot_ips, columns=["IP"])

    # index=False = nechceme cislovany index v CSV
    df_robots.to_csv(output_path, index=False, encoding="utf-8")

    print("  Robot IP adresy ulozene do: " + output_path)


# ============================================================
# FUNKCIA: remove_robot_ips
# ============================================================
def remove_robot_ips(df, robot_ips):
    """
    Vymazeme VSETKY zaznamy z IP adries robotov.
    Nielen pristup k robots.txt, ale vsetku aktivitu tychto IP adries.
    """
    print("\nKrok 3: Mazem VSETKY zaznamy robot IP adries (" + str(len(robot_ips)) + " IP)...")

    before = len(df)

    # isin() kontroluje ci hodnota stlpca IP je v zozname robot_ips
    # ekvivalent C: for (i=0; i<n; i++) { if (is_robot_ip(row[i].ip)) ... }
    mask_robot_ip = df["IP"].isin(robot_ips)

    # ~ = negacia – ponechame riadky kde IP NIE JE v zozname robotov
    df = df[~mask_robot_ip]
    df = df.reset_index(drop=True)

    after = len(df)
    print("  Vymazanych zaznamov: " + str(before - after) + ", zostatok: " + str(after))

    return df


# ============================================================
# FUNKCIA: remove_bot_agents
# ============================================================
def remove_bot_agents(df):
    """
    Vymazeme zaznamy kde Agent (User-Agent) obsahuje klucove slova robotov.
    Klucove slova su definovane v zozname BOT_KEYWORDS.
    """
    print("\nKrok 4: Mazem zaznamy podla User-Agent (klucove slova robotov)...")
    print("  Klucove slova: " + str(BOT_KEYWORDS))

    before = len(df)

    # Spojime klucove slova do jedneho regex vzoru oddelenych | (OR)
    # Priklad: "bot|crawl|spider|wget|..."
    # ekvivalent C: compiled_regex_t re = regex_compile(BOT_PATTERN);
    bot_pattern = "|".join(BOT_KEYWORDS)

    # str.contains() s regex=True aplikuje vzor na kazdy riadok stlpca Agent
    # case=False = case-insensitive (Googlebot, googlebot, GOOGLEBOT -> vsetko zachyti)
    # na=False   = prazdne Agent hodnoty ("-") sa povazuju za False (nie za bota)
    mask_bot_agent = df["Agent"].str.contains(bot_pattern, case=False, regex=True, na=False)

    # ~ = negacia – ponechame riadky kde Agent NEOBSAHUJE bot klucove slova
    df = df[~mask_bot_agent]
    df = df.reset_index(drop=True)

    after = len(df)
    print("  Vymazanych bot-agent zaznamov: " + str(before - after) + ", zostatok: " + str(after))

    return df


# ============================================================
# HLAVNA FUNKCIA – ekvivalent int main() v C
# ============================================================
def main():
    # --- Krok A: Nacitanie CSV zo Task 1 ---
    print("Nacitavam: " + INPUT_FILE + " ...")
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    print("  Nacitanych zaznamov: " + str(len(df)))
    print("  Stlpce: " + str(list(df.columns)))

    # --- Krok 1: Vymazanie cron uloh acymailing ---
    df = remove_cron_jobs(df)

    # --- Krok 2: Najdenie IP adries robotov (cez robots.txt) ---
    robot_ips = find_robot_ips(df)

    # --- Ulozenie zoznamu robot IP adries (este ich budeme potrebovat) ---
    save_robot_ips(robot_ips, ROBOTS_FILE)

    # --- Krok 3: Vymazanie vsetkych zaznamov robot IP adries ---
    df = remove_robot_ips(df, robot_ips)

    # --- Krok 4: Vymazanie robotov podla User-Agent ---
    df = remove_bot_agents(df)

    # --- Zhrnutie ---
    print("\nVysledny DataFrame:")
    print("  Zaznamov: " + str(len(df)))
    print("  Stlpce:   " + str(list(df.columns)))

    # --- Ulozenie vysledku ---
    print("\nUkladam do: " + OUTPUT_FILE + " ...")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print("Hotovo! Subor ulozeny: " + OUTPUT_FILE)


# Spustenie iba pri priamom spusteni (python task2_robots.py)
# ekvivalent C: int main() { ... }
if __name__ == "__main__":
    main()
