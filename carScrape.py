import requests
import json
import time
import random
import re
from datetime import datetime
import os

from TelegramHelper import TelegramHelper


class Yad2Monitor:
    def __init__(self):
        self.base_url = "https://www.yad2.co.il/vehicles/cars"
        self.known_listings = {}  # Dictionary to track listings we've seen
        self.history_file = "yad2_listings_history.json"
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1'
        ]
        self.load_history()
        self.last_request_time = 0
        self.telegram = TelegramHelper(
            bot_token="8177081670:AAHuO7F658tHTUX9rfXaaAYeqpu5_LmV7Ws",  # Replace with your bot token
            chat_id="-1002602358259"  # Replace with your group chat ID
        )

    def load_history(self):
        """Load previously seen listings from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.known_listings = json.load(f)
                print(f"Loaded {len(self.known_listings)} previous listings from history")
            except Exception as e:
                print(f"Error loading history file: {e}")
                self.known_listings = {}

    def save_history(self):
        """Save current listings to history file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.known_listings, f, ensure_ascii=False, indent=4)
            print(f"Saved {len(self.known_listings)} listings to history")
        except Exception as e:
            print(f"Error saving history file: {e}")

    def fetch_page(self, url):
        """Fetch the HTML content of the page with anti-blocking measures"""
        try:
            # Throttle requests to avoid being blocked
            current_time = time.time()
            elapsed = current_time - self.last_request_time

            # Force wait if previous request was too recent
            if elapsed < 30:
                wait_time = random.uniform(30, 60) - elapsed
                print(f"Throttling requests - waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)

            # Rotate user agents to appear as different browsers
            user_agent = random.choice(self.user_agents)

            # Create headers that look like a real browser
            headers = {
                'User-Agent': user_agent,
                'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Referer': 'https://www.yad2.co.il/',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1',
                'sec-ch-ua': '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }

            # Add random cookies
            cookies = {'visitor_id': f'{random.randint(10000000, 99999999)}'}

            print(f"Fetching page with User-Agent: {user_agent.split(' ')[0]}")
            response = self.session.get(
                url,
                headers=headers,
                cookies=cookies,
                timeout=30
            )

            # Record time of this request
            self.last_request_time = time.time()

            # If we get a 403 or other block indicator, wait longer
            if response.status_code == 403:
                print("Possible block detected (403 Forbidden). Waiting longer before next attempt...")
                time.sleep(random.uniform(300, 600))  # Wait 5-10 minutes
                return None

            response.raise_for_status()
            return response.text

        except requests.exceptions.RequestException as e:
            print(f"Error fetching page: {e}")
            # Wait longer if there's a connection error
            time.sleep(random.uniform(60, 120))
            return None

    def parse_car_listings(self, html):
        """Parse the HTML content to extract car listings"""
        listings = []

        # Regular expression to find car listing divs
        regex = r'<div class="feed-item-base_feedItemBox__5WVY1[^"]*"[^>]*data-testid="([^"]+)"[^>]*>'

        matches = re.finditer(regex, html)
        match_positions = []

        # Find all feed item boxes
        for match in matches:
            match_positions.append({
                'id': match.group(1),
                'index': match.start()
            })

        print(f"Found {len(match_positions)} potential car listings")

        # For each match, extract the relevant information
        for i in range(len(match_positions)):
            current_match = match_positions[i]
            next_index = match_positions[i + 1]['index'] if i < len(match_positions) - 1 else len(html)
            item_html = html[current_match['index']:next_index]

            # Extract key information using regex
            title = self.extract_text(item_html, r'<span class="feed-item-info_heading__k5pVC">([^<]+)</span>')
            sub_model = self.extract_text(item_html,
                                          r'<span class="feed-item-info_marketingText__eNE4R">([^<]+)</span>')
            year_hand = self.extract_text(item_html,
                                          r'<span class="feed-item-info_yearAndHandBox___JLbc"><span>([^<]+)</span>')
            price = self.extract_text(item_html, r'<span class="price_price__xQt90"[^>]*>([^<]+)</span>')

            # Try to extract image URL
            image_match = re.search(r'<img[^>]*data-nagish="feed-item-base-image"[^>]*src="([^"]+)"', item_html)
            image_url = image_match.group(1) if image_match else ''

            # Extract link to the listing
            link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*data-nagish="feed-item-base-link"', item_html)
            listing_link = link_match.group(1) if link_match else ''
            if listing_link and not listing_link.startswith('http'):
                listing_link = f"https://www.yad2.co.il{listing_link}"

            # Determine if it's from agency or private
            is_agency = 'commercial-item-left-side_agencyName__psfbp' in item_html
            seller_type = 'Agency' if is_agency else 'Private'

            # Extract seller name if available
            seller_name = ''
            if is_agency:
                seller_name = self.extract_text(item_html,
                                                r'<span class="commercial-item-left-side_agencyName__psfbp">([^<]+)</span>')

            # Extract more details if available
            km = self.extract_text(item_html, r'km">([^<]+)</span>')
            hand = self.extract_text(item_html, r'hand">([^<]+)</span>')

            # Add to listings array
            if title:
                listings.append({
                    'id': current_match['id'],
                    'title': title,
                    'sub_model': sub_model,
                    'year_hand': year_hand,
                    'price': price,
                    'seller_type': seller_type,
                    'seller_name': seller_name,
                    'image_url': image_url,
                    'link': listing_link
                })

        return listings

    def extract_text(self, html, pattern):
        """Helper function to extract text using a regex pattern"""
        match = re.search(pattern, html)
        return match.group(1).strip() if match else ''

    def check_for_new_listings(self, listings):
        """Check for new listings not seen before"""
        new_listings = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for listing in listings:
            listing_id = listing['id']

            # If we haven't seen this listing before, it's new
            if listing_id not in self.known_listings:
                listing['found_at'] = current_time
                new_listings.append(listing)

                # Add to known listings with timestamp
                self.known_listings[listing_id] = {
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'data': listing
                }
            else:
                # Update the last seen timestamp
                self.known_listings[listing_id]['last_seen'] = current_time
                # Update price if it changed
                if listing['price'] != self.known_listings[listing_id]['data']['price']:
                    old_price = self.known_listings[listing_id]['data']['price']
                    self.known_listings[listing_id]['data']['price'] = listing['price']
                    self.known_listings[listing_id]['data']['price_changed'] = True
                    self.known_listings[listing_id]['data']['old_price'] = old_price
                    print(f"Price changed for {listing['title']}: {old_price} -> {listing['price']}")

        return new_listings

    def display_listings(self, listings, is_new=False):
        """Display the car listings in a readable format"""
        if not listings:
            return

        prefix = "🆕 NEW" if is_new else "CURRENT"
        print(f"\n--- {prefix} LISTINGS ({len(listings)}) ---")

        for i, listing in enumerate(listings, 1):
            year_hand = listing.get('year_hand', '').split(' • ')
            year = year_hand[0] if len(year_hand) > 0 else ''
            hand = year_hand[1] if len(year_hand) > 1 else ''

            print(f"\n{i}. {listing.get('title', '')} {listing.get('sub_model', '')}")
            print(f"   Price: {listing.get('price', '')}")

            details = []
            if year:
                details.append(f"Year: {year}")
            if hand:
                details.append(f"Hand: {hand}")

            if details:
                print(f"   {' | '.join(details)}")

            if listing.get('seller_type'):
                seller_info = f"Seller: {listing['seller_type']}"
                if listing.get('seller_name'):
                    seller_info += f" ({listing['seller_name']})"
                print(f"   {seller_info}")

            if listing.get('link'):
                print(f"   Link: {listing['link']}")

        print("\n" + "-" * 60)

    def check_url(self, url):
        """Check a single URL for new listings"""
        # Fetch the page
        html_content = self.fetch_page(url)
        if not html_content:
            print(f"Failed to fetch page: {url}")
            return [], []

        # Parse and check for new listings
        listings = self.parse_car_listings(html_content)
        new_listings = self.check_for_new_listings(listings)

        return listings, new_listings

    def run_monitor(self, urls=None, interval_minutes=30, run_forever=True):
        """
        Main monitoring function. Checks for new listings at specified intervals.
        Sends notifications to Telegram when new listings are found.

        Parameters:
            urls: List of URLs to monitor
            interval_minutes: How often to check (in minutes)
            run_forever: Whether to run indefinitely or just once
        """
        if not urls:
            print("Error: At least one URL is required")
            return

        # Convert single URL to list if needed
        if isinstance(urls, str):
            urls = [urls]

        print(f"Starting Yad2 monitor with {len(urls)} URLs")
        for i, url in enumerate(urls, 1):
            print(f"URL {i}: {url}")
        print(f"Checking every {interval_minutes} minutes (with some randomization)")
        print("Telegram notifications enabled")

        try:
            iteration = 1
            while True:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{current_time}] Check #{iteration}")

                all_listings = []
                all_new_listings = []

                # Check each URL one by one
                for i, url in enumerate(urls, 1):
                    print(f"\nChecking URL {i}: {url}")
                    listings, new_listings = self.check_url(url)

                    # Display all current listings for this URL
                    print(f"URL {i} results:")
                    self.display_listings(listings)

                    # Add these listings to our collection
                    all_listings.extend(listings)
                    all_new_listings.extend(new_listings)

                # Handle new listings if any
                if all_new_listings:
                    self.display_listings(all_new_listings, is_new=True)
                    num_new = len(all_new_listings)
                    print(f"\n*** Found {num_new} new listings across all URLs! ***")

                    # Send Telegram notification
                    print("Sending notifications to Telegram...")

                    # Add the search URL to each listing for the Telegram message
                    for listing in all_new_listings:
                        if 'id' in listing:
                            listing_id = listing['id']
                            listing['url'] = f"https://www.yad2.co.il/item/{listing_id}"
                        else:
                            # Fallback to first URL if we can't determine the specific one
                            listing['url'] = urls[0]

                    # Send the listings to Telegram
                    self.telegram.send_multiple_listings(all_new_listings, is_new=True)
                    self.telegram.send_multiple_listings(all_listings, is_new=False)

                    print("Telegram notifications sent!")
                else:
                    print("\nNo new listings found across all URLs.")

                # Save the updated history
                self.save_history()

                # If not running forever, break after one check
                if not run_forever:
                    break

                # Sleep until next check with randomization
                jitter = random.uniform(-5, 5)  # +/- 5 minutes
                actual_interval = max(15, interval_minutes + jitter)  # Ensure minimum 15 min

                print(f"Next check in {actual_interval:.1f} minutes...")

                try:
                    # Sleep in smaller chunks so Ctrl+C works better
                    sleep_seconds = int(actual_interval * 60)
                    for _ in range(0, sleep_seconds, 10):
                        time.sleep(min(10, sleep_seconds - _))
                except KeyboardInterrupt:
                    print("\nMonitor stopped by user.")
                    self.save_history()
                    break

                iteration += 1

        except KeyboardInterrupt:
            print("\nMonitor stopped by user.")
            self.save_history()
        except Exception as e:
            print(f"Error in monitor: {e}")
            self.save_history()

if __name__ == "__main__":

    monitor = Yad2Monitor()

    urls = [
        "https://www.yad2.co.il/vehicles/cars?manufacturer=41&model=10574&year=2021-2023&km=0-100000&hand=0-1&seats=5&gearBox=102&yad2_source=latestSearchesPage",
        "https://www.yad2.co.il/vehicles/cars?year=2021-2024&price=-1-140000&km=10-55000&engineval=1600-2000&hand=0-1&topArea=2&seats=5&engineType=1101&gearBox=102&ownerID=1"
    ]

    monitor.run_monitor(
        urls=urls,
        interval_minutes=30
    )