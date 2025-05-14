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
from job_fetcher import get_jobs
load_dotenv()

scraper = cloudscraper.create_scraper()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

url = "https://www.upwork.com/nx/search/jobs/?proposals=0-4,5-9,10-14,15-19&q=%28automation%20OR%20python%20OR%20automate%20OR%20bot%20OR%20spreadsheet%20OR%20scrap%20OR%20api%29&page=1&per_page=20"
DESCRIPTIONS_FILE = "descriptions.json"

job_descriptions = {}
jobset = set()

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

def save_descriptions():
    if len(job_descriptions) >= 5000:
        print("Job descriptions limit reached, clearing the file.")
        job_descriptions.clear()
        
    with open(DESCRIPTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(job_descriptions, f, ensure_ascii=False, indent=2)


def run_warp():
	subprocess.run(["warp-cli", "disconnect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	subprocess.run(["warp-cli", "connect"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)   

	while True:
		result = subprocess.run(["warp-cli", "status"], capture_output=True, text=True)
		if "Connected" in result.stdout:
			break
		time.sleep(1)
run_warp()

def handle_callback():
    global TOKEN
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    processed = set()
	
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
				f"✍️ <b>Proposal</b>: {job[7].strip()}\n"
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

def last():
	global old_job
	try:
		run_warp()
		jobs = get_jobs()
		old_job = jobs[0].get('title')
		print("Initial last job:", old_job)
	except Exception as e:
		run_warp()
		print(f"Error occurred: {e}")

def scrapy():
	global old_job, jobset
	jobs = {}
	job_elements = get_jobs()
	last_job = job_elements[0].get('title') if job_elements else old_job
	for x in job_elements:
		price_text = x.get('type')
		experience_text = "Experience Level"
		experience = x.get('experience_level')
		price = x.get('price')
		title = x.get('title')
		link = x.get('link')
		clean_text = x.get('description')
		proposal = 'Less than 5'
		try:
			if title == old_job:
				old_job = last_job
				time.sleep(120)
				break
			if link in jobset:
				continue
			jobset.add(link)
			jobs[title] = clean_text, link, proposal, price_text, price, experience_text, experience, proposal
		except Exception as e:
			print("Error parsing job:", e)
	old_job = last_job
	return jobs

def main():
	global jobset
	while True:
		try:
			if len(jobset) >= 100:
				jobset.clear()
			data = scrapy()
			telegram(data)
		except Exception as e:
			print("Main loop error:", e)
		time.sleep(2)

if __name__ == "__main__":
	load_descriptions()
	last()

	t1 = threading.Thread(target=main)
	t2 = threading.Thread(target=handle_callback)

	t1.start()
	t2.start()

	t1.join()
	t2.join()
