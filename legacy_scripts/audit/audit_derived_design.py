#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit script for DerivedDesign field usage.
Parses data_models.py, scans repo for design.xxx = assignments, reports coverage.
"""

import ast
import os
import re
import glob
import sys
from pathlib import Path
from collections import defaultdict

def extract_deriveddesign_fields(data_models_path):
    """
    Parse src/uav_generator/data_models.py to extract DerivedDesign field names.
    Returns set of top-level field names (AnnAssign/Assign targets).
    """
    tree = ast.parse(open(data_models_path).read())
    
    fields = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'DerivedDesign':
            for body_node in node.body:
                if isinstance(body_node, (ast.AnnAssign, ast.Assign)):
                    # Get the target name (first target for Assign)
                    if isinstance(body_node, ast.AnnAssign):
                        target = body_node.target
                    else:  # Assign
                        target = body_node.targets[0]
                    
                    if isinstance(target, ast.Name):
                        fields.add(target.id)
    
    return fields

def find_used_fields(root_dir='.'):
    """
    Scan all .py files for 'design.xxx =' patterns.
    Returns dict: field -> list of files where used.
    """
    used = defaultdict(list)
    pattern = re.compile(r'design\.([a-zA-Z_][a-zA-Z0-9_]*)\s*=')
    
    for py_file in glob.glob(os.path.join(root_dir, '**/*.py'), recursive=True):
        try:
            content = open(py_file).read()
            for match in pattern.finditer(content):
                field = match.group(1)
                used[field].append(py_file)
        except Exception:
            pass  # Skip unreadable files
    
    return used

def main():
    root_dir = Path('.')
    data_models_path = root_dir / 'src/uav_generator/data_models.py'
    
    if not data_models_path.exists():
        print("ERROR: data_models.py not found!", file=sys.stderr)
        sys.exit(1)
    
    print("DerivedDesign Field Usage Audit")
    print("=" * 50)
    print()
    
    # Extract expected fields
    expected_fields = extract_deriveddesign_fields(data_models_path)
    print(f"Expected fields in DerivedDesign ({len(expected_fields)}):")
    for field in sorted(expected_fields):
        print(f"  - {field}")
    print()
    
    # Find used fields
    used_fields = find_used_fields()
    used_field_names = set(used_fields.keys())
    
    print("Fields used in code:")
    for field in sorted(used_field_names):
        files = used_fields[field]
        file_list = ', '.join(os.path.relpath(f, root_dir) for f in files)
        print(f"  - {field} (in {len(files)} files: {file_list})")
    print()
    
    # Analysis
    gaps = used_field_names - expected_fields  # Used but missing
    dead = expected_fields - used_field_names  # Defined but unused
    
    print("Coverage Analysis:")
    print(f"  Defined fields: {len(expected_fields)}")
    print(f"  Used fields:    {len(used_field_names)}")
    print(f"  Coverage:       {len(used_field_names & expected_fields) / len(expected_fields) * 100:.1f}%")
    print()
    
    if gaps:
        print("🚨 GAPS (used but NOT in DerivedDesign model):")
        for field in sorted(gaps):
            print(f"  - {field}")
        print()
    
    if dead:
        print("💀 DEAD CODE (in model but NOT used):")
        for field in sorted(dead):
            print(f"  - {field}")
        print()
    
    if not gaps and not dead:
        print("✅ Perfect coverage: All fields are used, no gaps!")
    
    print("\nAudit complete.")

if __name__ == '__main__':
    main()

