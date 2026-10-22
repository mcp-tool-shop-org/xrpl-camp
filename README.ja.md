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

XRP Ledgerを一度でマスターしましょう。アカウントは不要です。実際の資金も不要です。あなたとLedgerだけです。

ほとんどのブロックチェーンのチュートリアルは概念を教えます。XRPL Campでは、実際にウォレットを作成したり、資金を投入したり、パブリックLedgerに永続的なメモを書き込んだり、独立して検証したりして、誰でもLedger自体を参照して確認できる記録を作成します。一連のプロセスには約10分かかります。

ワークショップ、教室、自己学習用に設計されています。ガイダンスに沿って進めると、途中で停止した場合はそこから再開し、失敗したレッスンは実行を停止するだけで、実際には何も起こっていないと表示することはありません。

## 一般的なチュートリアルではなく、これを選ぶ理由

- **実際のトランザクション、スライドではありません。** 実際のLedgerに書き込みます。レッスン5で「自分で検証してください」と言われた場合、誰でも確認できるハッシュとエクスプローラーへのリンクが提供されます。
- **あなたの支払いによってアカウントが作成されます。** レッスン4は単なるデモの送金ではありません。それは、ほんの数分前に存在しなかった2番目のアカウントに資金を投入し、そのキーもあなたのものであり、そのアカウントを作成します。
- **失敗はカリキュラムの一部です。** `xrpl-camp try`は、ライブネットワークに対して意図的に問題を発生させ、どの失敗が費用を発生させ、どの失敗が無料であるかを示します。これは、実際に送信ボタンを押す*前*に行われます。
- **実際に検証できる証拠。** 証拠パックには実際のトランザクションが記載されており、`proof verify --online`はLedgerにそれらが実際に発生したかどうかを問い合わせます。この部分は誰も偽装できません。
- **設計により安全。** テストネットのみを使用します。テスト用XRPには価値がありません。あなたのシードは決してあなたのマシンから離れません。テレメトリー、分析、アカウントはありません。

## インストール

**Pythonは不要**（事前にビルドされたバイナリをダウンロードします）。

```bash
npx @mcptoolshop/xrpl-camp start
```

Pythonを使用する場合（3.11、3.12、または3.13）。

```bash
pipx install xrpl-camp
```

Dockerを使用する場合 — インストールが難しいワークショップ向け。

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> ボリュームをマウントします。作成したすべてのもの（ウォレット、証明書、証拠パック）は`/work`に書き込まれ、マウントされていないコンテナは終了時にそれらを破棄します。イメージは、忘れていないかどうかを通知します。

## クイックスタート

```bash
xrpl-camp start
```

6つのレッスンを順番に進め、再起動した場合でも再開します。

1. **メンタルモデル** — XRPLとは何か。ライブネットワークに問い合わせることで確認します。
2. **ウォレットの作成** — テストネットのキーペアを生成します。シードはあなたのマシンに保存されます。
3. **ウォレットへの資金投入** — 無料のテスト用XRPをFaucetから取得し、そのうちのいくつかが使用できない理由を説明します。
4. **支払い送信** — メモをLedgerに書き込み、アカウントを作成する支払いを実行します。
5. **トランザクションの検証** — 書き込んだ内容を確認し、入力した内容と比較します。
6. **証明書** — 保持し、証明できる記録。

## コマンド

| コマンド | その機能 |
|---------|-------------|
| `xrpl-camp start` | 6つのレッスンすべてをガイドに従って実行します（自動的に再開します）。 |
| `xrpl-camp start --memo "..."` | スクリプト化された、またはインタラクティブでない実行のために、レッスン4のメッセージを事前に提供します。 |
| `xrpl-camp read` | あなたの入力内容を、このマシンではなく、**Ledgerから読み取ります**。 |
| `xrpl-camp read <address>` | 他の人が書いたもの。キー、ログイン、または権限は必要ありません。 |
| `xrpl-camp read <hash>` | 1つのトランザクション全体。 |
| `xrpl-camp try` | ライブネットワークに対して意図的に問題を発生させます。署名は行わず、費用もかかりません。 |
| `xrpl-camp reserve` | NFTを生成・発行し、所有者がロックを予約し、その後返却する様子を観察する。 |
| `xrpl-camp status` | 進捗状況のチェックリスト（時間も表示されます）。 |
| `xrpl-camp status --detail` | ファシリテーターのビュー：ウォレット、エンドポイント、状態ディレクトリ、次のステップ。 |
| `xrpl-camp wallet create` / `show` | テストネットウォレットを作成または表示します。 |
| `xrpl-camp fund` | テストネットFaucetからウォレットに資金を投入します。 |
| `xrpl-camp send --memo "hello"` | メモの支払いをあなたのメールボックスに送信します。 |
| `xrpl-camp verify --tx <hash>` | **あなたが**送信したトランザクションを検証します。 |
| `xrpl-camp certificate` | 証明書と証明書パックを生成する（`--format text`は記念品として`.txt`を追加する）。 |
| `xrpl-camp proof verify <file>` | 証拠パックのハッシュを確認します。完全にオフラインで実行できます。 |
| `xrpl-camp proof verify <file> --online` | また、取引が実際に発生したかどうかを台帳に確認する（`--record`は日付付きの領収書を添付する）。 |
| `xrpl-camp proof verify <folder>` | フォルダー内のすべてのパックを検証します（ファシリテーター向け）。 |
| `xrpl-camp reset` | すべての状態を消去します（`RESET`と入力する必要があります）。 |
| `xrpl-camp self-check` | あなたの環境**と**Ledgerへの接続を診断します。 |
| `xrpl-camp support-bundle` | バグ報告用の診断用ZIPファイルを書き出します。 |

グローバルフラグ：`--version`、`--dry-run`、`--yes`（非インタラクティブ）、`--verbose`（エラーに関する技術的な詳細）。

## 最終的に得られるもの

- 資金が投入されたテストネットウォレット（ローカルに保存され、Gitで無視されます）。
- **あなたの支払いによって作成された、それまで存在しなかった2番目のアカウント** — そして、そのキーもあなたのものであり、そのアカウントを作成します。
- あなたが選択したメモが、永続的に記録され、独立して読み取り可能。
- 証明書（`xrpl_camp_certificate.json`） — 共有しても安全で、秘密鍵は含まれません。
- 証拠パック（`xrpl_camp_proof_pack.json`） — 誰でも解決できる実際のトランザクションをリストアップします。

## その証拠について

証拠パックにはSHA-256ハッシュが含まれています。このハッシュは、偶発的な編集を検出します。これは署名**ではなく**、それ自体ではパックが本物であるとは証明されません。誰でもフィールドを変更し、同じパブリック関数を使用してハッシュを再計算できます。

偽装できないのはLedgerです。

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

パックにリストされているすべてのトランザクションを解決し、それらが存在するか、パックのアドレスから送信されたか、パックが主張するメモが含まれているか、正常に完了したかを確認します。書き換えられたアドレスを持つパックは、オフラインのハッシュチェックには合格しますが、このチェックには合格しません。

知っておくべき2つの詳細があります。どちらも簡単に間違える可能性があるためです。

- 検証は常にパブリックなテストネット（または`--rpc-url`）に問い合わせます。パック内に記載されているエンドポイントには**決して**問い合わせません。偽造されたパックは、作成者が制御するサーバーを名前として指定できます。
- XRPLテストネットは定期的にリセットされます。その場合、正直なトランザクションは解決されなくなります。パックは各トランザクションのLedgerインデックスを記録するため、リセットされた場合、詐欺（終了コード1）としてではなく、検証不能（終了コード3）として報告されます。

オフライン検証はデフォルトのままであり、ネットワーク呼び出しは行われないため、飛行機の中やロックダウンされた教室のコンピューターでも引き続き機能します。

## ドライランモード

```bash
xrpl-camp start --dry-run
```

ネットワーク呼び出し、ディスクへの書き込み、誤解を招く可能性のある出力は行いません。レッスン6では、明示的にアーティファクトの生成を拒否します。ドライランは既存の状態を*読み取る*ことはできますが、何も変更することはありません。

## エンドポイントと状態

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

このツールは、署名を行う前に、テストネットであると確認できないエンドポイントを拒否します。`XRPL_CAMP_ALLOW_ANY_NETWORK=1`を設定する場合は、それが指す先を理解している場合にのみ設定してください。

デフォルトでは、状態は`./.xrpl-camp`に保存されます。これは、実行したフォルダーに属します。`XRPL_CAMP_HOME`はこれを上書きし、`xrpl-camp status --detail`は解決された絶対パスを出力します。

## セキュリティ

シードはローカルの`.xrpl-camp/wallet.json`に保存されます（POSIXでは所有者のみアクセス可能）。証明書やプルーフパックには決して含まれません。生成プロセスは、シードを含む成果物の書き込みを拒否します。

このツールは**デフォルトで**XRPLテストネットを使用します。テストネットのXRPには実際には価値がなく、明示的にオプトアウトしない限り、テストネット以外のエンドポイントを拒否します。テレメトリ、分析、または外部への通信は行いません。

[SECURITY.md](SECURITY.md)を参照してください。

## 脅威モデル

| 脅威 | 緩和策 |
|--------|-----------|
| シードが成果物に漏洩 | 生成プロセスは、xrpl-pyの`decode_seed`に基づいてシードチェックを実行し、問題が発生した場合は**ファイルの書き込みを拒否します**。 |
| シードがGitにコミット | `.xrpl-camp/`は、このリポジトリではGitで無視されます。状態は作業ディレクトリに書き込まれるため、独自の`.gitignore`に追加してください。 |
| シードが他のユーザーによって読み取れる | ウォレットファイルは0600、状態ディレクトリはPOSIXでは0700 |
| 学習者が秘密を公開メモに貼り付ける | メモテキストは、シードのような文字列がないかスキャンされ、送信前に拒否されます。 |
| テストネットのシードがメインネットで再利用 | ウォレット作成時に警告が表示されます。ツールはデフォルトでテストネット以外のエンドポイントを拒否します。 |
| プルーフパックの改ざん | SHA-256は、単純な編集を検出し、`--online`は、台帳に問い合わせることで、再シールされた偽造を検出します。 |
| 攻撃者のエンドポイントに対して検証 | `--online`は、テスト中のパックに記載されているエンドポイントを一切使用しません。 |
| 診断によって身元が漏洩 | `support-bundle`は、ホームディレクトリとアカウント名を削除します。 |

## ワークショップおよび教室向け

- **学習者ごとに1つのコマンド。** `npx`、`pipx`、またはコンテナを使用します。共有設定は行いません。
- **失敗は無料です。** `xrpl-camp try`は、費用をかけずに失敗モードを教えます。そのため、意図的に何かを壊した学習者は、そうでない学習者よりも多くのことを学びます。
- **ファシリテーターによるトリアージ。** `status --detail`は、ウォレット、エンドポイント、および状態ディレクトリを表示します。`self-check`は、楽観的なOKを報告するのではなく、実際の接続をプローブします。
- **一度に部屋全体を検証します。** `proof verify <folder> --online`は、すべての学習者のパックを台帳に対してチェックします。
- **レート制限は有効です。** 30人が1つのFaucetにアクセスすると、制限に達します。ツールはバックオフで再試行し、その旨を通知します。Wi-Fiを責めることはありません。

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

[MCP Tool Shop](https://mcp-tool-shop.github.io/)によって作成
