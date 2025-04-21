from flask import Flask, render_template, request, jsonify, send_file
from facebook_ad_scraper import FacebookAdScraper
import json
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import csv
from io import StringIO

app = Flask(__name__)

# Store the scraper instance
scraper = None
last_search_time = None

def initialize_scraper_if_needed(search_term=None):
    """Initialize the scraper if it doesn't exist or if it's been idle too long."""
    global scraper, last_search_time
    current_time = datetime.now()
    
    # If scraper exists, check if it's been idle too long (e.g., 30 minutes)
    if scraper and last_search_time:
        idle_time = (current_time - last_search_time).total_seconds() / 60  # minutes
        if idle_time > 30:  # Reset after 30 minutes of inactivity
            try:
                scraper.close()
            except:
                pass
            scraper = None
    
    # Initialize scraper if needed
    if not scraper:
        try:
            # Create the Ad Library URL with the search term
            if search_term:
                base_url = "https://www.facebook.com/ads/library/"
                params = {
                    "active_status": "active",
                    "ad_type": "all",
                    "country": "ALL",
                    "is_targeted_country": "false",
                    "media_type": "all",
                    "q": search_term,
                    "search_type": "keyword_unordered"
                }
                # Build the query string
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                url = f"{base_url}?{query_string}"
                print(f"Starting with URL: {url}")
                
                # Initialize scraper and navigate to the URL
                scraper = FacebookAdScraper(quiet_mode=False)
                scraper.driver.get(url)
            else:
                scraper = FacebookAdScraper(quiet_mode=False)
        except Exception as e:
            print(f"Error initializing scraper: {str(e)}")
            raise
    
    # Update last search time
    last_search_time = current_time

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Handle search requests."""
    try:
        data = request.get_json()
        search_term = data.get('search_term')
        url_patterns = data.get('url_patterns', [])
        
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400
            
        # Initialize scraper if needed
        initialize_scraper_if_needed(search_term)
        
        # Perform the search with URL patterns
        results = scraper.search_ads(search_term, url_patterns)
        
        # Process results
        matches = []
        flagged_ads = []
        
        for ad in results:
            ad_info = {
                'ad_text': ad.get('ad_text', ''),
                'library_id': ad.get('library_id', ''),
                'library_link': f"https://www.facebook.com/ads/library/?id={ad.get('library_id', '')}" if ad.get('library_id') else None,
                'image_url': ad.get('image_url'),
                'original_url': ad.get('original_urls', [''])[0] if ad.get('original_urls') else None,
                'final_url': ad.get('urls', [''])[0] if ad.get('urls') else None,
                'ad_page_url': ad.get('ad_page_url')
            }
            
            # Check if this is a flagged ad
            if 'matched_words' in ad:
                ad_info['matched_words'] = ad['matched_words']
                flagged_ads.append(ad_info)
            else:
                matches.append(ad_info)
        
        return jsonify({
            'matches': matches,
            'flagged_ads': flagged_ads
        })
        
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        matches = data.get('matches', [])
        format_type = data.get('format', 'json')  # Default to JSON if not specified
        
        if not matches:
            return jsonify({'error': 'No data to download'}), 400
            
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'csv':
            # Create CSV in memory
            si = StringIO()
            writer = csv.writer(si)
            
            # Write headers
            headers = ['Ad Text', 'Library ID', 'Library Link', 'Ad Page URL', 'Original URL', 'Final URL', 'Image URL']
            writer.writerow(headers)
            
            # Write data
            for match in matches:
                writer.writerow([
                    match.get('ad_text', ''),
                    match.get('library_id', ''),
                    match.get('library_link', ''),
                    match.get('ad_page_url', ''),
                    match.get('original_url', ''),
                    match.get('final_url', ''),
                    match.get('image_url', '')
                ])
            
            # Prepare the response
            output = si.getvalue()
            si.close()
            
            return send_file(
                StringIO(output),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'facebook_ad_matches_{timestamp}.csv'
            )
        else:
            # JSON download (existing functionality)
            filename = f'facebook_ad_matches_{timestamp}.json'
            
            # Save to a temporary file
            with open(filename, 'w') as f:
                json.dump(matches, f, indent=2)
                
            # Send the file
            return send_file(
                filename,
                mimetype='application/json',
                as_attachment=True,
                download_name=filename
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up the temporary file if it exists (JSON case only)
        if format_type == 'json' and os.path.exists(filename):
            os.remove(filename)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    global scraper, last_search_time
    try:
        if scraper:
            scraper.close()
            scraper = None
            last_search_time = None
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Cleanup when the Flask app shuts down
@app.teardown_appcontext
def shutdown_cleanup(exception=None):
    global scraper
    if scraper:
        try:
            scraper.close()
        except:
            pass
        scraper = None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False) 