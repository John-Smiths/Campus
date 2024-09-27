from os import system

def download(url, name):
    print("command", "-" * 20, ">", f'curl -o db/{name}.jpg "{url}"')
    system(f'curl -o db/{name}.jpg "{url}"')
