<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.md">English</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

npm के लिए एक सामान्य GitHub-रिलीज़ बाइनरी लॉन्चर। यह GitHub रिलीज़ से प्लेटफ़ॉर्म-विशिष्ट बाइनरी फ़ाइलें डाउनलोड करता है, उन्हें स्थानीय रूप से संग्रहीत करता है, SHA256 चेकसम की जांच करता है, और उन्हें सभी तर्कों के साथ चलाता है।

यह इस तरह बनाया गया है कि पायथन CLI (या कोई भी संकलित बाइनरी) बिना किसी निर्भरता के `npx` के माध्यम से वितरित किया जा सके।

## सुरक्षा और खतरे का मॉडल

npm-launcher बाइनरी फ़ाइलों को डाउनलोड और निष्पादित करता है। यह बताता है कि यह किन चीज़ों को छूता है और किन चीज़ों को नहीं:

- **नेटवर्क:** केवल HTTPS, `github.com` और GitHub के CDN पर। कोई अन्य गंतव्य नहीं।
- **फ़ाइल सिस्टम:** यह केवल स्थानीय कैश में लिखता है (`~/.cache/mcptoolshop/` या `%LOCALAPPDATA%\mcptoolshop\`)। यह सिस्टम फ़ाइलों को संशोधित नहीं करता है या कैश के बाहर की फ़ाइलों को नहीं पढ़ता है।
- **सत्यापन:** प्रत्येक बाइनरी फ़ाइल की जांच `checksums-<version>.txt` नामक फ़ाइल में दिए गए SHA256 से की जाती है, जो उसी रिलीज़ में मौजूद होती है। यदि कोई विसंगति पाई जाती है, तो निष्पादन रद्द हो जाता है और डाउनलोड की गई फ़ाइल हटा दी जाती है।
- **कोई टेलीमेट्री नहीं।** कोई गुप्त जानकारी नहीं। कोई भी क्रेडेंशियल संग्रहीत या प्रसारित नहीं किए जाते हैं।
- **अनुमतियाँ:** सामान्य उपयोगकर्ता फ़ाइल सिस्टम एक्सेस और आउटबाउंड HTTPS के अलावा किसी भी अनुमति की आवश्यकता नहीं है।

## यह कैसे काम करता है

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

## इंस्टॉलेशन

```bash
npm install @mcptoolshop/npm-launcher
```

यह पैकेज रैपर पैकेजों के लिए एक लाइब्रेरी है - अंतिम उपयोगकर्ता रैपर (जैसे `npx @mcptoolshop/sovereignty`) स्थापित करते हैं, न कि सीधे यह पैकेज।

## कॉन्फ़िगरेशन

रैपर `MCPTOOLSHOP_LAUNCH_CONFIG` के माध्यम से केवल शुद्ध JSON डेटा पास करते हैं। इसमें कोई फ़ंक्शन या जादू नहीं होता है।

| फ़ील्ड | आवश्यक | उदाहरण | विवरण |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | हाँ | `"sovereignty"`        | बाइनरी का बेस नाम |
| `owner`    | हाँ | `"mcp-tool-shop-org"`  | GitHub संगठन/उपयोगकर्ता |
| `repo`     | हाँ | `"sovereignty"`        | GitHub रिपॉजिटरी का नाम |
| `version`  | हाँ | `"1.4.0"`              | सेमवर् (बिना `v` उपसर्ग के) |
| `tag`      | no       | `"v1.4.0"`             | Git टैग (डिफ़ॉल्ट रूप से `v<version>`) |
| `quiet`    | no       | `true`                 | प्रगति संदेशों को दबाएं |

## एसेट नामकरण सम्मेलन

निश्चित। सभी टूल एक ही पैटर्न का पालन करते हैं:

```
<toolName>-<version>-<os>-<arch><ext>
```

| प्लेटफ़ॉर्म | उदाहरण एसेट |
|---------------|--------------------------------------|
| लिनक्स x64 | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel | `sovereignty-1.4.0-darwin-x64`       |
| विंडोज x64 | `sovereignty-1.4.0-win-x64.exe`     |

चेकसम फ़ाइल: `checksums-<version>.txt` (GNU coreutils प्रारूप)।

## रैपर कैसे लिखें

एक रैपर एक छोटा npm पैकेज होता है (~3 फ़ाइलें):

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

पूर्ण रैपर टेम्प्लेट और CI वर्कफ़्लो के लिए `examples/` देखें।

## पर्यावरण चर

| चर | प्रभाव |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | प्रगति संदेशों को दबाएं (त्रुटियां अभी भी प्रदर्शित होती हैं) |

## समर्थित प्लेटफ़ॉर्म

- लिनक्स x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- विंडोज x64

## कैश स्थान

| OS      | पथ |
|---------|----------------------------------------------|
| लिनक्स | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| विंडोज | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

द्वारा निर्मित <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
