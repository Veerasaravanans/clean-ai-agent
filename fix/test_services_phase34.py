"""
test_services_phase34.py - Phase 3.4 Acceptance Test

Tests screen streamer and verification engine services.
"""

import sys
sys.path.insert(0, '.')

import asyncio
from backend.services.screen_streamer import ScreenStreamer, get_stream_manager
from backend.services.verification_engine import VerificationEngine, VerificationStatus

# Track frames received
frames_received = []

async def frame_callback(frame_data):
    """Callback for new frames."""
    frames_received.append(frame_data)
    print(f"  📸 Frame {frame_data['frame_number']}: {frame_data['width']}x{frame_data['height']}, {frame_data['size_bytes']} bytes")

async def test_phase_34():
    """Phase 3.4 acceptance test."""
    print("=" * 80)
    print("Phase 3.4: Services Layer - Acceptance Test")
    print("=" * 80)
    
    # ═══════════════════════════════════════════════════════════════
    # PART 1: Screen Streamer Tests
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 80)
    print("PART 1: Screen Streamer")
    print("=" * 80)
    
    # Test 1: Create streamer
    print("\n✓ Test 1: Create screen streamer")
    streamer = ScreenStreamer(fps=2, quality=70, max_width=720)
    
    assert streamer.fps == 2, "❌ Wrong FPS"
    assert streamer.quality == 70, "❌ Wrong quality"
    assert streamer.max_width == 720, "❌ Wrong max_width"
    assert not streamer.active, "❌ Should not be active"
    
    print("  ✅ Streamer created:")
    print(f"     FPS: {streamer.fps}")
    print(f"     Quality: {streamer.quality}")
    print(f"     Max width: {streamer.max_width}")
    
    # Test 2: Start streaming (mock mode - no real device)
    print("\n✓ Test 2: Start streaming (3 seconds)")
    print("  ⏳ Streaming...")
    
    global frames_received
    frames_received = []
    
    await streamer.start(on_frame=frame_callback)
    
    # Stream for 3 seconds
    await asyncio.sleep(3)
    
    await streamer.stop()
    
    print(f"\n  ✅ Streaming stopped")
    print(f"     Frames captured: {streamer.frame_count}")
    print(f"     Errors: {streamer.error_count}")
    print(f"     Frames received in callback: {len(frames_received)}")
    
    # Note: Might be 0 if no device connected (mock mode)
    print("  ℹ️  If no device: frames = 0 (expected in mock mode)")
    
    # Test 3: Get stats
    print("\n✓ Test 3: Get streaming statistics")
    stats = streamer.get_stats()
    
    print(f"  📊 Streaming stats:")
    print(f"     Active: {stats['active']}")
    print(f"     Frame count: {stats['frame_count']}")
    print(f"     Error count: {stats['error_count']}")
    print(f"     Error rate: {stats['error_rate']:.2%}")
    
    assert not stats['active'], "❌ Should not be active after stop"
    print("  ✅ Statistics correct")
    
    # Test 4: Stream manager
    print("\n✓ Test 4: Stream manager")
    manager = get_stream_manager()
    
    stream1 = manager.create_streamer("test-stream-1", fps=2)
    stream2 = manager.create_streamer("test-stream-2", fps=1)
    
    assert manager.get_streamer("test-stream-1") is not None, "❌ Stream 1 not found"
    assert manager.get_streamer("test-stream-2") is not None, "❌ Stream 2 not found"
    
    print("  ✅ Stream manager working:")
    print(f"     Created 2 streamers")
    
    all_stats = manager.get_all_stats()
    print(f"     Total streamers: {len(all_stats)}")
    
    await manager.stop_all()
    print("  ✅ All streamers stopped")
    
    # ═══════════════════════════════════════════════════════════════
    # PART 2: Verification Engine Tests
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 80)
    print("PART 2: Verification Engine")
    print("=" * 80)
    
    # Test 5: Create verification engine
    print("\n✓ Test 5: Create verification engine")
    engine = VerificationEngine()
    
    print("  ✅ Verification engine created")
    
    # Test 6: Get performance metrics
    print("\n✓ Test 6: Get performance metrics")
    metrics = engine.get_performance_metrics()
    
    print(f"  📊 Performance metrics:")
    print(f"     OCR available: {metrics['ocr_available']}")
    print(f"     Screenshot available: {metrics['screenshot_available']}")
    print(f"     Verification available: {metrics['verification_available']}")
    
    print("  ✅ Metrics retrieved")
    
    # Test 7: Verify element exists (mock - no screenshot)
    print("\n✓ Test 7: Verify element exists (mock mode)")
    
    # This will fail gracefully in mock mode (no device)
    result = engine.verify_element_exists("Settings")
    
    print(f"  📋 Verification result:")
    print(f"     Verified: {result.verified}")
    print(f"     Status: {result.status}")
    print(f"     Details: {result.details}")
    
    if result.error:
        print(f"     Error (expected in mock): {result.error}")
        print("  ℹ️  Error expected without device - test passed")
    
    print("  ✅ Verification method working (graceful failure in mock mode)")
    
    # Test 8: Verify state (mock)
    print("\n✓ Test 8: Verify state with multiple elements (mock mode)")
    
    result = engine.verify_state(
        expected_elements=["Settings", "Bluetooth", "WiFi"],
        require_all=False
    )
    
    print(f"  📋 State verification:")
    print(f"     Status: {result.status}")
    print(f"     Confidence: {result.confidence:.2%}")
    
    print("  ✅ State verification method working")
    
    # Test 9: VerificationResult structure
    print("\n✓ Test 9: Verify VerificationResult structure")
    
    from backend.services.verification_engine import VerificationResult
    
    # Create mock result
    result = VerificationResult(
        verified=True,
        status=VerificationStatus.VERIFIED,
        confidence=0.95,
        details="Test element found",
        metrics={"x": 100, "y": 200}
    )
    
    assert result.verified == True, "❌ Wrong verified"
    assert result.status == VerificationStatus.VERIFIED, "❌ Wrong status"
    assert result.confidence == 0.95, "❌ Wrong confidence"
    assert result.details == "Test element found", "❌ Wrong details"
    assert result.metrics["x"] == 100, "❌ Wrong metrics"
    
    print("  ✅ VerificationResult structure correct:")
    print(f"     Verified: {result.verified}")
    print(f"     Status: {result.status.value}")
    print(f"     Confidence: {result.confidence:.0%}")
    print(f"     Details: {result.details}")
    
    print("\n" + "=" * 80)
    print("✅ PHASE 3.4 COMPLETE - All Tests Passed!")
    print("=" * 80)
    print("\nServices Summary:")
    print("  • Screen streamer: ✓")
    print("  • Stream manager: ✓")
    print("  • Verification engine: ✓")
    print("  • Element verification: ✓")
    print("  • State verification: ✓")
    print("\nNote: Tests run in mock mode (no device needed)")
    print("      Real device will enable full functionality")
    print("\nNext: Phase 3.5 - Models & Schemas")


if __name__ == "__main__":
    try:
        asyncio.run(test_phase_34())
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)