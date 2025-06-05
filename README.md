# LinkedIn Employee Scraper & Referral Bot

This project automates the process of scraping LinkedIn employee profiles for specific job postings and sending connection requests with a referral message.

## Features

- Scrapes employee profiles from LinkedIn job postings.
- Sends personalized connection requests with a referral message.
- Keeps track of already contacted profiles to avoid duplicates.
- Supports dry-run mode for testing.

## Setup

### 1. Clone the repository

```sh
git clone <your-repo-url>
cd Job_Referal_Bot
```

### 2. Create and activate a virtual environment

**Windows:**
```sh
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```sh
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```sh
pip install -r requirements.txt
```

### 4. Download ChromeDriver

- Download the appropriate version of [ChromeDriver](https://chromedriver.chromium.org/downloads) for your Chrome browser.
- Place `chromedriver.exe` in the project directory.

### 5. Prepare input files

- Add job links (one per line) to `job_links.txt`.

## Usage

### Scrape and send connection requests

```sh
python linkedin_employee_scraper.py
```

### Dry-run (scrape only, do not send messages)

```sh
python linkedin_employee_scraper.py --dry-run
```

## Output Files

- `linkedin_employees.csv`: Scraped employee profiles.
- `sent_log.csv`: Profiles already contacted.
- `failed_jobs.txt`: Job links where scraping failed.

## Notes

- You may need to log in manually if auto-login fails.
- Update your resume link and message template in `linkedin_employee_scraper.py` as needed.
- Use responsibly and in accordance with LinkedIn's terms of service.
