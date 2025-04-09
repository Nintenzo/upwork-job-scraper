import cloudscraper
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import re
import time
import subprocess
import os

load_dotenv()

jobset = set()
# Edit the following to add your own Telegram bot token and chat ID in the .env file
TOKEN = os.getenv("TOKEN") # TOKEN=<YourTelegramBotToken>
CHAT_ID = os.getenv("CHAT_ID") # CHAT_ID=<YourChatID>

scraper = cloudscraper.create_scraper()

# Edit the URL to specify the job search query on Upwork
url = "https://www.upwork.com/nx/search/jobs/"

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
				# title,clean_text0,link1,proposal2,price_text3,price4,experience_text5,experience6,proposal7
				part1 = f"Title: {x}\nProposal: {message[x][7].strip()}\n{message[x][3].strip()}: {message[x][4].strip()}\n{message[x][5].strip()}: {message[x][6].strip()}"
				part2 = f"Link: {message[x][1]}"
				part3 = message[x][0]  
				combined_message = f"{part1}\n\n{part3}\n\n{part2}"

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

def scrapy(soup):
    global old_job,jobset
    jobs = {}
    job = soup.find_all('h2',class_='h5 mb-0 mr-2 job-tile-title')
    last_job = soup.find('h2',class_='h5 mb-0 mr-2 job-tile-title').text
    for x in job:
        a_tag = x.find('a')
        if a_tag:
            try:
                title = a_tag.text.strip()
                if title == old_job:
                    old_job = last_job
                    time.sleep(120)
                    break
                link = 'https://upwork.com'+a_tag['href']
                response = scraper.get(link)
                html = response.text
                soup = BeautifulSoup(html, "html.parser")
                text = soup.find('div',class_='break mt-2').text
                clean_text = re.sub(r'\s+', ' ', text).strip()
                price = "Not specified"
                experience = "Not specified"
                experience_text = "Not specified"
                price_elements = soup.find_all(class_='description')
                for elm in price_elements:
                    pricecheck = elm.find_previous_sibling().get_text(strip=True)
                    if pricecheck[0] == "$":
                        price_text = elm.text
                        price = pricecheck
                        break
                    else:
                        price = "Price not set"
                for elm in price_elements:
                    experiencecheck = elm.get_text(strip=True)
                    experience = elm.find_previous_sibling().get_text(strip=True)
                    if experiencecheck == "Experience Level":
                        experience_text = elm.text
                        experience = experience
                        break
                    else:
                        experience = "Experience not set"
                proposal_element = soup.find(class_='value')
                proposal = proposal_element.text if proposal_element else "Not specified"
                if link in jobset: 
                    continue
                else:
                    jobset.add(link)
                    jobs[title] = clean_text,link,proposal,price_text,price,experience_text,experience,proposal
            except Exception:
                pass
    return jobs 
            
def main():
    global jobset
    try:
        while True:
            if len(jobset) >= 100:
                 jobset.clear()
            response = scraper.get(url)
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            data = scrapy(soup)
            telegram(data)
    except Exception as e:
        print(e)
last()
main()
