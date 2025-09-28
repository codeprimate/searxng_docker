#!/usr/bin/env python3
"""
SearXNG Query Script

A Python script to query a running SearXNG instance and return search results.
This script can be used to programmatically search using SearXNG.

Usage:
    python searxng_search.py "your search query"
    python searxng_search.py "python programming" --format json
    python searxng_search.py "docker compose" --categories general,it
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Any
import time


class SearXNGClient:
    """Client for interacting with SearXNG search engine."""
    
    def __init__(self, base_url: str = "http://localhost:7777", timeout: int = 30):
        """
        Initialize the SearXNG client.
        
        Args:
            base_url: Base URL of the SearXNG instance
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.search_url = f"{self.base_url}/search"
    
    def search(self, 
               query: str, 
               categories: Optional[List[str]] = None,
               engines: Optional[List[str]] = None,
               language: str = "en",
               format: str = "html") -> Dict[str, Any]:
        """
        Perform a search query.
        
        Args:
            query: Search query string
            categories: List of categories to search (e.g., ['general', 'it'])
            engines: List of specific engines to use
            language: Language code for results
            format: Output format ('html' or 'json')
            
        Returns:
            Dictionary containing search results and metadata
        """
        # Prepare search parameters
        params = {
            'q': query,
            'format': format,
            'lang': language
        }
        
        if categories:
            params['categories'] = ','.join(categories)
        
        if engines:
            params['engines'] = ','.join(engines)
        
        # Build URL with parameters
        url = f"{self.search_url}?{urllib.parse.urlencode(params)}"
        
        try:
            # Make the request
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content = response.read().decode('utf-8')
                
                if format == 'json':
                    return json.loads(content)
                else:
                    return {
                        'content': content,
                        'status_code': response.status,
                        'headers': dict(response.headers)
                    }
                    
        except urllib.error.HTTPError as e:
            return {
                'error': f"HTTP Error {e.code}: {e.reason}",
                'status_code': e.code
            }
        except urllib.error.URLError as e:
            return {
                'error': f"URL Error: {e.reason}",
                'status_code': None
            }
        except json.JSONDecodeError as e:
            return {
                'error': f"JSON Decode Error: {str(e)}",
                'content': content
            }
        except Exception as e:
            return {
                'error': f"Unexpected error: {str(e)}",
                'status_code': None
            }
    
    def get_engines(self) -> Dict[str, Any]:
        """Get available search engines."""
        try:
            url = f"{self.base_url}/engines"
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {'error': f"Failed to get engines: {str(e)}"}


def format_results(results: Dict[str, Any], output_format: str = "pretty") -> str:
    """
    Format search results for display.
    
    Args:
        results: Search results dictionary
        output_format: Output format ('pretty', 'json', 'simple')
        
    Returns:
        Formatted string of results
    """
    if 'error' in results:
        return f"Error: {results['error']}"
    
    if output_format == "json":
        return json.dumps(results, indent=2, ensure_ascii=False)
    
    if 'results' not in results:
        return "No results found or invalid response format."
    
    if output_format == "simple":
        output = []
        for result in results['results']:
            output.append(f"Title: {result.get('title', 'N/A')}")
            output.append(f"URL: {result.get('url', 'N/A')}")
            output.append(f"Content: {result.get('content', 'N/A')[:200]}...")
            output.append("-" * 50)
        return "\n".join(output)
    
    # Pretty format
    output = []
    output.append(f"Query: {results.get('query', 'N/A')}")
    output.append(f"Number of results: {len(results.get('results', []))}")
    output.append(f"Search time: {results.get('number_of_results', 0)} results")
    output.append("=" * 60)
    
    for i, result in enumerate(results.get('results', []), 1):
        output.append(f"\n{i}. {result.get('title', 'N/A')}")
        output.append(f"   URL: {result.get('url', 'N/A')}")
        output.append(f"   Engine: {result.get('engine', 'N/A')}")
        if result.get('content'):
            content = result['content'][:300]
            output.append(f"   Content: {content}...")
        output.append("-" * 40)
    
    return "\n".join(output)


def main():
    """Main function to handle command line arguments and execute search."""
    parser = argparse.ArgumentParser(
        description="Query SearXNG search engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "python programming"
  %(prog)s "docker compose" --format json
  %(prog)s "machine learning" --categories general,it
  %(prog)s "github" --engines github,stackoverflow
  %(prog)s "test query" --output pretty --base-url https://search.example.com
        """
    )
    
    parser.add_argument('query', help='Search query string')
    parser.add_argument('--base-url', default='http://localhost:7777', 
                       help='Base URL of SearXNG instance (default: http://localhost:7777)')
    parser.add_argument('--format', choices=['html', 'json'], default='json',
                       help='Response format (default: json)')
    parser.add_argument('--output', choices=['pretty', 'json', 'simple'], default='pretty',
                       help='Output format (default: pretty)')
    parser.add_argument('--categories', 
                       help='Comma-separated list of categories (e.g., general,it,videos)')
    parser.add_argument('--engines', 
                       help='Comma-separated list of engines to use')
    parser.add_argument('--language', default='en',
                       help='Language code (default: en)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Request timeout in seconds (default: 30)')
    parser.add_argument('--list-engines', action='store_true',
                       help='List available search engines and exit')
    
    args = parser.parse_args()
    
    # Initialize client
    client = SearXNGClient(base_url=args.base_url, timeout=args.timeout)
    
    # Handle list engines request
    if args.list_engines:
        engines = client.get_engines()
        if 'error' in engines:
            print(f"Error getting engines: {engines['error']}")
            sys.exit(1)
        
        print("Available search engines:")
        for engine_name, engine_info in engines.items():
            print(f"  {engine_name}: {engine_info.get('description', 'No description')}")
        return
    
    # Parse categories and engines
    categories = args.categories.split(',') if args.categories else None
    engines = args.engines.split(',') if args.engines else None
    
    # Perform search
    print(f"Searching for: '{args.query}'")
    print(f"Using SearXNG at: {args.base_url}")
    if categories:
        print(f"Categories: {', '.join(categories)}")
    if engines:
        print(f"Engines: {', '.join(engines)}")
    print("-" * 50)
    
    start_time = time.time()
    results = client.search(
        query=args.query,
        categories=categories,
        engines=engines,
        language=args.language,
        format=args.format
    )
    search_time = time.time() - start_time
    
    # Format and display results
    formatted_output = format_results(results, args.output)
    print(formatted_output)
    
    if 'error' not in results:
        print(f"\nSearch completed in {search_time:.2f} seconds")


if __name__ == "__main__":
    main()
