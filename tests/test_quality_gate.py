import numpy as np

from core.phase_a.s2_preprocess.quality_gate import assess_image_quality


def test_quality_gate_reject_blurry_image():
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    res = assess_image_quality(img)
    assert res.state in ("REJECT", "WARNING")


def test_quality_gate_good_with_text_like_content():
    img = np.full((500, 700, 3), 210, dtype=np.uint8)
    # Draw synthetic dark text lines to mimic prescription content
    for y in range(80, 420, 40):
        img[y:y + 3, 80:620] = 0
    res = assess_image_quality(img)
    assert res.state in ("GOOD", "WARNING")
    assert "blur_score" in res.metrics
