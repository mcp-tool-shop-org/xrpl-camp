<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/xrpl-camp/readme.png" width="400" alt="XRPL Camp">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/xrpl-camp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

一次性学习 XRP 区块链技术。无需注册账户，无需使用真钱。只需您和区块链技术本身。

XRPL Camp 课程将带您了解 6 个主题，从“什么是账本？”到“如何创建并充值钱包、完成支付以及生成可移植的证书”，整个过程大约需要 10 分钟。

## 安装

```bash
pipx install xrpl-camp
```

或者，可以使用 pip 进行安装：

```bash
pip install xrpl-camp
```

## 快速入门指南

```bash
xrpl-camp start
```

这会引导您完成所有6个课程的学习。

1. **概念模型**—— 了解 XRPL 的构成（账户、余额、交易、备忘录）。
2. **创建钱包**—— 生成一个测试网络密钥对。
3. **充值钱包**—— 从测试水龙头获取免费的测试版 XRP。
4. **发送支付**—— 向账本添加一条备忘录（自付，1 单位）。
5. **验证交易**—— 查找您添加的内容。
6. **证书**—— 获取一份可携带、可验证的您所执行操作的记录。

## 命令

| 命令。 | 它的作用/功能。 |
|---------|-------------|
| `xrpl-camp start` | 全程引导，学习所有6个课程。 |
| `xrpl-camp start --dry-run` | 在不使用网络连接的情况下，完整运行整个流程。 |
| `xrpl-camp wallet create` | 创建测试网络钱包。 |
| `xrpl-camp wallet show` | 显示您的钱包地址。 |
| `xrpl-camp fund` | 通过测试网络的水龙头（faucet）为您的钱包充值。 |
| `xrpl-camp fund --dry-run` | 看看资金的投入会带来什么影响，但目前没有相关网络或平台。 |
| `xrpl-camp send --memo "hello"` | 发送带有自定义备注的自付款。 |
| `xrpl-camp send --dry-run` | 模拟支付。 |
| `xrpl-camp verify --tx <hash>` | 验证账本上的交易。 |
| `xrpl-camp certificate` | 生成证书和证明文件包。 |
| `xrpl-camp reset` | 清除所有数据（需要手动确认）。 |

## 最终的结果

- 一个已配置的测试网络钱包（`.xrpl-camp/wallet.json`，本地文件，不应被 Git 跟踪）。
- 在 XRPL 测试网络上已确认的支付记录。
- 一份验证报告，详细显示账本中记录的内容。
- 一份证书（`xrpl_camp_certificate.json`），可以安全分享，不包含任何私钥。
- 一份证明包（`xrpl_camp_proof_pack.json`），具有防篡改功能，并经过 SHA-256 哈希处理。

## 模拟运行模式

每个网络命令都支持 `--dry-run` 参数。它会打印出如果执行该命令会发生的情况，而不会实际进行任何网络调用或修改任何状态。这对于增强信心和进行调试非常有用。

## 试用包

“防篡改记录包”是您所执行的所有操作的可靠记录，具有防篡改功能。

- 钱包地址和网络信息
- 课程完成的时间戳
- 交易ID以及对应的区块浏览器链接
- 工具版本
- 整个内容的SHA-256哈希值

任何人都可以验证文件的哈希值，以确认文件是否已被修改。

## 端点覆盖/端点重写

默认情况下，XRPL Camp 使用公共的 XRPL 测试网络节点。如果需要使用不同的节点地址，请按照以下步骤操作：

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
xrpl-camp fund
```

## 安全

您的助记词（私钥）存储在本地，并且永远不会包含在证书或证明包中。
此工具仅使用 XRPL **测试网络**——测试用的 XRP 没有实际价值。
没有数据收集、没有分析功能，也没有任何远程连接——所有网络连接都仅限于 XRPL 测试网络。

请参阅 [SECURITY.md](SECURITY.md) 文件以获取详细信息。

## 威胁模型

| 威胁。 | 减缓措施。 |
|--------|-----------|
| 通过证书进行的种子泄露。 | 证书生成过程明确不包含种子信息；`certificate_has_seed()` 安全检查用于验证这一点。 |
| 通过密封包装进行的种子泄漏检测。 | 生成证明包时，不包含种子信息；`proof_pack_has_seed()` 函数用于安全检查。 |
| 将代码提交到 Git 仓库。 | `.xrpl-camp/` 目录被 Git 忽略；`wallet show` 命令始终不会显示助记词。 |
| 主网中重用测试网的初始节点信息。 | 创建钱包时显示的警告信息。 |
| 备忘录内容曝光。 | 所有备忘录默认情况下都是公开的；用户在发送前会收到提醒。 |
| 篡改样本包。 | SHA-256 完整性哈希值；`verify_proof_pack()` 函数用于检测数据是否被修改。 |

## 发展

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
uv run ruff check .
uv run pytest tests/ -v
```

## 许可

麻省理工学院。

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建。
