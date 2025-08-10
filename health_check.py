import asyncio
from app.utils.health_monitor import HealthMonitor

async def main():
    hm = HealthMonitor()
    result = await hm.get_comprehensive_health_report()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
