from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import urllib3
import socket
from urllib.parse import unquote, parse_qs, urlparse
from selenium.webdriver.common.action_chains import ActionChains
import re
import subprocess
import shutil

class FacebookAdScraper:
    def __init__(self, quiet_mode=True):
        self.driver = None
        self.quiet_mode = quiet_mode
        self.setup_driver()
        self.flagged_ads = []  # Store flagged ads
        # Set predefined watch words
        self.watch_words = ["swimsuit", "underwear", "lingerie", "dating", "labiaplasty", "massage", "breast"]
        if not self.quiet_mode:
            print(f"Watching for the following words: {', '.join(self.watch_words)}")
        load_dotenv()  # Load environment variables
        
    def setup_driver(self):
        """Set up the Chrome WebDriver with appropriate options."""
        try:
            # First check internet connection
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=3)
            except OSError:
                raise Exception("No internet connection detected. Please check your connection.")

            chrome_options = Options()
            
            # Determine Chrome/Chromium binary location for cloud environment
            chrome_path = os.getenv("CHROME_PATH")
            # Try common binary names
            if not chrome_path:
                for exe in ("chromium", "chromium-browser"):  
                    path = shutil.which(exe)
                    if path:
                        chrome_path = path
                        break
            # Try common install paths
            if not chrome_path:
                for path in ("/usr/bin/chromium", "/usr/bin/chromium-browser"):  
                    if os.path.exists(path):
                        chrome_path = path
                        break
            # Only set binary_location if found
            if chrome_path:
                chrome_options.binary_location = chrome_path
            else:
                print("Warning: Chrome/Chromium binary not found; falling back to Firefox")
                # Fallback to Firefox if Chrome is unavailable
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from selenium.webdriver.firefox.service import Service as FirefoxService
                firefox_options = FirefoxOptions()
                firefox_options.headless = True
                gecko_path = shutil.which("geckodriver") or "/usr/bin/geckodriver"
                service = FirefoxService(executable_path=gecko_path)
                self.driver = webdriver.Firefox(service=service, options=firefox_options)
                # Set timeouts for Firefox
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                return
            
            # Cloud-specific options
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Disable SSL verification warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            if not self.quiet_mode:
                print("Installing ChromeDriver...")
            
            # Use chromedriver-binary-auto for cloud compatibility
            from selenium.webdriver.chrome.service import Service as ChromeService
            # Use CREATE_NO_WINDOW on Windows, fallback to 0 on other platforms
            try:
                creation_flag = subprocess.CREATE_NO_WINDOW
            except AttributeError:
                creation_flag = 0
            
            # Install and use a matching ChromeDriver via webdriver-manager
            driver_path = ChromeDriverManager().install()
            service = ChromeService(executable_path=driver_path)
            service.creation_flags = creation_flag
            
            if not self.quiet_mode:
                print("Starting Chrome browser...")
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            if not self.quiet_mode:
                print("Chrome WebDriver setup successful")
            
        except Exception as e:
            print(f"Error setting up Chrome WebDriver: {str(e)}")
            print("\nTroubleshooting steps:")
            print("1. Make sure you have a stable internet connection")
            print("2. Check if Chrome browser is installed and up to date")
            print("3. Try closing all Chrome windows and running the script again")
            print("4. If using a proxy or VPN, try disabling it temporarily")
            self.cleanup_driver()
            raise
        
    def cleanup_driver(self):
        """Clean up the WebDriver and its resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error during driver cleanup: {str(e)}")
            finally:
                self.driver = None
                
    def ensure_driver_active(self):
        """Ensure the WebDriver is active and responsive."""
        try:
            if not self.driver:
                self.setup_driver()
            # Try a simple operation to check if driver is responsive
            self.driver.current_url
            return True
        except Exception as e:
            print(f"Driver not active: {str(e)}")
            self.cleanup_driver()
            return False
        
    def login_to_facebook(self):
        """Login to Facebook if not already logged in."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not self.ensure_driver_active():
                    self.setup_driver()
                
                # Try to access Facebook
                print("Attempting to access Facebook...")
                self.driver.get("https://www.facebook.com")
                time.sleep(5)  # Wait for page to load
                
                # Check if we need to log in
                if "login" in self.driver.current_url.lower():
                    print("Please log in to Facebook in the browser window that opened.")
                    print("You have 60 seconds to complete the login...")
                    time.sleep(60)  # Give user time to log in
                    
                    # After login, navigate to Ad Library
                    print("Navigating to Ad Library after login...")
                    self.driver.get("https://www.facebook.com/ads/library/")
                    time.sleep(5)  # Wait for page to load
                    
                    # Check if we're still on login page
                    if "login" in self.driver.current_url.lower():
                        raise Exception("Login failed or timed out")
                return True
                    
            except Exception as e:
                print(f"Error during login attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    self.cleanup_driver()
                    time.sleep(5)
                else:
                    raise

    def get_final_url(self, url: str) -> str:
        """Get the final URL after any redirects."""
        try:
            if not self.ensure_driver_active():
                self.setup_driver()
            
            # Store the current window handle
            original_window = self.driver.current_window_handle
            
            # Open URL in a new tab
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(2)
            
            # Switch to the new tab
            new_window = [window for window in self.driver.window_handles if window != original_window][0]
            self.driver.switch_to.window(new_window)
            
            # Wait for the page to load and get the final URL
            time.sleep(5)
            final_url = self.driver.current_url
            
            # Close the new tab and switch back to original window
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            return final_url
        except Exception as e:
            print(f"Error getting final URL: {str(e)}")
            return url
        
    def set_watch_words(self, words: List[str]):
        """Set the list of words to watch for in ads."""
        self.watch_words = [word.lower() for word in words]
        if not self.quiet_mode:
            print(f"Watching for the following words: {', '.join(self.watch_words)}")

    def check_for_watch_words(self, text: str, ad_info: Dict) -> bool:
        """Check if any watch words appear in the text."""
        if not self.watch_words:
            return False
            
        text_lower = text.lower()
        found_words = []
        
        for word in self.watch_words:
            if word in text_lower:
                found_words.append(word)
                
        if found_words:
            flagged_info = {
                'matched_words': found_words,
                'ad_text': text,
                'library_id': ad_info.get('library_id'),
                'library_page': ad_info.get('library_page'),
                'urls': ad_info.get('urls', [])
            }
            self.flagged_ads.append(flagged_info)
            return True
            
        return False

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL by decoding it and extracting from Facebook redirect if needed."""
        if not url:
            return ""
            
        try:
            # First decode the URL and handle Facebook redirects
            decoded_url = url
            
            # Handle Facebook redirect links
            if 'facebook.com/l.php?' in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if 'u' in params:
                    decoded_url = params['u'][0]
            
            # Decode URL multiple times to handle nested encoding
            prev_url = None
            while prev_url != decoded_url:
                prev_url = decoded_url
                decoded_url = unquote(decoded_url)
            
            # Basic URL cleaning
            normalized = decoded_url.lower().strip()
            
            # Extract domain and path
            parsed = urlparse(normalized)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Remove common tracking parameters
            query_params = parse_qs(parsed.query)
            filtered_params = {k: v for k, v in query_params.items() 
                             if k.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 
                                                'key', 'creative_id', 'creative_name', 'campaign_id', 
                                                'campaign_name', 'adgroup_name', 'adgroup_id', 
                                                'placement', 'pixel', 'event']}
            
            # Reconstruct URL
            path = parsed.path.rstrip('/')
            if filtered_params:
                query = '&'.join(f"{k}={v[0]}" for k, v in filtered_params.items())
                normalized = f"{domain}{path}?{query}"
            else:
                normalized = f"{domain}{path}"
            
            if not self.quiet_mode:
                print(f"Original URL: {url}")
                print(f"Decoded URL: {decoded_url}")
                print(f"Normalized URL: {normalized}")
                
            return normalized
            
        except Exception as e:
            if not self.quiet_mode:
                print(f"Error normalizing URL {url}: {str(e)}")
            return url.lower()

    def _urls_match(self, url1: str, url2: str) -> bool:
        """Check if two URLs match after getting their final destinations."""
        try:
            # Get the base URLs without parameters
            def get_base_url(url):
                parsed = urlparse(url)
                # Remove www. if present
                domain = parsed.netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                # Get path without trailing slash
                path = parsed.path.rstrip('/')
                return f"{domain}{path}"

            # Get base URL for url1
            base_url1 = get_base_url(url1)
            
            # Get base URL for url2
            base_url2 = get_base_url(url2)
            
            if not self.quiet_mode:
                print(f"\nComparing URLs:")
                print(f"Base URL 1: {base_url1}")
                print(f"Base URL 2: {base_url2}")
            
            # Simple exact match of base URLs
            return base_url1 == base_url2
            
        except Exception as e:
            print(f"Error comparing URLs: {str(e)}")
            return False

    def _extract_image_url(self, ad_element) -> Optional[str]:
        """Extract image URL from an ad element using multiple approaches."""
        try:
            print("\nLooking for main ad creative...")
            
            # If we're on a "See ad details" element, go up to find the actual container
            if "See ad details" in ad_element.text:
                print("Found 'See ad details' element, looking for parent container...")
                try:
                    # Try going up multiple levels until we find a container with more content
                    current = ad_element
                    for _ in range(3):  # Try up to 3 levels up
                        parent = current.find_element(By.XPATH, "./..")
                        if len(parent.text) > len(current.text):
                            current = parent
                            print("Found larger parent container")
                        if "Library ID:" in parent.text:
                            current = parent
                            print("Found container with Library ID")
                            break
                    ad_element = current
                except Exception as e:
                    print(f"Error finding parent container: {str(e)}")

            # First try to find the main ad creative container
            main_creative_selectors = [
                "div[data-ft='{\"tn\":\"H\"}']",  # Main creative container
                "div.x1qjc9v5.x78zum5.x1q0g3np.x1a02dak",  # Creative wrapper
                "div.x78zum5.xdt5ytf.x1t2pt76.x1n2onr6",   # Image container
                "div.x78zum5.xdt5ytf.x1t2pt76",            # Another common container
                "div.x1qjc9v5.x78zum5.xl56j7k.x193iq5w"    # Video container
            ]

            print("\nSearching for main creative container...")
            main_container = None
            for selector in main_creative_selectors:
                try:
                    containers = ad_element.find_elements(By.CSS_SELECTOR, selector)
                    if containers:
                        # Get the largest container by size
                        main_container = max(containers, key=lambda x: x.size['width'] * x.size['height'])
                        print(f"Found main creative container with selector: {selector}")
                        break
                except:
                    continue

            if main_container:
                # First try to find a direct image in the main container
                try:
                    images = main_container.find_elements(By.TAG_NAME, "img")
                    # Filter out small images (likely icons) and profile pictures
                    for img in images:
                        try:
                            size = img.size
                            src = img.get_attribute("src")
                            if src and "fbcdn.net" in src:
                                # Check if it's not a profile picture (usually square and smaller)
                                if size['width'] > 100 and size['height'] > 100:
                                    # Prefer non-square images (likely to be ad creatives)
                                    if abs(size['width'] - size['height']) > 10:
                                        print(f"Found main creative image: {src}")
                                        print(f"Image size: {size['width']}x{size['height']}")
                                        return src
                        except:
                            continue

                    # If no suitable image found, try again without the size check
                    for img in images:
                        src = img.get_attribute("src")
                        if src and "fbcdn.net" in src:
                            print(f"Found potential creative image: {src}")
                            return src
                except:
                    pass

            # If still no image found, try a broader search with specific creative selectors
            creative_selectors = [
                "div.x1n2onr6 img",  # Common creative image
                "div.x1qjc9v5 img",   # Another creative container
                "div.x78zum5 img[src*='fbcdn.net']",  # Direct CDN images
                "div[role='img']"     # Role-based image containers
            ]

            print("\nTrying broader creative search...")
            for selector in creative_selectors:
                try:
                    elements = ad_element.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.tag_name == "img":
                            src = element.get_attribute("src")
                        else:
                            # For non-img elements, check background image
                            style = element.get_attribute("style")
                            if style and "background-image" in style:
                                url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                                src = url_match.group(1) if url_match else None
                            else:
                                continue

                        if src and "fbcdn.net" in src:
                            # Try to get size information
                            try:
                                size = element.size
                                if size['width'] > 100 and size['height'] > 100:
                                    print(f"Found creative with selector {selector}")
                                    print(f"Size: {size['width']}x{size['height']}")
                                    return src
                            except:
                                print(f"Found creative with selector {selector} (size unknown)")
                                return src
                except Exception as e:
                    print(f"Error with selector {selector}: {str(e)}")
                    continue

            # Last resort: find all images and try to identify the main creative
            print("\nTrying last resort image search...")
            all_images = ad_element.find_elements(By.TAG_NAME, "img")
            largest_image = None
            largest_size = 0

            for img in all_images:
                try:
                    src = img.get_attribute("src")
                    if src and "fbcdn.net" in src:
                        size = img.size
                        area = size['width'] * size['height']
                        if area > largest_size:
                            largest_size = area
                            largest_image = src
                except:
                    continue

            if largest_image:
                print(f"Found largest image in ad: {largest_image}")
                return largest_image

            print("No suitable creative image found")
            return None

        except Exception as e:
            print(f"\nError extracting image URL: {str(e)}")
            return None

    def search_ads(self, search_term: str, url_patterns: List[str] = None) -> List[Dict]:
        """
        Search for ads in Facebook Ad Library and collect their details including images.
        First checks if URLs match before collecting other details.
        """
        # Clear previous flagged ads
        self.flagged_ads = []
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not self.ensure_driver_active():
                    self.setup_driver()
                    
                # First ensure we're logged in
                if not self.login_to_facebook():
                    raise Exception("Failed to log in to Facebook")
                
                # Navigate to Facebook Ad Library
                print("Navigating to Facebook Ad Library...")
                self.driver.get("https://www.facebook.com/ads/library/")
                time.sleep(5)
                
                # Wait for the page to be fully loaded
                print("Waiting for page to load completely...")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Try to find and click the search box first
                print("Looking for search box...")
                search_box = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='search']"))
                )
                print("Found search box, entering search term...")
                
                # Clear the search box and enter the search term
                search_box.clear()
                time.sleep(1)
                search_box.send_keys(search_term)
                time.sleep(1)
                
                # Press Enter instead of submit
                search_box.send_keys(Keys.RETURN)
                time.sleep(5)
                
                # Wait for search results to load
                print("Waiting for search results to load...")
                try:
                    # Wait for any loading indicators to disappear
                    WebDriverWait(self.driver, 20).until(
                        lambda driver: not driver.find_elements(By.CSS_SELECTOR, "[role='progressbar']")
                    )
                    
                    # Wait for the search results container
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
                    )
                    
                    # Additional wait to ensure all ads are loaded
                    time.sleep(5)
                    
                    print("Search results loaded successfully")
                except TimeoutException:
                    print("Warning: Search results might not have loaded completely")
                
                # Scroll to load more ads
                print("Scrolling to load more ads...")
                self._scroll_to_load_more()
                
                print("\nAnalyzing all ad elements...")
                try:
                    # First find all ad elements using multiple selectors
                    print("Finding all ad elements...")
                    ad_elements = []
                    
                    # Try the most specific selector first
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
                    if elements:
                        ad_elements.extend(elements)
                        print(f"Found {len(elements)} elements with article role")
                    else:
                        # If no articles found, try other selectors
                        selectors = [
                            "div[data-testid='ad_card']",
                            "div[data-testid='fb-ad-card']",
                            "div.x1yztbdb:not([role='button'])",
                            "div.x1cy8zhl:not([role='button'])"
                        ]
                        
                        for selector in selectors:
                            if not ad_elements:  # Only try next selector if we haven't found elements yet
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements:
                                    ad_elements.extend(elements)
                                    print(f"Found {len(elements)} elements with selector: {selector}")
                    
                    # Remove duplicates while preserving order
                    ad_elements = list(dict.fromkeys(ad_elements))
                    print(f"\nFound {len(ad_elements)} unique ad elements")
                    
                    collected_ads = []
                    
                    for i, ad_element in enumerate(ad_elements, 1):
                        try:
                            print(f"\n{'='*80}")
                            print(f"Ad Element #{i}")
                            print(f"{'='*80}")
                            
                            # First, try to find the Learn More URL
                            learn_more_url = None
                            learn_more_final_url = None
                            
                            # Try multiple approaches to find links
                            link_finding_methods = [
                                # Method 1: Direct link elements
                                lambda: ad_element.find_elements(By.CSS_SELECTOR, "a[href*='l.php']"),
                                # Method 2: Links in parent
                                lambda: ad_element.find_element(By.XPATH, "./..").find_elements(By.TAG_NAME, "a"),
                                # Method 3: Links by role
                                lambda: ad_element.find_elements(By.CSS_SELECTOR, "a[role='link']"),
                                # Method 4: Any clickable element
                                lambda: ad_element.find_elements(By.CSS_SELECTOR, "[onclick], [role='button'], a")
                            ]
                            
                            print("\nLearn More Links Found:")
                            print("-" * 40)
                            
                            for method in link_finding_methods:
                                try:
                                    links = method()
                                    for link in links:
                                        href = link.get_attribute('href')
                                        text = link.text.strip()
                                        
                                        # Skip certain types of links
                                        if not href or not text:
                                            continue
                                        if any(x in text.lower() for x in ['see ad details', 'active ad', 'library id:']):
                                            continue
                                        if 'facebook.com/ads/library' in href:
                                            continue
                                            
                                        # Look specifically for the "Learn More" URL
                                        # It's usually the last URL that's not a Facebook profile link
                                        if not href.startswith('https://www.facebook.com/') or 'l.php' in href:
                                            learn_more_url = href
                                            learn_more_final_url = self.get_final_url(href)
                                            
                                            print(f"Text: {text}")
                                            print(f"Original URL:  {href}")
                                            print(f"Final URL:    {learn_more_final_url}")
                                            print("-" * 20)
                                            break
                                            
                                    if learn_more_url:
                                        break
                                except:
                                    continue
                            
                            # If no Learn More URL found, skip this ad
                            if not learn_more_url:
                                print("No Learn More URL found, skipping ad")
                                continue
                                
                            # Check if the Learn More URL matches any of the patterns
                            url_matched = False
                            if url_patterns:
                                for pattern in url_patterns:
                                    if self._urls_match(learn_more_final_url, pattern):
                                        url_matched = True
                                        break
                                        
                                if not url_matched:
                                    print(f"Learn More URL {learn_more_final_url} did not match any patterns, skipping ad")
                                    continue
                            
                            # If we get here, either there are no patterns to match or the URL matched
                            # Now collect all other ad details
                            print("\nURL matched! Collecting ad details...")
                            
                            # Get all text content
                            ad_text = ad_element.text
                            if not ad_text or ad_text.strip() == "See ad details":
                                parent = ad_element.find_element(By.XPATH, "./..")
                                if parent:
                                    ad_text = parent.text
                            
                            # Extract ad page URL from advertiser link
                            ad_page_url = None
                            try:
                                # Look for advertiser link with specific class
                                advertiser_link = ad_element.find_element(By.CSS_SELECTOR, "a.xt0psk2.x1hl2dhg.xt0b8zv.x8t9es0.x1fvot60.xxio538.xjnfcd9.xq9mrsl.x1yc453h.x1h4wwuj.x1fcty0u")
                                if advertiser_link:
                                    ad_page_url = advertiser_link.get_attribute('href')
                            except:
                                # Fallback: try to find any link with the advertiser name pattern
                                try:
                                    links = ad_element.find_elements(By.TAG_NAME, "a")
                                    for link in links:
                                        href = link.get_attribute('href')
                                        if href and '/ads/library/' not in href and 'facebook.com/' in href and not href.startswith('https://www.facebook.com/ads/'):
                                            ad_page_url = href
                                            break
                                except:
                                    pass
                            
                            ad_info = {
                                'urls': [learn_more_final_url],
                                'original_urls': [learn_more_url],
                                'library_id': None,
                                'ad_text': ad_text,
                                'library_page': learn_more_url,
                                'image_url': None,
                                'ad_page_url': ad_page_url  # Add the ad page URL
                            }
                            
                            # Check for watch words in ad text
                            if self.watch_words:
                                self.check_for_watch_words(ad_text, ad_info)
                            
                            # Look for Library ID
                            if 'Library ID:' in ad_text:
                                for line in ad_text.split('\n'):
                                    if 'Library ID:' in line:
                                        library_id = line.split('Library ID:')[1].strip()
                                        print(f"\nLibrary ID Found: {library_id}")
                                        ad_info['library_id'] = library_id
                                        break
                            
                            # If no Library ID found in text, look for 15-16 digit numbers
                            if not ad_info['library_id']:
                                matches = self.driver.execute_script("""
                                    function findIds(element) {
                                        const text = element.innerText || element.textContent;
                                        const matches = text.match(/\\b\\d{15,16}\\b/g) || [];
                                        return matches;
                                    }
                                    return findIds(arguments[0]);
                                """, ad_element)
                                
                                if matches:
                                    ad_info['library_id'] = matches[0]
                            
                            # Extract image URL
                            image_url = self._extract_image_url(ad_element)
                            if image_url:
                                print(f"Found image URL: {image_url}")
                                ad_info['image_url'] = image_url
                            
                            # Add to collected ads
                            collected_ads.append(ad_info)
                            
                        except Exception as e:
                            print(f"Error analyzing ad element: {str(e)}")
                            continue
                    
                except Exception as e:
                    print(f"Error during analysis: {str(e)}")
                
                print("\nAnalysis complete")
                return collected_ads
                    
            except TimeoutException as e:
                print(f"Timeout error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                self.cleanup_driver()
                time.sleep(5)
                
            except WebDriverException as e:
                print(f"WebDriver error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                self.cleanup_driver()
                time.sleep(5)
                
            except Exception as e:
                print(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                self.cleanup_driver()
                time.sleep(5)
        
        return []

    def _scroll_to_load_more(self):
        """Scroll the page to load more ads."""
        print("Starting to scroll...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 5  # Limit scrolling to avoid timeouts
        
        while scroll_count < max_scrolls:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Increased wait time
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_count += 1
            print(f"Scroll {scroll_count}/{max_scrolls} completed")
    
    def _extract_ad_details(self, ad_element) -> Optional[Dict]:
        """Extract relevant details from an ad element."""
        try:
            # Get ad text using the exact HTML structure
            ad_text = ad_element.find_element(By.CSS_SELECTOR, "div.x1iorvi4.x1pi30zi").text
            
            # Get advertiser name using the exact HTML structure
            advertiser = ad_element.find_element(By.CSS_SELECTOR, "div.x1iorvi4.x1pi30zi a[role='link']").text
            
            # Try to find the link using the exact HTML structure
            link = ad_element.find_element(By.CSS_SELECTOR, "a.x1hl2dhg.x1lku1pv.x1a2a7pz.x1t2pt76.xb9moi8.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16ldp7u.x1hl2dhg.x1lku1pv.x1a2a7pz.x1t2pt76.xb9moi8.xe8uvvx.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.xexx8yu.x4uap5.x18d9i69.xkhd6sd.x16ldp7u")
            href = link.get_attribute('href')
            
            # Extract image URL - get the raw src attribute without any processing
            try:
                image_div = ad_element.find_element(By.CSS_SELECTOR, "div.x1ywc1zp.x78zum5.xl56j7k.x1e56ztr.x1277o0a")
                image_url = image_div.find_element(By.TAG_NAME, "img").get_attribute("src")
            except:
                image_url = None
            
            if not href or ('http' not in href and 'facebook.com/l.php' not in href):
                print("No valid link found in ad")
                return None
            
            print(f"Found link: {href}")
            if image_url:
                print(f"Found image URL: {image_url}")
            
            return {
                "advertiser": advertiser,
                "ad_text": ad_text,
                "learn_more_link": href,
                "original_url": href,  # Keep the original URL
                "image_url": image_url  # Raw image URL without processing
            }
        except Exception as e:
            print(f"Error extracting ad details: {str(e)}")
            return None
    
    def close(self):
        """Close the WebDriver."""
        self.cleanup_driver()

    def _extract_url_from_facebook_redirect(self, url: str) -> str:
        """Extract the actual destination URL from a Facebook redirect link."""
        try:
            if 'l.php?' in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if 'u' in params:
                    return unquote(params['u'][0])
            return url
        except:
            return url
            
    def check_urls(self, url_pattern: str, ad_links: List[Dict]) -> List[Dict]:
        """Check URLs against a pattern and return matching ads."""
        matching_urls = []
        try:
            print(f"\nChecking URLs against pattern: {url_pattern}")
            
            for i, ad in enumerate(ad_links):
                learn_more_link = ad.get('learn_more_link', '')
                
                # Skip empty links
                if not learn_more_link:
                    continue
                    
                print(f"\nChecking URL: {learn_more_link}")
                
                # Try to match URLs
                if self._urls_match(learn_more_link, url_pattern):
                    print(f"Found matching URL!")
                    
                    # Try to extract Ad Library ID
                    library_id = None
                    if 'library_id' in ad:
                        library_id = ad['library_id']
                    elif 'ad_id' in ad:
                        library_id = ad['ad_id']
                        
                    # Construct Ad Library URL if we have an ID
                    ad_library_url = None
                    if library_id:
                        ad_library_url = f"https://www.facebook.com/ads/library/?id={library_id}"
                        print(f"Found Ad Library URL: {ad_library_url}")
                    
                    # Add to matches
                    matching_urls.append({
                        'url': learn_more_link,
                        'ad_text': ad.get('ad_text', ''),
                        'learn_more_link': learn_more_link,
                        'ad_library_url': ad_library_url,
                        'library_id': library_id
                    })
                else:
                    print("No match found")
            
        except Exception as e:
            print(f"Error during URL checking: {str(e)}")
        
        return matching_urls

    def scrape_ad_by_link(self, ad_link: str) -> Optional[Dict]:
        """Scrape a single Facebook Ad Library ad given its URL."""
        # Ensure WebDriver is ready
        if not self.ensure_driver_active():
            self.setup_driver()
        try:
            # Navigate to the ad link
            self.driver.get(ad_link)
            time.sleep(5)  # Wait for the page to load
            # Wait for the ad container to appear
            ad_element = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']"))
            )
            # Extract ad text
            ad_text = ad_element.text or ""
            # Parse library ID from the URL query parameters
            parsed = urlparse(ad_link)
            params = parse_qs(parsed.query)
            library_id = params.get('id', [None])[0]
            # Extract image URL
            image_url = self._extract_image_url(ad_element)
            # Build ad info dictionary
            return {
                'ad_text': ad_text,
                'library_id': library_id,
                'urls': [ad_link],
                'original_urls': [ad_link],
                'library_page': ad_link,
                'image_url': image_url,
                'ad_page_url': ad_link
            }
        except Exception as e:
            print(f"Error scraping ad by link {ad_link}: {e}")
            return None

def main():
    # Example usage
    scraper = None
    try:
        scraper = FacebookAdScraper()
        
        search_term = input("Enter search term: ")
        
        print(f"Starting search for term: {search_term}")
        print("Analyzing ads in the Facebook Ad Library...")
        
        # Get ad information
        ads = scraper.search_ads(search_term)
        
        if not ads:
            print("\nNo ads found.")
            return
            
        # Store all matching ads across multiple URL searches
        all_matching_ads = []
        
        while True:
            # Ask user for URL pattern to match
            url_pattern = input("\nEnter the URL pattern to match (e.g., https://example.com): ")
            
            # Find ads with matching URLs and their Library IDs
            matching_ads = []
            for ad in ads:
                for url in ad['urls']:
                    print(f"\nChecking URL: {url}")
                    
                    # Use the new _urls_match method for better matching
                    if scraper._urls_match(url, url_pattern):
                        if ad['library_id']:
                            # Get the normalized version of the URL for display
                            normalized_url = scraper._normalize_url(url)
                            matching_ads.append({
                                'original_url': url,
                                'actual_url': normalized_url,
                                'library_id': ad['library_id'],
                                'library_page': ad['library_page'],
                                'library_link': f"https://www.facebook.com/ads/library/?id={ad['library_id']}",
                                'image_url': ad.get('image_url')  # Include image URL if available
                            })
                            print(f"Found match!")
                        break  # Only need one matching URL per ad
            
            # Add any matches to our total results
            all_matching_ads.extend(matching_ads)
            
            # Display results for this URL pattern
            if matching_ads:
                print(f"\nFound {len(matching_ads)} ads with URLs matching {url_pattern}:")
                print("\nLibrary IDs for matching ads:")
                print("-" * 50)
                for ad in matching_ads:
                    print(f"Original URL: {ad['original_url']}")
                    print(f"Actual URL: {ad['actual_url']}")
                    print(f"Library ID: {ad['library_id']}")
                    print(f"Library Page: {ad['library_page']}")
                    print(f"Library Link: {ad['library_link']}")
                    if ad.get('image_url'):
                        print(f"Image URL: {ad['image_url']}")
                    print("-" * 50)
            else:
                print(f"\nNo ads found with URLs matching pattern: {url_pattern}")
                print("Note: The URL matcher now supports:")
                print("1. Domain matching (e.g., 'example.com')")
                print("2. Partial URL matching")
                print("3. Facebook redirect URL resolution")
                print("4. Case-insensitive matching")
            
            # Ask if user wants to search for more URLs
            while True:
                search_more = input("\nWould you like to look for more URLs? (yes/no): ").lower()
                if search_more in ['yes', 'no', 'y', 'n']:
                    break
                print("Please answer 'yes' or 'no'")
            
            if search_more.startswith('n'):
                break
        
        # Display final summary of all matches
        if all_matching_ads:
            print(f"\nFinal Summary - Found {len(all_matching_ads)} total matching ads:")
            print("\nAll Library IDs and Links:")
            print("-" * 50)
            # Use a set to track unique library IDs we've seen
            seen_ids = set()
            for ad in all_matching_ads:
                if ad['library_id'] not in seen_ids:
                    seen_ids.add(ad['library_id'])
                    print(f"Library ID: {ad['library_id']}")
                    print(f"Library Page: {ad['library_page']}")
                    print(f"Library Link: {ad['library_link']}")
                    print(f"Found in URL: {ad['actual_url']}")
                    if ad.get('image_url'):
                        print(f"Image URL: {ad['image_url']}")
                    print("-" * 50)
        else:
            print("\nNo matching ads found for any of the searched URLs.")
        
        # Display flagged ads if any were found
        if scraper.flagged_ads:
            print("\n" + "="*80)
            print("FLAGGED ADS - Watch Words Found:")
            print("="*80)
            
            for i, flagged_ad in enumerate(scraper.flagged_ads, 1):
                print(f"\nFlagged Ad #{i}:")
                print("-" * 50)
                print(f"Matched Words: {', '.join(flagged_ad['matched_words'])}")
                if flagged_ad['library_id']:
                    print(f"Library Link: https://www.facebook.com/ads/library/?id={flagged_ad['library_id']}")
                if flagged_ad['library_page']:
                    print(f"Ad Page: {flagged_ad['library_page']}")
                if flagged_ad['urls']:
                    print("\nAll URLs found in ad:")
                    for url in flagged_ad['urls']:
                        print(f"- {url}")
                print("\nAd Text Preview:")
                print("-" * 20)
                # Print first 200 characters of ad text with ellipsis if longer
                preview = flagged_ad['ad_text'][:200]
                if len(flagged_ad['ad_text']) > 200:
                    preview += "..."
                print(preview)
                print("-" * 50)
            
            print(f"\nTotal Flagged Ads: {len(scraper.flagged_ads)}")
        
        # Keep the window open until user chooses to close
        input("\nPress Enter when you want to close the browser window...")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Please check if:")
        print("1. You have a stable internet connection")
        print("2. You can access Facebook in your browser")
        print("3. You're logged into Facebook")
        print("4. The Facebook Ad Library is accessible in your region")
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main() 