# Google Business Scraper (GBS)

## Description

Google Business Scraper (GBS) is a Python-based tool designed to extract business information from Google Maps. It allows users to search for businesses based on location and query, and retrieve details such as name, address, phone number, website, rating, and more.

## Features

- Search businesses on Google Maps based on location and query
- Retrieve detailed information for each business
- Rate limiting to respect Google Maps API usage limits
- Concurrent fetching of place details for improved performance
- Flexible output options (CSV and/or JSON)
- Optional integration with Supabase for data storage
- Configurable via environment variables

## Prerequisites

- Python 3.7+
- Google Maps API key
- Supabase account (optional, for database storage)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/gbs.git
   cd gbs
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the project root directory with the following content:

```
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
SEARCH_LOCATION="New York, NY"
SEARCH_QUERY="commercial roofing contractors"
NUM_RESULTS=50
SEARCH_RADIUS=30000
OUTPUT_FILE=roofing_data
OUTPUT_CSV=true
OUTPUT_JSON=true
USE_SUPABASE=false
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_TABLE_NAME=your_table_name
```

Adjust the values according to your needs and API credentials.

## Usage

Run the script using:

```
python google_maps_scraper.py
```

The script will fetch data based on your configuration and save it to the specified output file(s).

## Output

Depending on your configuration, the script will generate:

- A CSV file (`<OUTPUT_FILE>.csv`)
- A JSON file (`<OUTPUT_FILE>.json`)

If Supabase integration is enabled, data will also be stored in the specified Supabase table.

## Logging

The script provides detailed logging information, including:

- Configuration details (excluding sensitive information)
- Progress updates during data fetching
- Any errors or issues encountered

Logs are printed to the console and can be redirected to a file if needed.

## Customization

You can modify the `get_place_details` function in the script to retrieve additional or different information for each business.

## Rate Limiting

The script implements rate limiting to avoid exceeding Google Maps API usage limits. You can adjust the `RATE_LIMIT` and `RATE_LIMIT_PERIOD` variables in the script if needed.

## Error Handling

The script includes error handling for common issues such as:

- Missing configuration
- API request failures
- Geocoding errors

Check the logs for detailed error messages if you encounter any issues.

## Contributing

Contributions to improve GBS are welcome. Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. Ensure you comply with Google's Terms of Service and any applicable laws when using this script.
