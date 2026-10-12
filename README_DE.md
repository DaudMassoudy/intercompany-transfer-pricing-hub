# Intercompany Transfer Pricing Hub — Operations, Analytics & Governance

**Version:** 2.4.0-rc.3-hotfix7  
**Release-Klasse:** Enterprise Production Release Candidate  
**Sprachen:** Deutsch (de-DE) und Englisch (en-GB)  
**Architektur:** Next.js + FastAPI + PostgreSQL + Redis + MinIO + n8n + deterministische Python-TP-Engine


## Hotfix 7 – zuverlässige Qualifikation

Hotfix 7 trennt die unveränderliche Paketvalidierung von veränderlichen Testartefakten. Die Release-Validierung läuft vor pytest, Coverage/Cache werden nach `qualification/results` umgeleitet, die lokale `.env` wird während der Paketvalidierung temporär isoliert und anschließend wiederhergestellt, und aktuelle Release-Evidenz wird vor dem Browser-UAT synchronisiert. Siehe `docs/HOTFIX7_QUALIFICATION_ISOLATION.md`.

## Zweck

Die Plattform operationalisiert genehmigte Verrechnungspreisrichtlinien entlang eines kontrollierten End-to-End-Prozesses:

**ERP-/Finanzdaten → Import → Validierung → ERP→TP-Zuordnung → Umlagen → maßgebliche importierte GuV → methodenkonsistente TP-Berechnung → YTD/YTG-Überwachung → deterministische Abweichungsanalyse → Simulation → True-Up → mehrstufige Freigabe → Buchungsjournal → ERP-Adapter → Abstimmung → Audit/Evidenz.**

## Deutsche Lokalisierung

Die Benutzeroberfläche ist vollständig zweisprachig. Bei deutscher Browser-/Systemsprache wird Deutsch automatisch vorausgewählt; die Auswahl kann oben rechts mit **DE / EN** gewechselt und wird lokal gespeichert.

Die Lokalisierung umfasst insbesondere:

- Navigation, Seitentitel, Hinweise und Aktionen;
- Verrechnungspreis- und Finance-Terminologie;
- Statuswerte und Freigaberollen;
- deutsche Zahlen-, Währungs-, Prozent-, Datums- und Zeitformate;
- deutsche Eingabeformate in Simulationen, z. B. `0,04` oder `-1.000.000`;
- deutschsprachige deterministische Antworten des TP Evidence Copilot;
- deutsche Darstellung von Richtlinien, TP-Methoden, PLIs, Ausnahmen und Buchungsinformationen.

Fachliche Standardabkürzungen wie **TNMM, ROS, EBIT, PLI, ERP, YTD und YTG** bleiben erhalten, damit die Anwendung mit international üblichen TP-Begriffen kompatibel bleibt.

## Schnellstart unter Windows

1. Docker Desktop starten.
2. ZIP in einen neuen Ordner entpacken.
3. `START_DEMO.bat` doppelklicken.
4. Auf die erfolgreichen Health Checks warten.
5. Browser öffnet sich automatisch.

## Demo-Benutzer

| Rolle | Benutzer | Passwort |
|---|---|---|
| TP Analyst | `analyst@otp.local` | `Demo-Analyst-2026!` |
| TP Manager | `manager@otp.local` | `Demo-Manager-2026!` |
| Finance Controller | `finance@otp.local` | `Demo-Finance-2026!` |
| Local Finance | `local.finance@otp.local` | `Demo-LocalFinance-2026!` |
| Master Data Steward | `data.steward@otp.local` | `Demo-DataSteward-2026!` |
| Group Tax Director | `tax.director@otp.local` | `Demo-Director-2026!` |
| Platform Admin | `demo.admin@otp.local` | `Demo-OTP-2026!` |

## Produktionsqualifizierung

Die RC-Version ist intern validiert, aber nicht als kundenspezifisch „Production Qualified“ zertifiziert. Externe Qualifizierungsschritte wie Live-SAP-Sandbox, unabhängiger Penetrationstest, Enterprise-IdP-Validierung, TP-/Finance-UAT und DR-Test bleiben separat nachzuweisen. Details: `docs/EXTERNAL_QUALIFICATION_REQUIRED.md`.

## RC.7: importierte Daten als maßgebliche GuV

Neu in RC.7 ist die geschlossene Datenkette von importierten ERP-Zeilen bis zur Steuerungszentrale. Nutzen Sie für die Demo `sample_data/20_Authoritative_PnL_Demo.csv` (500 deterministische Zeilen), führen Sie danach Mapping und die EUR-1-Mio.-IT-Umlage aus und erstellen Sie unter **Importierte GuV** den 2026-09-P&L-Lauf. DE01 ergibt anschließend EUR 111,9 Mio. Umsatz, EUR 2,58489 Mio. EBIT, 2,31 % ROS und EUR 1,89111 Mio. Zielanpassung.

Unter **Abweichungsanalyse** kann der EBIT-Unterschied gegenüber BUDGET additiv in Umsatz, COGS, direkte OPEX und Umlagen zerlegt werden. Die Komponentensumme muss mit der gesamten EBIT-Abweichung übereinstimmen; der Kontrollrest beträgt im Referenzfall EUR 0.

Unter **Production Qualification Center** werden intern belegbare Engineering-Kontrollen getrennt von externen Produktions-Gates geführt. Externe SAP-, PenTest-, IdP-, TP-/Finance-UAT-, Parallel-Close- und DR-Nachweise werden nicht selbst zertifiziert.


## RC.10: Governance für den Gesellschaftsstamm

Die Seite **Gesellschaften** ist jetzt eine echte Stammdatenverwaltung. Neue Gesellschaften und Änderungen werden nicht direkt in der produktiven Tabelle überschrieben, sondern als versionierte Änderungsanträge geführt. Der Master Data Steward kann Entwürfe anlegen, bearbeiten und zur Prüfung einreichen. Eine getrennte freigabeberechtigte Rolle (z. B. TP Manager oder Group Tax Director) muss die Änderung genehmigen, bevor sie in PostgreSQL wirksam wird.

`01_Entity_Master.xlsx` bleibt als kontrollierter Bulk-Onboarding-Kanal verfügbar: Vorschau → Validierung → Änderungsanträge → Maker-Checker-Freigabe. Das Fehlen einer Gesellschaft in Excel wird niemals als Löschung interpretiert.


Note: In rc.2, START_DEMO.bat and START_OTP.bat attempt to start Docker Desktop automatically if it is installed but not already running.


RC.3 environment fix: the generated `.env` now uses the same release/project identifiers as the launcher and is compatible with Windows PowerShell 5.1.

## v2.4.0-rc.3 Praxis-Upgrade

Dieses Release erweitert insbesondere mehrstufige Umlagen, Benchmark-Comparables, gesteuerte Freigaben, Journal-Templates, Reconciliation-Kontrollen, Evidence Packs, Abhängigkeitsanalysen und Audit-Nachvollziehbarkeit. Es bleibt ein Release Candidate; externe ERP-, IdP-, Penetrationstest- und Kunden-UAT-Qualifizierungen werden nicht selbst als bestanden ausgewiesen.

## Ein-Klick-Qualifizierung der 10/10-Praxistauglichkeit

Nach dem Entpacken unter Windows `QUALIFY_10_10.bat` doppelklicken. Die Qualifizierung startet die reale Docker-Anwendung, führt Backend-Regression/Coverage und Release-Validierung aus, testet alle 15 Ziel-Layer mit Chromium/Playwright und Live-API-UAT, erzeugt `qualification/results/LOCAL_10_10_QUALIFICATION.md` und synchronisiert die Evidenz in das Qualification Center. Ein Layer wird nur dann mit 10/10 ausgewiesen, wenn seine verpflichtenden lokalen Laufzeitprüfungen bestehen.
