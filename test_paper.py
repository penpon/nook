#!/usr/bin/env python3
import asyncio
from nook.services.paper_summarizer.paper_summarizer import PaperSummarizer

async def test():
    ps = PaperSummarizer()
    try:
        await ps.collect(limit=1)
        print("Success!")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())