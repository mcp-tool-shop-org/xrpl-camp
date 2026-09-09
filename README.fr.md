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
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Apprenez le fonctionnement du XRP Ledger en une seule session. Pas de comptes. Pas d’argent réel. Juste vous et le registre.

La plupart des tutoriels sur la blockchain enseignent des concepts. XRPL Camp vous fait _mettre_ ces concepts en pratique : créez un portefeuille, alimentez-le, écrivez un mémorandum permanent dans un registre public, vérifiez-le de manière indépendante, et repartez avec un enregistrement que n’importe qui peut vérifier par rapport au registre lui-même. L’ensemble du processus dure environ dix minutes.

Conçu pour les ateliers, les salles de classe et l’auto-apprentissage. Le processus guidé reprend là où vous vous êtes arrêté, une leçon infructueuse interrompt l’exécution au lieu de prétendre que tout s’est bien passé, et rien ne prétend que quelque chose s’est produit alors que ce n’était pas le cas.

## Pourquoi ceci plutôt qu’un tutoriel générique ?

- **De vraies transactions, pas des diapositives.** Vous écrivez dans un registre réel. Lorsque la leçon 5 indique « vérifiez-le vous-même », elle vous fournit un hachage et un lien vers un explorateur que n’importe qui peut vérifier.
- **Votre paiement crée un compte.** La leçon 4 n’est pas un simple transfert de test ; elle finance un deuxième compte qui n’existait pas un instant auparavant, et dont les clés vous appartiennent également.
- **L’échec fait partie du programme.** `xrpl-camp try` provoque intentionnellement des erreurs sur le réseau actif, puis vous montre quelles erreurs auraient entraîné des pertes financières et lesquelles sont gratuites, _avant_ que vous ne validiez quoi que ce soit.
- **Preuve que vous pouvez réellement vérifier.** Le paquet de preuves mentionne de vraies transactions et `proof verify --online` demande au registre si elles ont eu lieu. Personne ne peut falsifier cette partie.
- **Sécurité par conception.** Uniquement le testnet. Le XRP de test n’a aucune valeur. Votre clé de chiffrement ne quitte jamais votre appareil. Pas de télémétrie, pas d’analyse, pas de comptes.

## Installation

**Aucun Python requis** (télécharge un binaire précompilé) :

```bash
npx @mcptoolshop/xrpl-camp start
```

Avec Python :

```bash
pipx install xrpl-camp
```

Dans Docker, pour les ateliers où l’installation est la partie la plus difficile :

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> Montez un volume. Tout ce que vous créez (portefeuille, certificat, paquet de preuves) est écrit dans `/work`, et un conteneur non monté le supprime à la fermeture. L’image vous indique si vous l’avez oublié.

## Démarrage rapide

```bash
xrpl-camp start
```

Six leçons, dans l’ordre, reprenant si vous redémarrez :

1. **Modèle mental** : ce qu’est le XRPL, demandé au réseau actif plutôt qu’affirmé.
2. **Créer un portefeuille** : générer une paire de clés Testnet ; la clé de chiffrement reste sur votre appareil.
3. **Alimenter le portefeuille** : obtenir gratuitement du XRP de test auprès du robinet, et pourquoi une partie de celui-ci n’est pas utilisable.
4. **Envoyer un paiement** : écrivez votre mémorandum dans le registre, dans un paiement qui crée un compte.
5. **Vérifier la transaction** : recherchez ce que vous avez écrit et comparez-le à ce que vous avez tapé.
6. **Certificat** : un enregistrement que vous conservez et que vous pouvez prouver.

## Commandes

| Commande | Ce qu’elle fait |
|---------|-------------|
| `xrpl-camp start` | Processus guidé à travers les 6 leçons (reprend automatiquement) |
| `xrpl-camp start --memo "..."` | Fournir le message de la leçon 4 à l’avance, pour les exécutions scriptées ou non interactives |
| `xrpl-camp read` | Vos entrées, relues **à partir du registre** : pas à partir de cet appareil. |
| `xrpl-camp read <address>` | Ce que quelqu’un d’autre a écrit. Pas de clé, pas de connexion, pas d’autorisation. |
| `xrpl-camp read <hash>` | Une transaction, dans son intégralité. |
| `xrpl-camp try` | Provoquer intentionnellement une erreur sur le réseau actif. Ne signe rien, ne coûte rien. |
| `xrpl-camp status` | Liste de contrôle des progrès, avec les temps. |
| `xrpl-camp status --detail` | Vue pour l’animateur : portefeuille, point de terminaison, répertoire d’état, prochaine étape. |
| `xrpl-camp wallet create` / `show` | Créer ou afficher votre portefeuille Testnet. |
| `xrpl-camp fund` | Alimenter votre portefeuille via le robinet Testnet. |
| `xrpl-camp send --memo "hello"` | Envoyer un paiement de mémorandum à votre boîte de réception. |
| `xrpl-camp verify --tx <hash>` | Vérifier une transaction **que vous** avez envoyée. |
| `xrpl-camp certificate` | Générer le certificat + le paquet de preuves. |
| `xrpl-camp proof verify <file>` | Vérifier le hachage d’un paquet de preuves. Entièrement hors ligne. |
| `xrpl-camp proof verify <file> --online` | Demander également au registre si les transactions ont réellement eu lieu. |
| `xrpl-camp proof verify <folder>` | Vérifier chaque paquet dans un dossier, pour les animateurs. |
| `xrpl-camp reset` | Effacer tout l’état (nécessite de taper `RESET`). |
| `xrpl-camp self-check` | Diagnostiquer votre environnement **et** votre connexion au registre. |
| `xrpl-camp support-bundle` | Créer une archive zip de diagnostic pour les rapports de bogues. |

Indicateurs globaux : `--version`, `--dry-run`, `--yes` (non interactif), `--verbose` (détails techniques sur les erreurs).

## Ce que vous obtiendrez

- Un portefeuille Testnet financé, local et ignoré par Git.
- Un **deuxième compte qui n’existait pas avant que votre paiement ne le crée** : et dont les clés vous appartiennent également.
- Un mémorandum que vous avez choisi, enregistré de manière permanente et lisible de manière indépendante.
- Un certificat (`xrpl_camp_certificate.json`) : sûr à partager, sans clés privées.
- Un paquet de preuves (`xrpl_camp_proof_pack.json`) : mentionnant de vraies transactions que n’importe qui peut vérifier.

## À propos de cette preuve

Le paquet de preuves contient un hachage SHA-256. Ce hachage détecte une modification accidentelle. Il ne s’agit **pas** d’une signature, et en soi, il ne prouve pas que le paquet est authentique : n’importe qui peut modifier un champ et recalculer le hachage avec la même fonction publique que cet outil utilise.

Ce qui ne peut pas être falsifié, c’est le registre :

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

Il résout chaque transaction mentionnée dans le paquet et vérifie qu’elle existe, qu’elle a été envoyée par l’adresse du paquet, qu’elle contient le mémorandum que le paquet prétend contenir et qu’elle s’est terminée avec succès. Un paquet avec une adresse réécrite passe la vérification hors ligne du hachage et échoue à cette vérification.

Deux détails à connaître, car il est facile de se tromper :

- La vérification interroge toujours le Testnet public (ou `--rpc-url`), **jamais** le point de terminaison mentionné dans le paquet. Un paquet falsifié peut mentionner un serveur que son auteur contrôle.
- Le XRPL Testnet est périodiquement réinitialisé. Lorsque cela se produit, les transactions honnêtes cessent d’être résolues. Le paquet enregistre l’index du registre de chaque transaction, de sorte qu’une réinitialisation est signalée comme *non vérifiable* (code de sortie 3) plutôt que comme une fraude (code de sortie 1).

La vérification hors ligne reste la valeur par défaut et n’effectue aucune requête réseau, elle fonctionne donc toujours dans un avion ou sur un appareil de salle de classe verrouillé.

## Mode test

```bash
xrpl-camp start --dry-run
```

Aucune requête réseau, aucun enregistrement sur disque et aucune sortie trompeuse : la leçon 6 refuse explicitement de générer des artefacts. Le mode test peut *lire* l’état existant, mais ne modifie jamais rien.

## Point de terminaison et état

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

L’outil refuse les points de terminaison pour lesquels il ne peut pas confirmer qu’il s’agit du Testnet, avant de signer quoi que ce soit. Définissez `XRPL_CAMP_ALLOW_ANY_NETWORK=1` uniquement si vous comprenez ce que vous ciblez.

Par défaut, l’état est stocké dans `./.xrpl-camp` ; une session appartient au dossier dans lequel vous l’avez exécutée. `XRPL_CAMP_HOME` remplace ce paramètre, et `xrpl-camp status --detail` affiche le chemin absolu résolu.

## Sécurité

Votre clé privée est stockée localement dans `.xrpl-camp/wallet.json` (accessible uniquement au propriétaire sur POSIX) et n’est jamais incluse dans le certificat ou le paquet de preuve ; la génération refuse d’écrire un artefact qui en contiendrait une.

Par défaut, cet outil utilise le XRPL Testnet, où les XRP de test n’ont aucune valeur réelle, et il refuse les points de terminaison qui ne sont pas du Testnet, sauf si vous choisissez explicitement de ne pas l’utiliser. Pas de télémétrie, pas d’analyse, pas de communication vers un serveur distant.

Voir [SECURITY.md](SECURITY.md).

## Modèle de menace

| Menace | Atténuation |
|--------|-----------|
| Clé privée divulguée dans un artefact | La génération effectue une vérification de la clé privée basée sur le `decode_seed` de xrpl-py et refuse d’écrire le fichier si la vérification échoue. |
| Clé privée enregistrée dans git | `.xrpl-camp/` est ignoré par git *dans ce dépôt* ; l’état est écrit dans votre répertoire de travail, vous pouvez donc l’ajouter à votre propre `.gitignore`. |
| Clé privée accessible par d’autres utilisateurs | Fichier de portefeuille 0600, répertoire d’état 0700 sur POSIX |
| Un utilisateur copie un secret dans un mémo public | Le texte du mémo est analysé pour détecter les chaînes de caractères ressemblant à une clé privée et est refusé avant la soumission. |
| Clé privée du Testnet réutilisée sur le Mainnet | Un avertissement est affiché lors de la création du portefeuille ; l’outil refuse par défaut les points de terminaison qui ne sont pas du Testnet. |
| Altération du paquet de preuve | SHA-256 détecte les modifications mineures ; `--online` détecte une falsification en demandant au registre. |
| Vérification par rapport au point de terminaison d’un attaquant | `--online` n’utilise jamais le point de terminaison spécifié dans le paquet testé. |
| Diagnostics divulguant votre identité | `support-bundle` masque le répertoire personnel et le nom du compte. |

## Pour les ateliers et les salles de classe

- **Une commande par participant.** `npx`, `pipx` ou le conteneur ; pas de configuration partagée.
- **L’échec est gratuit.** `xrpl-camp try` enseigne les modes d’échec sans rien dépenser, de sorte qu’un participant qui casse quelque chose intentionnellement en apprend davantage qu’un participant qui ne le fait pas.
- **Tri par le facilitateur.** `status --detail` affiche le portefeuille, le point de terminaison et le répertoire d’état. `self-check` teste la connexion réelle au lieu de signaler un simple « OK ».
- **Vérification de toute la salle en une seule fois.** `proof verify <folder> --online` vérifie le paquet de chaque participant par rapport au registre.
- **Les limites de débit sont réelles.** Trente personnes accédant à un même robinet atteindront la limite ; l’outil réessaie avec un délai et l’indique plutôt que de blâmer votre connexion Wi-Fi.

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
