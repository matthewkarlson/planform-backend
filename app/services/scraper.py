import base64, uuid, tempfile
from playwright.async_api import async_playwright

async def screenshot(url: str) -> tuple[str, str]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page    = await browser.new_page(viewport={"width":1366,"height":768})
        await page.goto(url, wait_until="networkidle")
        # nuke typical cookie banners
        await page.add_style_tag(content='[class*="cookie"],[id*="cookie"]{display:none!important}')
        img = await page.screenshot(type="png")
        await browser.close()
    b64     = base64.b64encode(img).decode()
    file_id = f"{uuid.uuid4()}.png"
    path    = tempfile.gettempdir() + "/" + file_id
    with open(path, "wb") as f: f.write(img)
    return b64, path
