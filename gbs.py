import googlemaps
import pandas as pd
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import re

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Rate limiting parameters
RATE_LIMIT = 10  # requests per second
RATE_LIMIT_PERIOD = 1  # second

class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, f):
        def wrapped(*args, **kwargs):
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            self.calls.append(time.time())
            return f(*args, **kwargs)
        return wrapped

@RateLimiter(RATE_LIMIT, RATE_LIMIT_PERIOD)
def rate_limited_api_call(func, *args, **kwargs):
    return func(*args, **kwargs)

def extract_email_from_website(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_regex, soup.get_text())
        return emails[0] if emails else None
    except Exception as e:
        logger.error(f"Error extracting email from {url}: {e}")
        return None

def get_place_details(gmaps, place_id):
    details = rate_limited_api_call(gmaps.place, place_id=place_id)
    info = details['result']
    email = None
    website = info.get('website')
    if website:
        logger.info(f"Attempting to extract email from website: {website}")
        email = extract_email_from_website(website)
        if email:
            logger.info(f"Email extracted: {email}")
        else:
            logger.info("No email found on the website")
    
    return {
        'Name': info.get('name'),
        'Address': info.get('formatted_address'),
        'Phone': info.get('formatted_phone_number'),
        'Website': website,
        'Email': email,
        'Rating': info.get('rating'),
        'Reviews': info.get('user_ratings_total'),
        'Types': ', '.join(info.get('types', []))
    }

def get_location_coordinates(gmaps, location):
    logger.debug(f"Attempting to get coordinates for location: {location}")
    if isinstance(location, tuple) and len(location) == 2:
        logger.debug(f"Location is already in coordinate form: {location}")
        return location
    else:
        try:
            geocode_result = rate_limited_api_call(gmaps.geocode, location)
            if geocode_result:
                lat = geocode_result[0]['geometry']['location']['lat']
                lng = geocode_result[0]['geometry']['location']['lng']
                logger.debug(f"Geocoded {location} to coordinates: ({lat}, {lng})")
                return (lat, lng)
            else:
                raise ValueError(f"Unable to geocode location: {location}")
        except Exception as e:
            logger.error(f"Error geocoding location {location}: {e}")
            raise

def get_google_maps_data(api_key, location, query, num_results=100, radius=50000):
    gmaps = googlemaps.Client(key=api_key)
    
    logger.info(f"Fetching data for query: {query} in location: {location}")
    try:
        location_coords = get_location_coordinates(gmaps, location)
    except Exception as e:
        logger.error(f"Failed to get coordinates for location {location}: {e}")
        return []
    
    results = []
    next_page_token = None

    while len(results) < num_results:
        try:
            logger.debug(f"Searching for places. Current results: {len(results)}, Target: {num_results}")
            if next_page_token:
                time.sleep(2)  # Delay to respect API rate limits
                places = rate_limited_api_call(gmaps.places, query=query, location=location_coords, radius=radius, page_token=next_page_token)
            else:
                places = rate_limited_api_call(gmaps.places, query=query, location=location_coords, radius=radius)
            
            results.extend(places['results'])
            next_page_token = places.get('next_page_token')
            
            logger.info(f"Fetched {len(results)} results so far")
            
            if not next_page_token:
                logger.debug("No more pages available")
                break
        except Exception as e:
            logger.error(f"Error fetching places: {e}")
            break

    results = results[:num_results]
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_place = {executor.submit(get_place_details, gmaps, place['place_id']): place for place in results}
        data = []
        for future in as_completed(future_to_place):
            try:
                data.append(future.result())
            except Exception as e:
                logger.error(f"Error fetching place details: {e}")
    
    logger.info(f"Successfully fetched details for {len(data)} places")
    return data

def save_to_file(data, output_file, output_csv=True, output_json=True):
    if output_csv:
        csv_file = f"{output_file}.csv"
        pd.DataFrame(data).to_csv(csv_file, index=False)
        logger.info(f"Data saved to CSV: {csv_file}")
    
    if output_json:
        json_file = f"{output_file}.json"
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Data saved to JSON: {json_file}")

def add_to_supabase(data):
    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    table_name = os.getenv("SUPABASE_TABLE_NAME", "google_maps_data")
    
    for item in data:
        try:
            response = supabase.table(table_name).insert(item).execute()
            if response.data:
                logger.info(f"Successfully added item: {item['Name']} to Supabase")
            else:
                logger.error(f"Failed to add item: {item['Name']} to Supabase")
        except Exception as e:
            logger.error(f"Error adding item to Supabase: {e}")

def main():
    # Read configuration from .env file
    config = {
        "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY"),
        "SEARCH_LOCATION": os.getenv("SEARCH_LOCATION"),
        "SEARCH_QUERY": os.getenv("SEARCH_QUERY"),
        "NUM_RESULTS": os.getenv("NUM_RESULTS", "100"),
        "SEARCH_RADIUS": os.getenv("SEARCH_RADIUS", "50000"),
        "OUTPUT_FILE": os.getenv("OUTPUT_FILE", "output"),
        "OUTPUT_CSV": os.getenv("OUTPUT_CSV", "true").lower() == "true",
        "OUTPUT_JSON": os.getenv("OUTPUT_JSON", "true").lower() == "true",
        "USE_SUPABASE": os.getenv("USE_SUPABASE", "false").lower() == "true"
    }

    # Check for missing required configuration
    missing_config = [key for key, value in config.items() if value is None]
    
    if missing_config:
        logger.error("Missing required configuration. Please check your .env file.")
        for item in missing_config:
            logger.error(f"Missing configuration: {item}")
        return

    # Convert types and set defaults
    try:
        config["NUM_RESULTS"] = int(config["NUM_RESULTS"])
        config["SEARCH_RADIUS"] = int(config["SEARCH_RADIUS"])
    except ValueError as e:
        logger.error(f"Error in configuration values: {e}")
        return

    # Log the configuration (excluding the API key for security)
    logger.info("Current configuration:")
    for key, value in config.items():
        if key != "GOOGLE_MAPS_API_KEY":
            logger.info(f"{key}: {value}")

    # Debug log for location
    logger.debug(f"Search location from config: {config['SEARCH_LOCATION']}")

    data = get_google_maps_data(
        config["GOOGLE_MAPS_API_KEY"],
        config["SEARCH_LOCATION"],
        config["SEARCH_QUERY"],
        config["NUM_RESULTS"],
        config["SEARCH_RADIUS"]
    )
    
    if not data:
        logger.error("No data retrieved. Check the logs for errors.")
        return

    save_to_file(data, config["OUTPUT_FILE"], config["OUTPUT_CSV"], config["OUTPUT_JSON"])
    
    if config["USE_SUPABASE"]:
        if not all([os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"), os.getenv("SUPABASE_TABLE_NAME")]):
            logger.error("Supabase is enabled but missing required configuration. Please check your .env file for SUPABASE_URL, SUPABASE_KEY, and SUPABASE_TABLE_NAME.")
        else:
            add_to_supabase(data)

if __name__ == "__main__":
    main()