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
  <a href="https://codecov.io/gh/mcp-tool-shop-org/xrpl-camp"><img src="https://codecov.io/gh/mcp-tool-shop-org/xrpl-camp/branch/main/graph/badge.svg" alt="Coverage"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/xrpl-camp/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Aprenda o XRP Ledger de uma só vez. Sem contas. Sem dinheiro real. Apenas você e o livro-razão.

A maioria dos tutoriais de blockchain ensina conceitos. O XRPL Camp faz com que você os _pratique_ — crie uma carteira, adicione fundos a ela, escreva uma nota permanente em um livro-razão público, verifique-a de forma independente e saia com um registro que qualquer pessoa pode verificar no próprio livro-razão. Todo o processo leva cerca de dez minutos.

Criado para workshops, salas de aula e estudo individual. O fluxo guiado retoma de onde você parou, uma lição com falha interrompe a execução em vez de fingir, e nada afirma que algo aconteceu que não aconteceu.

## Por que isso em vez de um tutorial genérico?

- **Transações reais, não slides.** Você escreve em um livro-razão real. Quando a lição 5 diz "verifique você mesmo", ela fornece um hash e um link para um explorador que qualquer pessoa pode verificar.
- **Seu pagamento cria uma conta.** A lição 4 não é uma transferência de teste — ela financia uma segunda conta que não existia um momento antes, e cujas chaves também são suas.
- **A falha faz parte do currículo.** O `xrpl-camp try` quebra as coisas intencionalmente na rede ativa, e então mostra quais falhas teriam gerado custos e quais são gratuitas — *antes* de você clicar em enviar.
- **Prova de que você pode realmente verificar.** O pacote de prova nomeia transações reais e o `proof verify --online` pergunta ao livro-razão se elas realmente ocorreram. Ninguém pode falsificar essa parte.
- **Seguro por design.** Apenas Testnet. O teste XRP não tem valor. Sua chave privada nunca sai da sua máquina. Sem telemetria, sem análise, sem contas.

## Instalação

**Não requer Python** (baixa um binário pré-compilado):

```bash
npx @mcptoolshop/xrpl-camp start
```

Com Python (3.11, 3.12 ou 3.13):

```bash
pipx install xrpl-camp
```

Em Docker — para workshops onde a instalação é a parte mais difícil:

```bash
docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
```

> Monte um volume. Tudo o que você criar — carteira, certificado, pacote de prova — é gravado em `/work`, e um contêiner desmontado o descarta ao sair. A imagem informa se você esqueceu de algo.

## Início Rápido

```bash
xrpl-camp start
```

Seis lições, em ordem, retomando se você reiniciar:

1. **Modelo Mental** — o que é o XRPL, perguntado à rede ativa em vez de apenas afirmado.
2. **Criar Carteira** — gere um par de chaves Testnet; a chave privada permanece na sua máquina.
3. **Adicionar Fundos à Carteira** — obtenha XRP de teste gratuito do "faucet" e por que parte dele não pode ser gasta.
4. **Enviar Pagamento** — escreva sua nota no livro-razão, em um pagamento que cria uma conta.
5. **Verificar Transação** — procure o que você escreveu e compare com o que digitou.
6. **Certificado** — um registro que você mantém e pode provar.

## Comandos

| Comando | O que ele faz |
|---------|-------------|
| `xrpl-camp start` | Fluxo guiado por todas as 6 lições (retoma automaticamente) |
| `xrpl-camp start --memo "..."` | Forneça a mensagem da lição 4 antecipadamente, para execuções roteirizadas ou não interativas |
| `xrpl-camp read` | Suas entradas, lidas de volta **do livro-razão** — não desta máquina |
| `xrpl-camp read <address>` | O que outra pessoa escreveu. Sem chave, sem login, sem permissão |
| `xrpl-camp read <hash>` | Uma transação, completa |
| `xrpl-camp try` | Quebre-o intencionalmente na rede ativa. Não assina nada, não custa nada |
| `xrpl-camp reserve` | Crie e destrua um NFT para observar o bloqueio da reserva do proprietário e o retorno |
| `xrpl-camp status` | Lista de verificação de progresso, com tempos |
| `xrpl-camp status --detail` | Visualização para o facilitador: carteira, ponto de extremidade, diretório de estado, próxima etapa |
| `xrpl-camp wallet create` / `show` | Crie ou exiba sua carteira Testnet |
| `xrpl-camp fund` | Adicione fundos à sua carteira por meio do "faucet" Testnet |
| `xrpl-camp send --memo "hello"` | Envie um pagamento de nota para sua caixa de entrada |
| `xrpl-camp verify --tx <hash>` | Verifique uma transação **que você** enviou |
| `xrpl-camp certificate` | Gere o certificado + pacote de prova (o `--format text` adiciona uma lembrança `.txt`) |
| `xrpl-camp proof verify <file>` | Verifique o hash de um pacote de prova. Totalmente offline |
| `xrpl-camp proof verify <file> --online` | Pergunte também ao livro-razão se as transações realmente ocorreram (o `--record` anexa um recibo com data) |
| `xrpl-camp proof verify <folder>` | Verifique todos os pacotes em uma pasta — para facilitadores |
| `xrpl-camp reset` | Limpe todo o estado (requer digitar `RESET`) |
| `xrpl-camp self-check` | Diagnostique seu ambiente **e** sua conexão com o livro-razão |
| `xrpl-camp support-bundle` | Crie um arquivo zip de diagnóstico para relatórios de bugs |

Flags globais: `--version`, `--dry-run`, `--yes` (não interativo), `--verbose` (detalhes técnicos sobre erros).

## O que você terá no final

- Uma carteira Testnet financiada, local e ignorada pelo Git
- Uma **segunda conta que não existia até que seu pagamento a criasse** — e cujas chaves também são suas
- Uma nota que você escolheu, registrada permanentemente e legível de forma independente
- Um certificado (`xrpl_camp_certificate.json`) — seguro para compartilhar, sem chaves privadas
- Um pacote de prova (`xrpl_camp_proof_pack.json`) — nomeando transações reais que qualquer pessoa pode resolver

## Sobre essa prova

O pacote de prova carrega um hash SHA-256. Esse hash detecta uma edição acidental. **Não** é uma assinatura e, por si só, não prova que o pacote é genuíno — qualquer pessoa pode alterar um campo e recalcular o hash com a mesma função pública que esta ferramenta usa.

O que não pode ser falsificado é o livro-razão:

```bash
xrpl-camp proof verify xrpl_camp_proof_pack.json --online
```

Este resolve cada transação que o pacote nomeia e verifica se ela existe, foi enviada pelo endereço do pacote, contém a nota que o pacote afirma e foi concluída com sucesso. Um pacote com um endereço reescrito passa na verificação de hash offline e falha nesta.

Dois detalhes que valem a pena saber, porque ambos são fáceis de errar:

- A verificação sempre consulta o Testnet (ou `--rpc-url`) público, **nunca** o ponto de extremidade nomeado dentro do pacote. Um pacote falsificado pode nomear um servidor que seu autor controla.
- O XRPL Testnet é redefinido periodicamente (próximo em 25/11/2026). Quando isso acontece, as transações honestas param de ser resolvidas. Se o ponto de extremidade não mantiver o livro-razão em que uma transação foi registrada, o resultado é *não verificável* (saída 3), não fraude (saída 1), e a saída indica em que isso se baseia: uma redefinição anunciada (`history_signal: announced`) ou apenas o número do livro-razão do próprio pacote (`pack_claim`, mostrado como **UNCONFIRMED**). Nenhum dos dois conta como aprovado.

A verificação offline permanece como padrão e não faz chamadas de rede, portanto, ainda funciona em um avião ou em uma máquina de sala de aula com acesso restrito.

## Modo de Execução a Seco

```bash
xrpl-camp start --dry-run
```

Não há chamadas de rede, nem gravações em disco e nem resultados enganosos — a lição 6 recusa explicitamente gerar artefatos. O modo de teste pode *ler* o estado existente, mas nunca modifica nada.

## Ponto de extremidade e estado

```bash
export XRPL_CAMP_RPC_URL="https://your-node:51234/"
```

A ferramenta recusa os pontos de extremidade que não consegue confirmar serem Testnet, antes de assinar qualquer coisa. Defina `XRPL_CAMP_ALLOW_ANY_NETWORK=1` apenas se você entender para onde está apontando.

O estado é armazenado em `./.xrpl-camp` por padrão — uma sessão pertence à pasta em que você a executou. `XRPL_CAMP_HOME` substitui isso, e `xrpl-camp status --detail` imprime o caminho absoluto resolvido.

## Segurança

Sua semente é armazenada localmente em `.xrpl-camp/wallet.json` (apenas para o proprietário em POSIX) e nunca é incluída no certificado ou no pacote de prova — a geração recusa-se a gravar um artefato que contenha uma.

Por padrão, esta ferramenta usa XRPL Testnet, onde o teste XRP não tem valor real, e recusa pontos de extremidade não Testnet, a menos que você opte explicitamente por não fazê-lo. Sem telemetria, sem análise, sem comunicação com servidores externos.

Veja [SECURITY.md](SECURITY.md).

## Modelo de ameaças

| Ameaça | Mitigação |
|--------|-----------|
| Semente vazada em um artefato | A geração executa uma verificação de semente baseada no próprio `decode_seed` de xrpl-py e **recusa-se a gravar o arquivo** se detectar algo suspeito. |
| Semente enviada para o Git | `.xrpl-camp/` é ignorado pelo Git *neste repositório*; o estado é gravado no seu diretório de trabalho, então adicione-o ao seu próprio `.gitignore`. |
| Semente legível por outros usuários | Arquivo da carteira com permissão 0600, diretório de estado com permissão 0700 em POSIX. |
| O aluno cola um segredo em um memorando público | O texto do memorando é verificado em busca de sequências semelhantes a sementes e a submissão é recusada. |
| Semente Testnet reutilizada em Mainnet | Aviso na criação da carteira; a ferramenta recusa pontos de extremidade não Testnet por padrão. |
| Adulteração do pacote de prova | SHA-256 detecta edições superficiais; `--online` detecta uma falsificação re-selada consultando o livro-razão. |
| Verificação em relação ao ponto de extremidade de um invasor | `--online` nunca usa o ponto de extremidade especificado no pacote que está sendo testado. |
| Diagnósticos que revelam sua identidade | `support-bundle` oculta o diretório pessoal e o nome da conta. |

## Para workshops e salas de aula

- **Um comando por aluno.** `npx`, `pipx` ou o contêiner — sem configuração compartilhada.
- **Falha é permitida.** `xrpl-camp try` ensina os modos de falha sem gastar nada, então um aluno que quebra algo intencionalmente aprende mais do que um que não o faz.
- **Triagem do facilitador.** `status --detail` mostra a carteira, o ponto de extremidade e o diretório de estado. `self-check` verifica a conexão real em vez de relatar um "OK" otimista.
- **Verifique toda a sala de uma vez.** `proof verify <folder> --online` verifica o pacote de cada aluno em relação ao livro-razão.
- **Os limites de taxa são reais.** Trinta pessoas acessando uma única fonte atingirão o limite; a ferramenta tenta novamente com um intervalo e informa isso, em vez de culpar sua conexão Wi-Fi.

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
