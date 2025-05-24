import base64, uuid, tempfile
import asyncio
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
import time

async def screenshot(url: str) -> tuple[str, str]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page    = await browser.new_page(viewport={"width":1366,"height":768})
        await page.goto(url, wait_until="domcontentloaded")
        # nuke typical cookie banners
        time.sleep(1)
        await page.add_style_tag(content='[class*="cookie"],[id*="cookie"]{display:none!important}')
        img = await page.screenshot(type="png")
        await browser.close()
    b64     = base64.b64encode(img).decode()
    file_id = f"{uuid.uuid4()}.png"
    path    = tempfile.gettempdir() + "/" + file_id
    with open(path, "wb") as f: f.write(img)
    return b64, path

async def crawl_website(url: str, max_pages: int = 8) -> dict[str, str]:
    """
    Crawl a website to depth 1 and extract text content from pages.
    Prioritizes important pages like about, blog, team, etc.
    
    Args:
        url: The main URL to start crawling from
        max_pages: Maximum number of pages to crawl (including main page)
    
    Returns:
        Dictionary mapping URLs to their text content
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-web-security"]
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        # Extract domain from URL for filtering
        try:
            base_domain = urlparse(url).netloc.lower()
        except:
            await browser.close()
            return {url: "Error: Invalid URL"}
        
        # Priority keywords for important pages (ordered by importance)
        priority_keywords = [
            'about', 'team', 'company', 'who-we-are', 'our-story',
            'services', 'products', 'solutions', 'what-we-do',
            'contact', 'careers', 'mission', 'vision', 'values'
        ]
        
        # Blacklist keywords for pages to avoid (SEO content, generic pages)
        blacklist_keywords = [
            'blog', 'news', 'insights', 'articles', 'post', 'posts',
            'press-release', 'media', 'resources', 'download', 'downloads',
            'privacy', 'terms', 'legal', 'cookie', 'gdpr',
            'sitemap', 'search', 'tag', 'category', 'archive',
            'feed', 'rss', 'api', 'login', 'register', 'signup',
            'pricing', 'plans', 'billing', 'support', 'help', 'faq'
        ]
        
        page_contents = {}
        
        # Process main page first
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=8000)
            await page.add_style_tag(content='''
                [class*="cookie"],[id*="cookie"],
                [class*="banner"],[id*="banner"],
                .cookie-banner, .cookie-notice,
                header, nav, footer, .sidebar
                {display:none!important}
            ''')
            
            # Extract text content and links simultaneously
            page_data = await page.evaluate('''() => {
                // Remove unwanted elements
                const unwanted = document.querySelectorAll('script, style, noscript, header, nav, footer, .sidebar');
                unwanted.forEach(el => el.remove());
                
                // Get clean text content
                const textContent = document.body ? document.body.innerText.trim() : '';
                
                // Extract all internal links
                const links = Array.from(document.querySelectorAll('a[href]'))
                    .map(link => {
                        try {
                            const href = link.href;
                            if (href && href.startsWith('http')) {
                                return href;
                            }
                        } catch (e) {}
                        return null;
                    })
                    .filter(href => href !== null);
                
                return { content: textContent, links: links };
            }''')
            
            if page_data['content']:
                page_contents[url] = page_data['content'][:5000]  # Limit content length
            
            links = page_data['links'] or []
            
        except Exception as e:
            print(f"Error processing main page {url}: {e}")
            links = []
            page_contents[url] = f"Error accessing main page: {str(e)}"
        finally:
            await page.close()
        
        # Filter links to same domain and prioritize
        same_domain_links = []
        for link in links:
            try:
                link_domain = urlparse(link).netloc.lower()
                if link_domain == base_domain and link != url:
                    # Check if link contains blacklisted keywords
                    link_lower = link.lower()
                    is_blacklisted = any(keyword in link_lower for keyword in blacklist_keywords)
                    if not is_blacklisted:
                        same_domain_links.append(link)
            except:
                continue
        
        # Remove duplicates and prioritize by keywords
        unique_links = list(dict.fromkeys(same_domain_links))  # Preserve order, remove dupes
        
        def get_link_priority(link):
            link_lower = link.lower()
            for i, keyword in enumerate(priority_keywords):
                if keyword in link_lower:
                    return i
            return len(priority_keywords)
        
        # Sort by priority and limit
        unique_links.sort(key=get_link_priority)
        links_to_crawl = unique_links[:max_pages-1]  # -1 for main page already processed
        
        # Process links in parallel with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        
        async def extract_page_content(link):
            async with semaphore:
                page = await context.new_page()
                try:
                    await page.goto(link, wait_until="domcontentloaded", timeout=6000)
                    await page.add_style_tag(content='''
                        [class*="cookie"],[id*="cookie"],
                        [class*="banner"],[id*="banner"],
                        .cookie-banner, .cookie-notice,
                        header, nav, footer, .sidebar
                        {display:none!important}
                    ''')
                    
                    content = await page.evaluate('''() => {
                        const unwanted = document.querySelectorAll('script, style, noscript, header, nav, footer, .sidebar');
                        unwanted.forEach(el => el.remove());
                        return document.body ? document.body.innerText.trim() : '';
                    }''')
                    
                    return link, content[:5000] if content else ""  # Limit content length
                    
                except Exception as e:
                    print(f"Error processing {link}: {e}")
                    return link, ""
                finally:
                    await page.close()
        
        # Execute all page extractions in parallel
        if links_to_crawl:
            tasks = [extract_page_content(link) for link in links_to_crawl]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful results
            for result in results:
                if isinstance(result, tuple) and len(result) == 2:
                    link, content = result
                    if content and len(content.strip()) > 100:  # Only include substantial content
                        page_contents[link] = content
        
        await browser.close()
        return page_contents
