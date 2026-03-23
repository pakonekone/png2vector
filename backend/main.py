from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import io
import time
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image

app = FastAPI(title="PNG to Vector Converter", version="1.0.0")

# CORS configuration
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def flatten_transparency(image: Image.Image) -> Image.Image:
    """Ensure transparent backgrounds are composited over white."""
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        rgba_image = image.convert('RGBA')
        background = Image.new('RGBA', rgba_image.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba_image)
    return image


def auto_trace_parameters(image: Image.Image) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Analyze an image and derive sensible tracing parameters automatically.
    Uses Otsu thresholding plus simple heuristics tailored to high-contrast logos/icons.
    """
    prepared = flatten_transparency(image)
    grayscale = prepared.convert('L')
    width, height = grayscale.size
    histogram = grayscale.histogram()
    total_pixels = sum(histogram) or 1
    sum_total = sum(i * count for i, count in enumerate(histogram))

    # Otsu's method for optimal threshold
    sumB = 0.0
    wB = 0
    max_between = 0.0
    otsu_threshold = 128

    for i, count in enumerate(histogram):
        wB += count
        if wB == 0:
            continue
        wF = total_pixels - wB
        if wF == 0:
            break
        sumB += i * count
        mB = sumB / wB
        mF = (sum_total - sumB) / wF
        between = wB * wF * (mB - mF) ** 2
        if between > max_between:
            max_between = between
            otsu_threshold = i

    otsu_threshold = max(1, min(254, otsu_threshold))

    mean_brightness = sum_total / total_pixels
    dark_pixels = sum(histogram[:otsu_threshold])
    dark_ratio = dark_pixels / total_pixels

    # Sample the border to infer the background brightness
    pixels = grayscale.load()
    border_margin = max(1, min(width, height) // 10)
    sample_step = max(1, min(width, height) // 200)  # avoid iterating every pixel on huge canvases
    border_sum = 0
    border_count = 0

    for y in range(0, height, sample_step):
        for x in range(0, width, sample_step):
            if x < border_margin or x >= width - border_margin or y < border_margin or y >= height - border_margin:
                border_sum += pixels[x, y]
                border_count += 1

    background_level = border_sum / border_count if border_count else mean_brightness
    # Invert only when the background is clearly dark so light artwork becomes traceable.
    invert = background_level < 110 and dark_ratio > 0.5
    invert_reason = "Detected dark background" if invert else "Detected light or mid-tone background"

    longest_edge = max(width, height)
    turdsize = max(1, min(10, longest_edge // 256))

    if dark_ratio < 0.25:
        alphamax = 0.7
        smoothing_reason = "Crisp edges preserved for sparse artwork"
    elif dark_ratio < 0.55:
        alphamax = 1.0
        smoothing_reason = "Balanced smoothing for mixed content"
    else:
        alphamax = 1.3
        smoothing_reason = "Extra smoothing for dense fills"

    params = {
        "threshold": int(otsu_threshold),
        "turdsize": int(turdsize),
        "alphamax": round(alphamax, 2),
        "opticurve": True,
        "invert": invert
    }

    analysis = {
        "mode": "auto",
        "stats": {
            "mean_brightness": round(mean_brightness, 2),
            "background_level": round(background_level, 2),
            "dark_ratio": round(dark_ratio, 3),
            "longest_edge": longest_edge
        },
        "strategy": {
            "threshold": f"Otsu (result: {params['threshold']})",
            "invert_reason": invert_reason,
            "smoothing_reason": smoothing_reason,
            "speckle_reason": f"Longest edge {longest_edge}px → speckle cleanup {params['turdsize']}px"
        },
        "notes": [
            invert_reason,
            f"Auto threshold locked at {params['threshold']} for maximum contrast.",
            smoothing_reason,
            f"Noise below ~{params['turdsize']}px removed for cleaner paths."
        ]
    }

    return params, analysis


def image_to_svg(
    image: Image.Image,
    threshold: int = 128,
    turdsize: int = 2,
    alphamax: float = 1.0,
    opticurve: bool = True,
    invert: bool = False
) -> str:
    """
    Convert PIL Image to SVG using potrace command-line tool.

    Args:
        image: PIL Image object
        threshold: Binarization threshold (0-255)
        turdsize: Minimum size of speckles to remove
        alphamax: Corner rounding parameter
        opticurve: Enable curve optimization

    Returns:
        SVG content as string
    """
    image = flatten_transparency(image)

    # Convert to grayscale after compositing any transparency.
    if image.mode != 'L':
        image = image.convert('L')

    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as bmp_file, \
         tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as svg_file:

        bmp_path = bmp_file.name
        svg_path = svg_file.name

    try:
        # Apply threshold and save as BMP (potrace requires BMP)
        # Convert to 1-bit (black and white) using threshold
        if invert:
            # Invert: black becomes white, white becomes black
            bw_image = image.point(lambda x: 0 if x > threshold else 255)
        else:
            bw_image = image.point(lambda x: 255 if x > threshold else 0)
        bw_image = bw_image.convert('1')  # Convert to 1-bit black and white
        bw_image.save(bmp_path, 'BMP')

        # Build potrace command
        cmd = ['potrace']

        # Output SVG
        cmd.extend(['-s', '-o', svg_path])

        # Turdsize (suppress speckles)
        cmd.extend(['-t', str(turdsize)])

        # Alphamax (corner threshold)
        cmd.extend(['-a', str(alphamax)])

        # Curve optimization
        if opticurve:
            cmd.extend(['-O', '0.2'])  # Default optimization tolerance
        else:
            cmd.append('-n')  # Turn off curve optimization

        # Input file
        cmd.append(bmp_path)

        # Run potrace
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise Exception(f"Potrace failed: {result.stderr}")

        # Read the generated SVG
        with open(svg_path, 'r') as f:
            svg_content = f.read()

        return svg_content

    finally:
        # Clean up temporary files
        try:
            os.unlink(bmp_path)
        except:
            pass
        try:
            os.unlink(svg_path)
        except:
            pass


def image_to_svg_centerline(
    image: Image.Image,
    threshold: int = 128,
    invert: bool = False,
    quality_mode: str = "balanced"
) -> str:
    """
    Convert PIL Image to SVG using autotrace centerline mode (generates strokes, not fills).

    Args:
        image: PIL Image object
        threshold: Binarization threshold (0-255)
        invert: Invert colors before tracing
        quality_mode: "fast", "balanced", or "maximum" - controls quality vs speed trade-off

    Returns:
        SVG content as string with strokes
    """
    image = flatten_transparency(image)

    # NO upscaling - it introduces smoothing artifacts that create waviness
    original_size = image.size

    # Convert to grayscale after compositing any transparency
    if image.mode != 'L':
        image = image.convert('L')

    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.bmp', delete=False) as bmp_file, \
         tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as svg_file:

        bmp_path = bmp_file.name
        svg_path = svg_file.name

    try:
        # Apply threshold and save as BMP
        if invert:
            bw_image = image.point(lambda x: 0 if x > threshold else 255)
        else:
            bw_image = image.point(lambda x: 255 if x > threshold else 0)
        bw_image = bw_image.convert('1')
        bw_image.save(bmp_path, 'BMP')

        # Quality-based parameter profiles
        params = {
            "fast": {
                "error-threshold": "2.0",
                "filter-iterations": "4",
                "line-reversion-threshold": "0.08",
            },
            "balanced": {
                "error-threshold": "1.0",
                "filter-iterations": "10",
                "line-reversion-threshold": "0.12",
                "corner-threshold": "100",
            },
            "maximum": {
                "error-threshold": "0.8",
                "filter-iterations": "12",
                "line-reversion-threshold": "0.15",
                "corner-threshold": "120",
            }
        }

        selected = params.get(quality_mode, params["balanced"])

        # Build autotrace command with centerline mode and optimized parameters
        cmd = ['autotrace']

        # Centerline mode (generates strokes instead of fills)
        cmd.append('-centerline')

        # Quality parameters optimized to reduce waviness
        cmd.extend(['-error-threshold', selected["error-threshold"]])
        cmd.extend(['-filter-iterations', selected["filter-iterations"]])
        cmd.extend(['-line-threshold', '1.0'])  # Consistent across modes

        # CRITICAL: line-reversion-threshold forces near-straight curves to straight lines
        cmd.extend(['-line-reversion-threshold', selected["line-reversion-threshold"]])

        if "corner-threshold" in selected:
            cmd.extend(['-corner-threshold', selected["corner-threshold"]])

        # Output format SVG
        cmd.extend(['-output-format', 'svg'])

        # Output file
        cmd.extend(['-output-file', svg_path])

        # Input file
        cmd.append(bmp_path)

        # Run autotrace
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=501,
                detail="Organic stroke mode requires autotrace, which is not installed on this server. Use 'geometric' stroke engine instead."
            )

        if result.returncode != 0:
            raise Exception(f"Autotrace failed: {result.stderr}")

        # Read the generated SVG
        with open(svg_path, 'r') as f:
            svg_content = f.read()

        # No need for viewBox scaling since we're not upscaling anymore

        return svg_content

    finally:
        # Clean up temporary files
        try:
            os.unlink(bmp_path)
        except:
            pass
        try:
            os.unlink(svg_path)
        except:
            pass


def image_to_svg_geometric(
    image: Image.Image,
    threshold: int = 128,
    invert: bool = False,
    stroke_width: float = 2.0
) -> str:
    """
    Convert PIL Image to SVG using skeletonization for geometric icons.

    This method is optimized for icons with straight lines, right angles,
    and precise geometry (like tech icons, UI elements, etc.)

    Args:
        image: PIL Image object
        threshold: Binarization threshold (0-255)
        invert: Invert colors before tracing
        stroke_width: Width of strokes in the output SVG

    Returns:
        SVG content as string with clean geometric strokes
    """
    import numpy as np
    from skimage import morphology
    from scipy import ndimage
    from collections import deque

    image = flatten_transparency(image)
    original_size = image.size

    # Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')

    # Convert to numpy array
    img_array = np.array(image)

    # Binarize
    if invert:
        binary = img_array <= threshold
    else:
        binary = img_array > threshold

    # Invert for skeletonization (skeletonize expects white foreground)
    binary = ~binary

    # Apply skeletonization to get centerlines
    skeleton = morphology.skeletonize(binary)

    # Get stroke width from distance transform
    dist_transform = ndimage.distance_transform_edt(binary)

    # Find all skeleton points and their connections
    skeleton_points = np.argwhere(skeleton)

    if len(skeleton_points) == 0:
        # Return empty SVG if no skeleton found
        return f'''<?xml version="1.0" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{original_size[0]}" height="{original_size[1]}" viewBox="0 0 {original_size[0]} {original_size[1]}">
</svg>'''

    # Build adjacency for skeleton pixels
    def get_neighbors(y, x, skel):
        """Get 8-connected neighbors that are part of skeleton."""
        neighbors = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < skel.shape[0] and 0 <= nx < skel.shape[1]:
                    if skel[ny, nx]:
                        neighbors.append((ny, nx))
        return neighbors

    # Trace paths through the skeleton
    visited = set()
    paths = []

    # Find endpoints and junctions
    endpoint_or_junction = []
    for y, x in skeleton_points:
        neighbors = get_neighbors(y, x, skeleton)
        if len(neighbors) != 2:  # endpoint (1) or junction (3+)
            endpoint_or_junction.append((y, x))

    # If no endpoints found, start from any point (closed loop)
    if not endpoint_or_junction:
        endpoint_or_junction = [(skeleton_points[0][0], skeleton_points[0][1])]

    def trace_path(start_y, start_x):
        """Trace a path from a starting point."""
        path = [(start_x, start_y)]  # Note: SVG uses (x, y)
        visited.add((start_y, start_x))

        current = (start_y, start_x)
        while True:
            neighbors = get_neighbors(current[0], current[1], skeleton)
            unvisited = [n for n in neighbors if n not in visited]

            if not unvisited:
                break

            # Continue to next point
            next_point = unvisited[0]
            visited.add(next_point)
            path.append((next_point[1], next_point[0]))  # (x, y) for SVG
            current = next_point

            # Stop at junctions
            if len(get_neighbors(current[0], current[1], skeleton)) != 2:
                break

        return path

    # Trace all paths
    for start_y, start_x in endpoint_or_junction:
        if (start_y, start_x) not in visited:
            neighbors = get_neighbors(start_y, start_x, skeleton)
            for ny, nx in neighbors:
                if (ny, nx) not in visited:
                    path = [(start_x, start_y)]
                    visited.add((start_y, start_x))

                    # Trace from neighbor
                    current = (ny, nx)
                    visited.add(current)
                    path.append((nx, ny))

                    while True:
                        curr_neighbors = get_neighbors(current[0], current[1], skeleton)
                        unvisited = [n for n in curr_neighbors if n not in visited]

                        if not unvisited:
                            break

                        next_point = unvisited[0]
                        visited.add(next_point)
                        path.append((next_point[1], next_point[0]))
                        current = next_point

                        if len(get_neighbors(current[0], current[1], skeleton)) != 2:
                            break

                    if len(path) > 1:
                        paths.append(path)

    # Also trace from any unvisited skeleton points (for isolated segments)
    for y, x in skeleton_points:
        if (y, x) not in visited:
            path = trace_path(y, x)
            if len(path) > 1:
                paths.append(path)

    # Simplify paths using Douglas-Peucker algorithm
    def douglas_peucker(points, epsilon=1.0):
        """Simplify a path using the Douglas-Peucker algorithm."""
        if len(points) <= 2:
            return points

        # Find point with maximum distance from line between first and last
        start = np.array(points[0])
        end = np.array(points[-1])

        max_dist = 0
        max_idx = 0

        line_vec = end - start
        line_len = np.linalg.norm(line_vec)

        if line_len == 0:
            return [points[0], points[-1]]

        line_unit = line_vec / line_len

        for i in range(1, len(points) - 1):
            point = np.array(points[i])
            vec_to_point = point - start
            proj_length = np.dot(vec_to_point, line_unit)
            proj_length = max(0, min(line_len, proj_length))
            closest = start + proj_length * line_unit
            dist = np.linalg.norm(point - closest)

            if dist > max_dist:
                max_dist = dist
                max_idx = i

        # If max distance is greater than epsilon, recursively simplify
        if max_dist > epsilon:
            left = douglas_peucker(points[:max_idx + 1], epsilon)
            right = douglas_peucker(points[max_idx:], epsilon)
            return left[:-1] + right
        else:
            return [points[0], points[-1]]

    # Snap angles to common values (0, 45, 90, 135, 180, etc.)
    def snap_angle(points, angle_tolerance=10):
        """Snap line segments to common angles."""
        if len(points) < 2:
            return points

        result = [points[0]]
        for i in range(1, len(points)):
            prev = result[-1]
            curr = points[i]

            dx = curr[0] - prev[0]
            dy = curr[1] - prev[1]

            if abs(dx) < 0.01 and abs(dy) < 0.01:
                continue

            angle = np.degrees(np.arctan2(dy, dx))

            # Snap to nearest 45-degree angle
            snap_angles = [0, 45, 90, 135, 180, -45, -90, -135, -180]
            for snap in snap_angles:
                if abs(angle - snap) < angle_tolerance:
                    # Recalculate endpoint based on snapped angle
                    length = np.sqrt(dx*dx + dy*dy)
                    new_dx = length * np.cos(np.radians(snap))
                    new_dy = length * np.sin(np.radians(snap))
                    curr = (prev[0] + new_dx, prev[1] + new_dy)
                    break

            result.append(curr)

        return result

    # Process paths: simplify and snap angles
    processed_paths = []
    for path in paths:
        if len(path) > 2:
            # Simplify with Douglas-Peucker
            simplified = douglas_peucker(path, epsilon=1.5)
            # Snap angles
            snapped = snap_angle(simplified, angle_tolerance=8)
            processed_paths.append(snapped)
        else:
            processed_paths.append(path)

    # Calculate average stroke width from distance transform
    if len(skeleton_points) > 0:
        avg_width = np.mean([dist_transform[y, x] for y, x in skeleton_points]) * 2
        stroke_width = max(1.0, avg_width)

    # Generate SVG
    svg_paths = []
    for path in processed_paths:
        if len(path) < 2:
            continue

        # Build path data
        d = f"M {path[0][0]:.1f},{path[0][1]:.1f}"
        for x, y in path[1:]:
            d += f" L {x:.1f},{y:.1f}"

        svg_paths.append(f'<path d="{d}" fill="none" stroke="black" stroke-width="{stroke_width:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')

    svg_content = f'''<?xml version="1.0" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{original_size[0]}" height="{original_size[1]}" viewBox="0 0 {original_size[0]} {original_size[1]}">
{chr(10).join(svg_paths)}
</svg>'''

    return svg_content


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "PNG to Vector Converter API",
        "version": "1.0.0"
    }


@app.post("/convert")
async def convert_png_to_svg(
    file: UploadFile = File(...),
    threshold: Optional[int] = Form(None),
    turdsize: Optional[int] = Form(None),
    alphamax: Optional[float] = Form(None),
    opticurve: Optional[bool] = Form(True),
    invert: Optional[bool] = Form(None),
    auto_mode: bool = Form(True),
    mode: str = Form("fill"),
    quality_mode: str = Form("balanced"),
    stroke_engine: str = Form("geometric")
):
    """
    Convert uploaded PNG image to vectorized SVG.

    Parameters:
    - file: PNG image file
    - mode: "fill" (potrace, filled shapes) or "stroke" (editable strokes)
    - stroke_engine: "geometric" (for icons with straight lines) or "organic" (for handwriting/illustrations)
    - quality_mode: "fast", "balanced", or "maximum" - quality vs speed trade-off (for organic stroke mode)
    - threshold: Binarization threshold (0-255, default: 128)
    - turdsize: Suppress speckles of up to this size (default: 2)
    - alphamax: Corner threshold parameter (default: 1.0)
    - opticurve: Use curve optimization (default: true)
    - invert: Invert colors before tracing (default: true for white backgrounds)
    - auto_mode: Auto-calculate optimal parameters (default: true)
    """
    start_time = time.time()

    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Store original size
        original_size = image.size

        use_auto = auto_mode or any(value is None for value in (threshold, turdsize, alphamax, invert))
        if use_auto:
            params, analysis = auto_trace_parameters(image)
        else:
            params = {
                "threshold": threshold if threshold is not None else 128,
                "turdsize": turdsize if turdsize is not None else 2,
                "alphamax": alphamax if alphamax is not None else 1.0,
                "opticurve": bool(opticurve) if opticurve is not None else True,
                "invert": invert if invert is not None else True
            }
            analysis = {
                "mode": "manual",
                "notes": ["Manual parameters provided by client"]
            }

        # Convert to SVG based on mode
        if mode == "stroke":
            if stroke_engine == "geometric":
                # Geometric mode: optimized for icons with straight lines and angles
                svg_content = image_to_svg_geometric(
                    image,
                    threshold=params["threshold"],
                    invert=params["invert"]
                )
                params["mode"] = "stroke"
                params["stroke_engine"] = "geometric"
                if analysis:
                    analysis["notes"] = analysis.get("notes", []) + [
                        "Using geometric tracing (skeletonization) for precise lines and angles"
                    ]
            else:
                # Organic mode: for handwriting, illustrations, natural shapes (autotrace)
                svg_content = image_to_svg_centerline(
                    image,
                    threshold=params["threshold"],
                    invert=params["invert"],
                    quality_mode=quality_mode
                )
                params["mode"] = "stroke"
                params["stroke_engine"] = "organic"
                params["quality_mode"] = quality_mode
                if analysis:
                    analysis["notes"] = analysis.get("notes", []) + [
                        f"Using organic tracing (autotrace centerline) for natural shapes (quality: {quality_mode})"
                    ]
        else:
            # Fill mode: generates filled shapes (potrace)
            svg_content = image_to_svg(
                image,
                threshold=params["threshold"],
                turdsize=params["turdsize"],
                alphamax=params["alphamax"],
                opticurve=params["opticurve"],
                invert=params["invert"]
            )
            params["mode"] = "fill"

        processing_time = time.time() - start_time

        return JSONResponse({
            "svg_content": svg_content,
            "original_size": list(original_size),
            "processing_time": round(processing_time, 3),
            "parameters": params,
            "auto_mode": use_auto,
            "analysis": analysis
        })

    except Exception as e:
        import traceback
        error_detail = f"Error processing image: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/health")
async def health():
    """Detailed health check."""
    # Check if potrace is available
    try:
        result = subprocess.run(['potrace', '--version'], capture_output=True, text=True)
        potrace_available = result.returncode == 0
        potrace_version = result.stdout.split('\n')[0] if potrace_available else "not found"
    except FileNotFoundError:
        potrace_available = False
        potrace_version = "not found"

    return {
        "status": "healthy" if potrace_available else "unhealthy",
        "potrace": potrace_version,
        "pil": "available"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
