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
from rich.layout import Layout
import inquirer
import arabic_reshaper
from bidi.algorithm import get_display
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Input, Static, ListItem, ListView
from textual.binding import Binding
import msvcrt
from functools import lru_cache

# Initialize colorama for Windows compatibility
init(autoreset=True)

# Initialize Rich console with proper encoding for Windows and Arabic RTL support
console = Console(
    force_terminal=True, 
    width=120, 
    legacy_windows=False,
    file=sys.stdout,
    force_interactive=True
)

def fix_arabic_text(text):
    """Fix Arabic text display using arabic-reshaper and python-bidi for proper RTL"""
    try:
        if not text or not isinstance(text, str):
            return text
        
        # Check if text contains Arabic characters
        arabic_chars = re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text)
        
        if arabic_chars:
            # Configure arabic reshaper with proper settings
            configuration = {
                'delete_harakat': False,  # Keep diacritics
                'shift_harakat_position': False,
                'support_zwj': True,  # Support zero-width joiner
                'support_zwnj': True,  # Support zero-width non-joiner
            }
            
            # Reshape Arabic text with proper configuration
            reshaped_text = arabic_reshaper.reshape(text, **configuration)
            # Apply bidirectional algorithm for proper RTL display
            display_text = get_display(reshaped_text, base_dir='R')  # Force RTL base direction
            return display_text
        else:
            return text
    except Exception as e:
        # Fallback: just return original text if reshaping fails
        return text

def display_github_credits():
    """Display GitHub credits and project information"""
    credits_panel = Panel.fit(
        f"""
[bold cyan]🎌 Anime Streaming CLI[/bold cyan]
[dim]A powerful CLI tool for streaming anime[/dim]

[bold green]👨‍💻 Developer:[/bold green] joyboy
[bold blue]🔗 GitHub:[/bold blue] https://github.com/joyboy/anime-cli
[bold yellow]⭐ Star this project if you like it![/bold yellow]

[bold red]❤️ Special Thanks:[/bold red]
• anime3rb.com for providing the content
• yt-dlp team for video extraction
• Rich library for beautiful CLI interface
• Arabic text support libraries

[dim]Press any key to continue...[/dim]
        """,
        title="[bold cyan]Credits & Info[/bold cyan]",
        border_style="cyan"
    )
    
    console.print(Align.center(credits_panel))
    msvcrt.getch()

def check_mpv():
    """Check if MPV is installed and available"""
    try:
        subprocess.run(["mpv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def display_banner():
    """Display complete ASCII art banner with anime character"""
    ascii_art = """dont touch this i will place the ascii later"""
    
    banner_text = """
    """    
    console.print(f"[bold cyan]{ascii_art}[/bold cyan]")
    
    # Properly format Arabic text with RTL support
    welcome_text = fix_arabic_text("مرحباً بك في تطبيق مشاهدة الأنمي")
    subtitle_text = fix_arabic_text("أداة سطر الأوامر لمشاهدة الأنمي")
    
    console.print(f"\n[bold green]{welcome_text}[/bold green]")
    console.print(f"[dim]{subtitle_text}[/dim]")


def get_modern_choice(options, title="اختر خياراً", allow_input=False, input_prompt="أدخل رقم الحلقة"):
    """Modern interactive choice using inquirer with Arabic support"""
    try:
        if allow_input:
            # Add option for direct episode input
            enhanced_options = options + ["─" * 40, f"🔢 {input_prompt}"]
            
            question = [
                inquirer.List('choice',
                            message=fix_arabic_text(title),
                            choices=enhanced_options,
                            carousel=True)
            ]
            
            answers = inquirer.prompt(question)
            if not answers:
                return None
                
            choice = answers['choice']
            
            # Check if user selected direct input option
            if choice == f"🔢 {input_prompt}":
                try:
                    episode_num = IntPrompt.ask(f"[cyan]{fix_arabic_text(input_prompt)}[/cyan]")
                    return f"direct_input:{episode_num}"
                except:
                    console.print("[red]❌ رقم غير صحيح[/red]")
                    return None
            elif choice.startswith("─"):
                return None
            else:
                return enhanced_options.index(choice)
        else:
            question = [
                inquirer.List('choice',
                            message=fix_arabic_text(title),
                            choices=options,
                            carousel=True)
            ]
            
            answers = inquirer.prompt(question)
            if not answers:
                return None
                
            return options.index(answers['choice'])
            
    except KeyboardInterrupt:
        return None
    except Exception as e:
        console.print(f"[red]❌ {fix_arabic_text('خطأ في الاختيار')}: {str(e)}[/red]")
        return None

def display_search_results(results):
    """Display search results and get user choice"""
    if not results:
        console.print(f"[red]❌ {fix_arabic_text('لم يتم العثور على نتائج')}[/red]")
        return None
    
    # Create options list for modern navigation (display 20 results)
    options = []
    for idx, anime in enumerate(results[:20], 1):
        rating = f"⭐ {anime['rating']}" if anime['rating'] else "N/A"
        episodes = str(anime['episode_count']) if anime['episode_count'] else "N/A"
        year = anime['release_season'] if anime['release_season'] else "N/A"
        
        # Fix Arabic text in title
        title = fix_arabic_text(anime['title'][:50])
        
        option_text = f"{idx:2d}. {title:<50} | {rating:<8} | {episodes:<3} eps | {year}"
        options.append(option_text)
    
    choice = get_modern_choice(options, fix_arabic_text("🔍 اختر الأنمي"))
    return choice if choice is not None else None

def display_episodes_grid(episodes):
    """Display episodes with pagination and direct input support (20 per page)"""
    if not episodes:
        console.print(f"[red]❌ {fix_arabic_text('لم يتم العثور على حلقات')}[/red]")
        return None
    
    ep_numbers = [ep_num for ep_num, _ in episodes]
    total_episodes = len(episodes)
    episodes_per_page = 20  # Changed from 15 to 20
    total_pages = math.ceil(total_episodes / episodes_per_page)
    current_page = 0
    
    while True:
        # Calculate start and end indices for current page
        start_idx = current_page * episodes_per_page
        end_idx = min(start_idx + episodes_per_page, total_episodes)
        current_episodes = episodes[start_idx:end_idx]
        
        # Create options for current page
        options = []
        for ep_num, _ in current_episodes:
            options.append(fix_arabic_text(f"الحلقة {ep_num:3d}"))
        
        # Add navigation options if needed
        nav_options = []
        if current_page > 0:            nav_options.append(fix_arabic_text("⬅️  الصفحة السابقة"))
        if current_page < total_pages - 1:
            nav_options.append(fix_arabic_text("➡️  الصفحة التالية"))
          # Combine episode options with navigation
        all_options = options + (nav_options if nav_options else [])
        
        # Update title to show page info
        page_info = fix_arabic_text(f"📺 الحلقات {start_idx + 1}-{end_idx} من {total_episodes} (صفحة {current_page + 1}/{total_pages})")
        
        choice = get_modern_choice(all_options, page_info, allow_input=True, input_prompt=fix_arabic_text("أدخل رقم الحلقة"))
        
        if choice is None:
            return None
        elif isinstance(choice, str) and choice.startswith("direct_input:"):
            # Handle direct episode input
            episode_num = int(choice.split(":")[1])
            if episode_num in ep_numbers:
                return episode_num
            else:
                console.print(f"[red]❌ {fix_arabic_text('الحلقة')} {episode_num} {fix_arabic_text('غير موجودة')}[/red]")
                time.sleep(2)
                continue
        elif choice < len(options):
            # Episode selected
            selected_ep_num = current_episodes[choice][0]
            return selected_ep_num
        else:
            # Navigation option selected
            nav_choice = choice - len(options)
            if nav_choice == 0 and current_page > 0:
                # Previous page
                current_page -= 1
            elif nav_choice == (1 if current_page > 0 else 0) and current_page < total_pages - 1:
                # Next page
                current_page += 1

def display_qualities(qualities):
    """Display available qualities and get user choice"""
    if not qualities:
        console.print(f"[red]❌ {fix_arabic_text('لم يتم العثور على روابط المشاهدة')}[/red]")
        return None
    
    # Create options for quality selection
    options = []
    sorted_qualities = sorted(qualities.keys(), reverse=True)
    for quality in sorted_qualities:        options.append(f"{quality} - 🎬 {fix_arabic_text('مشاهدة مع MPV')}")
    
    choice = get_modern_choice(options, fix_arabic_text("🎥 اختر الجودة"))
    
    if choice is None:
        return None
    
    return sorted_qualities[choice]

def get_stream_url(download_url):
    """Extract the actual stream URL from the download page"""
    try:
        console.print(f"[yellow]🔍 {fix_arabic_text('استخراج رابط المشاهدة')}...[/yellow]")
        
        # Use yt-dlp to get the direct URL without downloading
        cmd = [
            "yt-dlp",
            "--get-url",
            "--extractor-args", "generic:impersonate",
            download_url        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            stream_url = result.stdout.strip()
            console.print(f"[green]✅ {fix_arabic_text('تم استخراج رابط المشاهدة بنجاح')}![/green]")
            return stream_url
        else:
            console.print(f"[red]❌ {fix_arabic_text('فشل في استخراج الرابط')}: {result.stderr}[/red]")
            return None
    except subprocess.TimeoutExpired:
        console.print(f"[red]❌ {fix_arabic_text('انتهت مهلة استخراج الرابط')}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]❌ {fix_arabic_text('خطأ في استخراج رابط المشاهدة')}: {str(e)}[/red]")
        return None

def stream_with_mpv(stream_url, anime_title="", episode_number=""):
    """Stream anime using MPV player"""
    if not check_mpv():
        console.print(f"[red]❌ {fix_arabic_text('مشغل MPV غير موجود')}![/red]")
        console.print(f"[yellow]{fix_arabic_text('يرجى تثبيت مشغل MPV')}:[/yellow]")
        console.print("• Windows: Download from https://mpv.io/installation/")
        console.print("• Or use chocolatey: choco install mpv")
        return False
    
    try:
        title = f"{fix_arabic_text(anime_title)} - {fix_arabic_text('الحلقة')} {episode_number}" if anime_title and episode_number else fix_arabic_text("حلقة أنمي")
        
        console.print(f"[green]🎬 {fix_arabic_text('بدء تشغيل MPV لـ')}: {title}[/green]")
        console.print(f"[dim]{fix_arabic_text('اضغط q في MPV للخروج، f للشاشة الكاملة، مسافة للإيقاف المؤقت')}[/dim]")
        
        # MPV command with optimized settings for streaming
        mpv_cmd = [
            "mpv",
            stream_url,
            f"--title={title}",
            "--cache=yes",
            "--demuxer-max-bytes=150M",
            "--demuxer-max-back-bytes=75M",
            "--keep-open=always",
            "--osd-playing-msg=🎬 Now Playing: ${filename}",
            "--osd-duration=3000",
            "--fullscreen"
        ]
        
        # Run MPV
        process = subprocess.Popen(mpv_cmd)
        
        # Wait for MPV to finish        process.wait()
        
        if process.returncode == 0:
            console.print(f"[green]✅ {fix_arabic_text('انتهت المشاهدة')}![/green]")
            return True
        else:
            console.print(f"[red]❌ {fix_arabic_text('خرج MPV برمز الخطأ')} {process.returncode}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]❌ {fix_arabic_text('خطأ في بدء تشغيل MPV')}: {str(e)}[/red]")
        return False

@lru_cache(maxsize=50)
def get_search_results(query):
    """Search for anime with enhanced details and caching (return 20 results)"""
    base_url = "https://anime3rb.com/search?q="
    search_url = base_url + urllib.parse.quote_plus(query)
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    try:
        resp = scraper.get(search_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        
        for card in soup.select('div.title-card')[:20]:  # Changed from 15 to 20
            try:
                title_link = card.find('a', href=True)
                title_element = card.find('h2', class_='title-name')
                
                if not title_link or not title_element:
                    continue
                    
                # Clean title text for better display (keep Arabic text)
                title = title_element.text.strip()
                
                url = title_link['href']
                
                poster_img = card.find('img')
                poster_image = poster_img['src'] if poster_img else None
                
                details_section = card.find('a', class_='details')
                rating = None
                episode_count = None
                genres = []
                release_season = None
                description = None
                
                if details_section:
                    genres_div = details_section.find('div', class_='genres')
                    if genres_div:
                        genre_spans = genres_div.find_all('span')
                        genres = [span.text.strip() for span in genre_spans]
                    
                    badges = details_section.find_all('span', class_='badge')
                    for badge in badges:
                        badge_text = badge.get_text(strip=True)
                        
                        if badge.find('svg'):
                            rating_match = re.search(r'(\d+\.?\d*)', badge_text)
                            if rating_match:
                                rating = float(rating_match.group(1))
                        
                        elif 'حلقات' in badge_text or 'حلقة' in badge_text:
                            episode_match = re.search(r'(\d+)', badge_text)
                            if episode_match:
                                episode_count = int(episode_match.group(1))
                        
                        elif re.search(r'\d{4}', badge_text):
                            release_season = badge_text
                    
                    synopsis_p = details_section.find('p', class_='synopsis')
                    if synopsis_p:
                        description = synopsis_p.text.strip()
                
                anime_data = {
                    "title": title,
                    "url": url,
                    "poster_image": poster_image,
                    "rating": rating,
                    "episode_count": episode_count,
                    "genres": genres,
                    "release_season": release_season,
                    "description": description
                }
                
                results.append(anime_data)
                
            except Exception as e:
                continue
        
        return results
    except Exception as e:
        console.print(f"[red]❌ خطأ في البحث: {str(e)}[/red]")
        return []

@lru_cache(maxsize=100)
def get_episodes(title_url):
    """Get episodes list for anime with caching"""
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    try:
        resp = scraper.get(title_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        episodes = []
        
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
        console.print(f"[red]❌ خطأ في الحلقات: {str(e)}[/red]")
        return []

def get_available_qualities(episode_url):
    """Get available download qualities for episode"""
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    try:
        resp = scraper.get(episode_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        qualities = {}
        quality_blocks = soup.select('div.flex.flex-col.flex-grow.sm\\:max-w-\\[300px\\].rounded-lg.overflow-hidden.bg-gray-50.dark\\:bg-dark-700')
        
        for block in quality_blocks:
            label = block.find('label')
            if label:
                label_text = label.text.strip()
                if "HEVC" in label_text:
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
        console.print(f"[red]❌ خطأ في الجودة: {str(e)}[/red]")
        return {}

def main():
    """Enhanced Interactive CLI Mode with modern navigation and Arabic support"""
    try:
        while True:
            # Show main menu first
            os.system('cls' if os.name == 'nt' else 'clear')
            display_banner()
            
            main_options = [
                "🔍 البحث عن أنمي",
                "ℹ️  عرض المعلومات والشكر",
                "❌ خروج"
            ]
            
            main_choice = get_modern_choice(main_options, "القائمة الرئيسية")
            
            if main_choice is None or main_choice == 2:  # Exit
                console.print("[yellow]👋 وداعاً![/yellow]")
                return
            elif main_choice == 1:  # Credits
                display_github_credits()
                continue
            elif main_choice != 0:  # Search
                continue
            
            # Search for anime
            os.system('cls' if os.name == 'nt' else 'clear')
            display_banner()
            
            console.print("\n" + "="*70)
            console.print("[bold cyan]🔍 أدخل اسم الأنمي للبحث:[/bold cyan]", end=" ")
            query = input().strip()
            
            if not query:
                console.print("[red]❌ يرجى إدخال استعلام بحث[/red]")
                time.sleep(2)
                continue
            
            # Show loading
            console.print("[yellow]🔍 البحث عن الأنمي...[/yellow]")
            results = get_search_results(query)
            
            if not results:
                console.print("[red]❌ لم يتم العثور على نتائج. جرب مصطلح بحث مختلف.[/red]")
                console.print("\n[yellow]اضغط أي مفتاح للبحث مرة أخرى...[/yellow]")
                msvcrt.getch()
                continue
            
            # Display results and get selection
            choice = display_search_results(results)
            if choice is None:
                continue
            
            chosen_anime = results[choice]
            chosen_title, chosen_url = chosen_anime['title'], chosen_anime['url']
            
            # Get episodes
            console.print(f"\n[bold green]✅ تم اختيار: {fix_arabic_text(chosen_title)}[/bold green]")
            console.print("[yellow]📺 تحميل الحلقات...[/yellow]")
            episodes = get_episodes(chosen_url)
            
            if not episodes:
                console.print("[red]❌ لم يتم العثور على حلقات لهذا الأنمي.[/red]")
                console.print("\n[yellow]اضغط أي مفتاح للمتابعة...[/yellow]")
                msvcrt.getch()
                continue
            
            # Episode selection loop
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
                    console.print("[red]❌ الحلقة غير موجودة[/red]")
                    continue
                
                console.print(f"\n[bold green]✅ تم اختيار الحلقة {ep_choice}[/bold green]")
                
                # Get qualities
                console.print("[yellow]🎥 تحميل جودة الفيديو...[/yellow]")
                qualities = get_available_qualities(ep_url)
                
                if not qualities:
                    console.print("[red]❌ لم يتم العثور على روابط مشاهدة لهذه الحلقة.[/red]")
                    console.print("\n[yellow]اضغط أي مفتاح للمتابعة...[/yellow]")
                    msvcrt.getch()
                    continue
                
                # Quality selection
                selected_quality = display_qualities(qualities)
                if selected_quality is None:
                    continue
                
                download_link = qualities[selected_quality]
                
                console.print(f"\n[bold green]✅ تم اختيار: {selected_quality}[/bold green]")
                
                # Get stream URL and auto-play
                stream_url = get_stream_url(download_link)
                if stream_url:
                    console.print(f"[dim]رابط المشاهدة: {stream_url[:50]}...[/dim]")
                    
                    # Auto-stream without asking
                    console.print("\n[bold green]🎬 بدء المشاهدة تلقائياً...[/bold green]")
                    success = stream_with_mpv(stream_url, chosen_title, str(ep_choice))
                    
                    if success:
                        # Ask what to do next
                        options = [
                            "🎬 مشاهدة الحلقة التالية",
                            "📺 اختيار حلقة مختلفة", 
                            "🔍 البحث عن أنمي جديد",
                            "❌ خروج"
                        ]
                        
                        next_choice = get_modern_choice(options, "ماذا تريد أن تفعل بعد ذلك؟")
                        
                        if next_choice == 0:  # Next episode
                            next_ep = ep_choice + 1
                            ep_numbers = [ep_num for ep_num, _ in episodes]
                            if next_ep in ep_numbers:
                                # Find next episode URL and auto-play with same quality
                                for ep_num, url in episodes:
                                    if ep_num == next_ep:
                                        ep_url = url
                                        break
                                
                                console.print(f"\n[bold green]🎬 تحميل الحلقة {next_ep}...[/bold green]")
                                qualities = get_available_qualities(ep_url)
                                
                                if selected_quality in qualities:
                                    download_link = qualities[selected_quality]
                                    stream_url = get_stream_url(download_link)
                                    if stream_url:
                                        stream_with_mpv(stream_url, chosen_title, str(next_ep))
                                        continue
                                
                                console.print("[yellow]📺 الحلقة غير متاحة أو جودة مختلفة.[/yellow]")
                                continue
                            else:
                                console.print("[yellow]📺 هذه كانت الحلقة الأخيرة![/yellow]")
                                console.print("\n[yellow]اضغط أي مفتاح للمتابعة...[/yellow]")
                                msvcrt.getch()
                                break
                        elif next_choice == 1:  # Different episode
                            continue
                        elif next_choice == 2:  # New anime
                            break
                        elif next_choice == 3:  # Exit
                            console.print("[yellow]👋 شكراً لاستخدام تطبيق الأنمي![/yellow]")
                            return
                    else:
                        console.print("[red]❌ فشل في المشاهدة. جرب جودة أو حلقة مختلفة.[/red]")
                        console.print("\n[yellow]اضغط أي مفتاح للمتابعة...[/yellow]")
                        msvcrt.getch()
                        continue
                else:
                    console.print("[red]❌ فشل في الحصول على رابط المشاهدة. جرب جودة مختلفة.[/red]")
                    console.print("\n[yellow]اضغط أي مفتاح للمتابعة...[/yellow]")
                    msvcrt.getch()
                    continue
            
            # Ask if user wants to search for different anime
            break
        
        console.print("\n[bold green]👋 شكراً لاستخدام تطبيق مشاهدة الأنمي![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 وداعاً![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ حدث خطأ: {str(e)}[/red]")
        console.print("[dim]يرجى المحاولة مرة أخرى أو الإبلاغ عن هذه المشكلة.[/dim]")

if __name__ == "__main__":
    main()
