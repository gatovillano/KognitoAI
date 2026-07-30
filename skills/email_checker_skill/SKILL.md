---
name: email-checker
description: Use when checking, reading, or fetching emails from accounts (Gmail,
  Outlook, Yahoo) using secure credential management.
---

# Email Checker Skill

This skill allows you to check emails from various providers (Gmail, Outlook, Yahoo) with secure credential handling.

## Features
- Secure credential handling via environment variables
- Support for Gmail, Outlook, Yahoo, and custom IMAP servers
- Option to fetch email bodies
- Option to mark emails as read
- Proper connection cleanup and error handling

## Setup Instructions

### 1. Set Environment Variables (SECURE METHOD)
Never hardcode credentials in your code or scripts. Instead, set these environment variables:

#### For Gmail (Recommended - App Password)
```bash
export EMAIL_ADDRESS="your.email@gmail.com"
export EMAIL_APP_PASSWORD="your-app-password-here"  # Generate from Google Account > Security > App Passwords
```

#### For Outlook/Hotmail
```bash
export EMAIL_ADDRESS="your.email@outlook.com"
export EMAIL_APP_PASSWORD="your-app-password-here"  # Generate from Microsoft Account > Security > App Passwords
```

#### For Yahoo
```bash
export EMAIL_ADDRESS="your.email@yahoo.com"
export EMAIL_APP_PASSWORD="your-app-password-here"  # Generate from Yahoo Account > Security > App Passwords
```

#### For Custom IMAP Server
```bash
export EMAIL_ADDRESS="your.email@domain.com"
export EMAIL_APP_PASSWORD="your-password-here"
export EMAIL_IMAP_SERVER="imap.yourdomain.com"  # Your custom IMAP server
```

### 2. Security Best Practices
- **Use App Passwords**: For Gmail, Outlook, and Yahoo, always use app-specific passwords instead of your main account password when 2FA is enabled
- **Environment Variables**: Store credentials in environment variables, never in code
- **Least Privilege**: Consider creating a dedicated email account for this skill if needed
- **Network Security**: The skill uses IMAP over SSL (port 993) for secure connections
- **No Logging**: Credentials are never logged or exposed in outputs

## Usage Examples

### Check Recent Gmail Inbox
```
LLAMADA_A_HERRAMIENTA: email_checker
{"provider": "gmail", "limit": 5}
```

### Check Outlook Sent Folder
```
LLAMADA_A_HERRAMIENTA: email_checker
{"provider": "outlook", "folder": "sent", "limit": 10}
```

### Check Yahoo Email with Body
```
LLAMADA_A_HERRAMIENTA: email_checker
{"provider": "yahoo", "limit": 3, "include_body": true}
```

### Mark Emails as Read After Fetching
```
LLAMADA_A_HERRAMIENTA: email_checker
{"provider": "gmail", "limit": 5, "mark_as_read": true}
```

## Supported Providers
- `gmail` - Gmail/Google Workspace
- `outlook` - Outlook/Hotmail/Office 365
- `yahoo` - Yahoo Mail
- `custom` - Any IMAP server (requires EMAIL_IMAP_SERVER env var)

## Parameters
- `provider` (required): Email provider (gmail, outlook, yahoo, custom)
- `folder` (optional): Folder to check (default: "inbox")
- `limit` (optional): Number of emails to fetch (default: 10)
- `mark_as_read` (optional): Whether to mark emails as read (default: false)
- `include_body` (optional): Whether to include email body (default: false)

## Error Handling
The skill provides meaningful error messages for:
- Missing environment variables
- Connection failures
- Authentication errors
- Folder selection issues
- Search failures

## Notes
- For providers requiring OAuth2 (more secure but complex), this skill uses app passwords as a balanced approach between security and usability
- Always enable 2FA on your email account and use app passwords
- The skill limits email body output to prevent overwhelming responses
- Connections are properly closed after use to prevent resource leaks