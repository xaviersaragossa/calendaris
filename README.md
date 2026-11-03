# Calendaris

Aplicació web (Flask) per veure els calendaris de Google de diversos usuaris
(comptes Gmail i Google Workspace) mitjançant OAuth 2.0.

## 1. Configurar Google Cloud

1. Entra a https://console.cloud.google.com i crea un projecte.
2. **APIs i serveis > Biblioteca**: activa **Google Calendar API**.
3. **Pantalla de consentiment d'OAuth**: tipus **Extern** (perquè hi ha comptes
   Gmail i d'empresa). Afegeix l'scope `.../auth/calendar.readonly`.
   Mentre l'app estigui en mode "Proves" cal afegir els correus dels usuaris
   com a *usuaris de prova* (màxim 100).
4. **Credencials > Crear credencials > ID de client OAuth**: tipus *Aplicació web*.
   - URI de redirecció autoritzat: `http://localhost:5000/callback`
5. Copia l'ID de client i el secret.

> Usuaris d'empresa (Workspace): si l'administrador té bloquejades les apps de
> tercers, haurà d'autoritzar l'ID de client a Admin Console > Seguretat > Control d'accés a l'API.

## 2. Executar en local

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # i omple els valors
python app.py
```

Obre http://localhost:5000.

## 3. Cap a producció

- Servir sota **HTTPS** i treure `OAUTHLIB_INSECURE_TRANSPORT` del `.env`.
- Actualitzar `REDIRECT_URI` i l'URI autoritzat a Google Cloud.
- Usar gunicorn (`gunicorn app:app`) i una base de dades gestionada si cal.
- Sol·licitar la verificació de l'app a Google per sortir del mode "Proves".
- Per poder crear/editar esdeveniments, canviar l'scope a `.../auth/calendar`.
