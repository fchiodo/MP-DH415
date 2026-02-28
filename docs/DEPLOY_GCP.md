# Deploy MP-DH415 su Google Cloud Platform (Free Tier)

Guida per eseguire il trading bot su una **VM e2-micro** (sempre gratuita su GCP).

---

## Risorse Free Tier usate

| Risorsa | Limite gratuito | Uso |
|---|---|---|
| Compute Engine e2-micro | 1 istanza/mese (us-central1 / us-west1 / us-east1) | VM che ospita bot + API |
| Disco HDD | 30 GB/mese | Sistema + codice + SQLite |
| Egress network | 1 GB/mese verso la maggior parte delle destinazioni | Chiamate FXCM + Slack |

> **Importante:** scegli la region `us-central1`, `us-west1` o `us-east1` per restare nel free tier.

---

## 1. Creare la VM su GCP

### Via Console Web (più semplice)

1. Vai su [console.cloud.google.com](https://console.cloud.google.com) → **Compute Engine** → **Istanze VM** → **Crea istanza**
2. Imposta:

| Campo | Valore |
|---|---|
| **Nome** | `trading-bot` |
| **Region** | `us-central1` (Iowa) |
| **Zone** | `us-central1-a` |
| **Tipo macchina** | `e2-micro` (0.25 vCPU, 1 GB RAM) — **free tier** |
| **Disco di avvio** | Ubuntu 22.04 LTS, **30 GB HDD standard** |
| **Firewall** | Abilita "Consenti traffico HTTP" se vuoi accedere all'API |

3. Clicca **Crea**.

### Via gcloud CLI

```bash
gcloud compute instances create trading-bot \
  --machine-type=e2-micro \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard \
  --tags=http-server
```

---

## 2. Connettersi alla VM

```bash
# Via gcloud (da terminale locale con gcloud installato)
gcloud compute ssh trading-bot --zone=us-central1-a

# Oppure dal browser: Console GCP → Compute Engine → SSH (pulsante)
```

---

## 3. Setup iniziale sulla VM

### 3a. Clona il repository

```bash
# Sulla VM:
cd ~
git clone https://github.com/TUO_USERNAME/MP-DH415.git
cd MP-DH415
```

### 3b. Crea il file .env

```bash
nano ~/MP-DH415/.env
```

Incolla il contenuto del tuo `.env` locale (non è nel repo per sicurezza):

```
SLACK_BOT_TOKEN='xoxb-...'
SLACK_CHANNEL='mt-bot'
FXCM_LOGIN_ID='...'
FXCM_PASSWORD='...'
FXCM_URL='http://www.fxcorporate.com/Hosts.jsp'
FXCM_CONNECTION='Demo'
FXCM_SESSION=Trade
RISK_PER_TRADE='1'
MIN_REWARD_RISK='2'
REFERENCE_BALANCE='10000'
ACTIVE_PAIRS='GBP/CHF'
```

Salva con `Ctrl+O`, esci con `Ctrl+X`.

### 3c. Esegui lo script di setup

```bash
chmod +x ~/MP-DH415/deploy/gcp_setup.sh
~/MP-DH415/deploy/gcp_setup.sh
```

Lo script in automatico:
- Installa Python 3.10
- Crea un virtualenv in `~/MP-DH415/venv`
- Installa tutte le dipendenze Python (incluso `forexconnect`)
- Registra e avvia i due servizi systemd (`trading-bot` e `flask-api`)

---

## 4. Verifica che i servizi girino

```bash
# Stato
sudo systemctl status trading-bot
sudo systemctl status flask-api

# Log in tempo reale
journalctl -u trading-bot -f
journalctl -u flask-api -f
```

### Comandi utili

```bash
# Fermare il bot
sudo systemctl stop trading-bot

# Riavviare
sudo systemctl restart trading-bot

# Aggiornare il codice e riavviare
cd ~/MP-DH415 && git pull && sudo systemctl restart trading-bot flask-api
```

---

## 5. Aprire la porta 5001 per l'API Flask

Se vuoi accedere alla Flask API dall'esterno (es. dal browser su Mac):

```bash
# Crea una regola firewall GCP
gcloud compute firewall-rules create allow-flask-api \
  --allow tcp:5001 \
  --source-ranges=0.0.0.0/0 \
  --description="Flask API per Trading Bot"
```

Oppure dalla Console: **VPC Network** → **Firewall** → **Crea regola** → porta TCP 5001.

L'API sarà raggiungibile su: `http://EXTERNAL_IP:5001`

Trova l'IP esterno su Console → Compute Engine → la tua istanza → colonna **IP esterno**.

---

## 6. Frontend React

Il frontend React è un'app statica. Opzioni:

**A) Build locale, serve statico dalla VM**
```bash
# In locale:
cd ~/Documents/MP-DH415/frontend
VITE_API_URL=http://EXTERNAL_IP:5001 npm run build

# Copia dist/ sulla VM (o committala nel repo)
scp -r dist/ trading-bot:~/MP-DH415/frontend/dist
```

**B) Render.com Static Site (gratuito)**  
Crea un Static Site su Render puntato alla cartella `frontend` con `VITE_API_URL=http://EXTERNAL_IP:5001`.

---

## 7. Bug fix applicati per GCP

### Problema principale risolto: percorso Python hardcoded

In `backend/bot_runner.py` c'era:
```python
python_path = '/opt/homebrew/bin/python3.10'  # ❌ percorso macOS
```
Corretto in:
```python
python_path = sys.executable  # ✓ usa lo stesso interprete che gira il processo
```

Questo era il motivo per cui il bot non si avviava su qualsiasi macchina diversa dal Mac di sviluppo.

### forexconnect aggiunto a requirements.txt

La libreria FXCM `forexconnect` è ora inclusa nelle dipendenze Python per Linux/GCP. In precedenza era installata solo manualmente.

---

## 8. Architettura su GCP

```
VM GCP e2-micro (us-central1)
│
├─ systemd: flask-api.service
│   └─ gunicorn → frontend/api/app.py → porta 5001
│       └─ legge/scrive my_database.db (SQLite)
│
└─ systemd: trading-bot.service
    └─ backend/bot_runner.py --interval 300
        └─ subprocess → martina.py per ogni coppia in ACTIVE_PAIRS
            ├─ ForexConnect → FXCM API (dati di mercato)
            └─ SQLite → my_database.db (trade, log, segnali)
```

---

## 9. Limiti free tier da tenere a mente

- **1 GB RAM**: il bot + l'API girano insieme. Se hai molte coppie in `ACTIVE_PAIRS` e la VM va in OOM, riduci il numero di coppie o aumenta l'`--interval`.
- **Disco**: SQLite crescerà nel tempo. Monitora con `du -sh ~/MP-DH415/my_database.db`.
- **Egress**: 1 GB gratis/mese. Con poche coppie non dovresti superarlo.
- **FXCM**: la connessione Demo funziona da qualsiasi IP. Se usi Live, verifica che l'IP della VM non sia bloccato.
