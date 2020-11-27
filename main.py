import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import urllib3
from bs4 import BeautifulSoup

import db

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


def fetch_title(proxy: urllib3.ProxyManager, title_id) -> dict:
    url = f"https://mangadex.org/api/v2/manga/{title_id}"
    rowid = db.run_sql(
        "INSERT INTO scrape (proxy, url) VALUES (?, ?)",
        (proxy.proxy_url, url),
        return_last_insert_rowid=True,
    )

    resp = proxy.request("GET", url)
    assert resp.status in [200, 404], resp.data
    title = json.loads(resp.data)

    db.run_sql(
        """
        UPDATE scrape
        SET resp_status = ?,
            resp_body = ?,
            ended_at = datetime('now')
        WHERE id = ?;
        """,
        (resp.status, resp.data, rowid),
    )
    print("Saved", title["data"]["title"])


def main():
    print("Migrating db")
    db.migrate()

    print("Fetching proxy list")
    unchecked_proxies = fetch_proxy_list()

    print("Checking proxies")
    working_proxies = check_proxies(unchecked_proxies)

    print(f"Found {len(working_proxies)} working proxies:")
    for pr in working_proxies:
        print(pr)

    proxy_managers = []
    for pr in working_proxies:
        pm = urllib3.ProxyManager(pr, headers=default_headers)
        pm.proxy_url = pr
        proxy_managers.append(pm)

    fetch_title(proxy_managers[0], 8)


if __name__ == "__main__":
    main()
