
GitHub Dynamic ZIP Uploader
--------------------------
This Flask app accepts a ZIP file upload, extracts it, initializes a git repo (if needed),
and pushes the extracted files to the specified GitHub repository using credentials provided
by the user in the form (username, email, personal access token). The app does NOT store tokens
permanently and cleans up temporary files after use.

Usage:
- Run: python main.py
- Open the web UI, upload a ZIP, provide repo URL and token.
- The app will extract the ZIP, run git commands and push to GitHub.

Security:
- Do NOT use long-lived tokens on public instances. Prefer temporary PATs and revoke after use.
- The app enforces a 200MB upload limit.
