# Deployment

This app is prepared for Streamlit Community Cloud using Python 3.12, branch main and entry point app.py. The default dataset is the author's supplied fictional demonstration dataset, published only as the minimized projection in data/demo.csv. No secret or external data service is required.

1. Run python -m pip install -r requirements-dev.txt, python -m pip check and python -m pytest from the project root.
2. Review the exact tracked file list and DATA_PROVENANCE.md. Include only data/demo.csv; do not commit the full input or private audit materials.
3. Push the reviewed code to its own new GitHub repository and verify the Tests workflow. The workflow runs on Windows and Linux.
4. Open Streamlit Community Cloud, choose Create app and the GitHub repository, select main and app.py, and set Python 3.12 in Advanced settings. Leave PROPERATI_ALLOW_UPLOADS unset so the public site remains a bundled demonstration.
5. Verify the resulting public URL in an unauthenticated browser at desktop and mobile widths. Check the author-declaration notice, predictions, validation and evaluation before claiming the app is live.

Official guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
