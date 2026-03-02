<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Apprenez le fonctionnement de la XRPL (XRP Ledger) en une seule session. Pas de comptes. Pas d'argent réel. Juste vous et la XRPL.

XRPL Camp vous guide à travers 6 leçons, de "qu'est-ce qu'une XRPL ?" à la création d'un portefeuille financé, d'un paiement confirmé et d'un certificat portable, en environ 10 minutes.

## Installation

```bash
pipx install xrpl-camp
```

Ou avec pip :

```bash
pip install xrpl-camp
```

## Démarrage rapide

```bash
xrpl-camp start
```

Cette commande exécute le tutoriel à travers les 6 leçons :

1. **Modèle mental** — Qu'est-ce que la XRPL (comptes, soldes, transactions, mémos)
2. **Création de portefeuille** — Générer une paire de clés pour le réseau de test (Testnet)
3. **Financement du portefeuille** — Obtenir des XRP de test gratuits grâce au "faucet"
4. **Envoi d'un paiement** — Écrire un mémo dans la XRPL (paiement à soi-même, 1 goutte)
5. **Vérification de la transaction** — Vérifier ce que vous avez écrit
6. **Certificat** — Obtenir un enregistrement portable et vérifiable de ce que vous avez fait

## Commandes

| Commande | Ce qu'elle fait |
|---------|-------------|
| `xrpl-camp start` | Exécute le tutoriel à travers les 6 leçons |
| `xrpl-camp start --dry-run` | Effectue le tutoriel complet sans connexion réseau |
| `xrpl-camp wallet create` | Crée un portefeuille pour le réseau de test (Testnet) |
| `xrpl-camp wallet show` | Affiche l'adresse de votre portefeuille |
| `xrpl-camp fund` | Finance votre portefeuille via le "faucet" du réseau de test (Testnet) |
| `xrpl-camp fund --dry-run` | Simule le financement sans connexion réseau |
| `xrpl-camp send --memo "hello"` | Envoie un paiement à vous-même avec un mémo personnalisé |
| `xrpl-camp send --dry-run` | Simule le paiement |
| `xrpl-camp verify --tx <hash>` | Vérifie une transaction sur la XRPL |
| `xrpl-camp certificate` | Génère un certificat et un "proof pack" |
| `xrpl-camp reset` | Efface toutes les données (nécessite une confirmation explicite) |

## Ce que vous obtenez

- Un portefeuille financé pour le réseau de test (Testnet) (`.xrpl-camp/wallet.json` — local, ignoré par Git)
- Un paiement confirmé sur le réseau de test (Testnet) de la XRPL
- Un rapport de vérification montrant exactement ce que la XRPL a enregistré
- Un certificat (`xrpl_camp_certificate.json`) — peut être partagé en toute sécurité, sans clés privées
- Un "proof pack" (`xrpl_camp_proof_pack.json`) — intègre une protection contre la falsification, avec un hachage SHA-256

## Mode de test (Dry-Run Mode)

Toutes les commandes qui nécessitent une connexion réseau prennent en charge l'option `--dry-run`. Elle affiche ce qui se passerait sans établir de connexion réseau ni modifier les données. Utile pour gagner en confiance et pour le débogage.

## "Proof Pack"

Le "proof pack" est un enregistrement sécurisé de tout ce que vous avez fait :

- Adresse du portefeuille et réseau
- Horodatages de la fin de chaque leçon
- Identifiants des transactions avec les liens vers les explorateurs
- Version de l'outil
- Hachage SHA-256 du contenu complet

Toute personne peut vérifier le hachage pour confirmer que le fichier n'a pas été modifié.

## Modification de l'adresse du nœud

Par défaut, XRPL Camp utilise le nœud public du réseau de test (Testnet) de la XRPL. Pour utiliser un autre nœud :

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```

## Sécurité

Votre clé secrète (clé privée) est stockée localement et n'est jamais incluse dans le certificat ou le "proof pack".
Cet outil utilise uniquement le réseau de test (Testnet) de la XRPL — les XRP de test n'ont aucune valeur réelle.
Aucune télémétrie, aucune analyse, aucun envoi de données — les seules connexions réseau sont établies avec le réseau de test (Testnet) de la XRPL.

Consultez le fichier [SECURITY.md](SECURITY.md) pour plus de détails.

## Analyse des risques

| Risque | Mesure de protection |
|--------|-----------|
| Fuite de la clé secrète via le certificat | La génération du certificat exclut explicitement la clé secrète ; vérification de sécurité `certificate_has_seed()` |
| Fuite de la clé secrète via le "proof pack" | La génération du "proof pack" exclut la clé secrète ; vérification de sécurité `proof_pack_has_seed()` |
| Clé secrète dans Git | Le dossier `.xrpl-camp/` est ignoré par Git ; la commande `wallet show` n'affiche jamais la clé secrète |
| Réutilisation de la clé secrète du réseau de test (Testnet) sur le réseau principal (Mainnet) | Un avertissement est affiché lors de la création du portefeuille |
| Exposition du contenu des mémos | Tous les mémos sont publics par conception ; les utilisateurs sont avertis avant d'envoyer un paiement |
| Altération du "proof pack" | Hachage d'intégrité SHA-256 ; `verify_proof_pack()` détecte toute modification |

## Développement

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
uv run ruff check .
uv run pytest tests/ -v
```

## Licence

MIT

---

Construit par [MCP Tool Shop](https://mcp-tool-shop.github.io/).
