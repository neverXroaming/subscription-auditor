#!/usr/bin/env python3
"""
Subscription Auditor - Main Application
Automatically discovers, analyzes, and manages subscriptions
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from subscription_manager import SubscriptionManager
from gmail_analyzer import GmailAnalyzer
from bank_parser import BankStatementParser
from refund_generator import RefundRequestGenerator

# Load environment variables
load_dotenv()

def setup_logging():
    """Configure logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()  # Remove default handler
    logger.add(
        "logs/subscription_auditor_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    logger.add(sys.stdout, level=log_level)

def main():
    """Main application entry point"""
    setup_logging()
    logger.info("Starting Subscription Auditor")
    
    try:
        # Initialize components
        gmail_analyzer = GmailAnalyzer()
        bank_parser = BankStatementParser()
        refund_generator = RefundRequestGenerator()
        
        # Create main manager
        manager = SubscriptionManager(
            gmail_analyzer=gmail_analyzer,
            bank_parser=bank_parser,
            refund_generator=refund_generator
        )
        
        # Run the audit
        logger.info("Starting subscription discovery...")
        subscriptions = manager.discover_subscriptions()
        logger.info(f"Found {len(subscriptions)} subscriptions")
        
        # Analyze for refund opportunities
        logger.info("Analyzing refund opportunities...")
        refund_opportunities = manager.identify_refund_opportunities()
        logger.info(f"Found {len(refund_opportunities)} potential refunds")
        
        # Generate reports
        logger.info("Generating reports...")
        manager.generate_reports()
        
        # Optionally generate refund requests
        if input("Generate refund requests? (y/n): ").lower() == 'y':
            manager.generate_refund_requests()
        
        logger.info("Audit complete! Check the 'data/output' folder for results.")
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()
