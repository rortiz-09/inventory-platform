"""
Server Governance Platform - Health Score Calculator
Dynamic scoring based on EOL status, operational risk, and data quality.

Score Base: 100 points
Deductions are cumulative and documented in health_penalties.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScorePenalty:
    """Definition of a scoring penalty."""
    name: str
    points: int
    description: str
    category: str  # 'eol', 'operational', 'data_quality'


@dataclass
class HealthScoreResult:
    """Result of health score calculation."""
    score: int
    penalties: List[str]
    risk_level: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    details: Dict[str, any] = field(default_factory=dict)
    
    @property
    def color(self) -> str:
        """Get color code for UI display."""
        if self.score >= 80:
            return "#22c55e"  # Green
        elif self.score >= 60:
            return "#eab308"  # Yellow
        elif self.score >= 40:
            return "#f97316"  # Orange
        else:
            return "#ef4444"  # Red


class HealthScoreCalculator:
    """
    Dynamic Health Score Calculator.
    
    Scoring Rules (Base: 100):
    
    EOL Status (-40 to -20):
    - EOL Date passed (Vencido): -40 pts
    - EOL Date < 180 days (Riesgo Inminente): -20 pts
    - Unknown version (no normalization): -15 pts
    
    Operational Risk (-20 to -5):
    - Environment = PROD: -20 pts
    - No Owner assigned: -5 pts
    - No valid IP: -10 pts
    - Uptime > 5 years: -10 pts
    """
    
    # Penalty definitions
    PENALTIES = {
        # EOL Status
        'eol_expired': ScorePenalty(
            name='eol_expired',
            points=40,
            description='Sistema Operativo fuera de soporte (EOL)',
            category='eol'
        ),
        'eol_imminent': ScorePenalty(
            name='eol_imminent',
            points=20,
            description='EOL en menos de 180 días',
            category='eol'
        ),
        'version_unknown': ScorePenalty(
            name='version_unknown',
            points=15,
            description='Versión de SO no reconocida',
            category='eol'
        ),
        
        # Operational Risk
        'env_prod': ScorePenalty(
            name='env_prod',
            points=20,
            description='Servidor en ambiente de PRODUCCIÓN',
            category='operational'
        ),
        'no_owner': ScorePenalty(
            name='no_owner',
            points=5,
            description='Sin responsable asignado',
            category='operational'
        ),
        'no_ip': ScorePenalty(
            name='no_ip',
            points=10,
            description='Sin dirección IP válida',
            category='operational'
        ),
        'old_server': ScorePenalty(
            name='old_server',
            points=10,
            description='Servidor con más de 5 años',
            category='operational'
        ),
        
        # Data Quality
        'network_unknown': ScorePenalty(
            name='network_unknown',
            points=5,
            description='Red no clasificada',
            category='data_quality'
        ),
        'no_backup': ScorePenalty(
            name='no_backup',
            points=5,
            description='Sin backup configurado',
            category='data_quality'
        ),
    }
    
    def __init__(self):
        self.base_score = 100
    
    def calculate(
        self,
        eol_date: Optional[date] = None,
        is_eol: bool = False,
        os_product_key: Optional[str] = None,
        environment: Optional[str] = None,
        owner: Optional[str] = None,
        ip_address: Optional[str] = None,
        created_at: Optional[datetime] = None,
        network_classification: Optional[str] = None,
        backup_enabled: bool = False,
        **kwargs
    ) -> HealthScoreResult:
        """
        Calculate health score for a server.
        
        Args:
            eol_date: End of life date
            is_eol: Whether OS is already EOL
            os_product_key: Normalized OS product key
            environment: Server environment (prod/dev/test)
            owner: Assigned owner
            ip_address: Server IP address
            created_at: When the server record was created
            network_classification: Classification result (unknown = penalty)
            backup_enabled: Whether backup is configured
            
        Returns:
            HealthScoreResult with score, penalties, and risk level
        """
        score = self.base_score
        penalties: List[str] = []
        details: Dict[str, any] = {}
        
        # === EOL Status Checks ===
        
        # Check if EOL already
        if is_eol:
            score -= self.PENALTIES['eol_expired'].points
            penalties.append(self.PENALTIES['eol_expired'].description)
            details['eol_status'] = 'EXPIRED'
        elif eol_date:
            # Check if EOL is imminent (< 180 days)
            days_until_eol = (eol_date - date.today()).days
            if days_until_eol < 180:
                score -= self.PENALTIES['eol_imminent'].points
                penalties.append(f"{self.PENALTIES['eol_imminent'].description} ({days_until_eol} días)")
                details['eol_status'] = 'IMMINENT'
                details['days_until_eol'] = days_until_eol
            else:
                details['eol_status'] = 'OK'
                details['days_until_eol'] = days_until_eol
        
        # Check if OS is unknown/unrecognized
        if os_product_key == 'unknown' or not os_product_key:
            score -= self.PENALTIES['version_unknown'].points
            penalties.append(self.PENALTIES['version_unknown'].description)
            details['os_status'] = 'UNKNOWN'
        else:
            details['os_status'] = 'RECOGNIZED'
        
        # === Operational Risk Checks ===
        
        # Production environment (higher risk)
        if environment and environment.lower() == 'prod':
            score -= self.PENALTIES['env_prod'].points
            penalties.append(self.PENALTIES['env_prod'].description)
            details['env_risk'] = 'HIGH'
        else:
            details['env_risk'] = 'LOW'
        
        # No owner assigned
        if not owner or owner.strip() == '':
            score -= self.PENALTIES['no_owner'].points
            penalties.append(self.PENALTIES['no_owner'].description)
        
        # No valid IP
        if not ip_address or ip_address.strip() == '':
            score -= self.PENALTIES['no_ip'].points
            penalties.append(self.PENALTIES['no_ip'].description)
        
        # Old server (> 5 years)
        if created_at:
            age_days = (datetime.now() - created_at).days
            if age_days > 5 * 365:  # 5 years
                score -= self.PENALTIES['old_server'].points
                penalties.append(self.PENALTIES['old_server'].description)
                details['age_years'] = round(age_days / 365, 1)
        
        # === Data Quality Checks ===
        
        # Unknown network
        if network_classification == 'unknown' or not network_classification:
            score -= self.PENALTIES['network_unknown'].points
            penalties.append(self.PENALTIES['network_unknown'].description)
        
        # No backup
        if not backup_enabled:
            score -= self.PENALTIES['no_backup'].points
            penalties.append(self.PENALTIES['no_backup'].description)
        
        # Ensure score doesn't go below 0
        score = max(0, score)
        
        # Determine risk level
        risk_level = self._get_risk_level(score)
        
        return HealthScoreResult(
            score=score,
            penalties=penalties,
            risk_level=risk_level,
            details=details
        )
    
    def _get_risk_level(self, score: int) -> str:
        """Determine risk level based on score."""
        if score >= 80:
            return 'LOW'
        elif score >= 60:
            return 'MEDIUM'
        elif score >= 40:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def calculate_from_server(self, server: dict) -> HealthScoreResult:
        """
        Calculate health score from a server dict.
        
        Args:
            server: Dictionary with server data
            
        Returns:
            HealthScoreResult
        """
        return self.calculate(
            eol_date=server.get('eol_date'),
            is_eol=server.get('eol_days_remaining', 0) < 0 if server.get('eol_days_remaining') is not None else False,
            os_product_key=server.get('os_product_key'),
            environment=server.get('environment'),
            owner=server.get('owner'),
            ip_address=server.get('ip_address'),
            created_at=server.get('created_at'),
            network_classification=server.get('city', server.get('environment')),
            backup_enabled=server.get('backup_enabled', False),
        )


# Singleton instance
calculator = HealthScoreCalculator()


def calculate_health_score(**kwargs) -> HealthScoreResult:
    """
    Convenience function to calculate health score.
    
    Usage:
        result = calculate_health_score(
            eol_date=date(2024, 6, 30),
            environment='prod',
            owner=None
        )
        print(f"Score: {result.score}, Risk: {result.risk_level}")
    """
    return calculator.calculate(**kwargs)


def calculate_server_health(server: dict) -> HealthScoreResult:
    """Calculate health score from server dict."""
    return calculator.calculate_from_server(server)


# Quick test
if __name__ == "__main__":
    from datetime import date, datetime, timedelta
    
    test_cases = [
        {
            "name": "Healthy server",
            "params": {
                "eol_date": date.today() + timedelta(days=365),
                "os_product_key": "rhel",
                "environment": "dev",
                "owner": "John Doe",
                "ip_address": "192.168.1.10",
                "backup_enabled": True,
            }
        },
        {
            "name": "EOL Expired Production",
            "params": {
                "is_eol": True,
                "os_product_key": "centos",
                "environment": "prod",
                "owner": None,
                "ip_address": "192.168.59.10",
            }
        },
        {
            "name": "Unknown OS",
            "params": {
                "os_product_key": "unknown",
                "environment": "test",
                "owner": "Jane Doe",
                "ip_address": None,
            }
        },
        {
            "name": "EOL Imminent",
            "params": {
                "eol_date": date.today() + timedelta(days=90),
                "os_product_key": "ubuntu",
                "environment": "prod",
                "owner": "Admin",
                "ip_address": "10.0.0.5",
                "backup_enabled": True,
            }
        },
    ]
    
    print("\n" + "=" * 80)
    print("HEALTH SCORE CALCULATOR TEST RESULTS")
    print("=" * 80 + "\n")
    
    for case in test_cases:
        result = calculate_health_score(**case["params"])
        print(f"\n{case['name']}:")
        print(f"  Score: {result.score}/100")
        print(f"  Risk Level: {result.risk_level}")
        print(f"  Penalties:")
        for penalty in result.penalties:
            print(f"    - {penalty}")
        print("-" * 40)
