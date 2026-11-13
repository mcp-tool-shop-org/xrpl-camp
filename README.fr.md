<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/xrpl-camp/"><img src="https://img.shields.io/pypi/v/xrpl-camp?label=PyPI" alt="PyPI version"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/xrpl-camp"><img src="https://img.shields.io/npm/v/@mcptoolshop/xrpl-camp?label=npm" alt="npm version"></a>
  <a href="https://codecov.io/gh/mcp-tool-shop-org/xrpl-camp"><img src="https://codecov.io/gh/mcp-tool-shop-org/xrpl-camp/branch/main/graph/badge.svg" alt="Coverage"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Apprenez les XRP Ledger en une seule séance. Pas de comptes. Pas d’argent réel. Juste vous et le grand livre.

La plupart des tutoriels sur la blockchain enseignent des concepts. XRPL Camp vous fait _mettre_ ces concepts en pratique : créez un portefeuille, alimentez-le, écrivez un mémorandum permanent dans un grand livre public, vérifiez-le de manière indépendante, et repartez avec un enregistrement que n’importe qui peut vérifier par rapport au grand livre lui-même. L’ensemble du processus dure environ dix minutes.

Conçu pour les ateliers, les salles de classe et l’auto-apprentissage. Le processus guidé reprend là où vous vous êtes arrêté, une leçon infructueuse arrête l’exécution au lieu de prétendre que tout s’est bien passé, et rien ne prétend que quelque chose s’est produit alors que ce n’était pas le cas.

## Pourquoi ceci plutôt qu’un tutoriel générique ?

- **Transactions réelles, pas des diapositives.** Vous écrivez dans un grand livre réel. Lorsque la leçon 5 indique « vérifiez-le vous-même », elle vous fournit un hachage et un lien vers un explorateur que n’importe qui peut vérifier.
- **Votre paiement crée un compte.** La leçon 4 n’est pas un simple transfert de test : elle finance un deuxième compte qui n’existait pas un instant auparavant, et dont les clés vous appartiennent également.
- **L’échec fait partie du programme.** `xrpl-camp try` provoque intentionnellement des erreurs sur le réseau en direct, puis vous montre quelles erreurs auraient entraîné des pertes et lesquelles sont gratuites, _avant_ que vous ne validiez une transaction.
- **Preuve que vous pouvez réellement vérifier.** Le paquet de preuves nomme des transactions réelles, et `proof verify --online` demande au grand livre si elles ont eu lieu. Personne ne peut falsifier cette partie.
- **Sécurité intégrée.** Testnet uniquement. Le test XRP n’a aucune valeur. Votre phrase de passe ne quitte jamais votre appareil. Pas de télémétrie, pas d’analyses, pas de comptes.

## Installation

**Aucun Python requis** (télécharge un binaire précompilé) :

```bash
npx @mcptoolshop/xrpl-camp start
```

Avec Python (3.11, 3.12 ou 3.13) :

```bash
pipx install xrpl-camp
```

Dans Docker — pour les ateliers où l’installation est la partie la plus difficile :

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> Montez un volume. Tout ce que vous créez — portefeuille, certificat, paquet de preuves — est écrit dans `/work`, et un conteneur démonté le supprime à la fermeture. L’image vous indique si vous avez oublié quelque chose.

## Démarrage rapide

```bash
xrpl-camp start
```

Six leçons, dans l’ordre, reprenant si vous redémarrez :

1. **Modèle mental** — ce qu’est le XRPL, demandé au réseau en direct plutôt qu’affirmé.
2. **Créer un portefeuille** — générer une paire de clés Testnet ; la phrase de passe reste sur votre appareil.
3. **Alimenter le portefeuille** — test XRP gratuit provenant du robinet, et pourquoi une partie de celui-ci n’est pas utilisable.
4. **Envoyer un paiement** — écrivez votre mémorandum dans le grand livre, dans un paiement qui crée un compte.
5. **Vérifier la transaction** — recherchez ce que vous avez écrit et comparez-le à ce que vous avez tapé.
6. **Certificat** — un enregistrement que vous conservez et que vous pouvez prouver.

## Commandes

| Commande | Ce qu’elle fait |
|---------|-------------|
| `xrpl-camp start` | Processus guidé à travers les 6 leçons (reprend automatiquement) |
| `xrpl-camp start --memo "..."` | Fournir le message de la leçon 4 à l’avance, pour les exécutions scriptées ou non interactives |
| `xrpl-camp read` | Vos entrées, relues **à partir du grand livre** — et non de cet appareil. |
| `xrpl-camp read <address>` | Ce que quelqu’un d’autre a écrit. Pas de clé, pas de connexion, pas d’autorisation. |
| `xrpl-camp read <hash>` | Une transaction, dans son intégralité. |
| `xrpl-camp try` | Provoquer intentionnellement une erreur sur le réseau en direct. Ne signe rien, ne coûte rien. |
| `xrpl-camp reserve` | Créer et détruire un NFT pour observer le verrouillage et le retour de la réserve du propriétaire. |
| `xrpl-camp status` | Liste de contrôle des progrès, avec les temps. |
| `xrpl-camp status --detail` | Vue du facilitateur : portefeuille, point de terminaison, répertoire d’état, prochaine étape. |
| `xrpl-camp wallet create` / `show` | Créer ou afficher votre portefeuille Testnet. |
| `xrpl-camp fund` | Alimenter votre portefeuille via le robinet Testnet. |
| `xrpl-camp send --memo "hello"` | Envoyer un paiement de mémorandum à votre boîte aux lettres. |
| `xrpl-camp verify --tx <hash>` | Vérifier une transaction **que vous** avez envoyée. |
| `xrpl-camp certificate` | Générer le certificat + le paquet de preuves (`--format text` ajoute un souvenir `.txt`). |
| `xrpl-camp proof verify <file>` | Vérifier le hachage d’un paquet de preuves. Entièrement hors ligne. |
| `xrpl-camp proof verify <file> --online` | Demander également au grand livre si les transactions ont réellement eu lieu (`--record` ajoute un reçu daté). |
| `xrpl-camp proof verify <folder>` | Vérifier tous les paquets d’un dossier — pour les facilitateurs. |
| `xrpl-camp reset` | Effacer tout l’état (nécessite de taper `RESET`). |
| `xrpl-camp self-check` | Diagnostiquer votre environnement **et** votre connexion au grand livre. |
| `xrpl-camp support-bundle` | Écrire un fichier zip de diagnostic pour les rapports de bogues. |

Indicateurs globaux : `--version`, `--dry-run`, `--yes` (non interactif), `--verbose` (détails techniques sur les erreurs).

## Ce que vous obtiendrez

- Un portefeuille Testnet financé, local et ignoré par Git.
- Un **deuxième compte qui n’existait pas avant que votre paiement ne le crée** — et dont les clés vous appartiennent également.
- Un mémorandum que vous avez choisi, enregistré de manière permanente et lisible de manière indépendante.
- Un certificat (`xrpl_camp_certificate.json`) — sans risque de partage, sans clés privées.
- Un paquet de preuves (`xrpl_camp_proof_pack.json`) — nommant des transactions réelles que n’importe qui peut résoudre.

## À propos de cette preuve

Le paquet de preuves contient un hachage SHA-256. Ce hachage détecte une modification accidentelle. Il ne s’agit **pas** d’une signature, et en lui-même, il ne prouve pas que le paquet est authentique — n’importe qui peut modifier un champ et recalculer le hachage avec la même fonction publique que cet outil utilise.

Ce qui ne peut pas être falsifié est le grand livre :

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

Il résout chaque transaction nommée par le paquet et vérifie qu’elle existe, qu’elle a été envoyée par l’adresse du paquet, qu’elle contient le mémorandum que le paquet prétend contenir et qu’elle s’est terminée avec succès. Un paquet avec une adresse réécrite passe la vérification hors ligne du hachage et échoue à celle-ci.

Deux détails à connaître, car il est facile de se tromper :

- La vérification interroge toujours le grand livre public Testnet (ou `--rpc-url`), **jamais** le point de terminaison nommé dans le paquet. Un paquet falsifié peut nommer un serveur que son auteur contrôle.
- Le XRPL Testnet est périodiquement réinitialisé (prochaine réinitialisation le 2026-11-25). Lorsque cela se produit, les transactions honnêtes cessent d’être résolues. Si le point de terminaison ne contient pas le grand livre dans lequel une transaction a été enregistrée, le résultat est *non vérifiable* (code de sortie 3), et non une fraude (code de sortie 1), et la sortie indique ce sur quoi cela repose : une réinitialisation annoncée (`history_signal: announced`), ou uniquement le numéro de grand livre du paquet (`pack_claim`, affiché comme **UNCONFIRMED**). Aucun des deux n’est une réussite.

La vérification hors ligne reste la valeur par défaut et n’effectue aucune requête réseau, elle fonctionne donc toujours dans un avion ou sur une machine de salle de classe verrouillée.

## Mode d’exécution à blanc

```bash
xrpl-camp start --dry-run
```

Aucun appel réseau, aucune écriture sur disque et aucune sortie trompeuse : la leçon 6 refuse explicitement de générer des artefacts. Le mode test peut *lire* l’état existant, mais ne modifie jamais quoi que ce soit.

## Point de terminaison et état

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

L’outil refuse les points de terminaison qu’il ne peut pas confirmer comme étant Testnet, avant de signer quoi que ce soit. Définissez `XRPL_CAMP_ALLOW_ANY_NETWORK=1` uniquement si vous comprenez ce que vous ciblez.

L’état est stocké par défaut dans `./.xrpl-camp` : une session appartient au dossier dans lequel vous l’avez exécutée. `XRPL_CAMP_HOME` remplace cela, et `xrpl-camp status --detail` affiche le chemin absolu résolu.

## Sécurité

Votre clé est stockée localement dans `.xrpl-camp/wallet.json` (accessible uniquement au propriétaire sur POSIX) et n’est jamais incluse dans le certificat ou le paquet de preuves : la génération refuse d’écrire un artefact contenant une clé.

Par défaut, cet outil utilise XRPL Testnet, où le test XRP n’a aucune valeur réelle, et refuse les points de terminaison non-Testnet, sauf si vous choisissez explicitement de ne pas le faire. Pas de télémétrie, pas d’analyse, pas de communication vers un serveur distant.

Voir [SECURITY.md](SECURITY.md).

## Modèle de menace

| Menace | Atténuation |
|--------|-----------|
| Clé divulguée dans un artefact | La génération effectue une vérification de la clé basée sur le `decode_seed` de xrpl-py et refuse d’écrire le fichier si la vérification échoue. |
| Clé enregistrée dans git | `.xrpl-camp/` est ignoré par git *dans ce dépôt* ; l’état est écrit dans votre répertoire de travail, vous pouvez donc l’ajouter à votre propre `.gitignore`. |
| Clé lisible par d’autres utilisateurs | Fichier de portefeuille 0600, répertoire d’état 0700 sur POSIX. |
| Un utilisateur copie une clé secrète dans un mémo public | Le texte du mémo est analysé pour détecter les chaînes de caractères ressemblant à une clé et est refusé avant la soumission. |
| Clé Testnet réutilisée sur Mainnet | Un avertissement est affiché lors de la création du portefeuille ; l’outil refuse par défaut les points de terminaison non-Testnet. |
| Altération du paquet de preuves | SHA-256 détecte les modifications mineures ; `--online` détecte une falsification après re-scellement en interrogeant le registre. |
| Vérification par rapport au point de terminaison d’un attaquant | `--online` n’utilise jamais le point de terminaison spécifié dans le paquet testé. |
| Diagnostics divulguant votre identité | `support-bundle` masque le répertoire personnel et le nom de compte. |

## Pour les ateliers et les salles de classe

- **Une commande par participant.** `npx`, `pipx` ou le conteneur : pas de configuration partagée.
- **L’échec est gratuit.** `xrpl-camp try` enseigne les modes d’échec sans rien dépenser, de sorte qu’un participant qui provoque intentionnellement une erreur en apprend davantage qu’un participant qui ne le fait pas.
- **Tri par le facilitateur.** `status --detail` affiche le portefeuille, le point de terminaison et le répertoire d’état. `self-check` teste la connexion réelle au lieu de signaler un simple « OK ».
- **Vérifiez toute la salle en même temps.** `proof verify <folder> --online` vérifie le paquet de chaque participant par rapport au registre.
- **Les limites de débit sont réelles.** Trente personnes utilisant un seul robinet atteindront la limite ; l’outil réessaie avec un délai et l’indique plutôt que de blâmer votre connexion Wi-Fi.

## Développement

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
bash scripts/verify.sh     # lint + tests + build + smoke
```

## Licence

MIT

---

Créé par [MCP Tool Shop](https://mcp-tool-shop.github.io/)
