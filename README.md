# Pokemon Visual Dataset

## Installation

1. Clone the project

```bash
git clone https://github.com/treeleaves30760/pokemon-visual-dataset
cd pokemon-visual-dataset
```

2. Install the dependency

```bash
conda create -n pokemon-visual python==3.11.10 -y
conda activate pokemon-visual
pip install -r requirements.txt
```

## Usage

```bash
python scrape_pokemon_data.py # Scrape whole pokemon from the website
python basic_dialog_generator.py # Generate the basic QA
```

## Reference

### Data Source
[歡迎來到神奇寶貝百科！](https://wiki.52poke.com/wiki/%E4%B8%BB%E9%A1%B5)