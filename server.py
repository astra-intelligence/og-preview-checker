"""OG Preview Checker - Check any GitHub repo's social preview status."""
import json, os, sys, re
from urllib.parse import urlparse

import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

GITHUB_API_URL = "https://api.github.com"

def parse_github_url(url):
    """Parse a GitHub URL to owner/repo."""
    parsed = urlparse(url)
    if parsed.netloc not in ('github.com', 'www.github.com'):
        return None
    
    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return None

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/check', methods=['GET', 'POST'])
def check():
    if request.method == 'POST':
        data = request.get_json()
        url = data.get('url', '')
    else:
        url = request.args.get('url', '')
    
    if not url:
        return jsonify({"success": False, "message": "No URL provided"})
    
    repo = parse_github_url(url)
    if not repo:
        return jsonify({"success": False, "message": "Invalid GitHub URL"})
    
    try:
        # Use GraphQL to get the social preview fields (not in REST API)
        query = """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            nameWithOwner
            description
            stargazerCount
            usesCustomOpenGraphImage
            openGraphImageUrl
          }
        }
        """
        owner, name = repo.split('/', 1)
        
        # Try to get token from env or gh config
        gql_token = os.environ.get('GITHUB_TOKEN', '')
        if not gql_token:
            try:
                with open(os.path.expanduser('~/.config/gh/hosts.yml')) as f:
                    for line in f:
                        if 'oauth_token' in line:
                            gql_token = line.split(':', 1)[1].strip()
                            break
            except Exception:
                pass
        
        headers = {"User-Agent": "OG-Preview-Checker/1.0"}
        if gql_token:
            headers["Authorization"] = f"Bearer {gql_token}"
        
        gql_resp = requests.post(
            f"{GITHUB_API_URL}/graphql",
            json={"query": query, "variables": {"owner": owner, "repo": name}},
            headers=headers,
            timeout=15
        )
        
        if gql_resp.status_code != 200:
            return jsonify({"success": False, "message": f"GitHub API error: {gql_resp.status_code}"})
        
        gql_data = gql_resp.json()
        
        if 'errors' in gql_data:
            return jsonify({"success": False, "message": f"GitHub GraphQL error: {gql_data['errors']}"})
        
        repo_data = gql_data.get('data', {}).get('repository')
        if not repo_data:
            return jsonify({"success": True, "repo": repo, "exists": False, "message": "Repository not found"})
        
        uses_custom = repo_data.get("usesCustomOpenGraphImage", False)
        og_image_url = repo_data.get("openGraphImageUrl", None)
        
        result = {
            "success": True,
            "repo": repo,
            "name": repo_data.get("nameWithOwner"),
            "description": repo_data.get("description"),
            "stars": repo_data.get("stargazerCount", 0),
            "has_custom_og_image": uses_custom,
            "og_image_url": og_image_url,
            "default_og": not uses_custom,
        }
        
        return jsonify(result)
    except requests.Timeout:
        return jsonify({"success": False, "message": "Request timed out"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/batch', methods=['POST'])
def batch():
    """Check multiple repos at once. Requires license key for paid use."""
    data = request.get_json()
    license_key = data.get('license_key', '')
    repos = data.get('repos', [])
    
    if not repos:
        return jsonify({"success": False, "message": "No repos provided"})
    
    if not license_key:
        return jsonify({"success": False, "message": "License key required for batch checking (max 3 repos free in web UI)"})
    
    if len(repos) > 10:
        return jsonify({"success": False, "message": "Max 10 repos per batch"})
    
    # Verify license
    try:
        # Check against OG Preview Checker Pro first, then fallback to OG Banner
        for permalink in ["og-preview-api-license", "kcdpnv"]:
            lr = requests.post("https://api.gumroad.com/v2/licenses/verify", data={
                "product_permalink": permalink,
                "license_key": license_key,
            }, timeout=15)
            lr_data = lr.json()
            if lr_data.get("success"):
                break
        else:
            return jsonify({"success": False, "message": "Invalid license — buy at https://grantshatz.gumroad.com/l/og-preview-api-license"})
    except Exception as e:
        return jsonify({"success": False, "message": f"License check failed: {e}"})
    
    results = []
    for repo in repos:
        try:
            resp = requests.get(
                f"{GITHUB_API_URL}/repos/{repo}",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "OG-Preview-Checker/1.0"
                },
                timeout=15
            )
            if resp.status_code == 200:
                d = resp.json()
                results.append({
                    "repo": repo,
                    "has_custom_og_image": d.get("uses_custom_open_graph_image", False),
                    "og_image_url": d.get("open_graph_image_url"),
                    "stars": d.get("stargazers_count", 0),
                })
            else:
                results.append({"repo": repo, "error": f"HTTP {resp.status_code}"})
        except Exception as e:
            results.append({"repo": repo, "error": str(e)})
    
    return jsonify({"success": True, "results": results})

@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate a free OG image for a GitHub repo."""
    data = request.get_json()
    url = data.get('url', '')
    repo_full = data.get('repo', '')

    if not repo_full and url:
        parsed = parse_github_url(url)
        if parsed:
            repo_full = parsed

    if not repo_full:
        return jsonify({"success": False, "message": "No repo provided"})

    try:
        owner, name = repo_full.split('/', 1)

        # Fetch repo info
        headers = {"User-Agent": "OG-Preview-Checker/1.0"}
        gql_token = os.environ.get('GITHUB_TOKEN', '')
        if not gql_token:
            try:
                with open(os.path.expanduser('~/.config/gh/hosts.yml')) as f:
                    for line in f:
                        if 'oauth_token' in line:
                            gql_token = line.split(':', 1)[1].strip()
                            break
            except Exception:
                pass
        if gql_token:
            headers["Authorization"] = f"Bearer {gql_token}"

        query = """query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            nameWithOwner, description, stargazerCount, primaryLanguage { name }
          }
        }"""
        gql_resp = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"owner": owner, "repo": name}},
            headers=headers, timeout=15
        )
        repo_data = gql_resp.json().get('data', {}).get('repository', {})
        desc = repo_data.get('description', '') or 'A GitHub project'
        stars = repo_data.get('stargazerCount', 0)
        lang = (repo_data.get('primaryLanguage') or {}).get('name', '')

        # Generate OG image with PIL
        from PIL import Image, ImageDraw, ImageFont
        import math

        img = Image.new('RGB', (1280, 640), (13, 17, 23))
        draw = ImageDraw.Draw(img)

        # Accent gradient bar
        for i in range(4):
            shade = 30 + i * 15
            draw.rectangle([0, 636 + i, 1280, 637 + i], fill=(shade, shade, shade))

        # Try fonts
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        title_font = body_font = small_font = None
        for fp in font_paths:
            if os.path.exists(fp):
                title_font = ImageFont.truetype(fp, 54)
                body_font = ImageFont.truetype(fp, 24)
                small_font = ImageFont.truetype(fp, 16)
                break
        if not title_font:
            title_font = body_font = small_font = ImageFont.load_default()

        # Repo name (truncate if too long)
        display_name = repo_full
        draw.text((64, 180), display_name, fill=(255, 255, 255), font=title_font)

        # Description
        desc_lines = []
        words = desc.split()
        line = ""
        for w in words:
            test = line + " " + w if line else w
            if len(test) > 55:
                desc_lines.append(line)
                line = w
            else:
                line = test
        desc_lines.append(line)
        y = 255
        for dl in desc_lines[:3]:
            draw.text((64, y), dl, fill=(180, 180, 200), font=body_font)
            y += 32

        # Stats
        stats_parts = []
        if stars:
            stats_parts.append(f"⭐ {stars} stars")
        if lang:
            stats_parts.append(f"🔷 {lang}")
        if stats_parts:
            draw.text((64, y + 20), "  |  ".join(stats_parts), fill=(99, 102, 241), font=small_font)

        # Bottom bar with Gumroad link
        draw.text((64, 590), "Get a custom OG image: grantshatz.gumroad.com/l/kcdpnv", fill=(70, 75, 90), font=small_font)

        # Save to temp
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        import base64
        b64 = base64.b64encode(buf.getvalue()).decode()

        return jsonify({
            "success": True,
            "repo": repo_full,
            "image_base64": f"data:image/png;base64,{b64}",
            "message": "Free OG image generated. For a custom-designed version with your brand colors, visit gumroad."
        })
    except ImportError:
        return jsonify({"success": False, "message": "PIL not available for image generation"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Generation error: {str(e)}"})


@app.route('/api/docs')
def api_docs_page():
    return send_from_directory('.', 'api-docs.html')

@app.route('/api')
def api_docs():
    return jsonify({
        "name": "OG Preview Checker API",
        "version": "1.0",
        "description": "Check any GitHub repo's social preview status",
        "endpoints": {
            "check": {
                "method": "GET",
                "path": "/api/check?url=https://github.com/owner/repo",
                "description": "Check a single repo's social preview"
            },
            "batch": {
                "method": "POST",
                "path": "/api/batch",
                "description": "Batch check repos (requires license key)"
            },
            "generate": {
                "method": "POST",
                "path": "/api/generate",
                "description": "Generate a free OG image for any GitHub repo"
            }
        }
    })

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    print(f"OG Preview Checker running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
