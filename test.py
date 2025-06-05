from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, csv, os, tempfile

# === CONFIG ===
CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver.exe")
SEARCH_URL = "https://www.linkedin.com/search/results/people/?keywords=Bottomline%20Bengaluru"  # update this

# === Setup Chrome ===
temp_profile = tempfile.mkdtemp()
options = webdriver.ChromeOptions()
options.add_argument(f"user-data-dir={temp_profile}")
options.add_argument("--start-maximized")

service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

# === Step 1: Login ===
driver.get("https://www.linkedin.com/login")
input("🔐 Log in manually, then press ENTER...")

# === Step 2: Visit People Search ===
driver.get(SEARCH_URL)
time.sleep(5)

# === Step 3: Scrape People ===
cards = driver.find_elements(By.CLASS_NAME, "reusable-search__result-container")
print(f"🔎 Found {len(cards)} profiles")

with open("debug_employees.csv", "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Name", "Profile URL"])
    
    for card in cards:
        try:
            profile_anchor = card.find_element(By.CSS_SELECTOR, "a[href*='/in/']")
            profile_url = profile_anchor.get_attribute("href").split("?")[0]

            name_elem = card.find_element(By.CSS_SELECTOR, "span[aria-hidden='true']")
            name = name_elem.text.strip()

            print(f"👤 {name} — {profile_url}")
            writer.writerow([name, profile_url])
        except Exception as e:
            print(f"⚠️ Skipped one card due to: {e}")
            continue

driver.quit()
print("✅ Done. Output saved to debug_employees.csv")
