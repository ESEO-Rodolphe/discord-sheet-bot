import os
import json
import gspread
from dotenv import load_dotenv

load_dotenv()
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

cred_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not cred_json:
    raise ValueError("GOOGLE_CREDENTIALS_JSON vide")
creds_dict = json.loads(cred_json)
if "private_key" in creds_dict:
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

gc = gspread.service_account_from_dict(creds_dict)
sh = gc.open_by_key(SPREADSHEET_ID)
ws_bdd = sh.worksheet("BDD")
ws_subs = sh.worksheet("Abonnements")

# -------------------- Cars --------------------
def get_all_cars():
    """Récupère toutes les voitures distinctes de la colonne C à partir de la ligne 2"""
    all_values = ws_bdd.col_values(3)[1:]  # Col C, ignorer header
    return sorted(list(set([v.strip() for v in all_values if v.strip() != ""])))

def search_cars(keyword):
    """Retourne toutes les voitures correspondant au mot-clé"""
    keyword = keyword.lower()
    return [car for car in get_all_cars() if keyword in car.lower()]

# -------------------- Subscriptions --------------------
def get_user_subscriptions_by_car(car_name):
    """Retourne la liste des user_id abonnés à une voiture"""
    records = ws_subs.get_all_records()
    return [r['user_id'] for r in records if r['voiture'] == car_name]

def get_user_subscriptions(user_id):
    """Récupère la liste des voitures suivies par un utilisateur"""
    records = ws_subs.get_all_records()
    return [r['voiture'] for r in records if str(r['user_id']) == str(user_id)]

def add_subscription(user_id, car_name):
    """Ajoute une ligne pour l'utilisateur et voiture si elle n'existe pas"""
    existing = ws_subs.get_all_records()
    for r in existing:
        if str(r['user_id']) == str(user_id) and r['voiture'] == car_name:
            return
    ws_subs.append_row([str(user_id), car_name])

def remove_subscription(user_id, car_name):
    """Supprime la ligne correspondant à user_id et car_name"""
    records = ws_subs.get_all_records()
    for idx, r in enumerate(records, start=2):  # start=2 car gspread index 1 = header
        if str(r['user_id']) == str(user_id) and r['voiture'] == car_name:
            ws_subs.delete_rows(idx)
            break
