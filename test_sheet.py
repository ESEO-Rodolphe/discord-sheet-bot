import gspread

CRED_FILE = "credentials.json"
SPREADSHEET_ID = "1i4fvlU2JsTkjCI34RviznJyOumYAdJWv24DT-2B_7bM"

def test_read():
    # Connexion avec le compte de service
    gc = gspread.service_account(filename=CRED_FILE)
    
    # Ouvre ton fichier Google Sheet
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # Sélectionne la feuille "BDD"
    ws = sh.worksheet("BDD")
    
    # Récupère toutes les valeurs de la colonne W (23e colonne)
    values = ws.col_values(23)
    
    if values:
        last_value = values[-1]  # dernière valeur non vide
        print(f"Dernière valeur en colonne W : {last_value}")
    else:
        print("Colonne W vide !")

if __name__ == "__main__":
    test_read()
