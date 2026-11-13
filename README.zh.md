<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

一次性掌握 XRP Ledger。无需注册账户。无需使用真实货币。只有你和账本。

大多数区块链教程都是讲解概念。XRPL Camp 让你_实际操作_——创建一个钱包，为其充值，向公共账本中写入一条永久消息，独立验证，然后带着一份任何人都可以对照账本进行核对的记录离开。整个过程大约需要十分钟。

专为研讨会、课堂和自学而设计。引导流程会从你上次停止的地方继续，如果某个环节失败，它会停止运行，而不是假装一切正常，并且不会声称发生了实际上没有发生的事情。

## 为什么选择这个，而不是通用的教程？

- **真实的交易，而不是幻灯片。** 你会向实际的账本写入数据。当第五课说“自己验证一下”时，它会给你一个哈希值和一个浏览器链接，任何人都可以用它来验证。
- **你的付款会创建一个账户。** 第四课不是一个简单的模拟转账——它会为之前不存在的第二个账户充值，并且该账户的密钥也是你的。
- **失败也是课程的一部分。** `xrpl-camp try` 会故意在实际网络上进行一些操作，然后向你展示哪些失败会导致损失，哪些是免费的——在你真正点击发送之前。
- **你可以实际验证。** 证明包会列出真实的交易，并且 `proof verify --online` 会询问账本这些交易是否真的发生了。没有人可以伪造这一部分。
- **从设计上来说是安全的。** 仅使用 Testnet。测试 XRP 没有价值。你的助记词永远不会离开你的设备。没有遥测数据，没有分析数据，没有账户。

## 安装

**不需要 Python**（下载预构建的二进制文件）：

```bash
npx @mcptoolshop/xrpl-camp start
```

使用 Python（3.11、3.12 或 3.13）：

```bash
pipx install xrpl-camp
```

在 Docker 中——用于研讨会，其中安装是难点：

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> 挂载一个卷。你创建的所有内容——钱包、证书、证明包——都会被写入 `/work`，并且未挂载的容器会在退出时删除这些内容。该镜像会告诉你是否忘记了挂载。

## 快速入门

```bash
xrpl-camp start
```

六个课程，按顺序进行，如果重新启动，会从上次停止的地方继续：

1. **思维模型**——什么是 XRPL，通过询问实际网络来了解，而不是简单地断言。
2. **创建钱包**——生成一个 Testnet 密钥对；助记词保存在你的设备上。
3. **充值钱包**——从水龙头获取免费的测试 XRP，以及为什么其中一部分不能被使用。
4. **发送付款**——将你的消息写入账本，以创建一个账户的付款。
5. **验证交易**——查找你写入的内容，并将其与你输入的内容进行比较。
6. **证书**——你保存的记录，你可以证明。

## 命令

| 命令 | 作用 |
|---------|-------------|
| `xrpl-camp start` | 引导完成所有 6 个课程（自动恢复） |
| `xrpl-camp start --memo "..."` | 提前提供第四课的消息，用于脚本化或非交互式运行 |
| `xrpl-camp read` | 你的条目，从**账本**上读取——而不是从这台机器上读取 |
| `xrpl-camp read <address>` | 其他人写入的内容。没有密钥，没有登录，没有权限 |
| `xrpl-camp read <hash>` | 一笔完整的交易 |
| `xrpl-camp try` | 故意在实际网络上进行破坏。不签名，不产生费用 |
| `xrpl-camp reserve` | 铸造和销毁一个 NFT，以观察所有者储备锁定的过程和返回 |
| `xrpl-camp status` | 进度检查表，带有时间 |
| `xrpl-camp status --detail` | 指导者视图：钱包、端点、状态目录、下一步 |
| `xrpl-camp wallet create` / `show` | 创建或显示你的 Testnet 钱包 |
| `xrpl-camp fund` | 通过 Testnet 水龙头为你的钱包充值 |
| `xrpl-camp send --memo "hello"` | 向你的邮箱发送一条消息付款 |
| `xrpl-camp verify --tx <hash>` | 验证你发送的交易 |
| `xrpl-camp certificate` | 生成证书 + 证明包（`--format text` 添加一个 `.txt` 纪念品） |
| `xrpl-camp proof verify <file>` | 检查证明包的哈希值。完全离线 |
| `xrpl-camp proof verify <file> --online` | 同时询问账本这些交易是否真的发生了（`--record` 会附加一个带有日期的收据） |
| `xrpl-camp proof verify <folder>` | 验证文件夹中的每个包——用于指导者 |
| `xrpl-camp reset` | 擦除所有状态（需要输入 `RESET`） |
| `xrpl-camp self-check` | 诊断你的环境**以及**你与账本的连接 |
| `xrpl-camp support-bundle` | 为错误报告编写一个诊断压缩包 |

全局标志：`--version`、`--dry-run`、`--yes`（非交互式）、`--verbose`（技术细节，关于错误）。

## 你最终会得到什么

- 一个已充值的 Testnet 钱包，本地存储并被 git 忽略
- **一个在你付款之前不存在的第二个账户**——并且该账户的密钥也是你的
- 你选择的消息，永久记录且可以独立读取
- 一个证书（`xrpl_camp_certificate.json`）——可以安全地共享，不包含私钥
- 一个证明包（`xrpl_camp_proof_pack.json`）——列出真实的交易，任何人都可以验证

## 关于该证明

证明包包含一个 SHA-256 哈希值。该哈希值可以检测到意外的编辑。它**不是**一个签名，并且本身并不能证明该包是真实的——任何人都可以更改一个字段，并使用与此工具使用的相同的公共函数重新计算哈希值。

无法伪造的是账本：

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

它会解析包中列出的每笔交易，并检查它是否存在、是否由包的地址发送、是否包含包声明的消息，以及是否成功完成。一个具有重写地址的包，可以通过离线哈希检查，但会失败此检查。

有两个细节值得了解，因为两者都很容易出错：

- 验证始终查询公共 Testnet（或 `--rpc-url`），**从不**查询包中命名的端点。伪造的包可以命名一个由其作者控制的服务器。
- XRPL Testnet 会定期重置（下次在 2026-11-25）。当发生这种情况时，真实的交易将停止解析。如果端点不保存记录交易的账本，结果将是*无法验证*（退出代码 3），而不是欺诈（退出代码 1），并且输出会说明它依赖于什么：一个已宣布的重置（`history_signal: announced`），或者仅是包自身的账本编号（`pack_claim`，显示为**UNCONFIRMED**）。两者都不是通过。

离线验证仍然是默认设置，并且不进行任何网络调用，因此它仍然可以在飞机上或锁定的课堂机器上工作。

## 模拟模式

```bash
xrpl-camp start --dry-run
```

不进行任何网络调用、不进行任何磁盘写入，也不产生任何误导性输出——第 6 课明确禁止生成任何工件。模拟运行可能会*读取*现有状态，但绝不会修改任何内容。

## 端点和状态

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

该工具在签名之前，会拒绝那些无法确认是否为 Testnet 的端点。仅在您了解要指向的目标时，才设置 `XRPL_CAMP_ALLOW_ANY_NETWORK=1`。

默认情况下，状态存储在 `./.xrpl-camp` 中——某个会话属于您运行它的文件夹。`XRPL_CAMP_HOME` 会覆盖此设置，而 `xrpl-camp status --detail` 会打印解析后的绝对路径。

## 安全性

您的种子存储在本地的 `.xrpl-camp/wallet.json` 中（仅所有者可访问，位于 POSIX），并且绝不会包含在证书或证明包中——生成过程会拒绝写入包含种子的工件。

此工具**默认使用** XRPL Testnet，其中测试 XRP 没有实际意义，并且除非您明确选择退出，否则会拒绝非 Testnet 端点。不收集遥测数据、不进行分析，也不会进行任何“回传”操作。

请参阅 [SECURITY.md](SECURITY.md)。

## 威胁模型

| 威胁 | 缓解措施 |
|--------|-----------|
| 种子泄露到工件中 | 生成过程会运行基于 xrpl-py 自身的 `decode_seed` 的种子检查，如果检查失败，则**拒绝写入文件**。 |
| 种子提交到 git | `.xrpl-camp/` 在此仓库中被 git 忽略；状态写入您的工作目录，因此请将其添加到您自己的 `.gitignore` 中。 |
| 其他用户可以读取种子 | 钱包文件权限设置为 0600，状态目录权限设置为 0700（位于 POSIX）。 |
| 学习者将密钥粘贴到公共备忘录中 | 在提交之前，备忘录文本会扫描是否存在类似种子的字符串，并拒绝。 |
| 在 Mainnet 上重复使用 Testnet 种子 | 在创建钱包时发出警告；该工具默认拒绝非 Testnet 端点。 |
| 篡改证明包 | SHA-256 检测到轻微的编辑；`--online` 通过向账本询问来检测重新密封的伪造。 |
| 针对攻击者的端点进行验证 | `--online` 绝不会使用正在测试的包中指定的端点。 |
| 诊断信息泄露您的身份 | `support-bundle` 会删除主目录和帐户名。 |

## 用于研讨会和课堂

- **每个学习者使用一个命令。** `npx`、`pipx` 或容器——没有共享设置。
- **失败是免费的。** `xrpl-camp try` 可以在不花费任何成本的情况下教授失败模式，因此，故意破坏某些东西的学习者比不破坏的学习者学得更多。
- **由指导者进行分类。** `status --detail` 显示钱包、端点和状态目录。`self-check` 探测实际连接，而不是报告一个乐观的“OK”。
- **一次性验证整个房间。** `proof verify <folder> --online` 检查每个学习者的包是否与账本一致。
- **速率限制是真实的。** 三十个人同时访问一个“水龙头”（faucet）会达到限制；该工具会进行重试，并进行退避，并会说明这一点，而不是责怪您的 Wi-Fi。

## 开发

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
bash scripts/verify.sh     # lint + tests + build + smoke
```

## 许可证

MIT

---

由 [MCP Tool Shop](https://mcp-tool-shop.github.io/) 构建
