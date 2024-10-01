# question_types/psychrometry.py

import matplotlib
matplotlib.use('Agg')  # Use the non-interactive Agg backend
import matplotlib.pyplot as plt
import numpy as np
import psychrolib
from psychrolib import GetHumRatioFromRelHum, GetTDryBulbFromEnthalpyAndHumRatio
from scipy.optimize import brentq
import io
import base64
import random

# Initialize PsychroLib to use SI units
psychrolib.SetUnitSystem(psychrolib.SI)

def find_T_sat(w2, pressure=101325):
    """
    Finds the dry-bulb temperature on the saturation curve for a given moisture content w2.
    """
    def func(T):
        try:
            return psychrolib.GetHumRatioFromRelHum(T, 1.0, pressure) - w2
        except:
            return 1e6  # Return a large value if computation fails

    T_min = -10
    T_max = 60

    try:
        w_min = psychrolib.GetHumRatioFromRelHum(T_min, 1.0, pressure)
        w_max = psychrolib.GetHumRatioFromRelHum(T_max, 1.0, pressure)
    except Exception as e:
        raise ValueError("Unable to compute saturation moisture content at the defined temperature bounds.")

    if w2 < w_min or w2 > w_max:
        raise ValueError(f"Moisture content w2={w2:.5f} kg/kg is outside the saturation curve range ({w_min:.5f} to {w_max:.5f} kg/kg).")

    T_sat = brentq(func, T_min, T_max)
    return T_sat

def plot_psychrometric_chart(point1, point2, colorblind=False):
    """
    Plots a psychrometric chart based on the provided two points and draws cooling and reheat lines.
    Returns a base64-encoded image.
    """
    # Extract temperatures and relative humidities
    T1, RH1 = point1
    T2, RH2 = point2

    # Ensure Point 2 has a lower temperature than Point 1
    if T2 >= T1:
        raise ValueError("Room Condition must have a lower temperature than Outside Condition.")

    # Calculate moisture contents
    try:
        w1 = GetHumRatioFromRelHum(T1, RH1 / 100.0, 101325)
    except Exception as e:
        raise ValueError(f"Invalid moisture content for Outside Condition: {e}")

    try:
        w2 = GetHumRatioFromRelHum(T2, RH2 / 100.0, 101325)
    except Exception as e:
        raise ValueError(f"Invalid moisture content for Room Condition: {e}")

    # Find intermediate cooling point on the saturation line with moisture content w2
    T_sat = find_T_sat(w2)

    # Define the range for dry-bulb temperature (°C)
    T_db = np.arange(-10, 61, 1)  # from -10°C to 60°C

    # Define Relative Humidity (RH) levels
    RH_levels = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    plt.figure(figsize=(14, 10))

    # Define color schemes
    if not colorblind:
        # Standard color scheme with requested changes
        rh_line_color = 'grey'               # Non-50% RH lines
        rh50_line_color = '#00008B'          # Dark Blue (almost black) for 50% RH
        saturation_color = '#00008B'         # Dark Blue (same as 50% RH) for 100% RH
        enthalpy_color = 'orange'            # Enthalpy lines
        point1_color = 'red'                 # Outside Condition
        point2_color = 'green'               # Room Condition
        cooling_line_color = 'blue'          # Cooling Line
        reheat_line_color = 'red'            # Reheat Line (changed to red)
        cooling_point_color = 'blue'         # Cooling Point (same as cooling line)
    else:
        # Color-blind-friendly color scheme
        rh_line_color = '#8DD3C7'            # Light Blue
        rh50_line_color = '#FFED6F'          # Yellow
        saturation_color = '#BEBADA'         # Lavender
        enthalpy_color = '#FB8072'           # Salmon
        point1_color = '#FDB462'             # Orange
        point2_color = '#80B1D3'             # Blue
        cooling_line_color = '#80B1D3'       # Blue
        reheat_line_color = '#FB8072'        # Salmon
        cooling_point_color = '#80B1D3'      # Blue

    # Plot constant RH lines
    for RH in RH_levels:
        w = []
        for T in T_db:
            try:
                w_val = GetHumRatioFromRelHum(T, RH / 100.0, 101325)
                w.append(w_val)
            except:
                w.append(np.nan)

        # Highlight the 50% RH line
        if RH == 50:
            plt.plot(T_db, w, linestyle='-', color=rh50_line_color, linewidth=2.5, label='_nolegend_')
        else:
            plt.plot(T_db, w, linestyle='--', color=rh_line_color, label='_nolegend_')

    # Plot saturation curve (100% RH)
    w_saturation = []
    for T in T_db:
        try:
            w_s = GetHumRatioFromRelHum(T, 1.0, 101325)
            w_saturation.append(w_s)
        except:
            w_saturation.append(np.nan)
    plt.plot(T_db, w_saturation, label='Saturation (100% RH)', color=saturation_color, linewidth=2)

    # Plot enthalpy lines (optional)
    enthalpy_values = np.arange(0, 1000, 100)  # Example: every 100 kJ/kg
    for h in enthalpy_values:
        w_enthalpy = []
        T_enthalpy = []
        for w in np.linspace(0, 0.030, 100):  # 0 to 0.030 kg/kg
            try:
                T = GetTDryBulbFromEnthalpyAndHumRatio(h, w, 101325)
                w_enthalpy.append(w)
                T_enthalpy.append(T)
            except:
                continue
        plt.plot(T_enthalpy, w_enthalpy, linestyle=':', color=enthalpy_color, label='_nolegend_')

    # Plot Outside Condition and Room Condition
    plt.plot(T1, w1, 'o', label=f'Outside Condition: {T1}°C, {RH1}% RH', markersize=8, color=point1_color)
    plt.plot(T2, w2, 'o', label=f'Room Condition: {T2}°C, {RH2}% RH', markersize=8, color=point2_color)

    # Plot intermediate cooling point
    plt.plot(T_sat, w2, 'o', label=f'Cooling Point: {T_sat:.2f}°C, {w2:.3f} kg/kg', markersize=8, color=cooling_point_color)

    # Draw Cooling Line from Outside Condition to Cooling Point
    plt.plot([T1, T_sat], [w1, w2], linestyle='-', color=cooling_line_color, linewidth=2, label='Cooling Line')

    # Draw Reheat Line from Cooling Point to Room Condition
    plt.plot([T_sat, T2], [w2, w2], linestyle='-', color=reheat_line_color, linewidth=2, label='Reheat Line')

    # Customize the plot
    plt.title('Psychrometric Chart Solution', fontsize=16)
    plt.xlabel('Dry-Bulb Temperature (°C)', fontsize=14)
    plt.ylabel('Moisture Content (kg/kg)', fontsize=14)  # Updated label
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Move Y-axis to the right
    ax = plt.gca()
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_ylim(0, 0.030)   # 0 to 0.030 kg/kg

    # Set Y-axis ticks at increments of 0.001 kg/kg
    y_ticks = np.arange(0, 0.031, 0.001)  # Up to 0.030 kg/kg
    ax.set_yticks(y_ticks)

    # Set X-axis ticks at increments of 5°C
    x_ticks = np.arange(-10, 65, 5)  # Up to 60°C
    ax.set_xticks(x_ticks)

    ax.set_xlim(-10, 60)    # -10°C to 60°C

    # Adjust Y-axis labels to display up to three decimal places
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.3f}'))

    # Enhance legend: include relevant labels
    handles, labels = ax.get_legend_handles_labels()
    filtered = [(h, l) for h, l in zip(handles, labels) if l != '_nolegend_']
    if filtered:
        plt.legend(*zip(*filtered), loc='upper left', fontsize='small', ncol=2, framealpha=0.9)

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close()
    buf.seek(0)

    # Encode the image to base64
    encoded_image = base64.b64encode(buf.read()).decode('utf-8')
    image_data = f"data:image/png;base64,{encoded_image}"

    return image_data

def generate_question():
    """
    Generates a psychrometry question involving plotting two points and drawing cooling/reheat lines.
    """
    # Generate Point 1 within specified ranges
    T1 = random.randint(28, 35)        # °C
    RH1 = random.randint(40, 70)       # %

    # Generate Point 2 within specified ranges
    T2 = random.randint(16, 24)        # °C
    RH2 = random.randint(40, 60)       # %

    question = {
        "prompt": "Plot the following two conditions and draw the cooling/reheat lines:",
        "points": {
            "point1": {
                "temperature": T1,
                "relative_humidity": RH1
            },
            "point2": {
                "temperature": T2,
                "relative_humidity": RH2
            }
        }
    }

    return question
