#!/usr/bin/env python3
"""
Page inspection tool to check current structure of 360.cn
"""

import asyncio
import sys
sys.path.insert(0, '.')

from playwright.async_api import async_playwright


async def inspect_page():
    """Inspect the current page structure"""
    
    print("🔍 360.cn Page Structure Inspector")
    print("=" * 50)
    
    async with async_playwright() as playwright:
        # Launch browser
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--no-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        try:
            print("📄 Navigating to https://wan.360.cn/...")
            await page.goto('https://wan.360.cn/', wait_until='domcontentloaded', timeout=60000)
            print(f"✅ Successfully loaded: {page.url}")
            
            # Wait for page to fully load
            await asyncio.sleep(3)
            
            # Get page title
            title = await page.title()
            print(f"📋 Page Title: {title}")
            
            # Look for registration-related elements
            print("\n🔍 Searching for registration elements...")
            
            # Try common registration selectors
            selectors_to_try = [
                # Original XPath
                'xpath=/html/body/div/div/div[2]/div/div/div/div[2]/form/div[6]/div[2]/a[1]',
                
                # CSS selectors
                'a[href*="register"]',
                'a[href*="reg"]',
                '.register',
                '.reg-btn',
                'input[value*="注册"]',
                'button[text*="注册"]',
                
                # Text-based selectors
                'text="注册"',
                'text="立即注册"',
                'text="免费注册"',
                'text="Register"',
                
                # Form elements
                'form a',
                'form input[type="button"]',
                'form input[type="submit"]'
            ]
            
            found_elements = []
            for selector in selectors_to_try:
                try:
                    elements = await page.locator(selector).all()
                    if elements:
                        for i, element in enumerate(elements):
                            text_content = await element.text_content()
                            is_visible = await element.is_visible()
                            print(f"  ✅ Found: {selector}[{i}] - Text: '{text_content}' - Visible: {is_visible}")
                            found_elements.append({
                                'selector': selector,
                                'index': i,
                                'text': text_content,
                                'visible': is_visible
                            })
                except Exception as e:
                    print(f"  ❌ Failed: {selector} - {str(e)}")
            
            if not found_elements:
                print("❌ No registration elements found!")
                
                # Take a screenshot for debugging
                screenshot_path = "360cn_page_debug.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Screenshot saved to: {screenshot_path}")
                
                # Get page HTML for analysis
                html_content = await page.content()
                html_file = "360cn_page_debug.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"📄 Page HTML saved to: {html_file}")
            else:
                print(f"\n✅ Found {len(found_elements)} potential registration elements")
                
                # Take screenshot showing found elements
                screenshot_path = "360cn_elements_found.png"
                await page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot saved to: {screenshot_path}")
            
            # Keep browser open for manual inspection
            print("\n⏰ Keeping browser open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"❌ Error inspecting page: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_page())