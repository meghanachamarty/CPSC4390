"""
Multi-Armed Bandit Algorithm Implementation

Uses epsilon-greedy strategy:
- With probability epsilon: explore (random variant)
- Otherwise: exploit (best performing variant)

This balances exploration vs exploitation better than traditional A/B testing.
"""
import random
import math
from typing import Dict, List, Optional


class EpsilonGreedyBandit:
    """Epsilon-greedy Multi-Armed Bandit implementation."""
    
    def __init__(self, variants: List[str], epsilon: float = 0.1, initial_value: float = 0.0):
        """
        Initialize the bandit.
        
        Args:
            variants: List of variant names (e.g., ['A', 'B', 'C'])
            epsilon: Exploration probability (0.0 to 1.0). Higher = more exploration.
            initial_value: Initial conversion rate estimate for new variants
        """
        self.variants = variants
        self.epsilon = epsilon
        self.initial_value = initial_value
        
        # Track performance: {variant: {'clicks': int, 'impressions': int, 'rate': float}}
        self.stats: Dict[str, Dict] = {
            variant: {
                'clicks': 0,
                'impressions': 0,
                'rate': initial_value  # conversion rate estimate
            }
            for variant in variants
        }
    
    def select_variant(self) -> str:
        """
        Select which variant to show based on epsilon-greedy algorithm.
        
        Returns:
            Variant name (e.g., 'A', 'B', or 'C')
        """
        # Explore: choose random variant with probability epsilon
        if random.random() < self.epsilon:
            return random.choice(self.variants)
        
        # Exploit: choose best performing variant
        return self._get_best_variant()
    
    def _get_best_variant(self) -> str:
        """Get the variant with the highest conversion rate.
        
        If multiple variants have the same best rate, randomly choose one
        to ensure fair exploration among tied variants.
        """
        # Find the maximum conversion rate
        max_rate = max(self.stats[variant]['rate'] for variant in self.variants)
        
        # Get all variants with the maximum rate
        best_variants = [v for v in self.variants if self.stats[v]['rate'] == max_rate]
        
        # Randomly choose among tied best variants
        return random.choice(best_variants)
    
    def record_impression(self, variant: str) -> None:
        """Record that a variant was shown to a user."""
        if variant not in self.stats:
            self.stats[variant] = {
                'clicks': 0,
                'impressions': 0,
                'rate': self.initial_value
            }
        
        self.stats[variant]['impressions'] += 1
    
    def record_conversion(self, variant: str) -> None:
        """Record that a user clicked (converted) on a variant."""
        if variant not in self.stats:
            self.stats[variant] = {
                'clicks': 0,
                'impressions': 0,
                'rate': self.initial_value
            }
        
        self.stats[variant]['clicks'] += 1
        
        # Update conversion rate estimate
        impressions = self.stats[variant]['impressions']
        clicks = self.stats[variant]['clicks']
        
        if impressions > 0:
            self.stats[variant]['rate'] = clicks / impressions
    
    def get_stats(self) -> Dict[str, Dict]:
        """Get current statistics for all variants."""
        return self.stats.copy()
    
    def get_best_variant(self) -> str:
        """Get the currently best performing variant."""
        return self._get_best_variant()


# Global bandit instance (in-memory for now, can be persisted to DB later)
_variants = ['A', 'B', 'C']  # Three button variants
_bandit = EpsilonGreedyBandit(variants=_variants, epsilon=0.1)

def get_bandit() -> EpsilonGreedyBandit:
    """Get the global bandit instance."""
    return _bandit

