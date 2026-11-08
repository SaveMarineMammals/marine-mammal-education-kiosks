# Module: dns-facility

Creates nested public hosted zones under an existing parent zone and optional CMS
address records.

| Zone | Purpose |
| --- | --- |
| `belize.<parent>` | Country / facility DNS |
| `kiosks.local.belize.<parent>` | Kiosk LAN names + Let's Encrypt DNS-01 |

Delegation NS records are written into the parent and belize zones automatically.
The parent zone (`savemarinemammals.com` by default) must already exist in the
account.
