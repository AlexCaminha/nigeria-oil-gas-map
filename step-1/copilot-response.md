CSV export (template and notes)

I couldn't find any oil block or field text data in the PDF's extracted text, so I created a CSV template with the exact columns you requested. If you want me to fill it, please upload a higher-resolution image/PDF of the map or a transcription of the block/field labels and their colors; I can then extract coordinates and statuses.

Two lines from the uploaded document:
"Addax's Licence Interests"
"Date: June 2005".

CSV (UTF-8) — headers only
oil block number,licensee,status,oil field name,developed_or_undeveloped,type,estimated Longitude,estimated Latitude

How I will populate the CSV once map details are available
- oil block number — read the OPL/OML identifier printed inside each block.
- licensee — the name printed beneath the block identifier.
- status — determined from the block background color using your legend (e.g., #FFFF00 → Returned to NNPC; #BEFFB0 → Onshore licensed; etc.).
- oil field name — text inside the block boundary; uppercase = developed, mixed case = undeveloped.
- developed_or_undeveloped — inferred from field name case.
- type — inferred from the field background color (#00FF00 → Oil or Oil/Gas; #FF0000 → Gas or Gas/Condensate).
- estimated Longitude / Latitude — estimated from the map extents you gave (Longitude 2°E–10°E, Latitude 2°N–8°N) by visually placing the field centroid relative to the map bounds.

Next steps (pick one)
- Upload a clearer scan or a high-resolution image of the map so I can read block/field labels and colors and produce a fully populated CSV.
- Or paste a short text list of the blocks/fields and their colors/positions and I will convert that into the CSV.
Tell me which option you prefer and I’ll produce the completed CSV.