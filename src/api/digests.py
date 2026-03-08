from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/digests/{digest_id}", response_class=HTMLResponse)
async def view_digest(digest_id: str):
    """View a digest in the browser."""
    # TODO: load digest from db by ID and return html_content
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html><head><title>Digest</title></head>
<body><p>Digest {digest_id} - TODO: load from database</p></body>
</html>""",
        status_code=200,
    )


@router.get("/preferences", response_class=HTMLResponse)
async def preferences_page():
    """Simple preferences management page."""
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html><head><title>Preferences</title>
<style>body{font-family:system-ui;max-width:500px;margin:60px auto;padding:0 20px;}</style>
</head><body>
<h1>Event Preferences</h1>
<p>Preference management coming soon. Edit <code>scripts/seed.py</code> to update your profile.</p>
</body></html>""",
        status_code=200,
    )
