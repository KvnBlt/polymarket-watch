# Polymarket Watch Bot

Petit bot Python qui surveille les trades récents d’adresses Polymarket et envoie un unique e-mail lorsqu’au moins un nouveau trade est détecté dans la fenêtre de temps définie.

## Prérequis

- Compte GitHub avec accès aux GitHub Actions.
- Identifiants SMTP (ex. Gmail + App Password, Mailgun, SendGrid, etc.).
- Adresse(s) Polymarket (en format wallet Polygon) à surveiller.

## Configuration

1. Copier `config.yaml`. Par défaut il contient l’adresse Polygon de gopfan2 (`0xf2f6af4f27ec2dcf4072095ab804016e14cd5817`, profil Polymarket : https://polymarket.com/profile/0xf2f6af4f27ec2dcf4072095ab804016e14cd5817?tab=activity). Remplacez-la si vous souhaitez suivre un autre trader et ajoutez d’autres adresses en les listant dans `addresses`.
2. Ajuster si besoin `window_minutes` (doit rester > intervalle CRON, soit > 15 min).
3. Laisser ou modifier les filtres optionnels `min_size` et `sides` (liste de `BUY`/`SELL`).
4. Mettre à jour la section `email` si vous souhaitez changer le destinataire ou le préfixe du sujet.

### Secrets SMTP

Dans le dépôt GitHub, créer les secrets Actions suivants (Settings → Secrets and variables → Actions):

| Secret | Description |
| --- | --- |
| `SMTP_HOST` | Serveur SMTP (ex. `smtp.gmail.com`) |
| `SMTP_PORT` | Port (`587` pour STARTTLS, `465` pour SSL, etc.) |
| `SMTP_USER` | Identifiant SMTP |
| `SMTP_PASS` | Mot de passe / App Password |
| `SMTP_FROM` | Adresse « From » (ex. `Polymarket Bot <sokhaar313@gmail.com>`) |

## Exécution locale

```bash
python -m venv .venv
source .venv/bin/activate  # sous Windows: .venv\Scripts\activate
pip install -r requirements.txt
export SMTP_HOST=...
export SMTP_PORT=...
export SMTP_USER=...
export SMTP_PASS=...
export SMTP_FROM=...
python -m src.main
```

Le script charge automatiquement les variables à partir d’un fichier `.env` si présent (via `python-dotenv`), ce qui simplifie les tests locaux.

## Déploiement GitHub Actions

1. Pousser le dépôt sur GitHub après avoir mis à jour `config.yaml`.
2. Créer les secrets SMTP comme indiqué ci-dessus.
3. Le workflow `.github/workflows/polymarket-watch.yml` se déclenche toutes les 15 minutes (`*/15 * * * *`). Aucune autre configuration n’est nécessaire.

## Ajouter un trader

Ajouter simplement une nouvelle adresse Polygon dans `addresses` de `config.yaml`. Le script interrogera toutes les adresses à chaque exécution.

## Tests rapides

Des tests unitaires de base sont fournis (formatage des e-mails, filtrage, intégration simulée). Installer pytest si nécessaire (`pip install pytest`) puis lancer :

```bash
pytest
```
