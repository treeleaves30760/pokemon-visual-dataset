import json
import os

def generate_basic_dialogues(input_file="data/pokemon_data.json", output_file="data/basicQA.json"):
    """Generate basic question-answer pairs for each Pokemon."""
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Load the Pokemon data
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            pokemon_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON in {input_file}. The file may be corrupted.")
        return False
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return False
    
    print(f"Loaded data for {len(pokemon_data)} Pokémon.")
    
    # Generate basic QA pairs
    basic_dialogues = []
    
    for pokemon in pokemon_data:
        try:
            # Get the basic information
            name = pokemon.get("name", "")
            
            main_image_path = pokemon.get("main_image_path", "")
            
            # Format the types
            types = pokemon.get("types", [])
            if not types:
                type_text = "Unknown-type"
            elif len(types) == 1:
                type_text = f"{types[0]}-type"
            else:
                type_text = f"{'/'.join(types)}-type"
            
            # Get the biology description
            biology_description = pokemon.get("biology_description", "")
            if not biology_description:
                biology_description = pokemon.get("general_description", "")
            
            # Create the simplified first sentence of the biology description
            if biology_description:
                first_sentence = biology_description.split('.')[0] + '.'
            else:
                first_sentence = ""
            
            # Create the dialogue entry
            dialogue = {
                "Name": name,
                "image": main_image_path,
                "problem": "What is in the images?",
                "solution": f"This is {name}, and is a {type_text} Pokemon. {first_sentence}"
            }
            
            basic_dialogues.append(dialogue)
            
        except Exception as e:
            print(f"Error processing Pokémon {pokemon.get('name', 'unknown')}: {str(e)}")
    
    # Exit if no valid dialogues were generated
    if not basic_dialogues:
        print("Error: No valid dialogues were generated.")
        return False
    
    # Save to JSON
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(basic_dialogues, f, ensure_ascii=False, indent=2)
        
        print(f"Generated {len(basic_dialogues)} basic dialogue pairs.")
        print(f"Output saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving dialogues to {output_file}: {str(e)}")
        return False

if __name__ == "__main__":
    generate_basic_dialogues() 