"""Automated web scraper for LinkedIn Jobs and Welcome to the Jungle using Playwright with stealth measures."""

import asyncio
import re
from typing import Any
from urllib.parse import quote_plus
from playwright.async_api import async_playwright

from src.utils.logger import log_audit_event, logger


class JobScraper:
    """Headless browser scraper extracting job postings without external dependencies."""

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def scrape_linkedin_jobs(
        self,
        keywords: list[str],
        location: str = "Paris, Île-de-France, France",
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Scrape public LinkedIn job search results without requiring user authentication."""
        query = quote_plus(" ".join(keywords))
        loc = quote_plus(location)
        search_url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc}&f_E=1%2C2"

        logger.info(f"Scraping LinkedIn Jobs: {search_url}")
        results: list[dict[str, Any]] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="fr-FR",
            )
            page = await context.new_page()

            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # Scroll down to trigger lazy loading
                for _ in range(3):
                    await page.mouse.wheel(0, 1000)
                    await page.wait_for_timeout(1000)

                job_cards = await page.locator("ul.jobs-search__results-list > li").all()
                logger.info(f"Found {len(job_cards)} job cards on LinkedIn page.")

                for card in job_cards[:limit]:
                    try:
                        title_elem = card.locator("h3.base-search-card__title")
                        company_elem = card.locator("h4.base-search-card__subtitle")
                        loc_elem = card.locator("span.job-search-card__location")
                        link_elem = card.locator("a.base-card__full-link")

                        title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else "Unknown Title"
                        company = (await company_elem.inner_text()).strip() if await company_elem.count() > 0 else "Unknown Company"
                        loc_text = (await loc_elem.inner_text()).strip() if await loc_elem.count() > 0 else location
                        job_link = await link_elem.get_attribute("href") if await link_elem.count() > 0 else ""

                        if not job_link or "utc.fr" in job_link:
                            continue

                        # Clean tracker parameters from URL
                        job_link = job_link.split("?")[0]

                        results.append({
                            "company_name": company,
                            "title": title,
                            "location": loc_text,
                            "job_url": job_link,
                            "source": "linkedin",
                            "workplace_type": "hybrid" if "hybride" in loc_text.lower() else "on-site",
                            "start_date": "Février 2027",
                            "duration_weeks": 26,
                            "description": f"Stage de fin d'études en {title} chez {company}. Localisation: {loc_text}.",
                            "raw_requirements": "Python, Machine Learning, Data Science, RAG, Deep Learning",
                        })
                    except Exception as card_err:
                        logger.debug(f"Error parsing LinkedIn job card: {card_err}")
                        continue

            except Exception as exc:
                logger.warning(f"LinkedIn scraping encountered issue: {exc}")
            finally:
                await browser.close()

        log_audit_event(
            event_type="SCRAPE_COMPLETED",
            entity_type="SCRAPER",
            entity_id="LINKEDIN",
            action="FETCH_JOBS",
            details={"count": len(results), "keywords": keywords},
        )
        return results

    async def scrape_welcome_to_the_jungle(
        self,
        keywords: list[str],
        location: str = "Paris, France",
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        """Scrape tech scale-up job postings on Welcome to the Jungle."""
        query = quote_plus(" ".join(keywords))
        search_url = f"https://www.welcometothejungle.com/fr/jobs?query={query}&aroundQuery=Paris&contract_types=internship"

        logger.info(f"Scraping Welcome to the Jungle: {search_url}")
        results: list[dict[str, Any]] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="fr-FR",
            )
            page = await context.new_page()

            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                cards = await page.locator("li[data-testid='search-results-list-item-wrapper']").all()
                logger.info(f"Found {len(cards)} cards on Welcome to the Jungle.")

                for card in cards[:limit]:
                    try:
                        title_elem = card.locator("h4")
                        company_elem = card.locator("span.sc-1tqy7y7-0, p")
                        link_elem = card.locator("a")

                        title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else "Stage IA"
                        company = (await company_elem.first.inner_text()).strip() if await company_elem.count() > 0 else "Tech Scale-up"
                        href = await link_elem.first.get_attribute("href") if await link_elem.count() > 0 else ""
                        full_url = f"https://www.welcometothejungle.com{href}" if href.startswith("/") else href

                        results.append({
                            "company_name": company,
                            "title": title,
                            "location": "Paris, Île-de-France",
                            "job_url": full_url,
                            "source": "wttj",
                            "workplace_type": "hybrid",
                            "start_date": "Février 2027",
                            "duration_weeks": 26,
                            "description": f"Stage chez {company} pour le poste {title}. Environnement startup / scale-up tech.",
                            "raw_requirements": "Python, IA, Machine Learning, RAG, LLM",
                        })
                    except Exception as err:
                        logger.debug(f"Error parsing WTTJ card: {err}")
                        continue
            except Exception as exc:
                logger.warning(f"WTTJ scraping issue: {exc}")
            finally:
                await browser.close()

        log_audit_event(
            event_type="SCRAPE_COMPLETED",
            entity_type="SCRAPER",
            entity_id="WTTJ",
            action="FETCH_JOBS",
            details={"count": len(results), "keywords": keywords},
        )
        return results


scraper = JobScraper(headless=True)
