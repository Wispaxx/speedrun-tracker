import requests
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL") or "https://discord.com/api/webhooks/1521120941092900934/SzETUs_lrGuVNaLNEwzFejU_lOQr74ZZBYml1A52uW8ct9m-upyTGvqmSjjuBc7mq5kE"
API_URL = "https://www.speedrun.com/api/v1/runs?game=m1mn0ekd&orderby=date&direction=desc&max=3"
STATE_FILE = "state/last_run_id.txt"

def get_run_details(run):
    """Extrait tous les détails d'une run"""
    details = {}
    
    # Runner
    runner_data = run["players"][0]
    if runner_data["rel"] == "user":
        try:
            runner_response = requests.get(f"https://www.speedrun.com/api/v1/users/{runner_data['id']}", timeout=10)
            details["runner"] = runner_response.json()["data"]["names"]["international"]
        except:
            details["runner"] = "Inconnu"
    else:
        details["runner"] = runner_data.get("name", "Invité")
    
    # Catégorie
    category_id = run["category"]
    level_id = run.get("level")
    try:
        category_response = requests.get(f"https://www.speedrun.com/api/v1/categories/{category_id}", timeout=10)
        category_data = category_response.json()["data"]
        category_name = category_data["name"]
        
        if category_data.get("type") == "per-level" and level_id:
            level_response = requests.get(f"https://www.speedrun.com/api/v1/levels/{level_id}", timeout=10)
            level_name = level_response.json()["data"]["name"]
            details["category"] = f"{level_name} - {category_name}"
        else:
            details["category"] = category_name
    except:
        details["category"] = "Catégorie inconnue"
    
    # Plateforme
    platform = "Non spécifiée"
    try:
        platform_id = run.get("system", {}).get("platform")
        if platform_id:
            platform_response = requests.get(f"https://www.speedrun.com/api/v1/platforms/{platform_id}", timeout=10)
            platform = platform_response.json()["data"]["name"]
    except:
        pass
    details["platform"] = platform
    
    # Temps
    time = run.get("times", {}).get("primary_t", "N/A")
    if isinstance(time, (int, float)):
        minutes = int(time // 60)
        seconds = int(time % 60)
        details["time"] = f"{minutes}m {seconds:02d}s" if minutes > 0 else f"{seconds}s"
    else:
        details["time"] = str(time)
    
    # Date
    date_raw = run.get("date")
    if date_raw:
        try:
            date_obj = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            details["date"] = date_obj.strftime("%d/%m/%Y à %H:%M UTC")
        except:
            details["date"] = date_raw
    else:
        details["date"] = "Date inconnue"
    
    details["link"] = f"https://www.speedrun.com/m1mn0ekd/run/{run['id']}"
    details["id"] = run["id"]
    
    return details

def send_discord_notification(run_details):
    """Envoie la notification Discord"""
    embed = {
        "title": "🚀 A pending run has been detected !",
        "color": 16776960,
        "fields": [
            {"name": "🏷️ Category / Level", "value": run_details["category"], "inline": True},
            {"name": "🏃 Runner", "value": run_details["runner"], "inline": True},
            {"name": "⏱️ Time", "value": run_details["time"], "inline": True},
            {"name": "🖥️ Platform", "value": run_details["platform"], "inline": True},
            {"name": "📅 Date", "value": run_details["date"], "inline": False},
            {"name": "🔗 Link", "value": f"[Click here]({run_details['link']})", "inline": False}
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    payload = {"embeds": [embed]}

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        return response.status_code == 204
    except Exception as e:
        print(f"❌ Erreur Discord : {e}")
        return False

def check_new_runs():
    print("🔍 Vérification des nouvelles runs...")
    
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ API répondue (statut {response.status_code})")
    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return

    if not data.get("data"):
        print("📭 Aucune run trouvée.")
        return

    runs = data["data"]
    print(f"📋 {len(runs)} runs trouvées")
    
    # Lire le cache
    os.makedirs("state", exist_ok=True)
    seen_ids = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            content = f.read().strip()
            if content:
                seen_ids = set(content.split(","))
        print(f"💾 Cache : {len(seen_ids)} runs déjà vues")
    
    # Vérifier chaque run (de la plus récente à la plus ancienne)
    new_runs = []
    for run in runs:
        run_id = run["id"]
        if run_id not in seen_ids:
            new_runs.append(run)
            seen_ids.add(run_id)
    
    if not new_runs:
        print("✅ Aucune nouvelle run détectée.")
        return
    
    print(f"🎉 {len(new_runs)} nouvelle(s) run(s) détectée(s) !")
    
    # Envoyer une notification pour chaque nouvelle run (de la plus ancienne à la plus récente)
    for run in reversed(new_runs):
        print(f"📝 Traitement de la run {run['id']}...")
        details = get_run_details(run)
        
        print(f"🏃 Runner : {details['runner']}")
        print(f"🏷️ Catégorie : {details['category']}")
        print(f"⏱️ Temps : {details['time']}")
        
        success = send_discord_notification(details)
        if success:
            print(f"✅ Notification envoyée pour {run['id']}")
        else:
            print(f"❌ Échec pour {run['id']}")
    
    # Mettre à jour le cache
    with open(STATE_FILE, "w") as f:
        f.write(",".join(seen_ids))
    print(f"💾 Cache mis à jour avec {len(seen_ids)} runs")

if __name__ == "__main__":
    check_new_runs()
