# Schema Extractor

A small API that pulls structured data out of documents. You describe what you need in plain language, for example "invoice number, issue date, gross total". A model turns that into a schema. Then you upload a PDF or an image and get back JSON that matches the schema.

## What it does

- Generates an extraction schema from a text description.
- Lets you refine the schema with feedback. Every change is saved as a new version, so you can look at the history or go back to an older version.
- Extracts data from a document using a chosen schema version. The file is sent straight to the model, there is no separate text extraction step.
- Keeps each user's schemas and results private.

Extraction runs in the background. You upload a file, get an id back right away, and check the status until it is done.

## Stack

Python 3.12, FastAPI, Pydantic AI (Gemini), PostgreSQL, SQLAlchemy, Docker Compose, uv.

## Running it

You need Docker and a Gemini API key.

```bash
cp .env.example .env
```

Fill in `SECRET_KEY` and `SCHEMA_MODEL__API_KEY` in `.env`.

Then start the app:

```bash
docker compose up --build api
```

The API listens on http://localhost:8000. Interactive docs are at http://localhost:8000/docs.

The Extractionstatus goes from `pending` to `running` to `done` or `failed`. By default the latest schema version is used. Add `-F "version=1"` to pin an older one.

## Configuration

Settings come from environment variables or the `.env` file.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs login tokens. Required. |
| `SCHEMA_MODEL__API_KEY` | Gemini API key. Required. |
| `SCHEMA_MODEL__NAME` | Model name, for example `google/gemini-3-flash-preview`. |
| `USE_SAME_MODEL` | If true, extraction uses the same model as schema generation. |
| `EXTRACTION_MODEL__NAME`, `EXTRACTION_MODEL__API_KEY` | Separate model for extraction, used when `USE_SAME_MODEL` is false. |
| `POSTGRES_PASSWORD` | Database password used by Docker Compose. |
| `MAX_UPLOAD_MB` | Maximum upload size. Default 10. |

Supported files are PDF, PNG, JPEG and WebP. The type is checked from the file contents, not the extension.

## Things to know

- Uploaded files are deleted as soon as processing ends, whether it worked or not.
- Documents are sent to Google's API, so do not upload anything you are not allowed to share with a third party.
- Background jobs run inside the server process. A restart interrupts them, and on startup they are marked as failed.
- Only the Google provider is implemented. Adding another one means a new case in `llm/factory.py`.
