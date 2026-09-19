from urllib.parse import urlsplit, urlunsplit, quote

def encode_chinese_url(url_with_chinese: str) -> str:
    """
    Converts a URL containing Chinese characters in its path to a URL-encoded format.

    Args:
        url_with_chinese: The original URL string with Chinese characters.

    Returns:
        The URL-encoded string.
    """
    # Split the URL into its components: scheme, netloc, path, query, fragment
    parts = urlsplit(url_with_chinese)

    # Encode the path component.
    # The 'safe' parameter ensures that characters like '/' are not encoded.
    encoded_path = quote(parts.path, safe='/')

    # Reassemble the URL with the encoded path
    encoded_url = urlunsplit((parts.scheme, parts.netloc, encoded_path, parts.query, parts.fragment))

    return encoded_url
