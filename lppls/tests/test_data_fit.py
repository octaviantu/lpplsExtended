import numpy as np
import pytest
from data_fit import DataFit


@pytest.fixture
def observations():
    return np.array([[1, 2, 3, 4, 5], [1, 4, 9, 16, 25]])


@pytest.fixture
def filter_settings():
    return {
        "tc_delta_min": 0.1,
        "tc_delta_max": 0.2,
        "m_min": 0.1,
        "m_max": 1,
        "w_min": 1,
        "w_max": 20,
    }


def test_basic_case(observations, filter_settings):
    data_fit = DataFit(observations, filter_settings)
    result = data_fit.parallel_compute_t2_fits(
        workers=2,
        window_size=5,
        smallest_window_size=2,
        t2_increment=1,
        t1_increment=1,
        max_searches=10,
    )
    assert result is not None


def test_empty_observations(filter_settings):
    empty_obs = np.array([[], []])
    data_fit = DataFit(empty_obs, filter_settings)
    result = data_fit.parallel_compute_t2_fits(workers=2)
    assert result == []
