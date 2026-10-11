# Data and privacy

The default app uses a minimized projection of the CSV supplied by the project author, who explicitly declared that dataset fictional and authorized publication of this projection. This declaration has not been independently verified. The bundled prices and evaluation results are demonstration data, not observations of actual transactions or evidence of market accuracy. The default is not replaced by independently generated example data.

Only eight necessary fields are published: property_type, neighborhood, area_total, area_covered, rooms, lat, lon, price_usd. Coordinates are rounded to three decimal places before a second validation and duplicate check. This reduces their precision; it is not a proof of anonymization or of any claim about the original data. Unit price, covered-area ratio and spatial groups are recomputed at runtime.

The full input CSV is not distributed. Free text, titles, descriptions, names, contacts, addresses, URLs, image links, export indices, unused features and private audit materials are excluded. Labels are restricted to known property types and CABA neighborhood names. No external data provider, map service or geocoder is called.

Uploads are disabled by default. Set PROPERATI_ALLOW_UPLOADS=1 only for intentional use, preferably a local server. Uploading sends the file from the browser to the server running Streamlit. Do not upload data you are not authorized to process there. The application does not save uploads to disk, log their contents or share a global data cache. Hosting infrastructure and the browser may have their own retention behavior. The author's fictional-data declaration applies to the bundled dataset, not automatically to arbitrary visitor uploads.

Review the exact staged file list before publication. The only data-file exception in .gitignore is data/demo.csv. Original inputs, transfer metadata and private reports must remain outside this repository. See DATA_PROVENANCE.md for the source declaration and transformation.
