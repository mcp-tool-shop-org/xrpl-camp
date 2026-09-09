import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'XRPL Camp',
  description: 'Learn the XRP Ledger in one sitting — real transactions, portable proof, 10 minutes.',
  logoBadge: 'XC',
  brandName: 'XRPL Camp',
  repoUrl: 'https://github.com/mcp-tool-shop-org/xrpl-camp',
  npmUrl: 'https://www.npmjs.com/package/@mcptoolshop/xrpl-camp',
  pypiUrl: 'https://pypi.org/project/xrpl-camp/',
  footerText: 'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>',

  hero: {
    badge: 'Open source',
    headline: 'XRPL Camp',
    headlineAccent: 'learn the ledger in one sitting.',
    description: 'Six lessons on a real public ledger. Your payment brings an account into existence, your memo is permanent, and the record you keep can be checked against the ledger itself. No accounts, no real money, about ten minutes.',
    primaryCta: { href: '#usage', label: 'Get started' },
    secondaryCta: { href: 'handbook/', label: 'Read the Handbook' },
    previews: [
      { label: 'Install', code: 'pipx install xrpl-camp' },
      { label: 'Start', code: 'xrpl-camp start' },
      { label: 'Break it', code: 'xrpl-camp try' },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'Features',
      subtitle: 'Everything you need to understand the XRPL — nothing you don\'t.',
      features: [
        { title: 'Real transactions', desc: 'Create a wallet, fund it, and send a payment that brings a second account into existence — on the actual Testnet, not a sandbox. The ledger metadata proves the account was created.' },
        { title: 'Failure as curriculum', desc: 'xrpl-camp try breaks things on purpose against the live network. It signs nothing and costs nothing, then shows you which failures would have reached the ledger and charged you.' },
        { title: 'Proof you can check', desc: 'The proof pack names real transactions. proof verify --online asks the ledger whether they happened — the part a hash cannot prove and nobody can fake.' },
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Usage',
      cards: [
        { title: 'Install', code: 'npx @mcptoolshop/xrpl-camp start\n# or: pipx install xrpl-camp\n# or: docker run --rm -it -v "$PWD:/work" \\\n#       ghcr.io/mcp-tool-shop-org/xrpl-camp start' },
        { title: 'Guided flow', code: 'xrpl-camp start\n\n# 1. Mental Model      asked of the live network\n# 2. Create Wallet     the seed stays on your machine\n# 3. Fund Wallet       and why some of it is locked\n# 4. Send Payment      this one creates an account\n# 5. Verify            compare the ledger to what you typed\n# 6. Certificate       a record you can prove' },
        { title: 'Afterwards', code: '# your entries, read back off the ledger\nxrpl-camp read\n\n# what somebody else wrote — no key needed\nxrpl-camp read rSomeoneElsesAddress\n\n# ask the ledger whether your record is real\nxrpl-camp proof verify xrpl_camp_proof_pack.json --online' },
      ],
    },
    {
      kind: 'data-table',
      id: 'commands',
      title: 'Commands',
      subtitle: 'Every networked command supports --dry-run.',
      columns: ['Command', 'What it does'],
      rows: [
        ['xrpl-camp start', 'Guided flow through all 6 lessons'],
        ['xrpl-camp read', 'Your entries, read back off the ledger'],
        ['xrpl-camp read <address>', "Somebody else's public history — no key, no login"],
        ['xrpl-camp try', 'Break it on purpose. Signs nothing, costs nothing'],
        ['xrpl-camp status --detail', 'Facilitator view: wallet, endpoint, state directory'],
        ['xrpl-camp send --memo "hello"', 'Send a memo payment to your mailbox'],
        ['xrpl-camp verify --tx <hash>', 'Verify a transaction you sent'],
        ['xrpl-camp certificate', 'Generate certificate + proof pack'],
        ['xrpl-camp proof verify <file>', "Check the pack's hash. Fully offline"],
        ['xrpl-camp proof verify <file> --online', 'Also ask the ledger whether it happened'],
        ['xrpl-camp self-check', 'Diagnose your environment and your connection'],
        ['xrpl-camp reset', 'Wipe all state (typed confirmation)'],
      ],
    },
    {
      kind: 'features',
      id: 'safety',
      title: 'Safety',
      subtitle: 'Built for learning, not for losing.',
      features: [
        { title: 'Testnet, and enforced', desc: 'The endpoint\'s network is checked before anything is signed, and a non-Testnet endpoint is refused unless you explicitly opt out. Test XRP has no real value.' },
        { title: 'Your seed stays yours', desc: 'Stored locally, owner-only on POSIX, and never written into a certificate or proof pack — generation refuses the file if a seed is present. Your memo is scanned for secrets before it becomes permanent.' },
        { title: 'No telemetry', desc: 'No analytics, no phone-home, no accounts. The only network calls go to the XRPL endpoint in use, and self-check tells you which one that is.' },
      ],
    },
  ],
};
