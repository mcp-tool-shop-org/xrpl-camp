<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
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

Aprenda sobre o XRP Ledger em uma única sessão. Sem contas. Sem dinheiro real. Apenas você e o livro-razão.

A maioria dos tutoriais sobre blockchain ensina conceitos. O XRPL Camp faz com que você os _pratique_ — crie uma carteira, adicione fundos a ela, escreva uma mensagem permanente em um livro-razão público, verifique-a de forma independente e saia com um registro que qualquer pessoa pode verificar em relação ao próprio livro-razão. Todo o processo leva cerca de dez minutos.

Criado para workshops, salas de aula e estudo individual. O fluxo guiado retoma de onde você parou, uma lição com falha interrompe a execução em vez de fingir que tudo está bem, e nada afirma que algo aconteceu que não aconteceu.

## Por que isso em vez de um tutorial genérico?

- **Transações reais, não slides.** Você escreve em um livro-razão real. Quando a lição 5 diz "verifique você mesmo", ela fornece um hash e um link para um explorador que qualquer pessoa pode verificar.
- **Seu pagamento cria uma conta.** A lição 4 não é uma transferência de teste — ela adiciona fundos a uma segunda conta que não existia um momento antes, e cujas chaves também são suas.
- **A falha faz parte do currículo.** `xrpl-camp try` causa falhas intencionalmente na rede ativa, depois mostra quais falhas teriam gerado custos e quais são gratuitas — *antes* de você clicar em enviar.
- **Prova de que você pode realmente verificar.** O pacote de prova lista transações reais e `proof verify --online` pergunta ao livro-razão se elas realmente ocorreram. Ninguém pode falsificar essa parte.
- **Seguro por design.** Apenas testnet. XRP de teste não tem valor. Sua chave privada nunca sai da sua máquina. Sem telemetria, sem análise, sem contas.

## Instalação

**Não é necessário Python** (baixa um binário pré-compilado):

```bash
npx @mcptoolshop/xrpl-camp start
```

Com Python:

```bash
pipx install xrpl-camp
```

No Docker — para workshops onde a instalação é a parte mais difícil:

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> Monte um volume. Tudo o que você criar — carteira, certificado, pacote de prova — é gravado em `/work`, e um contêiner não montado o descarta ao sair. A imagem informa se você esqueceu.

## Início Rápido

```bash
xrpl-camp start
```

Seis lições, em ordem, retomando se você reiniciar:

1. **Modelo Mental** — o que é o XRPL, perguntado à rede ativa em vez de apenas afirmado
2. **Criar Carteira** — gere um par de chaves Testnet; a chave privada permanece na sua máquina
3. **Adicionar Fundos à Carteira** — XRP de teste gratuito do faucet, e por que parte dele não pode ser gasto
4. **Enviar Pagamento** — escreva sua mensagem no livro-razão, em um pagamento que cria uma conta
5. **Verificar Transação** — procure o que você escreveu e compare com o que digitou
6. **Certificado** — um registro que você guarda e pode comprovar

## Comandos

| Comando | O que ele faz |
|---------|-------------|
| `xrpl-camp start` | Fluxo guiado por todas as 6 lições (retoma automaticamente) |
| `xrpl-camp start --memo "..."` | Forneça a mensagem da lição 4 antecipadamente, para execuções roteirizadas ou não interativas |
| `xrpl-camp read` | Suas entradas, lidas **do livro-razão** — não desta máquina |
| `xrpl-camp read <address>` | O que outra pessoa escreveu. Sem chave, sem login, sem permissão |
| `xrpl-camp read <hash>` | Uma transação, completa |
| `xrpl-camp try` | Cause uma falha intencionalmente na rede ativa. Não assina nada, não custa nada |
| `xrpl-camp status` | Lista de verificação de progresso, com tempos |
| `xrpl-camp status --detail` | Visualização do facilitador: carteira, endpoint, diretório de estado, próxima etapa |
| `xrpl-camp wallet create` / `show` | Crie ou exiba sua carteira Testnet |
| `xrpl-camp fund` | Adicione fundos à sua carteira por meio do faucet Testnet |
| `xrpl-camp send --memo "hello"` | Envie um pagamento de mensagem para sua caixa de entrada |
| `xrpl-camp verify --tx <hash>` | Verifique uma transação **que você** enviou |
| `xrpl-camp certificate` | Gere o certificado + pacote de prova |
| `xrpl-camp proof verify <file>` | Verifique o hash de um pacote de prova. Totalmente offline |
| `xrpl-camp proof verify <file> --online` | Pergunte também ao livro-razão se as transações realmente ocorreram |
| `xrpl-camp proof verify <folder>` | Verifique todos os pacotes em uma pasta — para facilitadores |
| `xrpl-camp reset` | Limpe todo o estado (requer digitar `RESET`) |
| `xrpl-camp self-check` | Diagnostique seu ambiente **e** sua conexão com o livro-razão |
| `xrpl-camp support-bundle` | Crie um arquivo zip de diagnóstico para relatórios de bugs |

Flags globais: `--version`, `--dry-run`, `--yes` (não interativo), `--verbose` (detalhes técnicos sobre erros).

## O que você terá no final

- Uma carteira Testnet com fundos, local e ignorada pelo Git
- Uma **segunda conta que não existia até que seu pagamento a criasse** — e cujas chaves também são suas
- Uma mensagem que você escolheu, registrada permanentemente e legível de forma independente
- Um certificado (`xrpl_camp_certificate.json`) — seguro para compartilhar, sem chaves privadas
- Um pacote de prova (`xrpl_camp_proof_pack.json`) — listando transações reais que qualquer pessoa pode resolver

## Sobre essa prova

O pacote de prova contém um hash SHA-256. Esse hash detecta uma edição acidental. Não é uma assinatura e, por si só, não prova que o pacote é genuíno — qualquer pessoa pode alterar um campo e recalcular o hash com a mesma função pública que esta ferramenta usa.

O que não pode ser falsificado é o livro-razão:

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

Este resolve cada transação que o pacote lista e verifica se ela existe, foi enviada pelo endereço do pacote, contém a mensagem que o pacote afirma e foi concluída com sucesso. Um pacote com um endereço reescrito passa na verificação de hash offline e falha nesta.

Dois detalhes que valem a pena saber, porque ambos são fáceis de errar:

- A verificação sempre consulta o Testnet público (ou `--rpc-url`), **nunca** o endpoint nomeado dentro do pacote. Um pacote falsificado pode nomear um servidor que seu autor controla.
- O XRPL Testnet é periodicamente redefinido. Quando isso acontece, as transações honestas param de ser resolvidas. O pacote registra o índice do livro-razão de cada transação, então uma redefinição é relatada como *não verificável* (saída 3) em vez de como fraude (saída 1).

A verificação offline permanece como padrão e não faz chamadas de rede, portanto, ainda funciona em um avião ou em uma máquina de sala de aula com acesso restrito.

## Modo de Execução a Seco

```bash
xrpl-camp start --dry-run
```

Sem chamadas de rede, sem gravações em disco e sem saída enganosa — a lição 6 se recusa explicitamente a gerar artefatos. A execução a seco pode *ler* o estado existente, mas nunca modifica nada.

## Endpoint e Estado

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

A ferramenta rejeita os pontos de extremidade que não consegue confirmar serem da Testnet, antes de assinar qualquer coisa. Defina `XRPL_CAMP_ALLOW_ANY_NETWORK=1` apenas se souber para onde está a apontar.

O estado é armazenado por padrão em `./.xrpl-camp` — uma sessão pertence à pasta onde foi executada. `XRPL_CAMP_HOME` substitui isso, e `xrpl-camp status --detail` imprime o caminho absoluto resolvido.

## Segurança

A sua chave privada é armazenada localmente em `.xrpl-camp/wallet.json` (apenas para o proprietário em POSIX) e nunca é incluída no certificado ou no pacote de prova — a geração recusa-se a escrever um artefato que contenha uma.

Esta ferramenta, por padrão, utiliza a XRPL Testnet, onde o XRP de teste não tem valor real, e rejeita pontos de extremidade que não sejam da Testnet, a menos que você opte explicitamente por não o fazer. Sem telemetria, sem análise, sem comunicação com um servidor central.

Consulte [SECURITY.md](SECURITY.md).

## Modelo de Ameaças

| Ameaça | Mitigação |
|--------|-----------|
| Chave privada divulgada em um artefato | A geração executa uma verificação da chave privada, baseada no `decode_seed` do xrpl-py, e **recusa-se a escrever o arquivo** se a verificação falhar. |
| Chave privada enviada para o Git | `.xrpl-camp/` é ignorado pelo Git *neste repositório*; o estado é escrito no seu diretório de trabalho, portanto, adicione-o ao seu próprio `.gitignore`. |
| Chave privada legível por outros usuários | Arquivo da carteira com permissão 0600, diretório de estado com permissão 0700 no POSIX. |
| Um usuário insere uma chave privada em um memorando público | O texto do memorando é verificado para identificar sequências que se assemelham a uma chave privada e é rejeitado antes do envio. |
| Chave privada da Testnet reutilizada na Mainnet | Aviso no momento da criação da carteira; a ferramenta rejeita pontos de extremidade que não sejam da Testnet por padrão. |
| Manipulação do pacote de prova | SHA-256 detecta edições simples; `--online` detecta uma falsificação re-selada, consultando o livro-razão. |
| Verificação em relação ao ponto de extremidade de um invasor | `--online` nunca usa o ponto de extremidade especificado no pacote que está sendo testado. |
| Diagnósticos que revelam sua identidade | `support-bundle` remove o diretório inicial e o nome da conta. |

## Para workshops e salas de aula

- **Um comando por aluno.** `npx`, `pipx` ou o contêiner — sem configuração compartilhada.
- **O fracasso é gratuito.** `xrpl-camp try` ensina os modos de falha sem gastar nada, então um aluno que quebra algo intencionalmente aprende mais do que um que não o faz.
- **Triagem do facilitador.** `status --detail` mostra a carteira, o ponto de extremidade e o diretório de estado. `self-check` verifica a conexão real, em vez de relatar um "OK" otimista.
- **Verifique toda a sala de uma vez.** `proof verify <folder> --online` verifica o pacote de cada aluno em relação ao livro-razão.
- **Os limites de taxa são reais.** Trinta pessoas acessando um único faucet atingirão o limite; a ferramenta tenta novamente com um atraso e informa isso, em vez de culpar sua conexão Wi-Fi.

## Desenvolvimento

```bash
git clone https://github.com/mcp-tool-shop-org/xrpl-camp.git
cd xrpl-camp
uv sync --dev
bash scripts/verify.sh     # lint + tests + build + smoke
```

## Licença

MIT

---

Criado por [MCP Tool Shop](https://mcp-tool-shop.github.io/)
