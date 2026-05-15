from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from aioresponses import aioresponses

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_aioresponse() -> Generator[aioresponses]:
    with aioresponses() as m:
        yield m
