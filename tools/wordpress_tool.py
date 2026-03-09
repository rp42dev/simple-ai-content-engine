import os
import requests
import markdown
import base64
from dotenv import load_dotenv

load_dotenv()

def post_to_wordpress(title, content_md, status='draft'):
    """
    Posts content to WordPress using the REST API.
    Converts Markdown to HTML before posting.
    """
    wp_url = os.getenv("WP_SITE_URL")
    wp_user = os.getenv("WP_USERNAME")
    wp_pass = os.getenv("WP_APP_PASSWORD")

    if not all([wp_url, wp_user, wp_pass]):
        return {"success": False, "error": "WordPress credentials not configured in .env"}

    # Clean URL
    wp_url = wp_url.rstrip("/")
    api_url = f"{wp_url}/wp-json/wp/v2/posts"

    # Convert Markdown to HTML
    html_content = markdown.markdown(content_md)

    # Setup Auth Header
    auth_str = f"{wp_user}:{wp_pass}"
    token = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }

    payload = {
        'title': title,
        'content': html_content,
        'status': status  # 'publish' or 'draft'
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code in [201, 200]:
            post_data = response.json()
            return {
                "success": True, 
                "link": post_data.get("link"),
                "post_id": post_data.get("id")
            }
        else:
            return {
                "success": False, 
                "error": f"WP Error {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
