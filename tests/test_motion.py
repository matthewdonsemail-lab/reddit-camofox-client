"""Motion planner tests: pure math, no browser needed."""
from reddit_camofox_client.domain_camofox.motion import human_scroll_trajectory


def test_empty_on_zero():
    assert human_scroll_trajectory(0) == []


def test_deltas_sum_to_distance():
    for distance in (200, 800, 2500, 5200, -1200):
        steps = human_scroll_trajectory(distance, seed=7)
        assert steps, distance
        total = sum(s.delta_y for s in steps)
        assert abs(total - distance) < 1e-6, (distance, total)


def test_seeded_determinism():
    a = human_scroll_trajectory(1200, seed=42)
    b = human_scroll_trajectory(1200, seed=42)
    assert [(s.delta_y, s.delay_ms) for s in a] == [(s.delta_y, s.delay_ms) for s in b]


def test_delays_stay_perceptible():
    steps = human_scroll_trajectory(300, seed=3)
    assert all(s.delay_ms >= 12 for s in steps)


def test_short_flick_is_fast():
    flick = human_scroll_trajectory(200, seed=1)
    crawl = human_scroll_trajectory(5000, seed=1)
    flick_ms = sum(s.delay_ms for s in flick)
    assert flick_ms < sum(s.delay_ms for s in crawl)
    assert len(flick) < len(crawl)
