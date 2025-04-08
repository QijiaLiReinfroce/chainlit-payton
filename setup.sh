#!/bin/bash
# setup.sh
conda env create -f environment.yml
conda activate chainlit
pip install -e .  # If you have a setup.py file