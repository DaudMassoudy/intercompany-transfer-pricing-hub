Intercompany Transfer Pricing Hub v2.0.0-rc.2

RC.1 upgrades the supplied RC.10 application in-place. Key additions are a governed enterprise Master Data Catalog and a configurable Allocation Workbench replacing the fixed €1m primary demo action. Automated backend validation: 100/100 tests pass; measured overall backend coverage: 84%. See docs/VALIDATION_REPORT.md and docs/FUNCTIONAL_COVERAGE_MATRIX.md for limits and open qualification gates.

ENTERPRISE OPERATIONAL TRANSFER PRICING PLATFORM v2.0.0-rc.2
================================================================
Release-Klasse / Release class: Internal Enterprise Release Candidate (external production qualification required)

DEUTSCH — SCHNELLSTART
1. Docker Desktop installieren/starten.
2. ZIP in einen neuen Ordner entpacken.
3. START_DEMO.bat doppelklicken.
4. Gesundheitschecks und Smoke-Test abwarten.
5. Der Browser öffnet die Anwendung automatisch. Die App bevorzugt Port 3000 und wählt bei Belegung automatisch einen freien Folgeport.
6. Die Oberfläche startet in deutscher Sprache bei deutscher Browser-/Systemsprache. Oben rechts kann jederzeit zwischen DE und EN gewechselt werden.

Demo-Benutzer
Analyst:      analyst@otp.local / Demo-Analyst-2026!
TP Manager:   manager@otp.local / Demo-Manager-2026!
Finance:      finance@otp.local / Demo-Finance-2026!
Local Finance: local.finance@otp.local / Demo-LocalFinance-2026!
Data Steward: data.steward@otp.local / Demo-DataSteward-2026!
Tax Director: tax.director@otp.local / Demo-Director-2026!
Admin:        demo.admin@otp.local / Demo-OTP-2026!

Die Demo-Kennwörter sind ausschließlich für die lokale, fiktive Demo bestimmt und dürfen nicht in Produktion wiederverwendet werden.
START_DEMO.bat erzeugt zufällige Infrastruktur-/JWT-/n8n-Secrets in einer lokalen .env-Datei.


RC.1 KONFIGURIERBARE PROFITABILITÄTS- UND STAMMDATEN-DEMO
1. Für Finanzdaten mit Local Finance / TP Analyst / Admin anmelden. Für Gesellschaftsstamm mit Data Steward anmelden.
2. sample_data\20_Authoritative_PnL_Demo.csv unter Datenimporte laden.
3. Datenqualität prüfen: 500 akzeptiert, 0 abgelehnt.
4. Zuordnungen ausführen: 500/500, 100% Abdeckung.
5. Umlagen: die vorkonfigurierte Group-IT-Regel öffnen, EUR 1 Mio. nur als Beispieldaten eingeben, zuerst simulieren und danach ausführen; Restbetrag EUR 0. Der Betrag ist nicht fest im Produkt verdrahtet.
6. Importierte GuV: maßgebliche GuV für 2026-09 erstellen.
7. DE01 prüfen: Umsatz EUR 111,9 Mio.; EBIT EUR 2,58489 Mio.; ROS 2,31%; Zielanpassung EUR 1,89111 Mio.
8. Abweichungsanalyse: DE01 gegen BUDGET ausführen; Kontrollrest EUR 0.
9. Danach Prognose → True-Up → Freigaben → Journal → SAP-Simulator → Abstimmung.

Wichtige Skripte
START_DEMO.bat    Startet die befüllte Demo-Umgebung.
START_OTP.bat     Startet den persistenten lokalen Modus ohne Datenreset.
STATUS_OTP.bat    Zeigt Dienste, Migrationen und API-Status.
BACKUP_OTP.bat    Erstellt ein lokales Backup mit Prüfsummen.
RESTORE_OTP.bat   Prüft und stellt ein Backup wieder her.
RESET_DEMO.bat    Setzt ausschließlich die Demo-Docker-Volumes zurück.
STOP_OTP.bat      Stoppt Dienste ohne persistente Volumes zu löschen.

ENGLISH — QUICK START
1. Install/start Docker Desktop.
2. Extract this ZIP to a new folder.
3. Double-click START_DEMO.bat.
4. Wait for health checks and smoke test.
5. The launcher opens the application automatically and selects collision-safe host ports when required.
6. Use the DE / EN switch in the top-right corner to change the UI language.

Qualification note
This is an Enterprise Production Release Candidate, not a claim of customer production qualification. See docs\EXTERNAL_QUALIFICATION_REQUIRED.md.

Evidence
See docs\VALIDATION_REPORT.md, docs\GERMAN_LOCALISATION.md and docs\PRODUCTION_QUALIFICATION_SCORECARD.md.


RC.1 STAMMDATEN-GOVERNANCE
- Gesellschaften: neue Gesellschaft anlegen oder bestehende Gesellschaft bearbeiten.
- Stammdatenänderungen werden als Entwurf gespeichert und versioniert.
- Maker-Checker: Data Steward erstellt/einreicht; TP Manager/Tax genehmigt.
- Gesellschaftsstamm kann zusätzlich aus sample_data\01_Entity_Master.xlsx als kontrollierte Bulk-Vorschau eingelesen werden.
- Fehlende Excel-Zeilen lösen niemals automatisch Löschung/Deaktivierung aus.

RC.1 ENTERPRISE MASTER DATA CATALOG
- Zusätzlich zum Gesellschaftsstamm können Partner, GL-Konten, Kosten-/Profitcenter, Werke, Business Units, Produktgruppen/SKUs, Kunden, Lieferanten, Währungen, FX-Quellen, Transaktionstypen und TP-Segmente über kontrollierte Änderungsanträge gepflegt werden.
- Genehmigte Änderungen werden versioniert; Deaktivierungen wirken bei unterstützten operativen Stammtabellen in die Laufzeitlogik.
- Details: docs\USER_GUIDE.md und docs\FUNCTIONAL_COVERAGE_MATRIX.md.


Note: In rc.2, START_DEMO.bat and START_OTP.bat attempt to start Docker Desktop automatically if it is installed but not already running.


RC.3 environment fix: the generated `.env` now uses the same release/project identifiers as the launcher and is compatible with Windows PowerShell 5.1.

RC.5 DATABASE STARTUP HARDENING
------------------------------
RC.5 automatically verifies and, when necessary, repairs the local PostgreSQL
role password before FastAPI starts. This preserves the database volume and
prevents a stale .env / persistent-volume password mismatch from breaking
one-click startup. Do not delete Docker volumes unless RESET_DEMO.bat is
explicitly intended.

LOCAL 10/10 PRACTICALITY QUALIFICATION (v2.4.0-rc.3-hotfix7)
------------------------------------------------------
For final machine-specific proof of all 15 target layers, double-click:

    QUALIFY_10_10.bat

It starts the real Docker stack, preserves normal data volumes, runs backend regression/coverage, validates the release, executes Chromium browser + live API UAT for every target layer, generates qualification\results\LOCAL_10_10_QUALIFICATION.md, synchronizes the evidence into the Qualification Center, and only reports 10/10 for a layer when its mandatory checks pass on that computer.

This is intentionally stricter than a static scorecard. External customer/third-party certification (live ERP, customer IdP, independent penetration test, customer Finance/TP UAT, parallel production close and production DR) remains separately labelled EXTERNAL QUALIFICATION REQUIRED.

v2.4.0-rc.3-hotfix7 QUALIFICATION NOTE
------------------------------
QUALIFY_10_10.bat now REUSES an already healthy OTP runtime. If the application is
already open and healthy, Step 1 should complete within seconds and must not rebuild it.
The first-ever Step 2 may still take several minutes because Docker may need to download
the pinned Playwright/Python qualification images; build/download progress is now shown
live in the command window.
