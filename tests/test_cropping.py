import pytest
from backend.data_engine.cropping import ROICropper
import os
import pandas as pd
import numpy as np

# We use mock data to avoid depending on the actual FastF1 API for unit tests
class MockCarData:
    def __init__(self, data):
        self.data = data

    def slice_by_time(self, start, end):
        # Simulate empty slice if start > end
        if start > end:
            return pd.DataFrame()
        return self.data

class MockSession:
    def __init__(self):
        # Create a fake dataframe that mimics FastF1 telemetry output
        self.fake_df = pd.DataFrame({
            'Time': pd.to_timedelta(np.arange(0, 10, 0.1), unit='s'),
            'Speed': np.random.randint(100, 300, 100),
            'Throttle': np.random.randint(0, 100, 100),
            'Brake': np.random.choice([0, 100], 100)
        })
        
        self.car_data = {
            'VER': MockCarData(self.fake_df)
        }

def test_roi_cropping_success():
    """
    Task 2.4: Ensure the cropping engine successfully generates 
    the micro-cropped .png image given valid inputs.
    """
    session = MockSession()
    channels = ['Speed', 'Throttle']
    
    filepath = ROICropper.generate_roi_crop(
        session=session, 
        driver='VER', 
        start_time=0, 
        end_time=5, 
        channels=channels, 
        session_id='test_session_123'
    )
    
    assert filepath is not None
    assert os.path.exists(filepath)
    assert str(filepath).endswith("_roi_crop.png")
    assert "test_session_123_VER" in str(filepath)
    
    # Cleanup test artifact
    if os.path.exists(filepath):
        os.remove(filepath)

def test_roi_cropping_invalid_driver():
    """
    Task 2.3: Boundary validation - Ensure system throws a ValueError
    if an invalid driver is requested for a specific session.
    """
    session = MockSession()
    with pytest.raises(ValueError, match="Driver HAM not found"):
        ROICropper.generate_roi_crop(
            session=session, 
            driver='HAM', 
            start_time=0, 
            end_time=5, 
            channels=['Speed'], 
            session_id='test_session'
        )

def test_roi_cropping_empty_bounds():
    """
    Task 2.3: Boundary validation - Ensure system throws an explicit 
    error if the user selects an empty temporal slice (e.g. out of bounds).
    """
    session = MockSession()
    with pytest.raises(ValueError, match="Empty ROI bounds"):
        ROICropper.generate_roi_crop(
            session=session, 
            driver='VER', 
            start_time=10, 
            end_time=5, 
            channels=['Speed'], 
            session_id='test_session'
        )
