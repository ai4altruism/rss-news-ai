# src/email_reporter.py

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

def generate_email_html(summary_data):
    """
    Generate HTML content for the email.
    
    Parameters:
        summary_data (dict): The grouped and summarized articles.
        
    Returns:
        str: HTML content for the email.
    """
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-bottom: 1px solid #ddd; }}
            .topic {{ margin: 25px 0; padding: 15px; border-radius: 5px; background-color: #fff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .topic-title {{ color: #3366cc; margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            .summary {{ margin-bottom: 15px; }}
            .articles {{ list-style-type: none; padding-left: 0; }}
            .article {{ margin: 8px 0; }}
            .article a {{ color: #0066cc; text-decoration: none; }}
            .article a:hover {{ text-decoration: underline; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #777; text-align: center; border-top: 1px solid #ddd; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>RSS AI News Monitor - Summary</h1>
            <p>Generated on {current_date}</p>
        </div>
    """
    
    for topic_group in summary_data.get("topics", []):
        topic_name = topic_group.get("topic", "Uncategorized")
        summary = topic_group.get("summary", "No summary available.")
        articles = topic_group.get("articles", [])
        
        html += f"""
        <div class="topic">
            <h2 class="topic-title">{topic_name}</h2>
            <div class="summary">
                <p>{summary}</p>
            </div>
        """
        
        if articles:
            html += '<ul class="articles">'
            for article in articles:
                title = article.get("title", "Untitled")
                link = article.get("link", "#")
                html += f'<li class="article"><a href="{link}" target="_blank">{title}</a></li>'
            html += '</ul>'
        
        html += '</div>'
    
    html += """
        <div class="footer">
            <p>This is an automated email from RSS AI News Monitor</p>
        </div>
    </body>
    </html>
    """
    
    return html

def send_email(summary_data, smtp_config, recipients):
    """
    Send the summary as an email.
    
    Parameters:
        summary_data (dict): The grouped and summarized articles.
        smtp_config (dict): SMTP configuration (server, port, username, password).
        recipients (list): List of email recipients.
        
    Returns:
        bool: Whether the email was sent successfully.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Generative AI News Monitor - Summary ({current_date})"
    msg['From'] = smtp_config.get('username')
    msg['To'] = ", ".join(recipients)
    
    # Generate plain text version
    plain_text = f"RSS AI News Monitor - News Summary ({current_date})\n\n"
    for topic_group in summary_data.get("topics", []):
        topic_name = topic_group.get("topic", "Uncategorized")
        summary = topic_group.get("summary", "No summary available.")
        articles = topic_group.get("articles", [])
        
        plain_text += f"{topic_name}\n"
        plain_text += f"{'-' * len(topic_name)}\n"
        plain_text += f"{summary}\n\n"
        
        if articles:
            plain_text += "Articles:\n"
            for article in articles:
                title = article.get("title", "Untitled")
                link = article.get("link", "#")
                plain_text += f"- {title}: {link}\n"
        
        plain_text += "\n\n"
    
    # Generate HTML version
    html_content = generate_email_html(summary_data)
    
    # Attach both versions
    part1 = MIMEText(plain_text, 'plain')
    part2 = MIMEText(html_content, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        # Connect to SMTP server
        if smtp_config.get('use_tls', True):
            server = smtplib.SMTP(smtp_config.get('server'), smtp_config.get('port', 587))
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_config.get('server'), smtp_config.get('port', 465))
        
        server.login(smtp_config.get('username'), smtp_config.get('password'))
        server.sendmail(smtp_config.get('username'), recipients, msg.as_string())
        server.quit()
        
        logging.info(f"Email sent successfully to {len(recipients)} recipients.")
        return True
    
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return False