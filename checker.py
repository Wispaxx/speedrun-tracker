import requests
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
# !!! NE METTEZ PAS L'URL DIRECTEMENT ICI !!!
# Utilisez le secret GitHub à la place
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
if not DISCORD_WEBHOOK_URL:
    # Fallback pour les tests en local (à supprimer après)
    DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1521120941092900934/SzETUs_lrGuVNaLNEwzFejU_lOQr74ZZBYml1A52uW8ct9m-upyTGvqmSjjuBc7mq5kE"

API_URL = "https://www.speedrun.com/api/v1/runs?game=m1mn0ekd&status=new"
STATE_FILE = "state/last_run_id.txt"

def safe_get(data, *keys, default="N/A"):
    """Récupère une valeur dans un dictionnaire imbriqué sans planter"""
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data if data else default

def check_new_runs():
    print("🔍 Vérification des nouvelles runs...")
    
    if not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL == "VOTRE_URL_DE_WEBHOOK_DISCORD_ICI":
        print("❌ ERREUR: L'URL du webhook Discord n'est pas configurée!")
        print("   Ajoutez le secret DISCORD_WEBHOOK_URL dans GitHub")
        return

    # 1. Récupérer les données de l'API
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la récupération des données : {e}")
        return

    # Vérifier qu'il y a des runs en attente
    if not data.get("data"):
        print("✅ Aucune run en attente (status=new) pour le moment.")
        return

    # Prendre la run la plus récente
    latest_run = data["data"][0]
    run_id = latest_run.get("id")
    if not run_id:
        print("❌ L'ID de la run n'a pas pu être récupéré")
        return

    # 2. Vérifier si c'est une nouvelle run
    os.makedirs("state", exist_ok=True)
    
    old_id = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            old_id = f.read().strip()

    if run_id == old_id:
        print("✅ Aucune nouvelle run détectée.")
        return

    # Sauvegarder le nouvel ID
    with open(STATE_FILE, "w") as f:
        f.write(run_id)

    # 3. Extraire les informations (avec gestion d'erreur)
    print("🎉 Nouvelle run détectée ! Préparation de l'embed...")

    # --- Extraire le nom du Runner ---
    runner_name = "Inconnu"
    try:
        players = latest_run.get("players", [])
        if players:
            player = players[0]
            if player.get("rel") == "user":
                runner_id = player.get("id")
                if runner_id:
                    try:
                        runner_resp = requests.get(f"https://www.speedrun.com/api/v1/users/{runner_id}", timeout=10)
                        runner_resp.raise_for_status()
                        runner_name = runner_resp.json().get("data", {}).get("names", {}).get("international", "Inconnu")
                    except Exception as e:
                        print(f"⚠️ Impossible de récupérer le nom du runner: {e}")
            else:
                runner_name = player.get("name", "Invité")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'extraction du runner: {e}")

    # --- Extraire le nom de la Catégorie ---
    category_name = "Catégorie inconnue"
    try:
        category_id = latest_run.get("category")
        if category_id:
            cat_resp = requests.get(f"https://www.speedrun.com/api/v1/categories/{category_id}", timeout=10)
            cat_resp.raise_for_status()
            category_name = cat_resp.json().get("data", {}).get("name", "Catégorie inconnue")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'extraction de la catégorie: {e}")

    # --- Extraire le Temps ---
    time = safe_get(latest_run, "times", "primary_t", default="N/A")
    if time and time != "N/A":
        try:
            # Nettoyer le temps pour l'affichage
            if isinstance(time, (int, float)):
                minutes = int(time // 60)
                seconds = int(time % 60)
                time = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        except:
            pass

    # --- Extraire la Date ---
    date_formatted = "Date inconnue"
    try:
        date_raw = latest_run.get("date")
        if date_raw:
            if "Z" in date_raw:
                date_raw = date_raw.replace("Z", "+00:00")
            date_obj = datetime.fromisoformat(date_raw)
            date_formatted = date_obj.strftime("%d/%m/%Y à %H:%M")
    except Exception as e:
        print(f"⚠️ Erreur lors du formatage de la date: {e}")

    # --- Construire le Lien ---
    game_id = "m1mn0ekd"
    run_link = f"https://www.speedrun.com/{game_id}/run/{run_id}"

    # 4. Construire l'embed (AVEC VALIDATION DES CHAMPS)
    # Discord ne tolère pas les champs vides !
    fields = []
    
    # Ajouter chaque champ uniquement s'il a une valeur valide
    if category_name and category_name != "Catégorie inconnue":
        fields.append({"name": "🏷️ Category", "value": str(category_name)[:1000], "inline": True})
    else:
        fields.append({"name": "🏷️ Category", "value": "Non spécifiée", "inline": True})
    
    if runner_name and runner_name != "Inconnu":
        fields.append({"name": "🏃 Runner", "value": str(runner_name)[:1000], "inline": True})
    else:
        fields.append({"name": "🏃 Runner", "value": "Anonyme", "inline": True})
    
    if time and time != "N/A":
        fields.append({"name": "⏱️ Time", "value": str(time)[:100], "inline": True})
    else:
        fields.append({"name": "⏱️ Time", "value": "N/A", "inline": True})
    
    fields.append({"name": "📅 Date", "value": str(date_formatted)[:100], "inline": False})
    fields.append({"name": "🔗 Link", "value": f"[Cliquez pour voir la run]({run_link})", "inline": False})

    # Construction du payload avec vérification
    embed = {
        "title": "🚀 A pending run has been detected !",
        "description": "Une nouvelle run en attente vient d'être soumise !",
        "color": 16776960,  # Jaune
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "footer": {
            "text": "Speedrun.com Tracker"
        }
    }

    payload = {
        "embeds": [embed],
        # Pas de content pour éviter les doublons
    }

    # 5. Envoyer à Discord avec gestion d'erreur détaillée
    try:
        headers = {"Content-Type": "application/json"}
        
        # Validation du payload avant envoi
        payload_json = json.dumps(payload)
        
        # Tester la longueur (Discord limite à 6000 caractères pour un embed)
        if len(payload_json) > 6000:
            print(f"⚠️ Payload trop long ({len(payload_json)} caractères), réduction...")
            # Réduire le titre et la description
            embed["title"] = embed["title"][:50]
            embed["description"] = embed["description"][:50]
            payload = {"embeds": [embed]}
            payload_json = json.dumps(payload)
        
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            data=payload_json,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 204:
            print("✅ Notification envoyée avec succès à Discord !")
        else:
            print(f"❌ Erreur lors de l'envoi : {response.status_code}")
            print(f"   Réponse de Discord : {response.text[:200]}")
            
            # Si l'erreur est un 400, afficher le payload pour déboguer
            if response.status_code == 400:
                print("\n--- Payload envoyé (pour débogage) ---")
                print(payload_json[:500])
                print("... (tronqué)")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de l'envoi à Discord : {e}")

if __name__ == "__main__":
    check_new_runs()