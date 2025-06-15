import cloudscraper
from bs4 import BeautifulSoup
import urllib.parse
import subprocess
import os
import sys
import json
import time
import re
import math
from pathlib import Path
from colorama import Fore, Back, Style, init
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.prompt import Prompt, IntPrompt
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
import inquirer
import msvcrt
from functools import lru_cache
import threading

# Initialize colorama for Windows compatibility
init(autoreset=True)

# Initialize Rich console with enhanced settings
console = Console(
    force_terminal=True, 
    width=120, 
    legacy_windows=False,
    file=sys.stdout,
    force_interactive=True,
    color_system="truecolor"
)

def check_mpv():
    """Check if MPV is installed and available"""
    try:
        subprocess.run(["mpv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def display_banner():
    """Display enhanced ASCII art banner"""
    banner_art = """
[bold cyan]
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║  ██████╗ ██╗   ██╗██╗████████╗     █████╗ ███╗   ██╗██╗███╗   ███╗███████╗ ║
    ║  ██╔══██╗██║   ██║██║╚══██╔══╝    ██╔══██╗████╗  ██║██║████╗ ████║██╔════╝ ║
    ║  ██████╔╝██║   ██║██║   ██║       ███████║██╔██╗ ██║██║██╔████╔██║█████╗   ║
    ║  ██╔══██╗██║   ██║██║   ██║       ██╔══██║██║╚██╗██║██║██║╚██╔╝██║██╔══╝   ║
    ║  ██║  ██║╚██████╔╝██║   ██║       ██║  ██║██║ ╚████║██║██║ ╚═╝ ██║███████╗ ║
    ║  ╚═╝  ╚═╝ ╚═════╝ ╚═╝   ╚═╝       ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝╚══════╝ ║
    ╚═══════════════════════════════════════════════════════════════════════╝
[/bold cyan]

[bold green]                    🎌 ANIME STREAMING COMMAND LINE TOOL 🎌[/bold green]
[dim]                         High-speed streaming • MPV Player • HD Quality[/dim]
"""
    
    console.print(Panel.fit(banner_art, border_style="cyan", padding=(1, 2)))

class ModernInquirer:
    """Enhanced inquirer with modern styling"""
    
    @staticmethod
    def select(message, choices, pointer="❯", selected_color="cyan"):
        """Modern selection prompt"""
        try:
            question = [
                inquirer.List('choice',
                            message=message,
                            choices=choices,
                            carousel=True)
            ]
            
            answers = inquirer.prompt(question)
            if not answers:
                return None
                
            return choices.index(answers['choice'])
        except KeyboardInterrupt:
            return None
        except Exception:
            return None

def loading_animation(text, duration=1.5):
    """Show loading animation with fixed Rich compatibility"""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(text, total=None)
            time.sleep(duration)
    except Exception:
        # Fallback to simple text loading
        console.print(f"[bold blue]{text}[/bold blue]")
        time.sleep(duration)

def success_message(text):
    """Display success message with modern styling"""
    console.print(f"[bold green]✅ {text}[/bold green]")

def error_message(text):
    """Display error message with modern styling"""
    console.print(f"[bold red]❌ {text}[/bold red]")

def info_message(text):
    """Display info message with modern styling"""
    console.print(f"[bold yellow]ℹ️  {text}[/bold yellow]")

def create_modern_table(title, data, columns):
    """Create a modern styled table"""
    table = Table(title=title, show_header=True, header_style="bold cyan", border_style="blue")
    
    for col in columns:
        table.add_column(col, style="white", no_wrap=False)
    
    for row in data:
        table.add_row(*row)
    
    return table

def show_main_menu():
    """Display modern main menu"""
    menu_options = [
        "🔍 Search Anime",
        "⚙️  Settings", 
        "❌ Exit"
    ]
    
    panel_content = """
[bold cyan]🎮 MAIN MENU[/bold cyan]

Choose an option to continue:
• Search for your favorite anime
• Configure application settings  
• Exit the application

[dim]Use arrow keys to navigate, Enter to select[/dim]
"""
    
    console.print(Panel(panel_content, border_style="green", padding=(1, 2)))
    
    choice = ModernInquirer.select("Select an option:", menu_options)
    return choice

def show_settings_menu():
    """Display settings menu"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        display_banner()
        
        mpv_status = "✅ Installed" if check_mpv() else "❌ Not Found"
        
        settings_content = f"""
[bold cyan]⚙️  SETTINGS[/bold cyan]

Application Configuration:
• Player: MPV Media Player
• Quality: Auto-select best available
• Streaming: Direct link streaming
• Cache: Enabled for smooth playback

[bold green]Current Status:[/bold green]
• MPV Player: {mpv_status}

[dim]Press any key to return to main menu[/dim]
"""
        
        console.print(Panel(settings_content, border_style="yellow", padding=(1, 2)))
        msvcrt.getch()
        break

def display_search_results(results):
    """Display search results in modern format"""
    if not results:
        error_message("No anime found. Try a different search term.")
        return None
    
    # Create a clean list for results
    console.print(f"\n[bold green]🔍 Found {len(results)} anime:[/bold green]")
    console.print()
    
    # Display results in a clean format
    for idx, anime in enumerate(results[:20], 1):
        console.print(f"[cyan]{idx:2d}.[/cyan] {anime['title']}")
    
    console.print()
    
    # Create selection options
    options = [f"{idx:2d}. {anime['title']}" for idx, anime in enumerate(results[:20], 1)]
    
    choice = ModernInquirer.select("Select anime:", options)
    return choice

def display_episodes_grid(episodes):
    """Display episodes with modern pagination"""
    if not episodes:
        error_message("No episodes found for this anime.")
        return None
    
    # Show episode count with modern styling
    episode_panel = Panel(
        f"[bold green]📺 Found {len(episodes)} Episodes[/bold green]\n"
        f"[dim]Episodes are available for streaming[/dim]",
        border_style="green"
    )
    console.print(episode_panel)
    
    ep_numbers = [ep_num for ep_num, _ in episodes]
    total_episodes = len(episodes)
    episodes_per_page = 20
    total_pages = math.ceil(total_episodes / episodes_per_page)
    current_page = 0
    
    while True:
        start_idx = current_page * episodes_per_page
        end_idx = min(start_idx + episodes_per_page, total_episodes)
        current_episodes = episodes[start_idx:end_idx]
        
        # Display episodes in a grid format
        console.print(f"\n[bold cyan]📺 Episodes {start_idx + 1}-{end_idx} of {total_episodes} (Page {current_page + 1}/{total_pages})[/bold cyan]")
        console.print()
        
        # Display episodes in rows of 10
        episodes_list = [ep_num for ep_num, _ in current_episodes]
        for i in range(0, len(episodes_list), 10):
            row = episodes_list[i:i+10]
            row_str = "  ".join([f"[cyan]{ep:3d}[/cyan]" for ep in row])
            console.print(f"  {row_str}")
        
        console.print()
        
        # Create options
        options = [str(ep_num) for ep_num, _ in current_episodes]
        
        # Add navigation
        nav_options = []
        if current_page > 0:
            nav_options.append("⬅️  Previous Page")
        if current_page < total_pages - 1:
            nav_options.append("➡️  Next Page")
        
        nav_options.extend([
            "🔢 Enter Episode Number",
            "🔙 Back to Anime Selection"
        ])
        
        all_options = options + ["─" * 30] + nav_options
        
        choice = ModernInquirer.select("Select episode or navigation:", all_options)
        
        if choice is None:
            return None
        elif choice < len(options):
            selected_ep_num = current_episodes[choice][0]
            return selected_ep_num
        elif choice == len(options):  # Separator
            continue
        else:
            # Navigation options
            nav_choice = choice - len(options) - 1
            if nav_choice == 0 and current_page > 0:  # Previous
                current_page -= 1
            elif nav_choice == (1 if current_page > 0 else 0) and current_page < total_pages - 1:  # Next
                current_page += 1
            elif nav_choice == (2 if current_page > 0 and current_page < total_pages - 1 else 1):  # Enter number
                try:
                    console.print()
                    episode_num = IntPrompt.ask("[cyan]Enter episode number[/cyan]")
                    if episode_num in ep_numbers:
                        return episode_num
                    else:
                        error_message(f"Episode {episode_num} not found")
                        time.sleep(2)
                except:
                    error_message("Invalid episode number")
                    time.sleep(2)
            else:  # Back
                return None

def display_qualities(qualities):
    """Display available qualities with modern styling"""
    if not qualities:
        error_message("No streaming links found for this episode.")
        return None
    
    # Display quality options
    console.print(f"\n[bold green]🎥 Available Quality Options:[/bold green]")
    console.print()
    
    sorted_qualities = sorted(qualities.keys(), reverse=True)
    
    for idx, quality in enumerate(sorted_qualities, 1):
        console.print(f"[cyan]{idx}.[/cyan] {quality} - 🎬 Stream with MPV")
    
    console.print()
    
    options = [f"{quality} - Stream with MPV" for quality in sorted_qualities]
    choice = ModernInquirer.select("Select quality:", options)
    
    if choice is None:
        return None
    
    return sorted_qualities[choice]

def stream_with_mpv_direct(download_url, anime_title="", episode_number=""):
    """Stream anime directly using MPV without extracting URL first"""
    if not check_mpv():
        error_message("MPV player not found!")
        console.print("[yellow]Please install MPV player:[/yellow]")
        console.print("• Windows: Download from https://mpv.io/installation/")
        console.print("• Or use chocolatey: choco install mpv")
        return False
    
    try:
        if anime_title and episode_number:
            title = f"{anime_title} - Episode {episode_number}"
        else:
            title = "Anime Episode"
        
        success_message(f"Starting MPV for: {title}")
        info_message("Controls: [q] Exit • [f] Fullscreen • [Space] Pause/Play • [←/→] Seek")
        
        console.print()
        loading_animation("🎬 Launching MPV player...")
        
        # Enhanced MPV command for direct streaming
        mpv_cmd = [
            "mpv",
            download_url,
            f"--title={title}",
            "--cache=yes",
            "--demuxer-max-bytes=200M",
            "--demuxer-max-back-bytes=100M",
            "--keep-open=yes",
            "--osd-playing-msg=🎬 Now Playing: ${media-title}",
            "--osd-duration=3000",
            "--fullscreen",
            "--sub-auto=fuzzy",
            "--audio-channels=stereo",
            "--hwdec=auto",  # Hardware decoding
            "--vo=gpu",      # GPU video output
            "--profile=gpu-hq"  # High quality profile
        ]
        
        # Launch MPV
        process = subprocess.Popen(mpv_cmd, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
        process.wait()
        
        if process.returncode == 0:
            success_message("Playback completed successfully!")
            return True
        else:
            error_message(f"MPV exited with error code {process.returncode}")
            return False
            
    except Exception as e:
        error_message(f"Error starting MPV: {str(e)}")
        return False

@lru_cache(maxsize=100)
def get_search_results(query):
    """Fast anime search with caching"""
    base_url = "https://anime3rb.com/search?q="
    search_url = base_url + urllib.parse.quote_plus(query)
    
    # Create optimized scraper
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    try:
        resp = scraper.get(search_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        
        # Optimized parsing - only get essential data
        for card in soup.select('div.title-card')[:25]:
            try:
                title_link = card.find('a', href=True)
                title_element = card.find('h2', class_='title-name')
                
                if title_link and title_element:
                    results.append({
                        "title": title_element.text.strip(),
                        "url": title_link['href']
                    })
            except:
                continue
        
        return results
    except Exception as e:
        error_message(f"Search failed: {str(e)}")
        return []

@lru_cache(maxsize=200)
def get_episodes(title_url):
    """Fast episode fetching with caching"""
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    try:
        resp = scraper.get(title_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        episodes = []
        
        # Optimized episode parsing
        for a in soup.select('a[href^="https://anime3rb.com/episode/"]'):
            video_data = a.find('div', class_='video-data')
            if video_data:
                span = video_data.find('span')
                if span:
                    ep_text = span.text.strip()
                    ep_number = ''.join(filter(str.isdigit, ep_text))
                    if ep_number:
                        episodes.append((int(ep_number), a['href']))
        
        episodes.sort()
        return episodes
    except Exception as e:
        error_message(f"Failed to load episodes: {str(e)}")
        return []

@lru_cache(maxsize=300)
def get_available_qualities(episode_url):
    """Fast quality fetching with caching"""
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    try:
        resp = scraper.get(episode_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        qualities = {}
        quality_blocks = soup.select('div.flex.flex-col.flex-grow.sm\\:max-w-\\[300px\\].rounded-lg.overflow-hidden.bg-gray-50.dark\\:bg-dark-700')
        
        for block in quality_blocks:
            label = block.find('label')
            if label:
                label_text = label.text.strip()
                if "HEVC" in label_text:  # Skip HEVC for compatibility
                    continue
                    
                a_tag = block.find('a', href=True)
                if a_tag and a_tag['href'].startswith("https://anime3rb.com/download/"):
                    if "1080p" in label_text:
                        qualities['1080p'] = a_tag['href']
                    elif "720p" in label_text:
                        qualities['720p'] = a_tag['href']
                    elif "480p" in label_text:
                        qualities['480p'] = a_tag['href']
        
        return qualities
    except Exception as e:
        error_message(f"Failed to load qualities: {str(e)}")
        return {}

def main():
    """Enhanced main application loop"""
    try:
        while True:
            # Clear screen and display banner
            os.system('cls' if os.name == 'nt' else 'clear')
            display_banner()
            
            # Main menu
            main_choice = show_main_menu()
            
            if main_choice is None or main_choice == 2:  # Exit
                console.print()
                console.print(Panel(
                    "[bold green]👋 Thanks for using Quit Anime![/bold green]\n"
                    "[dim]See you next time![/dim]",
                    border_style="green"
                ))
                return
            elif main_choice == 1:  # Settings
                show_settings_menu()
                continue
            elif main_choice != 0:  # Search
                continue
            
            # Search interface
            os.system('cls' if os.name == 'nt' else 'clear')
            display_banner()
            
            search_panel = Panel(
                "[bold cyan]🔍 ANIME SEARCH[/bold cyan]\n\n"
                "Enter the name of the anime you want to watch:",
                border_style="cyan"
            )
            console.print(search_panel)
            
            query = Prompt.ask("[bold cyan]Search[/bold cyan]")
            
            if not query.strip():
                error_message("Please enter a search term")
                time.sleep(2)
                continue
            
            # Search with loading
            loading_animation(f"🔍 Searching for '{query}'...")
            results = get_search_results(query.strip())
            
            if not results:
                error_message("No results found. Try a different search term.")
                console.print("\n[dim]Press any key to try again...[/dim]")
                msvcrt.getch()
                continue
            
            # Display results
            choice = display_search_results(results)
            if choice is None:
                continue
            
            chosen_anime = results[choice]
            chosen_title, chosen_url = chosen_anime['title'], chosen_anime['url']
            
            # Load episodes
            success_message(f"Selected: {chosen_title}")
            loading_animation("📺 Loading episodes...")
            episodes = get_episodes(chosen_url)
            
            if not episodes:
                error_message("No episodes found for this anime.")
                console.print("\n[dim]Press any key to continue...[/dim]")
                msvcrt.getch()
                continue
            
            # Episode selection and streaming loop
            while True:
                ep_choice = display_episodes_grid(episodes)
                if ep_choice is None:
                    break
                
                # Find episode URL
                ep_url = None
                for ep_num, url in episodes:
                    if ep_num == ep_choice:
                        ep_url = url
                        break
                
                if not ep_url:
                    error_message(f"Episode {ep_choice} not found")
                    continue
                
                success_message(f"Selected Episode {ep_choice}")
                
                # Get qualities
                loading_animation("🎥 Loading quality options...")
                qualities = get_available_qualities(ep_url)
                
                if not qualities:
                    error_message("No streaming links found for this episode.")
                    console.print("\n[dim]Press any key to continue...[/dim]")
                    msvcrt.getch()
                    continue
                
                # Quality selection
                selected_quality = display_qualities(qualities)
                if selected_quality is None:
                    continue
                
                download_link = qualities[selected_quality]
                success_message(f"Selected Quality: {selected_quality}")
                
                # Stream directly with MPV
                console.print()
                success = stream_with_mpv_direct(download_link, chosen_title, str(ep_choice))
                
                if success:
                    # Post-viewing options
                    post_panel = Panel(
                        "[bold green]🎬 PLAYBACK COMPLETED[/bold green]\n\n"
                        "What would you like to do next?",
                        border_style="green"
                    )
                    console.print(post_panel)
                    
                    post_options = [
                        "🎬 Watch Next Episode",
                        "📺 Select Different Episode", 
                        "🔍 Search New Anime",
                        "❌ Exit"
                    ]
                    
                    next_choice = ModernInquirer.select("Choose action:", post_options)
                    
                    if next_choice == 0:  # Next episode
                        next_ep = ep_choice + 1
                        ep_numbers = [ep_num for ep_num, _ in episodes]
                        if next_ep in ep_numbers:
                            # Auto-play next episode
                            for ep_num, url in episodes:
                                if ep_num == next_ep:
                                    ep_url = url
                                    break
                            
                            info_message(f"Loading Episode {next_ep}...")
                            qualities = get_available_qualities(ep_url)
                            
                            if selected_quality in qualities:
                                download_link = qualities[selected_quality]
                                stream_with_mpv_direct(download_link, chosen_title, str(next_ep))
                                continue
                            
                            error_message("Next episode unavailable in selected quality.")
                            continue
                        else:
                            info_message("That was the last episode!")
                            console.print("\n[dim]Press any key to continue...[/dim]")
                            msvcrt.getch()
                            break
                    elif next_choice == 1:  # Different episode
                        continue
                    elif next_choice == 2:  # New anime
                        break
                    elif next_choice == 3:  # Exit
                        console.print()
                        console.print(Panel(
                            "[bold green]👋 Thanks for using Quit Anime![/bold green]\n"
                            "[dim]Happy watching![/dim]",
                            border_style="green"
                        ))
                        return
                else:
                    error_message("Streaming failed. Try a different quality or episode.")
                    console.print("\n[dim]Press any key to continue...[/dim]")
                    msvcrt.getch()
                    continue
            
            break
        
    except KeyboardInterrupt:
        console.print()
        console.print(Panel(
            "[bold yellow]👋 Goodbye![/bold yellow]\n"
            "[dim]Thanks for using Quit Anime![/dim]",
            border_style="yellow"
        ))
    except Exception as e:
        console.print()
        error_message(f"An unexpected error occurred: {str(e)}")
        console.print("[dim]Please report this issue if it persists.[/dim]")

if __name__ == "__main__":
    main()
