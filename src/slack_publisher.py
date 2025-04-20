# src/slack_publisher.py

import requests
import logging
import json
from datetime import datetime
import math

# Constants for Slack limitations
MAX_BLOCKS_PER_MESSAGE = 45  # Slack limit is 50, leave buffer
MAX_ARTICLES_PER_TOPIC = 10  # Limit number of articles displayed per topic
MAX_TOPICS_PER_MESSAGE = 5   # Limit number of topics per message

def format_for_slack(summary_data, start_topic=0, end_topic=None):
    """
    Format the summary data into Slack message blocks with limits.
    
    Parameters:
        summary_data (dict): The grouped and summarized articles.
        start_topic (int): Index of the first topic to include
        end_topic (int): Index of the last topic to include (exclusive)
        
    Returns:
        list: Formatted Slack message blocks.
    """
    # Get topics
    topics = summary_data.get("topics", [])
    total_topics = len(topics)
    
    # If end_topic not specified, calculate based on MAX_TOPICS_PER_MESSAGE
    if end_topic is None:
        end_topic = min(start_topic + MAX_TOPICS_PER_MESSAGE, total_topics)
    
    # Create subset of topics for this message
    subset_topics = topics[start_topic:end_topic]
    
    # Create message header
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🤖 Generative AI News | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "emoji": True
            }
        }
    ]
    
    # Add pagination info if splitting into multiple messages
    if total_topics > MAX_TOPICS_PER_MESSAGE:
        current_page = math.ceil(start_topic / MAX_TOPICS_PER_MESSAGE) + 1
        total_pages = math.ceil(total_topics / MAX_TOPICS_PER_MESSAGE)
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Page {current_page} of {total_pages}* | Topics {start_topic+1}-{end_topic} of {total_topics}"
            }
        })
    
    blocks.append({
        "type": "divider"
    })
    
    # Process each topic in this subset
    for topic_group in subset_topics:
        topic_name = topic_group.get("topic", "Uncategorized")
        summary = topic_group.get("summary", "No summary available.")
        articles = topic_group.get("articles", [])
        
        # Add topic header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{topic_name}*"
            }
        })
        
        # Add summary
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary
            }
        })
        
        # Add article links (limited)
        if articles:
            # Limit number of articles displayed
            display_articles = articles[:MAX_ARTICLES_PER_TOPIC]
            total_articles = len(articles)
            
            link_text = "*Articles:*\n"
            for idx, article in enumerate(display_articles, 1):
                title = article.get("title", "Untitled")
                link = article.get("link", "#")
                # Truncate long titles
                if len(title) > 80:
                    title = title[:77] + "..."
                link_text += f"{idx}. <{link}|{title}>\n"
            
            # Add note if some articles were omitted
            if total_articles > MAX_ARTICLES_PER_TOPIC:
                omitted = total_articles - MAX_ARTICLES_PER_TOPIC
                link_text += f"_(+{omitted} more articles not shown)_\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": link_text
                }
            })
        
        blocks.append({
            "type": "divider"
        })
    
    return blocks

def publish_to_slack(summary_data, webhook_url):
    """
    Publish the summary data to a Slack channel using a webhook.
    Handles large datasets by splitting into multiple messages if needed.
    
    Parameters:
        summary_data (dict): The grouped and summarized articles.
        webhook_url (str): The Slack webhook URL.
        
    Returns:
        bool: Whether the message was sent successfully.
    """
    topics = summary_data.get("topics", [])
    total_topics = len(topics)
    
    if not topics:
        logging.info("No topics to publish to Slack.")
        return True
    
    success = True
    
    # If few topics, send as single message
    if total_topics <= MAX_TOPICS_PER_MESSAGE:
        blocks = format_for_slack(summary_data)
        success = send_slack_message(webhook_url, blocks)
    else:
        # Split into multiple messages
        for start_idx in range(0, total_topics, MAX_TOPICS_PER_MESSAGE):
            end_idx = min(start_idx + MAX_TOPICS_PER_MESSAGE, total_topics)
            blocks = format_for_slack(summary_data, start_idx, end_idx)
            
            # Send this batch
            batch_success = send_slack_message(webhook_url, blocks)
            if not batch_success:
                success = False
    
    return success

def send_slack_message(webhook_url, blocks):
    """
    Send a single Slack message with the given blocks.
    
    Parameters:
        webhook_url (str): The Slack webhook URL.
        blocks (list): The blocks to send.
        
    Returns:
        bool: Whether the message was sent successfully.
    """
    try:
        # Ensure we don't exceed Slack's block limit
        if len(blocks) > MAX_BLOCKS_PER_MESSAGE:
            logging.warning(f"Truncating Slack message from {len(blocks)} to {MAX_BLOCKS_PER_MESSAGE} blocks")
            blocks = blocks[:MAX_BLOCKS_PER_MESSAGE-1]
            
            # Add a note that content was truncated
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "⚠️ _Message truncated due to Slack limitations. Please check the web dashboard for complete information._"
                }
            })
        
        payload = {
            "blocks": blocks
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logging.info("Successfully published message to Slack.")
            return True
        else:
            logging.error(f"Failed to publish to Slack. Status: {response.status_code}, Response: {response.text}")
            
            # Debug information for troubleshooting
            logging.debug(f"Message had {len(blocks)} blocks and approximately {len(json.dumps(payload))} characters")
            
            return False
    
    except Exception as e:
        logging.error(f"Error publishing to Slack: {e}")
        return False