import os
import zipfile
import tempfile
import subprocess
import shutil
from flask import Flask, request, render_template, redirect, url_for
from pathlib import Path

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit

TEMPLATES_DIR = Path('templates')
TMP_ROOT = Path('tmp')
TMP_ROOT.mkdir(exist_ok=True)

def run(cmd_list, cwd=None, env=None):
    try:
        result = subprocess.run(cmd_list, cwd=cwd, env=env,
                                capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, '', str(e)

@app.route('/', methods=['GET', 'POST'])
def index():
    log_lines = []
    if request.method == 'POST':
        # get form fields
        repo = request.form.get('repo','').strip()
        user = request.form.get('user','').strip()
        email = request.form.get('email','').strip()
        token = request.form.get('token','').strip()

        uploaded = request.files.get('zipfile')
        if not uploaded or uploaded.filename == '':
            log_lines.append('ERROR: No ZIP file uploaded.')
            return render_template('index.html', log='\\n'.join(log_lines))

        if not repo.startswith('https://'):
            log_lines.append('ERROR: Repository URL must be HTTPS and include .git (e.g. https://github.com/user/repo.git)')
            return render_template('index.html', log='\\n'.join(log_lines))

        if not token:
            log_lines.append('ERROR: Personal Access Token is required.')
            return render_template('index.html', log='\\n'.join(log_lines))

        # Save uploaded zip to temp dir
        session_dir = TMP_ROOT / tempfile.mktemp(prefix='sess_')
        session_dir.mkdir(parents=True, exist_ok=True)
        zip_path = session_dir / uploaded.filename
        uploaded.save(str(zip_path))
        size = zip_path.stat().st_size
        log_lines.append(f'Saved upload to {zip_path} ({size} bytes)')

        # Safety size check
        if size > app.config['MAX_CONTENT_LENGTH']:
            log_lines.append('ERROR: Uploaded file exceeds size limit (200MB).')
            shutil.rmtree(str(session_dir), ignore_errors=True)
            return render_template('index.html', log='\\n'.join(log_lines))

        # Extract zip
        try:
            with zipfile.ZipFile(str(zip_path), 'r') as z:
                z.extractall(path=str(session_dir))
            log_lines.append('Extraction completed.')
        except Exception as e:
            log_lines.append('ERROR extracting ZIP: ' + str(e))
            shutil.rmtree(str(session_dir), ignore_errors=True)
            return render_template('index.html', log='\\n'.join(log_lines))

        # Determine project dir: if single top-level folder, use it
        entries = [p for p in session_dir.iterdir() if p.name != uploaded.filename]
        if len(entries) == 1 and entries[0].is_dir():
            project_dir = entries[0]
        else:
            project_dir = session_dir

        log_lines.append(f'Using project directory: {project_dir}')

        # Create askpass script that prints token for git
        askpass = project_dir / 'askpass.sh'
        askpass.write_text(f"#!/bin/sh\\necho {token}\\n")
        os.chmod(str(askpass), 0o700)

        env = os.environ.copy()
        env['GIT_ASKPASS'] = str(askpass)
        # disable interactive prompts
        env['GIT_TERMINAL_PROMPT'] = '0'

        # Initialize git if needed
        rc, out, err = run(['git','rev-parse','--is-inside-work-tree'], cwd=str(project_dir), env=env)
        if rc != 0:
            rc, out, err = run(['git','init'], cwd=str(project_dir), env=env)
            log_lines.append(out); log_lines.append(err)
        else:
            log_lines.append('Already a git repository.')

        # Ensure branch main
        run(['git','branch','-M','main'], cwd=str(project_dir), env=env)

        # Set user config if provided
        if user:
            run(['git','config','user.name', user], cwd=str(project_dir), env=env)
        if email:
            run(['git','config','user.email', email], cwd=str(project_dir), env=env)

        # Add safe directory
        run(['git','config','--global','--add','safe.directory', str(project_dir)], cwd=str(project_dir), env=env)

        # Remote setup: remove existing origin and add provided repo
        run(['git','remote','remove','origin'], cwd=str(project_dir), env=env)
        run(['git','remote','add','origin', repo], cwd=str(project_dir), env=env)

        # Add and commit
        rc, out, err = run(['git','add','.'], cwd=str(project_dir), env=env)
        log_lines.append(out); log_lines.append(err)
        rc, out, err = run(['git','commit','-m','Upload from web UI'], cwd=str(project_dir), env=env)
        log_lines.append(out); log_lines.append(err)

        # Pull remote changes (rebase) and then push
        rc, out, err = run(['git','pull','--rebase','origin','main'], cwd=str(project_dir), env=env)
        log_lines.append(out); log_lines.append(err)

        rc, out, err = run(['git','push','-u','origin','main'], cwd=str(project_dir), env=env)
        log_lines.append(out); log_lines.append(err)
        if rc != 0:
            # try force push as fallback
            rc2, out2, err2 = run(['git','push','-u','origin','main','--force'], cwd=str(project_dir), env=env)
            log_lines.append(out2); log_lines.append(err2)

        # Cleanup
        try:
            askpass.unlink()
        except Exception:
            pass
        try:
            shutil.rmtree(str(session_dir))
        except Exception as e:
            log_lines.append('Warning cleaning temp: ' + str(e))

        return render_template('index.html', log='\\n'.join([l for l in log_lines if l]))
    return render_template('index.html', log=None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)