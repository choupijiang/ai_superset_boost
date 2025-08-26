#!/usr/bin/env python3
"""
Superset Automation Module - Real Connection Version
"""

import os
import sys
import asyncio
import json
import logging
import tempfile
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

# Import Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not available, install with: pip install playwright")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('superset_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SupersetAutomation:
    """Superset automation class with real connection to Superset"""
    
    def __init__(self):
        """Initialize Superset automation"""
        self.superset_url = os.environ.get('SUPERSET_URL', 'http://localhost:8088')
        self.username = os.environ.get('SUPERSET_USERNAME', 'admin')
        self.password = os.environ.get('SUPERSET_PASSWORD', 'admin')
        
        # Create screenshots directory
        self.screenshots_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Create dashboard data directory
        self.dashboard_data_dir = os.path.join(os.path.dirname(__file__), 'dashboard_data')
        os.makedirs(self.dashboard_data_dir, exist_ok=True)
        
        # Initialize Playwright variables
        self.playwright = None
        self.browser = None
        self.page = None
        self.session_cookies = None
        
        # Configuration
        self.timeout = 20000  # Reduced from 30 to 20 seconds for faster processing
        self.headless = True  # Set to False for debugging
        
        logger.info(f"✅ SupersetAutomation initialized (Real Mode)")
        logger.info(f"   URL: {self.superset_url}")
        logger.info(f"   Screenshots dir: {self.screenshots_dir}")
        logger.info(f"   Playwright available: {PLAYWRIGHT_AVAILABLE}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()
    
    async def initialize_browser(self):
        """Initialize Playwright browser"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not available. Install with: pip install playwright")
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.page = await self.browser.new_page()
            
            # Set default timeout
            self.page.set_default_timeout(self.timeout)
            
            logger.info("✅ Browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize browser: {e}")
            return False
    
    async def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.page = None
            self.browser = None
            self.playwright = None
            
            logger.info("✅ Browser closed successfully")
            
        except Exception as e:
            logger.warning(f"⚠️  Error closing browser: {e}")
    
    async def login_to_superset(self):
        """Login to Superset using Playwright"""
        try:
            logger.info("🔐 Logging in to Superset...")
            
            if not self.page:
                await self.initialize_browser()
            
            # Navigate to login page
            login_url = f"{self.superset_url}/login/"
            await self.page.goto(login_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Take screenshot before login
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_login_screenshot = os.path.join(self.screenshots_dir, f"pre_login_{timestamp}.png")
            await self.page.screenshot(path=pre_login_screenshot)
            logger.info("📸 Pre-login screenshot saved")
            
            # Fill login form - try multiple selectors
            username_selectors = [
                "input[type='text']",
                "input[name='username']", 
                "#username",
                "input[placeholder='Username']",
                "input[placeholder*='用户名']"
            ]
            
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "#password", 
                "input[placeholder='Password']",
                "input[placeholder*='密码']"
            ]
            
            login_button_selectors = [
                "button[type='submit']",
                ".btn-primary",
                "#login",
                "button:has-text('Login')",
                "button:has-text('登录')",
                "input[type='submit']"
            ]
            
            # Fill username
            username_filled = False
            for selector in username_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.fill(selector, self.username)
                        username_filled = True
                        logger.info(f"✅ Username filled using selector: {selector}")
                        break
                except:
                    continue
            
            if not username_filled:
                logger.error("❌ Could not find username input field")
                return False
            
            # Fill password
            password_filled = False
            for selector in password_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.fill(selector, self.password)
                        password_filled = True
                        logger.info(f"✅ Password filled using selector: {selector}")
                        break
                except:
                    continue
            
            if not password_filled:
                logger.error("❌ Could not find password input field")
                return False
            
            # Click login button
            login_clicked = False
            for selector in login_button_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.click(selector)
                        login_clicked = True
                        logger.info(f"✅ Login button clicked using selector: {selector}")
                        break
                except:
                    continue
            
            if not login_clicked:
                logger.error("❌ Could not find login button")
                return False
            
            # Wait for login to complete
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Verify login success
            current_url = self.page.url
            if "/login/" in current_url or "login" in current_url:
                logger.error("❌ Login failed - still on login page")
                
                # Take screenshot for debugging
                failed_screenshot = os.path.join(self.screenshots_dir, f"login_failed_{timestamp}.png")
                await self.page.screenshot(path=failed_screenshot)
                logger.info("📸 Failed login screenshot saved")
                
                return False
            
            # Store session cookies
            cookies = await self.page.context.cookies()
            self.session_cookies = cookies
            
            # Take screenshot after successful login
            success_screenshot = os.path.join(self.screenshots_dir, f"login_success_{timestamp}.png")
            await self.page.screenshot(path=success_screenshot)
            logger.info("📸 Login success screenshot saved")
            
            logger.info("✅ Login successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    async def get_dashboard_list(self):
        """Get real list of available dashboards from Superset API"""
        try:
            logger.info("📋 Getting dashboard list from API...")
            
            # Use Superset API endpoint
            api_url = f"{self.superset_url}/api/v1/dashboard/"
            
            # Prepare headers with authentication if we have session cookies
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Add session cookies if available
            cookies = {}
            if self.session_cookies:
                for cookie in self.session_cookies:
                    cookies[cookie['name']] = cookie['value']
            
            # Make API request
            response = requests.get(api_url, headers=headers, cookies=cookies, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract dashboard information from API response
                dashboards = []
                
                # Handle different possible response formats
                if 'result' in data:
                    # Standard Superset API response format
                    dashboard_items = data['result']
                elif 'dashboards' in data:
                    # Alternative format
                    dashboard_items = data['dashboards']
                else:
                    # Direct list
                    dashboard_items = data if isinstance(data, list) else []
                
                for dashboard in dashboard_items:
                    # Extract dashboard information
                    dashboard_id = dashboard.get('id')
                    dashboard_title = dashboard.get('dashboard_title', dashboard.get('title', 'Unknown Dashboard'))
                    
                    # Construct dashboard URL
                    dashboard_url = f"/superset/dashboard/{dashboard_id}/"
                    
                    dashboards.append({
                        'id': dashboard_id,
                        'title': dashboard_title,
                        'url': dashboard_url,
                        'published': dashboard.get('published', False),
                        'changed_on': dashboard.get('changed_on'),
                        'created_by': dashboard.get('created_by', {}),
                        'owners': dashboard.get('owners', [])
                    })
                
                logger.info(f"✅ Found {len(dashboards)} dashboards via API")
                
                # Log dashboard information in table format
                logger.info("=" * 80)
                logger.info("Dashboard 列表:")
                logger.info("=" * 80)
                logger.info(f"{'ID':<6} {'状态':<10} {'Dashboard 名称':<40} {'URL'}")
                logger.info("-" * 80)
                
                for i, dashboard in enumerate(dashboards):
                    dashboard_id = dashboard.get('id', 'N/A')
                    dashboard_title = dashboard.get('title', 'N/A')
                    dashboard_url = dashboard.get('url', 'N/A')
                    published = dashboard.get('published', False)
                    
                    # Format status with emoji
                    status = "🟢 Public" if published else "🔴 Private"
                    
                    # Construct full URL with superset base
                    full_url = f"{self.superset_url}{dashboard_url}" if dashboard_url.startswith('/') else dashboard_url
                    
                    logger.info(f"{dashboard_id:<6} {status:<10} {dashboard_title:<40} {full_url}")
                
                logger.info("=" * 80)
                
                # Add statistics
                public_count = sum(1 for d in dashboards if d.get('published', False))
                private_count = len(dashboards) - public_count
                logger.info(f"📊 统计信息:")
                logger.info(f"   总计: {len(dashboards)} 个 dashboard")
                logger.info(f"   公开: {public_count} 个")
                logger.info(f"   私有: {private_count} 个")
                logger.info("=" * 80)
                
                return dashboards
                
            elif response.status_code == 401:
                logger.warning("⚠️ Authentication required, trying to login...")
                
                # Try to login and retry
                if await self.login_to_superset():
                    # Retry with fresh session
                    return await self.get_dashboard_list()
                else:
                    logger.error("❌ Login failed, cannot get dashboard list")
                    return []
                    
            elif response.status_code == 403:
                logger.error("❌ Permission denied accessing dashboard API")
                return []
                
            else:
                logger.warning(f"⚠️ API request failed with status {response.status_code}")
                
                # Fallback to web scraping method
                logger.info("🔄 Falling back to web scraping method...")
                return await self._get_dashboard_list_fallback()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API request failed: {e}")
            
            # Fallback to web scraping method
            logger.info("🔄 Falling back to web scraping method...")
            return await self._get_dashboard_list_fallback()
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard list: {e}")
            
            # Fallback to web scraping method
            logger.info("🔄 Falling back to web scraping method...")
            return await self._get_dashboard_list_fallback()
    
    async def _get_dashboard_list_fallback(self):
        """Fallback method using web scraping when API is not available"""
        try:
            logger.info("📋 Getting dashboard list via web scraping (fallback)...")
            
            if not self.page:
                await self.initialize_browser()
            
            # Navigate to dashboard list
            dashboard_list_url = f"{self.superset_url}/dashboard/list/"
            await self.page.goto(dashboard_list_url)
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Extract dashboard information using JavaScript
            dashboards = await self.page.evaluate("""
                () => {
                    const dashboards = [];
                    
                    // Try multiple selectors for dashboard links/cards
                    const selectors = [
                        'a[href*="/dashboard/"]',
                        '.dashboard-card a',
                        '.ant-card a[href*="/dashboard/"]',
                        'tr a[href*="/dashboard/"]',
                        '[data-test="dashboard-link"]',
                        '.dashboard-title a'
                    ];
                    
                    let elements = [];
                    for (const selector of selectors) {
                        elements = document.querySelectorAll(selector);
                        if (elements.length > 0) break;
                    }
                    
                    elements.forEach(el => {
                        const href = el.getAttribute('href');
                        if (href && href.includes('/dashboard/')) {
                            // Skip dashboard list pages
                            if (href.includes('/dashboard/list/')) return;
                            
                            const title = el.querySelector('span.dynamic-title')?.textContent.trim() ||
                                        el.textContent.trim() || 
                                        el.querySelector('.title')?.textContent.trim() ||
                                        el.querySelector('.dashboard-title')?.textContent.trim() ||
                                        el.getAttribute('title') ||
                                        'Unknown Dashboard';
                            
                            // Extract dashboard ID from URL
                            const idMatch = href.match(/\\/dashboard\\/(\\d+)/);
                            const id = idMatch ? parseInt(idMatch[1]) : Date.now();
                            
                            dashboards.push({
                                id: id,
                                title: title,
                                url: href.startsWith('http') ? href : href,
                                element_count: elements.length
                            });
                        }
                    });
                    
                    // Remove duplicates
                    const uniqueDashboards = dashboards.filter((dashboard, index, self) => 
                        index === self.findIndex(d => d.id === dashboard.id)
                    );
                    
                    return uniqueDashboards;
                }
            """)
            
            logger.info(f"✅ Found {len(dashboards)} dashboards via fallback method")
            
            # Log dashboard information in table format
            logger.info("=" * 80)
            logger.info("Dashboard 列表 (Fallback 方法):")
            logger.info("=" * 80)
            logger.info(f"{'ID':<6} {'状态':<10} {'Dashboard 名称':<40} {'URL'}")
            logger.info("-" * 80)
            
            for dashboard in dashboards:
                dashboard_id = dashboard.get('id', 'N/A')
                dashboard_title = dashboard.get('title', 'N/A')
                dashboard_url = dashboard.get('url', 'N/A')
                
                # For fallback method, we don't have published status, so mark as unknown
                status = "❓ Unknown"
                
                # Construct full URL with superset base
                full_url = f"{self.superset_url}{dashboard_url}" if dashboard_url.startswith('/') else dashboard_url
                
                logger.info(f"{dashboard_id:<6} {status:<10} {dashboard_title:<40} {full_url}")
            
            logger.info("=" * 80)
            logger.info(f"📊 统计信息 (Fallback):")
            logger.info(f"   总计: {len(dashboards)} 个 dashboard")
            logger.info("=" * 80)
            
            return dashboards
            
        except Exception as e:
            logger.error(f"❌ Fallback method failed: {e}")
            return []
    
    async def capture_dashboard_screenshot(self, dashboard, max_retries=2):
        """Capture screenshot of a specific dashboard using Superset's Download as Image"""
        try:
            logger.info(f"📸 Capturing dashboard: {dashboard['title']}")
            
            if not self.page:
                await self.initialize_browser()
            
            # Retry mechanism for dashboard loading
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"🔄 Attempt {attempt + 1}/{max_retries + 1}")
                    
                    # Navigate to dashboard
                    dashboard_url = dashboard['url'] if dashboard['url'].startswith('http') else f"{self.superset_url}{dashboard['url']}"
                    await self.page.goto(dashboard_url)
                    
                    # Use enhanced dashboard loading with error checking
                    dashboard_loaded = await self._wait_for_dashboard_load(dashboard['title'])
                    
                    if dashboard_loaded:
                        logger.info(f"✅ Dashboard '{dashboard['title']}' loaded successfully")
                        break
                    else:
                        if attempt < max_retries:
                            logger.warning(f"⚠️ Dashboard load failed, retrying... ({attempt + 1}/{max_retries + 1})")
                            await asyncio.sleep(2)  # Wait before retry
                        else:
                            logger.error(f"❌ Dashboard '{dashboard['title']}' failed to load properly after {max_retries + 1} attempts")
                            
                            # Try to capture error screenshot for debugging
                            error_filename = f"error_dashboard_{self._clean_filename(dashboard['title'])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            error_path = os.path.join(self.screenshots_dir, error_filename)
                            try:
                                await self.page.screenshot(path=error_path, full_page=True)
                                logger.info(f"📸 Error screenshot saved: {error_path}")
                            except Exception as screenshot_error:
                                logger.warning(f"⚠️ Could not capture error screenshot: {screenshot_error}")
                            
                            return None
                
                except Exception as attempt_error:
                    if attempt < max_retries:
                        logger.warning(f"⚠️ Attempt {attempt + 1} failed: {attempt_error}, retrying...")
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"❌ All {max_retries + 1} attempts failed: {attempt_error}")
                        return None
            
            # Generate filename
            clean_title = self._clean_filename(dashboard['title'])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"dashboard_{clean_title}_{timestamp}.png"
            screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
            
            # Try Superset's Download as Image functionality
            logger.info("🔄 Attempting Superset Download as Image...")
            export_success = await self._export_dashboard_as_image(screenshot_filename)
            
            if export_success:
                logger.info(f"✅ Dashboard exported using Superset: {screenshot_path}")
                return screenshot_path
            else:
                # Fallback to original screenshot method
                logger.warning("⚠️  Superset export failed, falling back to screenshot method")
                return await self._capture_dashboard_screenshot_fallback(dashboard, screenshot_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to capture dashboard screenshot: {e}")
            return None
    
    async def _generate_export_filename(self, export_type, dashboard_name=None, chart_name=None, file_extension=None):
        """Generate standardized export filename with timestamp"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_type == 'dashboard' and dashboard_name:
            clean_dashboard_name = self._clean_filename(dashboard_name)
            return f"dashboard_{clean_dashboard_name}_{timestamp}.{file_extension}"
        elif export_type == 'chart' and dashboard_name and chart_name:
            clean_dashboard_name = self._clean_filename(dashboard_name)
            clean_chart_name = self._clean_filename(chart_name)
            return f"dashboard_{clean_dashboard_name}_{clean_chart_name}_{timestamp}.{file_extension}"
        else:
            return f"export_{timestamp}.{file_extension}"
    
    async def _get_current_dashboard_name(self):
        """Extract dashboard name from current page"""
        try:
            # Try multiple selectors to find dashboard name
            name_selectors = [
                'span.dynamic-title',
                'h1.ant-typography',
                '.dashboard-header h1',
                '.ant-page-header-heading-title',
                '[data-test="dashboard-title"]',
                '.ant-breadcrumb li:last-child',
                'title'
            ]
            
            for selector in name_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        text = await element.text_content()
                        if text and text.strip():
                            return text.strip()
                except:
                    continue
            
            # Fallback: get from URL
            current_url = self.page.url
            import re
            dashboard_match = re.search(r'/dashboard/(\d+)', current_url)
            if dashboard_match:
                return f"Dashboard_{dashboard_match.group(1)}"
            
            return "Unknown_Dashboard"
            
        except Exception as e:
            logger.warning(f"⚠️ Could not extract dashboard name: {e}")
            return "Unknown_Dashboard"
    
    async def _get_chart_name_from_element(self, chart_element):
        """Extract chart name from chart element"""
        try:
            # Try to get chart name from various attributes
            name_selectors = [
                '[data-test="chart-title"]',
                '.chart-title',
                '.visualization-title',
                '.ant-card-head-title',
                'h3', 'h4', 'h5',
                '[class*="title"]'
            ]
            
            for selector in name_selectors:
                try:
                    title_element = await chart_element.query_selector(selector)
                    if title_element:
                        text = await title_element.text_content()
                        if text and text.strip():
                            return text.strip()
                except:
                    continue
            
            # Fallback: get from chart ID
            chart_id = await chart_element.get_attribute('id')
            if chart_id:
                return f"Chart_{chart_id}"
            
            return "Unknown_Chart"
            
        except Exception as e:
            logger.warning(f"⚠️ Could not extract chart name: {e}")
            return "Unknown_Chart"
    
    async def _export_dashboard_as_image(self, filename):
        """Export dashboard using Superset's native Download as Image functionality with improved download handling"""
        try:
            logger.info("🔄 Starting dashboard export with improved native functionality...")
            
            # Approach 1: Enhanced native export with proper download event handling
            if await self._try_enhanced_native_export('dashboard', filename):
                return True
            
            # Approach 2: Standard export button (fallback)
            if await self._try_standard_export('dashboard', filename):
                return True
            
            # Approach 3: Keyboard shortcuts
            if await self._try_keyboard_export('dashboard', filename):
                return True
            
            # Approach 4: Right-click context menu
            if await self._try_context_menu_export('dashboard', filename):
                return True
            
            # Approach 5: Direct API call (if available)
            if await self._try_api_export('dashboard', filename):
                return True
            
            logger.warning("⚠️  All export approaches failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in dashboard export: {e}")
            return False
    
    async def _export_dashboard_as_csv(self, filename):
        """Export dashboard using Superset's native CSV functionality with improved download handling"""
        try:
            logger.info("🔄 Starting dashboard CSV export with improved native functionality...")
            
            # Ensure we're on a dashboard page
            await self._wait_for_dashboard_load()
            
            # Set up download listener BEFORE triggering download
            download_path = os.path.join(self.screenshots_dir, filename)
            
            # Start download listener
            download_task = asyncio.create_task(self._wait_for_download_event())
            
            # Try to find and click the dashboard export button
            export_button_selectors = [
                'button[aria-label*="actions"]',
                '[data-test="header-actions-menu"]',
                '.header-actions button',
                '.dashboard-header button[aria-label*="menu"]',
                '.ant-btn[aria-label*="actions"]'
            ]
            
            export_button_clicked = False
            for selector in export_button_selectors:
                try:
                    export_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if export_button:
                        await export_button.click()
                        logger.info(f"✅ Found and clicked dashboard export button: {selector}")
                        export_button_clicked = True
                        break
                except:
                    continue
            
            if not export_button_clicked:
                logger.warning("⚠️ Could not find dashboard export button")
                return False
            
            # Wait for menu to appear and navigate to Download submenu
            await asyncio.sleep(1)
            
            # Click Download option
            try:
                download_option = await self.page.wait_for_selector('text="Download"', timeout=5000)
                await download_option.click()
                logger.info("✅ Found Download option: text=\"Download\"")
            except:
                logger.warning("⚠️ Could not find Download option")
                return False
            
            # Wait for submenu to appear
            await asyncio.sleep(1)
            
            # Check if CSV option is available and click it
            try:
                csv_option = await self.page.wait_for_selector('text="Export to .CSV"', timeout=5000)
                is_visible = await csv_option.is_visible()
                logger.info(f"   CSV option 'text=\"Export to .CSV\"' visible: {is_visible}")
                
                if is_visible:
                    await csv_option.click()
                    logger.info("✅ Selected CSV from submenu: text=\"Export to .CSV\"")
                else:
                    logger.warning("⚠️ CSV option not visible")
                    return False
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not find CSV option: {e}")
                return False
            
            # Wait for download to complete
            try:
                download_result = await asyncio.wait_for(download_task, timeout=30)
                if download_result:
                    logger.info(f"✅ Enhanced dashboard CSV export successful: {download_result}")
                    return True
                else:
                    logger.warning("⚠️ Download event not detected")
                    return False
                    
            except asyncio.TimeoutError:
                logger.warning("⚠️ Download timeout")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error in dashboard CSV export: {e}")
            return False
    
    async def _export_dashboard_as_excel(self, filename):
        """Export dashboard using Superset's native Excel functionality with improved download handling"""
        try:
            logger.info("🔄 Starting dashboard Excel export with improved native functionality...")
            
            # Ensure we're on a dashboard page
            await self._wait_for_dashboard_load()
            
            # Set up download listener BEFORE triggering download
            download_path = os.path.join(self.screenshots_dir, filename)
            
            # Start download listener
            download_task = asyncio.create_task(self._wait_for_download_event())
            
            # Try to find and click the dashboard export button
            export_button_selectors = [
                'button[aria-label*="actions"]',
                '[data-test="header-actions-menu"]',
                '.header-actions button',
                '.dashboard-header button[aria-label*="menu"]',
                '.ant-btn[aria-label*="actions"]'
            ]
            
            export_button_clicked = False
            for selector in export_button_selectors:
                try:
                    export_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if export_button:
                        await export_button.click()
                        logger.info(f"✅ Found and clicked dashboard export button: {selector}")
                        export_button_clicked = True
                        break
                except:
                    continue
            
            if not export_button_clicked:
                logger.warning("⚠️ Could not find dashboard export button")
                return False
            
            # Wait for menu to appear and navigate to Download submenu
            await asyncio.sleep(1)
            
            # Click Download option
            try:
                download_option = await self.page.wait_for_selector('text="Download"', timeout=5000)
                await download_option.click()
                logger.info("✅ Found Download option: text=\"Download\"")
            except:
                logger.warning("⚠️ Could not find Download option")
                return False
            
            # Wait for submenu to appear
            await asyncio.sleep(1)
            
            # Check if Excel option is available and click it
            try:
                excel_option = await self.page.wait_for_selector('text="Export to Excel"', timeout=5000)
                is_visible = await excel_option.is_visible()
                logger.info(f"   Excel option 'text=\"Export to Excel\"' visible: {is_visible}")
                
                if is_visible:
                    await excel_option.click()
                    logger.info("✅ Selected Excel from submenu: text=\"Export to Excel\"")
                else:
                    logger.warning("⚠️ Excel option not visible")
                    return False
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not find Excel option: {e}")
                return False
            
            # Wait for download to complete
            try:
                download_result = await asyncio.wait_for(download_task, timeout=30)
                if download_result:
                    logger.info(f"✅ Enhanced dashboard Excel export successful: {download_result}")
                    return True
                else:
                    logger.warning("⚠️ Download event not detected")
                    return False
                    
            except asyncio.TimeoutError:
                logger.warning("⚠️ Download timeout")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error in dashboard Excel export: {e}")
            return False
    
    async def _try_enhanced_native_export(self, export_type, filename):
        """Try enhanced native export with proper download event handling based on Playwright best practices"""
        try:
            logger.info(f"🔄 Trying enhanced native export for {export_type}...")
            
            # Ensure we're on a dashboard page
            if export_type == 'dashboard':
                await self._wait_for_dashboard_load()
            
            # Set up download listener BEFORE triggering download
            download_path = os.path.join(self.screenshots_dir, filename)
            
            # Method 1: Use page.waitForEvent('download') - Playwright recommended approach
            try:
                logger.info("🎯 Setting up download event listener...")
                
                # Start download listener
                download_task = asyncio.create_task(self._wait_for_download_event())
                
                # Trigger the download
                if await self._trigger_native_download(export_type):
                    try:
                        # Wait for download with timeout
                        download = await asyncio.wait_for(download_task, timeout=90000)  # 90 seconds total
                        
                        # Save the download
                        await download.save_as(download_path)
                        logger.info(f"✅ Enhanced native export successful: {download_path}")
                        return True
                        
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ Download event timeout")
                        # Cancel the task
                        if not download_task.done():
                            download_task.cancel()
                    except Exception as download_error:
                        logger.error(f"❌ Download handling error: {download_error}")
                        # Cancel the task
                        if not download_task.done():
                            download_task.cancel()
                
            except Exception as e:
                logger.error(f"❌ Enhanced export method failed: {e}")
            
            # Method 2: Fallback to existing approach if enhanced method fails
            logger.info("🔄 Falling back to standard export approach...")
            return await self._try_standard_export(export_type, filename)
            
        except Exception as e:
            logger.error(f"❌ Enhanced native export failed: {e}")
            return False

    async def _wait_for_download_event(self):
        """Wait for download event using Playwright's recommended approach with reduced timeout"""
        try:
            logger.info("🎯 Waiting for download event...")
            download = await self.page.wait_for_event('download', timeout=60000)  # Reduced to 60 seconds
            logger.info("✅ Download event detected")
            return download
        except asyncio.TimeoutError:
            logger.warning("⚠️ Download event timeout after 60 seconds")
            raise
        except Exception as e:
            logger.error(f"❌ Wait for download event failed: {e}")
            raise

    async def _trigger_native_download(self, export_type):
        """Trigger native download using Superset's UI"""
        try:
            if export_type == 'dashboard':
                return await self._trigger_dashboard_download()
            elif export_type == 'chart':
                return await self._trigger_chart_download()
            else:
                logger.error(f"❌ Unsupported export type: {export_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to trigger native download: {e}")
            return False

    async def _trigger_dashboard_download(self):
        """Trigger dashboard download using improved selectors and timing"""
        try:
            logger.info("🎯 Triggering dashboard download...")
            
            # Try multiple selectors for dashboard export button
            dashboard_selectors = [
                '[data-test="header-actions-menu"]',  # Playwright recommended
                'button[aria-label*="actions"]',      # Current working selector
                '.dashboard-header .ant-dropdown-trigger',
                '.ant-dropdown-trigger[aria-label*="more"]',
                'button[title*="export"]',
                '.header-actions .ant-dropdown-trigger'
            ]
            
            # Try each selector
            for selector in dashboard_selectors:
                try:
                    logger.info(f"🔍 Trying selector: {selector}")
                    
                    # Wait for element to be visible and clickable
                    element = await self.page.wait_for_selector(selector, state='visible', timeout=5000)
                    if element:
                        # Click the export button
                        await element.click()
                        logger.info(f"✅ Clicked export button: {selector}")
                        
                        # Wait for dropdown menu to appear
                        await asyncio.sleep(1)
                        
                        # Look for Download option
                        download_selectors = [
                            'text="Download"',
                            'text="下载"',
                            '.ant-dropdown-menu-item:has-text("Download")',
                            '.ant-dropdown-menu-item:has-text("下载")'
                        ]
                        
                        for dl_selector in download_selectors:
                            try:
                                download_element = await self.page.wait_for_selector(dl_selector, state='visible', timeout=3000)
                                if download_element:
                                    await download_element.click()
                                    logger.info(f"✅ Clicked Download option: {dl_selector}")
                                    
                                    # Wait for submenu
                                    await asyncio.sleep(1)
                                    
                                    # Look for "Download as Image" option
                                    image_selectors = [
                                        'text="Download as Image"',
                                        'text="Download as image"',
                                        'text="导出为图片"',
                                        '.ant-dropdown-menu-item:has-text("Image")',
                                        '.ant-dropdown-menu-item:has-text("图片")'
                                    ]
                                    
                                    for img_selector in image_selectors:
                                        try:
                                            image_element = await self.page.wait_for_selector(img_selector, state='visible', timeout=3000)
                                            if image_element:
                                                await image_element.click()
                                                logger.info(f"✅ Clicked Download as Image: {img_selector}")
                                                return True
                                        except:
                                            continue
                                        
                            except:
                                continue
                        
                        # If we got here, download menu didn't work, try clicking elsewhere to close
                        await self.page.mouse.click(10, 10)
                        
                except Exception as selector_error:
                    logger.warning(f"⚠️ Selector {selector} failed: {selector_error}")
                    continue
            
            logger.warning("⚠️ All dashboard download triggers failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Dashboard download trigger failed: {e}")
            return False

    async def _trigger_chart_download(self):
        """Trigger chart download using improved selectors and strategy"""
        try:
            logger.info("🎯 Triggering chart download...")
            
            # STRATEGY 1: Try to find chart-specific export buttons first
            chart_specific_selectors = [
                '.explore-chart-header .ant-dropdown-trigger',  # Playwright recommended for explore view
                '.chart-header .ant-dropdown-trigger',
                '.visualization-header .ant-dropdown-trigger',
                '[data-test="chart-header"] .ant-dropdown-trigger',
                '.chart-container .ant-dropdown-trigger',
                '.dashboard-chart .ant-dropdown-trigger'  # Dashboard chart specific
            ]
            
            for selector in chart_specific_selectors:
                try:
                    logger.info(f"🔍 Trying chart selector: {selector}")
                    
                    element = await self.page.wait_for_selector(selector, state='visible', timeout=3000)
                    if element:
                        await element.click()
                        logger.info(f"✅ Clicked chart export button: {selector}")
                        
                        # Wait for dropdown
                        await asyncio.sleep(1)
                        
                        # Look for Download option
                        download_selectors = [
                            'text="Download"',
                            'text="下载"',
                            '.ant-dropdown-menu-item:has-text("Download")',
                            '.ant-dropdown-menu-item:has-text("下载")'
                        ]
                        
                        for dl_selector in download_selectors:
                            try:
                                download_element = await self.page.wait_for_selector(dl_selector, state='visible', timeout=2000)
                                if download_element:
                                    await download_element.click()
                                    logger.info(f"✅ Clicked chart Download option: {dl_selector}")
                                    
                                    # Wait for submenu
                                    await asyncio.sleep(1)
                                    
                                    # Look for "Download as image" option
                                    image_selectors = [
                                        'text="Download as image"',
                                        'text="Download as Image"',
                                        'text="导出为图片"',
                                        '.ant-dropdown-menu-item:has-text("image")',
                                        '.ant-dropdown-menu-item:has-text("图片")'
                                    ]
                                    
                                    for img_selector in image_selectors:
                                        try:
                                            image_element = await self.page.wait_for_selector(img_selector, state='visible', timeout=2000)
                                            if image_element:
                                                await image_element.click()
                                                logger.info(f"✅ Clicked chart Download as Image: {img_selector}")
                                                return True
                                        except:
                                            continue
                                            
                            except:
                                continue
                        
                        # Close menu if opened
                        await self.page.mouse.click(10, 10)
                        
                except Exception as selector_error:
                    logger.debug(f"Chart selector {selector} not found: {selector_error}")
                    continue
            
            # STRATEGY 2: Try right-click context menu on chart
            logger.info("🔄 Trying right-click context menu strategy...")
            
            # Get chart position for right-click
            chart_position = await self._get_chart_position_for_context_menu()
            if chart_position:
                try:
                    # Right-click on chart
                    await self.page.mouse.click(chart_position['x'], chart_position['y'], button='right')
                    await asyncio.sleep(1)
                    
                    # Look for export options in context menu
                    context_selectors = [
                        'text="Export"',
                        'text="导出"', 
                        'text="Download"',
                        'text="下载"',
                        '.context-menu-item:has-text("Export")',
                        '.context-menu-item:has-text("Download")'
                    ]
                    
                    for selector in context_selectors:
                        try:
                            context_element = await self.page.wait_for_selector(selector, state='visible', timeout=2000)
                            if context_element:
                                await context_element.click()
                                await asyncio.sleep(1)
                                
                                # Look for image options
                                image_selectors = [
                                    'text="image"',
                                    'text="图片"',
                                    'text="as image"',
                                    'text="为图片"'
                                ]
                                
                                for img_selector in image_selectors:
                                    try:
                                        img_element = await self.page.wait_for_selector(img_selector, state='visible', timeout=2000)
                                        if img_element:
                                            await img_element.click()
                                            logger.info("✅ Selected image option from context menu")
                                            return True
                                    except:
                                        continue
                                        
                        except:
                            continue
                    
                    # Close context menu
                    await self.page.mouse.click(10, 10)
                    
                except Exception as context_error:
                    logger.warning(f"⚠️ Context menu strategy failed: {context_error}")
            
            # STRATEGY 3: Try keyboard shortcuts for chart export
            logger.info("🔄 Trying keyboard shortcut strategy...")
            
            keyboard_shortcuts = [
                # Try common export shortcuts
                {'key': 'e', 'modifiers': ['Ctrl']},
                {'key': 'e', 'modifiers': ['Meta']},
                {'key': 's', 'modifiers': ['Ctrl', 'Shift']},
                {'key': 's', 'modifiers': ['Meta', 'Shift']},
                {'key': 'd', 'modifiers': ['Ctrl']},
                {'key': 'd', 'modifiers': ['Meta']}
            ]
            
            for shortcut in keyboard_shortcuts:
                try:
                    await self.page.keyboard.press(shortcut['key'], modifiers=shortcut.get('modifiers', []))
                    await asyncio.sleep(2)
                    
                    # Check if any export dialog appeared
                    export_dialog = await self.page.query_selector('.ant-modal, .modal, [role="dialog"]')
                    if export_dialog:
                        logger.info("✅ Export dialog appeared via keyboard shortcut")
                        return True
                        
                except:
                    continue
            
            logger.warning("⚠️ All chart download strategies failed")
            logger.info("📝 Note: Charts in dashboard view may not have individual export capabilities")
            return False
            
        except Exception as e:
            logger.error(f"❌ Chart download trigger failed: {e}")
            return False
    
    async def _try_enhanced_chart_export(self, chart, filename, export_format='image'):
        """Try enhanced chart export with proper download event handling for different formats"""
        try:
            logger.info(f"🔄 Trying enhanced chart export as {export_format}...")
            
            # Start download listener
            download_task = asyncio.create_task(self._wait_for_download_event())
            
            try:
                # Find and click chart export button
                if not await self._find_and_click_export_button('chart'):
                    return False
                
                # Select the appropriate export option based on format
                if export_format == 'image':
                    if not await self._select_download_as_image():
                        return False
                elif export_format == 'csv':
                    if not await self._select_download_as_csv():
                        return False
                elif export_format == 'excel':
                    if not await self._select_download_as_excel():
                        return False
                else:
                    logger.warning(f"⚠️  Unsupported export format: {export_format}")
                    return False
                
                # Wait for download to complete
                download = await asyncio.wait_for(download_task, timeout=60.0)
                
                if download:
                    # Save the download with the desired filename
                    final_path = os.path.join(self.screenshots_dir, filename)
                    await download.save_as(final_path)
                    logger.info(f"✅ Enhanced chart export successful: {final_path}")
                    return True
                else:
                    logger.warning("⚠️  Download event listener returned None")
                    return False
                    
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  Enhanced chart export timeout for {export_format}")
                if not download_task.done():
                    download_task.cancel()
                return False
            except Exception as e:
                logger.error(f"❌ Enhanced chart export error for {export_format}: {e}")
                if not download_task.done():
                    download_task.cancel()
                return False
                
        except Exception as e:
            logger.error(f"❌ Enhanced chart export failed for {export_format}: {e}")
            return False
    
    async def _select_download_as_csv(self):
        """Select 'Export to .CSV' option from chart menu with submenu navigation"""
        try:
            selectors = self._get_superset_export_selectors()
            csv_selectors = selectors.get('download_csv', [])
            download_selectors = selectors.get('download_submenu', [])
            
            # Wait for dropdown menu to appear
            await asyncio.sleep(1)
            
            # Debug: Log all visible menu items
            logger.info("🔍 Debug: Checking available menu options...")
            try:
                menu_items = await self.page.query_selector_all('.ant-dropdown-menu-item, .dropdown-menu-item, .dropdown-item')
                for i, item in enumerate(menu_items):
                    text = await item.text_content()
                    visible = await item.is_visible()
                    logger.info(f"   Menu item {i}: '{text}' (visible: {visible})")
            except Exception as debug_e:
                logger.warning(f"⚠️ Could not debug menu items: {debug_e}")
            
            # STRATEGY 1: Try direct CSV selection (if visible)
            for selector in csv_selectors:
                try:
                    logger.info(f"🔍 Trying CSV selector: {selector}")
                    if await self.page.is_visible(selector, timeout=1000):
                        await self.page.click(selector)
                        logger.info(f"✅ Selected 'Export to CSV' option: {selector}")
                        return True
                    else:
                        logger.info(f"⚠️ CSV selector not visible: {selector}")
                except Exception as e:
                    logger.info(f"⚠️ CSV selector failed: {selector} - {e}")
                    continue
            
            # STRATEGY 2: Navigate through Download submenu
            logger.info("📁 Trying Download submenu navigation...")
            
            # Find and click Download option to reveal submenu
            for dl_selector in download_selectors:
                try:
                    download_element = await self.page.query_selector(dl_selector)
                    if download_element and await download_element.is_visible():
                        logger.info(f"✅ Found Download option: {dl_selector}")
                        
                        # Click Download to open submenu
                        await download_element.click()
                        await asyncio.sleep(1)  # Wait for submenu to appear
                        
                        # Now look for CSV in the revealed submenu
                        for csv_selector in csv_selectors:
                            try:
                                csv_element = await self.page.query_selector(csv_selector)
                                if csv_element:
                                    # Check if it became visible after submenu opens
                                    is_visible = await csv_element.is_visible()
                                    logger.info(f"   CSV option '{csv_selector}' visible: {is_visible}")
                                    
                                    if is_visible:
                                        await csv_element.click()
                                        logger.info(f"✅ Selected CSV from submenu: {csv_selector}")
                                        return True
                                    else:
                                        # Try to scroll into view and click anyway
                                        await csv_element.scroll_into_view_if_needed()
                                        await asyncio.sleep(0.5)
                                        await csv_element.click()
                                        logger.info(f"✅ Selected CSV from submenu (forced): {csv_selector}")
                                        return True
                            except Exception as e:
                                logger.debug(f"   CSV selector {csv_selector} failed: {e}")
                                continue
                        break
                except Exception as e:
                    logger.debug(f"Download selector {dl_selector} failed: {e}")
                    continue
            
            # STRATEGY 3: Try alternative approach - find CSV by text content
            logger.info("🔍 Trying to find CSV by text content...")
            try:
                # Look for any element containing CSV text
                csv_elements = await self.page.query_selector_all('*')
                for element in csv_elements:
                    try:
                        text = await element.text_content()
                        if text and 'CSV' in text and 'Export' in text:
                            # Try to click if it's a menu item
                            parent = await element.evaluate_handle("""(element) => {
                                let parent = element;
                                while (parent && parent.parentElement) {
                                    parent = parent.parentElement;
                                    if (parent.getAttribute && parent.getAttribute('role') === 'menuitem') {
                                        return parent;
                                    }
                                }
                                return null;
                            }""")
                            
                            if parent:
                                await parent.as_element().click()
                                logger.info(f"✅ Selected CSV via text content: {text.strip()}")
                                return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Text content search failed: {e}")
            
            logger.warning("⚠️  CSV export option not found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error selecting CSV option: {e}")
            return False
    
    async def _select_download_as_excel(self):
        """Select 'Export to Excel' option from chart menu with submenu navigation"""
        try:
            selectors = self._get_superset_export_selectors()
            excel_selectors = selectors.get('download_excel', [])
            download_selectors = selectors.get('download_submenu', [])
            
            # Wait for dropdown menu to appear
            await asyncio.sleep(1)
            
            # STRATEGY 1: Try direct Excel selection (if visible)
            for selector in excel_selectors:
                try:
                    if await self.page.is_visible(selector, timeout=1000):
                        await self.page.click(selector)
                        logger.info(f"✅ Selected 'Export to Excel' option: {selector}")
                        return True
                except:
                    continue
            
            # STRATEGY 2: Navigate through Download submenu
            logger.info("📁 Trying Download submenu navigation for Excel...")
            
            # Find and click Download option to reveal submenu
            for dl_selector in download_selectors:
                try:
                    download_element = await self.page.query_selector(dl_selector)
                    if download_element and await download_element.is_visible():
                        logger.info(f"✅ Found Download option: {dl_selector}")
                        
                        # Click Download to open submenu
                        await download_element.click()
                        await asyncio.sleep(1)  # Wait for submenu to appear
                        
                        # Now look for Excel in the revealed submenu
                        for excel_selector in excel_selectors:
                            try:
                                excel_element = await self.page.query_selector(excel_selector)
                                if excel_element:
                                    # Check if it became visible after submenu opens
                                    is_visible = await excel_element.is_visible()
                                    logger.info(f"   Excel option '{excel_selector}' visible: {is_visible}")
                                    
                                    if is_visible:
                                        await excel_element.click()
                                        logger.info(f"✅ Selected Excel from submenu: {excel_selector}")
                                        return True
                                    else:
                                        # Try to scroll into view and click anyway
                                        await excel_element.scroll_into_view_if_needed()
                                        await asyncio.sleep(0.5)
                                        await excel_element.click()
                                        logger.info(f"✅ Selected Excel from submenu (forced): {excel_selector}")
                                        return True
                            except Exception as e:
                                logger.debug(f"   Excel selector {excel_selector} failed: {e}")
                                continue
                        break
                except Exception as e:
                    logger.debug(f"Download selector {dl_selector} failed: {e}")
                    continue
            
            # STRATEGY 3: Try alternative approach - find Excel by text content
            logger.info("🔍 Trying to find Excel by text content...")
            try:
                # Look for any element containing Excel text
                excel_elements = await self.page.query_selector_all('*')
                for element in excel_elements:
                    try:
                        text = await element.text_content()
                        if text and 'Excel' in text and 'Export' in text:
                            # Try to click if it's a menu item
                            parent = await element.evaluate_handle("""(element) => {
                                let parent = element;
                                while (parent && parent.parentElement) {
                                    parent = parent.parentElement;
                                    if (parent.getAttribute && parent.getAttribute('role') === 'menuitem') {
                                        return parent;
                                    }
                                }
                                return null;
                            }""")
                            
                            if parent:
                                await parent.as_element().click()
                                logger.info(f"✅ Selected Excel via text content: {text.strip()}")
                                return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Text content search failed: {e}")
            
            logger.warning("⚠️  Excel export option not found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error selecting Excel option: {e}")
            return False

    async def _get_chart_position_for_context_menu(self):
        """Get chart position for right-click context menu"""
        try:
            # Find the first visible chart container
            chart_selectors = [
                '.dashboard-chart',
                '.chart-container', 
                '.visualization-container',
                '[data-test="chart-container"]'
            ]
            
            for selector in chart_selectors:
                try:
                    chart_element = await self.page.wait_for_selector(selector, state='visible', timeout=3000)
                    if chart_element:
                        # Get chart position
                        box = await chart_element.bounding_box()
                        if box and box['width'] > 50 and box['height'] > 50:
                            # Click in center of chart
                            return {
                                'x': box['x'] + box['width'] / 2,
                                'y': box['y'] + box['height'] / 2
                            }
                except:
                    continue
            
            logger.warning("⚠️ Could not find chart position for context menu")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get chart position: {e}")
            return None

    async def _wait_for_dashboard_load(self):
        """Wait for dashboard to fully load using improved waiting strategy"""
        try:
            logger.info("⏳ Waiting for dashboard to fully load...")
            
            # Wait for main dashboard container
            await self.page.wait_for_selector('.dashboard, .ant-layout-content, [data-test="dashboard"]', 
                                             state='visible', timeout=30000)
            
            # Wait for charts to load - improved version
            await self.page.wait_for_function("""
                () => {
                    // Check if dashboard has meaningful content
                    const containers = document.querySelectorAll('.chart-container, .visualization-container, .ant-card');
                    if (containers.length === 0) return false;
                    
                    // Check if loading spinners are gone
                    const spinners = document.querySelectorAll('.loading-spinner, .ant-spin, [data-test="loading"]');
                    const visibleSpinners = Array.from(spinners).filter(spinner => {
                        const style = window.getComputedStyle(spinner);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    });
                    
                    return visibleSpinners.length === 0;
                }
            """, timeout=60000)
            
            logger.info("✅ Dashboard fully loaded")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Dashboard load wait incomplete: {e}")
            return False

    async def _try_standard_export(self, export_type, filename):
        """Try standard export button approach"""
        try:
            logger.info(f"🔄 Trying standard export for {export_type}...")
            
            # Find and click export button
            if not await self._find_and_click_export_button(export_type):
                return False
            
            # Select Download as Image option
            if not await self._select_download_as_image():
                return False
            
            # Handle the download
            download_path = await self._handle_download_dialog(filename)
            return download_path is not None
            
        except Exception as e:
            logger.error(f"❌ Standard export failed: {e}")
            return False
    
    async def _try_keyboard_export(self, export_type, filename):
        """Try keyboard shortcuts for export"""
        try:
            logger.info(f"🔄 Trying keyboard export for {export_type}...")
            
            # Try common keyboard shortcuts
            keyboard_shortcuts = [
                # Ctrl/Cmd + Shift + S (Save as)
                {'key': 's', 'modifiers': ['Ctrl', 'Shift']},
                {'key': 's', 'modifiers': ['Meta', 'Shift']},
                # Ctrl/Cmd + E (Export)
                {'key': 'e', 'modifiers': ['Ctrl']},
                {'key': 'e', 'modifiers': ['Meta']},
                # Alt + E
                {'key': 'e', 'modifiers': ['Alt']},
            ]
            
            for shortcut in keyboard_shortcuts:
                try:
                    await self.page.keyboard.press(shortcut['key'], modifiers=shortcut.get('modifiers', []))
                    await asyncio.sleep(2)
                    
                    # Check if export dialog appeared
                    if await self._select_download_as_image():
                        download_path = await self._handle_download_dialog(filename)
                        if download_path:
                            return True
                            
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Keyboard export failed: {e}")
            return False
    
    async def _try_context_menu_export(self, export_type, filename):
        """Try right-click context menu for export"""
        try:
            logger.info(f"🔄 Trying context menu export for {export_type}...")
            
            # Get page center for right-click
            viewport_size = await self.page.viewport_size()
            center_x = viewport_size['width'] // 2
            center_y = viewport_size['height'] // 2
            
            # Right-click to open context menu
            await self.page.mouse.click(center_x, center_y, button='right')
            await asyncio.sleep(1)
            
            # Look for export options in context menu
            context_selectors = [
                'text="Export"',
                'text="Download"', 
                'text="Save as"',
                'text="Image"',
                '.context-menu-item:has-text("Export")',
                '.context-menu-item:has-text("Image")'
            ]
            
            for selector in context_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.click(selector)
                        await asyncio.sleep(1)
                        
                        # Try to select image option
                        if await self._select_download_as_image():
                            download_path = await self._handle_download_dialog(filename)
                            if download_path:
                                return True
                except:
                    continue
            
            # Close context menu by clicking elsewhere
            await self.page.mouse.click(10, 10)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Context menu export failed: {e}")
            return False
    
    async def _try_api_export(self, export_type, filename):
        """Try direct API call for export (if available)"""
        try:
            logger.info(f"🔄 Trying API export for {export_type}...")
            
            # Get current dashboard ID from URL
            current_url = self.page.url
            import re
            dashboard_id_match = re.search(r'/dashboard/(\d+)', current_url)
            
            if not dashboard_id_match:
                return False
            
            dashboard_id = dashboard_id_match.group(1)
            
            # Try Superset API endpoints for export
            api_endpoints = [
                f'/api/v1/dashboard/{dashboard_id}/export/png',
                f'/api/v1/dashboard/{dashboard_id}/export/image',
                f'/dashboard/{dashboard_id}/export/png',
                f'/dashboard/{dashboard_id}/export/image'
            ]
            
            for endpoint in api_endpoints:
                try:
                    api_url = f"{self.superset_url}{endpoint}"
                    
                    # Make API call with session cookies
                    response = await self.page.request.get(api_url)
                    
                    if response.status == 200:
                        # Save the response content as image
                        download_path = os.path.join(self.screenshots_dir, filename)
                        with open(download_path, 'wb') as f:
                            f.write(response.body())
                        
                        logger.info(f"✅ API export successful: {download_path}")
                        return True
                        
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"❌ API export failed: {e}")
            return False
    
    async def _capture_dashboard_screenshot_fallback(self, dashboard, screenshot_path):
        """Fallback method using original screenshot approach"""
        try:
            # Take full page screenshot
            await self.page.screenshot(path=screenshot_path, full_page=True)
            
            logger.info(f"✅ Dashboard screenshot saved (fallback): {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"❌ Failed to capture dashboard screenshot (fallback): {e}")
            return None
    
    async def capture_all_dashboards(self):
        """Capture screenshots of all available dashboards"""
        try:
            logger.info("📸 Capturing all dashboards...")
            
            # Login if not already logged in
            if not self.session_cookies:
                if not await self.login_to_superset():
                    logger.error("❌ Login failed, cannot capture dashboards")
                    return []
            
            # Get dashboard list
            dashboards = await self.get_dashboard_list()
            
            if not dashboards:
                logger.error("❌ No dashboards found")
                return []
            
            # Capture screenshots for each dashboard
            screenshots = []
            for dashboard in dashboards:
                screenshot_path = await self.capture_dashboard_screenshot(dashboard)
                if screenshot_path:
                    screenshots.append({
                        'title': dashboard['title'],
                        'path': screenshot_path,
                        'dashboard_id': dashboard['id']
                    })
                
                # Add delay between captures to avoid overwhelming the system
                await asyncio.sleep(2)
            
            logger.info(f"✅ Captured {len(screenshots)} dashboard screenshots")
            return screenshots
            
        except Exception as e:
            logger.error(f"❌ Failed to capture all dashboards: {e}")
            return []
    
    async def capture_all_dashboards_with_details(self):
        """Capture detailed dashboard information with charts"""
        try:
            logger.info("🚀 Starting detailed dashboard capture...")
            
            # Login if not already logged in
            if not self.session_cookies:
                if not await self.login_to_superset():
                    logger.error("❌ Login failed, cannot capture dashboards")
                    return []
            
            # Get dashboard list
            dashboards = await self.get_dashboard_list()
            
            if not dashboards:
                logger.error("❌ No dashboards found")
                return []
            
            # Limit to first 3 dashboards for performance
            dashboards_to_process = dashboards[:3]
            logger.info(f"📊 Processing {len(dashboards_to_process)} dashboards...")
            
            all_dashboards_data = []
            
            for dashboard in dashboards_to_process:
                try:
                    dashboard_data = await self._explore_dashboard_details(dashboard)
                    if dashboard_data:
                        all_dashboards_data.append(dashboard_data)
                    
                    # Add delay between dashboards (reduced from 3 to 2 seconds)
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing dashboard {dashboard['title']}: {e}")
                    continue
            
            logger.info(f"✅ Captured detailed data for {len(all_dashboards_data)} dashboards")
            return all_dashboards_data
            
        except Exception as e:
            logger.error(f"❌ Failed to capture detailed dashboards: {e}")
            return []
    
    async def _explore_dashboard_details(self, dashboard):
        """Explore dashboard and extract detailed information"""
        try:
            logger.info(f"🔍 Exploring dashboard: {dashboard['title']}")
            
            if not self.page:
                await self.initialize_browser()
            
            # Navigate to dashboard
            dashboard_url = dashboard['url'] if dashboard['url'].startswith('http') else f"{self.superset_url}{dashboard['url']}"
            await self.page.goto(dashboard_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for dashboard content to load (reduced from 5 to 3 seconds)
            await asyncio.sleep(3)
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_title = self._clean_filename(dashboard['title'])
            
            # Capture full dashboard screenshot
            dashboard_screenshot = f"dashboard_{clean_title}_full_{timestamp}.png"
            dashboard_screenshot_path = os.path.join(self.screenshots_dir, dashboard_screenshot)
            await self.page.screenshot(path=dashboard_screenshot_path, full_page=True)
            
            # Extract chart information
            charts_data = await self._extract_charts_data(clean_title, timestamp)
            
            return {
                'dashboard_id': dashboard['id'],
                'dashboard_title': dashboard['title'],
                'dashboard_screenshot': dashboard_screenshot,
                'dashboard_url': dashboard_url,
                'charts': charts_data,
                'total_charts': len(charts_data),
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to explore dashboard {dashboard['title']}: {e}")
            return None
    
    async def _extract_charts_data(self, dashboard_title, timestamp):
        """Extract chart information and screenshots from dashboard"""
        try:
            logger.info(f"📊 Extracting charts data...")
            
            # JavaScript to extract chart information with enhanced detection
            charts = await self.page.evaluate("""
                () => {
                    const charts = [];
                    
                    // Try multiple selectors for chart containers
                    const chartSelectors = [
                        '[data-test="chart-container"]',
                        '.chart-container',
                        '.visualization-container',
                        '.ant-card',
                        '.dashboard-chart',
                        '.slice_container',
                        '.chart',
                        '[class*="chart"]',
                        '[class*="visualization"]',
                        '.react-grid-item',
                        '.grid-item',
                        '[data-grid-item]'
                    ];
                    
                    let chartElements = [];
                    for (const selector of chartSelectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            chartElements = Array.from(elements);
                            break;
                        }
                    }
                    
                    // Filter out elements that are too small or hidden
                    chartElements = chartElements.filter(function(element) {
                        const rect = element.getBoundingClientRect();
                        const style = window.getComputedStyle(element);
                        
                        // Skip if element is not visible or too small
                        if (rect.width < 50 || rect.height < 50) return false;
                        if (style.display === 'none') return false;
                        if (style.visibility === 'hidden') return false;
                        if (style.opacity === '0') return false;
                        
                        // Skip if element is outside viewport
                        if (rect.bottom < 0 || rect.top > window.innerHeight) return false;
                        if (rect.right < 0 || rect.left > window.innerWidth) return false;
                        
                        return true;
                    });
                    
                    chartElements.forEach(function(element, index) {
                        const rect = element.getBoundingClientRect();
                        
                        // Try to extract chart title with multiple strategies
                        let title = 'Unknown Chart';
                        
                        // Strategy 1: Look for title elements within the chart
                        const titleSelectors = [
                            '.chart-title',
                            '.title', 
                            '.chart-header',
                            '.visualization-header',
                            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                            '[data-test="chart-title"]',
                            '.ant-card-head-title'
                        ];
                        
                        for (let i = 0; i < titleSelectors.length; i++) {
                            const selector = titleSelectors[i];
                            const titleElement = element.querySelector(selector);
                            if (titleElement && titleElement.textContent.trim()) {
                                title = titleElement.textContent.trim();
                                break;
                            }
                        }
                        
                        // Strategy 2: Use element attributes
                        if (title === 'Unknown Chart') {
                            title = element.getAttribute('title') ||
                                     element.getAttribute('data-chart-title') ||
                                     element.getAttribute('aria-label') ||
                                     'Chart ' + (index + 1);
                        }
                        
                        // Strategy 3: Look for nearby text
                        if (title === 'Unknown Chart') {
                            const parentElement = element.parentElement;
                            if (parentElement) {
                                const nearbyText = parentElement.textContent.trim();
                                if (nearbyText && nearbyText.length < 100) {
                                    title = nearbyText;
                                }
                            }
                        }
                        
                        // Get chart position with scroll offset
                        const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
                        const scrollY = window.pageYOffset || document.documentElement.scrollTop;
                        
                        const position = {
                            x: Math.round(rect.left + scrollX),
                            y: Math.round(rect.top + scrollY),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        };
                        
                        // Additional chart metadata
                        charts.push({
                            chart_id: 'chart_' + (index + 1),
                            chart_title: title.trim(),
                            chart_position: position,
                            element_class: element.className,
                            element_tag: element.tagName,
                            visible: rect.width > 0 && rect.height > 0,
                            in_viewport: (
                                rect.top >= 0 && 
                                rect.left >= 0 && 
                                rect.bottom <= window.innerHeight && 
                                rect.right <= window.innerWidth
                            )
                        });
                    });
                    
                    return charts;
                }
            """)
            
            logger.info(f"📊 Found {len(charts)} charts")
            
            # Capture individual chart screenshots
            charts_data = []
            for chart in charts:
                try:
                    # Skip charts that are not visible or in viewport
                    if not chart.get('visible', True):
                        logger.warning(f"⚠️  Skipping invisible chart: {chart['chart_title']}")
                        continue
                    
                    # Skip charts that are too small
                    chart_position = chart['chart_position']
                    if chart_position['width'] < 50 or chart_position['height'] < 50:
                        logger.warning(f"⚠️  Skipping too small chart: {chart['chart_title']} ({chart_position['width']}x{chart_position['height']})")
                        continue
                    
                    chart_screenshot_path = await self._capture_chart_screenshot(
                        chart, dashboard_title, timestamp
                    )
                    
                    if chart_screenshot_path:
                        chart_data = {
                            'chart_id': chart['chart_id'],
                            'chart_title': chart['chart_title'],
                            'chart_screenshot': chart_screenshot_path,
                            'chart_position': chart['chart_position'],
                            'has_real_data': True,
                            'processing_time': timestamp,
                            'chart_type': 'extracted_from_ui',
                            'visible': chart.get('visible', True),
                            'in_viewport': chart.get('in_viewport', False),
                            'element_class': chart.get('element_class', ''),
                            'element_tag': chart.get('element_tag', '')
                        }
                        
                        charts_data.append(chart_data)
                    else:
                        logger.warning(f"⚠️  Failed to capture screenshot for chart: {chart['chart_title']}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to capture chart {chart['chart_title']}: {e}")
                    continue
            
            return charts_data
            
        except Exception as e:
            logger.error(f"❌ Failed to extract charts data: {e}")
            return []
    
    async def _capture_chart_screenshot(self, chart, dashboard_title, timestamp):
        """Capture screenshot of individual chart using Superset's Download as Image"""
        try:
            # Validate input parameters
            if not chart or not isinstance(chart, dict):
                logger.error("❌ Invalid chart parameter")
                return None
            
            if not dashboard_title or not timestamp:
                logger.error("❌ Missing dashboard_title or timestamp")
                return None
            
            clean_title = self._clean_filename(dashboard_title)
            clean_chart_title = self._clean_filename(chart.get('chart_title', 'unknown'))
            
            chart_screenshot = f"chart_{clean_title}_{clean_chart_title}_{timestamp}.png"
            chart_screenshot_path = os.path.join(self.screenshots_dir, chart_screenshot)
            
            # Ensure screenshots directory exists
            os.makedirs(self.screenshots_dir, exist_ok=True)
            
            # Try Superset's Download as Image functionality for individual charts
            logger.info(f"🔄 Attempting Superset Download as Image for chart: {chart.get('chart_title', 'unknown')}")
            export_success = await self._export_chart_as_image(chart, chart_screenshot)
            
            if export_success:
                logger.info(f"✅ Chart exported using Superset: {chart_screenshot_path}")
                return chart_screenshot_path
            else:
                # Fallback to original screenshot method
                logger.warning("⚠️  Superset chart export failed, falling back to screenshot method")
                return await self._capture_chart_screenshot_fallback(chart, dashboard_title, timestamp)
            
        except Exception as e:
            logger.error(f"❌ Failed to capture chart screenshot: {e}")
            return None
    
    async def _export_chart_as_image(self, chart, filename):
        """Export chart using Superset's native Download as Image functionality with improved handling"""
        return await self._export_chart_as_format(chart, filename, 'image')
    
    async def _export_chart_as_csv(self, chart, filename):
        """Export chart using Superset's native CSV functionality"""
        return await self._export_chart_as_format(chart, filename, 'csv')
    
    async def _export_chart_as_excel(self, chart, filename):
        """Export chart using Superset's native Excel functionality"""
        return await self._export_chart_as_format(chart, filename, 'excel')
    
    async def _export_chart_as_format(self, chart, filename, export_format='image'):
        """Export chart using Superset's native functionality for different formats"""
        try:
            logger.info(f"🔄 Starting chart export as {export_format} with improved native functionality...")
            
            # Approach 1: Enhanced native export with proper download event handling
            if await self._try_enhanced_chart_export(chart, filename, export_format):
                return True
            
            # Approach 2: Standard chart export button
            if await self._try_chart_standard_export_format(chart, filename, export_format):
                return True
            
            # Approach 3: Keyboard shortcuts
            if await self._try_keyboard_export('chart', filename):
                return True
            
            # Approach 4: Right-click context menu on chart
            if await self._try_chart_context_menu_export(chart, filename):
                return True
            
            # Approach 5: Direct API call (if available)
            if await self._try_chart_api_export(chart, filename):
                return True
            
            logger.warning(f"⚠️  All chart {export_format} export approaches failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in chart {export_format} export: {e}")
            return False
    
    async def _try_chart_standard_export_format(self, chart, filename, export_format='image'):
        """Try standard export button approach for charts with different formats"""
        try:
            logger.info(f"🔄 Trying standard chart export as {export_format}...")
            
            # Try to find and click on the chart element first
            chart_position = chart.get('chart_position')
            if chart_position:
                # Click on the chart area to focus it
                x = chart_position.get('x', 0) + chart_position.get('width', 100) // 2
                y = chart_position.get('y', 0) + chart_position.get('height', 100) // 2
                
                try:
                    await self.page.mouse.click(x, y)
                    await asyncio.sleep(1)  # Wait for any menu to appear
                except:
                    pass
            
            # Look for chart export button
            if not await self._find_and_click_export_button('chart'):
                return False
            
            # Select the appropriate export option based on format
            if export_format == 'image':
                if not await self._select_download_as_image():
                    return False
            elif export_format == 'csv':
                if not await self._select_download_as_csv():
                    return False
            elif export_format == 'excel':
                if not await self._select_download_as_excel():
                    return False
            else:
                logger.warning(f"⚠️  Unsupported export format: {export_format}")
                return False
            
            # Handle the download
            download_path = await self._handle_download_dialog(filename)
            return download_path is not None
            
        except Exception as e:
            logger.error(f"❌ Standard chart export failed for {export_format}: {e}")
            return False
    
    async def _try_chart_standard_export(self, chart, filename):
        """Try standard export button approach for charts"""
        try:
            logger.info("🔄 Trying standard chart export...")
            
            # Try to find and click on the chart element first
            chart_position = chart.get('chart_position')
            if chart_position:
                # Click on the chart area to focus it
                x = chart_position.get('x', 0) + chart_position.get('width', 100) // 2
                y = chart_position.get('y', 0) + chart_position.get('height', 100) // 2
                
                try:
                    await self.page.mouse.click(x, y)
                    await asyncio.sleep(1)  # Wait for any menu to appear
                except:
                    pass
            
            # Look for chart export button
            if not await self._find_and_click_export_button('chart'):
                return False
            
            # Select Download as Image option
            if not await self._select_download_as_image():
                return False
            
            # Handle the download
            download_path = await self._handle_download_dialog(filename)
            return download_path is not None
            
        except Exception as e:
            logger.error(f"❌ Standard chart export failed: {e}")
            return False
    
    async def _try_chart_context_menu_export(self, chart, filename):
        """Try right-click context menu for charts"""
        try:
            logger.info("🔄 Trying chart context menu export...")
            
            # Get chart position
            chart_position = chart.get('chart_position')
            if not chart_position:
                return False
            
            # Calculate chart center
            x = chart_position.get('x', 0) + chart_position.get('width', 100) // 2
            y = chart_position.get('y', 0) + chart_position.get('height', 100) // 2
            
            # Right-click on chart to open context menu
            await self.page.mouse.click(x, y, button='right')
            await asyncio.sleep(1)
            
            # Look for export options in context menu
            context_selectors = [
                'text="Export"',
                'text="Download"', 
                'text="Save as"',
                'text="Image"',
                '.context-menu-item:has-text("Export")',
                '.context-menu-item:has-text("Image")'
            ]
            
            for selector in context_selectors:
                try:
                    if await self.page.is_visible(selector):
                        await self.page.click(selector)
                        await asyncio.sleep(1)
                        
                        # Try to select image option
                        if await self._select_download_as_image():
                            download_path = await self._handle_download_dialog(filename)
                            if download_path:
                                return True
                except:
                    continue
            
            # Close context menu by clicking elsewhere
            await self.page.mouse.click(10, 10)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Chart context menu export failed: {e}")
            return False
    
    async def _try_chart_api_export(self, chart, filename):
        """Try direct API call for chart export (if available)"""
        try:
            logger.info("🔄 Trying chart API export...")
            
            # Extract chart ID from chart data if available
            chart_id = chart.get('chart_id') or chart.get('id')
            if not chart_id:
                return False
            
            # Try Superset API endpoints for chart export
            api_endpoints = [
                f'/api/v1/chart/{chart_id}/export/png',
                f'/api/v1/chart/{chart_id}/export/image',
                f'/chart/{chart_id}/export/png',
                f'/chart/{chart_id}/export/image'
            ]
            
            for endpoint in api_endpoints:
                try:
                    api_url = f"{self.superset_url}{endpoint}"
                    
                    # Make API call with session cookies
                    response = await self.page.request.get(api_url)
                    
                    if response.status == 200:
                        # Save the response content as image
                        download_path = os.path.join(self.screenshots_dir, filename)
                        with open(download_path, 'wb') as f:
                            f.write(response.body())
                        
                        logger.info(f"✅ Chart API export successful: {download_path}")
                        return True
                        
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Chart API export failed: {e}")
            return False
    
    async def _capture_chart_screenshot_fallback(self, chart, dashboard_title, timestamp):
        """Fallback method using original screenshot approach"""
        try:
            clean_title = self._clean_filename(dashboard_title)
            clean_chart_title = self._clean_filename(chart.get('chart_title', 'unknown'))
            
            chart_screenshot = f"chart_{clean_title}_{clean_chart_title}_{timestamp}.png"
            chart_screenshot_path = os.path.join(self.screenshots_dir, chart_screenshot)
            
            # Get chart position with validation
            position = chart.get('chart_position')
            if not position or not isinstance(position, dict):
                logger.warning(f"⚠️  Invalid chart position for {chart.get('chart_title', 'unknown')}")
                return None
            
            # Validate position values
            required_keys = ['x', 'y', 'width', 'height']
            if not all(key in position for key in required_keys):
                logger.warning(f"⚠️  Missing position keys for {chart.get('chart_title', 'unknown')}")
                return None
            
            if (position['x'] < 0 or position['y'] < 0 or 
                position['width'] <= 0 or position['height'] <= 0):
                logger.warning(f"⚠️  Invalid chart position values for {chart.get('chart_title', 'unknown')}: {position}")
                return None
            
            # Get viewport size with fallback
            try:
                viewport_size = self.page.viewport_size
                if not viewport_size:
                    viewport_size = {'width': 1920, 'height': 1080}
            except Exception as e:
                logger.warning(f"⚠️  Failed to get viewport size: {e}")
                viewport_size = {'width': 1920, 'height': 1080}
            
            # Adjust position to be within viewport bounds
            x = max(0, min(position['x'], viewport_size['width'] - 100))
            y = max(0, min(position['y'], viewport_size['height'] - 100))
            width = min(position['width'], viewport_size['width'] - x)
            height = min(position['height'], viewport_size['height'] - y)
            
            # Ensure minimum size
            if width < 50 or height < 50:
                logger.warning(f"⚠️  Chart too small for screenshot: {width}x{height}")
                return None
            
            # Take screenshot of chart area with validation
            try:
                clip_params = {
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height
                }
                logger.info(f"📸 Capturing chart with clip params: {clip_params}")
                
                await self.page.screenshot(
                    path=chart_screenshot_path,
                    clip=clip_params
                )
                
                # Verify file was created
                if os.path.exists(chart_screenshot_path):
                    file_size = os.path.getsize(chart_screenshot_path)
                    logger.info(f"📸 Chart screenshot saved: {chart_screenshot_path} ({file_size} bytes)")
                    return chart_screenshot_path
                else:
                    logger.warning(f"⚠️  Screenshot file was not created: {chart_screenshot_path}")
                    return None
                
            except Exception as screenshot_error:
                logger.warning(f"⚠️  Failed to capture chart screenshot with clipping: {screenshot_error}")
                
                # Fallback: scroll to chart and take screenshot
                try:
                    logger.info(f"🔄 Attempting fallback screenshot for {chart.get('chart_title', 'unknown')}")
                    
                    # Scroll to chart position
                    await self.page.evaluate(f"window.scrollTo({x}, {y})")
                    await asyncio.sleep(1)
                    
                    # Take screenshot without clipping (full viewport)
                    fallback_screenshot = f"chart_{clean_title}_{clean_chart_title}_{timestamp}_fallback.png"
                    fallback_path = os.path.join(self.screenshots_dir, fallback_screenshot)
                    
                    await self.page.screenshot(path=fallback_path)
                    
                    # Verify fallback file was created
                    if os.path.exists(fallback_path):
                        file_size = os.path.getsize(fallback_path)
                        logger.info(f"📸 Fallback chart screenshot saved: {fallback_path} ({file_size} bytes)")
                        return fallback_path
                    else:
                        logger.warning(f"⚠️  Fallback screenshot file was not created: {fallback_path}")
                        return None
                    
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback screenshot also failed: {fallback_error}")
                    return None
            
        except Exception as e:
            logger.error(f"❌ Failed to capture chart screenshot (fallback): {e}")
            return None
    
    def _clean_filename(self, filename):
        """Clean filename for safe file system usage"""
        import re
        # Remove special characters and replace spaces
        cleaned = re.sub(r'[^\w\s-]', '', filename)
        cleaned = re.sub(r'[-\s]+', '_', cleaned)
        cleaned = cleaned.strip('_')
        return cleaned.lower() if cleaned else 'unknown'
    
    async def _check_dashboard_page_status(self, dashboard_title):
        """Check if dashboard page loaded correctly or shows error"""
        try:
            # Get page content
            page_content = await self.page.content()
            page_text = await self.page.text_content('body')
            
            # Check for error messages in page content - more specific detection
            page_content_lower = page_content.lower()
            page_text_lower = page_text.lower() if page_text else ""
            
            # More specific error patterns that indicate actual errors
            error_patterns = [
                '404 not found',
                '500 internal server error',
                'application error',
                'page not found',
                'unable to load',
                'loading failed',
                'something went wrong',
                'error loading dashboard',
                'dashboard not found',
                'access denied',
                'permission denied'
            ]
            
            for pattern in error_patterns:
                if pattern in page_content_lower or pattern in page_text_lower:
                    logger.error(f"❌ Error detected on dashboard page: {pattern}")
                    return False
            
            # Check for standalone "error" text that's not part of normal content
            # This avoids false positives from words like "terror" or "error" in code
            import re
            error_regex = r'\berror\b(?!\w)(?!\w*code|debug|terror)'
            if re.search(error_regex, page_text_lower):
                # Additional check to ensure it's not in a script or style tag
                if not self._is_error_in_code_block(page_content, 'error'):
                    logger.error("❌ Error detected on dashboard page: error")
                    return False
            
            # Check for specific Superset error patterns
            error_selectors = [
                '.ant-alert-error',
                '.ant-alert-message',
                '.error-message',
                '.error-page',
                '[data-test="error"]',
                '.ant-result-error',
                '.ant-result-title'
            ]
            
            for selector in error_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        element_text = await element.text_content()
                        if any(error in element_text.lower() for error in ['error', 'failed', 'not found', '404', '500']):
                            logger.error(f"❌ Error element found: {element_text}")
                            return False
                except:
                    continue
            
            # Check for dashboard-specific positive indicators
            dashboard_selectors = [
                '[data-test="chart-container"]',
                '.chart-container',
                '.visualization-container',
                '.ant-card',
                '.dashboard-grid',
                '.dashboard-header',
                '.dashboard-title',
                '[data-test="dashboard-header"]'
            ]
            
            # At least one dashboard selector should be present
            dashboard_found = False
            for selector in dashboard_selectors:
                try:
                    if await self.page.query_selector(selector):
                        dashboard_found = True
                        break
                except:
                    continue
            
            if not dashboard_found:
                logger.warning("⚠️ No dashboard elements found on page")
                return False
            
            # Check page title
            page_title = await self.page.title()
            if dashboard_title.lower() not in page_title.lower():
                logger.warning(f"⚠️ Page title '{page_title}' doesn't match dashboard '{dashboard_title}'")
            
            logger.info("✅ Dashboard page appears to be loaded correctly")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking dashboard page status: {e}")
            return False
    
    def _is_error_in_code_block(self, page_content, error_text):
        """Check if error text appears within script or style tags to avoid false positives"""
        import re
        
        # Find all script and style tags and their content
        script_pattern = r'<script[^>]*>.*?</script>'
        style_pattern = r'<style[^>]*>.*?</style>'
        
        # Check if error appears within script or style tags
        for pattern in [script_pattern, style_pattern]:
            matches = re.findall(pattern, page_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if error_text.lower() in match.lower():
                    return True
        
        return False
    
    async def _wait_for_dashboard_load(self, dashboard_title, max_wait_time=30):
        """Wait for dashboard to load with proper error checking"""
        try:
            logger.info(f"⏳ Waiting for dashboard '{dashboard_title}' to load...")
            
            # Wait for initial page load
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # Additional wait for dynamic content
            
            # Check page status
            status_ok = await self._check_dashboard_page_status(dashboard_title)
            
            if not status_ok:
                logger.error("❌ Dashboard page shows error or failed to load properly")
                return False
            
            # Wait for dashboard content specifically
            try:
                await self.page.wait_for_selector(
                    '[data-test="chart-container"], .chart-container, .visualization-container, .ant-card, .dashboard-grid', 
                    timeout=max_wait_time * 1000
                )
                logger.info("✅ Dashboard content loaded successfully")
                return True
            except:
                logger.warning("⚠️ Dashboard content elements not found within timeout")
                # Double-check if it's really an error
                status_ok = await self._check_dashboard_page_status(dashboard_title)
                return status_ok
            
        except Exception as e:
            logger.error(f"❌ Error waiting for dashboard load: {e}")
            return False
    
    def _get_superset_export_selectors(self):
        """Get enhanced selectors for Superset export buttons based on actual UI structure"""
        return {
            # Dashboard export selectors - Updated for Superset's actual UI
            'dashboard_export': [
                # Main dashboard actions
                '.dashboard-header .ant-dropdown-trigger',
                '.dashboard-header .ant-btn',
                '.ant-dropdown-trigger button[aria-label*="more"]',
                'button[aria-label*="more"]',
                '.header-actions .ant-dropdown-trigger',
                # Three dots menu (common in Superset)
                '.ant-dropdown-trigger[aria-label*="more"]',
                'button[aria-label*="Actions"]',
                'button[aria-label*="actions"]',
                # Direct export buttons
                'button[title*="export"]',
                'button[title*="Export"]',
                '.export-button',
                '.dashboard-export',
                # Alternative selectors
                '.ant-btn-icon:has(.anticon-ellipsis)',
                '.ant-btn:has(.anticon-more)',
                'button:has(.anticon-ellipsis)',
                'button:has(.anticon-more)'
            ],
            # Chart export selectors - Updated for actual dashboard chart structure
            'chart_export': [
                # Specific slice control buttons (found in analysis)
                '[id^="slice_"][id$="-controls"]',
                '[id^="slice_"][id$="-controls"].ant-dropdown-trigger',
                '[id^="slice_"][id$="-controls"].css-11peazl',
                # More Options buttons with aria-label
                '.ant-dropdown-trigger[aria-label*="More Options"]',
                '.ant-dropdown-trigger[aria-label*="more options"]',
                # Chart header actions (fallback)
                '.chart-header .ant-dropdown-trigger',
                '.chart-header .ant-btn',
                '.visualization-header .ant-dropdown-trigger',
                '.visualization-header .ant-btn',
                # Three dots menu for charts
                '.chart-container .ant-dropdown-trigger',
                '.visualization-container .ant-dropdown-trigger',
                '[data-test="chart-header"] .ant-dropdown-trigger',
                # Direct chart export
                '[data-test="chart-export"]',
                '.chart-export-button',
                '.visualization-export',
                # Hover actions
                '.chart-container:hover .ant-btn',
                '.visualization-container:hover .ant-btn',
                # Alternative selectors
                '.ant-card-head-extra .ant-dropdown-trigger',
                '.ant-card-extra .ant-dropdown-trigger'
            ],
            # Download as image selectors - Updated for actual menu items
            'download_image': [
                # Direct text matches (found in analysis)
                'text="Download as image"',
                'text="Download as Image"',
                'text="Export as Image"',
                'text="Download Image"',
                'text="Export Image"',
                # Menu item selectors
                '.ant-dropdown-menu-item:has-text("Image")',
                '.ant-dropdown-menu-item:has-text("image")',
                '.dropdown-menu-item:has-text("Image")',
                '.dropdown-item:has-text("Image")',
                # PNG specific
                '.ant-dropdown-menu-item:has-text("PNG")',
                'text="PNG"',
                # Image format options
                '.ant-dropdown-menu-item:has-text("png")',
                'text="png"'
            ],
            # CSV export selectors
            'download_csv': [
                # Direct text matches (found in analysis)
                'text="Export to .CSV"',
                'text="Export to CSV"',
                'text="Export CSV"',
                'text="CSV"',
                # Menu item selectors
                '.ant-dropdown-menu-item:has-text("CSV")',
                '.ant-dropdown-menu-item:has-text("csv")',
                '.dropdown-menu-item:has-text("CSV")',
                '.dropdown-item:has-text("CSV")'
            ],
            # Excel export selectors
            'download_excel': [
                # Direct text matches (found in analysis)
                'text="Export to Excel"',
                'text="Export Excel"',
                'text="Excel"',
                # Menu item selectors
                '.ant-dropdown-menu-item:has-text("Excel")',
                '.ant-dropdown-menu-item:has-text("excel")',
                '.dropdown-menu-item:has-text("Excel")',
                '.dropdown-item:has-text("Excel")'
            ],
            # Download submenu selector
            'download_submenu': [
                # Direct text matches (found in analysis)
                'text="Download"',
                'text="download"',
                # Menu item selectors
                '.ant-dropdown-menu-item:has-text("Download")',
                '.dropdown-menu-item:has-text("Download")'
            ],
            # Additional selectors for different Superset versions
            'share_menu': [
                'text="Share"',
                'text="share"',
                '.ant-dropdown-menu-item:has-text("Share")',
                '.dropdown-menu-item:has-text("Share")'
            ]
        }
    
    async def _find_and_click_export_button(self, export_type='dashboard'):
        """Find and click export button for dashboard or chart with enhanced detection"""
        try:
            selectors = self._get_superset_export_selectors()
            export_selectors = selectors.get(f'{export_type}_export', [])
            
            # First try: Look for visible buttons
            for selector in export_selectors:
                try:
                    if await self.page.is_visible(selector, timeout=2000):
                        await self.page.click(selector)
                        logger.info(f"✅ Found and clicked {export_type} export button: {selector}")
                        return True
                except:
                    continue
            
            # Second try: Look for hidden or off-screen buttons
            for selector in export_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        # Scroll into view if needed
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await element.click()
                        logger.info(f"✅ Found and clicked {export_type} export button (after scroll): {selector}")
                        return True
                except:
                    continue
            
            # Third try: Look for buttons that might need hover
            for selector in export_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        # Try hovering first to reveal hidden menus
                        await element.hover()
                        await asyncio.sleep(1)
                        await element.click()
                        logger.info(f"✅ Found and clicked {export_type} export button (after hover): {selector}")
                        return True
                except:
                    continue
            
            logger.warning(f"⚠️  No {export_type} export button found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error finding {export_type} export button: {e}")
            return False
    
    async def _select_download_as_image(self):
        """Select 'Download as Image' option from export menu with submenu navigation"""
        try:
            selectors = self._get_superset_export_selectors()
            image_selectors = selectors.get('download_image', [])
            download_selectors = selectors.get('download_submenu', [])
            
            # Wait for dropdown menu to appear
            await asyncio.sleep(1)
            
            # STRATEGY 1: Try direct image selection (if visible)
            for selector in image_selectors:
                try:
                    if await self.page.is_visible(selector, timeout=1000):
                        await self.page.click(selector)
                        logger.info(f"✅ Selected 'Download as Image' option: {selector}")
                        return True
                except:
                    continue
            
            # STRATEGY 2: Navigate through Download submenu
            logger.info("📁 Trying Download submenu navigation for Image...")
            
            # Find and click Download option to reveal submenu
            for dl_selector in download_selectors:
                try:
                    download_element = await self.page.query_selector(dl_selector)
                    if download_element and await download_element.is_visible():
                        logger.info(f"✅ Found Download option: {dl_selector}")
                        
                        # Click Download to open submenu
                        await download_element.click()
                        await asyncio.sleep(1)  # Wait for submenu to appear
                        
                        # Now look for Image in the revealed submenu
                        for image_selector in image_selectors:
                            try:
                                image_element = await self.page.query_selector(image_selector)
                                if image_element:
                                    # Check if it became visible after submenu opens
                                    is_visible = await image_element.is_visible()
                                    logger.info(f"   Image option '{image_selector}' visible: {is_visible}")
                                    
                                    if is_visible:
                                        await image_element.click()
                                        logger.info(f"✅ Selected Image from submenu: {image_selector}")
                                        return True
                                    else:
                                        # Try to scroll into view and click anyway
                                        await image_element.scroll_into_view_if_needed()
                                        await asyncio.sleep(0.5)
                                        await image_element.click()
                                        logger.info(f"✅ Selected Image from submenu (forced): {image_selector}")
                                        return True
                            except Exception as e:
                                logger.debug(f"   Image selector {image_selector} failed: {e}")
                                continue
                        break
                except Exception as e:
                    logger.debug(f"Download selector {dl_selector} failed: {e}")
                    continue
            
            # STRATEGY 3: Try alternative approach - find Image by text content
            logger.info("🔍 Trying to find Image by text content...")
            try:
                # Look for any element containing Image text
                image_elements = await self.page.query_selector_all('*')
                for element in image_elements:
                    try:
                        text = await element.text_content()
                        if text and any(keyword in text.lower() for keyword in ['image', 'png', 'download']):
                            # Try to click if it's a menu item
                            parent = await element.evaluate_handle("""(element) => {
                                let parent = element;
                                while (parent && parent.parentElement) {
                                    parent = parent.parentElement;
                                    if (parent.getAttribute && parent.getAttribute('role') === 'menuitem') {
                                        return parent;
                                    }
                                }
                                return null;
                            }""")
                            
                            if parent:
                                await parent.as_element().click()
                                logger.info(f"✅ Selected Image via text content: {text.strip()}")
                                return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Text content search failed: {e}")
            
            # STRATEGY 4: Fallback to old methods
            try:
                menu_items = await self.page.query_selector_all('.ant-dropdown-menu-item, .dropdown-menu-item, [role="menuitem"]')
                for item in menu_items:
                    text = await item.text_content()
                    if text and any(keyword in text.lower() for keyword in ['image', 'png', 'download', 'export']):
                        await item.click()
                        logger.info(f"✅ Selected image option via text content: {text.strip()}")
                        return True
            except:
                pass
            
            logger.warning("⚠️  'Download as Image' option not found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error selecting 'Download as Image': {e}")
            return False
    
    async def _handle_download_dialog(self, filename):
        """Handle download dialog and save file with improved download handling"""
        try:
            # Set up download path
            download_path = os.path.join(self.screenshots_dir, filename)
            
            # Method 1: Use expect_download with better timeout handling
            try:
                logger.info("🎯 Waiting for download event...")
                async with self.page.expect_download(timeout=150000) as download_info:  # Extended to 2.5 minutes
                    download = await download_info.value
                    await download.save_as(download_path)
                    logger.info(f"✅ File downloaded successfully: {download_path} ({download.suggested_filename})")
                    return download_path
            except asyncio.TimeoutError:
                logger.warning("⚠️ Download timeout, trying alternative methods...")
            except Exception as e:
                logger.warning(f"⚠️ Download event handling failed: {e}")
            
            # Method 2: Check existing downloads
            try:
                downloads = await self.page.context.downloads()
                if downloads:
                    download = downloads[-1]  # Get the most recent download
                    await download.save_as(download_path)
                    logger.info(f"✅ File downloaded via existing downloads: {download_path}")
                    return download_path
            except Exception as e:
                logger.warning(f"⚠️ Existing downloads check failed: {e}")
            
            # Method 3: Check for recently created files
            try:
                import time
                current_time = time.time()
                
                if os.path.exists(download_path):
                    file_mtime = os.path.getmtime(download_path)
                    if current_time - file_mtime < 120:  # File created in last 2 minutes
                        file_size = os.path.getsize(download_path)
                        logger.info(f"✅ File already existed: {download_path} ({file_size} bytes)")
                        return download_path
            except Exception as e:
                logger.warning(f"⚠️ File existence check failed: {e}")
            
            # Method 4: Try to find any recently created image files
            try:
                import time
                import glob
                
                current_time = time.time()
                # Look for recently created PNG/JPG files
                pattern = os.path.join(self.screenshots_dir, "*.png")
                recent_files = []
                
                for file_path in glob.glob(pattern):
                    try:
                        file_mtime = os.path.getmtime(file_path)
                        if current_time - file_mtime < 120:  # Created in last 2 minutes
                            recent_files.append((file_path, file_mtime))
                    except:
                        continue
                
                if recent_files:
                    # Sort by modification time (newest first)
                    recent_files.sort(key=lambda x: x[1], reverse=True)
                    latest_file = recent_files[0][0]
                    
                    # Rename it to our expected filename
                    if latest_file != download_path:
                        import shutil
                        shutil.move(latest_file, download_path)
                    
                    file_size = os.path.getsize(download_path)
                    logger.info(f"✅ Found and renamed recent download: {download_path} ({file_size} bytes)")
                    return download_path
                    
            except Exception as e:
                logger.warning(f"⚠️ Recent file search failed: {e}")
            
            logger.warning("⚠️ All download handling methods failed")
            return None
                
        except Exception as e:
            logger.error(f"❌ Error handling download: {e}")
            return None
    
    async def _wait_for_download_complete(self, timeout=30000):
        """Wait for download to complete"""
        try:
            # Wait for download to start
            await asyncio.sleep(2)
            
            # Check if any download is in progress
            downloads = await self.page.context.download()
            if downloads:
                download = downloads[-1]  # Get the most recent download
                await download.save_as(download.suggested_filename)
                return download.suggested_filename
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error waiting for download: {e}")
            return None
    
    def _get_mock_screenshots(self):
        """Fallback to mock screenshots if real capture fails"""
        return [
            {'title': 'World Banks Data', 'path': 'mock_world_banks_data.png'},
            {'title': 'Sales Dashboard', 'path': 'mock_sales_dashboard.png'},
            {'title': 'Financial Dashboard', 'path': 'mock_financial_dashboard.png'}
        ]
    
    def _get_mock_dashboard_data(self):
        """Fallback to mock dashboard data if real capture fails"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return [
            {
                'dashboard_id': 1,
                'dashboard_title': 'World Bank\'s Data',
                'dashboard_screenshot': 'mock_world_banks_data_full.png',
                'charts': [
                    {
                        'chart_id': 'world_bank_chart_1',
                        'chart_title': 'Global Health Metrics',
                        'chart_screenshot': 'mock_world_bank_chart_1.png',
                        'chart_data': self._create_mock_chart_data('World Bank\'s Data'),
                        'chart_position': {'x': 50, 'y': 100, 'width': 600, 'height': 400},
                        'processing_time': timestamp
                    }
                ],
                'total_charts': 1,
                'timestamp': timestamp
            }
        ]
    
    def _create_mock_chart_data(self, dashboard_title):
        """Create mock chart data based on dashboard title"""
        title_lower = dashboard_title.lower()
        
        if 'world bank' in title_lower or 'health' in title_lower:
            return {
                'data': {
                    'type': 'world_bank_data',
                    'countries': ['USA', 'China', 'India', 'Brazil', 'UK'],
                    'metrics': ['GDP Growth', 'Life Expectancy', 'Population'],
                    'period': '2010-2023',
                    'total_records': 150
                },
                'title': 'World Bank Health Data',
                'type': 'mock_world_bank_data'
            }
        elif 'sales' in title_lower:
            return {
                'data': {
                    'growth_rate': 15.3,
                    'monthly_data': [
                        {'month': 'Jan', 'sales': 98000},
                        {'month': 'Feb', 'sales': 102000},
                        {'month': 'Mar', 'sales': 115000},
                        {'month': 'Apr', 'sales': 108000},
                        {'month': 'May', 'sales': 125000},
                        {'month': 'Jun', 'sales': 132000}
                    ],
                    'period': '2024-01 to 2024-06',
                    'total_sales': 680000
                },
                'title': 'Sales Performance Data',
                'type': 'mock_sales_data'
            }
        elif 'financial' in title_lower:
            return {
                'data': {
                    'revenue': 2500000,
                    'expenses': 1800000,
                    'profit': 700000,
                    'profit_margin': 28.0,
                    'quarterly_data': [
                        {'quarter': 'Q1', 'revenue': 600000, 'profit': 150000},
                        {'quarter': 'Q2', 'revenue': 650000, 'profit': 180000},
                        {'quarter': 'Q3', 'revenue': 620000, 'profit': 170000},
                        {'quarter': 'Q4', 'revenue': 630000, 'profit': 200000}
                    ]
                },
                'title': 'Financial Performance Data',
                'type': 'mock_financial_data'
            }
        else:
            return {
                'data': {
                    'value': 1000,
                    'trend': 'increasing',
                    'period': '2024',
                    'records': 50
                },
                'title': 'General Data',
                'type': 'mock_general_data'
            }

# Example usage and testing
async def test_superset_connection():
    """Test the Superset connection"""
    async with SupersetAutomation() as automation:
        try:
            # Test login
            if await automation.login_to_superset():
                print("✅ Login successful")
                
                # Test dashboard list
                dashboards = await automation.get_dashboard_list()
                print(f"✅ Found {len(dashboards)} dashboards")
                
                # Test screenshot capture
                if dashboards:
                    screenshot_path = await automation.capture_dashboard_screenshot(dashboards[0])
                    if screenshot_path:
                        print(f"✅ Screenshot captured: {screenshot_path}")
                
            else:
                print("❌ Login failed")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_superset_connection())