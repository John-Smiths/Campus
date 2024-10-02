from os import system
from urllib.parse import quote, urlparse, urlunparse

def escape_url（url）：
    # 用于转义
    system（f'curl -o db/{name}.jpg “{url}”'）
    
    query_params = parsed_url.query
    escaped_query_params = []
    
    for param in query_params.split('&'):
        if '=' in param:
            key，值 = param。split（'='， 1）
            escaped_query_params.append(f"{quote(key)}={quote(value)}")
        else:
            escaped_query_params.append(quote(param))
    
    escaped_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        '&'.join(escaped_query_params),
        parsed_url.fragment
    ))
    
    return escaped_url

def download(url, name):
    print("command", "-" * 20, ">", f'curl -o db/{name}.jpg "escape_url(url)"')
    system(f'curl -o db/{name}.jpg "{url}"')
