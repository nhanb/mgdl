from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import urllib3
from bs4 import BeautifulSoup

default_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
}


def fetch_proxy_list() -> List[str]:
    client = urllib3.PoolManager(headers=default_headers)

    resp = client.request("GET", "https://www.sslproxies.org/")
    soup = BeautifulSoup(resp.data, "html.parser")
    txt = soup.find("textarea").text.strip()
    # TODO: use https once urllib3 is updated on arch:
    # https://github.com/urllib3/urllib3/issues/1850
    return ["http://" + line for line in txt.split("\n")[3:]]


def check_proxy(addr: str) -> bool:
    proxy = urllib3.ProxyManager(addr, headers=default_headers)
    try:
        ping = proxy.request(
            "GET",
            "https://hi.imnhan.com/ping.html",
            timeout=5,
            retries=False,
        )
        return ping.status == 200
    except urllib3.exceptions.HTTPError:
        return False


def check_proxies(addrs: List[str]) -> List[str]:
    working_addrs = []
    with ThreadPoolExecutor(max_workers=40) as executor:
        future_to_addr = {executor.submit(check_proxy, addr): addr for addr in addrs}
        for future in as_completed(future_to_addr):
            addr = future_to_addr[future]
            if future.result():
                working_addrs.append(addr)
    return working_addrs


def main():
    print("Fetching proxy list")
    unchecked_proxies = fetch_proxy_list()

    print("Checking proxies")
    working_proxies = check_proxies(unchecked_proxies)

    print(f"Found {len(working_proxies)} working proxies:")
    for pr in working_proxies:
        print(pr)


if __name__ == "__main__":
    main()
