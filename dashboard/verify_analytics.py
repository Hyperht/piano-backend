import os
import logging
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'piano.settings')
django.setup()

from analytics.services.dashboard import DashboardService

logger = logging.getLogger(__name__)


def verify():
    """Verification script for analytics data integrity."""
    logger.info("Verifying Analytics...")
    data = DashboardService.get_aggregated_analytics()
    logger.info("Keys found: %s", list(data.keys()))
    logger.info("Total Revenue: %s", data['total_revenue'])
    logger.info("Total Orders: %s", data['total_orders'])
    logger.info("Recent Orders Count: %d", len(data['recent_orders']))

    logger.info("Verifying Charts...")
    rev_chart = DashboardService.get_revenue_chart(30)
    logger.info("Revenue Chart Data Points: %d", len(rev_chart))
    if rev_chart:
        logger.info("Sample: %s", rev_chart[0])

    ord_chart = DashboardService.get_orders_chart(30)
    logger.info("Orders Chart Data Points: %d", len(ord_chart))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    verify()
