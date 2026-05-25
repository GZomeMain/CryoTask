#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CryoTask Entry Point
"""

import sys
import os

# Ensure the root directory is on the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.cryotask.main import main

if __name__ == "__main__":
    main()
