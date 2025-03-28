# Property24 Scraper 🏘️

An advanced asynchronous web scraper for Property24 property listings. Extracts detailed real estate data including pricing, features, and points of interest.

## Features

- **Full property details** extraction including:
  - Pricing and property size
  - Location hierarchy (Province/City/Town)
  - Key features and amenities
  - Points of interest (POIs) with distances
  - Property descriptions and images
- **Smart scrolling** with hover detection
- **Duplicate prevention** using listing IDs
- **Multi-context scraping** with 4 concurrent browsers
- **Automatic pagination** handling (32 pages per instance)
- **Data cleaning** and normalization pipelines

## Installation

1. **Clone repository**
```bash
git clone https://github.com/NtsakoCosm/scrape24.git
cd Property24-Scraper
