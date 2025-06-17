import cloudscraper
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
import sys
import readchar
import webbrowser
from urllib.parse import quote
import math
import re
import arabic_reshaper
from bidi.algorithm import get_display
import subprocess
import time
import threading

class AnimeScraperUI:
    def __init__(self):
        self.console = Console()
        self.scraper = cloudscraper.create_scraper()
        self.anime_choices = []
        self.episodes = []
        
    def is_arabic(self, text):
        """Check if text contains Arabic characters"""
        if not text:
            return False
        arabic_count = 0
        for char in text:
            if ('\u0600' <= char <= '\u06FF' or  # Arabic
                '\u0750' <= char <= '\u077F' or  # Arabic Supplement
                '\u08A0' <= char <= '\u08FF' or  # Arabic Extended-A
                '\uFB50' <= char <= '\uFDFF' or  # Arabic Presentation Forms-A
                '\uFE70' <= char <= '\uFEFF'):   # Arabic Presentation Forms-B
                arabic_count += 1
        return arabic_count > 0
    
    def format_arabic_text(self, text, max_width=60):
        """Format Arabic text for proper RTL display using arabic_reshaper and bidi"""
        if not text:
            return text
            
        text = text.strip()
        
        if self.is_arabic(text):
            try:
                # Apply reshaping (connects Arabic letters properly)
                reshaped_text = arabic_reshaper.reshape(text)
                
                # Apply bidi algorithm (right-to-left display)
                bidi_text = get_display(reshaped_text)
                
                # Truncate if too long
                if len(text) > max_width:
                    truncated = text[:max_width-3] + "..."
                    reshaped_truncated = arabic_reshaper.reshape(truncated)
                    bidi_text = get_display(reshaped_truncated)
                
                return bidi_text
            except Exception as e:
                # Fallback to original text if reshaping fails
                return text[:max_width] if len(text) > max_width else text
        
        # For non-Arabic text, just truncate if needed
        if len(text) > max_width:
            return text[:max_width-3] + "..."
        return text
    
    def preload_stream(self, url, progress_callback=None):
        """Preload stream to avoid buffering lag"""
        try:
            # Use curl or wget to preload first few MB
            cmd = [
                "curl",
                "-s",
                "-r", "0-5242880",  # Download first 5MB
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "-H", "Referer: https://videos.vid3rb.com/",
                "-o", "/dev/null" if sys.platform != "win32" else "nul",
                url
            ]
            
            if progress_callback:
                progress_callback("🔄 Preloading stream...")
            
            subprocess.run(cmd, timeout=10, capture_output=True)
            
            if progress_callback:
                progress_callback("✅ Stream preloaded")
                
        except:
            # Fallback: just wait a bit
            if progress_callback:
                progress_callback("⏳ Preparing stream...")
            time.sleep(2)
    
    def stream_with_mpv(self, url, episode_title, additional_args=None):
        """Stream video URL with mpv player using optimized buffering configuration"""
        
        # Base mpv command
        cmd = ['mpv']
        
        # Revised MPV options based on your provided correct command
        streaming_options = [
            # Cache and buffering
            '--cache=yes',
            '--cache-secs=30',
            '--demuxer-max-bytes=150M',
            '--demuxer-max-back-bytes=75M',
            
            # Network headers
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            '--referrer=https://videos.vid3rb.com/',
            
            # Playback and display
            f'--title={episode_title}',     # Set window title
            '--start=4',                    # Start at 4 seconds
            '--volume=70',                  # Set default volume
            '--fs',                         # Start in fullscreen
        ]
        
        # Add streaming options to command
        cmd.extend(streaming_options)
        
        # Add any additional arguments
        if additional_args:
            cmd.extend(additional_args)
        
        # Add the URL
        cmd.append(url)
        
        try:
            self.console.print(f"[green]🎬 Optimizing stream for smooth playback...[/green]")
            
            # Preload stream in background
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                preload_task = progress.add_task("🔄 Preloading stream buffer...", total=None)
                
                # Preload in separate thread
                def preload():
                    self.preload_stream(url, lambda msg: progress.update(preload_task, description=msg))
                
                preload_thread = threading.Thread(target=preload)
                preload_thread.start()
                preload_thread.join(timeout=8)  # Max 8 seconds preload
                
                progress.remove_task(preload_task)
            
            # Show optimized player info panel
            player_panel = Panel(
                f"[bold cyan]🎬 Now Streaming (Optimized)[/bold cyan]\n\n"
                f"[yellow]Episode:[/yellow] {episode_title}\n"
                f"[yellow]Player:[/yellow] MPV with optimized buffering\n"
                f"[yellow]Cache:[/yellow] 30 seconds + 150MB buffer\n"
                f"[yellow]Startup Time:[/yellow] 00:04 + Preload buffer\n\n"
                f"[dim]MPV Controls:\n"
                f"• Space: Pause/Play\n"
                f"• ←/→: Seek 10 seconds\n"
                f"• ↑/↓: Volume up/down\n"
                f"• 'f': Toggle fullscreen\n"
                f"• '0': Reset to beginning\n"
                f"• 'q': Quit player[/dim]",
                style="green"
            )
            self.console.print(player_panel)
            
            self.console.print(f"[cyan]🚀 Launching MPV with optimized settings...[/cyan]")
            
            # Run MPV with faster startup
            result = subprocess.run(cmd, check=False)  # Don't check=True for faster startup
            
            if result.returncode == 0:
                self.console.print(f"[green]✅ Video playback completed successfully[/green]")
            else:
                self.console.print(f"[yellow]⚠️ MPV exited with code {result.returncode}[/yellow]")
            
        except subprocess.CalledProcessError as e:
            self.console.print(f"[red]❌ Error running MPV: {e}[/red]")
            self.console.print(f"[yellow]💡 Streaming URL (try in browser/VLC):[/yellow]")
            self.console.print(f"[blue]{url}[/blue]")
        except FileNotFoundError:
            self.console.print("[red]❌ MPV not found. Please install MPV first:[/red]")
            self.console.print("[yellow]• Ubuntu/Debian: sudo apt install mpv[/yellow]")
            self.console.print("[yellow]• macOS: brew install mpv[/yellow]")
            self.console.print("[yellow]• Windows: Download from https://mpv.io/[/yellow]")
            self.console.print(f"\n[yellow]💡 Streaming URL (try in browser/VLC):[/yellow]")
            self.console.print(f"[blue]{url}[/blue]")
        except KeyboardInterrupt:
            self.console.print(f"[yellow]⏹️ Video playback interrupted by user[/yellow]")
    
    def extract_download_links(self, episode_url):
        """Extract download links for different qualities from episode page"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = self.scraper.get(episode_url, headers=headers)
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the download section
            download_section = soup.select_one('div.flex.flex-col.rounded-lg.bg-gray-100\\/70.dark\\:bg-dark-700\\/30')
            
            if not download_section:
                # Try alternative selectors
                download_section = soup.find('div', class_=re.compile(r'.*rounded-lg.*bg-gray-100.*'))
                
            if not download_section:
                return {"success": False, "error": "Download section not found"}
            
            download_links = {}
            
            # Find all download containers
            download_containers = download_section.find_all('div', class_=re.compile(r'.*flex.*flex-col.*rounded-lg.*'))
            
            for container in download_containers:
                # Look for quality label
                label_element = container.find('label', class_=re.compile(r'.*font-light.*'))
                if not label_element:
                    continue
                
                quality_text = label_element.get_text(strip=True)
                
                # Extract quality info
                quality = "Unknown"
                size = "Unknown"
                
                if "1080p HEVC" in quality_text:
                    quality = "1080p HEVC"
                elif "1080p" in quality_text:
                    quality = "1080p"
                elif "720p" in quality_text:
                    quality = "720p"
                elif "480p" in quality_text:
                    quality = "480p"
                
                # Find download link
                download_link = container.find('a', href=True)
                if download_link:
                    url = download_link['href']
                    
                    # Extract file size from button text
                    button_text = download_link.get_text(strip=True)
                    size_match = re.search(r'\[([\d.]+\s*[^\]]+)\]', button_text)
                    if size_match:
                        size = size_match.group(1)
                    
                    download_links[quality] = {
                        "url": url,
                        "size": size,
                        "quality_text": quality_text
                    }
            
            return {"success": True, "links": download_links}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def display_quality_selection(self, episode, download_info, selected_index=0):
        """Display quality selection menu with arrow navigation"""
        print("\033[H\033[J", end="")  # Clear screen without blinking
        
        # Format episode title
        formatted_title = self.format_arabic_text(episode['title'], max_width=100)
        
        self.console.print(f"[bold cyan]{formatted_title}[/bold cyan]")
        self.console.print(f"[dim]Episode {episode['num']} - Select Quality (Starts at 00:04 + Buffer)[/dim]\n")
        
        if not download_info["success"]:
            self.console.print(f"[red]❌ Failed to extract download links: {download_info.get('error', 'Unknown error')}[/red]")
            return None
        
        links = download_info["links"]
        if not links:
            self.console.print("[yellow]⚠️ No download links found for this episode[/yellow]")
            return None
        
        # Create quality selection table with arrow navigation
        self.console.print("[bold cyan]═══ 🎬 Select Quality (Optimized Buffering) ═══[/bold cyan]")
        
        quality_table = Table(show_header=True, header_style="bold cyan")
        quality_table.add_column("Selection", style="bright_green", width=12)
        quality_table.add_column("Quality", style="bright_yellow", width=20)
        quality_table.add_column("Size", style="bright_blue", width=25)
        quality_table.add_column("Description", style="white", min_width=35)
        
        links_list = list(links.items())
        for idx, (quality, info) in enumerate(links_list):
            # Enhanced quality descriptions
            descriptions = {
                "1080p HEVC": "High quality, smaller size, best for streaming",
                "1080p": "Full HD quality, larger buffer needed",
                "720p": "HD quality, balanced performance",
                "480p": "Standard quality, fastest streaming"
            }
            
            description = descriptions.get(quality, "Standard quality")
            
            if idx == selected_index:
                quality_table.add_row(
                    f"[bright_green]> {idx + 1}[/bright_green]",
                    f"[bold reverse yellow]{quality}[/]",
                    f"[bold reverse yellow]{info['size']}[/]",
                    f"[bold reverse yellow]{description}[/]"
                )
            else:
                quality_table.add_row(
                    f"[bright_green]  {idx + 1}[/bright_green]",
                    quality,
                    info["size"],
                    description
                )
        
        self.console.print(quality_table)
        
        # Enhanced instructions with buffering info
        self.console.print(f"\n[bold yellow]🚀 Optimization:[/bold yellow] 30s cache + 150MB buffer")
        self.console.print(f"[bold yellow]🕐 Timing:[/bold yellow] Starts at 00:04, preloads buffer to prevent lag")
        self.console.print(f"Use [bold magenta]↑[/]/[bold magenta]↓[/] arrows to select, [bold green]Enter[/] to stream, [bold red]q[/] to go back.")
        
        return links_list
    
    def get_streaming_url(self, download_url):
        """Extract final streaming URL using yt-dlp with faster processing"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("🚀 Fast URL extraction...", total=None)
                
                # Use yt-dlp to get the actual streaming URL with faster options
                cmd = [
                    "yt-dlp",
                    "--get-url",
                    "--no-check-certificate",       # Skip SSL verification for speed
                    "--extractor-args", "generic:impersonate",
                    "--socket-timeout", "15",       # Faster timeout
                    download_url
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=20  # Reduced timeout
                )
                
                progress.remove_task(task)
                
                if result.returncode == 0:
                    streaming_url = result.stdout.strip()
                    return {"success": True, "url": streaming_url}
                else:
                    return {"success": False, "error": result.stderr}
                    
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout while extracting URL"}
        except FileNotFoundError:
            return {"success": False, "error": "yt-dlp not found. Please install it: pip install yt-dlp"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def handle_quality_selection(self, episode, links_list):
        """Handle user quality selection with arrow navigation"""
        if not links_list:
            return
        
        selected_index = 0
        
        while True:
            # Display quality options with current selection
            current_links = self.display_quality_selection(episode, {"success": True, "links": dict(links_list)}, selected_index)
            
            if not current_links:
                return
            
            try:
                key = readchar.readkey()
                
                if key == readchar.key.UP:
                    selected_index = (selected_index - 1) % len(links_list)
                elif key == readchar.key.DOWN:
                    selected_index = (selected_index + 1) % len(links_list)
                elif key in (readchar.key.ENTER, "\r", "\n"):
                    # Select current quality
                    quality, info = links_list[selected_index]
                    
                    self.console.print(f"\n[bold green]✅ Selected: {quality} ({info['size']})[/bold green]")
                    self.console.print(f"[cyan]🚀 Optimizing for lag-free playback...[/cyan]")
                    
                    # Extract streaming URL
                    url_result = self.get_streaming_url(info["url"])
                    
                    if url_result["success"]:
                        streaming_url = url_result["url"]
                        self.console.print(f"[green]🔗 Streaming URL extracted successfully[/green]")
                        
                        # Format episode title for player
                        episode_title = f"Episode {episode['num']} - {episode['title'][:50]}"
                        
                        # Stream with optimized MPV function
                        self.stream_with_mpv(streaming_url, episode_title)
                        
                    else:
                        self.console.print(f"[red]❌ Failed to extract streaming URL: {url_result['error']}[/red]")
                    
                    self.console.print(f"\n[dim]Press Enter to continue...[/dim]")
                    readchar.readkey()
                    return
                elif key.lower() == 'q':
                    return
                    
            except KeyboardInterrupt:
                return
    
    def search_anime(self, anime_name):
        """Search for anime and return results"""
        self.console.print(f"[yellow]🔍 Searching for anime...[/yellow]")
        
        search_url = f"https://anime3rb.com/search?q={quote(anime_name)}"
        
        try:
            response = self.scraper.get(search_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                titles = soup.select('div[class*="title-card"]')
                
                self.anime_choices = []
                for title in titles:
                    title_element = title.select_one('h2.title-name')
                    url_element = title.select_one('a.btn.btn-md.btn-plain.w-full')
                    if title_element and url_element:
                        anime_title = title_element.text.strip()
                        anime_url = url_element['href']
                        self.anime_choices.append({"title": anime_title, "url": anime_url})
                
                return len(self.anime_choices) > 0
            else:
                self.console.print(f"[red]Failed to fetch search results. Status code: {response.status_code}[/red]")
                return False
        except Exception as e:
            self.console.print(f"[red]Error during search: {str(e)}[/red]")
            return False

    def print_anime_menu(self, anime_list, selected_index):
        """Print anime selection menu with proper Arabic RTL support"""
        print("\033[H\033[J", end="")  # Clear screen without blinking
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("No.", style="dim", width=4)
        table.add_column("Anime Title", style="bold white", min_width=60)
        
        for idx, anime in enumerate(anime_list):
            no = str(idx+1)
            # Format Arabic title properly using reshaper and bidi
            title = self.format_arabic_text(anime["title"], max_width=80)
            
            if idx == selected_index:
                table.add_row(f"[bright_green]> {no}[/bright_green]", f"[bold reverse yellow]{title}[/]")
            else:
                table.add_row(f"[bright_green]  {no}[/bright_green]", title)
        
        self.console.print(table)
        self.console.print(f"\nUse [bold magenta]↑[/]/[bold magenta]↓[/] arrows to select, [bold yellow]g[/bold yellow] to jump, [bold green]Enter[/] to show episodes, [bold red]q[/] to exit.")

    def select_anime(self, anime_list):
        """Handle anime selection using wit_anime style navigation"""
        selected = 0
        self.print_anime_menu(anime_list, selected)
        
        while True:
            key = readchar.readkey()
            if key in (readchar.key.UP, "k"):
                selected = (selected - 1) % len(anime_list)
                self.print_anime_menu(anime_list, selected)
            elif key in (readchar.key.DOWN, "j"):
                selected = (selected + 1) % len(anime_list)
                self.print_anime_menu(anime_list, selected)
            elif key.lower() == 'g':
                try:
                    num = int(Prompt.ask("Go to anime number")) - 1
                    if 0 <= num < len(anime_list):
                        selected = num
                        self.print_anime_menu(anime_list, selected)
                except Exception:
                    pass
            elif key in (readchar.key.ENTER, "\r", "\n"):
                return selected
            elif key in ("q", readchar.key.CTRL_C):
                sys.exit(0)
                
    def fetch_episodes(self, anime_url):
        """Fetch episodes from selected anime"""
        self.console.print(f"[yellow]📺 Loading episodes...[/yellow]")
        
        try:
            response = self.scraper.get(anime_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                episodes = soup.select('div.video-data')
                
                self.episodes = []
                for i, episode in enumerate(episodes):
                    episode_url_element = episode.find_parent('a')
                    episode_title_element = episode.select_one('p.font-light.text-sm')
                    
                    if episode_url_element and episode_title_element:
                        episode_url = episode_url_element['href']
                        episode_title = episode_title_element.text.strip()
                        self.episodes.append({
                            'num': i + 1,
                            'title': episode_title,
                            'url': episode_url
                        })
                
                return len(self.episodes) > 0
            else:
                self.console.print(f"[red]Failed to fetch episodes. Status code: {response.status_code}[/red]")
                return False
        except Exception as e:
            self.console.print(f"[red]Error fetching episodes: {str(e)}[/red]")
            return False

    def episode_menu(self, episodes, page_size=30):
        """Episode menu with optimized streaming functionality"""
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
            table.add_column("Episode Title", style="bold white", min_width=70)
            
            for idx in range(start, end):
                ep = episodes[idx]
                num_str = str(ep["num"])
                # Apply proper Arabic RTL formatting to episode titles
                episode_title = self.format_arabic_text(ep["title"], max_width=80)
                
                if idx == selected:
                    table.add_row(f"[bright_green]> {num_str}[/bright_green]", f"[bold reverse yellow]{episode_title}[/]")
                else:
                    table.add_row(f"[bright_green]  {num_str}[/bright_green]", episode_title)
            
            self.console.print(table)
            self.console.print(f"\nPage {page+1}/{max_page+1} | Episodes {start+1}-{end} of {total}")
            self.console.print("Use [bold magenta]↑[/]/[bold magenta]↓[/] to move, [bold magenta]←[/]/[bold magenta]→[/] for page, [bold yellow]g[/bold yellow] to jump")
            self.console.print("[bold green]Enter[/] for optimized streaming (00:04 start + Buffer), [bold cyan]o[/bold cyan] browser, [bold red]q[/bold red] exit, [bold yellow]b[/bold yellow] back.")
        
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
            elif key.lower() == 'o':
                # Open episode in browser
                ep = episodes[selected]
                webbrowser.open(ep['url'])
                self.console.print(f"\n[bold green]✓ Opened Episode {ep['num']} in browser[/bold green]\n")
                Prompt.ask("Press Enter to continue.")
                render_episodes()
            elif key in (readchar.key.ENTER, "\r", "\n"):
                # Extract quality options and let user choose
                ep = episodes[selected]
                
                self.console.print(f"[yellow]🚀 Loading quality options with optimization...[/yellow]")
                download_info = self.extract_download_links(ep['url'])
                
                if download_info["success"]:
                    links_list = list(download_info["links"].items())
                    if links_list:
                        self.handle_quality_selection(ep, links_list)
                else:
                    self.console.print(f"[red]❌ Failed to load quality options: {download_info.get('error', 'Unknown error')}[/red]")
                    self.console.print(f"[dim]Press Enter to continue...[/dim]")
                    readchar.readkey()
                
                render_episodes()
            elif key.lower() == 'b':
                # Go back to anime selection
                return True
            elif key in ("q", readchar.key.CTRL_C):
                sys.exit(0)

    def run(self):
        """Main application loop"""
        self.console.print("[bold blue]🎌 Anime Streaming Player (Lag-Free Optimized)[/bold blue]")
        self.console.print("[dim]Search anime, select quality, stream with optimized buffer[/dim]\n")
        
        while True:
            query = Prompt.ask("[bold blue]🔍 Enter anime search query[/bold blue]")
            
            if not self.search_anime(query):
                self.console.print("[red]No results found.[/red]")
                continue
            
            self.console.print(f"[green]✅ Found {len(self.anime_choices)} anime(s)[/green]")
            index = self.select_anime(self.anime_choices)
            chosen = self.anime_choices[index]
            
            self.console.print(f"\n[bold green]Selected:[/bold green] {self.format_arabic_text(chosen['title'], max_width=100)}")
            self.console.print(f"[dim]{chosen['url']}[/dim]")
            
            if not self.fetch_episodes(chosen["url"]):
                self.console.print("[red]No episodes found for this anime.[/red]")
                continue
            
            self.console.print(f"[green]✅ Found {len(self.episodes)} episode(s)[/green]")
            self.console.print("[cyan]🚀 Press Enter for lag-free streaming with optimized buffering[/cyan]")
            
            # Run episode menu, if it returns True, go back to anime selection
            if self.episode_menu(self.episodes):
                continue
            else:
                break

def main():
    try:
        app = AnimeScraperUI()
        app.run()
    except KeyboardInterrupt:
        print("\n\n[yellow]👋 Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"[red]💥 Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
