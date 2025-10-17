#!/usr/bin/env python3
"""
Quick failure analysis script - shows why videos are failing.
"""
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

def analyze_failures():
    """Analyze processing log for failure patterns."""
    log_path = Path("notes/processing_log.json")

    if not log_path.exists():
        print("❌ No processing log found (notes/processing_log.json)")
        return

    with open(log_path, 'r') as f:
        jobs = json.load(f)

    if not jobs:
        print("📝 Log is empty - no videos processed yet")
        return

    # Stats
    total = len(jobs)
    failed = [j for j in jobs if not j.get('success')]
    succeeded = [j for j in jobs if j.get('success')]

    print(f"\n📊 PROCESSING STATISTICS")
    print(f"=" * 60)
    print(f"Total jobs:      {total}")
    print(f"✅ Successful:    {len(succeeded)} ({len(succeeded)/total*100:.1f}%)")
    print(f"❌ Failed:        {len(failed)} ({len(failed)/total*100:.1f}%)")

    if succeeded:
        methods = Counter(j.get('method', 'unknown') for j in succeeded)
        print(f"\n✓ Success by method:")
        for method, count in methods.most_common():
            print(f"  • {method}: {count}")

        avg_duration = sum(j.get('processing_duration', 0) for j in succeeded) / len(succeeded)
        print(f"\n⏱  Average duration: {avg_duration:.1f}s")

    if not failed:
        print(f"\n✅ All jobs succeeded!")
        return

    # Analyze failures
    print(f"\n❌ FAILURE ANALYSIS")
    print(f"=" * 60)

    # Error types
    error_types = Counter()
    for job in failed:
        error = job.get('error', 'Unknown error')
        # Categorize errors
        if 'blocking' in error.lower() or 'ip' in error.lower():
            error_types['YouTube IP Block'] += 1
        elif 'transcript' in error.lower() or 'subtitle' in error.lower():
            error_types['No Transcript Available'] += 1
        elif 'timeout' in error.lower():
            error_types['Timeout'] += 1
        elif 'connection' in error.lower():
            error_types['Connection Error'] += 1
        else:
            error_types['Other'] += 1

    print("Error categories:")
    for error_type, count in error_types.most_common():
        print(f"  • {error_type}: {count}")

    # Show sample failures
    print(f"\n📋 Recent Failures (last 5):")
    for job in failed[-5:]:
        video_id = job.get('video_id', 'unknown')
        error = job.get('error', 'Unknown')
        duration = job.get('processing_duration', 0)
        timestamp = job.get('logged_at', 'unknown')[:19]

        print(f"\n  Video: {video_id}")
        print(f"  Time: {timestamp}")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Error: {error[:100]}...")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print(f"=" * 60)

    if error_types.get('YouTube IP Block', 0) > 0:
        print("⚠️  YouTube is blocking Tor exit nodes")
        print("   Solutions:")
        print("   1. Wait a few minutes between requests")
        print("   2. Rotate Tor circuit: sudo systemctl restart tor")
        print("   3. Use fewer parallel workers")
        print("   4. Enable circuit rotation (check Tor control port)")

    if error_types.get('No Transcript Available', 0) > 0:
        print("⚠️  Some videos don't have transcripts/subtitles")
        print("   This is expected - not all videos have captions")

    if error_types.get('Timeout', 0) > 0:
        print("⚠️  Timeouts occurring")
        print("   Solutions:")
        print("   1. Increase timeout in settings")
        print("   2. Check internet connection")
        print("   3. Try at different time of day")

def check_exit_nodes():
    """Check exit node tracker status."""
    log_path = Path("notes/exit_nodes.json")

    print(f"\n🌐 EXIT NODE STATUS")
    print(f"=" * 60)

    if not log_path.exists():
        print("📝 No exit nodes tracked yet")
        print("   (Will be created after first Tor use)")
        return

    with open(log_path, 'r') as f:
        nodes = json.load(f)

    if not nodes:
        print("📝 No exit nodes tracked yet")
        return

    now = datetime.now()
    in_cooldown = []
    available = []

    for ip, data in nodes.items():
        try:
            last_used = datetime.fromisoformat(data['last_used'])
            elapsed = (now - last_used).total_seconds()

            if elapsed < 3600:  # 1 hour
                remaining = 3600 - elapsed
                in_cooldown.append((ip, data, remaining))
            else:
                available.append((ip, data))
        except:
            pass

    print(f"Total tracked:   {len(nodes)}")
    print(f"⏳ In cooldown:   {len(in_cooldown)} (can't reuse yet)")
    print(f"✅ Available:     {len(available)} (ready to use)")

    if in_cooldown:
        print(f"\n⏳ Nodes in cooldown (most recent):")
        for ip, data, remaining in sorted(in_cooldown, key=lambda x: x[2])[:5]:
            minutes = int(remaining / 60)
            use_count = data.get('use_count', 0)
            print(f"  • {ip}: {minutes}m remaining ({use_count} uses)")

    if available:
        print(f"\n✅ Available nodes (most recent):")
        sorted_available = sorted(available, key=lambda x: x[1].get('last_used', ''), reverse=True)
        for ip, data in sorted_available[:5]:
            last_used = data.get('last_used', 'N/A')[:19]
            use_count = data.get('use_count', 0)
            print(f"  • {ip}: {use_count} uses, last: {last_used}")

def show_current_exit():
    """Show currently active Tor exit node."""
    import subprocess
    try:
        result = subprocess.run(
            ['curl', '--socks5', 'localhost:9050', 'https://api.ipify.org'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            ip = result.stdout.strip()
            print(f"\n🔄 Current Tor Exit: {ip}")
            return ip
        else:
            print(f"\n⚠️  Could not check current Tor exit")
    except Exception as e:
        print(f"\n⚠️  Error checking Tor exit: {e}")
    return None

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  📊 YouTube Study Buddy - Failure Analysis")
    print("=" * 60)

    analyze_failures()
    check_exit_nodes()
    show_current_exit()

    print("\n" + "=" * 60)
    print("\n💡 Tip: Open Streamlit app and check the 'Logs' tab")
    print("   for interactive filtering and detailed views!")
    print("\n" + "=" * 60 + "\n")
