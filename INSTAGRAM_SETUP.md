# Instagram Authentication Setup

Instagram has strict rate limiting and requires authentication for reliable access. Here are the options:

## Option 1: Cookies (Recommended)

1. **Export cookies from your browser:**
   - Install a browser extension like "Get cookies.txt" 
   - Visit Instagram and log in
   - Export cookies to a file (e.g., `instagram_cookies.txt`)

2. **Set environment variable:**
   ```bash
   export INSTAGRAM_COOKIES_FILE="/path/to/instagram_cookies.txt"
   ```

## Option 2: Username/Password

1. **Set environment variables:**
   ```bash
   export INSTAGRAM_USERNAME="your-instagram-username"
   export INSTAGRAM_PASSWORD="your-instagram-password"
   ```

## Option 3: Manual Cookie Export

1. **Get cookies manually:**
   - Open Developer Tools in your browser (F12)
   - Go to Instagram and log in
   - Go to Application/Storage tab → Cookies → https://www.instagram.com
   - Copy relevant cookies

2. **Create cookies.txt file:**
   ```
   # Netscape HTTP Cookie File
   .instagram.com	TRUE	/	FALSE	1234567890	sessionid	YOUR_SESSION_ID
   .instagram.com	TRUE	/	FALSE	1234567890	csrftoken	YOUR_CSRF_TOKEN
   ```

## Troubleshooting

- **Rate limiting:** Instagram aggressively rate limits requests
- **Login required:** Some content requires authentication
- **Cookies expire:** You may need to refresh cookies periodically
- **2FA:** If you have 2FA enabled, cookies method is preferred

## Testing

Test your setup with:
```bash
export INSTAGRAM_COOKIES_FILE="/path/to/cookies.txt"
python main.py
```

Then try accessing an Instagram URL through the API.