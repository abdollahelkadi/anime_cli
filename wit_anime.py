#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
import sys
import readchar
import webbrowser
import base64
import re
import json
from urllib.parse import urlparse

class AnimeWatcher:
    def __init__(self):
        self.console = Console()

    def get_anime_search_results(self, query):
        url = f"https://witanime.cyou/?search_param=animes&s={query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for card in soup.select("div.anime-card-container"):
            title_tag = card.select_one("div.anime-card-title h3 a")
            if not title_tag:
                continue
            title = title_tag.text.strip()
            anime_url = title_tag["href"]
            results.append({"title": title, "url": anime_url})
        return results

    def print_menu(self, anime_list, selected_index):
        print("\033[H\033[J", end="")  # Clear screen without blinking
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("No.", style="dim", width=4)
        table.add_column("Anime Title", style="bold white")
        for idx, anime in enumerate(anime_list):
            no = str(idx+1)
            title = anime["title"]
            if idx == selected_index:
                table.add_row(f"[bright_green]> {no}[/bright_green]", f"[bold reverse yellow]{title}[/]")
            else:
                table.add_row(f"[bright_green]  {no}[/bright_green]", title)
        self.console.print(table)
        self.console.print(f"\nUse [bold magenta]↑[/]/[bold magenta]↓[/] arrows to select, [bold yellow]g[/bold yellow] to jump, [bold green]Enter[/] to show episodes, [bold red]q[/] to exit.")

    def select_anime(self, anime_list):
        selected = 0
        self.print_menu(anime_list, selected)
        while True:
            key = readchar.readkey()
            if key in (readchar.key.UP, "k"):
                selected = (selected - 1) % len(anime_list)
                self.print_menu(anime_list, selected)
            elif key in (readchar.key.DOWN, "j"):
                selected = (selected + 1) % len(anime_list)
                self.print_menu(anime_list, selected)
            elif key.lower() == 'g':
                try:
                    num = int(Prompt.ask("Go to anime number")) - 1
                    if 0 <= num < len(anime_list):
                        selected = num
                        self.print_menu(anime_list, selected)
                except Exception:
                    pass
            elif key in (readchar.key.ENTER, "\r", "\n"):
                return selected
            elif key in ("q", readchar.key.CTRL_C):
                sys.exit(0)

    def decode_episodes(self, encoded_string):
        try:
            if '.' in encoded_string:
                b64_data, b64_key = encoded_string.split('.')
                decoded_data = base64.b64decode(b64_data)
                decoded_key = base64.b64decode(b64_key)
                decrypted_bytes = bytearray()
                key_len = len(decoded_key)
                for i, byte in enumerate(decoded_data):
                    decrypted_byte = byte ^ decoded_key[i % key_len]
                    decrypted_bytes.append(decrypted_byte)
                json_string = decrypted_bytes.decode('utf-8')
                return json.loads(json_string)
            else:
                decoded = base64.b64decode(encoded_string).decode("utf-8", errors="ignore")
                soup = BeautifulSoup(decoded, "html.parser")
                episodes = []
                for div in soup.select("div.DivEpisodeContainer"):
                    a = div.find("a", onclick=True)
                    if not a:
                        continue
                    ep_title = a.text.strip()
                    onclick_val = a.get("onclick", "")
                    m2 = re.search(r"openEpisode\('([^']+)'", onclick_val)
                    if not m2:
                        continue
                    b64_url = m2.group(1)
                    try:
                        ep_url = base64.b64decode(b64_url).decode("utf-8")
                    except Exception:
                        ep_url = b64_url
                    episodes.append({"title": ep_title, "url": ep_url})
                return episodes
        except Exception as e:
            self.console.print(f"[red]Failed to decode episodes: {e}[/red]")
            return []

    def get_episodes_list(self, anime_url):
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(anime_url, headers=headers)
        resp.raise_for_status()
        page_html = resp.text

        m = re.search(r"processedEpisodeData\s*=\s*'([^']+)'", page_html)
        if not m:
            self.console.print("[red]No processedEpisodeData variable found![/red]")
            return []
        encoded_string = m.group(1)
        episodes = self.decode_episodes(encoded_string)
        result = []
        for idx, ep in enumerate(episodes):
            if isinstance(ep, dict) and "number" in ep and "url" in ep:
                ep_title = f"Episode {ep['number']}"
                ep_url = ep["url"]
            else:
                ep_title = ep.get("title", f"Episode {idx+1}")
                ep_url = ep.get("url", "")
            result.append({"num": idx+1, "title": ep_title, "url": ep_url})
        return result

    def extract_dynamic_base64_vars(self, html):
        matches = re.findall(r'var\s+(\w+)\s*=\s*"([^"]{20,})"', html)
        decoded_vars = {}
        for name, val in matches:
            try:
                decoded = base64.b64decode(val)
                try:
                    obj = json.loads(decoded)
                    decoded_vars[name] = obj
                except Exception:
                    decoded_vars[name] = decoded
            except Exception:
                continue
        return decoded_vars

    def get_resource_config_vars(self, dynamic_vars):
        possible_arrays = [v for v in dynamic_vars.values() if isinstance(v, list)]
        res_var, conf_var = None, None
        for arr in possible_arrays:
            if all(isinstance(x, dict) and 'k' in x and 'd' in x for x in arr):
                conf_var = arr
            elif all(isinstance(x, str) for x in arr):
                res_var = arr
        if res_var and conf_var and len(res_var) == len(conf_var):
            return res_var, conf_var
        return None, None

    def extract_preview_servers_dynamic(self, soup, resourceRegistry, configRegistry):
        servers = []
        watch_section = soup.find("ul", id=re.compile("episode-servers", re.I))
        if not (resourceRegistry and configRegistry and watch_section):
            return []
        for a in watch_section.find_all("a", class_=re.compile("server-link", re.I)):
            label = ""
            span = a.find("span", class_=re.compile("ser", re.I))
            if span:
                label = span.text.strip()
            else:
                label = a.text.strip()
            server_id = a.get("data-server-id")
            url = "N/A"
            if (server_id and server_id.isdigit() and 
                int(server_id) < len(resourceRegistry) and 
                int(server_id) < len(configRegistry) and
                isinstance(configRegistry[int(server_id)], dict) and
                "k" in configRegistry[int(server_id)] and 
                "d" in configRegistry[int(server_id)]):
                idx = int(server_id)
                try:
                    reversed_str = resourceRegistry[idx][::-1]
                    b64_str = re.sub(r'[^A-Za-z0-9+/=]', '', reversed_str)
                    decoded_bytes = base64.b64decode(b64_str)
                    k_dec = int(base64.b64decode(configRegistry[idx]['k']).decode())
                    param_offset = configRegistry[idx]['d'][k_dec]
                    final_url = decoded_bytes[:-param_offset].decode()
                    url = final_url
                except Exception as e:
                    url = f"Error decoding: {e}"
            servers.append({"label": label, "server_id": server_id, "url": url})
        return servers

    def extract_preview_servers_html(self, soup):
        servers = []
        watch_section = soup.find("ul", id=re.compile("episode-servers", re.I))
        if watch_section:
            for a in watch_section.find_all("a", class_=re.compile("server-link", re.I)):
                label = ""
                span = a.find("span", class_=re.compile("ser", re.I))
                if span:
                    label = span.text.strip()
                else:
                    label = a.text.strip()
                server_id = a.get("data-server-id")
                servers.append({"label": label, "server_id": server_id, "url": None})
        return servers

    def xor_decrypt(self, hexstr, secret):
        b = bytes.fromhex(hexstr)
        secret_bytes = secret.encode("latin1")
        out = bytearray()
        for i, byte in enumerate(b):
            out.append(byte ^ secret_bytes[i % len(secret_bytes)])
        return out.decode("latin1")

    def find_js_var_dict(self, pattern, html):
        matches = re.finditer(pattern, html)
        arrs = {}
        for m in matches:
            idx = int(m.group(1))
            arrs[idx] = json.loads(m.group(2).replace("'", '"'))
        return arrs

    def get_server_name_from_url(self, url):
        if not url or url == "Index out of range" or url.startswith("Error decoding"):
            return url
        try:
            netloc = urlparse(url).netloc
            return netloc
        except Exception:
            return url

    def extract_download_links(self, html, soup):
        m_r = re.search(r'var\s+_m\s*=\s*\{"r"\s*:\s*"([^"]+)"\}', html)
        secret = None
        if m_r:
            secret = base64.b64decode(m_r.group(1)).decode("latin1")
        t_l = re.search(r'var\s+_t\s*=\s*\{"l"\s*:\s*"(\d+)"\}', html)
        l = int(t_l.group(1)) if t_l else 0
        p_arrays = self.find_js_var_dict(r'var\s+_p(\d+)\s*=\s*(\[[^\]]+\])', html)
        m_s = re.search(r'var\s+_s\s*=\s*(\[[^\]]+\]);', html)
        s_arrays = json.loads(m_s.group(1).replace("'", '"')) if m_s else []
        download_urls = []
        for idx in range(l):
            if idx not in p_arrays or idx >= len(s_arrays) or not secret:
                download_urls.append(None)
                continue
            chunks = p_arrays[idx]
            seqRaw = s_arrays[idx]
            try:
                seq_decrypted = self.xor_decrypt(seqRaw, secret)
                seq = json.loads(seq_decrypted)
                decrypted_chunks = [self.xor_decrypt(chunk, secret) for chunk in chunks]
                arranged = [None] * len(seq)
                for j, pos in enumerate(seq):
                    arranged[pos] = decrypted_chunks[j]
                url = "".join(arranged)
                download_urls.append(url)
            except Exception as e:
                download_urls.append(f"Error decoding: {e}")

        quality_map = {}
        for qlist in soup.find_all("ul", class_=re.compile("quality-list", re.I)):
            lis = qlist.find_all("li")
            if not lis: continue
            quality = lis[0].text.strip()
            for a in qlist.find_all("a", class_=re.compile("download-link", re.I)):
                data_index = a.get("data-index")
                if data_index is None or not data_index.isdigit():
                    continue
                data_index = int(data_index)
                label = a.find("span", class_=re.compile("notice", re.I)).text.strip()
                url = download_urls[data_index] if data_index < len(download_urls) else "Index out of range"
                name = self.get_server_name_from_url(url)
                if quality not in quality_map:
                    quality_map[quality] = []
                quality_map[quality].append({"name": name, "label": label, "url": url})
        return quality_map

    def get_episode_info(self, episode_url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(episode_url, headers=headers)
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract preview servers
            dynamic_vars = self.extract_dynamic_base64_vars(html)
            resourceRegistry, configRegistry = self.get_resource_config_vars(dynamic_vars)
            
            preview_servers = []
            if resourceRegistry and configRegistry:
                preview_servers = self.extract_preview_servers_dynamic(soup, resourceRegistry, configRegistry)
            else:
                preview_servers = self.extract_preview_servers_html(soup)

            # Extract download links
            quality_map = self.extract_download_links(html, soup)

            return {
                "preview_servers": preview_servers,
                "download_links": quality_map,
                "success": True
            }
        except Exception as e:
            return {
                "preview_servers": [],
                "download_links": {},
                "success": False,
                "error": str(e)
            }

    def display_episode_info(self, episode, episode_info):
        """Display both preview servers and download links"""
        self.console.clear()
        self.console.print(f"[bold cyan]{episode['title']}[/bold cyan]")
        self.console.print(f"[dim]URL: {episode['url']}[/dim]\n")

        if not episode_info["success"]:
            self.console.print(f"[red]Error extracting episode info: {episode_info.get('error', 'Unknown error')}[/red]")
            return

        # Display preview servers
        preview_servers = episode_info["preview_servers"]
        if preview_servers:
            self.console.print("[bold cyan]═══ Preview Watch Servers ═══[/bold cyan]")
            server_table = Table(show_header=True, header_style="bold cyan")
            server_table.add_column("Server", style="bright_green", width=20)
            server_table.add_column("URL", style="bright_blue")
            
            for server in preview_servers:
                url = server["url"] if server["url"] and "http" in str(server["url"]) else f"server-id: {server['server_id']}"
                server_table.add_row(server["label"], url)
            self.console.print(server_table)
        else:
            self.console.print("[yellow]No preview servers found.[/yellow]")

        # Display download links
        download_links = episode_info["download_links"]
        if download_links:
            self.console.print("\n[bold cyan]═══ Download Links ═══[/bold cyan]")
            for quality, links in download_links.items():
                self.console.print(f"\n[bold yellow]{quality}[/bold yellow]")
                download_table = Table(show_header=True, header_style="bold cyan")
                download_table.add_column("Server", style="bright_green", width=20)
                download_table.add_column("Type", style="bright_magenta", width=15)
                download_table.add_column("URL", style="bright_blue")
                
                for link in links:
                    download_table.add_row(link['name'], link['label'], link['url'])
                self.console.print(download_table)
        else:
            self.console.print("\n[yellow]No download links found for this episode.[/yellow]")

        self.console.print(f"\n[dim]Press Enter to continue...[/dim]")

    def episode_menu(self, episodes, page_size=30):
        total = len(episodes)
        if total == 0:
            self.console.print("[red]No episodes found.[/red]")
            Prompt.ask("Press Enter to exit.")
            sys.exit(0)
        page = 0
        selected = 0
        max_page = (total - 1) // page_size
        
        def render_episodes():
            print("\033[H\033[J", end="")
            start = page * page_size
            end = min(start + page_size, total)
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("No.", style="bright_green", width=6)
            table.add_column("Episode Title", style="bold white")
            
            for idx in range(start, end):
                ep = episodes[idx]
                num_str = str(ep["num"])
                episode_title = ep["title"]
                
                if idx == selected:
                    table.add_row(f"[bright_green]> {num_str}[/bright_green]", f"[bold reverse yellow]{episode_title}[/]")
                else:
                    table.add_row(f"[bright_green]  {num_str}[/bright_green]", episode_title)
            
            self.console.print(table)
            self.console.print(f"\nPage {page+1}/{max_page+1} | Episodes {start+1}-{end} of {total}")
            self.console.print("Use [bold magenta]↑[/]/[bold magenta]↓[/] to move, [bold magenta]←[/]/[bold magenta]→[/] for page, [bold yellow]g[/bold yellow] to jump")
            self.console.print("[bold green]Enter[/] to show URLs, [bold cyan]u[/bold cyan] for episode URL only, [bold red]q[/] to exit.")
        
        render_episodes()
        
        while True:
            key = readchar.readkey()
            if key in (readchar.key.UP, "k"):
                if selected > page * page_size:
                    selected -= 1
                    render_episodes()
                elif selected == page * page_size and page > 0:
                    page -= 1
                    selected = (page + 1) * page_size - 1
                    render_episodes()
            elif key in (readchar.key.DOWN, "j"):
                start = page * page_size
                end = min(start + page_size, total)
                if selected < end - 1:
                    selected += 1
                    render_episodes()
                elif selected == end - 1 and page < max_page:
                    page += 1
                    selected = page * page_size
                    render_episodes()
            elif key in (readchar.key.RIGHT, "l"):
                if page < max_page:
                    page += 1
                    selected = page * page_size
                    render_episodes()
            elif key in (readchar.key.LEFT, "h"):
                if page > 0:
                    page -= 1
                    selected = page * page_size
                    render_episodes()
            elif key.lower() == 'g':
                try:
                    num = int(Prompt.ask("Go to episode number"))
                    if 1 <= num <= total:
                        page = (num - 1) // page_size
                        selected = num - 1
                        render_episodes()
                except Exception:
                    pass
            elif key.lower() == 'u':
                # Show episode URL only
                ep = episodes[selected]
                self.console.print(f"\n[bold green]Episode {ep['num']} URL:[/bold green] {ep['url']}\n")
                Prompt.ask("Press Enter to continue.")
                render_episodes()
            elif key in (readchar.key.ENTER, "\r", "\n"):
                # Show all URLs (preview servers + download links)
                ep = episodes[selected]
                self.console.print(f"[yellow]Loading episode information for {ep['title']}...[/yellow]")
                
                episode_info = self.get_episode_info(ep['url'])
                self.display_episode_info(ep, episode_info)
                
                Prompt.ask("")
                render_episodes()
            elif key in ("q", readchar.key.CTRL_C):
                sys.exit(0)

def main():
    watcher = AnimeWatcher()
    console = watcher.console
    
    console.print("[bold blue]🎌 Wit Anime URL Extractor[/bold blue]")
    console.print("[dim]Extract preview servers and download links from episodes[/dim]\n")
    
    query = Prompt.ask("[bold blue]🔍 Enter anime search query[/bold blue]")
    
    console.print("[yellow]🔍 Searching for anime...[/yellow]")
    anime_list = watcher.get_anime_search_results(query)
    
    if not anime_list:
        console.print("[red]No results found.[/red]")
        sys.exit(0)
    
    console.print(f"[green]✅ Found {len(anime_list)} anime(s)[/green]")
    index = watcher.select_anime(anime_list)
    chosen = anime_list[index]
    
    console.print(f"\n[bold green]Selected:[/bold green] {chosen['title']}")
    console.print(f"[dim]{chosen['url']}[/dim]")
    
    console.print("[yellow]📺 Loading episodes...[/yellow]")
    episodes = watcher.get_episodes_list(chosen["url"])
    
    if not episodes:
        console.print("[red]No episodes found for this anime.[/red]")
        sys.exit(0)
    
    console.print(f"[green]✅ Found {len(episodes)} episode(s)[/green]")
    console.print("[cyan]💡 Press Enter to view preview servers and download links[/cyan]")
    watcher.episode_menu(episodes)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[yellow]👋 Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"[red]💥 Unexpected error: {e}[/red]")
        sys.exit(1)
