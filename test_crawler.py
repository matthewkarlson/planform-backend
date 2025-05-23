import asyncio
import sys
import os

# Add the app directory to the path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.scraper import crawl_website

async def test_crawler():
    """Test the website crawler with a sample URL"""
    
    # Test URL - you can change this to any website you want to test
    test_url = "https://nobullagency.co.uk"
    
    print(f"🕷️ Starting to crawl: {test_url}")
    print("=" * 60)
    
    try:
        # Call the crawler
        results = await crawl_website(test_url, max_pages=6)
        
        print(f"✅ Crawling completed! Found content from {len(results)} pages")
        print("=" * 60)
        
        # Print results for each page
        for i, (url, content) in enumerate(results.items(), 1):
            print(f"\n📄 Page {i}: {url}")
            print("-" * 40)
            
            if content.startswith("Error"):
                print(f"❌ {content}")
            else:
                # Print first 300 characters of content
                preview = content[:300].replace('\n', ' ').strip()
                if len(content) > 300:
                    preview += "..."
                print(f"📝 Content preview: {preview}")
                print(f"📊 Total content length: {len(content)} characters")
        
        print("\n" + "=" * 60)
        print("🎉 Test completed successfully!")
        
        # Show total content for AI context
        total_content = sum(len(content) for content in results.values() if not content.startswith("Error"))
        print(f"📈 Total content collected: {total_content} characters")
        
    except Exception as e:
        print(f"❌ Error during crawling: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_crawler()) 