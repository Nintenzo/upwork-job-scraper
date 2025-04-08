# Upwork Job Scraper

This script scrapes job listings from Upwork based on specific search terms, collects job details, and sends them via Telegram. The script is designed to automatically monitor job posts and notify you when new relevant jobs are posted.

To customize the search filter:
- Go to the Upwork Job Search page.
- Apply your desired filters (keywords, job categories, etc.).
- Copy the URL from your browser's address bar after applying the filters.
- Replace the current URL in the script with the new one

## Features

- Scrapes job listings from Upwork based on defined search criteria.
- Sends detailed job information (title, description, price, and proposal) to a specified Telegram chat.
- Uses Cloudflare 1.1.1.1 Warp VPN to avoid IP-based rate limits, rather than a traditional proxy.

## Prerequisites

Before running this script, make sure you have the following:

- **Python 3.x**: Ensure that you have Python installed on your system.
- **Telegram Bot**: You need to create a Telegram bot to send messages. [Here's a guide to creating a bot on Telegram](https://core.telegram.org/bots#botfather).
- **Cloudflare 1.1.1.1 Warp**: This script uses Cloudflare’s Warp VPN instead of proxies because free proxies are often unreliable and easily blocked. Warp is a free, stable, and fast service that helps bypass rate limits and IP restrictions, providing a more reliable option for scraping job listings.


## Setup Instructions

### 1. Install Dependencies

You can install the required libraries using the `requirements.txt` file:

```bash
pip install -r requirements.txt
