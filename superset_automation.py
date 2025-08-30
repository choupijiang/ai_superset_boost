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
import glob
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
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
        
        # Track download tasks for cleanup
        self._download_tasks = []
        
        # Configuration
        self.timeout = int(os.environ.get('SUPERSET_TIMEOUT', '120000'))  # Default 120 seconds, configurable via env
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
            logger.info("🧹 Starting browser cleanup...")
            
            # Cancel any pending download tasks
            if hasattr(self, '_download_tasks'):
                task_count = len(self._download_tasks)
                logger.info(f"📋 Cancelling {task_count} pending download tasks...")
                
                for task in self._download_tasks:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                self._download_tasks.clear()
                logger.info("✅ Download tasks cleared")
            
            if self.page:
                logger.info("📄 Closing browser page...")
                await self.page.close()
                logger.info("✅ Browser page closed")
            
            if self.browser:
                logger.info("🌐 Closing browser...")
                await self.browser.close()
                logger.info("✅ Browser closed")
            if self.playwright:
                logger.info("🎭 Stopping playwright...")
                await self.playwright.stop()
                logger.info("✅ Playwright stopped")
            
            self.page = None
            self.browser = None
            self.playwright = None
            
            logger.info("✅ Browser closed successfully")
            
        except Exception as e:
            logger.warning(f"⚠️  Error closing browser: {e}")
    
    def _log_screenshot_operation(self, operation: str, file_path: str, success: bool = True, error: str = None):
        """Log screenshot file operations with detailed information"""
        try:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            status = "✅" if success else "❌"
            
            if success:
                logger.info(f"{status} {operation}: {file_path} (Size: {file_size} bytes)")
            else:
                logger.error(f"{status} {operation}: {file_path} - {error}")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to log screenshot operation: {e}")
    
    def cleanup_screenshots(self, dashboard_ids: List[str] = None):
        """Clean up screenshot files, optionally for specific dashboards only"""
        try:
            logger.info("🧹 Starting screenshots cleanup...")
            
            if not os.path.exists(self.screenshots_dir):
                logger.info("ℹ️ Screenshots directory does not exist")
                return 0
            
            removed_count = 0
            for file_path in glob.glob(os.path.join(self.screenshots_dir, "*.png")):
                file_name = os.path.basename(file_path)
                
                # If dashboard_ids provided, only remove files for those dashboards
                if dashboard_ids:
                    should_remove = any(dashboard_id in file_name for dashboard_id in dashboard_ids)
                    if not should_remove:
                        continue
                
                try:
                    os.remove(file_path)
                    self._log_screenshot_operation("Screenshot deleted", file_path)
                    removed_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to delete screenshot {file_path}: {e}")
            
            logger.info(f"✅ Screenshots cleanup completed: {removed_count} files removed")
            return removed_count
            
        except Exception as e:
            logger.error(f"❌ Error during screenshots cleanup: {e}")
            return 0
    
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
    
    async def capture_dashboard_screenshot(self, dashboard, max_retries=1, context_callback=None):
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
                    
                    # Use relaxed dashboard loading
                    dashboard_loaded = await self._wait_for_dashboard_load(dashboard['title'])
                    
                    if dashboard_loaded:
                        logger.info(f"✅ Dashboard '{dashboard['title']}' loaded successfully")
                        break
                    else:
                        if attempt < max_retries:
                            logger.warning(f"⚠️ Dashboard load failed, retrying... ({attempt + 1}/{max_retries + 1})")
                            await asyncio.sleep(1)  # Reduced wait before retry
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
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"❌ All {max_retries + 1} attempts failed: {attempt_error}")
                        return None
            
            # Generate filename
            clean_title = self._clean_filename(dashboard['title'])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"dashboard_{clean_title}_{timestamp}.png"
            screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
            
            # Try Superset's Download as Image functionality first (priority)
            logger.info("🔄 Attempting Superset Download as Image...")
            export_success = await self._export_dashboard_as_image(screenshot_filename, dashboard['title'], dashboard, context_callback)
            
            if export_success:
                logger.info(f"✅ Dashboard exported using Superset native download: {screenshot_path}")
                return screenshot_path
            else:
                # Fallback to screenshot method
                logger.warning("⚠️ Superset export failed, falling back to screenshot method")
                return await self._capture_dashboard_screenshot_fallback(dashboard, screenshot_path, context_callback)
            
        except Exception as e:
            logger.error(f"❌ Failed to capture dashboard screenshot: {e}")
            return None
    
    async def _generate_export_filename(self, export_type, dashboard_name=None, file_extension=None):
        """Generate standardized export filename with timestamp"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_type == 'dashboard' and dashboard_name:
            clean_dashboard_name = self._clean_filename(dashboard_name)
            return f"dashboard_{clean_dashboard_name}_{timestamp}.{file_extension}"
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
    
    
    async def _export_dashboard_as_image(self, filename, dashboard_title=None, dashboard=None, context_callback=None):
        """Export dashboard using Superset's native Download as Image functionality"""
        try:
            logger.info("🔄 Starting dashboard export with native functionality...")
            
            # Wait a bit for page to stabilize
            await asyncio.sleep(2)
            
            # Approach 1: Try direct export button detection and click
            if await self._try_direct_export_button(filename, dashboard, context_callback):
                return True
            
            # Approach 2: Try menu-based export
            if await self._try_menu_export(filename, dashboard, context_callback):
                return True
            
            logger.warning("⚠️ All export approaches failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in dashboard export: {e}")
            return False
    
    async def _try_direct_export_button(self, filename, dashboard=None, context_callback=None):
        """Try to find and click direct export button"""
        try:
            logger.info("🔄 Trying direct export button...")
            
            # Look for any direct export/download buttons
            export_selectors = [
                'button[title*="export"]',
                'button[title*="Export"]',
                'button[aria-label*="export"]',
                'button[aria-label*="Export"]',
                '.export-button',
                '.dashboard-export',
                'button:has-text("Export")',
                'button:has-text("Download")',
                'button:has-text("export")',
                'button:has-text("download")'
            ]
            
            for selector in export_selectors:
                try:
                    if await self.page.is_visible(selector, timeout=2000):
                        # Set up download listener
                        download_task = asyncio.create_task(self._wait_for_download_event())
                        
                        # Click the button
                        await self.page.click(selector)
                        logger.info(f"✅ Found and clicked export button: {selector}")
                        
                        # Wait for download
                        try:
                            download = await asyncio.wait_for(download_task, timeout=self.timeout)
                            download_path = os.path.join(self.screenshots_dir, filename)
                            await download.save_as(download_path)
                            logger.info(f"✅ Direct export successful: {download_path}")
                            
                            # Trigger context analysis callback if provided
                            if context_callback:
                                try:
                                    await context_callback({
                                        'dashboard_id': dashboard.get('id'),
                                        'dashboard_title': dashboard.get('title'),
                                        'screenshot_path': download_path,
                                        'success': True
                                    })
                                except Exception as callback_error:
                                    logger.warning(f"⚠️ Context callback failed: {callback_error}")
                            
                            return True
                        except asyncio.TimeoutError:
                            logger.warning("⚠️ Direct export timeout")
                            if not download_task.done():
                                download_task.cancel()
                        except Exception as download_error:
                            logger.error(f"❌ Direct export download error: {download_error}")
                            if not download_task.done():
                                download_task.cancel()
                        
                        # Clean up
                        if download_task in self._download_tasks:
                            self._download_tasks.remove(download_task)
                        
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Direct export button failed: {e}")
            return False

    async def _wait_for_download_event(self):
        """Wait for download event using Playwright's recommended approach with configurable timeout"""
        try:
            logger.info("🎯 Waiting for download event...")
            download = await self.page.wait_for_event('download', timeout=self.timeout)
            logger.info("✅ Download event detected")
            return download
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Download event timeout after {self.timeout/1000} seconds")
            raise
        except Exception as e:
            logger.error(f"❌ Wait for download event failed: {e}")
            raise

    async def _trigger_native_download(self, export_type):
        """Trigger native download using Superset's UI"""
        try:
            if export_type == 'dashboard':
                return await self._trigger_dashboard_download()
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

        
    
    
    async def _try_menu_export(self, filename, dashboard=None, context_callback=None):
        """Try menu-based export approach"""
        try:
            logger.info("🔄 Trying menu export...")
            
            # Find and click actions/menu button
            menu_selectors = [
                '.dashboard-header .ant-dropdown-trigger',
                '.ant-dropdown-trigger button[aria-label*="more"]',
                'button[aria-label*="more"]',
                '.header-actions .ant-dropdown-trigger',
                'button[aria-label*="Actions"]',
                'button[aria-label*="actions"]',
                '.ant-btn-icon:has(.anticon-ellipsis)',
                '.ant-btn:has(.anticon-more)',
                'button:has(.anticon-ellipsis)',
                'button:has(.anticon-more)'
            ]
            
            for selector in menu_selectors:
                try:
                    if await self.page.is_visible(selector, timeout=2000):
                        await self.page.click(selector)
                        logger.info(f"✅ Found and clicked menu button: {selector}")
                        
                        # Wait for menu to appear
                        await asyncio.sleep(1)
                        
                        # Look for download/export options
                        download_selectors = [
                            'text="Download"',
                            'text="Export"',
                            'text="download"',
                            'text="export"',
                            '.ant-dropdown-menu-item:has-text("Download")',
                            '.ant-dropdown-menu-item:has-text("Export")',
                            '.dropdown-menu-item:has-text("Download")',
                            '.dropdown-menu-item:has-text("Export")'
                        ]
                        
                        for dl_selector in download_selectors:
                            try:
                                if await self.page.is_visible(dl_selector, timeout=1000):
                                    await self.page.click(dl_selector)
                                    logger.info(f"✅ Found and clicked download option: {dl_selector}")
                                    
                                    # Wait for submenu
                                    await asyncio.sleep(1)
                                    
                                    # Look for image option
                                    image_selectors = [
                                        'text="Download as Image"',
                                        'text="Download as image"',
                                        'text="Image"',
                                        'text="image"',
                                        'text="PNG"',
                                        'text="png"',
                                        '.ant-dropdown-menu-item:has-text("Image")',
                                        '.ant-dropdown-menu-item:has-text("PNG")'
                                    ]
                                    
                                    for img_selector in image_selectors:
                                        try:
                                            if await self.page.is_visible(img_selector, timeout=1000):
                                                # Set up download listener
                                                download_task = asyncio.create_task(self._wait_for_download_event())
                                                
                                                await self.page.click(img_selector)
                                                logger.info(f"✅ Found and clicked image option: {img_selector}")
                                                
                                                # Wait for download
                                                try:
                                                    download = await asyncio.wait_for(download_task, timeout=self.timeout)
                                                    download_path = os.path.join(self.screenshots_dir, filename)
                                                    await download.save_as(download_path)
                                                    logger.info(f"✅ Menu export successful: {download_path}")
                                                    
                                                    # Trigger context analysis callback if provided
                                                    if context_callback:
                                                        try:
                                                            await context_callback({
                                                                'dashboard_id': dashboard.get('id'),
                                                                'dashboard_title': dashboard.get('title'),
                                                                'screenshot_path': download_path,
                                                                'success': True
                                                            })
                                                        except Exception as callback_error:
                                                            logger.warning(f"⚠️ Context callback failed: {callback_error}")
                                                    
                                                    return True
                                                except asyncio.TimeoutError:
                                                    logger.warning("⚠️ Menu export timeout")
                                                    if not download_task.done():
                                                        download_task.cancel()
                                                except Exception as download_error:
                                                    logger.error(f"❌ Menu export download error: {download_error}")
                                                    if not download_task.done():
                                                        download_task.cancel()
                                                
                                                # Clean up
                                                if download_task in self._download_tasks:
                                                    self._download_tasks.remove(download_task)
                                                
                                        except:
                                            continue
                                    
                            except:
                                continue
                        
                        # Close menu if no success
                        await self.page.mouse.click(10, 10)
                        
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Menu export failed: {e}")
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
    
    async def _capture_dashboard_screenshot_fallback(self, dashboard, screenshot_path, context_callback=None):
        """Fallback method using original screenshot approach"""
        try:
            # Take full page screenshot
            await self.page.screenshot(path=screenshot_path, full_page=True)
            
            logger.info(f"✅ Dashboard screenshot saved (fallback): {screenshot_path}")
            
            # Trigger context analysis callback if provided
            if context_callback:
                try:
                    await context_callback({
                        'dashboard_id': dashboard.get('id'),
                        'dashboard_title': dashboard.get('title'),
                        'screenshot_path': screenshot_path,
                        'success': True
                    })
                except Exception as callback_error:
                    logger.warning(f"⚠️ Context callback failed: {callback_error}")
            
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
        """Capture dashboard information without charts"""
        try:
            logger.info("🚀 Starting dashboard capture...")
            
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
            
            # Process all dashboards
            logger.info(f"📊 Processing {len(dashboards)} dashboards...")
            
            all_dashboards_data = []
            
            for dashboard in dashboards:
                try:
                    dashboard_data = await self._capture_dashboard_only(dashboard)
                    if dashboard_data:
                        all_dashboards_data.append(dashboard_data)
                    
                    # Add delay between dashboards
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing dashboard {dashboard['title']}: {e}")
                    continue
            
            logger.info(f"✅ Captured data for {len(all_dashboards_data)} dashboards")
            return all_dashboards_data
            
        except Exception as e:
            logger.error(f"❌ Failed to capture dashboards: {e}")
            return []
    
    async def capture_dashboards_progressively(self, callback=None):
        """
        Capture dashboards progressively with callback function
        This allows for immediate AI analysis after each dashboard capture
        
        Args:
            callback: Optional callback function to call after each dashboard capture
                     Function signature: callback(dashboard_data, dashboard_index, total_dashboards)
        """
        try:
            logger.info("🚀 Starting progressive dashboard capture...")
            
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
            
            # Process dashboards one by one with callback
            logger.info(f"📊 Processing {len(dashboards)} dashboards progressively...")
            
            all_dashboards_data = []
            
            for index, dashboard in enumerate(dashboards):
                try:
                    logger.info(f"📸 Capturing dashboard {index + 1}/{len(dashboards)}: {dashboard['title']}")
                    
                    dashboard_data = await self._capture_dashboard_only(dashboard)
                    if dashboard_data:
                        all_dashboards_data.append(dashboard_data)
                        
                        # Call callback function if provided
                        if callback:
                            try:
                                await callback(dashboard_data, index, len(dashboards))
                            except Exception as callback_error:
                                logger.error(f"❌ Callback error for dashboard {dashboard['title']}: {callback_error}")
                                # Continue with next dashboard even if callback fails
                    
                    # Add delay between dashboards
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing dashboard {dashboard['title']}: {e}")
                    continue
            
            logger.info(f"✅ Progressively captured data for {len(all_dashboards_data)} dashboards")
            return all_dashboards_data
            
        except Exception as e:
            logger.error(f"❌ Failed to capture dashboards progressively: {e}")
            return []

  
  
    
    
    
    async def _capture_dashboard_only(self, dashboard):
        """Capture dashboard screenshot and basic information"""
        try:
            logger.info(f"📸 Capturing dashboard: {dashboard['title']}")
            
            if not self.page:
                await self.initialize_browser()
            
            # Navigate to dashboard
            dashboard_url = dashboard['url'] if dashboard['url'].startswith('http') else f"{self.superset_url}{dashboard['url']}"
            await self.page.goto(dashboard_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for dashboard content to load
            await asyncio.sleep(3)
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_title = self._clean_filename(dashboard['title'])
            
            # Capture full dashboard screenshot
            dashboard_screenshot = f"dashboard_{clean_title}_{timestamp}.png"
            dashboard_screenshot_path = os.path.join(self.screenshots_dir, dashboard_screenshot)
            await self.page.screenshot(path=dashboard_screenshot_path, full_page=True)
            
            return {
                'dashboard_id': dashboard['id'],
                'dashboard_title': dashboard['title'],
                'dashboard_screenshot': dashboard_screenshot,
                'dashboard_url': dashboard_url,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to capture dashboard {dashboard['title']}: {e}")
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
    
    async def _wait_for_dashboard_load(self, dashboard_title, max_wait_time=10):
        """Wait for dashboard to load with minimal error checking"""
        try:
            logger.info(f"⏳ Waiting for dashboard '{dashboard_title}' to load...")
            
            # Wait for initial page load
            await self.page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(1)  # Minimal wait for dynamic content
            
            # Only check for critical errors - be more lenient
            status_ok = await self._check_dashboard_page_status(dashboard_title)
            
            if not status_ok:
                logger.error("❌ Dashboard page shows error or failed to load properly")
                return False
            
            # Just check if page has basic content - no specific selectors
            try:
                # Get page title to verify we're on a dashboard
                page_title = await self.page.title()
                if dashboard_title.lower() in page_title.lower() or 'dashboard' in page_title.lower():
                    logger.info("✅ Dashboard page loaded successfully")
                    return True
                else:
                    logger.warning(f"⚠️ Page title '{page_title}' doesn't match expected dashboard")
                    # Still consider it loaded if no critical errors
                    return status_ok
            except:
                logger.warning("⚠️ Could not verify page title, but assuming loaded")
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
            # Download as image selectors - Updated for actual menu items
            'download_image': [
                # Direct text matches (found in analysis)
                'text="Download as image"',
                'text="Download as Image"', 
                'text="Download Image"', 
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
        """Find and click export button for dashboard with enhanced detection"""
        try:
            # Only support dashboard export
            if export_type != 'dashboard':
                logger.error(f"❌ Unsupported export type: {export_type}")
                return False
                
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
    
    async def _handle_download_dialog(self, filename, dashboard=None, context_callback=None):
        """Handle download dialog and save file with improved download handling"""
        try:
            # Set up download path
            download_path = os.path.join(self.screenshots_dir, filename)
            logger.info(f"📁 Preparing download path: {download_path}")
            
            # Ensure screenshots directory exists
            os.makedirs(self.screenshots_dir, exist_ok=True)
            logger.info(f"📂 Screenshots directory confirmed: {self.screenshots_dir}")
            
            # Check if file already exists
            if os.path.exists(download_path):
                logger.info(f"🔄 File already exists, will overwrite: {download_path}")
            
            # Method 1: Use expect_download with better timeout handling
            try:
                logger.info("🎯 Waiting for download event...")
                async with self.page.expect_download(timeout=150000) as download_info:  # Extended to 2.5 minutes
                    download = await download_info.value
                    logger.info(f"📥 Download started: {download.suggested_filename}")
                    await download.save_as(download_path)
                    logger.info(f"✅ File downloaded successfully: {download_path}")
                    logger.info(f"📊 File size: {os.path.getsize(download_path)} bytes")
                    
                    # Trigger context analysis callback if provided
                    if context_callback and dashboard:
                        try:
                            await context_callback({
                                'dashboard_id': dashboard.get('id'),
                                'dashboard_title': dashboard.get('title'),
                                'screenshot_path': download_path,
                                'success': True
                            })
                        except Exception as callback_error:
                            logger.warning(f"⚠️ Context callback failed: {callback_error}")
                    
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
                    
                    # Trigger context analysis callback if provided
                    if context_callback and dashboard:
                        try:
                            await context_callback({
                                'dashboard_id': dashboard.get('id'),
                                'dashboard_title': dashboard.get('title'),
                                'screenshot_path': download_path,
                                'success': True
                            })
                        except Exception as callback_error:
                            logger.warning(f"⚠️ Context callback failed: {callback_error}")
                    
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
                        
                        # Trigger context analysis callback if provided
                        if context_callback and dashboard:
                            try:
                                await context_callback({
                                    'dashboard_id': dashboard.get('id'),
                                    'dashboard_title': dashboard.get('title'),
                                    'screenshot_path': download_path,
                                    'success': True
                                })
                            except Exception as callback_error:
                                logger.warning(f"⚠️ Context callback failed: {callback_error}")
                        
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
                    
                    # Trigger context analysis callback if provided
                    if context_callback and dashboard:
                        try:
                            await context_callback({
                                'dashboard_id': dashboard.get('id'),
                                'dashboard_title': dashboard.get('title'),
                                'screenshot_path': download_path,
                                'success': True
                            })
                        except Exception as callback_error:
                            logger.warning(f"⚠️ Context callback failed: {callback_error}")
                    
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
                'timestamp': timestamp
            }
        ]
    

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