"""
Browser action executor for CAPTCHA solving.

Provides human-like mouse movements to avoid anti-automation detection.
"""
import asyncio
import math
import random
import logging

logger = logging.getLogger(__name__)


async def human_like_drag(page, start_x: float, start_y: float, end_x: float, end_y: float):
    """Simulate a human-like drag from start to end position.

    Uses a bezier-like curve with acceleration/deceleration and slight randomness
    to mimic natural human movement.
    """
    distance = end_x - start_x
    steps = max(20, int(abs(distance) / 3))

    # Generate trajectory points with easing
    points = _generate_trajectory(start_x, start_y, end_x, end_y, steps)

    # Mouse down on start position
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.05, 0.15))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.1, 0.2))

    # Move through trajectory points
    for x, y in points:
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.008, 0.025))

    # Overshoot slightly, then correct back
    overshoot = random.uniform(2, 6)
    await page.mouse.move(end_x + overshoot, end_y + random.uniform(-1, 1))
    await asyncio.sleep(random.uniform(0.05, 0.1))
    await page.mouse.move(end_x, end_y)
    await asyncio.sleep(random.uniform(0.05, 0.15))

    # Release
    await page.mouse.up()
    await asyncio.sleep(0.3)
    logger.info(f"Human-like drag: ({start_x:.0f},{start_y:.0f}) → ({end_x:.0f},{end_y:.0f})")


def _generate_trajectory(
    sx: float, sy: float, ex: float, ey: float, steps: int
) -> list[tuple[float, float]]:
    """Generate trajectory points with easing and slight randomness.

    Movement profile: fast start → constant middle → slow end (ease-out).
    Y axis has small random wobble.
    """
    points = []
    dx = ex - sx
    dy = ey - sy

    for i in range(1, steps + 1):
        t = i / steps
        # Ease-out cubic: fast start, slow end
        eased_t = 1 - (1 - t) ** 3

        x = sx + dx * eased_t
        # Add small Y wobble (±2px), more in the middle of the movement
        wobble = math.sin(t * math.pi) * random.uniform(-2, 2)
        y = sy + dy * eased_t + wobble

        points.append((x, y))

    return points


async def click_sequence(
    page,
    points: list[tuple[float, float]],
    delay_between: float = 0.3,
):
    """Click a sequence of points with human-like delays.

    Used for text-order CAPTCHAs where multiple targets must be clicked in order.
    """
    for i, (x, y) in enumerate(points):
        # Small random offset for natural imprecision
        offset_x = random.uniform(-2, 2)
        offset_y = random.uniform(-2, 2)

        await page.mouse.move(x + offset_x, y + offset_y)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.click(x + offset_x, y + offset_y)
        logger.info(f"Click sequence [{i+1}/{len(points)}]: ({x:.0f},{y:.0f})")

        if i < len(points) - 1:
            await asyncio.sleep(random.uniform(delay_between * 0.7, delay_between * 1.3))


async def human_like_click(page, x: float, y: float):
    """Single click with small random offset for natural feel."""
    offset_x = random.uniform(-1, 1)
    offset_y = random.uniform(-1, 1)
    await page.mouse.move(x + offset_x, y + offset_y)
    await asyncio.sleep(random.uniform(0.03, 0.1))
    await page.mouse.click(x + offset_x, y + offset_y)
