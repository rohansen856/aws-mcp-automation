# Documentation for Website Scraper and Data Saving in ChromaDB

## Overview
This script implements a web scraper that extracts structured data from websites and integrates it with ChromaDB, a vector database for semantic search. The scraper is designed to crawl websites, parse their content, and store the extracted data in a vectorized format for efficient querying and retrieval.

---

## Key Features
1. **Web Crawling**:
    - The scraper starts from a given URL and recursively visits linked pages up to a specified depth.
    - It ensures that only valid URLs are visited and avoids blacklisted domains (e.g., social media platforms).

2. **Content Parsing**:
    - Extracts structured data such as titles, headings, paragraphs, images, and links from web pages.
    - Cleans and normalizes text content to ensure consistency.

3. **ChromaDB Integration**:
    - Stores the extracted data in a ChromaDB collection for semantic search.
    - Supports persistence by saving the database to a specified directory.

4. **Data Deduplication**:
    - Generates a unique content hash for each page to avoid duplicate entries in the database.

5. **Search Functionality**:
    - Allows querying the vector database to find semantically similar content.

6. **Data Export**:
    - Saves the structured data to JSON files for further analysis or backup.

---

## Detailed Documentation

### 1. **Web Scraper Class (`WebScraperWithVector`)**
This class encapsulates the functionality for web scraping and ChromaDB integration.

#### **Initialization**
- **`__init__(self, collection_name, persist_directory)`**:
  - Initializes the scraper with a specified ChromaDB collection name and persistence directory.
  - Sets up the ChromaDB client and collection.

#### **Crawling**
- **`crawl_website(self, start_url, max_depth, max_pages)`**:
  - Starts crawling from the given URL.
  - Parameters:
     - `start_url`: The starting URL for the crawl.
     - `max_depth`: Maximum depth of recursion for crawling.
     - `max_pages`: Maximum number of pages to process.
  - Returns a list of structured data extracted from the crawled pages.

#### **Content Parsing**
- **`parse_content(self, url)`**:
  - Fetches and parses the HTML content of a given URL.
  - Extracts structured data such as:
     - Title
     - Headings (h1-h6)
     - Paragraphs
     - Images (with `src` and `alt` attributes)
     - Links
  - Returns a dictionary containing the extracted data.

- **`clean_text(self, text)`**:
  - Cleans and normalizes text by removing extra whitespace and special characters.

#### **Link Extraction**
- **`extract_links(self, soup, base_url)`**:
  - Extracts all valid links from a web page.
  - Ensures that links are absolute and belong to the same domain as the starting URL.

#### **Data Deduplication**
- **`content_hash`**:
  - Generates a unique MD5 hash for the content of each page to identify duplicates.

---

### 2. **ChromaDB Integration**
The scraper integrates with ChromaDB to store and query vectorized representations of the scraped data.

#### **Setup**
- **`setup_chromadb(self)`**:
  - Initializes the ChromaDB client and creates or retrieves the specified collection.
  - Ensures persistence by saving the database to the specified directory.

#### **Data Preparation**
- **`prepare_document_for_vector_db(self, page_data)`**:
  - Combines the extracted text content (title, headings, paragraphs) into a single document for vectorization.
  - Prepares metadata such as URL, title, and content statistics for storage in ChromaDB.

#### **Data Insertion**
- **`insert_to_vector_db(self, structured_data)`**:
  - Inserts the structured data into the ChromaDB collection in batches.
  - Ensures efficient storage and avoids memory issues by processing data in chunks.

#### **Semantic Search**
- **`search_similar_content(self, query, n_results)`**:
  - Searches the ChromaDB collection for content similar to the given query.
  - Parameters:
     - `query`: The search query string.
     - `n_results`: Number of results to return.
  - Prints the URLs, titles, and content previews of the top results.

#### **Collection Statistics**
- **`get_collection_stats(self)`**:
  - Displays statistics about the ChromaDB collection, including:
     - Total number of documents.
     - Sample metadata keys.
     - Storage path.

---

### 3. **Data Export**
- **`save_structured_data(self, data, output_dir)`**:
  - Saves the structured data to JSON files in the specified output directory.
  - Creates individual JSON files for each page and a combined file for all pages.
  - Parameters:
     - `data`: List of structured data dictionaries.
     - `output_dir`: Directory where the JSON files will be saved.

---

## Usage
1. **Crawling a Website**:
    - Run the script with the `--url` parameter to specify the starting URL.
    - Use `--depth` and `--max-pages` to control the crawl depth and the number of pages to process.

2. **Saving Data**:
    - The scraped data is saved to JSON files in the specified output directory (`--output-dir`).

3. **Storing in ChromaDB**:
    - The data is automatically inserted into the ChromaDB collection for semantic search.

4. **Querying the Database**:
    - Use the `--search` parameter to query the vector database for similar content.

5. **Viewing Statistics**:
    - Use the `--stats` parameter to display collection statistics.

---

## Logging
- Logs are saved to `scraper.log` and printed to the console.
- Includes detailed information about the scraping process, errors, and database operations.

---

## Error Handling
- Handles network errors, invalid URLs, and empty content gracefully.
- Logs warnings and errors for debugging and monitoring.

---

## Example Command