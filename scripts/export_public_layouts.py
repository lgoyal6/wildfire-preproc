"""Record the original optimizer on its explicit synthetic regression fixture.
No ELMFIRE process, federal data, field location or fresh fire prediction.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import importlib.util
import json
import subprocess
import sys
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("layout_fixture", ROOT / "tests/test_optimization_firebreaks.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from wildfire_preproc.optimization import FirebreakOptimizationConfig, optimize_firebreaks

def pixels(path):
    with rasterio.open(path) as dataset:
        mask = dataset.read(1)
    return np.argwhere(mask > 0)[:, ::-1].tolist()

with TemporaryDirectory(prefix="wildfire-layout-demo-") as directory:
    temp = Path(directory)
    inputs = fixture._build_inputs(temp)
    baseline = fixture._build_baseline(temp)
    result = optimize_firebreaks(inputs, baseline_dir=baseline, out_dir=temp / "out", config=FirebreakOptimizationConfig(max_layouts=3, offsets_m=(250.0, 500.0)))
    data = json.loads(result.output_path.read_text())
    data["masks"] = {row["layout_id"]: pixels(temp / "out" / row["artifacts"]["firebreak_mask"]) for row in data["ranked_layouts"]}
    data["protected_cells"] = pixels(inputs / "protected_mask.tif")
    data["grid_size"] = 200
    data["cell_size_m"] = 30
    data["scope"] = "Original optimizer with synthetic rasters and fixture-supplied baseline summaries. Layout cost and geometric proxy ranking only. ELMFIRE was not run; optimized spread result is null."
    files = ["src/wildfire_preproc/optimization/firebreaks.py", "tests/test_optimization_firebreaks.py"]
    data["source"] = {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "sha256": {file: hashlib.sha256((ROOT / file).read_bytes()).hexdigest() for file in files}}
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, separators=(",", ":")) + "\n")
    print("Recorded", len(data["ranked_layouts"]), "ranked layouts; no spread simulation")
