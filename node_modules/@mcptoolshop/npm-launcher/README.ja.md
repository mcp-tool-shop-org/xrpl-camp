<p align="center">
  <a href="README.md">English</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/npm-launcher/readme.png" width="400" alt="npm-launcher" />
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/npm-launcher/actions"><img src="https://github.com/mcp-tool-shop-org/npm-launcher/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/npm-launcher"><img src="https://img.shields.io/npm/v/@mcptoolshop/npm-launcher" alt="npm version"></a>
  <a href="https://github.com/mcp-tool-shop-org/npm-launcher/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
  <a href="https://mcp-tool-shop-org.github.io/npm-launcher/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

npm用の汎用的なGitHubリリースバイナリランチャーです。GitHub Releasesからプラットフォーム固有のバイナリをダウンロードし、ローカルにキャッシュし、SHA256チェックサムを検証し、引数をそのまま渡して実行します。

PythonのCLI（またはその他のコンパイル済みバイナリ）が、依存関係なしで`npx`で配布できるように設計されています。

## セキュリティと脅威モデル

`npm-launcher`はバイナリをダウンロードして実行します。以下に、何にアクセスし、何にアクセスしないかを説明します。

- **ネットワーク:** HTTPSのみを使用し、`github.com`とGitHubのCDNに接続します。他の宛先には接続しません。
- **ファイルシステム:** ローカルキャッシュのみに書き込みます（`~/.cache/mcptoolshop/`または`%LOCALAPPDATA%\mcptoolshop\`）。システムファイルを変更したり、キャッシュ以外のファイルを読み込んだりしません。
- **検証:** すべてのバイナリは、同じリリースに含まれる`checksums-<version>.txt`ファイルからのSHA256チェックサムと比較されます。不一致が見つかった場合、実行は中止され、ダウンロードしたファイルは削除されます。
- **テレメトリーはありません。** 機密情報の取り扱いもありません。認証情報も保存または送信しません。
- **権限:** 通常のユーザーがファイルシステムにアクセスしたり、HTTPSで外部に接続したりする権限以上の権限は必要ありません。

## 仕組み

```
npx @mcptoolshop/sovereignty tutorial
        │
        ▼
  wrapper sets config JSON
        │
        ▼
  npm-launcher resolves platform (linux-x64, darwin-arm64, etc.)
        │
        ▼
  checks local cache (~/.cache/mcptoolshop/<tool>/<version>/)
        │
        ├─ cached → run binary
        │
        └─ not cached:
             fetch checksums-<version>.txt from GitHub Release
             download <tool>-<version>-<os>-<arch>[.exe]
             verify SHA256
             cache + chmod +x
             run binary
```

## インストール

```bash
npm install @mcptoolshop/npm-launcher
```

このパッケージは、ラッパーパッケージ用のライブラリです。エンドユーザーは、このパッケージを直接インストールするのではなく、ラッパー（例：`npx @mcptoolshop/sovereignty`）をインストールします。

## 設定契約

ラッパーは、`MCPTOOLSHOP_LAUNCH_CONFIG`を介して純粋なJSONのみを渡します。関数や特殊な機能はありません。

| フィールド | 必須 | 例 | 説明 |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | はい | `"sovereignty"`        | バイナリのベース名 |
| `owner`    | はい | `"mcp-tool-shop-org"`  | GitHubの組織/ユーザー名 |
| `repo`     | はい | `"sovereignty"`        | GitHubのリポジトリ名 |
| `version`  | はい | `"1.4.0"`              | セマンティックバージョニング（`v`プレフィックスなし） |
| `tag`      | no       | `"v1.4.0"`             | Gitタグ（デフォルトは`v<バージョン>`） |
| `quiet`    | no       | `true`                 | プログレスメッセージを抑制 |

## アセットの命名規則

固定されています。すべてのツールは同じパターンに従います。

```
<toolName>-<version>-<os>-<arch><ext>
```

| プラットフォーム | アセットの例 |
|---------------|--------------------------------------|
| Linux x64 | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel | `sovereignty-1.4.0-darwin-x64`       |
| Windows x64 | `sovereignty-1.4.0-win-x64.exe`     |

チェックサムファイル：`checksums-<version>.txt`（GNU coreutils形式）。

## ラッパーの作成

ラッパーは、非常に小さなnpmパッケージ（約3つのファイル）です。

**package.json:**
```json
{
  "name": "@mcptoolshop/sovereignty",
  "version": "1.4.0",
  "bin": { "sovereignty": "bin/sovereignty.js" },
  "dependencies": { "@mcptoolshop/npm-launcher": "^1.0.0" }
}
```

**bin/sovereignty.js:**
```js
#!/usr/bin/env node
process.env.MCPTOOLSHOP_LAUNCH_CONFIG = JSON.stringify({
  toolName: "sovereignty",
  owner: "mcp-tool-shop-org",
  repo: "sovereignty",
  version: "1.4.0",
});
require("@mcptoolshop/npm-launcher/bin/mcptoolshop-launch.js");
```

完全なラッパーのテンプレートとCIワークフローについては、`examples/`ディレクトリを参照してください。

## 環境変数

| 変数 | 効果 |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | プログレスメッセージを抑制（エラーは表示されます） |

## サポートされているプラットフォーム

- Linux x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- Windows x64

## キャッシュの場所

| OS      | パス |
|---------|----------------------------------------------|
| Linux | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| Windows | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

作成者：<a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
