import pytest
from backend.data_engine.ingestion import FastF1Processor, check_memory_limit
from backend.data_engine.cropping import ROICropper
import psutil
import polars as pl
from pathlib import Path

def test_memory_limit_decorator(caplog):
    """
    Tests that the psutil memory monitor correctly flags when system RAM 
    breaches the specified limit.
    """
    # Set limit impossibly low to force the warning
    @check_memory_limit(limit_gb=0.0001)
    def dummy_func():
        # Allocate some tiny memory
        dummy_data = [x for x in range(1000)]
        return True

    res = dummy_func()
    assert res is True
    
    # Assert the logger captured the memory warning
    assert any("budget" in record.message for record in caplog.records)

@pytest.mark.skip(reason="Downloads real F1 data which takes time. Un-skip to run manually.")
def test_fetch_and_stream_session():
    """
    Integration test to ensure FastF1 correctly fetches a Grand Prix session
    and converts the Pandas laps dataframe into a zero-copy Polars dataframe 
    without crashing system RAM.
    """
    processor = FastF1Processor()
    # Fetching a shorter session like Qualifying
    result = processor.fetch_and_stream_session(2023, 'Monaco', 'Q')
    
    assert 'session' in result
    assert 'laps_pl' in result
    assert 'weather_pl' in result
    
    laps = result['laps_pl']
    # Verify it was successfully converted to Polars
    assert isinstance(laps, pl.DataFrame)
    assert len(laps) > 0
    
    # Verify the memory limit was not breached
    mem = psutil.virtual_memory()
    used_gb = mem.used / (1024 ** 3)
    assert used_gb < 14.0, f"Memory leak detected: {used_gb} GB used."
