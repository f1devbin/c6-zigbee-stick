"""Build the flasher site in docs/: English at the root, Russian in /ru/, sitemap.

Run after changing any text here: python tools/build_site.py
"""

from __future__ import annotations

from datetime import date
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "docs"
BASE = "https://f1devbin.github.io/c6-zigbee-stick/"
REPO = "https://github.com/f1devbin/c6-zigbee-stick"
FIRMWARE = "1.5.80"
HACS_LINK = ("https://my.home-assistant.io/redirect/hacs_repository/"
             "?owner=f1devbin&repository=c6-zigbee-stick&category=integration")
LANGS = {"en": "", "ru": "ru/"}  # language -> path under BASE

T = {
    "en": {
        "title": "ESP32-C6 Zigbee Coordinator for Home Assistant: Web Flasher",
        "desc": "Turn an ESP32-C6 into a Zigbee coordinator for Home Assistant: flash it from the browser, "
                "plug it in, and the integration sets up Zigbee2MQTT for you. Free and open source.",
        "h1": "ESP32-C6 Zigbee coordinator for Home Assistant",
        "lead": "C6 Zigbee Stick turns an ordinary ESP32-C6 board into a Zigbee coordinator. Flash the firmware "
                "from this page, plug the board into Home Assistant, and the integration finds it and sets up "
                "Zigbee2MQTT. No terminal, no YAML.",
        "switch": "Русский",
        "s1": "1. Flash the ESP32-C6 from your browser",
        "s1p": "Connect the board to your computer with a data USB cable (to the USB connector, not UART) "
               "and press the button. Works in Chrome and Edge on a computer.",
        "btn": "Install firmware",
        "nousb": "Your browser cannot talk to USB ports. Open this page in Chrome or Edge on a computer.",
        "fwnote": f"Firmware: esp-coordinator {FIRMWARE} (Espressif ZBOSS stack, NCP over USB), unmodified. "
                  "The board's flash is fully erased.",
        "s2": "2. Add the integration through HACS",
        "s2p": "Once per Home Assistant: open the repository in HACS with the button below (or add "
               f"<code>{REPO}</code> as a custom repository of type “Integration”), install "
               "“C6 Zigbee Stick” and restart Home Assistant.",
        "hacs": "Open in HACS",
        "s3": "3. Plug the stick into Home Assistant",
        "s3p": "A “Discovered: C6 Zigbee Stick” card appears in Settings → Devices &amp; services. Press "
               "“Add”: the integration installs and starts Zigbee2MQTT (and the Mosquitto broker if there is "
               "no MQTT yet), points it at the stick and restarts it when the stick is plugged back in. Then "
               "pair Zigbee devices in Zigbee2MQTT with “Permit join”.",
        "boards": "Supported boards",
        "boardsp": "Any ESP32-C6 board whose USB connector is wired to the chip's own USB: ESP32-C6-DevKitC-1, "
                   "ESP32-C6-DevKitM-1, Seeed Studio XIAO ESP32C6, WeAct ESP32-C6 and similar. On boards with "
                   "two connectors use the one labelled USB, not UART or COM.",
        "faq": "FAQ",
        "qa": [
            ("Can an ESP32-C6 be a Zigbee coordinator?",
             "Yes. The ESP32-C6 has an IEEE 802.15.4 radio. With Espressif's ZBOSS stack in network "
             "co-processor mode it works as a coordinator, and Zigbee2MQTT talks to it with its zboss adapter."),
            ("Does it work with ZHA?",
             "Not yet: Home Assistant's built-in ZHA has no ZBOSS support, so the integration uses Zigbee2MQTT."),
            ("Why does Home Assistant need an integration for it?",
             "Retail sticks are recognised by the name in their USB descriptor. Every ESP32-C6 reports the "
             "same fixed descriptor (303a:1001, “USB JTAG/serial debug unit”), so the integration asks the board "
             "over the ZBOSS protocol whether it really is a coordinator before offering to set it up."),
            ("What are the limitations?",
             "Zigbee2MQTT's zboss adapter is marked experimental: changing the channel means re-pairing devices, "
             "and network backups, install codes and touchlink are not supported yet."),
        ],
        "foot": "Source code, details and issues:",
        "og": "en_US",
    },
    "ru": {
        "title": "Zigbee-координатор на ESP32-C6 для Home Assistant: прошивка из браузера",
        "desc": "Превратите ESP32-C6 в Zigbee-координатор для Home Assistant: прошейте из браузера, вставьте "
                "в USB, и интеграция сама настроит Zigbee2MQTT. Бесплатно, открытый код.",
        "h1": "Zigbee-координатор на ESP32-C6 для Home Assistant",
        "lead": "C6 Zigbee Stick превращает обычную плату ESP32-C6 в Zigbee-координатор. Прошейте её с этой "
                "страницы, вставьте в Home Assistant, и интеграция сама найдёт стик и настроит Zigbee2MQTT. "
                "Без терминала и YAML.",
        "switch": "English",
        "s1": "1. Прошейте ESP32-C6 из браузера",
        "s1p": "Подключите плату к компьютеру USB-кабелем с передачей данных (к разъёму USB, а не UART) и нажмите "
               "кнопку. Работает в Chrome и Edge на компьютере.",
        "btn": "Установить прошивку",
        "nousb": "Ваш браузер не умеет работать с USB-портами. Откройте страницу в Chrome или Edge на компьютере.",
        "fwnote": f"Прошивка: esp-coordinator {FIRMWARE} (стек Espressif ZBOSS, NCP по USB) без изменений. "
                  "Память платы будет полностью стёрта.",
        "s2": "2. Добавьте интеграцию через HACS",
        "s2p": "Один раз на Home Assistant: откройте репозиторий в HACS кнопкой ниже (или добавьте "
               f"<code>{REPO}</code> как пользовательский репозиторий типа «Интеграция»), установите "
               "«C6 Zigbee Stick» и перезапустите Home Assistant.",
        "hacs": "Открыть в HACS",
        "s3": "3. Вставьте стик в Home Assistant",
        "s3p": "В «Настройки → Устройства и службы» появится карточка «Обнаружено: C6 Zigbee Stick». Нажмите "
               "«Добавить»: интеграция установит и запустит Zigbee2MQTT (и брокер Mosquitto, если MQTT ещё нет), "
               "направит его на стик и перезапустит, если стик переподключить. Затем добавляйте устройства "
               "в Zigbee2MQTT кнопкой «Разрешить подключение».",
        "boards": "Подходящие платы",
        "boardsp": "Любая плата ESP32-C6, у которой USB-разъём подключён к встроенному USB чипа: ESP32-C6-DevKitC-1, "
                   "ESP32-C6-DevKitM-1, Seeed Studio XIAO ESP32C6, WeAct ESP32-C6 и подобные. На платах с двумя "
                   "разъёмами используйте подписанный USB, а не UART или COM.",
        "faq": "Вопросы и ответы",
        "qa": [
            ("Может ли ESP32-C6 быть Zigbee-координатором?",
             "Да. В ESP32-C6 есть радио IEEE 802.15.4. Со стеком Espressif ZBOSS в режиме сетевого сопроцессора "
             "плата работает координатором, а Zigbee2MQTT управляет ей через адаптер zboss."),
            ("Работает ли с ZHA?",
             "Пока нет: встроенный ZHA в Home Assistant не поддерживает ZBOSS, поэтому интеграция использует "
             "Zigbee2MQTT."),
            ("Зачем Home Assistant отдельная интеграция?",
             "Покупные стики распознаются по имени в USB-дескрипторе. Все ESP32-C6 показывают один и тот же "
             "неизменяемый дескриптор (303a:1001, «USB JTAG/serial debug unit»), поэтому интеграция сначала "
             "спрашивает плату по протоколу ZBOSS, действительно ли это координатор."),
            ("Какие ограничения?",
             "Адаптер zboss в Zigbee2MQTT помечен как экспериментальный: смена канала требует заново подключить "
             "устройства, резервные копии сети, install codes и touchlink пока не поддерживаются."),
        ],
        "foot": "Исходный код, подробности и вопросы:",
        "og": "ru_RU",
    },
}

CSS = """:root{--bg:#0f1b2d;--text:#fff;--text2:#dce6f3;--link:#8fd0ff;--btn:#8fd0ff;--btn-text:#0b1626;--rule:#33496b;color-scheme:dark}
@media (prefers-color-scheme:light){:root{--bg:#f7f9fc;--text:#0a1424;--text2:#1d2d43;--link:#084a8e;--btn:#084a8e;--btn-text:#fff;--rule:#bccadb;color-scheme:light}}
body{margin:0;background:var(--bg);color:var(--text2);font:400 18px/1.65 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:44rem;margin:0 auto;padding:2.5rem 1.25rem 4rem}
h1,h2,h3{color:var(--text);line-height:1.2} h1{font-size:2.2rem;margin:0 0 1rem} h2{font-size:1.35rem;margin:2.5rem 0 .5rem} h3{font-size:1.1rem;margin:1.5rem 0 .25rem}
.lead{font-size:1.2rem;color:var(--text)} a{color:var(--link)} code{font-size:.9em;word-break:break-all}
.lang{text-align:right;margin:0 0 1rem} .note{font-size:.95rem}
.logo{width:72px;height:72px;display:block;margin:0 0 1rem}
esp-web-install-button{display:block;margin:1.25rem 0}
.btn{display:inline-block;font-family:inherit;font-weight:600;font-size:1.05rem;line-height:1.2;padding:.9rem 1.4rem;border-radius:.5rem;border:0;background:var(--btn);color:var(--btn-text);cursor:pointer;text-decoration:none}
footer{border-top:1px solid var(--rule);margin-top:3rem;padding-top:1rem;font-size:.95rem}"""


def url(lang: str) -> str:
    return BASE + LANGS[lang]


def page(lang: str) -> str:
    t = T[lang]
    up = "../" * LANGS[lang].count("/")
    other = "ru" if lang == "en" else "en"
    alternates = "".join(f'<link rel="alternate" hreflang="{l}" href="{url(l)}">\n' for l in LANGS)
    alternates += f'<link rel="alternate" hreflang="x-default" href="{url("en")}">\n'
    ld = [
        {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "C6 Zigbee Stick",
            "description": t["desc"],
            "url": url(lang),
            "inLanguage": lang,
            "applicationCategory": "UtilitiesApplication",
            "operatingSystem": "Home Assistant OS",
            "softwareVersion": FIRMWARE,
            "downloadUrl": BASE + f"firmware/esp-coordinator-esp32c6-v{FIRMWARE}-factory.bin",
            "codeRepository": REPO,
            "license": "https://opensource.org/licenses/MIT",
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "author": {"@type": "Person", "name": "f1devbin", "url": "https://f1devbin.github.io/"},
            "image": BASE + "og.png",
            "keywords": "ESP32-C6, Zigbee coordinator, Home Assistant, Zigbee2MQTT, ZBOSS, HACS, web flasher",
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in t["qa"]
            ],
        },
    ]
    faq = "".join(f"<h3>{html.escape(q)}</h3>\n<p>{html.escape(a)}</p>\n" for q, a in t["qa"])
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["desc"])}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{url(lang)}">
{alternates}<link rel="icon" type="image/png" href="{up}icon.png">
<link rel="apple-touch-icon" href="{up}icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="C6 Zigbee Stick">
<meta property="og:title" content="{html.escape(t["title"])}">
<meta property="og:description" content="{html.escape(t["desc"])}">
<meta property="og:url" content="{url(lang)}">
<meta property="og:image" content="{BASE}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{t["og"]}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script type="module" src="https://unpkg.com/esp-web-tools@10.4.0/dist/web/install-button.js?module"></script>
<style>
{CSS}
</style>
</head>
<body>
<main>
<p class="lang"><a href="{url(other)}" hreflang="{other}">{t["switch"]}</a></p>
<img class="logo" src="{up}icon.png" alt="" width="72" height="72">
<h1>{t["h1"]}</h1>
<p class="lead">{t["lead"]}</p>
<h2>{t["s1"]}</h2>
<p>{t["s1p"]}</p>
<esp-web-install-button manifest="{up}manifest.json">
<button slot="activate" class="btn">{t["btn"]}</button>
<span slot="unsupported">{t["nousb"]}</span>
<span slot="not-allowed">{t["nousb"]}</span>
</esp-web-install-button>
<p class="note">{t["fwnote"]}</p>
<h2>{t["s2"]}</h2>
<p>{t["s2p"]}</p>
<p><a class="btn" href="{HACS_LINK}" rel="nofollow">{t["hacs"]}</a></p>
<h2>{t["s3"]}</h2>
<p>{t["s3p"]}</p>
<h2>{t["boards"]}</h2>
<p>{t["boardsp"]}</p>
<h2>{t["faq"]}</h2>
{faq}<footer><p>{t["foot"]} <a href="{REPO}">github.com/f1devbin/c6-zigbee-stick</a></p></footer>
</main>
</body>
</html>
"""


def sitemap() -> str:
    today = date.today().isoformat()
    links = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{url(l)}"/>' for l in LANGS)
    links += f'<xhtml:link rel="alternate" hreflang="x-default" href="{url("en")}"/>'
    urls = "".join(f"<url><loc>{url(l)}</loc><lastmod>{today}</lastmod>{links}</url>\n" for l in LANGS)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + urls + "</urlset>\n")


def main() -> None:
    for lang, path in LANGS.items():
        out = ROOT / path / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(lang), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(sitemap(), encoding="utf-8")


if __name__ == "__main__":
    main()
