import requests
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL") or "https://discord.com/api/webhooks/1521120941092900934/SzETUs_lrGuVNaLNEwzFejU_lOQr74ZZBYml1A52uW8ct9m-upyTGvqmSjjuBc7mq5kE"
API_URL = "https://www.speedrun.com/api/v1/runs?game=m1mn0ekd&orderby=date&direction=desc&max=1"

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

    # Prendre la run la plus récente
    latest_run = data["data"][0]
    run_id = latest_run["id"]
    print(f"🎯 Run la plus récente : {run_id}")

    # --- PAS DE CACHE : on envoie directement ---
    print("📝 Extraction des détails...")
    
    # Runner
    runner_data = latest_run["players"][0]
    if runner_data["rel"] == "user":
        runner_id = runner_data["id"]
        try:
            runner_response = requests.get(f"https://www.speedrun.com/api/v1/users/{runner_id}", timeout=10)
            runner_name = runner_response.json()["data"]["names"]["international"]
        except:
            runner_name = "Inconnu"
    else:
        runner_name = runner_data.get("name", "Invité")
    print(f"🏃 Runner : {runner_name}")

    # Catégorie
    category_id = latest_run["category"]
    level_id = latest_run.get("level")
    category_name = "Catégorie inconnue"
    level_name = None
    
    try:
        category_response = requests.get(f"https://www.speedrun.com/api/v1/categories/{category_id}", timeout=10)
        category_data = category_response.json()["data"]
        category_name = category_data["name"]
        
        if category_data.get("type") == "per-level" and level_id:
            level_response = requests.get(f"https://www.speedrun.com/api/v1/levels/{level_id}", timeout=10)
            level_name = level_response.json()["data"]["name"]
    except:
        pass
    
    full_category = f"{level_name} - {category_name}" if level_name else category_name
    print(f"🏷️ Catégorie : {full_category}")

    # Plateforme
    platform = "Non spécifiée"
    try:
        system = latest_run.get("system", {})
        platform_id = system.get("platform")
        if platform_id:
            platform_response = requests.get(f"https://www.speedrun.com/api/v1/platforms/{platform_id}", timeout=10)
            platform = platform_response.json()["data"]["name"]
    except:
        pass
    print(f"🖥️ Plateforme : {platform}")

    # Temps
    time = latest_run.get("times", {}).get("primary_t", "N/A")
    if isinstance(time, (int, float)):
        minutes = int(time // 60)
        seconds = int(time % 60)
        time_str = f"{minutes}m {seconds:02d}s" if minutes > 0 else f"{seconds}s"
    else:
        time_str = str(time)
    print(f"⏱️ Temps : {time_str}")

    # Date
    date_raw = latest_run.get("date")
    if date_raw:
        try:
            date_obj = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            date_formatted = date_obj.strftime("%d/%m/%Y à %H:%M UTC")
        except:
            date_formatted = date_raw
    else:
        date_formatted = "Date inconnue"
    print(f"📅 Date : {date_formatted}")

    # Lien
    run_link = f"https://www.speedrun.com/m1mn0ekd/run/{run_id}"
    print(f"🔗 Lien : {run_link}")

    # --- ENVOI DISCORD ---
    print("📨 Envoi de la notification...")
    
    embed = {
        "title": "🚀 A pending run has been detected !",
        "color": 16776960,
        "fields": [
            {"name": "🏷️ Category / Level", "value": full_category, "inline": True},
            {"name": "🏃 Runner", "value": runner_name, "inline": True},
            {"name": "⏱️ Time", "value": time_str, "inline": True},
            {"name": "🖥️ Platform", "value": platform, "inline": True},
            {"name": "📅 Date", "value": date_formatted, "inline": False},
            {"name": "🔗 Link", "value": f"[Click here]({run_link})", "inline": False}
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    payload = {"embeds": [embed]}

    try:
        discord_response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        discord_response.raise_for_status()
        print("✅ Notification envoyée !")
    except Exception as e:
        print(f"❌ Erreur Discord : {e}")

if __name__ == "__main__":
    check_new_runs()
