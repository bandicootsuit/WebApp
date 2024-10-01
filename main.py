# main.py

from flask import Flask, render_template, request, jsonify
import os
import logging
from question_types import psychrometry, wall_heat_loss, thermal_bridging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)  # Set to INFO for standard logs

# ----------------- Main Menu Route -----------------

@app.route('/')
def main_menu():
    """
    Renders the main menu interface.
    """
    return render_template('index.html')

# ----------------- Psychrometry Routes -----------------

@app.route('/psychrometry')
def psychrometry_menu():
    """
    Renders the psychrometric chart question interface.
    """
    return render_template('psychrometry.html')

@app.route('/psychrometry/generate_question', methods=['GET'])
def generate_psychrometry_question():
    """
    Generates a multi-part psychrometric chart question.
    """
    try:
        question = psychrometry.generate_question()
        logging.info("Generated psychrometry question successfully.")
        return jsonify(question)
    except Exception as e:
        logging.error(f"Error generating psychrometry question: {e}")
        return jsonify({"error": "Failed to generate psychrometry question."}), 500

@app.route('/psychrometry/show_solution', methods=['POST'])
def show_psychrometry_solution():
    """
    Generates the solution for a multi-part psychrometric question.
    Expects JSON data with 'point1', 'point2', 'mass_flow', and 'Cp'.
    """
    data = request.get_json()

    if not data:
        logging.error("No data provided in the show solution request.")
        return jsonify({"error": "No data provided."}), 400

    try:
        # Extract data
        point1 = data.get('point1')
        point2 = data.get('point2')
        mass_flow = data.get('mass_flow')
        Cp = data.get('Cp')
        colorblind = data.get('colorblind', False)  # Optional

        # Validate inputs
        if not all([point1, point2, mass_flow, Cp]):
            logging.error("Incomplete data provided for solution generation.")
            return jsonify({"error": "Incomplete data provided."}), 400

        # Generate the solution
        question_data = {
            "data": {
                "Outside Condition": point1,
                "Room Condition": point2,
                "Mass flow of air": f"{mass_flow} kg/s",
                "Cp for moist air": f"{Cp} kJ/kg-K"
            }
        }

        solution = psychrometry.generate_solution(question_data)

        logging.info("Generated psychrometric chart solution successfully.")

        return jsonify(solution)

    except ValueError as ve:
        logging.error(f"ValueError: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred while generating the solution."}), 500

# ----------------- Wall Heat Loss Routes -----------------

@app.route('/heat_loss')
def heat_loss_menu():
    """
    Renders the wall heat loss question interface.
    """
    return render_template('wall_heat_loss.html')

@app.route('/heat_loss/generate_question', methods=['POST'])
def generate_heat_loss_question():
    """
    Generates a wall heat loss question along with its solution.
    Expects JSON data with 'num_layers' (int).
    """
    data = request.get_json()

    if not data:
        logging.error("No data provided in the heat loss request.")
        return jsonify({"error": "No data provided."}), 400

    num_layers = data.get('num_layers', 3)  # Default to 3 if not provided

    # Validate num_layers
    if not isinstance(num_layers, int) or not (1 <= num_layers <= 6):
        logging.error(f"Invalid number of layers received for heat loss: {num_layers}")
        return jsonify({"error": "Number of layers must be an integer between 1 and 6."}), 400

    try:
        # Generate the question
        question = wall_heat_loss.generate_question(num_layers=num_layers)
        logging.info(f"Generated wall heat loss question with {num_layers} layers successfully.")

        # Generate the solution (heat loss chart)
        solution_image = wall_heat_loss.plot_heat_loss_calculation(
            length=question['parameters']['length'],
            height=question['parameters']['height'],
            layers=question['parameters']['layers'],
            T_inside=question['parameters']['T_inside'],
            T_outside=question['parameters']['T_outside']
        )
        logging.info("Generated wall heat loss chart successfully.")

        # Prepare the response
        response = {
            "prompt": question['prompt'],
            "parameters": question['parameters'],
            "solution_image": solution_image  # Base64-encoded image
        }

        return jsonify(response)

    except ValueError as ve:
        logging.error(f"ValueError during wall heat loss question/solution generation: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"Unexpected error during wall heat loss question/solution generation: {e}")
        return jsonify({"error": "An unexpected error occurred while generating the wall heat loss question and solution."}), 500

# ----------------- Thermal Bridging Routes -----------------

@app.route('/thermal_bridging')
def thermal_bridging_menu():
    """
    Renders the thermal bridging heat loss question interface.
    """
    return render_template('thermal_bridging.html')

@app.route('/thermal_bridging/generate_question', methods=['POST'])
def generate_thermal_bridging_question():
    """
    Generates a thermal bridging heat loss question along with its solution.
    Expects JSON data with 'num_layers' (int).
    """
    data = request.get_json()

    if not data:
        logging.error("No data provided in the thermal bridging request.")
        return jsonify({"error": "No data provided."}), 400

    num_layers = data.get('num_layers', 3)  # Default to 3 if not provided

    # Validate num_layers (should be between 3 and 5 as per examples)
    if not isinstance(num_layers, int) or not (3 <= num_layers <= 5):
        logging.error(f"Invalid number of layers received for thermal bridging: {num_layers}")
        return jsonify({"error": "Number of layers must be an integer between 3 and 5."}), 400

    try:
        # Generate the thermal bridging question
        question = thermal_bridging.generate_thermal_bridging_question(num_layers=num_layers)
        logging.info(f"Generated thermal bridging question with {num_layers} layers successfully.")

        # Generate the solution (thermal bridging heat loss chart)
        solution_image = thermal_bridging.plot_thermal_bridging_calculation(
            length=question['parameters']['length'],
            height=question['parameters']['height'],
            layers=question['parameters']['layers'],
            T_inside=question['parameters']['T_inside'],
            T_outside=question['parameters']['T_outside']
        )
        logging.info("Generated thermal bridging heat loss chart successfully.")

        # Prepare the response
        response = {
            "prompt": question['prompt'],
            "parameters": question['parameters'],
            "solution_image": solution_image  # Base64-encoded image
        }

        return jsonify(response)

    except ValueError as ve:
        logging.error(f"ValueError during thermal bridging question/solution generation: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"Unexpected error during thermal bridging question/solution generation: {e}")
        return jsonify({"error": "An unexpected error occurred while generating the thermal bridging question and solution."}), 500

if __name__ == '__main__':
    # For environments like Replit, use host='0.0.0.0' and a specific port
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port, debug=True)
