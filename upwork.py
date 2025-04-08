import cloudscraper
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import re
import time
import subprocess
import os

load_dotenv()

# Edit the following to add your own Telegram bot token and chat ID in the .env file
TOKEN = os.getenv("TOKEN") # TOKEN=<YourTelegramBotToken>
CHAT_ID = os.getenv("CHAT_ID") # CHAT_ID=<YourChatID>

scraper = cloudscraper.create_scraper()

# Edit the URL to specify the job search query on Upwork
url = "https://www.upwork.com/nx/search/jobs/?page=1&per_page=20&q=%28automation%20OR%20python%20OR%20automate%20OR%20bot%20OR%20spreadsheet%20OR%20scrap%29"

# Ensure the "warp-cli" command is available on your system, or remove if not using Warp VPN
def run_warp():
    subprocess.run(["warp-cli", "disconnect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    subprocess.run(["warp-cli", "connect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   
    time.sleep(10)
run_warp()

def telegram(message=None):
	global TOKEN, CHAT_ID
	try:
		if message:
			for x in message:
				print(x)
				part1 = f"Title: {x}\nProposal: {message[x][2]}\nPrice: {message[x][3]}\n"
				part2 = message[x][0]
				part3 = message[x][1]
				combined_message = f"{part1}\n{part2}\n{part3}"

				chunks = [combined_message[i:i+4096] for i in range(0, len(combined_message), 4096)]

				for chunk in chunks:
					method = "sendMessage"
					url = f"https://api.telegram.org/bot{TOKEN}/{method}"
					data = {
						"chat_id": CHAT_ID,
						"text": chunk
					}
					response = requests.post(url=url, data=data)
					if response.status_code == 200:
						print(f"Sent chunk: {chunk[:30]}...")
					else:
						print(f"Failed to send chunk: {response.status_code}")

				separator = "\n==============================================================================================================================================================================\n"
				url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
				data = {
					"chat_id": CHAT_ID,
					"text": separator
				}
				response = requests.post(url=url, data=data)
				if response.status_code == 200:
					print("Separator sent.")
				else:
					print(f"Failed to send separator: {response.status_code}")

	except Exception as e:
		print(f"Error occurred: {e}")
		return

def last():
    global old_job
    response = scraper.get(url)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    old_job = soup.find('h2',class_='h5 mb-0 mr-2 job-tile-title').text
    print(old_job)

def main():
    global old_job
    while True:
        jobs = {}
        response = scraper.get(url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        job = soup.find_all('h2',class_='h5 mb-0 mr-2 job-tile-title')
        last_job = soup.find('h2',class_='h5 mb-0 mr-2 job-tile-title').text
        for x in job:
            a_tag = x.find('a')
            if a_tag:
                try:
                    title = a_tag.text.strip()
                    if title == old_job:
                        old_job = last_job
                        time.sleep(60)
                        break
                    link = 'https://upwork.com'+a_tag['href']
                    response = scraper.get(link)
                    html = response.text
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.find('div',class_='break mt-2').text
                    clean_text = re.sub(r'\s+', ' ', text).strip()
                    priceelement = soup.find_all(class_='description')
                    price = priceelement[0].find_previous_sibling()
                    price = price.get_text(strip=True)
                    if price[0] != "$":
                        price = priceelement[3].find_previous_sibling()
                        price = price.get_text(strip=True)
                        if price == "Ongoing project" or "Complex project":
                              price = "Not Sure"
                    proposal = soup.find(class_='value').text
                    jobs[title] = clean_text,link,proposal,price
                except Exception as e:
                    print(e)
        telegram(jobs)
last()
main()
