#!/usr/bin/env python3
import asyncio
from app.services.summary_enrichment_worker import SummaryEnrichmentWorker

async def main():
    w = SummaryEnrichmentWorker()
    ok = await w.run_once()
    print('Enrichment run_once result:', ok)

if __name__ == '__main__':
    asyncio.run(main())


