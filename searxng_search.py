#!/usr/bin/env python3
"""
SearXNG Search Client - A comprehensive Python client for SearXNG search engine.

This module provides a robust, feature-rich Python client for interacting with
SearXNG instances. It offers both programmatic API access and command-line
interface capabilities for searching across multiple engines and categories.

Key Features:
    - Full SearXNG API compatibility with support for all search parameters
    - Multiple output formats (JSON, HTML, pretty-printed, simple)
    - Configurable search categories and specific engine selection
    - Comprehensive error handling and logging
    - Environment-based configuration with .env file support
    - Command-line interface with extensive options
    - Type hints throughout for better IDE support and maintainability

Configuration:
    The client can be configured via environment variables or .env file:
    - SEARXNG_PROTOCOL: Protocol (http/https, default: http)
    - SEARXNG_HOST: Hostname (default: localhost)
    - SEARXNG_PORT: Port number (default: 7777)
    
    Create a .env file with your configuration (see env.example for template).

Usage Examples:
    # Basic search
    python searxng_search.py "python programming"
    
    # JSON output with specific categories
    python searxng_search.py "docker compose" --format json --categories general,it
    
    # Use specific search engines
    python searxng_search.py "github" --engines github,stackoverflow
    
    # Custom SearXNG instance
    python searxng_search.py "test" --base-url https://search.example.com
    
    # List available engines
    python searxng_search.py --list-engines

Programmatic Usage:
    from searxng_search import SearXNGClient
    
    client = SearXNGClient(base_url="http://localhost:7777")
    results = client.search("python programming", categories=["general"])
    print(format_results(results, "pretty"))
"""

# Standard library imports for core functionality
import argparse          # Command-line argument parsing
import json             # JSON data serialization/deserialization
import logging          # Application logging and debugging
import os               # Operating system interface for environment variables
import sys              # System-specific parameters and functions
import time             # Time-related functions for performance measurement
import urllib.parse     # URL parsing and encoding utilities
import urllib.request   # HTTP client functionality for web requests

# Type hinting imports for better code documentation and IDE support
from typing import Dict, List, Optional, Any, Union

# Optional dependency for .env file support
# Gracefully handle missing python-dotenv package
try:
    from dotenv import load_dotenv
    load_dotenv()  # Automatically load environment variables from .env file
except ImportError:
    # python-dotenv not installed - continue without .env file support
    # This allows the script to work in environments without the optional dependency
    pass

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Network and HTTP configuration
DEFAULT_TIMEOUT = 30  # Default HTTP request timeout in seconds
                      # Prevents hanging requests and provides reasonable timeout for search operations

DEFAULT_USER_AGENT = "SearXNG-Python-Client/1.0"  # User-Agent string for HTTP requests
                                                   # Helps identify this client to SearXNG instances
                                                   # Some instances may use this for rate limiting or analytics

# Content display limits for different output formats
MAX_CONTENT_PREVIEW = 200    # Maximum characters to show in simple output format
                             # Keeps simple output concise while showing essential content

MAX_DETAILED_CONTENT = 300   # Maximum characters to show in pretty output format
                             # Provides more detail than simple format while preventing excessive output

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Configure application-wide logging
# Uses INFO level to provide useful operational information without being verbose
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)  # Create logger instance for this module


class SearXNGClient:
    """
    A comprehensive client for interacting with SearXNG search engine instances.
    
    This class provides a robust interface for performing searches, retrieving
    engine information, and managing connections to SearXNG instances. It handles
    all aspects of HTTP communication, error handling, and response processing.
    
    The client supports all major SearXNG features including:
    - Multi-category searches (general, images, videos, news, etc.)
    - Specific search engine selection
    - Language-specific searches
    - Multiple output formats (JSON, HTML)
    - Configurable timeouts and connection settings
    
    Attributes:
        base_url (str): The base URL of the SearXNG instance
        timeout (int): HTTP request timeout in seconds
        search_url (str): Complete URL for search requests
        
    Example:
        >>> client = SearXNGClient(base_url="http://localhost:7777")
        >>> results = client.search("python programming", categories=["general"])
        >>> print(f"Found {len(results.get('results', []))} results")
        
    Note:
        The client automatically constructs the base URL from environment
        variables if not provided during initialization. See module docstring
        for environment variable configuration details.
    """
    
    def __init__(self, base_url: str = None, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize a new SearXNG client instance.
        
        Creates a client configured to connect to a specific SearXNG instance.
        If no base URL is provided, the client will attempt to construct one from
        environment variables (SEARXNG_PROTOCOL, SEARXNG_HOST, SEARXNG_PORT).
        
        Args:
            base_url (str, optional): Complete base URL of the SearXNG instance.
                Should include protocol (http/https) and port if not standard.
                Example: "https://search.example.com:8080"
                If None, constructs URL from environment variables.
            timeout (int, optional): HTTP request timeout in seconds.
                Defaults to DEFAULT_TIMEOUT (30 seconds).
                Prevents hanging requests and provides reasonable timeout for searches.
                
        Raises:
            ValueError: If the provided base_url is invalid or malformed.
                Specifically raised when base_url doesn't start with http:// or https://.
                
        Example:
            >>> # Using explicit URL
            >>> client = SearXNGClient("https://search.example.com")
            >>> 
            >>> # Using environment variables
            >>> client = SearXNGClient()  # Uses SEARXNG_* env vars
            >>> 
            >>> # Custom timeout
            >>> client = SearXNGClient(timeout=60)
        """
        # Construct base URL from environment variables if not provided
        if base_url is None:
            # Read configuration from environment variables with sensible defaults
            protocol = os.environ.get('SEARXNG_PROTOCOL', 'http')  # Default to HTTP for local instances
            host = os.environ.get('SEARXNG_HOST', 'localhost')     # Default to localhost
            port = os.environ.get('SEARXNG_PORT', '7777')          # Default SearXNG port
            base_url = f"{protocol}://{host}:{port}"
        
        # Validate that the URL uses a supported protocol
        if not base_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid base URL: {base_url}. Must start with http:// or https://")
        
        # Store configuration and construct search endpoint URL
        self.base_url = base_url.rstrip('/')  # Remove trailing slash for consistency
        self.timeout = timeout                # Store timeout for HTTP requests
        self.search_url = f"{self.base_url}/search"  # Construct search endpoint URL
        
        # Log successful initialization for debugging and monitoring
        logger.info(f"Initialized SearXNG client for {self.base_url}")
    
    def search(self, 
               query: str, 
               categories: Optional[List[str]] = None,
               engines: Optional[List[str]] = None,
               language: str = "en",
               format: str = "json") -> Dict[str, Any]:
        """
        Perform a search query against the SearXNG instance.
        
        Executes a search request with the specified parameters and returns
        formatted results. Supports all major SearXNG search features including
        category filtering, engine selection, and language preferences.
        
        Args:
            query (str): The search query string to execute.
                Can contain multiple terms, phrases, or search operators.
                Example: "python programming tutorial"
                
            categories (List[str], optional): List of search categories to include.
                Common categories: 'general', 'images', 'videos', 'news', 'it', 'science'.
                If None, searches all available categories.
                Example: ['general', 'it']
                
            engines (List[str], optional): List of specific search engines to use.
                Overrides category selection and uses only specified engines.
                Engine names vary by SearXNG instance configuration.
                Example: ['google', 'bing', 'duckduckgo']
                
            language (str, optional): Language code for search results.
                Uses ISO 639-1 language codes (e.g., 'en', 'es', 'fr').
                Defaults to 'en' (English).
                
            format (str, optional): Response format from SearXNG.
                'json': Returns structured JSON data (default, recommended)
                'html': Returns raw HTML response
                Defaults to 'json'.
                
        Returns:
            Dict[str, Any]: Search results dictionary containing:
                - 'results': List of search result objects
                - 'query': The original search query
                - 'number_of_results': Total number of results found
                - 'engines': List of engines used for the search
                - 'error': Error message (if request failed)
                
        Raises:
            No exceptions are raised - errors are returned in the result dictionary
            under the 'error' key for graceful error handling.
            
        Example:
            >>> client = SearXNGClient()
            >>> results = client.search("python tutorial", categories=["general", "it"])
            >>> if 'error' not in results:
            ...     print(f"Found {len(results['results'])} results")
            ...     for result in results['results'][:3]:
            ...         print(f"- {result['title']}")
        """
        # Log the search query for debugging and monitoring
        logger.info(f"Searching for: '{query}'")
        
        # Build the search parameters dictionary
        # These parameters are sent to the SearXNG API
        params = {
            'q': query,           # The search query string
            'format': format,     # Response format (json/html)
            'lang': language      # Language code for results
        }
        
        # Add category filtering if specified
        # Categories are comma-separated in the API
        if categories:
            params['categories'] = ','.join(categories)
        
        # Add engine filtering if specified
        # Engines are comma-separated in the API
        if engines:
            params['engines'] = ','.join(engines)
        
        # Construct the complete search URL with query parameters
        # urllib.parse.urlencode handles proper URL encoding of parameters
        url = f"{self.search_url}?{urllib.parse.urlencode(params)}"
        
        try:
            # Create HTTP request with proper headers
            request = urllib.request.Request(url)
            request.add_header('User-Agent', DEFAULT_USER_AGENT)  # Identify this client
            
            # Execute the HTTP request with timeout
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                # Read and decode the response content
                content = response.read().decode('utf-8')
                
                # Process response based on requested format
                if format == 'json':
                    # Parse JSON response into Python dictionary
                    return json.loads(content)
                else:
                    # Return raw HTML content with metadata
                    return {
                        'content': content,
                        'status_code': response.status,
                        'headers': dict(response.headers)
                    }
                    
        # Handle specific HTTP errors (4xx, 5xx status codes)
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
            return {'error': f"HTTP Error {e.code}: {e.reason}"}
        # Handle network/connection errors
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason}")
            return {'error': f"URL Error: {e.reason}"}
        # Handle JSON parsing errors (malformed response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {str(e)}")
            return {'error': f"JSON Decode Error: {str(e)}"}
        # Handle any other unexpected errors
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {'error': f"Unexpected error: {str(e)}"}
    
    def get_engines(self) -> Dict[str, Any]:
        """
        Retrieve information about available search engines from the SearXNG instance.
        
        Fetches the list of configured search engines and their metadata from
        the SearXNG instance. This is useful for discovering which engines
        are available for use in search queries.
        
        Returns:
            Dict[str, Any]: Dictionary containing engine information:
                - Keys: Engine names (e.g., 'google', 'bing', 'duckduckgo')
                - Values: Engine metadata including description, categories, etc.
                - 'error': Error message if the request failed
                
        Example:
            >>> client = SearXNGClient()
            >>> engines = client.get_engines()
            >>> if 'error' not in engines:
            ...     for name, info in engines.items():
            ...         print(f"{name}: {info.get('description', 'No description')}")
            ... else:
            ...     print(f"Error: {engines['error']}")
            
        Note:
            Engine names and metadata vary by SearXNG instance configuration.
            Some engines may be disabled or require specific setup.
        """
        try:
            # Construct URL for the engines endpoint
            url = f"{self.base_url}/engines"
            
            # Make HTTP request to get engine information
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                # Parse JSON response containing engine metadata
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            # Return error information instead of raising exception
            # This allows graceful handling of network issues or API changes
            return {'error': f"Failed to get engines: {str(e)}"}


def format_results(results: Dict[str, Any], output_format: str = "pretty") -> str:
    """
    Format search results for human-readable display or structured output.
    
    Takes raw search results from SearXNG and formats them according to the
    specified output format. Supports multiple display styles optimized for
    different use cases (CLI display, JSON export, simple text).
    
    Args:
        results (Dict[str, Any]): Search results dictionary from SearXNG API.
            Expected keys:
            - 'results': List of search result objects
            - 'query': Original search query
            - 'number_of_results': Total results count
            - 'error': Error message (if search failed)
            
        output_format (str, optional): Desired output format.
            'pretty': Human-readable format with full details (default)
            'json': Pretty-printed JSON for programmatic use
            'simple': Minimal format with essential information only
            Defaults to 'pretty'.
            
    Returns:
        str: Formatted string representation of the search results.
            Format depends on output_format parameter:
            - 'pretty': Multi-line formatted text with separators
            - 'json': Indented JSON string
            - 'simple': Concise text format
            
    Example:
        >>> results = {'results': [{'title': 'Python Tutorial', 'url': 'https://example.com'}]}
        >>> print(format_results(results, 'simple'))
        Title: Python Tutorial
        URL: https://example.com
        Content: N/A
        --------------------------------------------------
        
    Note:
        Content is automatically truncated based on MAX_CONTENT_PREVIEW and
        MAX_DETAILED_CONTENT constants to prevent excessive output.
    """
    # Handle error cases first - return error message immediately
    if 'error' in results:
        return f"Error: {results['error']}"
    
    # JSON output format - return pretty-printed JSON for programmatic use
    if output_format == "json":
        return json.dumps(results, indent=2, ensure_ascii=False)
    
    # Validate that results contain the expected structure
    if 'results' not in results:
        return "No results found or invalid response format."
    
    # Simple output format - minimal information for quick scanning
    if output_format == "simple":
        output = []
        for result in results['results']:
            # Extract and display essential information
            output.append(f"Title: {result.get('title', 'N/A')}")
            output.append(f"URL: {result.get('url', 'N/A')}")
            
            # Truncate content to prevent excessive output
            content = result.get('content', 'N/A')
            if len(content) > MAX_CONTENT_PREVIEW:
                content = content[:MAX_CONTENT_PREVIEW] + "..."
            output.append(f"Content: {content}")
            output.append("-" * 50)  # Separator between results
        return "\n".join(output)
    
    # Pretty output format - comprehensive display with full details
    output = []
    
    # Display search metadata
    output.append(f"Query: {results.get('query', 'N/A')}")
    output.append(f"Number of results: {len(results.get('results', []))}")
    output.append(f"Search time: {results.get('number_of_results', 0)} results")
    output.append("=" * 60)  # Header separator
    
    # Display each search result with detailed information
    for i, result in enumerate(results.get('results', []), 1):
        output.append(f"\n{i}. {result.get('title', 'N/A')}")
        output.append(f"   URL: {result.get('url', 'N/A')}")
        output.append(f"   Engine: {result.get('engine', 'N/A')}")
        
        # Display content if available, with truncation for readability
        if result.get('content'):
            content = result['content']
            if len(content) > MAX_DETAILED_CONTENT:
                content = content[:MAX_DETAILED_CONTENT] + "..."
            output.append(f"   Content: {content}")
        output.append("-" * 40)  # Separator between results
    
    return "\n".join(output)


def main():
    """
    Main entry point for the SearXNG search client command-line interface.
    
    Parses command-line arguments, initializes the SearXNG client, and executes
    the requested search operation. Handles both search queries and engine
    listing functionality with comprehensive error handling and user feedback.
    
    Command-line arguments are processed using argparse with extensive help
    text and examples. The function supports all major SearXNG features
    including category filtering, engine selection, and multiple output formats.
    
    Returns:
        None: Output is printed to stdout, errors to stderr
        
    Exit codes:
        0: Successful execution
        1: Error occurred (network issues, invalid configuration, etc.)
        
    Example usage from command line:
        python searxng_search.py "python tutorial" --categories general,it
        python searxng_search.py --list-engines
        python searxng_search.py "docker" --output json --base-url https://search.example.com
    """
    # Configure command-line argument parser with comprehensive help
    parser = argparse.ArgumentParser(
        description="Query SearXNG search engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,  # Preserve formatting in help text
        epilog="""
Examples:
  %(prog)s "python programming"
  %(prog)s "docker compose" --format json
  %(prog)s "machine learning" --categories general,it
  %(prog)s "github" --engines github,stackoverflow
  %(prog)s "test query" --output pretty --base-url https://search.example.com
        """
    )
    
    # Define command-line arguments with detailed help text
    parser.add_argument('query', help='Search query string')
    parser.add_argument('--base-url', default=None, 
                       help='Base URL of SearXNG instance (default: uses SEARXNG_PROTOCOL, SEARXNG_HOST, SEARXNG_PORT env vars or .env file)')
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
    
    # Parse command-line arguments
    args = parser.parse_args()
    
    # Initialize SearXNG client with user-specified configuration
    client = SearXNGClient(base_url=args.base_url, timeout=args.timeout)
    
    # Handle special case: list available search engines
    if args.list_engines:
        engines = client.get_engines()
        if 'error' in engines:
            print(f"Error getting engines: {engines['error']}")
            sys.exit(1)  # Exit with error code for script automation
        
        # Display available engines with descriptions
        print("Available search engines:")
        for engine_name, engine_info in engines.items():
            print(f"  {engine_name}: {engine_info.get('description', 'No description')}")
        return  # Exit successfully after listing engines
    
    # Parse comma-separated lists from command-line arguments
    categories = args.categories.split(',') if args.categories else None
    engines = args.engines.split(',') if args.engines else None
    
    # Display search parameters for user feedback
    print(f"Searching for: '{args.query}'")
    if categories:
        print(f"Categories: {', '.join(categories)}")
    if engines:
        print(f"Engines: {', '.join(engines)}")
    print("-" * 50)  # Visual separator
    
    # Execute search and measure performance
    start_time = time.time()
    results = client.search(
        query=args.query,
        categories=categories,
        engines=engines,
        language=args.language,
        format=args.format
    )
    search_time = time.time() - start_time
    
    # Format and display results according to user preference
    formatted_output = format_results(results, args.output)
    print(formatted_output)
    
    # Display performance information for successful searches
    if 'error' not in results:
        print(f"\nSearch completed in {search_time:.2f} seconds")


# Script entry point - only execute main() when run directly
# This allows the module to be imported without executing the CLI
if __name__ == "__main__":
    main()
