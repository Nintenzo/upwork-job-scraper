import cloudscraper
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import re
import time
import threading
import hashlib
import json
import subprocess
import os

load_dotenv()

scraper = cloudscraper.create_scraper()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

url = "https://www.upwork.com/nx/search/jobs/?proposals=0-4,5-9,10-14,15-19&q=%28automation%20OR%20python%20OR%20automate%20OR%20bot%20OR%20spreadsheet%20OR%20scrap%20OR%20api%29&page=1&per_page=20"
DESCRIPTIONS_FILE = "descriptions.json"

job_descriptions = {}
jobset = set()

# --- Load descriptions from file ---
def load_descriptions():
	global job_descriptions
	if os.path.exists(DESCRIPTIONS_FILE):
		with open(DESCRIPTIONS_FILE, "r", encoding="utf-8") as f:
			try:
				job_descriptions = json.load(f)
			except json.JSONDecodeError:
				job_descriptions = {}
	else:
		job_descriptions = {}

# --- Save descriptions to file ---
# --- Save descriptions to file ---  
def save_descriptions():
    # Check if job_descriptions has exceeded 5000 entries
    if len(job_descriptions) >= 5000:
        print("Job descriptions limit reached, clearing the file.")
        job_descriptions.clear()  # Clear the job descriptions if limit is reached
        
    with open(DESCRIPTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(job_descriptions, f, ensure_ascii=False, indent=2)


# --- Optional Warp VPN switch ---
def run_warp():
	subprocess.run(["warp-cli", "disconnect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	subprocess.run(["warp-cli", "connect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   

	while True:
		result = subprocess.run(["warp-cli", "status"], capture_output=True, text=True)
		if "Connected" in result.stdout:
			break
		time.sleep(1)
run_warp()

# --- Handle callback queries ---
def handle_callback():
    global TOKEN
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    processed = set()  # Initialize this inside the function to avoid shared state
	
    while True:
        try:
            resp = requests.get(url)
            data = resp.json()

            if "result" in data:
                for item in data["result"]:
                    if "callback_query" in item:
                        cq = item["callback_query"]
                        cb_id = cq["id"]
                        cid = cq["message"]["chat"]["id"]
                        cb_data = cq["data"]

                        if cb_data.startswith("desc_") and cb_data not in processed:
                            processed.add(cb_data)
                            uid = cb_data.split("_")[1]
                            description = job_descriptions.get(uid, "No description found.")

                            # Remove loading spinner
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                                          json={"callback_query_id": cb_id})

                            # Send description
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                                "chat_id": cid,
                                "text": f"📄 <b>Job Description</b>:\n{description}",
                                "parse_mode": "HTML"
                            })
            time.sleep(2)
        except Exception as e:
            print("Callback error:", e)
            time.sleep(3)


# --- Send job message to Telegram ---
def telegram(message=None):
	global TOKEN, CHAT_ID
	if not message:
		return
	try:
		for title in message:
			job = message[title]
			uid = hashlib.md5(job[1].encode()).hexdigest()[:10]
			job_descriptions[uid] = job[0]
			save_descriptions()
			caption = (
				f"📌 <b>{title}</b>\n"
				f"💼 <b>{job[3].strip()}</b>: {job[4].strip()}\n"
				f"⚙️ <b>{job[5].strip()}</b>: {job[6].strip()}\n"
				f"📎 <a href='{job[1]}'>Job Link</a>"
			)

			url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
			payload = {
				"chat_id": CHAT_ID,
				"text": caption,
				"parse_mode": "HTML",
				"reply_markup": {
					"inline_keyboard": [[
						{"text": "📝 View Description", "callback_data": f"desc_{uid}"}
					]]
				}
			}
			response = requests.post(url, json=payload)
			if response.status_code == 200:
				print(f"Sent job: {title}")
			else:
				print(f"Failed to send job: {response.status_code} {response.text}")
	except Exception as e:
		print(f"Error occurred: {e}")

# --- Get initial last job ---
def last():
	global old_job
	response = scraper.get(url)
	if response.status_code in ["403","429","400"]:
		run_warp()
		response = scraper.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	old_job = soup.find('h2', class_='h5 mb-0 mr-2 job-tile-title').text
	print("Initial last job:", old_job)

# --- Scrape job details ---
def scrapy(soup):
	global old_job, jobset
	jobs = {}
	job = soup.find_all('h2', class_='h5 mb-0 mr-2 job-tile-title')
	last_job = soup.find('h2', class_='h5 mb-0 mr-2 job-tile-title').text
	for x in job:
		a_tag = x.find('a')
		if a_tag:
			try:
				title = a_tag.text.strip()
				if title == old_job:
					old_job = last_job
					time.sleep(120)
					break
				link = 'https://upwork.com' + a_tag['href']
				if link in jobset:
					continue

				response = scraper.get(link)
				if response.status_code in ["403","429","400"]:
					run_warp()
					response = scraper.get(url)
				soup = BeautifulSoup(response.text, "html.parser")
				text = soup.find('div', class_='break mt-2').text
				clean_text = re.sub(r'\s+', ' ', text).strip()

				price = "Not specified"
				experience = "Not specified"
				experience_text = "Not specified"
				price_text = "Not specified"
				price_elements = soup.find_all(class_='description')
				for elm in price_elements:
					pricecheck = elm.find_previous_sibling().get_text(strip=True)
					if pricecheck.startswith("$"):
						price_text = elm.text
						price = pricecheck
						break
				for elm in price_elements:
					experiencecheck = elm.get_text(strip=True)
					if experiencecheck == "Experience Level":
						experience = elm.find_previous_sibling().get_text(strip=True)
						experience_text = elm.text
						break

				proposal_element = soup.find(class_='value')
				proposal = proposal_element.text if proposal_element else "Not specified"

				jobset.add(link)
				jobs[title] = clean_text, link, proposal, price_text, price, experience_text, experience, proposal
			except Exception as e:
				print("Error parsing job:", e)
	old_job = last_job
	return jobs

# --- Main scraping loop ---
def main():
	global jobset
	while True:
		try:
			if len(jobset) >= 100:
				jobset.clear()
			response = scraper.get(url)
			if response.status_code in ["403","429","400"]:
				run_warp()
				response = scraper.get(url)
			soup = BeautifulSoup(response.text, "html.parser")
			data = scrapy(soup)
			telegram(data)
		except Exception as e:
			print("Main loop error:", e)
		time.sleep(2)

# --- Entry Point ---
if __name__ == "__main__":
	load_descriptions()
	last()

	t1 = threading.Thread(target=main)
	t2 = threading.Thread(target=handle_callback)

	t1.start()
	t2.start()

	t1.join()
	t2.join()
