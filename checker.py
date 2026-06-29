import requests
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
# !!! REMPLACEZ CETTE URL PAR LA VOTRE !!!
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1521120941092900934/SzETUs_lrGuVNaLNEwzFejU_lOQr74ZZBYml1A52uW8ct9m-upyTGvqmSjjuBc7mq5kE"
API_URL = "https://www.speedrun.com/api/v1/runs?game=m1mn0ekd&status=new"
STATE_FILE = "state/last_run_id.txt"

def check_new_runs():
    print("🔍 Vérification des nouvelles runs...")

    # 1. Récupérer les données de l'API
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Vérifie que la requête a réussi
        data = response.json()
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des données : {e}")
        return

    # Vérifier qu'il y a des runs en attente
    if not data.get("data"):
        print("✅ Aucune run en attente (status=new) pour le moment.")
        return

    # Prendre la run la plus récente (la première dans la liste)
    latest_run = data["data"][0]
    run_id = latest_run["id"]

    # 2. Vérifier si c'est une nouvelle run (comparaison avec l'état précédent)
    old_id = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            old_id = f.read().strip()

    # Créer le dossier 'state' s'il n'existe pas
    os.makedirs("state", exist_ok=True)

    # Si c'est la même run que la dernière fois, on arrête
    if run_id == old_id:
        print("✅ Aucune nouvelle run détectée.")
        return

    # Sauvegarder le nouvel ID pour la prochaine vérification
    with open(STATE_FILE, "w") as f:
        f.write(run_id)

    # 3. C'est une nouvelle run ! Extraire les informations
    print("🎉 Nouvelle run détectée ! Préparation de l'embed...")

    # --- Extraire le nom du Runner ---
    runner_data = latest_run["players"][0]
    if runner_data["rel"] == "user":
        # Si c'est un utilisateur enregistré, on va chercher son nom via l'API
        runner_id = runner_data["id"]
        try:
            runner_response = requests.get(f"https://www.speedrun.com/api/v1/users/{runner_id}")
            runner_response.raise_for_status()
            runner_name = runner_response.json()["data"]["names"]["international"]
        except Exception:
            runner_name = "Inconnu"
    else:  # Si c'est un invité (guest)
        runner_name = runner_data.get("name", "Invité")

    # --- Extraire le nom de la Catégorie ---
    category_id = latest_run["category"]
    try:
        category_response = requests.get(f"https://www.speedrun.com/api/v1/categories/{category_id}")
        category_response.raise_for_status()
        category_name = category_response.json()["data"]["name"]
    except Exception:
        category_name = "Catégorie inconnue"

    # --- Extraire le Temps ---
    time = latest_run.get("times", {}).get("primary_t", "N/A")

    # --- Extraire la Date ---
    date_raw = latest_run.get("date")
    if date_raw:
        try:
            # Formatage de la date pour un affichage plus lisible
            date_obj = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            date_formatted = date_obj.strftime("%d/%m/%Y à %H:%M UTC")
        except Exception:
            date_formatted = date_raw
    else:
        date_formatted = "Date inconnue"

    # --- Construire le Lien vers la run ---
    game_id = "m1mn0ekd"
    run_link = f"https://www.speedrun.com/{game_id}/run/{run_id}"

    # 4. Construire et envoyer l'embed Discord (JAUNE)
    embed = {
        "title": "🚀 A pending run has been detected !",
        "color": 16776960,  # Code hexadécimal pour la couleur jaune (#FFFF00)
        "fields": [
            {"name": "🏷️ Category", "value": category_name, "inline": True},
            {"name": "🏃 Runner", "value": runner_name, "inline": True},
            {"name": "⏱️ Time", "value": time, "inline": True},
            {"name": "📅 Date", "value": date_formatted, "inline": False},
            {"name": "🔗 Link", "value": f"[Click here to view the run]({run_link})", "inline": False}
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    payload = {"embeds": [embed]}

    # Envoyer la notification à Discord
    try:
        discord_response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        discord_response.raise_for_status()
        # Un code 204 signifie "succès, pas de contenu en retour"
        if discord_response.status_code == 204:
            print("✅ Notification envoyée avec succès à Discord !")
        else:
            print(f"⚠️ Réponse inattendue de Discord : {discord_response.status_code}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi à Discord : {e}")

if __name__ == "__main__":
    check_new_runs()