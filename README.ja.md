<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

一度で XRP Ledger をマスターしましょう。アカウントは不要です。実際のお金も不要です。あなたと台帳だけです。

ほとんどのブロックチェーンのチュートリアルは、概念を教えます。XRPL Camp は、実際にそれらを「実行」させます。つまり、ウォレットを作成し、資金を投入し、公開台帳に永続的なメモを書き込み、独立して検証し、誰でも台帳自体を参照して確認できる記録を持って終了します。この一連の流れには約 10 分かかります。

ワークショップ、教室、および自主学習用に設計されています。ガイダンスに沿って進むと、途中で停止した場合は、そこで再開します。失敗したレッスンは、実際には何も起こっていないと偽るのではなく、実行を停止します。

## 一般的なチュートリアルではなく、これを選ぶ理由

- **実際のトランザクション、スライドではありません。** 実際の台帳に書き込みます。レッスン 5 で「自分で検証してください」と言われた場合、誰でも確認できるハッシュとエクスプローラーへのリンクが提供されます。
- **あなたの支払いによって、アカウントが作成されます。** レッスン 4 は単なるお試し転送ではありません。それは、ほんの数分前に存在しなかった 2 番目のアカウントに資金を投入し、そのキーもあなたのものになります。
- **失敗はカリキュラムの一部です。** `xrpl-camp try` は、ライブネットワークに対して意図的に問題を発生させ、次に、どの失敗が費用がかかり、どの失敗が無料であるかを示します。これは、実際に送信ボタンを押す *前* に行われます。
- **実際に検証できることの証明。** 証明パックには実際のトランザクションの名前が記載されており、`proof verify --online` は台帳にそれらが実際に発生したかどうかを問い合わせます。この部分は誰も偽装できません。
- **設計による安全性。** Testnet のみを使用します。テスト XRP には価値がありません。あなたのシードは決してあなたのマシンから離れません。テレメトリー、分析、アカウントはありません。

## インストール

**Python は不要**（事前に構築されたバイナリをダウンロードします）：

```bash
npx @mcptoolshop/xrpl-camp start
```

Python を使用する場合（3.11、3.12、または 3.13）：

```bash
pipx install xrpl-camp
```

Docker を使用する場合 — インストールが難しいワークショップの場合：

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> ボリュームをマウントします。作成したすべてのもの（ウォレット、証明書、証明パック）は `/work` に書き込まれ、マウント解除されたコンテナーは終了時にそれらを破棄します。イメージは、忘れていないかどうかを教えてくれます。

## クイックスタート

```bash
xrpl-camp start
```

6 つのレッスンを順番に進め、再起動した場合でも再開します。

1. **メンタルモデル** — XRPL が何であるか。ライブネットワークに問い合わせて確認します。
2. **ウォレットの作成** — Testnet キーペアを生成します。シードはマシンに保存されます。
3. **ウォレットへの資金投入** — 無料のテスト XRP をファセットから取得し、そのうちのいくつかが使用できない理由を説明します。
4. **支払い** — メモを台帳に書き込み、アカウントを作成する支払いを実行します。
5. **トランザクションの検証** — 自分が書いたものを検索し、入力した内容と比較します。
6. **証明書** — 保持し、証明できる記録。

## コマンド

| コマンド | その機能 |
|---------|-------------|
| `xrpl-camp start` | 6 つすべてのレッスンをガイドに従って実行します（自動的に再開します）。 |
| `xrpl-camp start --memo "..."` | スクリプト化された、またはインタラクティブでない実行のために、レッスン 4 のメッセージを事前に提供します。 |
| `xrpl-camp read` | 入力内容を読み取り、**台帳から** 取得します。このマシンからではありません。 |
| `xrpl-camp read <address>` | 他の人が書いたもの。キー、ログイン、または権限は必要ありません。 |
| `xrpl-camp read <hash>` | 1 つのトランザクション全体。 |
| `xrpl-camp try` | ライブネットワークに対して、意図的に問題を発生させます。署名は行わず、費用もかかりません。 |
| `xrpl-camp reserve` | NFT をミントおよびバーンして、所有者のリザーブロックとリターンを監視します。 |
| `xrpl-camp status` | 進捗状況のチェックリスト（時間も表示されます）。 |
| `xrpl-camp status --detail` | ファシリテーターのビュー：ウォレット、エンドポイント、状態ディレクトリ、次の手順。 |
| `xrpl-camp wallet create` / `show` | Testnet ウォレットを作成または表示します。 |
| `xrpl-camp fund` | Testnet ファセットを通じてウォレットに資金を投入します。 |
| `xrpl-camp send --memo "hello"` | 自分のメールボックスにメモの支払いを送信します。 |
| `xrpl-camp verify --tx <hash>` | **自分が** 送信したトランザクションを検証します。 |
| `xrpl-camp certificate` | 証明書と証明パックを生成します（`--format text` は `.txt` の記念品を追加します）。 |
| `xrpl-camp proof verify <file>` | 証明パックのハッシュを確認します。完全にオフラインで実行できます。 |
| `xrpl-camp proof verify <file> --online` | トランザクションが実際に発生したかどうかを台帳にも問い合わせます（`--record` は日付付きのレシートを追加します）。 |
| `xrpl-camp proof verify <folder>` | フォルダー内のすべてのパックを検証します（ファシリテーター用）。 |
| `xrpl-camp reset` | すべての状態を消去します（`RESET` と入力する必要があります）。 |
| `xrpl-camp self-check` | 環境と台帳への接続を診断します。 |
| `xrpl-camp support-bundle` | バグ報告用の診断 zip ファイルを作成します。 |

グローバルフラグ：`--version`、`--dry-run`、`--yes`（非インタラクティブ）、`--verbose`（エラーに関する技術的な詳細）。

## 最終的に得られるもの

- 資金が投入された Testnet ウォレット（ローカルに保存され、gitignore されます）。
- **支払いによって作成された、それまで存在しなかった 2 番目のアカウント** — そのキーもあなたのものです。
- 選択したメモが、永続的に記録され、独立して読み取り可能になります。
- 証明書（`xrpl_camp_certificate.json`） — 安全に共有でき、秘密鍵は含まれません。
- 証明パック（`xrpl_camp_proof_pack.json`） — 実際のトランザクションの名前が記載されており、誰でも解決できます。

## その証明について

証明パックには SHA-256 ハッシュが含まれています。このハッシュは、偶発的な編集を検出します。これは署名ではなく、それ自体ではパックが本物であるとは証明されません。誰でもフィールドを変更し、このツールで使用されているのと同じ公開関数を使用してハッシュを再計算できます。

偽装できないのは台帳です。

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

これは、パックに記載されているすべてのトランザクションを解決し、それらが存在すること、パックのアドレスから送信されたこと、パックが主張するメモが含まれていること、および正常に完了したことを確認します。書き換えられたアドレスを持つパックは、オフラインのハッシュチェックには合格しますが、このチェックには合格しません。

覚えておくべき 2 つの点があります。どちらも簡単に間違える可能性があるためです。

- 検証は常に、公開 Testnet（または `--rpc-url`）に問い合わせます。**決して** パック内に記載されているエンドポイントには問い合わせません。偽造されたパックは、作成者が制御するサーバーを名前として指定できます。
- XRPL Testnet は定期的にリセットされます（次回は 2026 年 11 月 25 日）。その時点で、正直なトランザクションは解決されなくなります。エンドポイントが、トランザクションが記録された台帳を保持していない場合、結果は *検証不能*（終了コード 3）となり、詐欺（終了コード 1）とはなりません。出力には、その理由が記載されます。つまり、発表されたリセット（`history_signal: announced`）、またはパック自体の台帳番号（`pack_claim`、**UNCONFIRMED**として表示）のみです。どちらも合格ではありません。

オフライン検証はデフォルトのままであり、ネットワーク呼び出しは行われないため、飛行機の中やロックダウンされた教室のコンピューターでも引き続き機能します。

## ドライランモード

```bash
xrpl-camp start --dry-run
```

ネットワークへのアクセス、ディスクへの書き込み、誤解を招く可能性のある出力は一切行いません。レッスン6では、明示的に成果物の生成を拒否します。テスト実行では、既存の状態を読み込むことはできますが、いかなる変更も行いません。

## エンドポイントと状態

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

このツールは、署名を行う前に、エンドポイントがTestnetであることを確認できない場合、そのエンドポイントを拒否します。 `XRPL_CAMP_ALLOW_ANY_NETWORK=1`を設定するのは、それが何を指しているのかを理解している場合に限ります。

デフォルトでは、状態は`./.xrpl-camp`に保存されます。これは、実行したフォルダーに属します。`XRPL_CAMP_HOME`でそれを上書きし、`xrpl-camp status --detail`で解決された絶対パスを出力します。

## セキュリティ

シードはローカルの`.xrpl-camp/wallet.json`に保存され（POSIXでは所有者のみアクセス可能）、証明書や証明パックには決して含まれません。生成プロセスでは、シードを含む成果物の書き込みを拒否します。

このツールは、デフォルトでXRPL Testnetを使用します。テストのXRPには実際には意味がなく、明示的にオプトアウトしない限り、非Testnetエンドポイントは拒否されます。テレメトリー、分析、または外部への通信は行いません。

[SECURITY.md](SECURITY.md)を参照してください。

## 脅威モデル

| 脅威 | 緩和策 |
|--------|-----------|
| 成果物にシードが漏洩 | 生成プロセスでは、xrpl-pyの独自の`decode_seed`に基づいてシードチェックを実行し、シードが検出された場合はファイルの書き込みを拒否します。 |
| シードがgitにコミット | `.xrpl-camp/`は、このリポジトリではgitignoreされます。状態は作業ディレクトリに書き込まれるため、独自の`.gitignore`に追加してください。 |
| 他のユーザーがシードを読み取れる | ウォレットファイルは0600、状態ディレクトリは0700（POSIX）。 |
| 学習者が秘密情報をパブリックなメモに貼り付ける | メモのテキストは、シードのような文字列がないかスキャンされ、送信前に拒否されます。 |
| TestnetシードがMainnetで再利用 | ウォレット作成時に警告が表示されます。デフォルトでは、このツールは非Testnetエンドポイントを拒否します。 |
| 証明パックの改ざん | SHA-256は、軽微な編集を検出し、`--online`は、台帳に問い合わせることで、再シールされた偽造を検出します。 |
| 攻撃者のエンドポイントに対して検証 | `--online`は、テスト対象のパックに記載されているエンドポイントを一切使用しません。 |
| 診断によって身元が漏洩 | `support-bundle`は、ホームディレクトリとアカウント名を削除します。 |

## ワークショップおよび教室向け

- **学習者ごとに1つのコマンド。** `npx`、`pipx`、またはコンテナーを使用します。共有設定は行いません。
- **失敗は無料です。** `xrpl-camp try`は、費用をかけずに失敗モードを教えます。そのため、意図的に何かを壊した学習者は、そうでない学習者よりも多くのことを学びます。
- **ファシリテーターによるトリアージ。** `status --detail`は、ウォレット、エンドポイント、および状態ディレクトリを表示します。`self-check`は、楽観的なOKを報告するのではなく、実際の接続をプローブします。
- **一度に部屋全体を検証します。** `proof verify <folder> --online`は、すべての学習者のパックを台帳に対してチェックします。
- **レート制限は有効です。** 30人が1つのFaucetにアクセスすると、制限に達します。このツールは、バックオフで再試行し、その旨を通知します。Wi-Fiを責めることはありません。

## 開発

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
bash scripts/verify.sh     # lint + tests + build + smoke
```

## ライセンス

MIT

---

[MCP Tool Shop](https://mcp-tool-shop.github.io/)によって作成されました。
