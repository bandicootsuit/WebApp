# question_types/thermal_bridging.py

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

# Define the path to the ThermalBridging Data directory
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Data', 'ThermalBridging'))
logging.debug(f"ThermalBridging DATA_DIR resolved to: {DATA_DIR}")

def load_json(file_name):
    """
    Utility function to load JSON data from the Data/ThermalBridging directory.

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
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from file {file_name}: {e}")
        raise

# Load data from JSON files
try:
    tb_materials_thickness_mm = load_json('standard_thicknesses.json')
    tb_standard_constructions = load_json('standard_constructions.json')
    tb_thermal_properties = load_json('thermal_properties.json')
except Exception as e:
    logging.critical(f"Failed to load necessary ThermalBridging data files: {e}")
    raise

# Extract k and R values
tb_materials_k = tb_thermal_properties.get('k_values', {})
tb_materials_R = tb_thermal_properties.get('R_values', {})

def calculate_R_parallel(fractions, R_values):
    """
    Calculates the parallel thermal resistance for mixed layers.

    Parameters:
    - fractions (list of float): List of surface area fractions (should sum to 1).
    - R_values (list of float): List of thermal resistances for each parallel path.

    Returns:
    - float: Combined parallel thermal resistance.
    """
    reciprocal_R = 0
    for fraction, R in zip(fractions, R_values):
        reciprocal_R += fraction / R
    R_total = 1 / reciprocal_R
    logging.debug(f"Calculated R_parallel: {R_total} m²K/W")
    return R_total

def plot_thermal_bridging_calculation(length, height, layers, T_inside, T_outside):
    """
    Calculates and plots heat loss through a wall with thermal bridging.

    Parameters:
    - length (float): Length of the wall in meters.
    - height (float): Height of the wall in meters.
    - layers (list of dict): Each dict contains 'material', 'thickness' (m), and optional 'insulation' and 'additional_insulation' dicts.
    - T_inside (float): Inside temperature in °C.
    - T_outside (float): Outside temperature in °C.

    Returns:
    - base64-encoded image string.
    """
    logging.info("Starting thermal bridging heat loss calculation.")
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
    layer_names = []
    for layer in layers_with_surfaces:
        material = layer.get('material')
        thickness = layer.get('thickness')
        if 'insulation' in layer:
            # Mixed layer with thermal bridging
            insulation = layer['insulation']
            insulation_material = insulation['material']
            structural_percentage = layer.get('structural_percentage', 0.1)  # Default to 10% if not set
            insulation_percentage = 1 - structural_percentage  # Remaining percentage
            insulation_thickness = thickness
            insulation_k = insulation['k']
            fraction = insulation_percentage
            R_insulation = insulation_thickness / insulation_k
            R_structural = thickness / tb_materials_k.get(layer.get('structural_material', '').lower().replace(' ', '_'), 0.2)  # Default k=0.2 W/mK if not found
            R_parallel = calculate_R_parallel([fraction, 1 - fraction], [R_insulation, R_structural])
            R_values.append(R_parallel)
            layer_names.append("Multi-layer")  # Set to "Multi-layer"
            logging.debug(f"Layer '{material}' is a mixed layer with R_parallel = {R_parallel} m²K/W")
        elif 'R' in layer:
            R = layer['R']
            R_values.append(R)
            layer_names.append(material)
            logging.debug(f"Layer '{material}' has R = {R} m²K/W")
        elif 'k' in layer and layer['k'] is not None:
            R = thickness / layer['k']
            R_values.append(R)
            layer_names.append(material)
            logging.debug(f"Layer '{material}' with thickness {thickness} m and k {layer['k']} W/mK has R = {R} m²K/W")

        else:
            error_msg = f"Layer '{material}' must have either 'k', 'R', or 'insulation' defined."
            logging.error(error_msg)
            raise ValueError(error_msg)

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
    plt.figure(figsize=(10, 6))

    # Use a fixed sky blue color for all bars
    bar_color = 'skyblue'

    bars = plt.barh(layer_names, R_values, color=bar_color, edgecolor='black')

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
    plt.title('Thermal Resistance of Wall Layers with Thermal Bridging', fontsize=16)
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
    logging.info("Thermal bridging heat loss chart generated successfully.")

    return image_data

def generate_thermal_bridging_question(num_layers=3):
    """
    Generates a thermal bridging heat loss question based on the number of layers.

    Parameters:
    - num_layers (int): Number of wall layers (3, 4, or 5).

    Returns:
    - dict: Question prompt and parameters.
    """
    # Ensure num_layers is between 3 and 5 as per provided examples
    num_layers = max(3, min(num_layers, 5))

    # Select predefined wall types based on the number of layers
    wall_types = tb_standard_constructions.get(str(num_layers), [])

    if not wall_types:
        error_msg = f"No predefined thermal bridging wall types for {num_layers} layers."
        logging.error(error_msg)
        raise ValueError(error_msg)

    selected_wall = random.choice(wall_types)
    logging.info(f"Selected thermal bridging wall type: {selected_wall['name']} with {num_layers} layers.")

    # Convert thickness from mm to meters and assign k or R values
    converted_layers = []
    for layer in selected_wall["layers"]:
        material = layer["material"]
        # For mixed layers, material name includes ' & Insulation'
        if ' & Insulation' in material:
            structural_material_name = material.split(' & ')[0].title()  # e.g., "Metal Frame"
            base_material_key = structural_material_name.lower().replace(' ', '_')  # e.g., "metal_frame"
            available_thicknesses = tb_materials_thickness_mm.get(base_material_key)
        else:
            structural_material_name = None
            base_material_key = material.lower().replace(' ', '_')
            available_thicknesses = tb_materials_thickness_mm.get(base_material_key)

        if not available_thicknesses:
            error_msg = f"No standard thicknesses found for material '{material}'."
            logging.error(error_msg)
            raise ValueError(error_msg)
        thickness_mm = random.choice(available_thicknesses)
        thickness_m = thickness_mm / 1000  # Convert mm to m

        if 'insulation' in layer:
            insulation = layer['insulation']
            insulation_material_key = insulation['material'].lower().replace(' ', '_')
            insulation_material = insulation['material'].replace('_', ' ').title()
            insulation_thickness_mm = tb_materials_thickness_mm.get(insulation_material_key, [100])[0]
            insulation_thickness_m = insulation_thickness_mm / 1000  # Convert mm to m
            insulation_k = tb_materials_k.get(insulation_material_key, 0.04)  # Default k=0.04 W/mK

            # Handle percentage_range for structural components
            percentage_range = layer.get('percentage_range', [5, 15])  # Default range
            structural_percentage = random.uniform(percentage_range[0], percentage_range[1])
            insulation_percentage_actual = 100 - structural_percentage

            # Convert percentages to fractions
            structural_fraction = structural_percentage / 100
            insulation_fraction = insulation_percentage_actual / 100

            # Assign a generic name for combined layers
            combined_name = "Multi-layer"

            converted_layer = {
                "material": combined_name,
                "thickness": thickness_m,
                "k": tb_materials_k.get(base_material_key, 0.2),  # Structural material k-value
                "structural_material": structural_material_name,  # Actual structural material name
                "structural_percentage": structural_fraction,
                "insulation": {
                    "material": insulation_material,
                    "percentage": insulation_percentage_actual,
                    "thickness": insulation_thickness_m,
                    "k": insulation_k
                }
            }

            # Check for additional insulation
            if 'additional_insulation' in layer:
                additional_insulation = layer['additional_insulation']
                additional_material_key = additional_insulation['material'].lower().replace(' ', '_')
                additional_material = additional_insulation['material'].replace('_', ' ').title()
                additional_percentage = additional_insulation.get('percentage', 0)
                additional_thickness_mm = tb_materials_thickness_mm.get(additional_material_key, [100])[0]
                additional_thickness_m = additional_thickness_mm / 1000  # Convert mm to m
                additional_k = tb_materials_k.get(additional_material_key, 0.03)  # Default k=0.03 W/mK

                converted_layer["additional_insulation"] = {
                    "material": additional_material,
                    "percentage": additional_percentage,
                    "thickness": additional_thickness_m,
                    "k": additional_k
                }

            converted_layers.append(converted_layer)
            logging.debug(f"Assigned mixed layer for '{combined_name}' with insulation.")
        else:
            if base_material_key in tb_materials_k and tb_materials_k[base_material_key] is not None:
                converted_layers.append({
                    "material": material.replace('_', ' ').title(),
                    "thickness": thickness_m,
                    "k": tb_materials_k[base_material_key]
                })
                logging.debug(f"Assigned k-value for material '{material}': {tb_materials_k[base_material_key]} W/mK")
            elif base_material_key in tb_materials_R:
                converted_layers.append({
                    "material": material.replace('_', ' ').title(),
                    "thickness": thickness_m,
                    "R": tb_materials_R[base_material_key]
                })
                logging.debug(f"Assigned R-value for material '{material}': {tb_materials_R[base_material_key]} m²K/W")
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
        "prompt": f"Determine the heat loss through the following wall with thermal bridging ({selected_wall['name']}):",
        "parameters": {
            "length": length,
            "height": height,
            "layers": converted_layers,
            "T_inside": T_inside,
            "T_outside": T_outside
        }
    }

    logging.info("Thermal bridging question generated successfully.")
    return question
