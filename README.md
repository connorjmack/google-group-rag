# Scholar-RAG: Community Archive Ingestion Pipeline

## Overview
Scholar-RAG is a data ingestion and retrieval framework designed to extract, structure, and index technical knowledge from distributed community archives. 

While formal academic literature is easily accessible via standard APIs, a significant volume of specialized domain knowledge—particularly in fields like climate modeling, energy systems, and geospatial analysis—resides in unstructured mailing lists and Google Groups. This repository provides a generalized pipeline to harvest these "dark data" sources, converting threaded email discussions into a structured corpus suitable for Retrieval-Augmented Generation (RAG) applications.

## Repository Structure
The pipeline consists of two primary modules:
1.  **Ingestion Engine:** A Selenium-based scraper that abstracts the DOM structure of public Google Groups to target arbitrary communities (e.g., Carbon Dioxide Removal, OpenMod, Pangeo).
2.  **Indexing Pipeline:** (In development) A workflow to chunk, embed, and store text data in a vector database for semantic query resolution.

## Features
* **Generalized DOM Targeting:** Utilizes shared CSS class structures across Google Groups to eliminate the need for group-specific scrapers.
* **Politeness Architecture:** Implements stochastic delays and user-agent rotation to respect server load and adhere to standard web crawling ethics.
* **Structured Output:** Normalizes nested email threads into a flat CSV schema containing metadata (date, author, thread URL) and full-text content.

## Installation

### Using Conda (Recommended)
```bash
conda env create -f environment.yml
conda activate scholar-rag