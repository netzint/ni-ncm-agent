# ni-ncm-agent

Debian-/Ubuntu-Paket des **Netzint Centralized Monitoring (NCM) Agent**.
Installiert auf einem Zielhost die Icinga2-Konfiguration, die benötigten
Nagios-Plugins und registriert den Host am NCM-Master oder -Satellite.

Maintainer: Lukas Spitznagel &lt;lukas.spitznagel@netzint.de&gt; – Netzint GmbH.

## Inhalt

Das Paket installiert:

- `/usr/bin/ni-ncm-agent` – Registrierungs-/Installer-CLI für Icinga2
- `/usr/lib/nagios/plugins/` – Monitoring-Plugins:
  - `check_bbb_cluster.py` – Scalelite/BBB-Cluster-Status
  - `check_docker.py` – Status laufender Docker-Container
  - `check_linux_memory` – Speicherauslastung
  - `check_pbs.py` – Proxmox Backup Server (Version, Disks, Datastores, GC)
  - `check_proxmox.py` – Proxmox VE (Cluster, Ceph, Storage, Disks, VMs, Backups, OSDs)
  - `check_usb_apc.py` – APC-USV via `apcaccess`
- `/etc/sudoers.d/ncm` – `NOPASSWD`-Rechte für den `nagios`-User auf
  `pvesh`, `ceph`, `proxmox-backup-debug`, `proxmox-backup-manager`
  (Docker läuft bewusst **nicht** über sudo – siehe Sicherheitshinweise)

In `preinst` wird zusätzlich das Icinga-Repository
(`https://packages.icinga.com/${ID}`) inkl. GPG-Key eingerichtet.
In `postinst` wird das Konfigurationsverzeichnis
`/etc/netzint/ni-ncm-agent` angelegt; falls Docker installiert ist,
wird `nagios` in die `docker`-Gruppe aufgenommen und eine ACL auf
`/var/run/docker.sock` gesetzt.

## Unterstützte Plattformen

Pro Release werden Pakete für folgende Distributionen gebaut
(siehe `buildpackage.sh`):

| Distribution     | Codename   |
| ---------------- | ---------- |
| Ubuntu 18.04 LTS | `bionic`   |
| Ubuntu 20.04 LTS | `focal`    |
| Ubuntu 22.04 LTS | `jammy`    |
| Ubuntu 24.04 LTS | `noble`    |
| Ubuntu 26.04 LTS | `resolute` |
| Debian 10        | `buster`   |
| Debian 11        | `bullseye` |
| Debian 12        | `bookworm` |
| Debian 13        | `trixie`   |

> **Hinweis zum Umbenennen `nobel` → `noble`:** Frühere Releases haben den
> Suffix `-nobel` benutzt. Auf einem reprepro-Server, der bisher eine
> Distribution `nobel` ausgeliefert hat, lässt sich die Kompatibilität für
> alte Clients erhalten. Siehe Abschnitt
> [Reprepro: Alias für `nobel`/`noble`](#reprepro-alias-für-nobelnoble).

## Bauen

Lokal:

```bash
sudo apt-get install debhelper fakeroot
./buildpackage.sh
```

Das Skript iteriert über die Plattformen, generiert pro Plattform eine
`debian/changelog` aus `debian/changelog.template` und ruft
`dpkg-buildpackage` auf. Die Artefakte landen im übergeordneten Verzeichnis
(`../*.deb`, `../*.changes`, `../*.dsc`, `../*.tar.*`).

Automatisiert über GitHub Actions: ein Tag `v*` triggert
`.github/workflows/release.yml` (Build), anschließend
`publish-release.yml` (Upload auf den Paket-Server via SSH/scp und
`/usr/local/bin/publish-debs ncm`).

## Installation

```bash
sudo apt install ./ni-ncm-agent_<version>_all.deb
```

Falls weder `/etc/os-release` noch das Icinga-Repository erkannt werden,
kann ein Fallback in `/etc/netzint/ni-ncm-agent/icinga-repo.ini` gelegt
werden:

```ini
ID=ubuntu
VERSION_CODENAME=jammy
```

## Verwendung

Registrierung am NCM-Master:

```bash
sudo ni-ncm-agent --master --name <hostname> --install
```

Registrierung an einem Satellite:

```bash
sudo ni-ncm-agent --satellite \
    --name <hostname> \
    --ncm-name <satellite-cn> \
    --ncm-address <satellite-ip-or-fqdn> \
    --install
```

Weitere Optionen: `--debug`, `--quiet`.

## Release

1. Versionsblock oben in `debian/changelog.template` ergänzen
   (`%platform%`-Platzhalter beibehalten).
2. Commit + Tag `vX.Y.Z` pushen – die Pipeline baut, erstellt das
   GitHub-Release und veröffentlicht auf dem Paket-Server.

## Reprepro: Alias für `nobel`/`noble`

Ab Version 1.3.5 wird der korrekte Ubuntu-Codename `noble` für 24.04
verwendet (statt der historischen Tippfehler-Variante `nobel`). Reprepro
unterstützt das direkt über die Felder `Suite:` (Client-Alias) und
`AlsoAcceptFor:` (Upload-Alias).

In `conf/distributions` den `noble`-Block so anpassen:

```
Codename: noble
Suite: nobel
AlsoAcceptFor: nobel
Components: main
Architectures: amd64 source
# ... weitere bestehende Felder (SignWith, Description, ...) bleiben
```

Anschließend einmalig neu exportieren:

```bash
reprepro export noble
```

Was das bewirkt:

- **`Suite: nobel`** – reprepro legt automatisch den Symlink
  `dists/nobel → dists/noble` an. Clients mit
  `deb https://repo.example/ncm nobel main` in ihrer `sources.list`
  greifen transparent auf die `noble`-Distribution zu, ohne dass
  irgendetwas dupliziert werden muss.
- **`AlsoAcceptFor: nobel`** – `.changes`-Dateien, deren
  `Distribution:`-Feld noch `nobel` sagt (z. B. Pakete aus alten
  Buildständen), werden trotzdem in `noble` einsortiert. Neue Builds
  mit `Distribution: noble` funktionieren ohnehin.

Sobald keine Clients mehr `nobel` benutzen, lassen sich die beiden
Zeilen wieder entfernen.

> **Migrationspfad:** `apt` betrachtet `-noble` als höher als `-nobel`
> (Position 3: `b` < `l`), eine Aktualisierung auf das neue Paket
> erfolgt also automatisch.

## Sicherheit

Mit Release 1.3.5 wurden folgende Punkte behoben (Details siehe
`debian/changelog.template`):

- **Shell-Injection:** Die Plugins `check_pbs.py`, `check_proxmox.py` und
  `check_bbb_cluster.py` benutzten `os.popen` mit konkatenierten
  Argumenten. Sie nutzen jetzt `subprocess.run([...], shell=False)`.
- **Sudoers gehärtet:** Die Zeile
  `nagios ALL=NOPASSWD: /usr/bin/docker` ist entfernt. `nagios` wird in
  die `docker`-Gruppe aufgenommen und erhält zusätzlich per ACL Zugriff
  auf den Docker-Socket. Damit ist kein `sudo`-Pfad mehr nötig, um
  Container-Status abzufragen.
- **`preinst` gehärtet:** `set -euo pipefail`, GPG-Key wird über eine
  Temp-Datei heruntergeladen und gegen leeren Download geprüft.
- **GitHub Actions aktualisiert:** `actions/checkout@v4`,
  `softprops/action-gh-release@v2`, `appleboy/scp-action@v0.1.7`,
  `appleboy/ssh-action@v1.0.3`. Runner auf `ubuntu-24.04`.
- **`sudo-rs`-Kompatibilität (Ubuntu 25.10+/26.04):** `postinst` setzt
  `/etc/sudoers.d/ncm` explizit auf `0440 root:root`. Damit liest sowohl
  klassisches `sudo` als auch das in 26.04 standardmäßig aktive `sudo-rs`
  die Regeln zuverlässig.

Bekannte verbleibende Punkte (bewusst so belassen):

- Der NCM-Ticket-Endpoint nutzt ein hartkodiertes Service-Identifier-
  Passwort (kein per-User-Geheimnis). Wenn das Verhalten geändert
  werden soll, müsste serverseitig ebenfalls migriert werden.
- Einzelne logische Sonderfälle (z. B. Mapping `HEALTH_ERR` → warn statt
  critical in `check_proxmox.py`, ungenutzte lokale `critical`-Variable
  in `storage-status`) wurden nicht angefasst, weil sie das
  Monitoring-Verhalten ändern würden.

## Lizenz

Interne Software der Netzint GmbH. Einzelne Plugins (z. B.
`check_linux_memory`, `check_bbb_cluster.py`) stammen aus Drittquellen
und stehen unter ihrer jeweiligen Lizenz (GPLv3 bzw. die im Header
angegebene).
