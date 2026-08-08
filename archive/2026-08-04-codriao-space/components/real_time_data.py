import aiohttp
import asyncio
from typing import List, Dict, Any

class RealTimeDataIntegrator:
    """Integrates real-time data for up-to-date responses"""

    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def fetch_and_integrate(self, urls: List[str]) -> Dict[str, Any]:
        """Fetch data from multiple sources and integrate it"""
        tasks = [self.fetch_data(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        integrated_data = self.integrate_data(results)
        return integrated_data

    async def fetch_data(self, url: str) -> Dict[str, Any]:
        """Fetch data from an external API"""
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()  # Raise an error for bad status codes
                return await response.json()
        except Exception as e:
            return {"error": str(e), "url": url}

    def integrate_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Integrate data from multiple sources"""
        integrated_data = {}
        for item in data:
            if isinstance(item, dict):
                integrated_data.update(item)
            else:
                # Handle the case where fetch_data returned an error
                integrated_data.setdefault("errors", []).append(item)
        return integrated_data

    async def close_session(self):
        """Close the aiohttp session"""
        await self.session.close()