<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

XRP Ledgerについて、一度の操作で学べます。アカウントも、実際の資金も不要です。あなたとLedgerだけで学習を進めます。

XRPL Campでは、6つのレッスンを通して学習します。内容は、「Ledgerとは何か？」から始まり、資金を投入したウォレット、確認済みの支払い、そしてポータブルな証明書まで、約10分で理解できます。

## インストール

```bash
pipx install xrpl-camp
```

または、pipを使用する場合：

```bash
pip install xrpl-camp
```

## クイックスタート

```bash
xrpl-camp start
```

このコマンドを実行すると、6つのレッスンを順番に進めます。

1. **メンタルモデル** — XRPLとは何か（アカウント、残高、トランザクション、メモ）
2. **ウォレット作成** — テストネットのキーペアを生成
3. **ウォレットへの資金投入** — 無料のテストXRPをFaucetから取得
4. **支払い送信** — Ledgerにメモを送信（自己支払い、1滴）
5. **トランザクションの確認** — 送信した内容を確認
6. **証明書** — 行ったことの、安全に共有できる記録を取得

## コマンド

| コマンド | 機能 |
|---------|-------------|
| `xrpl-camp start` | 6つのレッスンを順番に進める |
| `xrpl-camp start --dry-run` | ネットワーク接続なしで、一連の流れを実行 |
| `xrpl-camp wallet create` | テストネットのウォレットを作成 |
| `xrpl-camp wallet show` | ウォレットのアドレスを表示 |
| `xrpl-camp fund` | テストネットのFaucetからウォレットに資金を投入 |
| `xrpl-camp fund --dry-run` | 資金投入の効果をシミュレーション（ネットワーク接続なし） |
| `xrpl-camp send --memo "hello"` | カスタムメモ付きの自己支払いを送信 |
| `xrpl-camp send --dry-run` | 支払いをシミュレーション |
| `xrpl-camp verify --tx <hash>` | Ledger上のトランザクションを確認 |
| `xrpl-camp certificate` | 証明書と証明パックを生成 |
| `xrpl-camp reset` | すべての状態をクリア（確認が必要） |

## 最終的に得られるもの

- 資金が投入されたテストネットのウォレット (`.xrpl-camp/wallet.json` — ローカル、Gitで管理されない)
- XRPLテストネット上での支払い完了
- Ledgerに記録された内容を正確に示した検証レポート
- 証明書 (`xrpl_camp_certificate.json`) — 安全に共有可能、秘密鍵は含まれない
- 証明パック (`xrpl_camp_proof_pack.json`) — 改ざん防止、SHA-256ハッシュで保護

## ドライランモード

ネットワーク接続が必要なコマンドには、`--dry-run`オプションが利用可能です。これにより、ネットワーク接続を行わずに、何が起こるかをシミュレーションできます。これは、自信を高めたり、デバッグしたりするのに役立ちます。

## 証明パック

証明パックは、あなたが実行したすべてのことの、改ざん防止された記録です。

- ウォレットのアドレスとネットワーク
- レッソンの完了タイムスタンプ
- エクスプローラーへのリンク付きのトランザクションID
- ツールのバージョン
- コンテンツ全体のSHA-256ハッシュ

誰でもハッシュを検証することで、ファイルが編集されていないことを確認できます。

## エンドポイントの変更

デフォルトでは、XRPL CampはパブリックなXRPLテストネットノードを使用します。別のエンドポイントを使用するには、以下のように設定します。

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```

## セキュリティ

あなたのシード（秘密鍵）はローカルに保存され、証明書や証明パックには一切含まれません。
このツールは、XRPL **テストネット**のみを使用します。テストXRPには実際の価値はありません。
テレメトリー、分析、自動報告機能はありません。ネットワーク接続は、XRPLテストネットのみが行います。

詳細は、[SECURITY.md](SECURITY.md) を参照してください。

## 脅威モデル

| 脅威 | 対策 |
|--------|-----------|
| 証明書からのシード漏洩 | 証明書の生成時に、シードが明示的に除外されます。`certificate_has_seed()`による安全性のチェックも行われます。 |
| 証明パックからのシード漏洩 | 証明パックの生成時に、シードが除外されます。`proof_pack_has_seed()`による安全性のチェックも行われます。 |
| Gitへのシードの保存 | `.xrpl-camp/` はGitで管理対象から除外されます。`wallet show` コマンドでシードを表示することはありません。 |
| テストネットのシードをメインネットで使用 | ウォレット作成時に警告が表示されます。 |
| メモの内容の公開 | すべてのメモは、設計上公開されます。送信前に、ユーザーに警告が表示されます。 |
| 証明パックの改ざん | SHA-256による整合性チェックが行われています。`verify_proof_pack()` で改ざんを検出できます。 |

## 開発

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
uv run ruff check .
uv run pytest tests/ -v
```

## ライセンス

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/) によって作成されました。
