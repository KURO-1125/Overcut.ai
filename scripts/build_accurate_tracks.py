import json
import math
import os
import numpy as np
from scipy.interpolate import splprep, splev

def build_monaco_from_telemetry():
    """Extracts exact FastF1 Monaco Qualifying telemetry (identical to Image 1)."""
    import fastf1
    fastf1.Cache.enable_cache('data/raw_cache')
    session = fastf1.get_session(2023, 'Monaco', 'Q')
    session.load(telemetry=True, laps=True)
    lap = session.laps.pick_fastest()
    telemetry = lap.get_telemetry().dropna(subset=['X', 'Y'])
    circuit_info = session.get_circuit_info()

    times = telemetry['Time'].dt.total_seconds().tolist()
    t0 = times[0]
    norm_times = [round(t - t0, 3) for t in times]
    distances = telemetry['Distance'].values
    times_np = np.array(norm_times)

    corners = []
    for _, row in circuit_info.corners.iterrows():
        c_dist = row['Distance']
        c_idx = int(np.argmin(np.abs(distances - c_dist)))
        c_time = round(float(times_np[c_idx]), 1)
        c_num = int(row['Number'])
        c_letter = str(row['Letter']) if str(row['Letter']) != 'nan' else ''
        corners.append({
            'id': f'T{c_num}{c_letter}',
            'name': f'Turn {c_num}{c_letter}',
            'start': max(0.0, round(c_time - 2.0, 1)),
            'end': round(c_time + 2.0, 1),
            'type': 'Circuit Turn',
            'mid_t': c_time
        })

    xs = telemetry['X'].values
    ys = telemetry['Y'].values
    pad, bw, bh = 25, 320, 380
    x_min, x_max = float(xs.min()), float(xs.max())
    y_min, y_max = float(ys.min()), float(ys.max())

    track_points = []
    svg_parts = []
    for i in range(len(xs)):
        sx = round(pad + ((float(xs[i]) - x_min) / (x_max - x_min)) * (bw - 2 * pad), 1)
        sy = round(pad + (1.0 - (float(ys[i]) - y_min) / (y_max - y_min)) * (bh - 2 * pad), 1)
        track_points.append({
            't': norm_times[i],
            'x': sx,
            'y': sy,
            'spd': int(telemetry['Speed'].iloc[i])
        })
        prefix = 'M' if i == 0 else 'L'
        svg_parts.append(f'{prefix} {sx} {sy}')
    svg_parts.append('Z')

    corner_pins = []
    for c in corners:
        closest_idx = int(np.argmin([abs(pt['t'] - c['mid_t']) for pt in track_points]))
        corner_pins.append({
            'id': c['id'],
            'name': c['name'],
            'x': track_points[closest_idx]['x'],
            'y': track_points[closest_idx]['y'],
            'start': c['start'],
            'end': c['end'],
            'type': c['type'],
            'speed': int(telemetry['Speed'].iloc[closest_idx])
        })

    return {
        'viewBox': '0 0 320 380',
        'svg_path': ' '.join(svg_parts),
        'points': track_points,
        'corner_pins': corner_pins,
        'circuit_name': 'Circuit de Monaco',
        'location': 'Monte Carlo, Monaco',
        'lap_len': '3.337 km',
        'start_finish': {'x': track_points[0]['x'], 'y': track_points[0]['y']}
    }

def process_geojson_circuit(coords, name, location, lap_len, rotation_deg=0.0, corner_defs=None, lap_time=80.0):
    """Processes real GPS coordinates into normalized SVG and corner pins."""
    raw = np.array(coords, dtype=float)
    lons = raw[:, 0]
    lats = raw[:, 1]
    mean_lat = math.radians(np.mean(lats))
    
    # Project to Cartesian metric space
    xm = (lons - np.mean(lons)) * math.cos(mean_lat) * 111320.0
    ym = (lats - np.mean(lats)) * 110540.0
    
    # Apply rotation if specified (to match FIA broadcast orientation)
    if rotation_deg != 0.0:
        rad = math.radians(rotation_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        rot_x = xm * cos_a - ym * sin_a
        rot_y = xm * sin_a + ym * cos_a
        xm, ym = rot_x, rot_y

    # Spline smoothing across closed loop
    try:
        tck, u = splprep([xm, ym], s=0, per=True)
        u_new = np.linspace(0, 1, 350, endpoint=False)
        smooth_x, smooth_y = splev(u_new, tck)
    except Exception:
        # Fallback linear if splprep fails
        u_old = np.linspace(0, 1, len(xm))
        u_new = np.linspace(0, 1, 350, endpoint=False)
        smooth_x = np.interp(u_new, u_old, xm)
        smooth_y = np.interp(u_new, u_old, ym)

    pad = 25
    bw, bh = 320, 380
    min_x, max_x = float(smooth_x.min()), float(smooth_x.max())
    min_y, max_y = float(smooth_y.min()), float(smooth_y.max())
    span_x = max(max_x - min_x, 1e-5)
    span_y = max(max_y - min_y, 1e-5)
    
    scale = min((bw - 2 * pad) / span_x, (bh - 2 * pad) / span_y)
    off_x = pad + ((bw - 2 * pad) - span_x * scale) / 2.0
    off_y = pad + ((bh - 2 * pad) - span_y * scale) / 2.0
    
    svg_x = np.round(off_x + (smooth_x - min_x) * scale, 1)
    svg_y = np.round(off_y + (max_y - smooth_y) * scale, 1) # Invert Y for SVG
    
    n_pts = len(svg_x)
    track_points = []
    svg_parts = []
    
    for i in range(n_pts):
        sx = float(svg_x[i])
        sy = float(svg_y[i])
        t = round((i / float(n_pts)) * lap_time, 2)
        track_points.append({'t': t, 'x': sx, 'y': sy, 'spd': 225})
        prefix = 'M' if i == 0 else 'L'
        svg_parts.append(f'{prefix} {sx} {sy}')
    svg_parts.append('Z')
    
    # Calculate corner pins
    corner_pins = []
    if corner_defs:
        for c in corner_defs:
            ratio = c.get('ratio', 0.5)
            target_t = round(ratio * lap_time, 1)
            idx = int(ratio * (n_pts - 1))
            pt = track_points[idx]
            corner_pins.append({
                'id': f"T{c['num']}",
                'name': f"Turn {c['num']} {c['name']}",
                'x': pt['x'],
                'y': pt['y'],
                'start': max(0.0, round(target_t - 2.0, 1)),
                'end': round(target_t + 2.0, 1),
                'type': c.get('desc', 'Circuit Corner'),
                'speed': c.get('speed', 150)
            })
            
    return {
        'viewBox': '0 0 320 380',
        'svg_path': ' '.join(svg_parts),
        'points': track_points,
        'corner_pins': corner_pins,
        'circuit_name': name,
        'location': location,
        'lap_len': lap_len,
        'start_finish': {'x': track_points[0]['x'], 'y': track_points[0]['y']}
    }

if __name__ == '__main__':
    print('Testing build_monaco_from_telemetry...')
    m = build_monaco_from_telemetry()
    print('Monaco built! Points:', len(m['points']), 'Corners:', len(m['corner_pins']))
