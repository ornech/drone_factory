# main.py
import yaml
import argparse
from pathlib import Path
from uav_generator.data_models import ProjectInput
from uav_generator.pipeline import PipelineOrchestrator

def main():
    """
    Main entry point for the UAV design generator application.
    """
    parser = argparse.ArgumentParser(
        description="Generate a UAV design from a mission specification."
    )
    parser.add_argument(
        "project_file",
        type=Path,
        help="Path to the project.yaml file.",
    )
    args = parser.parse_args()

    project_path: Path = args.project_file

    if not project_path.is_file():
        print(f"Error: Project file not found at '{project_path}'")
        exit(1)

    print(f"INFO: Loading project from '{project_path}'...")
    try:
        with open(project_path, 'r') as f:
            project_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML file. {e}")
        exit(1)
    except Exception as e:
        print(f"Error: Failed to read project file. {e}")
        exit(1)


    # Validate input data using Pydantic models
    try:
        project_input = ProjectInput(**project_data)
        print("INFO: Project file loaded and validated successfully.")
    except Exception as e:
        print(f"Error: Project file validation failed. {e}")
        exit(1)

    # Instantiate and run the generation pipeline
    orchestrator = PipelineOrchestrator(project_input, output_dir=project_path.parent)
    success = orchestrator.run()

    if success:
        print("\nINFO: UAV design package generated successfully.")
    else:
        print("\nERROR: UAV design generation failed due to blocking issues.")
        exit(1)


if __name__ == "__main__":
    main()
