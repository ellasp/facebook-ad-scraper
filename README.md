# Facebook Ad Scraper

A Streamlit web application for searching and analyzing Facebook ads with custom URL matching capabilities.

## Features

- Search Facebook Ad Library with custom terms
- Match ads against specific URL patterns
- Flag ads containing watch words
- Download results in CSV or JSON format
- Multi-user support with secure authentication
- Cloud-ready deployment

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run streamlit_app.py
```

## Cloud Deployment

### Deploy to Streamlit Cloud

1. Push your code to a GitHub repository

2. Visit [share.streamlit.io](https://share.streamlit.io)

3. Sign in with GitHub

4. Click "New app" and select your repository

5. Configure the deployment:
   - Main file path: `streamlit_app.py`
   - Python version: 3.9+

### Environment Variables

The following environment variables should be set in your Streamlit Cloud deployment:

- `STREAMLIT_SERVER_PORT`: Port for the Streamlit server (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Server address (default: 0.0.0.0)

### Security Notes

- User data is stored in JSON files in the `users` directory
- Passwords are hashed using SHA-256
- Each user gets their own isolated session
- Selenium runs in headless mode with security options

## Usage

1. Register for an account or log in
2. Enter search terms and URL patterns
3. Configure watch words in the sidebar
4. Run searches and analyze results
5. Download results in preferred format

## Maintenance

- Monitor the `users` directory size
- Regularly backup user data
- Update dependencies as needed
- Check Streamlit Cloud logs for issues

## Troubleshooting

If you encounter issues:

1. Check internet connection
2. Verify Facebook Ad Library access
3. Clear browser cache
4. Reset the scraper using the sidebar button
5. Check Streamlit Cloud logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details 