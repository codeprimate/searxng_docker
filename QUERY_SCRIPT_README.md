# SearXNG Query Script

A Python script to programmatically query your SearXNG instance and retrieve search results.

## Features

- **Simple command-line interface** for searching
- **Multiple output formats** (pretty, JSON, simple)
- **Category filtering** (general, it, videos, etc.)
- **Engine selection** (specific search engines)
- **Language support** for internationalized results
- **Error handling** with informative messages
- **No external dependencies** (uses Python standard library only)

## Quick Start

### 1. Make sure SearXNG is running

```bash
# Start your SearXNG instance
docker compose up -d

# Verify it's running
docker compose ps
```

### 2. Basic usage

```bash
# Simple search
python searxng_search.py "python programming"

# Search with specific categories
python searxng_search.py "docker compose" --categories general,it

# Get JSON output
python searxng_search.py "machine learning" --format json --output json
```

## Usage Examples

### Basic Searches

```bash
# Simple text search
python searxng_search.py "artificial intelligence"

# Search with quotes for exact phrases
python searxng_search.py '"machine learning algorithms"'

# Search with multiple terms
python searxng_search.py "python flask docker deployment"
```

### Category Filtering

```bash
# Search only in general category
python searxng_search.py "news" --categories general

# Search in multiple categories
python searxng_search.py "programming" --categories general,it

# Available categories: general, it, files, images, videos, music, map, news, science, social media
```

### Engine Selection

```bash
# Use only specific engines
python searxng_search.py "github" --engines github

# Use multiple engines
python searxng_search.py "stackoverflow" --engines github,stackoverflow

# List all available engines
python searxng_search.py --list-engines
```

### Output Formats

```bash
# Pretty formatted output (default)
python searxng_search.py "python" --output pretty

# Simple format
python searxng_search.py "python" --output simple

# Raw JSON output
python searxng_search.py "python" --output json
```

### Advanced Options

```bash
# Custom SearXNG instance
python searxng_search.py "test" --base-url https://search.example.com

# Different language
python searxng_search.py "hello" --language es

# Custom timeout
python searxng_search.py "slow query" --timeout 60
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `query` | Search query string (required) | - |
| `--base-url` | SearXNG instance URL | Uses SEARXNG_PROTOCOL, SEARXNG_HOST, SEARXNG_PORT env vars |
| `--format` | Response format (html/json) | `json` |
| `--output` | Output format (pretty/json/simple) | `pretty` |
| `--categories` | Comma-separated categories | All |
| `--engines` | Comma-separated engines | All |
| `--language` | Language code | `en` |
| `--timeout` | Request timeout (seconds) | `30` |
| `--list-engines` | List available engines | - |

## Integration Examples

### Python Script Integration

```python
from searxng_search import SearXNGClient

# Initialize client (uses environment variables by default)
client = SearXNGClient()

# Perform search
results = client.search("python programming", categories=["general", "it"])

# Process results
if 'error' not in results:
    for result in results.get('results', []):
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Content: {result['content'][:200]}...")
        print("-" * 40)
else:
    print(f"Error: {results['error']}")
```

### Shell Script Integration

```bash
#!/bin/bash

# Search and save results to file
python searxng_search.py "docker compose" --output json > results.json

# Search and process with jq
python searxng_search.py "python" --output json | jq '.results[0].title'

# Search and count results
python searxng_search.py "machine learning" --output json | jq '.results | length'
```

### Batch Processing

```bash
#!/bin/bash

# Search multiple queries
queries=("python programming" "docker compose" "machine learning")

for query in "${queries[@]}"; do
    echo "Searching: $query"
    python searxng_search.py "$query" --output simple
    echo "=========================================="
done
```

## Error Handling

The script handles various error conditions:

- **Connection errors**: When SearXNG is not running
- **HTTP errors**: Invalid responses from SearXNG
- **Timeout errors**: When requests take too long
- **JSON parsing errors**: When response format is invalid

Example error output:
```
Error: HTTP Error 404: Not Found
Error: URL Error: [Errno 61] Connection refused
Error: JSON Decode Error: Expecting value: line 1 column 1 (char 0)
```

## Troubleshooting

### Common Issues

1. **Connection refused**: SearXNG is not running
   ```bash
   docker compose up -d
   ```

2. **404 Not Found**: Wrong base URL or environment variables
   ```bash
   # Check environment variables
   echo $SEARXNG_PROTOCOL $SEARXNG_HOST $SEARXNG_PORT
   
   # Or specify base URL explicitly
   python searxng_search.py "test" --base-url http://localhost:7777
   ```

3. **Timeout errors**: SearXNG is slow or overloaded
   ```bash
   python searxng_search.py "test" --timeout 60
   ```

4. **No results**: Try different categories or engines
   ```bash
   python searxng_search.py "test" --categories general
   python searxng_search.py --list-engines
   ```

### Debug Mode

For debugging, you can modify the script to add verbose output:

```python
# Add this to the search method for debugging
print(f"Request URL: {url}")
print(f"Response status: {response.status}")
```

## Performance Tips

1. **Use specific categories** to reduce search time
2. **Limit engines** for faster results
3. **Use appropriate timeouts** for your network
4. **Cache results** for repeated queries

## Security Notes

- The script uses standard HTTP libraries
- No authentication is implemented (SearXNG is typically public)
- Be cautious when using custom base URLs
- Consider rate limiting for automated usage

## License

This script is provided as-is for use with your SearXNG instance.
