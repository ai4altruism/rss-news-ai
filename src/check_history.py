#!/usr/bin/env python3
# src/check_history.py

import os
import json
import logging
from datetime import datetime
from utils import setup_logger

def check_article_history():
    """Check the article history file and display its contents."""
    logger = setup_logger()
    history_file = "data/article_history.json"
    
    logger.info("Checking article history...")
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check if data directory exists
    data_dir = os.path.dirname(history_file)
    if os.path.exists(data_dir):
        logger.info(f"Data directory {data_dir} exists")
        logger.info(f"Data directory contents: {os.listdir(data_dir)}")
    else:
        logger.error(f"Data directory {data_dir} does not exist!")
    
    # Check if history file exists
    if os.path.exists(history_file):
        logger.info(f"Article history file {history_file} exists")
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
            
            article_count = len(history.get("articles", {}))
            last_cleaned = history.get("last_cleaned", "Never")
            
            logger.info(f"History contains {article_count} articles")
            logger.info(f"Last cleaned: {last_cleaned}")
            
            # Show sample of articles (limit to 5 for brevity)
            sample_articles = list(history.get("articles", {}).items())[:5]
            for url, data in sample_articles:
                logger.info(f"Sample article: {data.get('title')} - {url[:50]}...")
                
        except Exception as e:
            logger.error(f"Error reading history file: {e}")
    else:
        logger.error(f"Article history file {history_file} does not exist!")
    
    # Check file permissions
    try:
        test_file = f"{data_dir}/test_write_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        with open(test_file, "w") as f:
            f.write("Test write permissions")
        logger.info(f"Successfully created test file {test_file}")
        os.remove(test_file)
        logger.info(f"Successfully removed test file {test_file}")
    except Exception as e:
        logger.error(f"Error testing write permissions: {e}")

if __name__ == "__main__":
    check_article_history()