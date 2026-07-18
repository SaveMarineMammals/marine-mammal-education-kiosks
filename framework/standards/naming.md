# Naming

| Thing | Pattern | Example |
| --- | --- | --- |
| Exhibit slug | `kebab-case` | `humpback-migration` |
| Git path | `exhibits/<slug>/` | `exhibits/humpback-migration/` |
| Xibo Library folder | `exhibits/<slug>` | `exhibits/humpback-migration` |
| Exhibit tag | `exhibit:<slug>` | `exhibit:humpback-migration` |
| Role tag | `role:<role>` | `role:hero-video` |
| Playlist tag | `playlist:<name>` | `playlist:attract-loop` |
| Display group | location/role | `lobby`, `classroom-a` |
| Player hostname | `kiosk-<location>-<nn>` | `kiosk-lobby-01` |
| Layout template id | `kebab-case` | `full-bleed-video` |
| Content version | semver | `1.2.0` |

Never rename a slug after `published`. Retire and create a new exhibit if a rename is unavoidable.
