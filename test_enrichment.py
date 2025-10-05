import asyncio
from app.services.summary_enrichment_worker import SummaryEnrichmentWorker

async def run():
    worker = SummaryEnrichmentWorker()
    # Check if flight exists
    fs_id = await worker._get_flight_summary_id_by_callsign('FJI910')
    if fs_id:
        print(f"Found flight summary id: {fs_id}")
        result = await worker.process_enrichment(fs_id)
        print(f"Processed FJI910 enrichment: {result}")
    else:
        print("Flight not found")

if __name__ == '__main__':
    asyncio.run(run())