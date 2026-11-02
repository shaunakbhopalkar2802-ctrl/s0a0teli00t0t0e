# SatelliteAlpha web app

Shows monthly ship activity near a port (from open Sentinel-2 vessel detections) and tests whether it is linked
to the next period's excess return of the port company. Research exercise, not investment advice.

## Files
- `app.py` - the web app (Streamlit)
- `requirements.txt` - packages the host installs
- `monthly_ship_counts.csv` - **you create this**: it is produced by the Colab notebook (`SatelliteAlpha_Colab_v3.ipynb`)

## Run it on your own computer (test first)
```
pip install -r requirements.txt
streamlit run app.py
```
Open the address it prints (usually http://localhost:8501). If `monthly_ship_counts.csv` is not in the folder,
the app asks you to upload it.

## Deploy it for free on Streamlit Community Cloud
1. Run the Colab notebook until the end. It downloads `monthly_ship_counts.csv`.
2. Create a free GitHub account and a new **public** repository.
3. Upload `app.py`, `requirements.txt` and `monthly_ship_counts.csv` to the repository
   (Add file -> Upload files). The CSV is small, so this is fine.
4. Go to https://share.streamlit.io and sign in with GitHub.
5. Choose "Create app" (the button wording may differ slightly), pick your repository and branch,
   set the main file path to `app.py`, then press Deploy.
6. After a few minutes you get a public link you can share.

To update the results later: run the notebook again, upload the new CSV to the repository, and the app redeploys by itself.

## Notes
- The big dataset is NOT used inside the app (it is about 700 MB, too large for free hosting).
  The notebook turns it into the small CSV first.
- Stock prices are downloaded live from Yahoo Finance when someone opens the app. If Yahoo is slow or rate-limited,
  wait a minute and reload.
- If a result says it used a fallback setting (wider area or quarterly data), mention that when you report it.
