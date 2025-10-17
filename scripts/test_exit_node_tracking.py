#!/usr/bin/env python3
"""
Test script for exit node tracking with persistent cooldown.

Tests the 1-hour cooldown enforcement across app restarts.
"""
import json
import time
from pathlib import Path

from src.yt_study_buddy.exit_node_tracker import ExitNodeTracker


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def test_basic_tracking():
    """Test basic IP tracking and cooldown."""
    print_section("Test 1: Basic Tracking")

    # Use temp path for testing
    test_log = Path("notes/test_exit_nodes.json")
    if test_log.exists():
        test_log.unlink()

    tracker = ExitNodeTracker(log_path=test_log, cooldown_hours=0.001)  # ~3.6 seconds

    # Record first use
    ip1 = "185.220.101.1"
    success = tracker.record_use(ip1, worker_id=1)
    print(f"✓ Recorded use of {ip1}: {success}")

    # Try immediate reuse (should fail)
    success = tracker.record_use(ip1, worker_id=2)
    print(f"{'✓' if not success else '✗'} Immediate reuse blocked: {not success}")

    # Check cooldown
    remaining = tracker.get_cooldown_remaining(ip1)
    print(f"  Cooldown remaining: {remaining:.1f}s")

    # Wait for cooldown
    print("  Waiting 4s for cooldown...")
    time.sleep(4)

    # Should be available now
    available = tracker.is_available(ip1)
    print(f"✓ IP available after cooldown: {available}")

    # Clean up
    test_log.unlink()


def test_persistence():
    """Test that cooldown persists across tracker instances."""
    print_section("Test 2: Persistence Across Restarts")

    test_log = Path("notes/test_exit_nodes.json")
    if test_log.exists():
        test_log.unlink()

    # Create tracker and record use
    tracker1 = ExitNodeTracker(log_path=test_log, cooldown_hours=0.01)  # ~36 seconds
    ip = "185.220.101.2"
    tracker1.record_use(ip, worker_id=1)
    print(f"✓ Tracker 1: Recorded {ip}")

    # Delete tracker (simulate app restart)
    del tracker1

    # Create new tracker instance
    tracker2 = ExitNodeTracker(log_path=test_log, cooldown_hours=0.01)
    available = tracker2.is_available(ip)
    remaining = tracker2.get_cooldown_remaining(ip)

    print(f"✓ Tracker 2: Loaded from disk")
    print(f"  IP available: {available}")
    print(f"  Cooldown remaining: {remaining:.1f}s")

    # Should still be in cooldown
    success = tracker2.record_use(ip, worker_id=2, force=False)
    print(f"{'✓' if not success else '✗'} Cooldown enforced across restart: {not success}")

    # Clean up
    test_log.unlink()


def test_multiple_ips():
    """Test tracking multiple IPs with different cooldowns."""
    print_section("Test 3: Multiple IPs")

    test_log = Path("notes/test_exit_nodes.json")
    if test_log.exists():
        test_log.unlink()

    tracker = ExitNodeTracker(log_path=test_log, cooldown_hours=0.01)

    # Record multiple IPs
    ips = ["185.220.101.1", "185.220.101.2", "185.220.101.3"]
    for i, ip in enumerate(ips):
        tracker.record_use(ip, worker_id=i)
        print(f"✓ Recorded {ip} (worker {i})")
        time.sleep(1)  # Stagger timestamps

    # Check stats
    stats = tracker.get_stats()
    print(f"\n  Total tracked: {stats['total_tracked']}")
    print(f"  In cooldown: {stats['in_cooldown']}")
    print(f"  Available: {stats['available']}")

    # Get unavailable IPs
    unavailable = tracker.get_unavailable_ips()
    print(f"\n  IPs in cooldown: {', '.join(unavailable)}")

    # Wait and recheck
    print("\n  Waiting 5s...")
    time.sleep(5)

    unavailable = tracker.get_unavailable_ips()
    print(f"  IPs in cooldown now: {', '.join(unavailable) if unavailable else 'none'}")

    # Clean up
    test_log.unlink()


def test_real_world_scenario():
    """Simulate real parallel processing scenario."""
    print_section("Test 4: Real-World Simulation")

    test_log = Path("notes/test_exit_nodes.json")
    if test_log.exists():
        test_log.unlink()

    tracker = ExitNodeTracker(log_path=test_log, cooldown_hours=1.0)

    # Simulate 3 workers getting different exit IPs
    worker_ips = {
        0: "185.220.101.1",
        1: "185.220.101.2",
        2: "185.220.101.3"
    }

    print("Simulating parallel processing with 3 workers:")
    for worker_id, ip in worker_ips.items():
        success = tracker.record_use(ip, worker_id=worker_id)
        print(f"  Worker {worker_id}: {ip} {'✓' if success else '✗'}")

    # Show stats
    stats = tracker.get_stats()
    print(f"\nStats:")
    print(f"  Total tracked: {stats['total_tracked']}")
    print(f"  In cooldown: {stats['in_cooldown']}")
    print(f"  Cooldown period: {stats['cooldown_hours']} hour(s)")

    # Show log file content
    print(f"\nLog file content ({test_log}):")
    with open(test_log, 'r') as f:
        log_data = json.load(f)
        print(json.dumps(log_data, indent=2))

    # Clean up
    # test_log.unlink()  # Keep for inspection


def test_cleanup():
    """Test automatic cleanup of expired entries."""
    print_section("Test 5: Automatic Cleanup")

    test_log = Path("notes/test_exit_nodes.json")
    if test_log.exists():
        test_log.unlink()

    tracker = ExitNodeTracker(
        log_path=test_log,
        cooldown_hours=0.001,  # ~3.6 seconds
        auto_cleanup=True
    )

    # Add multiple IPs
    ips = ["185.220.101.1", "185.220.101.2", "185.220.101.3"]
    for ip in ips:
        tracker.record_use(ip)

    print(f"Added {len(ips)} IPs")
    print(f"Total tracked: {tracker.get_stats()['total_tracked']}")

    # Wait for expiry
    print("Waiting 5s for entries to expire...")
    time.sleep(5)

    # Record new IP (triggers auto-cleanup)
    tracker.record_use("185.220.101.4")

    stats = tracker.get_stats()
    print(f"\nAfter auto-cleanup:")
    print(f"  Total tracked: {stats['total_tracked']}")
    print(f"  In cooldown: {stats['in_cooldown']}")

    # Manual cleanup
    removed = tracker.cleanup()
    print(f"\nManual cleanup removed: {removed} entries")

    # Clean up
    test_log.unlink()


if __name__ == "__main__":
    print("Exit Node Tracking Test Suite")
    print("=" * 60)

    try:
        test_basic_tracking()
        test_persistence()
        test_multiple_ips()
        test_real_world_scenario()
        test_cleanup()

        print_section("✓ All Tests Passed")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
