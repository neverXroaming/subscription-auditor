"""
Core subscription management logic
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class Subscription:
    """Subscription data model"""
    name: str
    cost: float
    billing_cycle: str  # monthly, yearly, etc.
    last_charged: datetime
    vendor_email: str
    cancellation_url: Optional[str] = None
    phone_number: Optional[str] = None
    usage_score: float = 0.0  # 0-10 scale
    refund_eligible: bool = False
    days_since_signup: int = 0
    category: str = "unknown"

class SubscriptionManager:
    """Main subscription management class"""
    
    def __init__(self, gmail_analyzer, bank_parser, refund_generator):
        self.gmail_analyzer = gmail_analyzer
        self.bank_parser = bank_parser
        self.refund_generator = refund_generator
        self.subscriptions: List[Subscription] = []
        
    def discover_subscriptions(self) -> List[Subscription]:
        """Discover all subscriptions from multiple sources"""
        logger.info("Discovering subscriptions from Gmail...")
        email_subscriptions = self.gmail_analyzer.find_subscription_emails()
        
        logger.info("Discovering subscriptions from bank statements...")
        bank_subscriptions = self.bank_parser.find_recurring_charges()
        
        # Merge and deduplicate
        self.subscriptions = self._merge_subscription_data(
            email_subscriptions, bank_subscriptions
        )
        
        # Enrich with additional data
        self._enrich_subscription_data()
        
        return self.subscriptions
    
    def _merge_subscription_data(self, email_subs, bank_subs) -> List[Subscription]:
        """Merge subscription data from different sources"""
        merged = {}
        
        # Process email subscriptions
        for sub in email_subs:
            key = self._generate_subscription_key(sub['name'])
            merged[key] = Subscription(
                name=sub['name'],
                cost=sub.get('cost', 0.0),
                billing_cycle=sub.get('billing_cycle', 'monthly'),
                last_charged=sub.get('last_charged', datetime.now()),
                vendor_email=sub.get('vendor_email', ''),
                cancellation_url=sub.get('cancellation_url'),
                days_since_signup=sub.get('days_since_signup', 0)
            )
        
        # Process bank subscriptions
        for sub in bank_subs:
            key = self._generate_subscription_key(sub['name'])
            if key in merged:
                # Update existing with bank data
                merged[key].cost = sub['cost']
                merged[key].last_charged = sub['last_charged']
            else:
                # Create new subscription
                merged[key] = Subscription(
                    name=sub['name'],
                    cost=sub['cost'],
                    billing_cycle='monthly',  # assume monthly from bank data
                    last_charged=sub['last_charged'],
                    vendor_email='',
                )
        
        return list(merged.values())
    
    def _generate_subscription_key(self, name: str) -> str:
        """Generate a unique key for subscription matching"""
        return name.lower().replace(' ', '').replace('-', '').replace('_', '')
    
    def _enrich_subscription_data(self):
        """Enrich subscription data with additional information"""
        for sub in self.subscriptions:
            # Calculate usage score (placeholder - would need actual usage data)
            sub.usage_score = self._calculate_usage_score(sub)
            
            # Determine refund eligibility
            sub.refund_eligible = self._is_refund_eligible(sub)
            
            # Categorize subscription
            sub.category = self._categorize_subscription(sub)
    
    def _calculate_usage_score(self, subscription: Subscription) -> float:
        """Calculate usage score (0-10) for a subscription"""
        # Placeholder logic - in reality, you'd integrate with usage APIs
        # For now, use heuristics based on subscription age and type
        
        if subscription.days_since_signup < 7:
            return 1.0  # Likely unused if very new
        elif subscription.days_since_signup < 30:
            return 3.0  # Possibly unused
        else:
            return 5.0  # Assume moderate usage for older subscriptions
    
    def _is_refund_eligible(self, subscription: Subscription) -> bool:
        """Determine if subscription is eligible for refund"""
        return (
            subscription.days_since_signup <= 30 and
            subscription.usage_score < 3.0 and
            subscription.cost > 10.0  # Only worth pursuing for higher amounts
        )
    
    def _categorize_subscription(self, subscription: Subscription) -> str:
        """Categorize subscription by type"""
        name_lower = subscription.name.lower()
        
        if any(word in name_lower for word in ['netflix', 'hulu', 'disney', 'streaming']):
            return 'entertainment'
        elif any(word in name_lower for word in ['adobe', 'canva', 'figma', 'design']):
            return 'design_tools'
        elif any(word in name_lower for word in ['github', 'aws', 'hosting', 'domain']):
            return 'development'
        elif any(word in name_lower for word in ['gym', 'fitness', 'health']):
            return 'health_fitness'
        else:
            return 'other'
    
    def identify_refund_opportunities(self) -> List[Subscription]:
        """Identify subscriptions eligible for refunds"""
        return [sub for sub in self.subscriptions if sub.refund_eligible]
    
    def generate_reports(self):
        """Generate comprehensive reports"""
        # Create output directory
        output_dir = Path("data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate CSV report
        df = pd.DataFrame([
            {
                'Name': sub.name,
                'Monthly Cost': sub.cost,
                'Billing Cycle': sub.billing_cycle,
                'Last Charged': sub.last_charged.strftime('%Y-%m-%d'),
                'Category': sub.category,
                'Usage Score': sub.usage_score,
                'Refund Eligible': sub.refund_eligible,
                'Days Since Signup': sub.days_since_signup,
                'Vendor Email': sub.vendor_email,
                'Cancellation URL': sub.cancellation_url or 'N/A'
            }
            for sub in self.subscriptions
        ])
        
        # Save reports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        df.to_csv(output_dir / f'subscription_audit_{timestamp}.csv', index=False)
        
        # Generate summary statistics
        summary = {
            'total_subscriptions': len(self.subscriptions),
            'total_monthly_cost': sum(sub.cost for sub in self.subscriptions),
            'refund_opportunities': len([sub for sub in self.subscriptions if sub.refund_eligible]),
            'potential_refund_amount': sum(sub.cost for sub in self.subscriptions if sub.refund_eligible),
            'by_category': df.groupby('Category')['Monthly Cost'].sum().to_dict()
        }
        
        # Save summary
        with open(output_dir / f'summary_{timestamp}.txt', 'w') as f:
            f.write("SUBSCRIPTION AUDIT SUMMARY\n")
            f.write("=" * 30 + "\n\n")
            f.write(f"Total Subscriptions: {summary['total_subscriptions']}\n")
            f.write(f"Total Monthly Cost: ${summary['total_monthly_cost']:.2f}\n")
            f.write(f"Total Annual Cost: ${summary['total_monthly_cost'] * 12:.2f}\n\n")
            f.write(f"Refund Opportunities: {summary['refund_opportunities']}\n")
            f.write(f"Potential Refund Amount: ${summary['potential_refund_amount']:.2f}\n\n")
            f.write("Spending by Category:\n")
            for category, amount in summary['by_category'].items():
                f.write(f"  {category.title()}: ${amount:.2f}\n")
        
        logger.info(f"Reports generated in {output_dir}")
    
    def generate_refund_requests(self):
        """Generate refund requests for eligible subscriptions"""
        refund_eligible = [sub for sub in self.subscriptions if sub.refund_eligible]
        
        for subscription in refund_eligible:
            try:
                request = self.refund_generator.create_refund_request(subscription)
                logger.info(f"Generated refund request for {subscription.name}")
            except Exception as e:
                logger.error(f"Failed to generate refund request for {subscription.name}: {e}")
