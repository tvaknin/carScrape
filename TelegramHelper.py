import requests


class TelegramHelper:
    """
    Helper class to send messages to Telegram.
    """

    def __init__(self, bot_token, chat_id):
        """
        Initialize the Telegram helper.

        Parameters:
            bot_token: Your Telegram bot token from BotFather
            chat_id: The chat ID of your group
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        # Done! Congratulations on your new bot. You will find it at t.me/YadTiguanBot. You can now add a description, about section and profile picture for your bot, see /help for a list of commands. By the way, when you've finished creating your cool bot, ping our Bot Support if you want a better username for it. Just make sure the bot is fully operational before you do this.
        #
        # Use this token to access the HTTP API:
        # 8177081670:AAHuO7F658tHTUX9rfXaaAYeqpu5_LmV7Ws
        # Keep your token secure and store it safely, it can be used by anyone to control your bot.
        #
        # For a description of the Bot API, see this page: https://core.telegram.org/bots/api

    def send_message(self, text):
        """
        Send a simple text message to the Telegram group.

        Parameters:
            text: The message text to send

        Returns:
            Response from Telegram API
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"  # Enables HTML formatting
        }

        try:
            response = requests.post(url, data=payload)
            return response.json()
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return None

    def send_listing(self, listing):
        """
        Send a formatted message about a car listing.

        Parameters:
            listing: Dictionary containing listing details

        Returns:
            Response from Telegram API
        """
        # Create a nicely formatted message with proper RTL support
        message = f"🚗 <b>New Listing Found!</b>\n\n"

        # Add listing details with proper formatting for Hebrew
        if 'title' in listing:
            message += f"<b>{listing['title']}</b>\n\n"
        if 'sub_model' in listing:
            message += f"📋 <b>Model:</b> {listing['sub_model']}\n"
        if 'price' in listing:
            message += f"💰 <b>Price:</b> {listing['price']}\n"
        if 'year_hand' in listing:
            message += f"📅 <b>Info:</b> {listing['year_hand']}\n"
        if 'seller_name' in listing:
            message += f"👤 <b>Seller:</b> {listing['seller_name']}\n"
        if 'seller_type' in listing:
            message += f"🏢 <b>Type:</b> {listing['seller_type']}\n"

        # Add spacing before link
        message += "\n"

        # Add the URL if available
        if 'id' in listing:
            listing_url = f"https://www.yad2.co.il/item/{listing['id']}"
            message += f"<a href='{listing_url}'>🔗 View on Yad2</a>"
        elif 'link' in listing and listing['link']:
            message += f"<a href='{listing['link']}'>🔗 View on Yad2</a>"

        return self.send_message(message)

    def send_multiple_listings(self, listings, is_new=True):
        """
        Send a summary of multiple listings.

        Parameters:
            listings: List of listing dictionaries
            is_new: Whether these are new listings (for message formatting)

        Returns:
            Response from the last message sent
        """
        response = None

        # For NEW listings: Send detailed individual messages
        if is_new:
            message = f"🚨 <b>NEW LISTINGS ALERT</b> 🚨\n\n<b>Found {len(listings)} new listings:</b>"
            self.send_message(message)

            # Send individual details for each new listing (with links)
            for listing in listings:
                response = self.send_listing(listing)

        # For CURRENT listings: Just send a simple summary without links
        else:
            # Create a compact summary of all current listings
            summary = f"📋 <b>Current Listings Summary ({len(listings)})</b>\n\n"

            # Add a one-line summary for each listing
            for i, listing in enumerate(listings[:20]):  # Show max 20 in summary
                title = listing.get('title', 'Unnamed Listing')
                price = listing.get('price', 'N/A')
                sub_model = listing.get('sub_model', '')
                year_hand = listing.get('year_hand', '')
                seller_type = listing.get('seller_type', '')

                # Format: "1. Title - Sub_model - Price - Year/Hand - Seller_type"
                summary += f"{i + 1}. <b>{title}</b>"
                if sub_model:
                    summary += f" - {sub_model}"
                summary += f" - {price}"
                if year_hand:
                    summary += f" - {year_hand}"
                if seller_type:
                    summary += f" - {seller_type}"
                summary += "\n"

            # If there are more than 20 listings
            if len(listings) > 20:
                summary += f"\n...and {len(listings) - 20} more listings."

            # Send the single summary message
            response = self.send_message(summary)

        return response