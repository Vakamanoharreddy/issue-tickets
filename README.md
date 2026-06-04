# Flask Ticketing App

This repository contains a Flask application that uses templates under `Template/requirement` and static assets under `static/`.

## Option 1: Deploy as a Flask app

This is the recommended approach for the full application.

1. Choose a Python host:
   - Railway
   - Render
   - Heroku
   - PythonAnywhere
2. Deploy this repository directly.
3. The repository includes:
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
4. The app entrypoint is `file.py` and the WSGI app object is `app`.

### Example with Heroku / Railway

- Install dependencies with `pip install -r requirements.txt`
- Start locally with `gunicorn file:app` or `python file.py`
- Configure environment variables (`SECRET_KEY`, `SMTP_USERNAME`, `SMTP_PASSWORD`, etc.)

## Option 2: GitHub Pages static landing page

GitHub Pages cannot run Python/Flask. To avoid a 404 on GitHub Pages, this repo now includes a static site at `docs/index.html`.

To enable it:

1. Open GitHub repo settings.
2. Go to Pages.
3. Set source to branch `main` and folder `/docs`.
4. Save and wait for the site to publish.

> The static GitHub Pages site is only a landing page. The real application still needs a Flask server.

## Notes

- Do not expect GitHub Pages to serve the full ticketing app.
- Use the Flask deployment option for the working backend.
