# question_types/wall_heat_loss.py

import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import random
import logging
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)  # Set to INFO for standard logs

# Define the path to the Data directory
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data', 'Walls'))
logging.debug(f"DATA_DIR resolved to: {DATA_DIR}")

def load_json(file_name):
    """
    Utility function to load JSON data from the Data/Walls directory.

    Parameters:
    - file_name (str): Name of the JSON file.

    Returns:
    - dict: Parsed JSON data.
    """
    file_path = os.path.join(DATA_DIR, file_name)
    logging.debug(f"Attempting to load file: {file_path}")
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            logging.info(f"Loaded data from {file_name} successfully.")
            return data
    except FileNotFoundError:
        logging.error(f"File {file_name} not found in {DATA_DIR}.")
        if os.path.exists(DATA_DIR):
            available_files = os.listdir(DATA_DIR)
            logging.error(f"Available files in {DATA_DIR}: {available_files}")
        else:
            logging.error(f"Directory {DATA_DIR} does not exist.")
        raise
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from file {file_name}.")
        raise

# Load data from JSON files
try:
    materials_thickness_mm = load_json('standard_thicknesses.json')
    standard_constructions = load_json('standard_constructions.json')
    thermal_properties = load_json('thermal_properties.json')
except Exception as e:
    logging.critical(f"Failed to load necessary data files: {e}")
    raise

# Extract k and R values
materials_k = thermal_properties.get('k_values', {})
materials_R = thermal_properties.get('R_values', {})

def plot_heat_loss_calculation(length, height, layers, T_inside, T_outside):
    """
    Calculates and plots heat loss through a multilayer wall, including Rsi and Rso.

    Parameters:
    - length (float): Length of the wall in meters.
    - height (float): Height of the wall in meters.
    - layers (list of dict): Each dict contains 'material', 'thickness' (m), 'k' (W/mK) or 'R' (m²K/W).
    - T_inside (float): Inside temperature in °C.
    - T_outside (float): Outside temperature in °C.

    Returns:
    - base64-encoded image string.
    """
    logging.info("Starting heat loss calculation.")
    # Define surface resistances (Rsi and Rso)
    Rsi = 0.13  # Internal surface resistance in m²K/W
    Rso = 0.04  # External surface resistance in m²K/W

    # Insert Rsi at the beginning and Rso at the end of the layers
    layers_with_surfaces = [{'material': 'Internal Surface (Rsi)', 'thickness': 0, 'R': Rsi}] + layers + [{'material': 'External Surface (Rso)', 'thickness': 0, 'R': Rso}]

    # Calculate total area
    area = length * height  # m²
    logging.info(f"Wall area: {area} m²")

    # Calculate thermal resistance of each layer
    R_values = []
    for layer in layers_with_surfaces:
        material = layer.get('material')
        thickness = layer.get('thickness')
        if 'k' in layer and layer['k'] is not None:
            R = thickness / layer['k']
            logging.debug(f"Layer '{material}' with thickness {thickness} m and k {layer['k']} W/mK has R = {R} m²K/W")
        elif 'R' in layer:
            R = layer['R']
            logging.debug(f"Layer '{material}' has R = {R} m²K/W")
        else:
            error_msg = f"Layer '{material}' must have either 'k' or 'R' defined."
            logging.error(error_msg)
            raise ValueError(error_msg)
        R_values.append(R)

    # Total thermal resistance
    R_total = sum(R_values)
    logging.info(f"Total thermal resistance (R_total): {R_total} m²K/W")

    # Heat transfer (Q) = (T_inside - T_outside) / R_total * area
    Q = (T_inside - T_outside) * area / R_total  # Watts
    logging.info(f"Heat Loss (Q): {Q} W")

    # Calculate U-value
    U_value = 1 / R_total  # W/m²K
    logging.info(f"U-value (Overall): {U_value} W/m²K")

    # Plotting the calculation
    layers_names = [layer['material'] for layer in layers_with_surfaces]
    plt.figure(figsize=(10, 6))

    # Use a fixed sky blue color for all bars
    bar_color = 'skyblue'

    bars = plt.barh(layers_names, R_values, color=bar_color, edgecolor='black')

    # Determine the maximum R-value
    max_R = max(R_values)
    threshold = 0.2 * max_R  # 20% of the maximum R-value
    logging.info(f"Max R-value: {max_R} m²K/W, Threshold for label positioning: {threshold} m²K/W")

    for bar, R in zip(bars, R_values):
        bar_width = bar.get_width()

        if R <= threshold:
            # Place label outside the bar to the right with white background
            plt.text(bar_width + 0.02, bar.get_y() + bar.get_height()/2,
                     f'R = {R:.2f} m²K/W',
                     va='center', ha='left', color='black', fontsize=10,
                     bbox=dict(facecolor='white', edgecolor='none', alpha=0.7))
            logging.debug(f"Placed R-value label outside for R = {R}")
        else:
            # Place label inside the bar with black text
            plt.text(bar_width / 2, bar.get_y() + bar.get_height()/2,
                     f'R = {R:.2f} m²K/W',
                     va='center', ha='center', color='black', fontsize=10)
            logging.debug(f"Placed R-value label inside for R = {R}")

    plt.xlabel('Thermal Resistance (m²K/W)', fontsize=14)
    plt.title('Thermal Resistance of Wall Layers', fontsize=16)
    plt.grid(axis='x', linestyle='--', alpha=0.7)

    # Annotate total thermal resistance, heat loss, and U-value
    annotation_text = (
        f'R_total = {R_total:.2f} m²K/W\n'
        f'Heat Loss Q = {Q:.2f} W\n'
        f'U-value (Overall) = {U_value:.2f} W/m²K'
    )
    plt.text(1.02, 0.95, annotation_text,
             horizontalalignment='left',
             verticalalignment='top',
             transform=plt.gca().transAxes,
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'))
    logging.debug("Added annotations to the chart.")

    # Adjust layout to accommodate annotations
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close()
    buf.seek(0)

    # Encode the image to base64
    encoded_image = base64.b64encode(buf.read()).decode('utf-8')
    image_data = f"data:image/png;base64,{encoded_image}"
    logging.info("Heat loss chart generated successfully.")

    return image_data

def generate_question(num_layers=3):
    """
    Generates a heat loss question with predefined wall types based on the number of layers.

    Parameters:
    - num_layers (int): Number of wall layers (1 to 6).

    Returns:
    - dict: Question prompt and parameters.
    """
    # Ensure num_layers is between 1 and 6
    num_layers = max(1, min(num_layers, 6))

    # Select predefined wall types based on the number of layers
    wall_types = standard_constructions.get(str(num_layers), [])

    if not wall_types:
        error_msg = f"No predefined wall types for {num_layers} layers."
        logging.error(error_msg)
        raise ValueError(error_msg)

    selected_wall = random.choice(wall_types)
    logging.info(f"Selected wall type: {selected_wall['name']} with {num_layers} layers.")

    # Convert thickness from mm to meters and assign k or R values
    converted_layers = []
    for layer in selected_wall["layers"]:
        material = layer["material"]
        available_thicknesses = materials_thickness_mm.get(material)
        if not available_thicknesses:
            error_msg = f"No standard thicknesses found for material '{material}'."
            logging.error(error_msg)
            raise ValueError(error_msg)
        thickness_mm = random.choice(available_thicknesses)
        thickness_m = thickness_mm / 1000  # Convert mm to m

        if material in materials_k and materials_k[material] is not None:
            converted_layers.append({
                "material": material,
                "thickness": thickness_m,
                "k": materials_k[material]
            })
            logging.debug(f"Assigned k-value for material '{material}': {materials_k[material]} W/mK")
        elif material in materials_R:
            converted_layers.append({
                "material": material,
                "thickness": thickness_m,
                "R": materials_R[material]
            })
            logging.debug(f"Assigned R-value for material '{material}': {materials_R[material]} m²K/W")
        else:
            error_msg = f"Material '{material}' must have either 'k' or 'R' defined."
            logging.error(error_msg)
            raise ValueError(error_msg)

    # Define wall dimensions
    length = round(random.uniform(3, 10), 2)  # meters
    height = round(random.uniform(2, 5), 2)   # meters
    logging.info(f"Wall dimensions: Length = {length} m, Height = {height} m")

    # Define temperature difference
    T_inside = random.randint(18, 25)    # °C
    T_outside = random.randint(-5, 5)    # °C
    logging.info(f"Temperature inside: {T_inside}°C, Temperature outside: {T_outside}°C")

    question = {
        "prompt": f"Determine the heat loss through the following multilayer wall ({selected_wall['name']}):",
        "parameters": {
            "length": length,
            "height": height,
            "layers": converted_layers,
            "T_inside": T_inside,
            "T_outside": T_outside
        }
    }

    logging.info("Question generated successfully.")
    return question
