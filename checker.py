import requests
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL") or "VOTRE_URL_DE_WEBHOOK_DISCORD_ICI"
API_URL = "https://www.speedrun.com/api/v1/runs?game=m1mn0ekd&orderby=date&direction=desc&max=5"
STATE_FILE = "state/last_run_id.txt"

def check_new_runs():
    print("🔍 Vérification des nouvelles runs...")
    print(f"📡 URL interrogée : {API_URL}")
    
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ API répondue (statut {response.status_code})")
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des données : {e}")
        return

    if not data.get("data"):
        print("📭 Aucune run trouvée.")
        return

    # Prendre la run la plus récente
    latest_run = data["data"][0]
    run_id = latest_run["id"]
    print(f"🆕 Run la plus récente : {run_id}")

    # --- SUPPRESSION DU CACHE : on ne vérifie plus l'ancien ID ---
    # On envoie directement la notification pour la run la plus récente
    print("🎉 Envoi de la notification pour la run la plus récente...")
    
    # Extraire les détails
    print("📝 Extraction des détails...")
    
    # --- Runner ---
    runner_data = latest_run["players"][0]
    if runner_data["rel"] == "user":
        runner_id = runner_data["id"]
        try:
            runner_response = requests.get(f"https://www.speedrun.com/api/v1/users/{runner_id}", timeout=10)
            runner_response.raise_for_status()
            runner_name = runner_response.json()["data"]["names"]["international"]
        except Exception as e:
            print(f"⚠️ Erreur runner : {e}")
            runner_name = "Inconnu"
    else:
        runner_name = runner_data.get("name", "Invité")
    print(f"🏃 Runner : {runner_name}")

    # --- Catégorie ---
    category_id = latest_run["category"]
    level_id = latest_run.get("level")
    category_name = "Catégorie inconnue"
    level_name = None
    
    try:
        category_response = requests.get(f"https://www.speedrun.com/api/v1/categories/{category_id}", timeout=10)
        category_response.raise_for_status()
        category_data = category_response.json()["data"]
        category_name = category_data["name"]
        
        if category_data.get("type") == "per-level" and level_id:
            level_response = requests.get(f"https://www.speedrun.com/api/v1/levels/{level_id}", timeout=10)
            level_response.raise_for_status()
            level_name = level_response.json()["data"]["name"]
    except Exception as e:
        print(f"⚠️ Erreur catégorie/niveau : {e}")
    
    if level_name:
        full_category = f"{level_name} - {category_name}"
    else:
        full_category = category_name
    print(f"🏷️ Catégorie complète : {full_category}")

    # --- Plateforme ---
    platform = "Non spécifiée"
    try:
        system = latest_run.get("system", {})
        platform_id = system.get("platform")
        if platform_id:
            platform_response = requests.get(f"https://www.speedrun.com/api/v1/platforms/{platform_id}", timeout=10)
            platform_response.raise_for_status()
            platform = platform_response.json()["data"]["name"]
    except Exception as e:
        print(f"⚠️ Erreur plateforme : {e}")
    print(f"🖥️ Plateforme : {platform}")

    # --- Temps ---
    time = latest_run.get("times", {}).get("primary_t", "N/A")
    if isinstance(time, (int, float)):
        minutes = int(time // 60)
        seconds = int(time % 60)
        if minutes > 0:
            time_str = f"{minutes}m {seconds:02d}s"
        else:
            time_str = f"{seconds}s"
    else:
        time_str = str(time)
    print(f"⏱️ Temps : {time_str}")

    # --- Date ---
    date_raw = latest_run.get("date")
    if date_raw:
        try:
            date_obj = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            date_formatted = date_obj.strftime("%d/%m/%Y à %H:%M UTC")
        except Exception:
            date_formatted = date_raw
    else:
        date_formatted = "Date inconnue"
    print(f"📅 Date : {date_formatted}")

    # --- Lien ---
    game_id = "m1mn0ekd"
    run_link = f"https://www.speedrun.com/{game_id}/run/{run_id}"
    print(f"🔗 Lien : {run_link}")

    # --- Envoyer l'embed Discord ---
    print("📨 Envoi de la notification Discord...")
    
    embed = {
        "title": "🚀 A pending run has been detected !",
        "color": 16776960,  # Jaune
        "fields": [
            {"name": "🏷️ Category / Level", "value": full_category, "inline": True},
            {"name": "🏃 Runner", "value": runner_name, "inline": True},
            {"name": "⏱️ Time", "value": time_str, "inline": True},
            {"name": "🖥️ Platform", "value": platform, "inline": True},
            {"name": "📅 Date", "value": date_formatted, "inline": False},
            {"name": "🔗 Link", "value": f"[Click here to view the run]({run_link})", "inline": False}
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    payload = {"embeds": [embed]}

    try:
        discord_response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        discord_response.raise_for_status()
        if discord_response.status_code == 204:
            print("✅ Notification envoyée avec succès !")
        else:
            print(f"⚠️ Réponse inattendue : {discord_response.status_code}")
            print(discord_response.text)
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi : {e}")

if __name__ == "__main__":
    check_new_runs()
