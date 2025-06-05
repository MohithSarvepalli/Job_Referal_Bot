import os
import csv
import time
import tempfile
import argparse
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup

# === ARGUMENTS ===
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="Only scrape, do not send messages")
args = parser.parse_args()

# === CONFIGURATION ===
CHROMEDRIVER_PATH = os.path.join(os.getcwd(), "chromedriver.exe") #Remove .exe if you are running on MAC/Linux
RESUME_LINK = "https://yourdomain.com/resume.pdf"  # Replace with your actual resume URL

MESSAGE_TEMPLATE = """Hi {name}, hope you’re well. If possible, could you kindly refer me for this role at {company}? {job_link}
I’d truly appreciate your help!
"""

# === LOAD JOB LINKS ===
with open("job_links.txt", "r") as f:
    job_links = [line.strip() for line in f if line.strip()]

# === SETUP SELENIUM ===
temp_profile = tempfile.mkdtemp()
options = webdriver.ChromeOptions()
options.add_argument(f"user-data-dir={temp_profile}")
options.add_argument("--start-maximized")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

# === STEP 1: LOGIN ===
driver.get("https://www.linkedin.com/login")

try:
    username_field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
    password_field = driver.find_element(By.ID, "password")

    username_field.clear()
    username_field.send_keys("Your email")

    password_field.clear()
    password_field.send_keys("Passs")

    sign_in_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
    sign_in_btn.click()
    print("🔐 Attempting auto-login...")

    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "global-nav-search")))
    print("✅ Logged in successfully.")
except Exception as e:
    print(f"⚠️ Auto-login failed: {e}")
    input("➡️ Log in manually, then press ENTER to continue...")

# === STEP 2: SCRAPE & SAVE TO CSV ===
csv_filename = "linkedin_employees.csv"
sent_log_file = "sent_log.csv"
failed_jobs_file = "failed_jobs.txt"

sent_profiles = set()
if os.path.exists(sent_log_file):
    with open(sent_log_file, "r", encoding="utf-8") as s:
        reader = csv.reader(s)
        sent_profiles = set(row[0] for row in reader)

# Commented out scraping section, only sending connection requests from CSV
with open(csv_filename, "w", newline='', encoding='utf-8') as csv_file, open(failed_jobs_file, "w") as failed_file:
    writer = csv.writer(csv_file)
    writer.writerow(["Profile URL", "Company", "Location", "Job Link"])

    for job_link in job_links:
        driver.get(job_link)
        time.sleep(5)

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

            try:
                company_elem = driver.find_element(By.XPATH, "/html/body/div[6]/div[3]/div[2]/div/div/main/div[2]/div[1]/div/div[1]/div/div/div/div[1]/div[1]/div/a")
                company = company_elem.text
                # Try to extract company ID from href
                company_href = company_elem.get_attribute("href")
                company_id_match = re.search(r"/company/(\d+)", company_href or "")
                company_id = company_id_match.group(1) if company_id_match else None
            except:
                company = "Company not found"
                company_id = None

            try:
                location = driver.find_element(By.XPATH, "/html/body/div[6]/div[3]/div[2]/div/div/main/div[2]/div[1]/div/div[1]/div/div/div/div[3]/div/span/span[1]").text
            except:
                location = "Location not found"

            print(f"✅ Job Found: {company} – {location}")

        except Exception as e:
            print(f"❌ Failed to extract job info: {e}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"job_fail_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            print(f"🖼️ Screenshot saved: {screenshot_path}")
            failed_file.write(job_link + "\n")
            continue

        search_query = f"{company} {location}"
        # Step 1: Search without current company filter
        base_search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_query}&origin=JOB_PAGE_JOB_VIEW"
        driver.get(base_search_url)
        time.sleep(5)
        screenshot_path = f"job_{company}_nofilter.png"
        driver.save_screenshot(screenshot_path)

        # Step 2: Parse page to find company ID for current company filter
        soup = BeautifulSoup(driver.page_source, "html.parser")
        company_id = None
        # Try to find the input for current company filter matching the company name
        for li in soup.select('li.search-reusables__collection-values-item'):
            label = li.find('label', class_='search-reusables__value-label')
            if label and company.lower() in label.text.strip().lower():
                input_elem = li.find('input', {'name': 'current-company-filter-value'})
                if input_elem and input_elem.has_attr('value'):
                    company_id = input_elem['value']
                    break

        # Step 3: If found, reload with current company filter
        if company_id:
            filtered_search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_query}&currentCompany=[%22{company_id}%22]&origin=JOB_PAGE_JOB_VIEW"
            driver.get(filtered_search_url)
            time.sleep(5)
            screenshot_path = f"job_{company}_filtered.png"
            driver.save_screenshot(screenshot_path)
        else:
            print(f"⚠️ Could not find company ID for '{company}', continuing without current company filter.")

        # Scroll the page to load more results and collect all profile links
        soup = None
        all_profile_hrefs = set()
        scroll_attempts = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
        while scroll_attempts < 10:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            for a in soup.find_all("a", href=True):
                if "/in/" in a["href"]:
                    match = re.search(r"/in/([^/?#]+)", a["href"])
                    if match:
                        username = match.group(1)
                        if not username.lower().startswith("acoa"):
                            all_profile_hrefs.add(a["href"])
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1

        print(f"==== Found {len(all_profile_hrefs)} unique /in/ profile links after scrolling ====")
        for href in all_profile_hrefs:
            print(href)
        print("======================================")

        print("➡️ Scraping people from search results...")
        people = set()
        # Only visit and save the filtered, deduplicated valid_profile_hrefs
        for raw_href in all_profile_hrefs:
            try:
                # Visit the raw href in a new tab
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[-1])
                driver.get(raw_href)
                time.sleep(3)  # Wait for profile to load

                canonical_url = driver.current_url.split("?")[0].split("#")[0]
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

                if canonical_url in people:
                    continue

                people.add(canonical_url)
                # Add a space after the comma before company name
                writer.writerow([canonical_url, f"{company}", location, job_link])
                print(f"📥 Saved: {canonical_url}")
                if len(people) >= 20:
                    break
            except Exception:
                # Always return to search tab if error
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                continue

        if len(people) == 0:
            print("⚠️ No employee profiles found. Consider checking the search URL or page structure.")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"people_search_fail_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            print(f"🖼️ People search screenshot saved: {screenshot_path}")

print(f"\n📄 Using existing {csv_filename} for sending connection requests.")
if args.dry_run:
    print("🛑 Dry run mode active. No messages will be sent.")
    driver.quit()
    exit()

input("⏭️ Press ENTER to begin sending connection requests...\n")

with open(csv_filename, "r", encoding='utf-8') as f, open(sent_log_file, "a", newline='', encoding='utf-8') as sent_log:
    reader = csv.DictReader(f)
    sent_writer = csv.writer(sent_log)

    for row in reader:
        profile_url = row["Profile URL"]
        company = row["Company"]
        job_link = row["Job Link"]

        if profile_url in sent_profiles:
            print(f"🔁 Already contacted: {profile_url}")
            continue

        driver.get(profile_url)
        time.sleep(10)

        try:
            connect_btn = None
            connect_under_more = False
            # Try to find Connect button by aria-label (Invite ... to connect)
            try:
                connect_btn = driver.find_element(By.XPATH, "//button[contains(translate(@aria-label, 'CONNECT', 'connect'), 'connect') and contains(translate(@aria-label, 'INVITE', 'invite'), 'invite')]")
                # Check if this button is inside a <li> (dropdown menu)
                try:
                    parent_li = connect_btn.find_element(By.XPATH, "./ancestor::li[1]")
                    if parent_li:
                        connect_under_more = True
                except Exception:
                    connect_under_more = False
                print(f"✅ Connect button found by aria-label for {profile_url} (under More: {connect_under_more})")
            except NoSuchElementException:
                # Fallback: try visible text "Connect" outside More
                try:
                    connect_btn = driver.find_element(By.XPATH, "//button[.//span[normalize-space(text())='Connect']]")
                    try:
                        parent_li = connect_btn.find_element(By.XPATH, "./ancestor::li[1]")
                        if parent_li:
                            connect_under_more = True
                    except Exception:
                        connect_under_more = False
                    print(f"✅ Connect button found by span for {profile_url} (under More: {connect_under_more})")
                except NoSuchElementException:
                    # If not found, try clicking More and then look for Connect in dropdown
                    try:
                        more_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'More actions') or .//span[text()='More']]")
                        driver.execute_script("arguments[0].scrollIntoView(true);", more_btn)
                        time.sleep(1)
                        more_btn.click()
                        print(f"✅ More button found and clicked for {profile_url}")
                        time.sleep(2)
                        try:
                            connect_btn = driver.find_element(By.XPATH, "//div[contains(translate(@aria-label, 'CONNECT', 'connect'), 'connect') and contains(translate(@aria-label, 'INVITE', 'invite'), 'invite')]")
                            connect_under_more = True
                            print(f"✅ Connect button found in dropdown by aria-label for {profile_url} (under More: True)")
                        except NoSuchElementException:
                            try:
                                connect_btn = driver.find_element(By.XPATH, "//div[.//span[normalize-space(text())='Connect']]")
                                connect_under_more = True
                                print(f"✅ Connect button found in dropdown by span for {profile_url} (under More: True)")
                            except NoSuchElementException:
                                print(f"⚠️ No Connect button found for {profile_url}, skipping.")
                                continue
                    except NoSuchElementException:
                        print(f"⚠️ No Connect button found for {profile_url}, skipping.")
                        continue

            # If connect is under more, ensure More is clicked before clicking Connect
            if connect_under_more:
                try:
                    # Try JS click directly for More button (handles "element not interactable")
                    more_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'More actions') or .//span[text()='More']]")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", more_btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", more_btn)
                    print(f"🔵 Explicitly JS-clicked More for {profile_url} before Connect (under More: True)")
                    time.sleep(2)
                    # After clicking More, explicitly click the Connect span inside the dropdown
                    try:
                        connect_span = driver.find_element(By.XPATH, "//span[contains(@class, 'flex-1') and text()='Connect']")
                        driver.execute_script("arguments[0].click();", connect_span)
                        print(f"✅ Connect span clicked inside More for {profile_url}")
                        time.sleep(2)
                    except Exception as e:
                        print(f"⚠️ Could not click Connect span inside More for {profile_url}: {e}")
                        continue
                except Exception as e:
                    print(f"⚠️ Could not click More for {profile_url}: {e}")
                    continue
            else:
                # Always use JS click for Connect button (covers JS/react buttons)
                try:
                    driver.execute_script("arguments[0].click();", connect_btn)
                    print(f"✅ Connect button JS-clicked for {profile_url} (under More: {connect_under_more})")
                    time.sleep(2)
                except Exception as e:
                    print(f"⚠️ Connect button JS click failed for {profile_url}: {e}")
                    continue

            # Wait for the Add a note button to appear
            try:
                add_note_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Add a note']"))
                )
                add_note_btn.click()
                time.sleep(1)
            except Exception:
                print(f"⚠️ 'Add a note' button not found for {profile_url}, skipping.")
                continue

            msg_box = driver.find_element(By.ID, "custom-message")
            message = MESSAGE_TEMPLATE.format(
                name="there", company=company, job_link=job_link, resume=RESUME_LINK
            )
            message = message[:200]
            msg_box.send_keys(message)
            time.sleep(2)
            send_btn = driver.find_element(By.XPATH, "//button[@aria-label='Send invitation']")
            send_btn.click()
            print(f"📨 Sent to {profile_url}")
            sent_writer.writerow([profile_url])
        except Exception as e:
            print(f"⚠️ Could not message {profile_url}: {e}")

        time.sleep(2)

driver.quit()
