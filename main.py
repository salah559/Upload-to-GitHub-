from flask import Flask, request, render_template_string
import requests
import base64

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GitHub Uploader</title>
</head>
<body>
    <h2>Upload File to GitHub</h2>
    <form method="POST" enctype="multipart/form-data">
        <label>GitHub Token:</label><br>
        <input type="password" name="token" required><br><br>
        <label>GitHub Username:</label><br>
        <input type="text" name="username" required><br><br>
        <label>Repository Name:</label><br>
        <input type="text" name="repo" required><br><br>
        <label>File:</label><br>
        <input type="file" name="file" required><br><br>
        <button type="submit">Upload</button>
    </form>
    {% if message %}
        <p>{{ message }}</p>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    if request.method == "POST":
        token = request.form["token"]
        username = request.form["username"]
        repo = request.form["repo"]
        file = request.files["file"]
        content = base64.b64encode(file.read()).decode("utf-8")

        url = f"https://api.github.com/repos/{username}/{repo}/contents/{file.filename}"
        headers = {"Authorization": f"token {token}"}
        data = {
            "message": f"upload {file.filename}",
            "content": content
        }
        response = requests.put(url, headers=headers, json=data)
        if response.status_code in [200,201]:
            message = f"✅ File '{file.filename}' uploaded successfully!"
        else:
            message = f"❌ Error: {response.json()}"
    return render_template_string(HTML_FORM, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
