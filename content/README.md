# Downloadable content

Files in this folder are uploaded to the private content bucket by
`deploy/deploy.sh`. They are never served directly: the backend hands out
short-lived download links.

The four guide PDFs are built from the text files in `docs/guides/`. To change
one, edit its text file and run `python3 tools/build_guides.py` from the repo
root. The format is explained at the top of that script.

To add a file:

1. Put it in `guides/` (anyone can download) or `members/` (sign-in needed).
   The folder is only a convention; access is controlled by the catalogue.
2. Add an entry to `backend/content_catalogue.json`:

   ```json
   {
     "id": "lowercase-words-with-dashes",
     "title": "Shown to users",
     "description": "One sentence about the file.",
     "file": "guides/your-file.pdf",
     "requires_login": false
   }
   ```

3. Record the file's source in the assets log.
4. Run `deploy/deploy.sh`.

The app checks the catalogue at start-up and refuses to start if an entry is
malformed.
