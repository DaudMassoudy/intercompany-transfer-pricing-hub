# TP Arrow Mark Branding Patch

This package applies the TP Arrow Mark to the enterprise Intercompany Transfer Pricing Hub, based on the previously supplied TP Arrow concept: white T, vivid blue P and rising arrow on a dark navy rounded-square field.

Updated:
- frontend/components/Shell.tsx: replaces text TP placeholder with branded SVG image.
- frontend/app/globals.css: increases sidebar mark size to 44 px and removes default blue badge style.
- frontend/public/tp-arrow-mark.svg and .png: reusable logo assets.
- frontend/app/icon.svg, favicon.ico, apple-icon.png: browser / touch icons.
- frontend/app/layout.tsx: explicit icon metadata.

The starting archive was the MINIO_FIXED release; its MinIO image override and launcher-side fixes are preserved. External image mirror availability is not guaranteed. No database, business-logic, API, or workflow files were changed.

Start: extract to a fresh folder, open Docker Desktop, run START_OTP.bat; a frontend image rebuild is required to see changes. If the browser has cached an old favicon, use a hard refresh or a private window.

Verification: archive integrity, asset rendering and source changes checked; full Docker startup was not executed in this environment.
