# SearXNG API Documentation

This document provides comprehensive documentation for using the SearXNG API with curl and understanding the response schema.

## Table of Contents

- [Using curl](#using-curl)
- [Response Schema](#response-schema)
- [Error Handling](#error-handling)
- [Practical Examples](#practical-examples)

## Using curl

You can query SearXNG directly using curl for simple integration or testing:

### Basic Search
```bash
# Simple search query
curl "http://localhost:7777/search?q=python+programming&format=json"

# URL-encoded query for complex searches
curl "http://localhost:7777/search?q=python%20programming%20tutorial&format=json"
```

### Advanced Search Options
```bash
# Search with specific categories
curl "http://localhost:7777/search?q=docker&categories=general,it&format=json"

# Search with specific engines
curl "http://localhost:7777/search?q=github&engines=github,stackoverflow&format=json"

# Search with language preference
curl "http://localhost:7777/search?q=hello&lang=es&format=json"

# Get HTML format instead of JSON
curl "http://localhost:7777/search?q=python&format=html"
```

### Available Parameters

| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| `q` | Search query (required) | `python programming` |
| `format` | Response format | `json`, `html` |
| `categories` | Search categories (comma-separated) | `general`, `it`, `videos`, `images`, `news` |
| `engines` | Specific engines (comma-separated) | `google`, `bing`, `duckduckgo`, `github` |
| `lang` | Language code | `en`, `es`, `fr`, `de` |

### Available Categories
- `general` - General web search
- `it` - Information technology
- `files` - File search
- `images` - Image search
- `videos` - Video search
- `music` - Music search
- `map` - Maps and locations
- `news` - News articles
- `science` - Scientific content
- `social media` - Social media platforms

### Available Engines
Based on the current configuration, the following engines are available:
- `bing` - Microsoft Bing
- `duckduckgo` - DuckDuckGo
- `google` - Google Search
- `startpage` - Startpage
- `wikipedia` - Wikipedia
- `wikidata` - Wikidata
- `github` - GitHub
- `reddit` - Reddit
- `youtube` - YouTube
- `vimeo` - Vimeo
- `stackexchange` - Stack Exchange
- `ahmia` - Ahmia (Tor search)
- `yacy` - YaCy

## Response Schema

SearXNG returns structured JSON responses with the following schema:

### Successful Response Structure
```json
{
  "query": "python programming",
  "number_of_results": 42,
  "results": [
    {
      "url": "https://example.com/python-tutorial",
      "title": "Python Programming Tutorial",
      "content": "Learn Python programming with this comprehensive tutorial...",
      "engine": "google",
      "parsed_url": ["https", "example.com", "/python-tutorial"],
      "template": "default.html",
      "engines": ["google"],
      "positions": [1],
      "score": 0.95
    }
  ],
  "answers": [],
  "corrections": [],
  "infoboxes": [],
  "suggestions": [],
  "unresponsive_engines": []
}
```

### Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | The original search query |
| `number_of_results` | integer | Total number of results found |
| `results` | array | Array of search result objects |
| `answers` | array | Direct answers (e.g., calculations, definitions) |
| `corrections` | array | Spelling corrections for the query |
| `infoboxes` | array | Structured information boxes |
| `suggestions` | array | Search suggestions |
| `unresponsive_engines` | array | Engines that failed to respond |

### Individual Result Object Schema
```json
{
  "url": "string",           // The result URL
  "title": "string",         // Result title
  "content": "string",       // Result snippet/description
  "engine": "string",        // Search engine that found this result
  "parsed_url": ["string"],  // Parsed URL components
  "template": "string",      // Template used for rendering
  "engines": ["string"],     // Engines that returned this result
  "positions": [integer],    // Position in search results
  "score": float             // Relevance score (0.0-1.0)
}
```

### Additional Response Fields

#### Answers Array
Contains direct answers to queries (calculations, definitions, etc.):
```json
{
  "answers": [
    {
      "answer": "42",
      "type": "calculation",
      "engine": "calculator"
    }
  ]
}
```

#### Corrections Array
Contains spelling corrections:
```json
{
  "corrections": [
    {
      "correction": "python programming",
      "original": "pythn programing"
    }
  ]
}
```

#### Infoboxes Array
Contains structured information:
```json
{
  "infoboxes": [
    {
      "infobox": "Python (programming language)",
      "content": "Python is a high-level programming language...",
      "engine": "wikipedia"
    }
  ]
}
```

## Error Handling

### Error Response Schema
```json
{
  "error": "string",         // Error message
  "status_code": integer     // HTTP status code (if applicable)
}
```

### Common Error Examples

#### Connection Refused (SearXNG not running)
```json
{
  "error": "URL Error: [Errno 61] Connection refused"
}
```

#### Invalid Query Parameters
```json
{
  "error": "HTTP Error 400: Bad Request"
}
```

#### SearXNG Instance Not Found
```json
{
  "error": "HTTP Error 404: Not Found"
}
```

#### Request Timeout
```json
{
  "error": "HTTP Error 504: Gateway Timeout"
}
```

#### JSON Parsing Error
```json
{
  "error": "JSON Decode Error: Expecting value: line 1 column 1 (char 0)"
}
```

## Practical Examples

### Programming Tutorials
```bash
# Search for Python Flask tutorials
curl "http://localhost:7777/search?q=python%20flask%20tutorial&categories=general,it&format=json"

# Search for Docker tutorials
curl "http://localhost:7777/search?q=docker%20compose%20tutorial&categories=general,it&format=json"

# Search for machine learning resources
curl "http://localhost:7777/search?q=machine%20learning%20python&categories=general,it&format=json"
```

### Video Content
```bash
# Search for video tutorials
curl "http://localhost:7777/search?q=docker%20tutorial&categories=videos&format=json"

# Search for programming videos
curl "http://localhost:7777/search?q=python%20programming&categories=videos&format=json"
```

### Specific Platforms
```bash
# Search GitHub repositories
curl "http://localhost:7777/search?q=flask%20web%20framework&engines=github&format=json"

# Search Stack Overflow
curl "http://localhost:7777/search?q=python%20error&engines=stackexchange&format=json"

# Search Reddit discussions
curl "http://localhost:7777/search?q=python%20programming&engines=reddit&format=json"
```

### Exact Phrase Searches
```bash
# Search for exact phrases (use quotes in URL encoding)
curl "http://localhost:7777/search?q=%22machine%20learning%22&format=json"

# Search for specific terms
curl "http://localhost:7777/search?q=%22docker%20compose%22%20tutorial&format=json"
```

### Multi-language Searches
```bash
# Search in Spanish
curl "http://localhost:7777/search?q=programacion%20python&lang=es&format=json"

# Search in French
curl "http://localhost:7777/search?q=programmation%20python&lang=fr&format=json"

# Search in German
curl "http://localhost:7777/search?q=python%20programmierung&lang=de&format=json"
```

### Integration Examples

#### Shell Script Integration
```bash
#!/bin/bash

# Search and save results to file
curl "http://localhost:7777/search?q=docker%20compose&format=json" > results.json

# Search and extract first result title
curl "http://localhost:7777/search?q=python&format=json" | jq '.results[0].title'

# Search and count results
curl "http://localhost:7777/search?q=machine%20learning&format=json" | jq '.results | length'
```

#### Batch Processing
```bash
#!/bin/bash

# Search multiple queries
queries=("python programming" "docker compose" "machine learning")

for query in "${queries[@]}"; do
    echo "Searching: $query"
    curl "http://localhost:7777/search?q=$(echo "$query" | sed 's/ /%20/g')&format=json" | jq '.results | length'
    echo "=========================================="
done
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: SearXNG is not running
   ```bash
   # Check if SearXNG is running
   docker compose ps
   
   # Start SearXNG if not running
   docker compose up -d
   ```

2. **404 Not Found**: Wrong base URL or port
   ```bash
   # Check your configuration
   echo $SEARXNG_PROTOCOL $SEARXNG_HOST $SEARXNG_PORT
   
   # Test with explicit URL
   curl "http://localhost:7777/search?q=test&format=json"
   ```

3. **Timeout Errors**: SearXNG is slow or overloaded
   ```bash
   # Use longer timeout
   curl --max-time 60 "http://localhost:7777/search?q=test&format=json"
   ```

4. **No Results**: Try different categories or engines
   ```bash
   # Search in general category
   curl "http://localhost:7777/search?q=test&categories=general&format=json"
   
   # Use specific engines
   curl "http://localhost:7777/search?q=test&engines=google,bing&format=json"
   ```

### Debug Mode

For debugging, you can add verbose output to curl:
```bash
# Verbose output
curl -v "http://localhost:7777/search?q=test&format=json"

# Include response headers
curl -i "http://localhost:7777/search?q=test&format=json"
```
