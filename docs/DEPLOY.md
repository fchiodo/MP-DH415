# Deploy MP-DH415 su Render

Guida pratica per mettere online **3 servizi** sullo stesso progetto Render (stesso repo).

---

## 0. Prerequisiti

- **Repo Git** (GitHub/GitLab) collegato a Render.
- **Branch**: di solito `main`.
- Tutti e tre i servizi nello **stesso region** (es. Frankfurt) per ridurre latenza.

---

## 1. Servizio 1: API Flask (Web Service)

Lo screenshot che hai è per questo servizio. Imposta così:

| Campo | Valore |
|-------|--------|
| **Type** | Web Service |
| **Name** | `mp-dh415-api` (o simile) |
| **Language** | Python 3 |
| **Branch** | `main` |
| **Region** | Frankfurt (EU Central) (o quello che usi per tutti) |
| **Root Directory** | **`frontend/api`** ← **obbligatorio** (altrimenti non trova `requirements.txt`) |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT app:app` |

**Env vars** (nella sezione Environment del servizio):

- Tutte le variabili che oggi metti in `.env` (FXCM, Slack, risk, ecc.).
- **`FRONTEND_URL`** = URL pubblico del frontend Render (es. `https://mp-dh415.onrender.com`) per CORS.

**Modifiche già fatte nel repo:**

- `frontend/api/requirements.txt`: aggiunto **gunicorn**.
- CORS: accetta le origini da `FRONTEND_URL` (oltre a localhost).
- Se non esiste `.env`, il caricamento viene saltato (Render usa le env vars della dashboard).
- Salvataggio config da UI: su Render restituisce errore se non c’è `.env` (configurazione solo da dashboard).

---

## 2. Servizio 2: Frontend React (Static Site)

Crea un **nuovo** servizio → **Static Site** (non Web Service).

| Campo | Valore |
|-------|--------|
| **Name** | `mp-dh415` (o simile) |
| **Branch** | `main` |
| **Region** | Stesso dell’API (es. Frankfurt) |
| **Root Directory** | **`frontend`** |
| **Build Command** | `npm install && npm run build` |
| **Publish Directory** | **`dist`** (output di Vite) |

**Env var:**

- **`VITE_API_URL`** = URL pubblico dell’API su Render (es. `https://mp-dh415-api.onrender.com`).

Così il frontend in build time punta all’API giusta.

---

## 3. Servizio 3: Bot runner (Background Worker)

Crea un **nuovo** servizio → **Background Worker**.

| Campo | Valore |
|-------|--------|
| **Name** | `mp-dh415-bot` |
| **Language** | Python 3 |
| **Branch** | `main` |
| **Region** | Stesso di API e frontend |
| **Root Directory** | **`backend`** |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python bot_runner.py --interval 300` |

(Regola `--interval` a piacere, es. 60 o 300 secondi.)

**Env vars:** stesse del bot (FXCM, Slack, `ACTIVE_PAIRS`, `SIMULATION_MODE`, ecc.). Copiale dalla dashboard dell’API o imposta le stesse qui.

---

## 4. Cosa mancava dallo screenshot (risposte dirette)

1. **Root Directory**  
   Per l’API Flask va impostata a **`frontend/api`**. Se resta vuota, Render cerca `requirements.txt` nella root del repo e il build fallisce.

2. **Start Command**  
   Non era in figura; per l’API deve essere:  
   `gunicorn --bind 0.0.0.0:$PORT app:app`

3. **Tre servizi**  
   Lo schermo riguardava un solo Web Service. Ti servono:
   - 1 **Static Site** (frontend),
   - 1 **Web Service** (API),
   - 1 **Background Worker** (bot).

4. **Env vars**  
   Vanno configurate nella sezione Environment di ogni servizio (FXCM, Slack, `FRONTEND_URL` sull’API, `VITE_API_URL` sul frontend).

---

## 5. Database (SQLite) e limiti su Render

- Su Render **API** e **Worker** sono processi separati: **due filesystem diversi**.
- Ogni servizio ha la propria copia di `my_database.db` (se la crei nel repo root di quel servizio). Quindi:
  - L’API legge/scrive un SQLite sul **suo** disco.
  - Il bot legge/scrive un altro SQLite sul **suo** disco.
  - **Non condividono lo stesso DB** con la configurazione attuale.

Opzioni:

- **Solo sviluppo/test**: accetti che API e bot abbiano DB separati (es. vedi i log dal frontend, i trade “reali” solo dove gira il bot). Per test va bene.
- **Stabile**: usare un **database gestito** (es. **Render Postgres** o altro) e sostituire SQLite con un adapter (es. PostgreSQL + stesso schema). Richiede modifiche a `db_utils.py` e all’API (e un servizio DB su Render).

Per ora il codice è pensato per SQLite; la modifica per Postgres è un passo successivo se ti serve coerenza tra API e Worker.

---

## 6. SSE e piani Free

- L’endpoint **`/api/logs/stream`** (SSE) funziona su Render.
- Su piano **Free**, dopo **~15 min senza richieste** il Web Service va in sleep; al prossimo accesso c’è un **cold start** (qualche secondo/minuto).
- Le connessioni SSE contano come traffico; se non c’è traffico per 15 min, il servizio si spegne e le SSE si chiudono. Il frontend può riconnettersi quando il servizio si riattiva.

---

## 7. Start/Stop bot da UI su Render

- In **locale** la Flask avvia il bot con un **subprocess** (`bot_runner.py`). Su Render è sconsigliato far partire un loop infinito da un Web Service.
- Con la configurazione sopra il **bot è il Background Worker**: è sempre acceso (o parte a ogni deploy) e **non** viene avviato/fermato dai pulsanti Start/Stop della dashboard.
- I pulsanti Start/Stop in produzione su Render al momento **non** controllano il Worker (chiamano ancora l’endpoint che userebbe subprocess, che sul Web Service non deve lanciare il bot). Per evitare confusione puoi:
  - nascondere o disabilitare Start/Stop quando `VITE_API_URL` è l’URL Render, oppure
  - in un secondo tempo introdurre un “segnale” (file/DB/Redis) che il Worker legge per fare start/stop logico.

---

## 8. Checklist rapida

- [ ] Repo collegato a Render, branch `main`.
- [ ] **Static Site** (frontend): Root `frontend`, build `npm install && npm run build`, publish `dist`, env `VITE_API_URL`.
- [ ] **Web Service** (API): Root **`frontend/api`**, build `pip install -r requirements.txt`, start `gunicorn --bind 0.0.0.0:$PORT app:app`, env vars + `FRONTEND_URL`.
- [ ] **Background Worker** (bot): Root **`backend`**, build `pip install -r requirements.txt`, start `python bot_runner.py --interval 300`, env vars come per il bot.
- [ ] Stessa region per tutti e tre.
- [ ] Deciso: SQLite “per test” (due DB separati) oppure piano per Postgres in seguito.

Dopo il primo deploy, verifica che il frontend apra l’API (e che CORS sia ok) e che il Worker parta senza errori (FXCM/forexconnect disponibile nell’ambiente Render).
