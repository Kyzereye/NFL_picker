#!/usr/bin/env python3
"""
Analyze DraftKings page structure to understand how games are organized
"""

import sys
import os
import json
import re
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_page_structure():
    """Analyze the DraftKings page structure"""
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--user-agent={Config.USER_AGENT}")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        logger.info("Loading DraftKings NFL page...")
        driver.get("https://sportsbook.draftkings.com/leagues/football/nfl")
        time.sleep(10)  # Wait for dynamic content
        
        # Get the page title
        title = driver.title
        logger.info(f"Page title: {title}")
        
        # Look for the main content area
        main_selectors = [
            'main',
            '[role="main"]',
            '.sportsbook-content',
            '.main-content',
            '#main-content'
        ]
        
        main_content = None
        for selector in main_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                main_content = element
                logger.info(f"Found main content with selector: {selector}")
                break
            except:
                continue
        
        if not main_content:
            logger.warning("Could not find main content area")
            main_content = driver.find_element(By.TAG_NAME, 'body')
        
        # Look for different types of elements that might contain games
        element_types = {
            'Links with "event" in href': '//a[contains(@href, "/event/")]',
            'Elements with "Bills" text': '//*[contains(text(), "Bills")]',
            'Elements with "Dolphins" text': '//*[contains(text(), "Dolphins")]',
            'Elements with odds patterns': '//*[contains(text(), "-") or contains(text(), "+")]',
            'Divs with event classes': '//div[contains(@class, "event")]',
            'Divs with game classes': '//div[contains(@class, "game")]',
            'Divs with match classes': '//div[contains(@class, "match")]',
            'Tables': '//table',
            'Table rows': '//tr',
            'List items': '//li'
        }
        
        findings = {}
        for desc, xpath in element_types.items():
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                findings[desc] = len(elements)
                
                if elements and len(elements) < 20:  # Show details for smaller sets
                    logger.info(f"{desc}: {len(elements)} elements")
                    for i, elem in enumerate(elements[:5]):  # Show first 5
                        try:
                            text = elem.text[:100] if elem.text else elem.get_attribute('outerHTML')[:100]
                            logger.info(f"  {i+1}: {text}...")
                        except:
                            pass
                else:
                    logger.info(f"{desc}: {len(elements)} elements")
                    
            except Exception as e:
                findings[desc] = f"Error: {e}"
        
        # Look for specific NFL game patterns in the page source
        page_source = driver.page_source
        
        # Save page source for analysis
        with open('/home/jeff/Projects/study/NFL/draftkings_page_analysis.html', 'w') as f:
            f.write(page_source)
        
        # Look for game patterns
        game_patterns = {
            'Thursday Night Football': r'Thursday.*Night.*Football',
            'Team @ Team patterns': r'[A-Z][a-z]+\s+@\s+[A-Z][a-z]+',
            'Team vs Team patterns': r'[A-Z][a-z]+\s+vs\.?\s+[A-Z][a-z]+',
            'Odds patterns': r'[+-]\d{2,4}',
            'Event URLs': r'/event/[^"\'>\s]+',
            'Game time patterns': r'\d{1,2}:\d{2}\s*(AM|PM|ET)',
        }
        
        pattern_findings = {}
        for desc, pattern in game_patterns.items():
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            pattern_findings[desc] = len(matches)
            
            if matches and len(matches) < 20:
                logger.info(f"{desc}: Found {len(matches)} matches")
                for match in matches[:5]:
                    logger.info(f"  - {match}")
            else:
                logger.info(f"{desc}: {len(matches)} matches")
        
        # Look for JSON data in the page
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__APP_STATE__\s*=\s*({.*?});',
            r'window\.__DATA__\s*=\s*({.*?});'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, page_source, re.DOTALL)
            if matches:
                logger.info(f"Found JSON data with pattern: {pattern}")
                try:
                    data = json.loads(matches[0])
                    logger.info(f"JSON keys: {list(data.keys())[:10]}")
                except:
                    logger.info("Could not parse JSON data")
        
        # Summary
        logger.info("\n=== ANALYSIS SUMMARY ===")
        logger.info(f"Page title: {title}")
        logger.info("Element counts:")
        for desc, count in findings.items():
            logger.info(f"  {desc}: {count}")
        
        logger.info("Pattern matches:")
        for desc, count in pattern_findings.items():
            logger.info(f"  {desc}: {count}")
        
        return findings, pattern_findings
        
    finally:
        driver.quit()

def main():
    """Main analysis function"""
    logger.info("Starting DraftKings page analysis...")
    
    try:
        findings, patterns = analyze_page_structure()
        
        # Save analysis results
        analysis_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'element_findings': findings,
            'pattern_findings': patterns
        }
        
        with open('/home/jeff/Projects/study/NFL/draftkings_analysis.json', 'w') as f:
            json.dump(analysis_results, f, indent=2)
        
        logger.info("Analysis complete. Results saved to draftkings_analysis.json")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()

