# German Localisation — v2.0.0-rc.1

## Scope

The application supports a professional bilingual German/English user experience without changing authoritative accounting or Transfer Pricing calculations.

### Language behaviour

- Supported UI languages: `de` and `en`.
- German browser/system language defaults to German on first use.
- The DE/EN switch is available on the login screen and in the authenticated shell.
- The selected language is stored as `otp_language` in browser local storage.
- The document `<html lang>` attribute is updated when the user changes language.
- Internal API identifiers, database enums, policy codes, GL accounts, entity codes and audit object identifiers remain language-neutral.

## German finance and TP terminology

Examples:

| Internal / English | German UI |
|---|---|
| Control Tower | Steuerungszentrale |
| Legal Entity | Rechtliche Gesellschaft |
| Limited-Risk Distributor | Vertriebsunternehmen mit begrenztem Risiko (LRD) |
| Contract Manufacturer | Auftragsfertiger |
| Shared Services | Shared Services |
| TP Policy | TP-Richtlinie |
| Mapping | Zuordnung |
| Allocation | Umlage |
| Revenue | Umsatzerlöse |
| COGS | Umsatzkosten (COGS) |
| Gross Profit | Bruttoergebnis |
| OPEX | Operative Aufwendungen (OPEX) |
| True-Up | True-Up / Anpassung |
| Approval | Freigabe |
| Journal | Buchungsjournal |
| Posting Reconciliation | Buchungsabstimmung |
| Audit Trail | Prüfpfad |

Internationally established abbreviations such as TNMM, ROS, EBIT, PLI, ERP, YTD and YTG are retained. Method names may include a German description while preserving the standard abbreviation.

## Locale-aware formatting

German (`de-DE`):

- Currency example: `1.891.110 €`
- Percentage example: `4,00 %`
- Number example: `1.000.000,25`
- Date/time uses German locale conventions.

English (`en-GB`) retains English/European display conventions.

Simulation inputs accept German-formatted numeric strings such as `0,04` and `-1.000.000` in German mode.

## Copilot localisation

`GET /api/v1/ai/explain/{entity_code}?lang=de` produces a deterministic German explanation with German numerical formatting. The result remains evidence-grounded and advisory. No authoritative calculation is delegated to AI.

## Validation

The localisation release is validated by:

1. backend regression suite including a German Copilot response test;
2. frontend import/source validation including the localisation module;
3. TypeScript/TSX transpilation preflight;
4. release structure validation requiring the bilingual localisation assets;
5. clean ZIP integrity validation.

German localisation does not alter TP formulas, policy logic, approval controls, ERP posting logic, reconciliation logic or tenant/security boundaries.
